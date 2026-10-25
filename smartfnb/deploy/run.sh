#!/bin/bash
# SmartF&B Phase-0 总编排(在 k8s-master 上执行)
# 用法: ./run.sh <phase>  phase: all | images | db | datagen | warmup | bench | svc | verify
set -e
cd /opt/fnb/smartfnb
REG=10.167.2.175:30500
PH=${1:-all}
LOG=/opt/fnb/logs
mkdir -p $LOG

log() { echo "[$(date '+%F %T')] $*" | tee -a $LOG/run.log; }

build_images() {
  log "== 1. tools image =="
  docker build -q -t $REG/fnb/tools:0.1.7 -f tools/Dockerfile tools/ >> $LOG/build.log 2>&1
  docker push -q $REG/fnb/tools:0.1.7 >> $LOG/build.log 2>&1
  log "== 2. maven build (TDD tests run here) =="
  docker run --rm -v "$PWD/java":/ws -v /opt/fnb/.m2:/root/.m2 \
    -v "$PWD/java/settings.xml":/root/.m2/settings.xml \
    -w /ws $REG/base/maven:3.9.11-eclipse-temurin-25 \
    mvn -q -T2 package >> $LOG/maven.log 2>&1
  log "maven done:"; grep -hE "Tests run|BUILD" $LOG/maven.log | tail -5 || true
  for svc in recipe inventory portal; do
    log "== 3. java image $svc =="
    docker build -q -t $REG/fnb/svc-$svc:0.1.1 -f java/Dockerfile.$svc java/ >> $LOG/build.log 2>&1
    docker push -q $REG/fnb/svc-$svc:0.1.1 >> $LOG/build.log 2>&1
  done
  log "== 4. agent-runtime =="
  docker build -q -t $REG/fnb/agent-runtime:0.1.1 agent-runtime/ >> $LOG/build.log 2>&1
  docker push -q $REG/fnb/agent-runtime:0.1.1 >> $LOG/build.log 2>&1
  log "== 5. mcp-fnb-tools =="
  docker build -q -t $REG/fnb/mcp-fnb-tools:0.1.1 mcp-fnb-tools/ >> $LOG/build.log 2>&1
  docker push -q $REG/fnb/mcp-fnb-tools:0.1.1 >> $LOG/build.log 2>&1
  log "== 6. web-admin (npm build in container) =="
  docker build -q -t $REG/fnb/web-admin:0.1.1 web-admin/ >> $LOG/build.log 2>&1
  docker push -q $REG/fnb/web-admin:0.1.1 >> $LOG/build.log 2>&1
  log "ALL IMAGES BUILT & PUSHED"
}

wait_job() {
  local name=$1 timeout=${2:-60m}
  log "waiting job/$name (timeout $timeout)..."
  kubectl -n fnb-prod wait --for=condition=complete job/$name --timeout=$timeout >> $LOG/jobs.log 2>&1 \
    || { kubectl -n fnb-prod describe job/$name | tail -20 >> $LOG/jobs.log; log "JOB $name FAILED - see jobs.log"; return 1; }
  log "job/$name complete"
}

case $PH in
  images) build_images ;;
  db)
    kubectl -n fnb-prod delete job db-init --ignore-not-found
    kubectl apply -f deploy/01-infra-jobs.yaml
    wait_job db-init 10m
    kubectl logs -n fnb-prod job/db-init | tail -8 | tee -a $LOG/run.log
    ;;
  datagen)
    kubectl -n fnb-prod delete job data-gen --ignore-not-found
    kubectl apply -f deploy/02-datagen.yaml
    wait_job data-gen 150m
    ;;
  indexes)
    kubectl -n fnb-prod delete job db-indexes --ignore-not-found
    kubectl apply -f deploy/03-postload.yaml
    wait_job db-indexes 30m
    kubectl logs -n fnb-prod job/db-indexes -c idx | tail -20 | tee -a $LOG/run.log
    ;;
  warmup)
    kubectl -n fnb-prod delete job redis-warmup --ignore-not-found
    kubectl apply -f deploy/04-warmup-bench.yaml
    wait_job redis-warmup 30m
    kubectl logs -n fnb-prod job/redis-warmup | tail -3 | tee -a $LOG/run.log
    ;;
  bench)
    kubectl -n fnb-prod delete job llm-bench --ignore-not-found
    kubectl apply -f deploy/04-warmup-bench.yaml
    wait_job llm-bench 25m
    kubectl logs -n fnb-prod job/llm-bench | tail -10 | tee -a $LOG/run.log
    ;;
  svc)
    kubectl apply -f deploy/03-services.yaml
    kubectl -n fnb-prod rollout status deploy/svc-recipe --timeout=5m
    kubectl -n fnb-prod rollout status deploy/svc-inventory --timeout=5m
    kubectl -n fnb-prod rollout status deploy/svc-portal --timeout=5m
    kubectl -n fnb-prod rollout status deploy/mcp-fnb-tools --timeout=5m
    kubectl -n fnb-prod rollout status deploy/agent-runtime --timeout=5m
    kubectl -n fnb-prod rollout status deploy/web-admin --timeout=5m
    log "ALL SERVICES ROLLED OUT"
    ;;
  verify)
    log "== VERIFY =="
    NODE=10.167.2.175
    echo "-- health checks --"
    curl -s --max-time 10 http://$NODE:30251/actuator/health | head -c 200; echo
    curl -s --max-time 10 http://$NODE:30252/health; echo
    echo "-- GraphQL stores --"
    curl -s --max-time 15 -X POST http://$NODE:30251/graphql -H 'Content-Type: application/json' \
      -d '{"query":"{stores{id,name}}"}' | head -c 300; echo
    echo "-- diff report (sample) --"
    curl -s --max-time 60 -X POST http://$NODE:30251/graphql -H 'Content-Type: application/json' \
      -d '{"query":"{diffReport(storeId:7,date:\"2026-10-22\",limit:3){alertCount lines{ingName theoGram actualGram diffPct level}}}"}' | head -c 500; echo
    echo "-- web --"
    curl -s --max-time 10 -o /dev/null -w "web-admin http %{http_code}\n" http://$NODE:30250/
    ;;
  all)
    build_images
    $0 db
    $0 datagen
    $0 warmup
    $0 bench
    $0 svc
    $0 verify
    log "PHASE-0 PIPELINE COMPLETE"
    ;;
  *) echo "usage: run.sh {all|images|db|datagen|indexes|warmup|bench|svc|verify}"; exit 1 ;;
esac

#!/bin/bash
# Locust矩阵(v2): S3智能体SSE + S7混合业务流, 20/50/100用户×90s
set -u
cd /opt/fnb/smartfnb
REG=10.167.2.175:30500
IMG=$REG/perf/locust:latest
LOG=/opt/fnb/perf/matrix.log
echo "=== LOCUST START $(date) ===" >> $LOG

for U in 20 50 100; do
  for SC in s3_agent_sse s7_mixed; do
    SF="$SC.py"
    NAME="locust-${SC//_/-}-$U"
    echo "--- locust $SC @ ${U}users ---" >> $LOG
    kubectl -n fnb-prod run $NAME --image=$IMG --restart=Never --overrides="{\"spec\":{\"containers\":[{\"name\":\"locust\",\"image\":\"$IMG\",\"args\":[\"locust\",\"-f\",\"/scripts/$SF\",\"--headless\",\"-u\",\"$U\",\"-r\",\"$((U/5 > 0 ? U/5 : 1))\",\"--run-time\",\"90s\",\"--csv\",\"/tmp/out\",\"--host\",\"http://10.167.2.175:30252\"],\"volumeMounts\":[{\"name\":\"scripts\",\"mountPath\":\"/scripts\"}],\"resources\":{\"limits\":{\"cpu\":\"2\",\"memory\":\"2Gi\"}}}],\"volumes\":[{\"name\":\"scripts\",\"configMap\":{\"name\":\"locust-scripts\"}}]}}" >/dev/null 2>&1
    for i in $(seq 1 36); do
      ph=$(kubectl -n fnb-prod get pod $NAME -o jsonpath='{.status.phase}' 2>/dev/null || echo Gone)
      [ "$ph" = "Succeeded" ] || [ "$ph" = "Failed" ] || [ "$ph" = "Gone" ] && break
      sleep 5
    done
    kubectl -n fnb-prod logs $NAME >> $LOG 2>&1
    kubectl -n fnb-prod delete pod $NAME --force --grace-period=0 >/dev/null 2>&1
  done
done
echo "=== LOCUST DONE $(date) ===" >> $LOG

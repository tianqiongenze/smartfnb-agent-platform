#!/bin/bash
# 全量压测总编排(后台): 结果追加 /opt/fnb/perf/results.jsonl
set -u
cd /opt/fnb/smartfnb
LOG=/opt/fnb/perf/matrix.log
: > /opt/fnb/perf/results.jsonl
echo "=== MATRIX START $(date) ===" | tee -a $LOG

# A组: 闭环模型 5场景×5梯度(60s)
for V in 50 100 200 500 1000; do
  for S in s1 s2 s4 s5 s6; do
    echo "--- $S @ ${V}vu ---" >> $LOG
    bash tests/perf/run_perf.sh $S $V 60 NT >> $LOG 2>&1 || true
  done
done

# B组: 开放模型(到达率) — 验证§1.4口径 5-10K QPS
for RATE in 3000 6000; do
  echo "--- s1 open @ ${RATE}rps ---" >> $LOG
  TS=$(date +%H%M%S)
  kubectl -n fnb-prod run k6-open-$RATE --image=10.167.2.175:30500/perf/k6:0.1.0 --restart=Never --command -- \
    sh -c "k6 run -e BASE=http://svc-portal:8080 --summary-export=/tmp/s.json /scripts/s1_menu.js <<K6EOF
import http from 'k6/http';
import { check } from 'k6';
export const options = { scenarios: { open: { executor: 'constant-arrival-rate', rate: $RATE, timeUnit: '1s', duration: '60s', preAllocatedVUs: 2000, maxVUs: 20000 } }, discardResponseBodies: true };
const BASE = __ENV.BASE;
export default function () {
  const r = http.post(BASE + '/graphql', JSON.stringify({ query: '{stores{id,name}}' }), { headers: { 'Content-Type': 'application/json' } });
  check(r, { '200': (s) => s.status === 200 });
}
K6EOF
echo ===SUMMARY_BEGIN===; cat /tmp/s.json" >/dev/null 2>&1
  for i in $(seq 1 24); do
    ph=$(kubectl -n fnb-prod get pod k6-open-$RATE -o jsonpath='{.status.phase}' 2>/dev/null || echo Gone)
    [ "$ph" = "Succeeded" ] || [ "$ph" = "Failed" ] || [ "$ph" = "Gone" ] && break
    sleep 5
  done
  kubectl -n fnb-prod logs k6-open-$RATE > /opt/fnb/perf/open-${RATE}-${TS}.log 2>&1
  kubectl -n fnb-prod delete pod k6-open-$RATE --force --grace-period=0 >/dev/null 2>&1
  python3 - "/opt/fnb/perf/open-${RATE}-${TS}.log" "open-${RATE}rps" <<'PYEOF'
import json, sys, re
log = open(sys.argv[1], encoding="utf-8", errors="replace").read()
i = log.find("===SUMMARY_BEGIN===")
s = None
if i >= 0:
    m = re.search(r"\{.*\}", log[i:], re.S)
    if m:
        try: s = json.loads(m.group(0))
        except Exception: pass
if s:
    md = s["metrics"]; dur = md.get("http_req_duration", {})
    r = {"name": sys.argv[2], "requests": md.get("http_reqs", {}).get("count"),
         "rps": round(md.get("http_reqs", {}).get("rate", 0), 1),
         "p50": round(dur.get("med", 0), 1), "p95": round(dur.get('p(95)', 0), 1),
         "p99": round(dur.get('p(99)', 0), 1),
         "errPct": round(md.get("http_req_failed", {}).get("rate", 0) * 100, 2)}
    print(json.dumps(r, ensure_ascii=False))
    open("/opt/fnb/perf/results.jsonl", "a").write(json.dumps(r, ensure_ascii=False) + "\n")
else:
    print(sys.argv[2] + " PARSE_FAIL")
PYEOF
done

# C组: 风暴探针 10K VU / 100K VU(单Pod尽力而为, 超容量即取证)
for VU in 10000 100000; do
  echo "--- s1 storm @ ${VU}vu ---" >> $LOG
  TS=$(date +%H%M%S)
  kubectl -n fnb-prod run k6-storm-$VU --image=10.167.2.175:30500/perf/k6:0.1.0 --restart=Never \
    --overrides='{"spec":{"containers":[{"name":"k6","image":"10.167.2.175:30500/perf/k6:0.1.0","command":["sh","-c"],"args":["k6 run -e BASE=http://svc-portal:8080 --summary-export=/tmp/s.json /scripts/s1_menu.js <<K6EOF\nimport http from '"'"'k6/http'"'"';\nexport const options = { scenarios: { storm: { executor: '"'"'ramping-vus'"'"', startVUs: 0, stages: [{ duration: '"'"'20s'"'"', target: $VU }, { duration: '"'"'30s'"'"', target: $VU }, { duration: '"'"'10s'"'"', target: 0 }] }, discardResponseBodies: true, noConnectionReuse: false };\nconst BASE = __ENV.BASE;\nexport default function () { http.post(BASE + '"'"'/graphql'"'"', JSON.stringify({ query: '"'"'{stores{id,name}}'"'"' }), { headers: { '"'"'Content-Type'"'"': '"'"'application/json'"'"' } }); }\nK6EOF\necho ===SUMMARY_BEGIN===; cat /tmp/s.json"],"resources":{"limits":{"cpu":"4","memory":"8Gi"}}}]}}' >/dev/null 2>&1
  for i in $(seq 1 40); do
    ph=$(kubectl -n fnb-prod get pod k6-storm-$VU -o jsonpath='{.status.phase}' 2>/dev/null || echo Gone)
    [ "$ph" = "Succeeded" ] || [ "$ph" = "Failed" ] || [ "$ph" = "Gone" ] && break
    sleep 5
  done
  kubectl -n fnb-prod logs k6-storm-$VU > /opt/fnb/perf/storm-${VU}-${TS}.log 2>&1
  kubectl -n fnb-prod delete pod k6-storm-$VU --force --grace-period=0 >/dev/null 2>&1
  python3 - "/opt/fnb/perf/storm-${VU}-${TS}.log" "storm-${VU}vu" <<'PYEOF'
import json, sys, re
log = open(sys.argv[1], encoding="utf-8", errors="replace").read()
i = log.find("===SUMMARY_BEGIN===")
s = None
if i >= 0:
    m = re.search(r"\{.*\}", log[i:], re.S)
    if m:
        try: s = json.loads(m.group(0))
        except Exception: pass
if s:
    md = s["metrics"]; dur = md.get("http_req_duration", {})
    r = {"name": sys.argv[2], "requests": md.get("http_reqs", {}).get("count"),
         "rps": round(md.get("http_reqs", {}).get("rate", 0), 1),
         "p50": round(dur.get("med", 0), 1), "p95": round(dur.get('p(95)', 0), 1),
         "p99": round(dur.get('p(99)', 0), 1),
         "errPct": round(md.get("http_req_failed", {}).get("rate", 0) * 100, 2)}
    print(json.dumps(r, ensure_ascii=False))
    open("/opt/fnb/perf/results.jsonl", "a").write(json.dumps(r, ensure_ascii=False) + "\n")
else:
    print(sys.argv[2] + " PARSE_FAIL")
PYEOF
done

echo "=== K6 MATRIX DONE $(date) ===" | tee -a $LOG

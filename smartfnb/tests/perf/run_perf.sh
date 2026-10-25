#!/bin/bash
# R9 梯度编排器(v3): 非交互Pod + logs 收全量输出(确定性)
# 用法: run_perf.sh <s1|s2|s4|s5|s6> <vus> [dur_s] [NT]
set -e
SC=$1; VUS=$2; DUR=${3:-120}; NT=${4:-}
REG=10.167.2.175:30500
IMG=$REG/perf/k6:0.1.0
OUT=/opt/fnb/perf; mkdir -p $OUT
TS=$(date +%H%M%S)
NAME="k6-${SC}-${VUS}vu-${TS}"
LOG=$OUT/${SC}-${VUS}vu-${TS}.log

case $SC in
  s1) SCRIPT=s1_menu.js;     BASE=http://svc-portal:8080 ;;
  s2) SCRIPT=s2_diff.js;     BASE=http://svc-portal:8080 ;;
  s4) SCRIPT=s4_write.js;    BASE=http://svc-inventory:8080 ;;
  s5) SCRIPT=s5_member.js;   BASE=http://svc-member:8080 ;;
  s6) SCRIPT=s6_forecast.js; BASE=http://svc-forecast:8000 ;;
  open) SCRIPT=open_s1.js;   BASE=http://svc-portal:8080 ;;
  storm) SCRIPT=storm_s1.js; BASE=http://svc-portal:8080 ;;
  *) echo "unknown scenario: $SC"; exit 1 ;;
esac

ENVV="-e VUS=$VUS -e DUR=${DUR}s -e BASE=$BASE"
[ "$SC" = "storm" ] && ENVV="-e STORM_VUS=$VUS -e BASE=$BASE"
[ "$SC" = "open" ] && ENVV="-e RATE=$VUS -e DUR=${DUR}s -e BASE=$BASE -e NO_THRESH=1 -e PRE=4000 -e MAX=30000"
[ -n "$NT" ] && ENVV="$ENVV -e NO_THRESH=1"

kubectl -n fnb-prod run $NAME --image=$IMG --restart=Never --command -- \
  sh -c "k6 run $ENVV --summary-export=/tmp/summary.json /scripts/$SCRIPT; echo ===SUMMARY_BEGIN===; cat /tmp/summary.json" >/dev/null

for i in $(seq 1 $((DUR + 60))); do
  phase=$(kubectl -n fnb-prod get pod $NAME -o jsonpath='{.status.phase}' 2>/dev/null || echo Gone)
  if [ "$phase" = "Succeeded" ] || [ "$phase" = "Failed" ] || [ "$phase" = "Gone" ]; then break; fi
  sleep 5
done
sleep 3
kubectl -n fnb-prod logs $NAME > $LOG 2>&1 || true
kubectl -n fnb-prod delete pod $NAME --ignore-not-found --force --grace-period=0 >/dev/null 2>&1 || true

python3 - "$LOG" "${SC}-${VUS}vu-${TS}" <<'PYEOF'
import json, sys, re
log, name = sys.argv[1], sys.argv[2]
i = log.find("===SUMMARY_BEGIN===")
s = None
if i >= 0:
    mm = re.search(r"\{.*\}", log[i:], re.S)
    if mm:
        try:
            s = json.loads(mm.group(0))
        except Exception:
            s = None
if s is None:
    print(f"{name} PARSE_FAIL"); sys.exit(0)
md = s.get("metrics", {})
dur = md.get("http_req_duration", {})
r = {"name": name,
     "requests": md.get("http_reqs", {}).get("count"),
     "rps": round(md.get("http_reqs", {}).get("rate", 0), 1),
     "p50": round(dur.get("med", 0), 1),
     "p95": round(dur.get('p(95)', 0), 1),
     "p99": round(dur.get('p(99)', 0), 1),
     "errPct": round(md.get("http_req_failed", {}).get("rate", 0) * 100, 2)}
print(json.dumps(r, ensure_ascii=False))
with open("/opt/fnb/perf/results.jsonl", "a") as f:
    f.write(json.dumps(r, ensure_ascii=False) + "\n")
PYEOF

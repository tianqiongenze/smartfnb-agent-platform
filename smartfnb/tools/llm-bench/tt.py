#!/usr/bin/env python3
import json, time, urllib.request, sys

BASE = "http://10.167.2.176:30253"
model = sys.argv[1] if len(sys.argv) > 1 else "qwen3:4b"
threads = int(sys.argv[2]) if len(sys.argv) > 2 else 16
n = int(sys.argv[3]) if len(sys.argv) > 3 else 60

body = json.dumps({"model": model, "prompt": "用50字说明食材浪费监控的价值", "stream": False,
                   "options": {"num_predict": n, "num_thread": threads}}).encode()
t0 = time.time()
req = urllib.request.Request(BASE + "/api/generate", body, {"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=900) as r:
    d = json.loads(r.read())
wall = time.time() - t0
ec = d.get("eval_count", 0)
ed = max(d.get("eval_duration", 1), 1)
ld = d.get("load_duration", 0) / 1e9
print(f"{model} threads={threads}: {ec} tok | {ec/(ed/1e9):.1f} tok/s | load={ld:.1f}s | wall={wall:.0f}s | eval={ed/1e9:.1f}s")
print("head:", d.get("response", "")[:60])

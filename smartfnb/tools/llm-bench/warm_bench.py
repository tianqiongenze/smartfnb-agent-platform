#!/usr/bin/env python3
"""Phase-0 LLM吞吐实测(热推理): master上直跑, 经NodePort访问worker上的Ollama"""
import json, time, urllib.request

BASE = "http://10.167.2.176:30086"
PROMPT = "用100字说明食材浪费监控的价值"
NUM = 150

def gen(model, timeout=280):
    body = json.dumps({"model": model, "prompt": PROMPT, "stream": False,
                       "options": {"num_predict": NUM}}).encode()
    t0 = time.time()
    req = urllib.request.Request(BASE + "/api/generate", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    wall = time.time() - t0
    ec, ed = d.get("eval_count", 0), max(d.get("eval_duration", 1), 1)
    print(f"{model}: {ec} tok | {ec/(ed/1e9):.1f} tok/s(模型计算) | {ec/wall:.1f} tok/s(含排队) | "
          f"load={d.get('load_duration',0)/1e9:.1f}s | eval={ed/1e9:.1f}s", flush=True)
    return ec, wall

if __name__ == "__main__":
    for m in ("qwen3:4b", "qwen3:8b"):
        for run in (1, 2):
            try:
                gen(m)
            except Exception as e:
                print(f"{m} run{run} FAILED: {e}", flush=True)

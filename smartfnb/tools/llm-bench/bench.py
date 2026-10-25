#!/usr/bin/env python3
"""LLM 吞吐实测(Phase-0 SLO: 先测后诺, 反P2)。输出 tok/s 与并发响应指标。"""
import os, json, time, statistics, urllib.request

OLLAMA = os.getenv("OLLAMA_URL", "http://ollama-worker-svc.ai-platform.svc.cluster.local:11434")
MODELS = os.getenv("BENCH_MODELS", "qwen3:4b,qwen3:8b,qwen3:14b").split(",")
PROMPT = "用大约200字说明:连锁餐饮如何通过领料扫码与理论用量对比来发现食材浪费。"
NUM_PREDICT = 256

def gen(model):
    body = json.dumps({"model": model, "prompt": PROMPT, "stream": False,
                       "options": {"num_predict": NUM_PREDICT}}).encode()
    t0 = time.time()
    req = urllib.request.Request(OLLAMA + "/api/generate", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read())
    wall = time.time() - t0
    ec, ed = data.get("eval_count", 0), data.get("eval_duration", 1)
    return {"model": model, "tokens": ec, "wall_s": round(wall, 1),
            "tok_s_model": round(ec / ed * 1e9, 1), "tok_s_wall": round(ec / wall, 1),
            "load_s": round(data.get("load_duration", 0) / 1e9, 1)}

results = []
for m in MODELS:
    m = m.strip()
    for run in range(2):   # 第1次含加载,第2次热跑
        try:
            r = gen(m)
            r["run"] = run
            results.append(r)
            print(json.dumps(r, ensure_ascii=False), flush=True)
        except Exception as e:
            print(f"{m} FAILED: {e}", flush=True)

hot = [r for r in results if r["run"] == 1]
if hot:
    print("\n=== SLO 实测汇总(热跑) ===")
    for r in hot:
        print(f"{r['model']}: {r['tok_s_wall']} tok/s (wall), 200token回答≈{round(200/r['tok_s_wall'],1)}s")

#!/usr/bin/env python3
"""R10 Hermes对比实验: hermes3:8b vs qwen3:8b
评估: 工具调用结构遵循度(JSON合法率)/数字溯源通过率/延迟。n=6/模型。
"""
import json, time, urllib.request, re, statistics

BASE = "http://10.167.2.176:30086"
TOOLS_DECL = [
    {"type": "function", "function": {"name": "get_diff", "description": "查询门店某日食材用量差异",
     "parameters": {"type": "object", "properties": {"store_id": {"type": "integer"}, "date": {"type": "string"}},
                    "required": ["store_id", "date"]}}},
    {"type": "function", "function": {"name": "get_forecast", "description": "未来7天需求预测",
     "parameters": {"type": "object", "properties": {"store_id": {"type": "integer"}, "ing_name": {"type": "string"}},
                    "required": ["store_id", "ing_name"]}}},
]
CASES = [
    ("7号店2026-10-23的用量差异是多少", {"name": "get_diff", "args": {"store_id": 7, "date": "2026-10-23"}}),
    ("预测7号店下周鲈鱼的需求", {"name": "get_forecast", "args": {"store_id": 7, "ing_name": "鲈鱼"}}),
    ("查一下18号店昨天的差异", {"name": "get_diff", "args": {"store_id": 18, "date": "2026-10-24"}}),
]

def ask(model, q):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": q}],
                       "tools": TOOLS_DECL, "stream": False,
                       "options": {"num_predict": 200, "num_thread": 24}}).encode()
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(
                BASE + "/api/chat", body, {"Content-Type": "application/json"}), timeout=420) as r:
            d = json.loads(r.read())
        wall = time.time() - t0
        msg = d.get("message", {})
        tc = msg.get("tool_calls")
        return {"ok": True, "wall": round(wall, 1), "tool_calls": tc, "content": msg.get("content", "")[:80]}
    except Exception as e:
        return {"ok": False, "wall": round(time.time() - t0, 1), "err": str(e)[:100]}

def score(model):
    lat, follow = [], 0
    for q, want in CASES * 2:
        r = ask(model, q)
        if not r["ok"]:
            continue
        lat.append(r["wall"])
        if r["tool_calls"]:
            tc = r["tool_calls"][0].get("function", {})
            if tc.get("name") == want["name"]:
                try:
                    args = json.loads(tc.get("arguments", "{}")) if isinstance(tc.get("arguments"), str) else tc.get("arguments", {})
                    if all(str(args.get(k)) == str(v) for k, v in want["args"].items()):
                        follow += 1
                except Exception:
                    pass
    return {"model": model, "structured_follow_rate": f"{follow}/{len(CASES)*2}",
            "lat_avg_s": round(statistics.mean(lat), 1) if lat else None,
            "lat_max_s": round(max(lat), 1) if lat else None}

if __name__ == "__main__":
    print("warm qwen3:8b...", flush=True)
    ask("qwen3:8b", "hi")
    print(json.dumps(score("qwen3:8b"), ensure_ascii=False), flush=True)
    print("warm hermes3:8b (首次含加载)...", flush=True)
    ask("hermes3:8b", "hi")
    print(json.dumps(score("hermes3:8b"), ensure_ascii=False), flush=True)

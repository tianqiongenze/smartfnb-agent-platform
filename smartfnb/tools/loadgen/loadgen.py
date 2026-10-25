#!/usr/bin/env python3
"""负载测试(Phase2第一轮/Phase3全量): asyncio四场景。
S1 菜单GraphQL | S2 差异报表GraphQL | S3 智能体FAQ(缓存命中) | S4 领料写入
输出: RPS/P50/P95/P99/错误率。口径见总体方案§11.5。
"""
import asyncio, json, time, statistics, os, sys
import aiohttp

PORTAL = os.getenv("PORTAL_URL", "http://10.167.2.175:30251")
AGENT = os.getenv("AGENT_URL", "http://10.167.2.175:30252")

def pct(sorted_vals, p):
    if not sorted_vals:
        return 0
    k = min(int(len(sorted_vals) * p / 100), len(sorted_vals) - 1)
    return sorted_vals[k]

async def scenario(name, url, payload_fn, conc, seconds, is_sse=False):
    lat, errs = [], 0
    deadline = time.time() + seconds
    async with aiohttp.ClientSession() as sess:
        async def worker():
            nonlocal errs
            while time.time() < deadline:
                t0 = time.time()
                try:
                    async with sess.post(url, json=payload_fn(), timeout=aiohttp.ClientTimeout(total=30)) as r:
                        body = await r.read()
                        if r.status != 200:
                            errs += 1
                        elif is_sse and b'"event": "answer"' not in body and b'"event":"answer"' not in body:
                            errs += 1
                except Exception:
                    errs += 1
                lat.append((time.time() - t0) * 1000)
        await asyncio.gather(*[worker() for _ in range(conc)])
    lat.sort()
    n = len(lat)
    rps = round(n / seconds, 1)
    res = {"scenario": name, "conc": conc, "requests": n, "rps": rps,
           "p50": round(pct(lat, 50), 1), "p95": round(pct(lat, 95), 1),
           "p99": round(pct(lat, 99), 1), "errPct": round(errs / max(n, 1) * 100, 2)}
    print(json.dumps(res, ensure_ascii=False), flush=True)
    return res

def gql(query, variables=None):
    return lambda: {"query": query, "variables": variables or {}}

async def main():
    secs = int(os.getenv("SECS", "60"))
    results = []
    print(f"=== 负载测试 {secs}s/场景 ===", flush=True)
    results.append(await scenario("S1_菜单浏览", PORTAL + "/graphql",
        gql("{stores{id,name}}"), int(os.getenv("S1_CONC", "200")), secs))
    results.append(await scenario("S2_差异报表", PORTAL + "/graphql",
        gql("query($s:Int,$d:String!){diffReport(storeId:$s,date:$d,limit:60){alertCount lines{ingName diffPct}}}",
            {"s": 7, "d": "2026-10-23"}), int(os.getenv("S2_CONC", "30")), secs))
    results.append(await scenario("S3_智能体FAQ缓存", AGENT + "/api/agent/chat",
        lambda: {"question": "怎么降低蔬菜浪费", "storeId": 7, "date": "2026-10-23"},
        int(os.getenv("S3_CONC", "10")), secs, is_sse=True))
    results.append(await scenario("S4_领料写入", PORTAL + "/api/movements",
        lambda: {"storeId": 1 + int(time.time()) % 32, "ingId": 1 + int(time.time() * 7) % 500,
                 "movementType": "consume", "qty": 1.5, "unitCode": "kg"},
        int(os.getenv("S4_CONC", "30")), secs))
    print("=== PASS标准: S1 P95<300ms / S2 P95<1s / S3 P95<1s / S4 P95<500ms, 错误率<1% ===", flush=True)

if __name__ == "__main__":
    asyncio.run(main())

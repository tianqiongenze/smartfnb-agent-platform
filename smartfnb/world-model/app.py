"""R4 World Model — 门店运营数字孪生(统计仿真形态):
- 从 daily_demand 拟合 (店,食材,星期) 的需求分布(均值/标准差)
- /simulate: 蒙特卡洛推演采购量方案 → 缺货/浪费期望成本, 输出最优量
- /forecast-ci: 未来N天 p10/p50/p90 置信区间
学术口径: 基于历史统计的业务世界模型(Business World Model), 非神经世界模型(Genie类)——
在无GPU教学环境下的可落地形态, 决策前先仿真(what-if)。
"""
from __future__ import annotations

import datetime as dt
import math
import os
import random
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pymysql
from litestar import Litestar, get, post
from litestar.status_codes import HTTP_200_OK

DB = dict(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
          user="root", charset="utf8mb4", database="fnb")

STATS: dict[tuple[int, int, int], tuple[float, float]] = {}   # (store,ing,weekday)->(mean,sd)
PRICE: dict[int, float] = {}
LOADED_AT: float = 0

def load_stats() -> None:
    global STATS, PRICE, LOADED_AT
    c = pymysql.connect(**DB)
    try:
        cur = c.cursor()
        cur.execute("""SELECT store_id, ing_id, WEEKDAY(stat_date) wd,
                              AVG(demand_gram), STDDEV_SAMP(demand_gram)
                       FROM daily_demand GROUP BY store_id, ing_id, WEEKDAY(stat_date)""")
        for s, i, wd, avg, sd in cur.fetchall():
            STATS[(s, i, wd)] = (float(avg or 0), float(sd or 0))
        cur.execute("SELECT ing_id, ref_price FROM ingredient WHERE ref_price IS NOT NULL")
        PRICE.clear()
        PRICE.update({i: float(p) for i, p in cur.fetchall()})
        LOADED_AT = dt.datetime.now().timestamp()
    finally:
        c.close()

def ensure_stats(max_age_s: int = 3600):
    if not STATS or dt.datetime.now().timestamp() - LOADED_AT > max_age_s:
        load_stats()

def resolve_ing(name: str) -> int | None:
    c = pymysql.connect(**DB)
    try:
        cur = c.cursor()
        cur.execute("SELECT ing_id FROM ingredient WHERE name_std=%s LIMIT 1", (name,))
        r = cur.fetchone()
        return r[0] if r else None
    finally:
        c.close()

SHORTAGE_COST_MULT = 3.0      # 缺货损失=食材价×3(客诉+流失)

def simulate_policy(mean: float, sd: float, qty: float, days: int, price: float,
                    trials: int = 2000, rng: random.Random | None = None) -> dict:
    rng = rng or random.Random(42)
    short = waste = 0.0
    for _ in range(trials):
        for _d in range(days):
            demand = max(0, rng.gauss(mean, sd))
            short += max(0.0, demand - qty)
            waste += max(0.0, qty - demand)
    n = trials * days
    es, ew = short / n, waste / n                       # 期望克/天
    cost = es / 1000 * price * SHORTAGE_COST_MULT + ew / 1000 * price
    return {"qtyPerDayKg": round(qty / 1000, 2),
            "expectedShortageKgPerDay": round(es / 1000, 2),
            "expectedWasteKgPerDay": round(ew / 1000, 2),
            "expectedCostPerDay": round(cost, 1)}

@asynccontextmanager
async def _lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    load_stats()
    print(f"WORLD_MODEL_READY stats={len(STATS)}", flush=True)
    yield

@get("/health")
async def health() -> dict:
    return {"status": "ok", "stats": len(STATS), "loadedAt": LOADED_AT}

@post("/simulate", status_code=HTTP_200_OK)
async def simulate(data: dict) -> dict:
    """采购量方案推演: 自动扫描0.6x~1.4x均值共9档, 输出各档成本与最优档"""
    ensure_stats()
    store, ing = int(data["storeId"]), str(data["ingName"])
    days = int(data.get("days", 7))
    iid = resolve_ing(ing)
    if iid is None:
        return {"error": f"未找到食材: {ing}", "degraded": True}
    today = dt.date.today()
    means = []
    for d in range(days):
        wd = (today + dt.timedelta(days=d)).weekday()
        m, sd = STATS.get((store, iid, wd), (0, 0))
        means.append((m or 0.0, sd or (m * 0.3 if m else 0.0)))
    avg_mean = sum(m for m, _ in means) / len(means)
    overall_sd = sum(s for _, s in means) / len(means)
    price = PRICE.get(iid, 20.0)
    plans = []
    overall_sd = sum(s for _, s in means) / len(means)
    for f in [0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4]:
        plans.append(simulate_policy(avg_mean, overall_sd, avg_mean * f, days, price,
                                     trials=800, rng=random.Random(42)))
    best = min(plans, key=lambda p: p["expectedCostPerDay"])
    return {"storeId": store, "ingId": iid, "ingName": ing, "days": days,
            "avgDemandKgPerDay": round(avg_mean / 1000, 2),
            "shortageCostMultiplier": SHORTAGE_COST_MULT,
            "plans": plans, "recommended": best,
            "method": "蒙特卡洛(800 trials/档) × 正态拟合(店×食材×星期)"}

@get("/forecast-ci", status_code=HTTP_200_OK)
async def forecast_ci(storeId: int, ingName: str, days: int = 7) -> dict:
    ensure_stats()
    iid = resolve_ing(ingName)
    if iid is None:
        return {"error": f"未找到食材: {ingName}", "degraded": True}
    today = dt.date.today()
    rng = random.Random(7)
    out = []
    for d in range(days):
        date = today + dt.timedelta(days=d)
        m, sd = STATS.get((storeId, iid, date.weekday()), (0, 0))
        samples = [max(0, rng.gauss(m, sd or (m * 0.3 if m else 0))) for _ in range(1000)]
        samples.sort()
        out.append({"date": date.isoformat(),
                    "p10Kg": round(samples[100] / 1000, 2),
                    "p50Kg": round(samples[500] / 1000, 2),
                    "p90Kg": round(samples[900] / 1000, 2)})
    return {"storeId": storeId, "ingName": ingName, "days": out,
            "method": "分布抽样1000次/日 (p10-p90置信带)"}

app = Litestar(route_handlers=[health, simulate, forecast_ci], lifespan=[_lifespan])

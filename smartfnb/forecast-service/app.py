"""svc-forecast 需求预测服务(Litestar + uvicorn, Phase3)
GET /api/forecast?storeId=&ingName=&days=7 → 逐日预测+置信度+依赖声明(反P6)
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date as _date
from typing import AsyncGenerator

import pymysql
from litestar import Litestar, get
from litestar.status_codes import HTTP_200_OK

from forecast_core import forecast_days, freshness_check

DB = dict(host=os.getenv("DB_HOST", "tidb.infra.svc.cluster.local"), port=4000,
          user="root", charset="utf8mb4", database="fnb")

def q(sql: str, args: tuple = ()) -> list[dict]:
    c = pymysql.connect(**DB)
    try:
        cur = c.cursor(pymysql.cursors.DictCursor)
        cur.execute(sql, args)
        return cur.fetchall()
    finally:
        c.close()

@asynccontextmanager
async def _lifespan(app: Litestar) -> AsyncGenerator[None, None]:
    c = pymysql.connect(**DB)
    c.close()
    print("forecast service ready", flush=True)
    yield

@get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "svc-forecast"}

@get("/api/forecast", status_code=HTTP_200_OK)
async def forecast(storeId: int, ingName: str, days: int = 7) -> dict:
    ing = q("SELECT ing_id, name_std FROM ingredient WHERE name_std=%s LIMIT 1", (ingName,))
    if not ing:
        return {"error": f"未找到食材: {ingName}", "degraded": True}
    iid = ing[0]["ing_id"]
    # 依赖声明: 基表新鲜度
    mx = q("SELECT MAX(stat_date) m FROM daily_demand WHERE store_id=%s AND ing_id=%s", (storeId, iid))
    fresh = freshness_check(mx[0]["m"], _date.today())
    series = [(r["stat_date"], float(r["demand_gram"])) for r in q(
        """SELECT stat_date, demand_gram FROM daily_demand
           WHERE store_id=%s AND ing_id=%s AND stat_date >= %s ORDER BY stat_date""",
        (storeId, iid, _date.today() - __import__("datetime").timedelta(days=70)))]
    days_fc = forecast_days(series, _date.today(), min(days, 14))
    # 全局降级优先(依赖不满足), 否则用回测置信度
    for d in days_fc:
        if fresh["degraded"]:
            d["demand_gram"] = None
            d["degraded"] = True
            d["reason"] = fresh["reason"]
            d["fallback"] = fresh["fallback"]
    return {"storeId": storeId, "ingredient": ing[0], "days": days_fc,
            "dependency": fresh,
            "trace": {"sql": "SELECT ... FROM daily_demand WHERE store_id=%s AND ing_id=%s (预计算表005)",
                      "method": "加权移动平均×周内因子×趋势, 回测MAPE置信度"}}

app = Litestar(route_handlers=[health, forecast], lifespan=[_lifespan])

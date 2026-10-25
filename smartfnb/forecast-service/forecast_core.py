"""需求预测纯算法(Phase3, pytest可测):
加权移动平均 × 周内季节因子 × 趋势比; 回测MAPE决定置信度。
依赖声明(反P6): 数据新鲜度不足时 degraded=true + fallback建议。
"""
from __future__ import annotations

import datetime as dt

HIGH_MAPE, MED_MAPE = 20.0, 35.0

def weekday_factors(series: list[tuple[dt.date, float]]) -> dict[int, float]:
    """周内因子: 各星期均量 / 总均量(≥4周样本才启用, 否则全1.0)"""
    by_wd: dict[int, list[float]] = {}
    for d, v in series:
        by_wd.setdefault(d.weekday(), []).append(v)
    weeks = max((len(v) for v in by_wd.values()), default=0)
    all_v = [v for _, v in series]
    mean = sum(all_v) / len(all_v) if all_v else 0
    if mean <= 0 or weeks < 4:
        return {}
    return {wd: (sum(v) / len(v)) / mean for wd, v in by_wd.items() if sum(v) > 0}

def forecast_days(series: list[tuple[dt.date, float]], start: dt.date, days: int = 7) -> list[dict]:
    """series: 历史按日需求(克)。返回逐日预测列表(含置信度与回测MAPE)。"""
    out = []
    if not series:
        return [{"date": (start + dt.timedelta(days=i)).isoformat(), "demand_gram": None,
                 "degraded": True, "reason": "无历史数据", "fallback": "建议参考同类食材近7日均值"}
                for i in range(days)]
    by_date = dict(series)
    factors = weekday_factors(series)
    values = [v for _, v in series]
    # 趋势: 近7日均 / 之前28日均
    recent = values[-7:]
    prior = values[-35:-7]
    trend = (sum(recent) / len(recent)) / (sum(prior) / len(prior)) if prior and sum(prior) > 0 else 1.0
    trend = max(0.5, min(trend, 2.0))
    # 回测: 用倒数15~8天的数据预测倒数7天, 计算MAPE
    mape = _backtest_mape(series)
    conf = "HIGH" if mape <= HIGH_MAPE else ("MEDIUM" if mape <= MED_MAPE else "LOW")
    for i in range(days):
        d = start + dt.timedelta(days=i)
        f = factors.get(d.weekday(), 1.0)
        pred = sum(values[-28:]) / min(len(values), 28) * f * trend
        out.append({"date": d.isoformat(), "demand_gram": round(max(pred, 0)),
                    "degraded": False, "confidence": conf, "mape": round(mape, 1)})
    return out

def _backtest_mape(series: list[tuple[dt.date, float]]) -> float:
    """留出最后7天做回测: 用前段同星期均值预测, MAPE百分比"""
    if len(series) < 22:
        return 50.0
    train = dict(series[:-7])
    errs = []
    for d, actual in series[-7:]:
        same = [v for dd, v in train.items() if dd.weekday() == d.weekday()]
        pred = sum(same) / len(same) if same else sum(train.values()) / len(train)
        if actual > 0:
            errs.append(abs(pred - actual) / actual * 100)
    return sum(errs) / len(errs) if errs else 50.0

def freshness_check(max_stat_date: dt.date | None, today: dt.date, max_lag: int = 3) -> dict:
    """数据依赖声明(反P6): daily_demand最后日期滞后>3天 → 降级输出"""
    if max_stat_date is None:
        return {"degraded": True, "reason": "预测基表为空", "fallback": "建议参考近7日均值"}
    lag = (today - max_stat_date).days
    if lag > max_lag:
        return {"degraded": True, "reason": f"需求数据滞后{lag}天(阈值{max_lag}), 预测置信度不足",
                "fallback": "建议参考近7日均值, 并检查数据管道"}
    return {"degraded": False, "reason": None, "fallback": None}

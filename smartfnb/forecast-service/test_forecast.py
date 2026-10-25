import datetime as dt
from forecast_core import weekday_factors, forecast_days, freshness_check


class TestForecast:
    def _series(self, base=10000.0, weeks=10):
        out = []
        d0 = dt.date(2026, 8, 1)
        for i in range(weeks * 7):
            d = d0 + dt.timedelta(days=i)
            wk = 1.3 if d.weekday() >= 5 else 0.9     # 周末高峰
            out.append((d, round(base * wk * (1 + 0.01 * (i % 7)))))
        return out

    def test_weekend_factor_detected(self):
        f = weekday_factors(self._series())
        assert f and f[5] > 1.15 and f[1] < 1.0      # 周六放大, 周一缩小

    def test_forecast_shape_and_confidence(self):
        fc = forecast_days(self._series(), dt.date(2026, 10, 10), days=7)
        assert len(fc) == 7 and all(x["demand_gram"] > 0 for x in fc)
        assert all(x["confidence"] in ("HIGH", "MEDIUM", "LOW") for x in fc)

    def test_weekend_peak_higher_than_weekday(self):
        fc = forecast_days(self._series(), dt.date(2026, 10, 10), days=7)
        by = {x["date"]: x["demand_gram"] for x in fc}
        sat = dt.date(2026, 10, 10)                   # 周六
        mon = dt.date(2026, 10, 12)                   # 周一
        assert by[sat.isoformat()] > by[mon.isoformat()]

    def test_empty_series_degrades(self):
        fc = forecast_days([], dt.date(2026, 10, 10), days=3)
        assert all(x["degraded"] and x["demand_gram"] is None for x in fc)

    def test_freshness_ok(self):
        r = freshness_check(dt.date(2026, 10, 23), dt.date(2026, 10, 24))
        assert not r["degraded"]

    def test_freshness_stale_degrades(self):
        """反P6: 数据滞后>3天必须降级并给fallback, 禁止静默输出低置信预测"""
        r = freshness_check(dt.date(2026, 10, 1), dt.date(2026, 10, 24))
        assert r["degraded"] and "滞后" in r["reason"] and r["fallback"]

    def test_freshness_empty(self):
        assert freshness_check(None, dt.date(2026, 10, 24))["degraded"]

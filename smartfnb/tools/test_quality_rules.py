import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "quality"))
import datetime as dt
from quality_check import (rule_freshness, rule_completeness, rule_unit_consistency,
                           rule_alias_coverage, rule_outlier, overall)


class TestQualityRules:
    """TDD: 质量门禁规则(数据资产评估清单的制度化, 反P1)"""

    def test_freshness_pass(self):
        r = rule_freshness(dt.date(2026, 10, 23), dt.date(2026, 10, 24), max_lag_days=2)
        assert r["status"] == "PASS" and r["metric"] == 1

    def test_freshness_fail_stale(self):
        r = rule_freshness(dt.date(2026, 10, 1), dt.date(2026, 10, 24))
        assert r["status"] == "FAIL"

    def test_freshness_fail_empty(self):
        assert rule_freshness(None, dt.date(2026, 10, 24))["status"] == "FAIL"

    def test_completeness_pass(self):
        assert rule_completeness(300, 10000)["status"] == "PASS"   # 3%<5%

    def test_completeness_fail(self):
        assert rule_completeness(600, 10000)["status"] == "FAIL"   # 6%>5%

    def test_unit_consistency(self):
        assert rule_unit_consistency(0)["status"] == "PASS"
        assert rule_unit_consistency(7)["status"] == "FAIL"

    def test_alias_coverage(self):
        assert rule_alias_coverage(480, 20)["status"] == "PASS"    # 96%
        assert rule_alias_coverage(400, 100)["status"] == "FAIL"   # 80%<90%

    def test_outlier(self):
        assert rule_outlier(5, 10000)["status"] == "PASS"
        assert rule_outlier(200, 10000)["status"] == "FAIL"

    def test_overall_gate(self):
        assert overall([{"status": "PASS"}, {"status": "PASS"}]) == "PASS"
        assert overall([{"status": "PASS"}, {"status": "FAIL"}]) == "FAIL"

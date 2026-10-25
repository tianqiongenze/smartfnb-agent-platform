import pytest
from app.guards import route_intent, numeric_guard, parse_proc_request

class TestIntentRouter:
    def test_diff_keywords(self):
        assert route_intent("今天7号店牛肉用量差异是多少") == "diff_agent"
        assert route_intent("查一下浪费情况") == "diff_agent"
        assert route_intent("哪些食材多用了") == "diff_agent"

    def test_menu_keywords(self):
        assert route_intent("帮我推荐几个招牌菜") == "menu_agent"
        assert route_intent("看看菜单") == "menu_agent"

    def test_smalltalk(self):
        assert route_intent("你好") == "smalltalk"
        assert route_intent("谢谢") == "smalltalk"

    def test_proc_parse(self):
        r = parse_proc_request("帮7号店采购50公斤鲈鱼")
        assert r["qty"] == 50.0 and r["ing_hint"] == "鲈鱼"
        assert parse_proc_request("帮我补货")["qty"] is None

    def test_proc_route(self):
        assert route_intent("帮7号店采购50公斤鲈鱼") == "procurement_agent"
        assert route_intent("看看待审批建议单") == "procurement_agent"

    def test_default_knowledge(self):
        assert route_intent("等保二级要多久测评一次") == "knowledge_agent"

class TestNumericGuard:
    """复刻'8公斤牛肉'演示事故: 答案数字必须能在工具输出中溯源"""

    def test_verified_number_passes(self):
        tools = ['{"theo_gram": 8700, "actual_gram": 12800, "diff_pct": 47.1}']
        v = numeric_guard("牛肉实际12800克, 理论8700克, 差异47.1%", tools)
        assert v["ok"] and v["confidence"] == "HIGH"

    def test_kg_gram_equivalence(self):
        tools = ['{"actual_gram": 12800}']
        v = numeric_guard("实际用量12.8公斤", tools)
        assert v["ok"]

    def test_fabricated_number_flagged(self):
        tools = ['{"actual_gram": 8200}']
        v = numeric_guard("实际需要36.5公斤牛肉", tools)
        assert not v["ok"]
        assert "36.5" in v["unverified"]
        assert v["confidence"] == "LOW"

    def test_no_tool_output_fails_closed(self):
        v = numeric_guard("牛肉需要8.2公斤", [])
        assert not v["ok"] and v["confidence"] == "LOW"

    def test_common_numbers_ignored(self):
        tools = ['{"diff_pct": 47.1}']
        v = numeric_guard("超过15%阈值, 共2条预警, 差异47.1%", tools)
        assert v["ok"]

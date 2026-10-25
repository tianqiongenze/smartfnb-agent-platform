import pytest
from app.direct import faq_cache_key, faq_hit, kg, direct_diff_answer, needs_llm_analysis


class FakeRedis:
    def __init__(self, data=None):
        self.data = data or {}
    def get(self, k):
        return self.data.get(k)


class TestFaqCache:
    def test_key_format(self):
        assert faq_cache_key(" 怎么降低浪费 ").startswith("fnb:qa:")

    def test_hit(self):
        import hashlib, json
        q = "怎么降低浪费"
        key = "fnb:qa:" + hashlib.md5(q.encode()).hexdigest()
        r = FakeRedis({key: json.dumps({"q": q, "a": "按BOM领料扫码"})})
        hit = faq_hit(r, q)
        assert hit and hit["answer"] == "按BOM领料扫码" and hit["cache_hit"]

    def test_miss_and_disabled(self):
        assert faq_hit(FakeRedis(), "不存在的问题") is None
        assert faq_hit(None, "怎么降低浪费") is None


class TestDirectAnswer:
    """工具直答: 数字全部来自工具结果(反幻觉的快路径)"""

    def test_kg_format(self):
        assert kg(9099) == "9.1kg"
        assert kg(500) == "500g"
        assert kg(None) == "-"

    def test_direct_answer_numbers_traced(self):
        tool = {"lines": [
            {"name_std": "鲈鱼03", "category": "海鲜", "theo_gram": 9099,
             "actual_gram": 2972, "diff_pct": -67.3},
            {"name_std": "五花肉", "category": "肉类", "theo_gram": 12504,
             "actual_gram": 5043, "diff_pct": -59.7},
        ]}
        out = direct_diff_answer(tool, 7, "2026-10-23")
        assert out["tool_traced"] and out["confidence"] == "HIGH"
        assert "9.1kg" in out["answer"] and "3.0kg" in out["answer"]
        assert "-67.3%" in out["answer"]
        assert "MCP工具get_diff" in out["answer"]

    def test_empty_lines_degraded(self):
        out = direct_diff_answer({"lines": []}, 7, "2026-10-23")
        assert out["confidence"] == "MEDIUM" and "无差异数据" in out["answer"]

    def test_needs_llm_analysis(self):
        assert needs_llm_analysis("为什么牛肉差异这么大")
        assert needs_llm_analysis("分析一下原因")
        assert not needs_llm_analysis("7号店今天的差异是多少")

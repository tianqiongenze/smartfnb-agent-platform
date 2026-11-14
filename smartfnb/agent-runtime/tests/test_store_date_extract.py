"""[OPT-D08/C4] 回归: 对话文本中的店号/日期必须覆盖页面默认值(修复前本文件红灯)"""
import pytest

from app.guards import extract_store_date


class TestStoreExtraction:
    def test_store_from_text_overrides_default(self):
        # 修复前: '2号店'被 guards.py:44 当'残留数字'清掉, 落到页面默认 storeId=7
        assert extract_store_date("2号店2026-10-23牛肉用量差异", 7, "2026-10-26")[0] == 2

    def test_store_matches_selector_value_unchanged(self):
        assert extract_store_date("7号店牛肉用量差异", 7, "2026-10-26")[0] == 7

    def test_qty_without_store_suffix_not_misread(self):
        # '采购50公斤' 无'号店'后缀, 不得把 50 当店号
        assert extract_store_date("采购50公斤鲈鱼", 7, "2026-10-26")[0] == 7

    def test_two_digit_store(self):
        assert extract_store_date("18号店差异", 7, "2026-10-26")[0] == 18


class TestDateExtraction:
    def test_iso_date_overrides_default(self):
        assert extract_store_date("2号店2026-10-23牛肉用量差异", 7, "2026-10-25")[1] == "2026-10-23"

    def test_cn_date(self):
        assert extract_store_date("7号店2026年10月23日的差异", 7, "2026-10-25")[1] == "2026-10-23"

    def test_invalid_date_keeps_default(self):
        s, d = extract_store_date("7号店2026-13-99差异", 7, "2026-10-25")
        assert (s, d) == (7, "2026-10-25")

    def test_no_match_keeps_defaults(self):
        s, d = extract_store_date("牛肉用量差异多少", 7, "2026-10-25")
        assert (s, d) == (7, "2026-10-25")

    def test_accepts_date_object_default(self):
        import datetime
        s, d = extract_store_date("牛肉差异", 7, datetime.date(2026, 10, 25))
        assert d == "2026-10-25"

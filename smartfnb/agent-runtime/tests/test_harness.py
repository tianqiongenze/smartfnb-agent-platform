import pytest
from app.harness import Budget, BudgetExceeded, SessionContext, run_eval, verify


class TestBudget:
    """R1 TDD: 预算控制"""

    def test_charge_within_budget(self):
        b = Budget(max_llm_calls=2, max_llm_tokens=100)
        b.charge_call(40); b.charge_call(50)
        assert b.llm_calls == 2 and b.llm_tokens == 90

    def test_calls_exhausted(self):
        b = Budget(max_llm_calls=1)
        b.charge_call(10)
        with pytest.raises(BudgetExceeded):
            b.charge_call(10)

    def test_tokens_exhausted(self):
        b = Budget(max_llm_calls=5, max_llm_tokens=100)
        b.charge_call(90)
        with pytest.raises(BudgetExceeded):
            b.charge_call(20)

    def test_consecutive_error_breaker(self):
        b = Budget(max_consecutive_errors=2)
        b.record_error()
        with pytest.raises(BudgetExceeded):
            b.record_error()

    def test_success_resets_errors(self):
        b = Budget(max_consecutive_errors=2)
        b.record_error(); b.record_success(); b.record_error()
        assert b.consecutive_errors == 1


class TestContext:
    def test_trim_keeps_latest(self):
        ctx = SessionContext(question="q", store_id=7, date="2026-10-23",
                             max_context_tokens=60)
        for i in range(10):
            ctx.add_history("user", f"消息{i}" * 10)
        assert len(ctx.history) <= 4          # 裁剪生效且保留最新

    def test_retrieved_never_dropped(self):
        ctx = SessionContext(question="q", store_id=7, date="d", max_context_tokens=50)
        ctx.add_retrieved('{"actual_gram": 8200}')
        assert ctx.retrieved                    # 溯源数据不裁剪

    def test_token_estimate(self):
        ctx = SessionContext(question="差异是多少", store_id=7, date="2026-10-23")
        assert ctx.token_estimate > 0


class TestVerify:
    def test_verified_answer(self):
        ctx = SessionContext(question="q", store_id=7, date="d")
        ctx.add_retrieved('{"theo_gram": 8700}')
        ans, conf = verify(ctx, "理论8700克")
        assert conf == "HIGH"

    def test_fabricated_answer_flagged(self):
        ctx = SessionContext(question="q", store_id=7, date="d")
        ctx.add_retrieved('{"theo_gram": 8700}')
        ans, conf = verify(ctx, "理论99999克")
        assert conf == "LOW" and "溯源校验" in ans


class TestEvalHarness:
    """评测回路: 100条评审集回归(意图准确率≥95%, 守卫通过率≥95%)"""

    def test_evalset_loaded(self):
        r = run_eval()
        assert r.total >= 100

    def test_intent_accuracy(self):
        r = run_eval()
        assert r.intent_acc >= 95.0, r.failures

    def test_guard_pass_rate(self):
        r = run_eval()
        assert r.guard_pass >= 95.0, r.failures

    def test_parse_pass_rate(self):
        r = run_eval()
        assert r.parse_pass >= 95.0, r.failures

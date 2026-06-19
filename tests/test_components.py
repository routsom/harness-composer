"""Unit tests for individual library components."""

import pytest

from harness_composer.library.context_strategies import (
    MinimalContextStrategy,
    CompressionContextStrategy,
)
from harness_composer.library.guardrails import (
    FinancialThresholdGuardrail,
    PiiRedactionGuardrail,
    IrreversibilityConfirmationGuardrail,
)
from harness_composer.library.guardrails.base import GuardrailOutcome
from harness_composer.library.tool_wrappers import WebSearchToolWrapper
from harness_composer.library.verification import (
    DatabaseWriteCheck,
    ExternalConfirmationCheck,
)
from harness_composer.library.verification.base import VerificationStatus


# ── Context strategies ───────────────────────────────────────────────────────

class TestMinimalContextStrategy:
    def _msgs(self, n: int):
        return [{"role": "system", "content": "sys"}] + [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"}
            for i in range(n)
        ]

    def test_keeps_system_prompt(self):
        strat = MinimalContextStrategy(window_size=2)
        window = strat.build(self._msgs(6))
        assert window.messages[0]["role"] == "system"

    def test_truncates_to_window_size(self):
        strat = MinimalContextStrategy(window_size=2)
        window = strat.build(self._msgs(10))
        non_sys = [m for m in window.messages if m["role"] != "system"]
        assert len(non_sys) <= 2

    def test_short_history_not_truncated(self):
        strat = MinimalContextStrategy(window_size=10)
        msgs = self._msgs(3)
        window = strat.build(msgs)
        assert len(window.messages) == len(msgs)


class TestCompressionContextStrategy:
    def _msgs(self, n: int):
        return [{"role": "system", "content": "sys"}] + [
            {"role": "user", "content": f"msg{i}"} for i in range(n)
        ]

    def test_no_compression_when_short(self):
        strat = CompressionContextStrategy(tail_size=10)
        msgs = self._msgs(5)
        window = strat.build(msgs)
        assert len(window.messages) == len(msgs)

    def test_summary_injected_when_long(self):
        strat = CompressionContextStrategy(tail_size=3)
        msgs = self._msgs(10)
        window = strat.build(msgs)
        summary_msgs = [m for m in window.messages if "CONTEXT SUMMARY" in str(m.get("content", ""))]
        assert len(summary_msgs) == 1

    def test_state_carries_summary(self):
        strat = CompressionContextStrategy(tail_size=3)
        msgs = self._msgs(10)
        window = strat.build(msgs)
        assert "summary" in window.state


# ── Financial threshold guardrail ────────────────────────────────────────────

class TestFinancialThresholdGuardrail:
    @pytest.fixture
    def g(self):
        return FinancialThresholdGuardrail(soft_limit=200, hard_limit=1000, currency="GBP")

    def test_allow_below_soft(self, g):
        r = g.check({"amount": 100, "currency": "GBP"})
        assert r.outcome == GuardrailOutcome.ALLOW

    def test_escalate_above_soft(self, g):
        r = g.check({"amount": 500, "currency": "GBP"})
        assert r.outcome == GuardrailOutcome.ESCALATE

    def test_block_above_hard(self, g):
        r = g.check({"amount": 1500, "currency": "GBP"})
        assert r.outcome == GuardrailOutcome.BLOCK

    def test_escalate_on_currency_mismatch(self, g):
        r = g.check({"amount": 50, "currency": "USD"})
        assert r.outcome == GuardrailOutcome.ESCALATE

    def test_allow_on_missing_amount(self, g):
        r = g.check({})
        assert r.outcome == GuardrailOutcome.ALLOW

    def test_invalid_limits_raise(self):
        with pytest.raises(ValueError):
            FinancialThresholdGuardrail(soft_limit=500, hard_limit=100)


# ── PII redaction guardrail ──────────────────────────────────────────────────

class TestPiiRedactionGuardrail:
    def test_no_pii_allows(self):
        g = PiiRedactionGuardrail()
        r = g.check({"message": "Hello, how are you?"})
        assert r.outcome == GuardrailOutcome.ALLOW

    def test_email_triggers_redact(self):
        g = PiiRedactionGuardrail()
        r = g.check({"message": "Contact test@example.com for details."})
        assert r.outcome == GuardrailOutcome.REDACT
        assert r.modified_payload is not None
        assert "test@example.com" not in r.modified_payload["message"]

    def test_block_mode(self):
        g = PiiRedactionGuardrail(block_on_detection=True)
        r = g.check({"message": "My SSN is 123-45-6789."})
        assert r.outcome == GuardrailOutcome.BLOCK


# ── Irreversibility confirmation guardrail ───────────────────────────────────

class TestIrreversibilityConfirmationGuardrail:
    def test_allow_when_confirmed(self):
        g = IrreversibilityConfirmationGuardrail()
        r = g.check({"confirmed": True, "action": "send_email"})
        assert r.outcome == GuardrailOutcome.ALLOW

    def test_escalate_when_not_confirmed(self):
        g = IrreversibilityConfirmationGuardrail(escalate_instead_of_block=True)
        r = g.check({"action": "send_email"})
        assert r.outcome == GuardrailOutcome.ESCALATE

    def test_block_when_not_confirmed_and_block_mode(self):
        g = IrreversibilityConfirmationGuardrail(escalate_instead_of_block=False)
        r = g.check({"action": "send_email"})
        assert r.outcome == GuardrailOutcome.BLOCK


# ── Tool wrappers ────────────────────────────────────────────────────────────

class TestWebSearchToolWrapper:
    def test_invoke_returns_results(self):
        tool = WebSearchToolWrapper()
        result = tool.invoke(query="test query")
        assert "results" in result
        assert isinstance(result["results"], list)

    def test_empty_query_raises(self):
        tool = WebSearchToolWrapper()
        with pytest.raises(ValueError):
            tool.invoke(query="")

    def test_metadata_kind(self):
        from harness_composer.library.base import ComponentKind
        tool = WebSearchToolWrapper()
        assert tool.metadata.kind == ComponentKind.TOOL_WRAPPER


# ── Verification checks ──────────────────────────────────────────────────────

class TestExternalConfirmationCheck:
    def test_verified_with_valid_reference(self):
        check = ExternalConfirmationCheck()
        r = check.verify({}, {"reference_id": "REF-123"})
        assert r.status == VerificationStatus.VERIFIED

    def test_uncertain_with_missing_reference(self):
        check = ExternalConfirmationCheck()
        r = check.verify({}, {})
        assert r.status == VerificationStatus.UNCERTAIN

    def test_failed_with_not_found(self):
        def always_none(ref: str):
            return None

        check = ExternalConfirmationCheck(lookup_fn=always_none)
        r = check.verify({}, {"reference_id": "REF-999"})
        assert r.status == VerificationStatus.FAILED


class TestDatabaseWriteCheck:
    def test_verified_when_record_found(self):
        check = DatabaseWriteCheck()
        r = check.verify({"table": "orders"}, {"id": "ord-42"})
        assert r.status == VerificationStatus.VERIFIED

    def test_uncertain_without_id(self):
        check = DatabaseWriteCheck()
        r = check.verify({"table": "orders"}, {})
        assert r.status == VerificationStatus.UNCERTAIN

    def test_failed_when_record_not_found(self):
        def always_none(record_id: str, table: str):
            return None

        check = DatabaseWriteCheck(read_fn=always_none)
        r = check.verify({"table": "orders"}, {"id": "ord-99"})
        assert r.status == VerificationStatus.FAILED

    def test_field_assertion_failure(self):
        def return_wrong(record_id: str, table: str):
            return {"id": record_id, "status": "PENDING"}

        check = DatabaseWriteCheck(
            read_fn=return_wrong,
            expected_fields={"status": "CONFIRMED"},
        )
        r = check.verify({"table": "orders"}, {"id": "ord-1"})
        assert r.status == VerificationStatus.FAILED

"""
Financial threshold guardrail.

Blocks or escalates any action whose monetary value exceeds a configurable
ceiling.  The payload is expected to contain an ``amount`` key (numeric)
and optionally a ``currency`` key.

Example payload
---------------
{"amount": 450.00, "currency": "GBP", "description": "Flights to Edinburgh"}
"""

from __future__ import annotations

from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.guardrails.base import (
    BaseGuardrail,
    GuardrailOutcome,
    GuardrailResult,
)


class FinancialThresholdGuardrail(BaseGuardrail):
    """
    Block or escalate transactions above *hard_limit*, escalate above
    *soft_limit*.

    Parameters
    ----------
    soft_limit:
        Amounts above this trigger ESCALATE (human review required).
    hard_limit:
        Amounts above this trigger BLOCK (absolute stop).
    currency:
        Expected currency code.  If the payload carries a different code,
        the check escalates for safety.
    """

    def __init__(
        self,
        soft_limit: float = 500.0,
        hard_limit: float = 2_000.0,
        currency: str = "GBP",
    ) -> None:
        if soft_limit >= hard_limit:
            raise ValueError("soft_limit must be less than hard_limit")
        self._soft_limit = soft_limit
        self._hard_limit = hard_limit
        self._currency = currency.upper()

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="guardrail_financial_threshold",
            kind=ComponentKind.GUARDRAIL,
            version="1.0.0",
            description=(
                f"Block transactions > {self._currency} {self._hard_limit}; "
                f"escalate > {self._currency} {self._soft_limit}."
            ),
            tags=frozenset({"financial", "transact", "payment"}),
        )

    def check(self, payload: dict[str, Any]) -> GuardrailResult:
        amount   = payload.get("amount")
        currency = str(payload.get("currency", self._currency)).upper()

        if amount is None:
            # No amount in payload — allow but note the absence.
            return GuardrailResult(
                outcome=GuardrailOutcome.ALLOW,
                reason="No 'amount' key in payload; check skipped.",
            )

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return GuardrailResult(
                outcome=GuardrailOutcome.ESCALATE,
                reason=f"Could not parse amount '{payload['amount']}' as a number.",
            )

        if currency != self._currency:
            return GuardrailResult(
                outcome=GuardrailOutcome.ESCALATE,
                reason=(
                    f"Currency mismatch: expected {self._currency}, got {currency}. "
                    "Escalating for human review."
                ),
            )

        if amount > self._hard_limit:
            return GuardrailResult(
                outcome=GuardrailOutcome.BLOCK,
                reason=(
                    f"Transaction amount {currency} {amount:.2f} exceeds the hard "
                    f"limit of {currency} {self._hard_limit:.2f}."
                ),
            )

        if amount > self._soft_limit:
            return GuardrailResult(
                outcome=GuardrailOutcome.ESCALATE,
                reason=(
                    f"Transaction amount {currency} {amount:.2f} exceeds the soft "
                    f"limit of {currency} {self._soft_limit:.2f}. "
                    "Routing to human reviewer."
                ),
            )

        return GuardrailResult(
            outcome=GuardrailOutcome.ALLOW,
            reason=f"Amount {currency} {amount:.2f} is within approved limits.",
        )

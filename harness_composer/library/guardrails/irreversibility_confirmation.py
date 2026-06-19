"""
Irreversibility confirmation guardrail.

For actions that cannot be undone (sending messages, publishing, deploying,
financial wire transfers), this guardrail requires explicit confirmation to
be present in the payload before allowing execution.

This prevents an agent from performing an irreversible action on the basis of
ambiguous or low-confidence instructions.
"""

from __future__ import annotations

from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.guardrails.base import (
    BaseGuardrail,
    GuardrailOutcome,
    GuardrailResult,
)


class IrreversibilityConfirmationGuardrail(BaseGuardrail):
    """
    Require an explicit confirmation token in the payload for irreversible actions.

    The expected token is configurable.  The framework adapter is responsible
    for obtaining confirmation from the user / orchestrator and injecting the
    token into the payload before calling the tool.

    Parameters
    ----------
    confirmation_key:
        Key to look for in the payload.
    expected_value:
        Value that constitutes a valid confirmation.
    escalate_instead_of_block:
        If True, absence of confirmation triggers ESCALATE (route to human)
        rather than BLOCK (hard stop).  Use ESCALATE when the action might be
        legitimate but the system wants a human sign-off rather than a silent
        block.
    """

    def __init__(
        self,
        confirmation_key: str = "confirmed",
        expected_value: Any = True,
        escalate_instead_of_block: bool = True,
    ) -> None:
        self._key   = confirmation_key
        self._value = expected_value
        self._escalate = escalate_instead_of_block

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="guardrail_irreversibility_confirmation",
            kind=ComponentKind.GUARDRAIL,
            version="1.0.0",
            description=(
                f"Require payload['{self._key}'] == {self._value!r} "
                "before allowing an irreversible action."
            ),
            tags=frozenset({"irreversible", "confirmation", "send", "deploy", "financial"}),
        )

    def check(self, payload: dict[str, Any]) -> GuardrailResult:
        value = payload.get(self._key)

        if value == self._value:
            return GuardrailResult(
                outcome=GuardrailOutcome.ALLOW,
                reason=f"Confirmation key '{self._key}' is present and valid.",
            )

        outcome = GuardrailOutcome.ESCALATE if self._escalate else GuardrailOutcome.BLOCK
        return GuardrailResult(
            outcome=outcome,
            reason=(
                f"Irreversible action requires payload['{self._key}'] == {self._value!r}. "
                f"Got: {value!r}. "
                + ("Escalating to human reviewer." if self._escalate else "Hard stop.")
            ),
        )

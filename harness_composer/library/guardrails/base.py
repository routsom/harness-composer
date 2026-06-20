"""Abstract base class for guardrails."""

from __future__ import annotations

from abc import abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from harness_composer.library.base import BaseComponent


class GuardrailOutcome(StrEnum):
    ALLOW   = "allow"    # Proceed normally.
    BLOCK   = "block"    # Hard stop — do not execute.
    ESCALATE= "escalate" # Pause and route to a human reviewer.
    REDACT  = "redact"   # Proceed, but with sensitive data removed.


class GuardrailResult(BaseModel):
    outcome: GuardrailOutcome
    reason: str
    # Optionally, a modified version of the payload (used by REDACT).
    modified_payload: dict[str, Any] | None = None

    model_config = ConfigDict(frozen=True)


class BaseGuardrail(BaseComponent):
    """
    A pre- or post-execution safety check.

    Guardrails are called by the Composition Engine before (and optionally
    after) each agent action.  They must never have side effects beyond
    returning a :class:`GuardrailResult`.
    """

    @abstractmethod
    def check(self, payload: dict[str, Any]) -> GuardrailResult:
        """
        Evaluate *payload* and return a :class:`GuardrailResult`.

        Parameters
        ----------
        payload:
            The action payload about to be executed (tool call arguments,
            message content, etc.).
        """

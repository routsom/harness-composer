"""Abstract base class for verification checks."""

from __future__ import annotations

from abc import abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from harness_composer.library.base import BaseComponent


class VerificationStatus(StrEnum):
    VERIFIED = "verified"   # The action provably had its intended effect.
    FAILED   = "failed"     # The action did not have the intended effect.
    UNCERTAIN= "uncertain"  # Could not determine — human review recommended.


class VerificationResult(BaseModel):
    status: VerificationStatus
    reason: str
    evidence: dict[str, Any] | None = None

    model_config = ConfigDict(frozen=True)


class BaseVerificationCheck(BaseComponent):
    """
    Confirms that an action actually had its intended effect.

    Verification checks are distinct from guardrails: guardrails fire
    *before* execution to decide whether to allow it; verification checks
    fire *after* execution to confirm it succeeded — independently of the
    agent's self-report.

    From the product gist:
    "checking an external booking system for confirmation, checking a
    database write actually persisted."
    """

    @abstractmethod
    def verify(
        self,
        action_payload: dict[str, Any],
        action_result: dict[str, Any],
    ) -> VerificationResult:
        """
        Verify that the action described by *action_payload* completed
        successfully, given the raw *action_result* returned by the tool.

        Parameters
        ----------
        action_payload:
            The original arguments passed to the tool.
        action_result:
            The dict returned by the tool wrapper's ``invoke`` method.
        """

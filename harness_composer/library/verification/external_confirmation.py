"""
External confirmation verification check.

Queries an external system to confirm a booking / order / transaction
actually completed, rather than trusting the agent's or the API's
self-reported success.

In production you would inject a real lookup client (airline confirmation
API, payment processor receipt endpoint, etc.).  The default uses a
pluggable callable so the component can be unit-tested offline.
"""

from __future__ import annotations

from typing import Any, Callable


def _stub_lookup(reference_id: str) -> dict[str, Any] | None:
    """
    Stub lookup — returns a fake confirmation for any non-empty reference_id.
    Replace with a real API call in production.
    """
    if reference_id:
        return {"status": "CONFIRMED", "reference": reference_id}
    return None


from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.verification.base import (
    BaseVerificationCheck,
    VerificationResult,
    VerificationStatus,
)


class ExternalConfirmationCheck(BaseVerificationCheck):
    """
    Verify a transaction by querying an external confirmation endpoint.

    Parameters
    ----------
    lookup_fn:
        Callable with signature ``(reference_id: str) -> dict | None``.
        Returns the confirmation record if found, or ``None`` if not.
    reference_key:
        Key in *action_result* that holds the reference / booking ID.
    confirmed_status_value:
        Value in the confirmation record's ``status`` field that means
        "confirmed".  Case-insensitive comparison.
    """

    def __init__(
        self,
        lookup_fn: Callable[[str], dict[str, Any] | None] | None = None,
        reference_key: str = "reference_id",
        confirmed_status_value: str = "CONFIRMED",
    ) -> None:
        self._lookup_fn = lookup_fn or _stub_lookup
        self._reference_key = reference_key
        self._confirmed_value = confirmed_status_value.upper()

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="verification_external_confirmation",
            kind=ComponentKind.VERIFICATION_CHECK,
            version="1.0.0",
            description=(
                "Query an external system to verify a transaction completed, "
                "using the reference ID returned by the tool."
            ),
            tags=frozenset({"transact", "booking", "financial", "external_api"}),
        )

    def verify(
        self,
        action_payload: dict[str, Any],
        action_result: dict[str, Any],
    ) -> VerificationResult:
        reference_id = action_result.get(self._reference_key)

        if not reference_id:
            return VerificationResult(
                status=VerificationStatus.UNCERTAIN,
                reason=(
                    f"No '{self._reference_key}' found in action result. "
                    "Cannot confirm externally."
                ),
                evidence=action_result,
            )

        record = self._lookup_fn(str(reference_id))

        if record is None:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                reason=f"External lookup returned no record for reference '{reference_id}'.",
                evidence={"reference_id": reference_id},
            )

        status_val = str(record.get("status", "")).upper()
        if status_val == self._confirmed_value:
            return VerificationResult(
                status=VerificationStatus.VERIFIED,
                reason=f"External system confirmed reference '{reference_id}' as {status_val}.",
                evidence=record,
            )

        return VerificationResult(
            status=VerificationStatus.FAILED,
            reason=(
                f"External system returned status '{status_val}' for reference "
                f"'{reference_id}'; expected '{self._confirmed_value}'."
            ),
            evidence=record,
        )

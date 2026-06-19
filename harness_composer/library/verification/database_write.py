"""
Database write verification check.

After a write operation, re-reads the record from the database and asserts
that at least one expected key-value pair is present.  This confirms the
write actually persisted, rather than relying on the agent's report that
it succeeded.

In production you would inject a real DB client.  The default uses a
pluggable callable for offline / unit-test usage.
"""

from __future__ import annotations

from typing import Any, Callable


def _stub_read(record_id: str, table: str) -> dict[str, Any] | None:
    """Stub reader — returns a fake record for any non-empty ID."""
    if record_id:
        return {"id": record_id, "table": table, "_stub": True}
    return None


from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.verification.base import (
    BaseVerificationCheck,
    VerificationResult,
    VerificationStatus,
)


class DatabaseWriteCheck(BaseVerificationCheck):
    """
    Verify a DB write by re-reading the record and asserting expected fields.

    Parameters
    ----------
    read_fn:
        Callable with signature ``(record_id: str, table: str) -> dict | None``.
    record_id_key:
        Key in *action_result* that holds the written record's ID.
    table_key:
        Key in *action_payload* that specifies the target table / collection.
    expected_fields:
        Dict of ``{field: value}`` pairs that must be present in the re-read
        record.  An empty dict skips field assertions (existence check only).
    """

    def __init__(
        self,
        read_fn: Callable[[str, str], dict[str, Any] | None] | None = None,
        record_id_key: str = "id",
        table_key: str = "table",
        expected_fields: dict[str, Any] | None = None,
    ) -> None:
        self._read_fn = read_fn or _stub_read
        self._record_id_key = record_id_key
        self._table_key = table_key
        self._expected_fields: dict[str, Any] = expected_fields or {}

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="verification_database_write",
            kind=ComponentKind.VERIFICATION_CHECK,
            version="1.0.0",
            description=(
                "Re-read a record from the DB after a write and assert expected fields "
                "are present, confirming the write persisted."
            ),
            tags=frozenset({"write", "database_write", "database"}),
        )

    def verify(
        self,
        action_payload: dict[str, Any],
        action_result: dict[str, Any],
    ) -> VerificationResult:
        record_id = action_result.get(self._record_id_key)
        table     = action_payload.get(self._table_key, "unknown")

        if not record_id:
            return VerificationResult(
                status=VerificationStatus.UNCERTAIN,
                reason=(
                    f"No '{self._record_id_key}' in action_result. "
                    "Cannot re-read record to verify write."
                ),
            )

        record = self._read_fn(str(record_id), str(table))

        if record is None:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                reason=f"Record '{record_id}' not found in '{table}' after write.",
                evidence={"record_id": record_id, "table": table},
            )

        # Check expected fields.
        failures: list[str] = []
        for field, expected in self._expected_fields.items():
            actual = record.get(field)
            if actual != expected:
                failures.append(f"{field}: expected {expected!r}, got {actual!r}")

        if failures:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                reason="Record found but field assertions failed: " + "; ".join(failures),
                evidence=record,
            )

        return VerificationResult(
            status=VerificationStatus.VERIFIED,
            reason=f"Record '{record_id}' found in '{table}' with all expected fields.",
            evidence=record,
        )

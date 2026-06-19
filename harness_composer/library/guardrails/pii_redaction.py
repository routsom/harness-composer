"""
PII redaction guardrail.

Scans a payload for common PII patterns and either blocks the action or
returns a redacted copy, depending on configuration.

Detected patterns (regex-based, no external dependencies)
----------------------------------------------------------
- Email addresses
- UK/US phone numbers
- UK National Insurance numbers
- US Social Security Numbers
- UK postcodes
- Credit card numbers (Luhn-naive: 13-19 consecutive digits)
"""

from __future__ import annotations

import json
import re
from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.guardrails.base import (
    BaseGuardrail,
    GuardrailOutcome,
    GuardrailResult,
)

_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email",    re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("phone_uk", re.compile(r"\b(?:0|\+44)\s?[\d\s\-]{9,13}\b")),
    ("phone_us", re.compile(r"\b(?:\+1[\s\-]?)?\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{4}\b")),
    ("ni_number",re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", re.I)),
    ("ssn",      re.compile(r"\b\d{3}[-\s]\d{2}[-\s]\d{4}\b")),
    ("uk_post",  re.compile(r"\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b", re.I)),
    ("card",     re.compile(r"\b(?:\d[\s\-]?){13,19}\b")),
]

_REDACT_PLACEHOLDER = "[REDACTED]"


def _redact_string(text: str) -> tuple[str, list[str]]:
    """Replace PII in *text* with ``[REDACTED]``.  Returns (redacted, detected_types)."""
    detected: list[str] = []
    for label, pattern in _PII_PATTERNS:
        new_text, n = pattern.subn(_REDACT_PLACEHOLDER, text)
        if n:
            text = new_text
            detected.append(label)
    return text, detected


def _redact_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Recursively redact all string values in a dict payload."""
    result: dict[str, Any] = {}
    all_detected: list[str] = []
    for k, v in payload.items():
        if isinstance(v, str):
            cleaned, detected = _redact_string(v)
            result[k] = cleaned
            all_detected.extend(detected)
        elif isinstance(v, dict):
            cleaned_dict, detected = _redact_payload(v)
            result[k] = cleaned_dict
            all_detected.extend(detected)
        else:
            result[k] = v
    return result, all_detected


class PiiRedactionGuardrail(BaseGuardrail):
    """
    Scan payload strings for PII and redact them before execution.

    Parameters
    ----------
    block_on_detection:
        If True, return BLOCK instead of REDACT when PII is found.
        Use this for tasks where the payload should never contain PII at all
        (e.g. a logging pipeline).
    """

    def __init__(self, block_on_detection: bool = False) -> None:
        self._block = block_on_detection

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="guardrail_pii_redaction",
            kind=ComponentKind.GUARDRAIL,
            version="1.0.0",
            description=(
                "Scan payload for common PII patterns and redact or block. "
                "Detects emails, phone numbers, NI numbers, SSNs, postcodes, card numbers."
            ),
            tags=frozenset({"pii", "privacy", "redact", "compliance"}),
        )

    def check(self, payload: dict[str, Any]) -> GuardrailResult:
        redacted, detected = _redact_payload(payload)

        if not detected:
            return GuardrailResult(
                outcome=GuardrailOutcome.ALLOW,
                reason="No PII detected in payload.",
            )

        types = ", ".join(sorted(set(detected)))

        if self._block:
            return GuardrailResult(
                outcome=GuardrailOutcome.BLOCK,
                reason=f"PII detected ({types}) and block_on_detection is enabled.",
            )

        return GuardrailResult(
            outcome=GuardrailOutcome.REDACT,
            reason=f"PII detected and redacted: {types}.",
            modified_payload=redacted,
        )

"""
Rules-based Task Classifier.

Implements the MVP classifier: explicit keyword / pattern matching that is
fully auditable without requiring an LLM call.  Each signal that fires is
recorded in ``TaskProfile.matched_signals`` so that the classification is
always explainable.

Design rationale (from the product gist)
-----------------------------------------
"Start with a rules-based classifier (explicit logic: does the task
description contain payment-related language, does it reference an external
irreversible action) before attempting an LLM-based classifier. Rules-based
is slower to generalise but far easier to audit and trust early on — and
auditability is the entire point of this product."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Pattern

from harness_composer.classifier.base import BaseClassifier
from harness_composer.classifier.task_profile import (
    ActionType,
    RiskLevel,
    TaskProfile,
)

_VERSION = "rules-based-1.0"

# ---------------------------------------------------------------------------
# Signal definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Signal:
    """A named, regex-based detection signal."""

    name: str
    pattern: Pattern[str]
    description: str


def _sig(name: str, pattern: str, description: str) -> Signal:
    return Signal(name=name, pattern=re.compile(pattern, re.IGNORECASE), description=description)


# Financial / transactional signals
FINANCIAL_SIGNALS: list[Signal] = [
    _sig("payment",        r"\bpay(ment|ing|s)?\b",           "payment language"),
    _sig("book_ticket",    r"\bbook(ing|ed|s)?\b.{0,30}\b(flight|ticket|train|hotel)\b",
                                                                 "booking with likely payment"),
    _sig("purchase",       r"\bpurchase|buy|checkout|order\b", "purchase language"),
    _sig("invoice",        r"\binvoice|billing|charge|refund\b","invoice / billing language"),
    _sig("transfer",       r"\btransfer.{0,20}\b(money|funds|usd|gbp|eur)\b",
                                                                 "financial transfer language"),
]

# PII signals
PII_SIGNALS: list[Signal] = [
    _sig("pii_name",    r"\bfull name|first name|last name|surname\b", "name PII"),
    _sig("pii_email",   r"\bemail address(es)?\b",                      "email PII"),
    _sig("pii_phone",   r"\bphone number|mobile number\b",              "phone PII"),
    _sig("pii_address", r"\bhome address|postal address|street address\b", "address PII"),
    _sig("pii_ssn",     r"\bssn|national insurance|passport number\b",  "government ID PII"),
    _sig("pii_health",  r"\bmedical record|health data|diagnosis\b",    "health PII"),
]

# Irreversibility signals
IRREVERSIBLE_SIGNALS: list[Signal] = [
    _sig("delete",      r"\bdelete|destroy|drop table|truncate\b",       "destructive data operation"),
    _sig("send_email",  r"\bsend.{0,10}\bemail\b",                       "outbound email"),
    _sig("send_message",r"\bsend.{0,10}\b(message|sms|text|slack|tweet)\b","outbound message"),
    _sig("publish",     r"\bpublish|deploy|go live|release\b",           "publish / deploy action"),
    _sig("wire",        r"\bwire.{0,10}\b(money|funds)\b",               "wire transfer"),
]

# External system signals
EXTERNAL_SIGNALS: list[Signal] = [
    _sig("flight_api",   r"\bflight|airline|amadeus\b",   "flight_search_api"),
    _sig("hotel_api",    r"\bhotel|accommodation\b",       "hotel_search_api"),
    _sig("payment_api",  r"\bstripe|paypal|pay(ment)?\b",  "payment_processor"),
    _sig("crm_api",      r"\bcrm|salesforce|hubspot\b",    "crm_api"),
    _sig("calendar_api", r"\bcalendar|schedule|meeting\b", "calendar_api"),
    _sig("email_api",    r"\bemail|smtp|mailgun|sendgrid\b","email_api"),
    _sig("db_write",     r"\binsert|update|upsert|write to\b","database_write"),
    _sig("search_api",   r"\bsearch|google|bing\b",         "web_search_api"),
]

# Action-type signals
READ_SIGNALS: list[Signal] = [
    _sig("summarise",   r"\bsummarise?|summarize|explain|describe|what is\b", "read/summarise"),
    _sig("lookup",      r"\blook up|find out|retrieve|fetch|get\b",            "read/lookup"),
    _sig("analyse",     r"\banalyse?|analyze|review|audit\b",                  "read/analyse"),
]

WRITE_SIGNALS: list[Signal] = [
    _sig("create_record", r"\bcreate|add|insert|new record\b",      "write/create"),
    _sig("update_record", r"\bupdate|modify|edit|change\b",          "write/update"),
    _sig("save_file",     r"\bsave|write to file|export\b",          "write/file"),
]

COMMUNICATE_SIGNALS: list[Signal] = [
    _sig("send_comm",  r"\bsend|notify|alert|ping|message\b",        "communicate/send"),
    _sig("post_social",r"\bpost to|tweet|linkedin\b",                 "communicate/social"),
]

ORCHESTRATE_SIGNALS: list[Signal] = [
    _sig("spawn_agent", r"\bspawn|delegate|hand off|sub-?agent\b",   "orchestrate/spawn"),
    _sig("pipeline",    r"\bpipeline|workflow|chain of\b",            "orchestrate/pipeline"),
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _matched(signals: list[Signal], text: str) -> list[str]:
    """Return the ``name`` of every signal whose pattern matches *text*."""
    return [s.name for s in signals if s.pattern.search(text)]


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

class RulesBasedClassifier(BaseClassifier):
    """
    Fully deterministic, auditable classifier.

    All classification logic is expressed as named regex signals.  Each signal
    that fires is captured in :attr:`TaskProfile.matched_signals` so that
    every decision can be reconstructed from the log.
    """

    @property
    def version(self) -> str:
        return _VERSION

    def classify(
        self,
        task: str,
        *,
        agent_id: str | None = None,
        agent_track_record: float | None = None,
    ) -> TaskProfile:
        matched: list[str] = []

        # ── Detect signals ───────────────────────────────────────────────────
        financial_hits   = _matched(FINANCIAL_SIGNALS,    task)
        pii_hits         = _matched(PII_SIGNALS,          task)
        irreversible_hits= _matched(IRREVERSIBLE_SIGNALS, task)
        external_hits    = _matched(EXTERNAL_SIGNALS,     task)
        read_hits        = _matched(READ_SIGNALS,         task)
        write_hits       = _matched(WRITE_SIGNALS,        task)
        communicate_hits = _matched(COMMUNICATE_SIGNALS,  task)
        orchestrate_hits = _matched(ORCHESTRATE_SIGNALS,  task)

        matched.extend(financial_hits + pii_hits + irreversible_hits +
                       external_hits + read_hits + write_hits +
                       communicate_hits + orchestrate_hits)

        # ── Derive action type (priority order) ──────────────────────────────
        if orchestrate_hits:
            action_type = ActionType.ORCHESTRATE
        elif financial_hits:
            action_type = ActionType.TRANSACT
        elif communicate_hits:
            action_type = ActionType.COMMUNICATE
        elif write_hits:
            action_type = ActionType.WRITE
        elif external_hits:
            action_type = ActionType.EXTERNAL_API
        else:
            action_type = ActionType.READ

        # ── Derive reversibility ─────────────────────────────────────────────
        is_reversible = len(irreversible_hits) == 0 and len(financial_hits) == 0
        # Bookings have a partial reversibility window (24 h default)
        reversibility_window: int | None = None
        if financial_hits and not irreversible_hits:
            reversibility_window = 86_400  # 24 h

        # ── Derive data sensitivity ──────────────────────────────────────────
        touches_pii        = bool(pii_hits)
        touches_financial  = bool(financial_hits)

        # ── Derive external systems ──────────────────────────────────────────
        # Map signal names → canonical system ids
        _signal_to_system: dict[str, str] = {
            "flight_api":   "flight_search_api",
            "hotel_api":    "hotel_search_api",
            "payment_api":  "payment_processor",
            "crm_api":      "crm_api",
            "calendar_api": "calendar_api",
            "email_api":    "email_api",
            "db_write":     "database_write",
            "search_api":   "web_search_api",
        }
        required_systems: set[str] = {
            _signal_to_system[h] for h in external_hits if h in _signal_to_system
        }
        # Financial tasks always need a payment processor
        if financial_hits:
            required_systems.add("payment_processor")

        # ── Derive risk level ────────────────────────────────────────────────
        risk_score = 0
        if touches_financial:
            risk_score += 3
        if not is_reversible:
            risk_score += 2
        if touches_pii:
            risk_score += 2
        if action_type == ActionType.ORCHESTRATE:
            risk_score += 1
        if action_type in {ActionType.WRITE, ActionType.EXTERNAL_API}:
            risk_score += 1
        if len(required_systems) > 2:
            risk_score += 1

        if risk_score >= 5:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 3:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 1:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # ── Human approval requirement ───────────────────────────────────────
        # Require approval for CRITICAL risk, or when agent track record is poor.
        requires_human_approval = (
            risk_level == RiskLevel.CRITICAL
            or (agent_track_record is not None and agent_track_record < 0.7)
        )

        # ── Confidence threshold ─────────────────────────────────────────────
        # Higher risk → higher required confidence.
        threshold_map = {
            RiskLevel.LOW: 0.7,
            RiskLevel.MEDIUM: 0.85,
            RiskLevel.HIGH: 0.9,
            RiskLevel.CRITICAL: 0.95,
        }
        confidence_threshold = threshold_map[risk_level]

        return TaskProfile(
            action_type=action_type,
            risk_level=risk_level,
            is_reversible=is_reversible,
            reversibility_window_seconds=reversibility_window,
            touches_pii=touches_pii,
            touches_financial_data=touches_financial,
            required_external_systems=frozenset(required_systems),
            requires_human_approval=requires_human_approval,
            confidence_threshold=confidence_threshold,
            classifier_version=self.version,
            matched_signals=matched,
        )

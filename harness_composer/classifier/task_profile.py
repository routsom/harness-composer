"""Data model produced by the Task Classifier."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ActionType(StrEnum):
    """High-level category of the action a task intends to perform."""

    READ = "read"             # Retrieving or summarising information; no side-effects.
    WRITE = "write"           # Creating or mutating structured data (DB rows, files).
    COMMUNICATE = "communicate"  # Sending messages, emails, notifications.
    TRANSACT = "transact"     # Financial operations: payments, bookings with payment.
    EXTERNAL_API = "external_api"  # Calling an external third-party service.
    ORCHESTRATE = "orchestrate"   # Spinning up sub-agents or chaining multiple tasks.


class RiskLevel(StrEnum):
    """Composite risk level assigned by the classifier."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskProfile(BaseModel):
    """
    Structured output of the Task Classifier.

    Every field is derived by the classifier from the raw task description (and
    optional agent metadata).  The Composition Engine consumes this profile to
    select components from the library.
    """

    # ── Core classification ──────────────────────────────────────────────────

    action_type: ActionType = Field(
        description="Dominant action type of the task."
    )
    risk_level: RiskLevel = Field(
        description="Overall risk level, factoring in reversibility, data sensitivity, "
                    "and financial exposure.",
    )

    # ── Reversibility ────────────────────────────────────────────────────────

    is_reversible: bool = Field(
        description="True when the action can be undone without data loss or financial cost.",
    )
    reversibility_window_seconds: int | None = Field(
        default=None,
        description="If partially reversible, the window in seconds during which reversal "
                    "is possible (e.g. 86400 for 24 h cancellation policy).",
    )

    # ── Data sensitivity ─────────────────────────────────────────────────────

    touches_pii: bool = Field(
        default=False,
        description="True if the task is likely to read or write personally identifiable "
                    "information.",
    )
    touches_financial_data: bool = Field(
        default=False,
        description="True if the task involves payment, banking, or financial records.",
    )

    # ── External systems ─────────────────────────────────────────────────────

    required_external_systems: frozenset[str] = Field(
        default_factory=frozenset,
        description="Identifiers of external systems the task is expected to call "
                    "(e.g. 'payment_processor', 'flight_search_api').",
    )

    # ── Confidence / autonomy ────────────────────────────────────────────────

    requires_human_approval: bool = Field(
        default=False,
        description="True when the classifier determines the task must not proceed "
                    "without an explicit human sign-off.",
    )
    confidence_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Minimum model confidence required before the task executes "
                    "without escalation.",
    )

    # ── Classifier metadata ──────────────────────────────────────────────────

    classifier_version: str = Field(
        default="unknown",
        description="Version string of the classifier that produced this profile, "
                    "enabling audit trails.",
    )
    matched_signals: list[str] = Field(
        default_factory=list,
        description="Human-readable list of signals (keywords / patterns) that drove "
                    "the classification, satisfying explainability requirements.",
    )

    model_config = ConfigDict(frozen=True)

"""Shared base types for all library components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class ComponentKind(StrEnum):
    TOOL_WRAPPER       = "tool_wrapper"
    CONTEXT_STRATEGY   = "context_strategy"
    GUARDRAIL          = "guardrail"
    VERIFICATION_CHECK = "verification_check"


class ComponentMetadata(BaseModel):
    """
    Descriptive metadata attached to every library component.

    This is what the Composition Engine indexes when selecting components.
    """

    id: str
    kind: ComponentKind
    version: str
    description: str
    # Tags used by the composition engine for matching (e.g. "financial", "pii").
    tags: frozenset[str] = frozenset()

    model_config = ConfigDict(frozen=True)


class BaseComponent(ABC):
    """Root ABC for all harness components."""

    @property
    @abstractmethod
    def metadata(self) -> ComponentMetadata:
        """Return this component's immutable metadata."""

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict (used by framework adapters)."""
        return self.metadata.model_dump()

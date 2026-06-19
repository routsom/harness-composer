"""Abstract base for context window management strategies."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from harness_composer.library.base import BaseComponent


class ContextWindow(BaseModel):
    """The managed context handed to the LLM for a given turn."""

    messages: list[dict[str, Any]] = Field(default_factory=list)
    # Any metadata the strategy wants to persist across turns (e.g. a summary).
    state: dict[str, Any] = Field(default_factory=dict)
    token_budget: int | None = None


class BaseContextStrategy(BaseComponent):
    """
    A context strategy controls what the agent sees in its context window.

    Different tasks need radically different strategies:
    - A single-step lookup needs minimal context.
    - A long multi-step task needs compression and checkpointing so the
      window does not overflow and important state is not silently dropped.
    """

    @abstractmethod
    def build(
        self,
        messages: list[dict[str, Any]],
        *,
        token_budget: int | None = None,
        state: dict[str, Any] | None = None,
    ) -> ContextWindow:
        """
        Take a raw message list and return a managed :class:`ContextWindow`.

        Parameters
        ----------
        messages:
            Full conversation history up to this point.
        token_budget:
            Maximum tokens the strategy may use.  ``None`` means no limit.
        state:
            Persisted state from the previous turn (e.g. a running summary).
        """

"""
Minimal context strategy.

Best for: short, single-step, low-stakes tasks (e.g. "Summarise this document").

Behaviour
---------
Passes only the last N messages (default: last 4, i.e. ≈ 2 turns) to the model.
The system prompt is always preserved.  Everything else is dropped.

This is deliberately conservative — for tasks where prior history is not needed,
sending it only wastes tokens and risks leaking irrelevant information into the
model's reasoning.
"""

from __future__ import annotations

from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.context_strategies.base import BaseContextStrategy, ContextWindow


class MinimalContextStrategy(BaseContextStrategy):
    """
    Keep only the system prompt + the last *window_size* messages.

    Parameters
    ----------
    window_size:
        Number of most-recent messages to retain (not counting the system prompt).
    """

    def __init__(self, window_size: int = 4) -> None:
        if window_size < 1:
            raise ValueError("window_size must be >= 1")
        self._window_size = window_size

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="context_minimal",
            kind=ComponentKind.CONTEXT_STRATEGY,
            version="1.0.0",
            description=(
                f"Retain system prompt + last {self._window_size} messages. "
                "Suitable for short, single-step tasks."
            ),
            tags=frozenset({"read", "low_risk", "short_task"}),
        )

    def build(
        self,
        messages: list[dict[str, Any]],
        *,
        token_budget: int | None = None,
        state: dict[str, Any] | None = None,
    ) -> ContextWindow:
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system  = [m for m in messages if m.get("role") != "system"]
        recent      = non_system[-self._window_size :]
        return ContextWindow(
            messages=system_msgs + recent,
            state=state or {},
            token_budget=token_budget,
        )

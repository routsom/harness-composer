"""
Compression + checkpointing context strategy.

Best for: multi-step tasks with non-trivial history (e.g. booking flows,
long-running pipelines).

Behaviour
---------
1. Always keep the system prompt.
2. Keep the last *tail_size* messages verbatim (the "hot" window).
3. Everything older than the tail is replaced by a running summary stored in
   ``ContextWindow.state["summary"]``.  In production the summarisation step
   would call the LLM; here we provide a pluggable ``summarise_fn`` so the
   component can be unit-tested without a live model.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.context_strategies.base import BaseContextStrategy, ContextWindow


def _default_summarise(messages: list[dict[str, Any]]) -> str:
    """Naïve stub: concatenates role + first 80 chars of content."""
    parts = []
    for m in messages:
        role    = m.get("role", "?")
        content = str(m.get("content", ""))[:80]
        parts.append(f"[{role}] {content}")
    return " | ".join(parts)


class CompressionContextStrategy(BaseContextStrategy):
    """
    Keep a running summary of old messages + the last *tail_size* verbatim.

    Parameters
    ----------
    tail_size:
        Number of most-recent non-system messages to keep verbatim.
    summarise_fn:
        Callable that takes a list of messages and returns a summary string.
        Defaults to a simple concatenation stub — replace with an LLM call
        in production.
    """

    def __init__(
        self,
        tail_size: int = 10,
        summarise_fn: Callable[[list[dict[str, Any]]], str] | None = None,
    ) -> None:
        if tail_size < 1:
            raise ValueError("tail_size must be >= 1")
        self._tail_size = tail_size
        self._summarise = summarise_fn or _default_summarise

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="context_compression",
            kind=ComponentKind.CONTEXT_STRATEGY,
            version="1.0.0",
            description=(
                f"Running summary of old messages + last {self._tail_size} verbatim. "
                "Suitable for multi-step tasks with long histories."
            ),
            tags=frozenset({"multi_step", "long_task", "financial", "transact"}),
        )

    def build(
        self,
        messages: list[dict[str, Any]],
        *,
        token_budget: int | None = None,
        state: dict[str, Any] | None = None,
    ) -> ContextWindow:
        state = state or {}
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system  = [m for m in messages if m.get("role") != "system"]

        if len(non_system) <= self._tail_size:
            # History fits in the tail — no compression needed.
            return ContextWindow(
                messages=system_msgs + non_system,
                state=state,
                token_budget=token_budget,
            )

        tail       = non_system[-self._tail_size :]
        to_compress= non_system[: -self._tail_size]

        # Append new messages to any existing summary.
        prior_summary = state.get("summary", "")
        new_summary   = self._summarise(to_compress)
        summary       = f"{prior_summary} {new_summary}".strip() if prior_summary else new_summary

        summary_msg: dict[str, Any] = {
            "role": "system",
            "content": f"[CONTEXT SUMMARY — earlier conversation]\n{summary}",
        }

        return ContextWindow(
            messages=system_msgs + [summary_msg] + tail,
            state={**state, "summary": summary},
            token_budget=token_budget,
        )

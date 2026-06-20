"""
Web Search tool wrapper — read-only, no side effects.

In production you would inject a real search client (SerpAPI, Tavily, etc.).
The default implementation stubs the call so the component can be unit-tested
without network access.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.tool_wrappers.base import BaseToolWrapper, ToolPermission


def _stub_search(query: str, max_results: int) -> list[dict[str, str]]:
    """Stub backend — replaced by a real client in production."""
    return [
        {"title": f"Result for '{query}'", "url": "https://example.com", "snippet": "…"},
    ]


class WebSearchToolWrapper(BaseToolWrapper):
    """
    Read-only web search.  Requires no special permissions beyond READ_ONLY.

    Parameters
    ----------
    search_fn:
        Callable with signature ``(query: str, max_results: int) -> list[dict]``.
        Defaults to a no-op stub for offline / test usage.
    max_results:
        Maximum number of results to return per query.
    """

    def __init__(
        self,
        search_fn: Callable[[str, int], list[dict[str, str]]] | None = None,
        max_results: int = 5,
    ) -> None:
        self._search_fn = search_fn or _stub_search
        self._max_results = max_results

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="web_search",
            kind=ComponentKind.TOOL_WRAPPER,
            version="1.0.0",
            description="Read-only web search.  Returns a ranked list of results.",
            tags=frozenset({"read", "search", "web_search_api"}),
        )

    @property
    def required_permissions(self) -> frozenset[ToolPermission]:
        return frozenset({ToolPermission.READ_ONLY})

    def invoke(self, *, query: str, max_results: int | None = None) -> dict[str, Any]:  # type: ignore[override]
        if not query or not query.strip():
            raise ValueError("'query' must be a non-empty string.")
        results = self._search_fn(query, max_results or self._max_results)
        return {"query": query, "results": results}

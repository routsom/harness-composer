"""
HTTP Request tool wrapper — generic, permissioned HTTP client.

Supports allow-listing domains so that an agent cannot make arbitrary
outbound requests beyond what the task profile justifies.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from harness_composer.library.base import ComponentKind, ComponentMetadata
from harness_composer.library.tool_wrappers.base import BaseToolWrapper, ToolPermission


class HttpRequestToolWrapper(BaseToolWrapper):
    """
    Generic HTTP tool with domain allow-listing.

    Parameters
    ----------
    allowed_domains:
        If non-empty, requests to any domain not in this set will be rejected
        before hitting the network.  Pass an empty set to allow all domains
        (not recommended for production).
    allow_mutations:
        If False (default) only GET requests are permitted.  Set to True
        to enable POST/PUT/PATCH/DELETE — and add the WRITE permission.
    timeout_seconds:
        Network timeout for each request.
    """

    def __init__(
        self,
        allowed_domains: set[str] | None = None,
        allow_mutations: bool = False,
        timeout_seconds: int = 10,
    ) -> None:
        self._allowed_domains: set[str] = allowed_domains or set()
        self._allow_mutations = allow_mutations
        self._timeout = timeout_seconds

    @property
    def metadata(self) -> ComponentMetadata:
        return ComponentMetadata(
            id="http_request",
            kind=ComponentKind.TOOL_WRAPPER,
            version="1.0.0",
            description=(
                "Generic HTTP client with domain allow-listing and optional "
                "mutation support."
            ),
            tags=frozenset(
                {"external_api", "http", "read" if not self._allow_mutations else "write"}
            ),
        )

    @property
    def required_permissions(self) -> frozenset[ToolPermission]:
        perms = {ToolPermission.READ_ONLY}
        if self._allow_mutations:
            perms.add(ToolPermission.WRITE)
        return frozenset(perms)

    def invoke(  # type: ignore[override]
        self,
        *,
        url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        method = method.upper()

        if not self._allow_mutations and method != "GET":
            raise PermissionError(
                f"This tool wrapper is configured read-only; {method} is not permitted."
            )

        if self._allowed_domains:
            from urllib.parse import urlparse
            domain = urlparse(url).hostname or ""
            if not any(domain == d or domain.endswith(f".{d}") for d in self._allowed_domains):
                raise PermissionError(
                    f"Domain '{domain}' is not in the allowed-domain list for this tool."
                )

        req_headers = {"Content-Type": "application/json", **(headers or {})}
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode()
                try:
                    payload = json.loads(raw)
                except json.JSONDecodeError:
                    payload = raw
                return {"status_code": resp.status, "body": payload}
        except urllib.error.HTTPError as exc:
            return {"status_code": exc.code, "error": str(exc)}
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Request to {url} failed: {exc.reason}") from exc

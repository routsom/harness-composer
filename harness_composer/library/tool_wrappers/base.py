"""Base class and permission model for tool wrappers."""

from __future__ import annotations

from abc import abstractmethod
from enum import StrEnum
from typing import Any

from harness_composer.library.base import BaseComponent


class ToolPermission(StrEnum):
    """
    Permission flags that gate what a tool wrapper is allowed to do.

    The Composition Engine only grants permissions that are justified by the
    task profile — the principle of least privilege.
    """
    READ_ONLY   = "read_only"    # Safe: no state mutation.
    WRITE       = "write"        # Mutates state in an external system.
    PAYMENT     = "payment"      # Initiates or completes a financial transaction.
    SEND        = "send"         # Sends an outbound message / notification.


class BaseToolWrapper(BaseComponent):
    """
    A typed, permissioned wrapper around a specific external capability.

    Concrete implementations provide:
    - A metadata descriptor (id, version, tags, required permissions).
    - An ``invoke`` method that performs the actual call and returns
      a structured result dict.
    - Optional ``pre_invoke`` / ``post_invoke`` hooks for instrumentation.
    """

    @property
    @abstractmethod
    def required_permissions(self) -> frozenset[ToolPermission]:
        """Permissions this tool needs to operate."""

    @abstractmethod
    def invoke(self, **kwargs: Any) -> dict[str, Any]:
        """
        Execute the tool.

        Parameters are tool-specific and validated by the concrete class.
        Returns a plain dict so results are framework-agnostic.
        """

    def pre_invoke(self, **kwargs: Any) -> None:
        """Called immediately before ``invoke``.  Override for instrumentation."""

    def post_invoke(self, result: dict[str, Any]) -> None:
        """Called immediately after a successful ``invoke``. Override for instrumentation."""

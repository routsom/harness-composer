"""Abstract base class for framework adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from harness_composer.composition.harness_config import HarnessConfig
from harness_composer.registry import ComponentRegistry


class BaseFrameworkAdapter(ABC):
    """
    Injects a :class:`HarnessConfig` into a specific agent framework.

    Each framework exposes its own extension points:
    - LangChain/LangGraph: pre/post model callbacks
    - AWS Bedrock AgentCore: HookProvider lifecycle events
    - Google ADK: plugin system
    - Microsoft Agent Framework: middleware pipeline

    Adapters never modify the components themselves — they translate the
    harness configuration into whatever the framework's native API expects.
    """

    def __init__(self, registry: ComponentRegistry) -> None:
        self._registry = registry

    @abstractmethod
    def inject(self, config: HarnessConfig, agent: Any) -> Any:
        """
        Wrap or configure *agent* with the guardrails, tools, and verification
        checks described by *config*.

        Returns the wrapped/configured agent (may be the same object mutated
        in-place, depending on the framework).
        """

    @property
    @abstractmethod
    def framework_name(self) -> str:
        """Human-readable name of the target framework (used in logs)."""

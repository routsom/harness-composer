"""
LangChain callback handler that enforces the composed harness.

LangChain's callback system fires events at key lifecycle points:
- ``on_tool_start``   — before a tool is called
- ``on_tool_end``     — after a tool returns
- ``on_llm_start``    — before each LLM call

We use these hooks to:
1. Run guardrail checks before any tool execution.
2. Run verification checks after tool execution.
3. Optionally surface the managed context window on LLM calls.

The handler raises ``GuardrailViolation`` (a subclass of RuntimeError) when a
guardrail returns BLOCK, so the agent's execution loop sees a hard error rather
than a silent bypass.

Note: this module has an optional dependency on ``langchain-core``.
If langchain is not installed, importing this module will raise ImportError
with a helpful message.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from langchain_core.callbacks import BaseCallbackHandler
except ImportError as exc:
    raise ImportError(
        "langchain-core is required for the LangChain adapter. "
        "Install it with: pip install 'harness-composer[langchain]'"
    ) from exc

from harness_composer.composition.harness_config import HarnessConfig
from harness_composer.library.guardrails.base import GuardrailOutcome
from harness_composer.library.verification.base import VerificationStatus
from harness_composer.registry import ComponentRegistry

logger = logging.getLogger(__name__)


class GuardrailViolation(RuntimeError):
    """Raised when a guardrail returns BLOCK, halting agent execution."""


class HarnessCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """
    LangChain callback handler that enforces a :class:`HarnessConfig`.

    Parameters
    ----------
    config:
        The harness configuration assembled by the Composition Engine.
    registry:
        The component registry used to resolve metadata → live instances.
    raise_on_escalate:
        If True, ESCALATE outcomes are treated as hard errors (same as BLOCK).
        If False (default), ESCALATE is logged as a warning and execution
        continues — you should hook in your own escalation workflow instead.
    """

    def __init__(
        self,
        config: HarnessConfig,
        registry: ComponentRegistry,
        raise_on_escalate: bool = False,
    ) -> None:
        super().__init__()
        self._config = config
        self._registry = registry
        self._raise_on_escalate = raise_on_escalate

    # ── Guardrail hook: fires before every tool call ─────────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown_tool")
        payload: dict[str, Any] = {"tool": tool_name, "input": input_str}

        for guard_meta in self._config.guardrails:
            guardrail = self._registry.resolve(guard_meta)

            # Resolve the actual guardrail component (avoids circular import).
            from harness_composer.library.guardrails.base import BaseGuardrail
            if not isinstance(guardrail, BaseGuardrail):
                continue

            result = guardrail.check(payload)
            logger.debug(
                "Guardrail '%s' → %s (%s)",
                guard_meta.id, result.outcome.value, result.reason,
            )

            if result.outcome == GuardrailOutcome.BLOCK:
                raise GuardrailViolation(
                    f"Guardrail '{guard_meta.id}' blocked tool '{tool_name}': "
                    f"{result.reason}"
                )

            if result.outcome == GuardrailOutcome.ESCALATE:
                msg = (
                    f"Guardrail '{guard_meta.id}' escalated tool '{tool_name}': "
                    f"{result.reason}"
                )
                if self._raise_on_escalate:
                    raise GuardrailViolation(msg)
                logger.warning(msg)

    # ── Verification hook: fires after every tool call ───────────────────────

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        if not self._config.verification_checks:
            return

        action_result: dict[str, Any] = {"raw_output": output}
        action_payload: dict[str, Any] = {}  # Not available post-hoc in base callback.

        for check_meta in self._config.verification_checks:
            check_component = self._registry.resolve(check_meta)

            from harness_composer.library.verification.base import BaseVerificationCheck
            if not isinstance(check_component, BaseVerificationCheck):
                continue

            result = check_component.verify(action_payload, action_result)
            logger.debug(
                "Verification '%s' → %s (%s)",
                check_meta.id, result.status.value, result.reason,
            )

            if result.status == VerificationStatus.FAILED:
                logger.error(
                    "Verification check '%s' FAILED: %s",
                    check_meta.id, result.reason,
                )
            elif result.status == VerificationStatus.UNCERTAIN:
                logger.warning(
                    "Verification check '%s' UNCERTAIN: %s",
                    check_meta.id, result.reason,
                )

    def on_tool_error(
        self, error: Exception | KeyboardInterrupt, **kwargs: Any
    ) -> None:
        logger.error("Tool error captured by HarnessCallbackHandler: %s", error)

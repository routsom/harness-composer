"""
LangChain / LangGraph framework adapter.

Injects the composed harness into a LangChain agent or chain by:
1. Attaching the :class:`HarnessCallbackHandler` (guardrails + verification).
2. Filtering the agent's tool list to only those authorised by the harness.
3. Logging the full harness config for audit purposes.

LangChain extension points used
---------------------------------
- ``RunnableConfig["callbacks"]`` — the standard callback list; all
  LangChain runnables accept this without modification.
- ``agent.tools`` / ``agent.tools_map`` — the list of tools available to
  the agent executor; we filter this in-place to enforce least-privilege.
"""

from __future__ import annotations

import logging
from typing import Any

from harness_composer.adapters.base import BaseFrameworkAdapter
from harness_composer.adapters.langchain.callbacks import HarnessCallbackHandler
from harness_composer.composition.harness_config import HarnessConfig
from harness_composer.registry import ComponentRegistry

logger = logging.getLogger(__name__)


class LangChainAdapter(BaseFrameworkAdapter):
    """
    Adapter for LangChain agents and chains.

    Parameters
    ----------
    registry:
        The component registry (used to resolve metadata → instances).
    raise_on_escalate:
        Forwarded to :class:`HarnessCallbackHandler`.
    """

    def __init__(
        self,
        registry: ComponentRegistry,
        raise_on_escalate: bool = False,
    ) -> None:
        super().__init__(registry)
        self._raise_on_escalate = raise_on_escalate

    @property
    def framework_name(self) -> str:
        return "LangChain"

    def inject(self, config: HarnessConfig, agent: Any) -> Any:
        """
        Attach the harness to *agent* and return the configured agent.

        The agent is expected to be a LangChain ``AgentExecutor`` or any
        ``Runnable`` that accepts a ``config`` keyword argument with callbacks.

        If *agent* has a ``tools`` attribute, the list is filtered to only
        include tools authorised by the harness configuration.

        Parameters
        ----------
        config:
            The :class:`HarnessConfig` produced by the Composition Engine.
        agent:
            A LangChain ``AgentExecutor``, ``Runnable``, or compatible object.

        Returns
        -------
        Any
            The same *agent* object, configured with the harness callbacks
            and (if applicable) a filtered tool list.
        """
        logger.info(
            "[HarnessComposer/%s] Injecting harness: %s",
            self.framework_name, config.summary(),
        )

        # 1. Attach callback handler.
        callback = HarnessCallbackHandler(
            config=config,
            registry=self._registry,
            raise_on_escalate=self._raise_on_escalate,
        )
        _attach_callback(agent, callback)

        # 2. Filter tools to the authorised set.
        authorised_tool_ids = {t.id for t in config.tool_wrappers}
        if authorised_tool_ids:
            _filter_tools(agent, authorised_tool_ids)

        return agent

    def build_runnable_config(self, config: HarnessConfig) -> dict[str, Any]:
        """
        Return a ``RunnableConfig`` dict that can be passed as ``config=``
        to any LangChain ``Runnable.invoke()`` / ``Runnable.stream()`` call.

        Use this when you cannot mutate the agent object directly.

        >>> runnable_config = adapter.build_runnable_config(harness)
        >>> chain.invoke({"input": task}, config=runnable_config)
        """
        callback = HarnessCallbackHandler(
            config=config,
            registry=self._registry,
            raise_on_escalate=self._raise_on_escalate,
        )
        return {"callbacks": [callback]}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _attach_callback(agent: Any, callback: Any) -> None:
    """Attach *callback* to *agent* using the most appropriate mechanism."""
    # AgentExecutor and many LangChain objects expose ``callbacks``.
    if hasattr(agent, "callbacks") and agent.callbacks is not None:
        agent.callbacks.append(callback)
    elif hasattr(agent, "callbacks"):
        agent.callbacks = [callback]
    else:
        logger.debug(
            "Agent type '%s' has no 'callbacks' attribute; "
            "use build_runnable_config() instead.",
            type(agent).__name__,
        )


def _filter_tools(agent: Any, authorised_ids: set[str]) -> None:
    """Remove tools from *agent* that are not in *authorised_ids*."""
    if not hasattr(agent, "tools"):
        return
    original = list(agent.tools)
    filtered = [
        t for t in original
        if getattr(t, "name", None) in authorised_ids
    ]
    if len(filtered) != len(original):
        removed = [getattr(t, "name", "?") for t in original if t not in filtered]
        logger.info(
            "[HarnessComposer] Tool least-privilege: removed %s from agent.",
            removed,
        )
    agent.tools = filtered

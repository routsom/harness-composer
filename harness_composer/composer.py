"""
HarnessComposer — the public entry point.

Wires the classifier, composition engine, and (optionally) a framework
adapter together into a single, easy-to-use object.

Usage
-----
>>> from harness_composer import HarnessComposer
>>> from harness_composer.registry import default_registry
>>>
>>> composer = HarnessComposer(registry=default_registry())
>>> harness = composer.compose("Book me a flight to Edinburgh next Tuesday")
>>> print(harness.summary())
"""

from __future__ import annotations

import logging
from typing import Any

from harness_composer.classifier.base import BaseClassifier
from harness_composer.classifier.rules_based import RulesBasedClassifier
from harness_composer.composition.engine import CompositionEngine
from harness_composer.composition.harness_config import HarnessConfig
from harness_composer.registry import ComponentRegistry

logger = logging.getLogger(__name__)


class HarnessComposer:
    """
    Façade that orchestrates the full composition pipeline:

        task description
            → TaskClassifier  (produces TaskProfile)
            → CompositionEngine (selects components from registry)
            → HarnessConfig     (ready to inject into an agent)

    Parameters
    ----------
    registry:
        The component registry to draw from.  Use :func:`default_registry`
        for the built-in set, or build a custom one.
    classifier:
        A :class:`~harness_composer.classifier.base.BaseClassifier` instance.
        Defaults to :class:`~harness_composer.classifier.rules_based.RulesBasedClassifier`.
    """

    def __init__(
        self,
        registry: ComponentRegistry,
        classifier: BaseClassifier | None = None,
    ) -> None:
        self._registry = registry
        self._classifier = classifier or RulesBasedClassifier()
        self._engine = CompositionEngine(registry)

    def compose(
        self,
        task: str,
        *,
        agent_id: str | None = None,
        agent_track_record: float | None = None,
    ) -> HarnessConfig:
        """
        Classify *task* and return a :class:`HarnessConfig` tailored to it.

        Parameters
        ----------
        task:
            Raw natural-language task description.
        agent_id:
            Optional stable identifier for the requesting agent.
        agent_track_record:
            Fraction of past tasks by this agent completed without error.

        Returns
        -------
        HarnessConfig
            A complete, serialisable harness configuration.
        """
        logger.info("[HarnessComposer] Classifying task: %.80s…", task)
        profile = self._classifier.classify(
            task,
            agent_id=agent_id,
            agent_track_record=agent_track_record,
        )
        logger.info(
            "[HarnessComposer] Profile: risk=%s, action=%s, signals=%s",
            profile.risk_level.value,
            profile.action_type.value,
            profile.matched_signals,
        )

        config = self._engine.compose(profile)
        logger.info("[HarnessComposer] Composed: %s", config.summary())
        return config

    def compose_and_inject(
        self,
        task: str,
        agent: Any,
        adapter: BaseFrameworkAdapter,  # type: ignore[name-defined]  # noqa: F821
        *,
        agent_id: str | None = None,
        agent_track_record: float | None = None,
    ) -> Any:
        """
        Convenience method: compose the harness *and* inject it into *agent*
        in one call.

        Parameters
        ----------
        task:
            Raw natural-language task description.
        agent:
            The agent object to inject the harness into.
        adapter:
            The :class:`~harness_composer.adapters.base.BaseFrameworkAdapter`
            that knows how to inject into the target framework.

        Returns
        -------
        Any
            The configured agent, as returned by ``adapter.inject()``.
        """
        config = self.compose(
            task,
            agent_id=agent_id,
            agent_track_record=agent_track_record,
        )
        return adapter.inject(config, agent)

    @property
    def registry(self) -> ComponentRegistry:
        return self._registry

    @property
    def classifier(self) -> BaseClassifier:
        return self._classifier

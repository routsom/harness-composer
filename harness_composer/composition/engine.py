"""
Composition Engine.

Takes a :class:`TaskProfile` (from the classifier) and a
:class:`ComponentRegistry` (the library) and selects the right subset of
components, assembling them into a :class:`HarnessConfig`.

Design rationale
----------------
At MVP this is a lookup-and-filter problem, not an ML problem.  The engine
applies a tag-based selection strategy that is fully deterministic and
auditable:

1. Tool wrappers — selected by matching ``required_external_systems`` tags.
2. Context strategy — selected by risk level and action type heuristic.
3. Guardrails — selected by matching task profile attributes to guard tags.
4. Verification checks — selected by matching action type and external
   system tags.

The generative step (from the product gist) generates a *configuration*, not
code.  The engine never writes new logic.
"""

from __future__ import annotations

from harness_composer.classifier.task_profile import ActionType, RiskLevel, TaskProfile
from harness_composer.composition.harness_config import HarnessConfig
from harness_composer.library.base import ComponentKind, ComponentMetadata


class CompositionEngine:
    """
    Assembles a :class:`HarnessConfig` from a :class:`TaskProfile` and the
    available components in the registry.

    Parameters
    ----------
    registry:
        The :class:`~harness_composer.registry.ComponentRegistry` to draw
        components from.
    """

    def __init__(self, registry: ComponentRegistry) -> None:  # type: ignore[name-defined]  # noqa: F821
        self._registry = registry

    def compose(self, profile: TaskProfile) -> HarnessConfig:
        """Return a :class:`HarnessConfig` tailored to *profile*."""
        tool_wrappers       = self._select_tools(profile)
        context_strategy    = self._select_context_strategy(profile)
        guardrails          = self._select_guardrails(profile)
        verification_checks = self._select_verification_checks(profile)

        return HarnessConfig(
            task_profile=profile,
            tool_wrappers=tool_wrappers,
            context_strategy=context_strategy,
            guardrails=guardrails,
            verification_checks=verification_checks,
        )

    # ── Private selection helpers ────────────────────────────────────────────

    def _select_tools(self, profile: TaskProfile) -> list[ComponentMetadata]:
        """
        Select tool wrappers whose tags overlap with the required external
        systems declared in the task profile.
        """
        all_tools = self._registry.list_by_kind(ComponentKind.TOOL_WRAPPER)
        if not profile.required_external_systems:
            return []
        selected = [
            t for t in all_tools
            if t.tags & profile.required_external_systems  # set intersection
        ]
        return selected

    def _select_context_strategy(self, profile: TaskProfile) -> ComponentMetadata | None:
        """
        Heuristic: use compression for multi-step / financial tasks; minimal
        for everything else.
        """
        all_strats = self._registry.list_by_kind(ComponentKind.CONTEXT_STRATEGY)
        if not all_strats:
            return None

        needs_compression = (
            profile.action_type in {ActionType.TRANSACT, ActionType.ORCHESTRATE}
            or profile.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        )

        tag = "multi_step" if needs_compression else "short_task"
        for s in all_strats:
            if tag in s.tags:
                return s

        # Fallback: return the first available strategy.
        return all_strats[0]

    def _select_guardrails(self, profile: TaskProfile) -> list[ComponentMetadata]:
        """
        Select guardrail sets that are relevant to the task profile.
        Rules (OR logic — any matching tag qualifies a guardrail):
        - financial_threshold: if touches_financial_data or action is TRANSACT
        - pii_redaction:       if touches_pii
        - irreversibility:     if not is_reversible
        """
        all_guards = self._registry.list_by_kind(ComponentKind.GUARDRAIL)
        selected: list[ComponentMetadata] = []

        for g in all_guards:
            tags = g.tags
            if (
                profile.touches_financial_data
                and tags & {"financial", "payment", "transact"}
            ):
                selected.append(g)
            elif (
                profile.touches_pii
                and tags & {"pii", "privacy"}
            ):
                selected.append(g)
            elif (
                not profile.is_reversible
                and tags & {"irreversible", "confirmation"}
            ):
                selected.append(g)

        return selected

    def _select_verification_checks(self, profile: TaskProfile) -> list[ComponentMetadata]:
        """
        Select verification checks whose tags match the task profile.
        For LOW-risk / READ-only tasks, no verification is needed.
        """
        if (
            profile.risk_level == RiskLevel.LOW
            and profile.action_type == ActionType.READ
        ):
            return []

        all_checks = self._registry.list_by_kind(ComponentKind.VERIFICATION_CHECK)
        action_tag = profile.action_type.value  # e.g. "transact", "write"
        selected = [
            c for c in all_checks
            if c.tags & {action_tag} | (c.tags & profile.required_external_systems)
        ]
        return selected

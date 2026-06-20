"""
Component Registry.

The registry is the runtime catalogue of all available library components.
It maps component IDs to instances, and supports querying by kind and tags.

Every component must be registered here before the Composition Engine can
select it.  This is the governance gate: nothing reaches an agent unless it
has been explicitly registered.

Governance notes (from the product gist)
-----------------------------------------
"Every component should be human-reviewed and versioned for the foreseeable
future."

In practice, this means:
- Components are added to the registry in code (not discovered dynamically).
- Each component has an explicit version string.
- The registry is intentionally append-only at runtime — no component is
  removed or replaced after startup without a restart.
"""

from __future__ import annotations

from collections.abc import Iterator

from harness_composer.library.base import BaseComponent, ComponentKind, ComponentMetadata


class ComponentRegistry:
    """
    Stores and indexes library components.

    Parameters
    ----------
    components:
        Optional initial list of components.
    """

    def __init__(self, components: list[BaseComponent] | None = None) -> None:
        self._store: dict[str, BaseComponent] = {}
        for c in components or []:
            self.register(c)

    def register(self, component: BaseComponent) -> ComponentRegistry:
        """
        Add *component* to the registry.

        Raises
        ------
        ValueError
            If a component with the same ID is already registered.
        """
        cid = component.metadata.id
        if cid in self._store:
            raise ValueError(
                f"Component '{cid}' is already registered. "
                "Bump the version and use a new ID to replace it."
            )
        self._store[cid] = component
        return self  # fluent API

    def get(self, component_id: str) -> BaseComponent:
        """Return the component with *component_id* or raise ``KeyError``."""
        return self._store[component_id]

    def list_by_kind(self, kind: ComponentKind) -> list[ComponentMetadata]:
        """Return metadata for all registered components of *kind*."""
        return [
            c.metadata
            for c in self._store.values()
            if c.metadata.kind == kind
        ]

    def list_by_tag(self, tag: str) -> list[ComponentMetadata]:
        """Return metadata for all components that carry *tag*."""
        return [
            c.metadata
            for c in self._store.values()
            if tag in c.metadata.tags
        ]

    def resolve(self, metadata: ComponentMetadata) -> BaseComponent:
        """Resolve a metadata reference back to the live component instance."""
        return self.get(metadata.id)

    def __iter__(self) -> Iterator[BaseComponent]:
        return iter(self._store.values())

    def __len__(self) -> int:
        return len(self._store)


def default_registry() -> ComponentRegistry:
    """
    Build and return a registry pre-loaded with all built-in components.

    This is the "batteries included" starting point.  Callers can add their
    own components on top.

    >>> registry = default_registry()
    >>> len(registry)
    10
    """
    from harness_composer.library.context_strategies import (
        CompressionContextStrategy,
        MinimalContextStrategy,
    )
    from harness_composer.library.guardrails import (
        FinancialThresholdGuardrail,
        IrreversibilityConfirmationGuardrail,
        PiiRedactionGuardrail,
    )
    from harness_composer.library.tool_wrappers import (
        HttpRequestToolWrapper,
        WebSearchToolWrapper,
    )
    from harness_composer.library.verification import (
        DatabaseWriteCheck,
        ExternalConfirmationCheck,
    )

    return ComponentRegistry(
        components=[
            # Tool wrappers
            WebSearchToolWrapper(),
            HttpRequestToolWrapper(allow_mutations=False),
            # Context strategies
            MinimalContextStrategy(),
            CompressionContextStrategy(),
            # Guardrails
            FinancialThresholdGuardrail(),
            PiiRedactionGuardrail(),
            IrreversibilityConfirmationGuardrail(),
            # Verification checks
            ExternalConfirmationCheck(),
            DatabaseWriteCheck(),
        ]
    )

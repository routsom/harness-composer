"""
HarnessConfig — the output of the Composition Engine.

A HarnessConfig is a plain, serialisable data object.  It contains
references to the selected component instances, not the components
themselves, so that it can be logged, diffed, and audited without
executing anything.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from harness_composer.classifier.task_profile import TaskProfile
from harness_composer.library.base import ComponentMetadata


class HarnessConfig(BaseModel):
    """
    A complete harness configuration for one task.

    Framework adapters consume this object and inject the selected
    components into whichever agent runtime is in use.
    """

    # The task profile that drove composition.
    task_profile: TaskProfile

    # Selected components (metadata only — adapters resolve instances).
    tool_wrappers: list[ComponentMetadata] = Field(default_factory=list)
    context_strategy: ComponentMetadata | None = None
    guardrails: list[ComponentMetadata] = Field(default_factory=list)
    verification_checks: list[ComponentMetadata] = Field(default_factory=list)

    # Adapter-specific extras injected at composition time.
    adapter_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Framework-specific configuration merged in by the adapter.",
    )

    model_config = ConfigDict(frozen=True)

    def summary(self) -> str:
        """Return a one-line human-readable summary suitable for logging."""
        tools   = [t.id for t in self.tool_wrappers]
        guards  = [g.id for g in self.guardrails]
        checks  = [v.id for v in self.verification_checks]
        ctx     = self.context_strategy.id if self.context_strategy else "none"
        return (
            f"HarnessConfig("
            f"risk={self.task_profile.risk_level.value}, "
            f"action={self.task_profile.action_type.value}, "
            f"tools={tools}, "
            f"context={ctx}, "
            f"guardrails={guards}, "
            f"verification={checks})"
        )

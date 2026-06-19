"""
Component Library — pre-built, versioned, independently testable harness parts.

Every component is a plain Python object that can be:
- instantiated without external dependencies (except optional integrations),
- unit-tested in isolation,
- versioned and reviewed before being added to the registry.

Sub-packages
------------
tool_wrappers     — typed, permissioned wrappers around external capabilities.
context_strategies — different approaches to managing the LLM context window.
guardrails         — pre- and post-execution safety checks.
verification       — checks that confirm an action had its intended effect.
"""

from harness_composer.library.base import (
    ComponentKind,
    ComponentMetadata,
    BaseComponent,
)

__all__ = ["ComponentKind", "ComponentMetadata", "BaseComponent"]

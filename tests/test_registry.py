"""Tests for the ComponentRegistry."""

import pytest

from harness_composer.library.base import ComponentKind
from harness_composer.library.tool_wrappers import WebSearchToolWrapper
from harness_composer.registry import ComponentRegistry, default_registry


def test_default_registry_has_expected_count():
    registry = default_registry()
    assert len(registry) == 9


def test_register_duplicate_raises():
    registry = ComponentRegistry()
    tool = WebSearchToolWrapper()
    registry.register(tool)
    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool)


def test_list_by_kind():
    registry = default_registry()
    tools = registry.list_by_kind(ComponentKind.TOOL_WRAPPER)
    assert len(tools) >= 2
    assert all(t.kind == ComponentKind.TOOL_WRAPPER for t in tools)


def test_list_by_tag():
    registry = default_registry()
    financial = registry.list_by_tag("financial")
    assert len(financial) >= 1


def test_get_missing_raises():
    registry = default_registry()
    with pytest.raises(KeyError):
        registry.get("nonexistent_component_id")


def test_resolve_returns_live_instance():
    registry = default_registry()
    tools = registry.list_by_kind(ComponentKind.TOOL_WRAPPER)
    assert tools, "expected at least one tool"
    instance = registry.resolve(tools[0])
    assert instance is not None
    assert instance.metadata.id == tools[0].id

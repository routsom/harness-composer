"""Tests for the Composition Engine and HarnessConfig."""

import pytest

from harness_composer.classifier.rules_based import RulesBasedClassifier
from harness_composer.composition.engine import CompositionEngine
from harness_composer.composition.harness_config import HarnessConfig
from harness_composer.library.base import ComponentKind
from harness_composer.registry import default_registry


@pytest.fixture
def registry():
    return default_registry()


@pytest.fixture
def engine(registry):
    return CompositionEngine(registry)


@pytest.fixture
def clf():
    return RulesBasedClassifier()


class TestCompositionForFlightBooking:
    """High-risk financial task → full harness expected."""

    @pytest.fixture(autouse=True)
    def compose(self, clf, engine):
        profile = clf.classify("Book me a flight to Edinburgh and pay for it.")
        self.config = engine.compose(profile)

    def test_returns_harness_config(self):
        assert isinstance(self.config, HarnessConfig)

    def test_financial_guardrail_selected(self):
        ids = {g.id for g in self.config.guardrails}
        assert "guardrail_financial_threshold" in ids

    def test_irreversibility_guardrail_selected(self):
        ids = {g.id for g in self.config.guardrails}
        assert "guardrail_irreversibility_confirmation" in ids

    def test_verification_check_selected(self):
        assert len(self.config.verification_checks) > 0

    def test_compression_context_strategy(self):
        assert self.config.context_strategy is not None
        assert self.config.context_strategy.id == "context_compression"

    def test_summary_non_empty(self):
        assert len(self.config.summary()) > 0


class TestCompositionForDocumentSummary:
    """Low-risk read task → minimal harness expected."""

    @pytest.fixture(autouse=True)
    def compose(self, clf, engine):
        profile = clf.classify("Summarise this internal document.")
        self.config = engine.compose(profile)

    def test_no_guardrails(self):
        assert self.config.guardrails == []

    def test_no_verification_checks(self):
        assert self.config.verification_checks == []

    def test_minimal_context_strategy(self):
        assert self.config.context_strategy is not None
        assert self.config.context_strategy.id == "context_minimal"

    def test_no_tools_for_local_read(self):
        # Document summary has no external system references.
        assert self.config.tool_wrappers == []


class TestCompositionForPiiTask:
    """Task touching PII → PII guardrail expected."""

    def test_pii_guardrail_selected(self, clf, engine):
        profile = clf.classify("Find and log the email address of the customer.")
        config = engine.compose(profile)
        ids = {g.id for g in config.guardrails}
        assert "guardrail_pii_redaction" in ids


class TestHarnessConfigSerialisability:
    def test_model_dump(self, clf, engine):
        profile = clf.classify("Book a flight.")
        config = engine.compose(profile)
        d = config.model_dump()
        assert "task_profile" in d
        assert "guardrails" in d

    def test_summary_contains_risk(self, clf, engine):
        profile = clf.classify("Book a flight and pay.")
        config = engine.compose(profile)
        assert "risk=" in config.summary()

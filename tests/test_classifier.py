"""Tests for the rules-based task classifier."""

import pytest

from harness_composer.classifier.rules_based import RulesBasedClassifier
from harness_composer.classifier.task_profile import ActionType, RiskLevel


@pytest.fixture
def clf():
    return RulesBasedClassifier()


class TestActionTypeDetection:
    def test_read_summarise(self, clf):
        p = clf.classify("Summarise this internal document.")
        assert p.action_type == ActionType.READ

    def test_read_lookup(self, clf):
        p = clf.classify("Look up the current weather in London.")
        assert p.action_type == ActionType.READ

    def test_transact_booking(self, clf):
        p = clf.classify("Book me a flight to Edinburgh next Tuesday.")
        assert p.action_type == ActionType.TRANSACT

    def test_transact_payment(self, clf):
        p = clf.classify("Process the payment for order #1234.")
        assert p.action_type == ActionType.TRANSACT

    def test_communicate_send(self, clf):
        p = clf.classify("Send an email to the team about the meeting.")
        assert p.action_type == ActionType.COMMUNICATE

    def test_write_create(self, clf):
        p = clf.classify("Create a new record in the CRM for this lead.")
        assert p.action_type == ActionType.WRITE

    def test_orchestrate_pipeline(self, clf):
        p = clf.classify("Run the full data pipeline and delegate to sub-agents.")
        assert p.action_type == ActionType.ORCHESTRATE


class TestRiskLevel:
    def test_low_risk_read(self, clf):
        p = clf.classify("Summarise this document.")
        assert p.risk_level == RiskLevel.LOW

    def test_medium_risk_write(self, clf):
        p = clf.classify("Update the record in the CRM.")
        assert p.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}

    def test_high_risk_financial(self, clf):
        p = clf.classify("Book and pay for a flight to Edinburgh.")
        assert p.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}


class TestReversibility:
    def test_summarise_is_reversible(self, clf):
        p = clf.classify("Summarise the document.")
        assert p.is_reversible is True

    def test_booking_is_not_fully_reversible(self, clf):
        p = clf.classify("Book me a flight and pay for it.")
        assert p.is_reversible is False

    def test_irreversible_send(self, clf):
        p = clf.classify("Send the email to all customers.")
        assert p.is_reversible is False


class TestDataSensitivity:
    def test_pii_detected_email(self, clf):
        p = clf.classify("Find the email address of the customer.")
        assert p.touches_pii is True

    def test_no_pii_in_summary(self, clf):
        p = clf.classify("Summarise the Q3 report.")
        assert p.touches_pii is False

    def test_financial_detected(self, clf):
        p = clf.classify("Process the payment for the invoice.")
        assert p.touches_financial_data is True


class TestExternalSystems:
    def test_flight_requires_flight_api(self, clf):
        p = clf.classify("Book a flight to Paris.")
        assert "flight_search_api" in p.required_external_systems

    def test_payment_requires_processor(self, clf):
        p = clf.classify("Process the payment via Stripe.")
        assert "payment_processor" in p.required_external_systems

    def test_summarise_no_external_systems(self, clf):
        p = clf.classify("Summarise this document.")
        assert len(p.required_external_systems) == 0


class TestExplainability:
    def test_matched_signals_non_empty_for_financial(self, clf):
        p = clf.classify("Book and pay for a flight.")
        assert len(p.matched_signals) > 0

    def test_classifier_version_set(self, clf):
        p = clf.classify("Anything.")
        assert p.classifier_version == clf.version


class TestAgentTrackRecord:
    def test_poor_track_record_requires_approval(self, clf):
        p = clf.classify("Summarise this doc.", agent_track_record=0.5)
        assert p.requires_human_approval is True

    def test_good_track_record_no_forced_approval_on_low_risk(self, clf):
        p = clf.classify("Summarise this doc.", agent_track_record=0.95)
        assert p.requires_human_approval is False

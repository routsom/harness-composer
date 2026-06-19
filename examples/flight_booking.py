"""
Example: "Book me a flight to Edinburgh next Tuesday."

Demonstrates the full composition pipeline for a high-risk, financial,
multi-step task.  No real LangChain agent is created — we show what the
composed harness looks like so you can validate the output without any
external dependencies.

Run:
    python examples/flight_booking.py
"""

from __future__ import annotations

import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from harness_composer import HarnessComposer
from harness_composer.registry import default_registry

# ── Compose ──────────────────────────────────────────────────────────────────

task = "Book me a flight to Edinburgh next Tuesday and pay with my corporate card."

registry = default_registry()
composer  = HarnessComposer(registry=registry)
harness   = composer.compose(task)

# ── Display results ───────────────────────────────────────────────────────────

print("\n" + "=" * 70)
print("TASK")
print("=" * 70)
print(task)

print("\n" + "=" * 70)
print("TASK PROFILE  (classifier output)")
print("=" * 70)
profile = harness.task_profile
print(f"  Action type         : {profile.action_type.value}")
print(f"  Risk level          : {profile.risk_level.value}")
print(f"  Reversible          : {profile.is_reversible}")
print(f"  Reversibility window: {profile.reversibility_window_seconds}s")
print(f"  Touches PII         : {profile.touches_pii}")
print(f"  Touches financial   : {profile.touches_financial_data}")
print(f"  External systems    : {sorted(profile.required_external_systems)}")
print(f"  Requires approval   : {profile.requires_human_approval}")
print(f"  Confidence threshold: {profile.confidence_threshold}")
print(f"  Matched signals     : {profile.matched_signals}")
print(f"  Classifier version  : {profile.classifier_version}")

print("\n" + "=" * 70)
print("HARNESS CONFIG  (composition engine output)")
print("=" * 70)
print(f"  Tool wrappers      : {[t.id for t in harness.tool_wrappers]}")
print(f"  Context strategy   : {harness.context_strategy.id if harness.context_strategy else 'none'}")
print(f"  Guardrails         : {[g.id for g in harness.guardrails]}")
print(f"  Verification checks: {[v.id for v in harness.verification_checks]}")
print(f"\n  Summary: {harness.summary()}")

# ── Demonstrate guardrail checks ─────────────────────────────────────────────

print("\n" + "=" * 70)
print("GUARDRAIL CHECKS  (simulated tool payload)")
print("=" * 70)

from harness_composer.library.guardrails import FinancialThresholdGuardrail

guardrail = FinancialThresholdGuardrail(soft_limit=300, hard_limit=1500)

for amount in [150.0, 450.0, 2000.0]:
    result = guardrail.check({"amount": amount, "currency": "GBP"})
    print(f"  £{amount:>7.2f}  →  {result.outcome.value:10s}  {result.reason}")

# ── Demonstrate verification check ──────────────────────────────────────────

print("\n" + "=" * 70)
print("VERIFICATION CHECK  (simulated post-booking confirmation)")
print("=" * 70)

from harness_composer.library.verification import ExternalConfirmationCheck

check = ExternalConfirmationCheck()

# Successful confirmation
result = check.verify(
    action_payload={"destination": "Edinburgh"},
    action_result={"reference_id": "BA-20241203-EDI-7821"},
)
print(f"  With valid reference   → {result.status.value}: {result.reason}")

# Missing reference
result = check.verify(
    action_payload={"destination": "Edinburgh"},
    action_result={},
)
print(f"  With missing reference → {result.status.value}: {result.reason}")
print()

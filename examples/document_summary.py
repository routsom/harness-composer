"""
Example: "Summarise this internal document."

Demonstrates that the harness is dramatically lighter for low-risk, read-only
tasks.  No payment guardrail, no booking verification, minimal context strategy.

Run:
    python examples/document_summary.py
"""

from __future__ import annotations

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

from harness_composer import HarnessComposer
from harness_composer.registry import default_registry

task = "Summarise this internal document for the quarterly review."

registry = default_registry()
composer  = HarnessComposer(registry=registry)
harness   = composer.compose(task)

print("\n" + "=" * 70)
print("TASK")
print("=" * 70)
print(task)

print("\n" + "=" * 70)
print("TASK PROFILE")
print("=" * 70)
profile = harness.task_profile
print(f"  Action type         : {profile.action_type.value}")
print(f"  Risk level          : {profile.risk_level.value}")
print(f"  Reversible          : {profile.is_reversible}")
print(f"  Touches PII         : {profile.touches_pii}")
print(f"  Touches financial   : {profile.touches_financial_data}")
print(f"  External systems    : {sorted(profile.required_external_systems)}")
print(f"  Requires approval   : {profile.requires_human_approval}")
print(f"  Matched signals     : {profile.matched_signals}")

print("\n" + "=" * 70)
print("HARNESS CONFIG")
print("=" * 70)
print(f"  Tool wrappers      : {[t.id for t in harness.tool_wrappers]}")
print(f"  Context strategy   : {harness.context_strategy.id if harness.context_strategy else 'none'}")
print(f"  Guardrails         : {[g.id for g in harness.guardrails]}")
print(f"  Verification checks: {[v.id for v in harness.verification_checks]}")
print(f"\n  Summary: {harness.summary()}")

print("\n[Note: compare the guardrail and verification lists against the flight")
print(" booking example — they are empty for this low-risk read-only task.]\n")

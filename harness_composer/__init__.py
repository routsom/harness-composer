"""
Harness Composer — dynamically assemble the right agent harness for any task.

Quickstart
----------
>>> from harness_composer import HarnessComposer
>>> from harness_composer.registry import default_registry
>>>
>>> composer = HarnessComposer(registry=default_registry())
>>> harness = composer.compose("Book me a flight to Edinburgh next Tuesday")
>>> print(harness)
"""

from harness_composer.classifier.task_profile import ActionType, RiskLevel, TaskProfile
from harness_composer.composer import HarnessComposer
from harness_composer.composition.harness_config import HarnessConfig

__all__ = [
    "HarnessComposer",
    "HarnessConfig",
    "TaskProfile",
    "ActionType",
    "RiskLevel",
]

"""Abstract base class for Task Classifiers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from harness_composer.classifier.task_profile import TaskProfile


class BaseClassifier(ABC):
    """
    A classifier takes a raw task description (and optional agent metadata) and
    returns a :class:`TaskProfile` that the Composition Engine consumes.

    The contract is intentionally thin so that rule-based, ML-based, and
    LLM-based implementations can all conform to it.
    """

    @abstractmethod
    def classify(
        self,
        task: str,
        *,
        agent_id: str | None = None,
        agent_track_record: float | None = None,
    ) -> TaskProfile:
        """
        Classify *task* and return a :class:`TaskProfile`.

        Parameters
        ----------
        task:
            Raw natural-language description of the task.
        agent_id:
            Optional stable identifier for the agent requesting execution.
            Used to look up track-record data if available.
        agent_track_record:
            Fraction of past tasks by this agent that completed without
            override or error (0.0–1.0).  ``None`` means no history.
        """

    @property
    @abstractmethod
    def version(self) -> str:
        """Stable version string used in audit trails."""

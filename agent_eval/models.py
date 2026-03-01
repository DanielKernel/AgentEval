"""Data models for AgentEval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Criterion:
    """A single evaluation criterion.

    Attributes:
        name: Short identifier for the criterion (e.g. "correctness").
        description: Human-readable description of what is being measured.
        weight: Relative importance when computing a weighted overall score.
            All criterion weights in an eval task are normalised at score time.
        passing_threshold: Minimum score [0, 1] required for this criterion to
            be considered passing.
    """

    name: str
    description: str
    weight: float = 1.0
    passing_threshold: float = 0.5

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(f"Criterion weight must be positive, got {self.weight!r}")
        if not 0.0 <= self.passing_threshold <= 1.0:
            raise ValueError(
                f"passing_threshold must be in [0, 1], got {self.passing_threshold!r}"
            )


@dataclass
class EvalTask:
    """A single evaluation task pairing an agent input with the expected output.

    Attributes:
        task_id: Unique identifier for the task.
        input: The prompt / question given to the agent.
        expected_output: The reference / gold answer (optional – some criteria
            may not require a reference).
        metadata: Arbitrary extra data attached to the task.
    """

    task_id: str
    input: str
    expected_output: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CriterionScore:
    """Score for a single criterion within one evaluation result.

    Attributes:
        criterion: The criterion that was scored.
        score: Numeric score in [0, 1].
        passing: Whether the score meets or exceeds the criterion's threshold.
        reasoning: Optional explanation produced by the evaluator.
    """

    criterion: Criterion
    score: float
    passing: bool
    reasoning: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be in [0, 1], got {self.score!r}")


@dataclass
class EvalResult:
    """Aggregated evaluation result for one (task, agent_output) pair.

    Attributes:
        task: The task that was evaluated.
        agent_output: The raw string produced by the agent.
        criterion_scores: Per-criterion breakdown of the evaluation.
        overall_score: Weighted average across all criteria.
        passed: True when *every* criterion's score meets its threshold.
    """

    task: EvalTask
    agent_output: str
    criterion_scores: List[CriterionScore]
    overall_score: float
    passed: bool

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the result."""
        return {
            "task_id": self.task.task_id,
            "agent_output": self.agent_output,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "criterion_scores": [
                {
                    "criterion": cs.criterion.name,
                    "score": cs.score,
                    "passing": cs.passing,
                    "reasoning": cs.reasoning,
                }
                for cs in self.criterion_scores
            ],
        }


@dataclass
class TranscriptStep:
    """One step of an agent interaction transcript."""

    step_id: int
    action: str = ""
    observation: str = ""
    tool_name: Optional[str] = None
    tool_input: Dict[str, Any] = field(default_factory=dict)
    tool_output: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the transcript step."""
        return {
            "step_id": self.step_id,
            "action": self.action,
            "observation": self.observation,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "metadata": self.metadata,
        }


@dataclass
class TrialResult:
    """Result for one trial of a task."""

    trial_index: int
    seed: Optional[int]
    eval_result: EvalResult
    transcript: List[TranscriptStep] = field(default_factory=list)
    outcome: Optional[Dict[str, Any]] = None
    error: str = ""

    @property
    def passed(self) -> bool:
        """Whether this trial passed and did not raise runtime errors."""
        return self.eval_result.passed and not self.error

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the trial result."""
        return {
            "trial_index": self.trial_index,
            "seed": self.seed,
            "passed": self.passed,
            "error": self.error,
            "outcome": self.outcome,
            "transcript": [step.to_dict() for step in self.transcript],
            "eval_result": self.eval_result.to_dict(),
        }


@dataclass
class TaskTrialResult:
    """Aggregated result of multiple trials for one task."""

    task: EvalTask
    trials: List[TrialResult]

    def __post_init__(self) -> None:
        if not self.trials:
            raise ValueError("TaskTrialResult requires at least one trial")

    @property
    def k(self) -> int:
        """Number of trials for this task."""
        return len(self.trials)

    @property
    def pass_at_k(self) -> float:
        """Empirical pass@k for this task."""
        return 1.0 if any(trial.passed for trial in self.trials) else 0.0

    @property
    def pass_hat_k(self) -> float:
        """Empirical pass^k for this task (all trials must pass)."""
        return 1.0 if all(trial.passed for trial in self.trials) else 0.0

    @property
    def trial_pass_rate(self) -> float:
        """Fraction of successful trials."""
        return sum(1 for trial in self.trials if trial.passed) / self.k

    @property
    def mean_overall_score(self) -> float:
        """Mean overall score across all trials."""
        return sum(trial.eval_result.overall_score for trial in self.trials) / self.k

    @property
    def best_overall_score(self) -> float:
        """Best overall score across trials."""
        return max(trial.eval_result.overall_score for trial in self.trials)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the task-level trial result."""
        return {
            "task_id": self.task.task_id,
            "k": self.k,
            "pass_at_k": self.pass_at_k,
            "pass_hat_k": self.pass_hat_k,
            "trial_pass_rate": self.trial_pass_rate,
            "mean_overall_score": self.mean_overall_score,
            "best_overall_score": self.best_overall_score,
            "trials": [trial.to_dict() for trial in self.trials],
        }

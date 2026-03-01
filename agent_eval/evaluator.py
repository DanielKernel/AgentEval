"""Core evaluator implementation for AgentEval."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence

from agent_eval.models import (
    Criterion,
    CriterionScore,
    EvalResult,
    EvalTask,
    TaskTrialResult,
    TranscriptStep,
    TrialResult,
)


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def exact_match(agent_output: str, expected_output: Optional[str]) -> float:
    """Return 1.0 when the outputs match exactly (case-insensitive, stripped)."""
    if expected_output is None:
        return 0.0
    return 1.0 if agent_output.strip().lower() == expected_output.strip().lower() else 0.0


def contains_keywords(keywords: Sequence[str]) -> Callable[[str, Optional[str]], float]:
    """Return a scoring function that measures keyword coverage.

    The score equals the fraction of *keywords* (case-insensitive) that appear
    anywhere in the agent output.
    """
    if not keywords:
        raise ValueError("keywords must be a non-empty sequence")

    lowered = [kw.lower() for kw in keywords]

    def _score(agent_output: str, _expected: Optional[str]) -> float:
        text = agent_output.lower()
        hits = sum(1 for kw in lowered if kw in text)
        return hits / len(lowered)

    return _score


def length_check(
    min_words: int = 0,
    max_words: Optional[int] = None,
) -> Callable[[str, Optional[str]], float]:
    """Return a scoring function that checks the word count of the agent output.

    Returns 1.0 when the word count is within [min_words, max_words],
    otherwise 0.0.
    """

    def _score(agent_output: str, _expected: Optional[str]) -> float:
        word_count = len(agent_output.split())
        if word_count < min_words:
            return 0.0
        if max_words is not None and word_count > max_words:
            return 0.0
        return 1.0

    return _score


def regex_match(pattern: str, flags: int = re.IGNORECASE) -> Callable[[str, Optional[str]], float]:
    """Return a scoring function that checks whether the agent output matches *pattern*."""
    compiled = re.compile(pattern, flags)

    def _score(agent_output: str, _expected: Optional[str]) -> float:
        return 1.0 if compiled.search(agent_output) else 0.0

    return _score


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

ScoringFn = Callable[[str, Optional[str]], float]


class AgentEvaluator:
    """Evaluate agent outputs against a set of criteria.

    Parameters
    ----------
    criteria:
        List of :class:`~agent_eval.models.Criterion` objects that define what
        is evaluated.
    scoring_functions:
        Mapping from ``criterion.name`` to a callable with signature
        ``(agent_output: str, expected_output: Optional[str]) -> float``.
        The callable must return a float in ``[0, 1]``.
        Criteria without an explicit scoring function fall back to
        :func:`exact_match`.
    """

    def __init__(
        self,
        criteria: List[Criterion],
        scoring_functions: Optional[Dict[str, ScoringFn]] = None,
    ) -> None:
        if not criteria:
            raise ValueError("At least one criterion is required")
        self.criteria = criteria
        self._scoring_fns: Dict[str, ScoringFn] = scoring_functions or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, task: EvalTask, agent_output: str) -> EvalResult:
        """Evaluate *agent_output* for the given *task*.

        Parameters
        ----------
        task:
            The :class:`~agent_eval.models.EvalTask` being evaluated.
        agent_output:
            The raw string produced by the agent.

        Returns
        -------
        :class:`~agent_eval.models.EvalResult`
        """
        criterion_scores: List[CriterionScore] = []
        for criterion in self.criteria:
            score_fn = self._scoring_fns.get(criterion.name, exact_match)
            raw_score = score_fn(agent_output, task.expected_output)
            raw_score = max(0.0, min(1.0, float(raw_score)))
            passing = raw_score >= criterion.passing_threshold
            criterion_scores.append(
                CriterionScore(
                    criterion=criterion,
                    score=raw_score,
                    passing=passing,
                )
            )

        overall_score = self._weighted_average(criterion_scores)
        passed = all(cs.passing for cs in criterion_scores)

        return EvalResult(
            task=task,
            agent_output=agent_output,
            criterion_scores=criterion_scores,
            overall_score=overall_score,
            passed=passed,
        )

    def evaluate_batch(
        self,
        tasks: List[EvalTask],
        agent_outputs: List[str],
    ) -> List[EvalResult]:
        """Evaluate a list of tasks in order.

        Parameters
        ----------
        tasks:
            Ordered list of :class:`~agent_eval.models.EvalTask` objects.
        agent_outputs:
            Ordered list of agent responses corresponding to *tasks*.

        Returns
        -------
        List of :class:`~agent_eval.models.EvalResult`.
        """
        if len(tasks) != len(agent_outputs):
            raise ValueError(
                f"tasks and agent_outputs must have the same length "
                f"({len(tasks)} vs {len(agent_outputs)})"
            )
        return [self.evaluate(task, output) for task, output in zip(tasks, agent_outputs)]

    def evaluate_task_trials(
        self,
        task: EvalTask,
        agent_outputs: Sequence[str],
        seeds: Optional[Sequence[Optional[int]]] = None,
        transcripts: Optional[Sequence[Optional[Sequence[Dict[str, Any]]]]] = None,
        outcomes: Optional[Sequence[Optional[Dict[str, Any]]]] = None,
        errors: Optional[Sequence[str]] = None,
    ) -> TaskTrialResult:
        """Evaluate multiple trial outputs for a single task.

        ``pass@k`` is represented by ``TaskTrialResult.pass_at_k`` and
        ``pass^k`` by ``TaskTrialResult.pass_hat_k``.
        """
        if not agent_outputs:
            raise ValueError("agent_outputs must contain at least one trial output")

        k = len(agent_outputs)
        seed_values = self._normalise_optional_values(
            values=seeds,
            expected_length=k,
            field_name="seeds",
            default_value=None,
        )
        transcript_values = self._normalise_optional_values(
            values=transcripts,
            expected_length=k,
            field_name="transcripts",
            default_value=None,
        )
        outcome_values = self._normalise_optional_values(
            values=outcomes,
            expected_length=k,
            field_name="outcomes",
            default_value=None,
        )
        error_values = self._normalise_optional_values(
            values=errors,
            expected_length=k,
            field_name="errors",
            default_value="",
        )

        trials: List[TrialResult] = []
        for i, output in enumerate(agent_outputs):
            eval_result = self.evaluate(task, output)
            transcript_steps = self._normalise_transcript_steps(transcript_values[i])
            trials.append(
                TrialResult(
                    trial_index=i,
                    seed=seed_values[i],
                    eval_result=eval_result,
                    transcript=transcript_steps,
                    outcome=outcome_values[i],
                    error=error_values[i],
                )
            )

        return TaskTrialResult(task=task, trials=trials)

    def evaluate_batch_trials(
        self,
        tasks: Sequence[EvalTask],
        outputs_by_task: Sequence[Sequence[str]],
        seeds_by_task: Optional[Sequence[Optional[Sequence[Optional[int]]]]] = None,
        transcripts_by_task: Optional[
            Sequence[Optional[Sequence[Optional[Sequence[Dict[str, Any]]]]]]
        ] = None,
        outcomes_by_task: Optional[Sequence[Optional[Sequence[Optional[Dict[str, Any]]]]]] = None,
        errors_by_task: Optional[Sequence[Optional[Sequence[str]]]] = None,
    ) -> List[TaskTrialResult]:
        """Evaluate multiple tasks where each task has k trial outputs."""
        if len(tasks) != len(outputs_by_task):
            raise ValueError(
                f"tasks and outputs_by_task must have the same length "
                f"({len(tasks)} vs {len(outputs_by_task)})"
            )

        if seeds_by_task is not None and len(seeds_by_task) != len(tasks):
            raise ValueError(
                f"seeds_by_task must have the same length as tasks "
                f"({len(seeds_by_task)} vs {len(tasks)})"
            )
        if transcripts_by_task is not None and len(transcripts_by_task) != len(tasks):
            raise ValueError(
                f"transcripts_by_task must have the same length as tasks "
                f"({len(transcripts_by_task)} vs {len(tasks)})"
            )
        if outcomes_by_task is not None and len(outcomes_by_task) != len(tasks):
            raise ValueError(
                f"outcomes_by_task must have the same length as tasks "
                f"({len(outcomes_by_task)} vs {len(tasks)})"
            )
        if errors_by_task is not None and len(errors_by_task) != len(tasks):
            raise ValueError(
                f"errors_by_task must have the same length as tasks "
                f"({len(errors_by_task)} vs {len(tasks)})"
            )

        task_results: List[TaskTrialResult] = []
        for i, task in enumerate(tasks):
            task_results.append(
                self.evaluate_task_trials(
                    task=task,
                    agent_outputs=outputs_by_task[i],
                    seeds=None if seeds_by_task is None else seeds_by_task[i],
                    transcripts=None if transcripts_by_task is None else transcripts_by_task[i],
                    outcomes=None if outcomes_by_task is None else outcomes_by_task[i],
                    errors=None if errors_by_task is None else errors_by_task[i],
                )
            )
        return task_results

    def summary(self, results: List[EvalResult]) -> Dict:
        """Return aggregate statistics over a list of results.

        Parameters
        ----------
        results:
            Output of :meth:`evaluate_batch`.

        Returns
        -------
        dict with keys ``total``, ``passed``, ``failed``,
        ``pass_rate``, ``mean_overall_score``, and per-criterion
        averages under ``criterion_averages``.
        """
        if not results:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "mean_overall_score": 0.0,
                "criterion_averages": {},
            }

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        mean_score = sum(r.overall_score for r in results) / total

        criterion_averages: Dict[str, float] = {}
        for criterion in self.criteria:
            scores = [
                cs.score
                for r in results
                for cs in r.criterion_scores
                if cs.criterion.name == criterion.name
            ]
            criterion_averages[criterion.name] = sum(scores) / len(scores) if scores else 0.0

        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total,
            "mean_overall_score": mean_score,
            "criterion_averages": criterion_averages,
        }

    def trial_summary(self, task_trial_results: Sequence[TaskTrialResult]) -> Dict[str, Any]:
        """Return aggregate statistics over task-level trial results."""
        if not task_trial_results:
            return {
                "total_tasks": 0,
                "total_trials": 0,
                "pass_at_k": 0.0,
                "pass_hat_k": 0.0,
                "trial_pass_rate": 0.0,
                "mean_trial_score": 0.0,
                "mean_best_score": 0.0,
                "criterion_averages": {},
                "k_values": [],
                "trial_errors": 0,
            }

        total_tasks = len(task_trial_results)
        total_trials = sum(task_result.k for task_result in task_trial_results)
        passed_trials = sum(
            1
            for task_result in task_trial_results
            for trial in task_result.trials
            if trial.passed
        )
        pass_at_k = sum(task_result.pass_at_k for task_result in task_trial_results) / total_tasks
        pass_hat_k = sum(task_result.pass_hat_k for task_result in task_trial_results) / total_tasks
        mean_trial_score = (
            sum(
                trial.eval_result.overall_score
                for task_result in task_trial_results
                for trial in task_result.trials
            )
            / total_trials
        )
        mean_best_score = (
            sum(task_result.best_overall_score for task_result in task_trial_results) / total_tasks
        )
        trial_errors = sum(
            1
            for task_result in task_trial_results
            for trial in task_result.trials
            if trial.error
        )

        criterion_averages: Dict[str, float] = {}
        for criterion in self.criteria:
            scores = [
                cs.score
                for task_result in task_trial_results
                for trial in task_result.trials
                for cs in trial.eval_result.criterion_scores
                if cs.criterion.name == criterion.name
            ]
            criterion_averages[criterion.name] = sum(scores) / len(scores) if scores else 0.0

        k_values = sorted({task_result.k for task_result in task_trial_results})

        return {
            "total_tasks": total_tasks,
            "total_trials": total_trials,
            "pass_at_k": pass_at_k,
            "pass_hat_k": pass_hat_k,
            "trial_pass_rate": passed_trials / total_trials,
            "mean_trial_score": mean_trial_score,
            "mean_best_score": mean_best_score,
            "criterion_averages": criterion_averages,
            "k_values": k_values,
            "trial_errors": trial_errors,
        }

    def summary_json(self, results: List[EvalResult]) -> str:
        """Return :meth:`summary` serialised as a JSON string."""
        return json.dumps(self.summary(results), indent=2)

    def trial_summary_json(self, task_trial_results: Sequence[TaskTrialResult]) -> str:
        """Return :meth:`trial_summary` serialised as a JSON string."""
        return json.dumps(self.trial_summary(task_trial_results), indent=2)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _weighted_average(criterion_scores: List[CriterionScore]) -> float:
        total_weight = sum(cs.criterion.weight for cs in criterion_scores)
        if total_weight == 0:
            return 0.0
        return sum(cs.score * cs.criterion.weight for cs in criterion_scores) / total_weight

    @staticmethod
    def _normalise_optional_values(
        values: Optional[Sequence[Any]],
        expected_length: int,
        field_name: str,
        default_value: Any,
    ) -> List[Any]:
        if values is None:
            return [default_value for _ in range(expected_length)]
        if len(values) != expected_length:
            raise ValueError(
                f"{field_name} must have the same length as agent_outputs "
                f"({len(values)} vs {expected_length})"
            )
        return list(values)

    @staticmethod
    def _normalise_transcript_steps(
        raw_steps: Optional[Sequence[Any]],
    ) -> List[TranscriptStep]:
        if raw_steps is None:
            return []

        normalised_steps: List[TranscriptStep] = []
        for i, raw in enumerate(raw_steps):
            if isinstance(raw, TranscriptStep):
                normalised_steps.append(raw)
                continue

            if isinstance(raw, dict):
                step_data = raw
            else:
                step_data = {"step_id": i, "observation": str(raw)}
            normalised_steps.append(
                TranscriptStep(
                    step_id=int(step_data.get("step_id", i)),
                    action=str(step_data.get("action", "")),
                    observation=str(step_data.get("observation", "")),
                    tool_name=step_data.get("tool_name"),
                    tool_input=step_data.get("tool_input", {}) or {},
                    tool_output=step_data.get("tool_output"),
                    metadata=step_data.get("metadata", {}) or {},
                )
            )
        return normalised_steps

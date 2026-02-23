"""Core evaluator implementation for AgentEval."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Sequence

from agent_eval.models import (
    Criterion,
    CriterionScore,
    EvalResult,
    EvalTask,
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

    def summary_json(self, results: List[EvalResult]) -> str:
        """Return :meth:`summary` serialised as a JSON string."""
        return json.dumps(self.summary(results), indent=2)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _weighted_average(criterion_scores: List[CriterionScore]) -> float:
        total_weight = sum(cs.criterion.weight for cs in criterion_scores)
        if total_weight == 0:
            return 0.0
        return sum(cs.score * cs.criterion.weight for cs in criterion_scores) / total_weight

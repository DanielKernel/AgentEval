"""Unit tests for AgentEval."""

import pytest

from agent_eval.models import Criterion, EvalTask, CriterionScore, EvalResult
from agent_eval.evaluator import (
    AgentEvaluator,
    contains_keywords,
    exact_match,
    length_check,
    regex_match,
)


# ---------------------------------------------------------------------------
# Criterion tests
# ---------------------------------------------------------------------------

class TestCriterion:
    def test_defaults(self):
        c = Criterion(name="correctness", description="Is it correct?")
        assert c.weight == 1.0
        assert c.passing_threshold == 0.5

    def test_invalid_weight(self):
        with pytest.raises(ValueError, match="weight must be positive"):
            Criterion(name="x", description="y", weight=0)

    def test_invalid_threshold(self):
        with pytest.raises(ValueError, match="passing_threshold"):
            Criterion(name="x", description="y", passing_threshold=1.5)


# ---------------------------------------------------------------------------
# Scoring function tests
# ---------------------------------------------------------------------------

class TestScoringFunctions:
    def test_exact_match_hit(self):
        assert exact_match("Hello World", "hello world") == 1.0

    def test_exact_match_miss(self):
        assert exact_match("Hello", "World") == 0.0

    def test_exact_match_no_expected(self):
        assert exact_match("anything", None) == 0.0

    def test_contains_keywords_full(self):
        fn = contains_keywords(["python", "agent"])
        assert fn("This agent uses Python", None) == 1.0

    def test_contains_keywords_partial(self):
        fn = contains_keywords(["python", "agent", "missing"])
        score = fn("This agent uses Python", None)
        assert abs(score - 2 / 3) < 1e-9

    def test_contains_keywords_empty_raises(self):
        with pytest.raises(ValueError):
            contains_keywords([])

    def test_length_check_in_range(self):
        fn = length_check(min_words=3, max_words=10)
        assert fn("one two three four", None) == 1.0

    def test_length_check_too_short(self):
        fn = length_check(min_words=5)
        assert fn("too short", None) == 0.0

    def test_length_check_too_long(self):
        fn = length_check(max_words=2)
        assert fn("one two three", None) == 0.0

    def test_regex_match_hit(self):
        fn = regex_match(r"\d{3}-\d{4}")
        assert fn("Call 555-1234 now", None) == 1.0

    def test_regex_match_miss(self):
        fn = regex_match(r"\d{3}-\d{4}")
        assert fn("no phone here", None) == 0.0


# ---------------------------------------------------------------------------
# AgentEvaluator tests
# ---------------------------------------------------------------------------

class TestAgentEvaluator:
    @pytest.fixture
    def simple_criterion(self):
        return Criterion(
            name="correctness",
            description="The output matches the expected answer.",
            weight=1.0,
            passing_threshold=1.0,
        )

    @pytest.fixture
    def simple_task(self):
        return EvalTask(
            task_id="t1",
            input="What is 2+2?",
            expected_output="4",
        )

    @pytest.fixture
    def evaluator(self, simple_criterion):
        return AgentEvaluator(criteria=[simple_criterion])

    def test_evaluate_passing(self, evaluator, simple_task):
        result = evaluator.evaluate(simple_task, "4")
        assert result.passed is True
        assert result.overall_score == 1.0

    def test_evaluate_failing(self, evaluator, simple_task):
        result = evaluator.evaluate(simple_task, "5")
        assert result.passed is False
        assert result.overall_score == 0.0

    def test_evaluate_batch_length_mismatch(self, evaluator, simple_task):
        with pytest.raises(ValueError, match="same length"):
            evaluator.evaluate_batch([simple_task], ["a", "b"])

    def test_evaluate_batch(self, evaluator, simple_task):
        t2 = EvalTask(task_id="t2", input="What is 3+3?", expected_output="6")
        results = evaluator.evaluate_batch([simple_task, t2], ["4", "6"])
        assert len(results) == 2
        assert all(r.passed for r in results)

    def test_summary_empty(self, evaluator):
        s = evaluator.summary([])
        assert s["total"] == 0
        assert s["pass_rate"] == 0.0

    def test_summary(self, evaluator, simple_task):
        t2 = EvalTask(task_id="t2", input="What is 3+3?", expected_output="6")
        results = evaluator.evaluate_batch([simple_task, t2], ["4", "wrong"])
        s = evaluator.summary(results)
        assert s["total"] == 2
        assert s["passed"] == 1
        assert s["failed"] == 1
        assert s["pass_rate"] == 0.5

    def test_to_dict(self, evaluator, simple_task):
        result = evaluator.evaluate(simple_task, "4")
        d = result.to_dict()
        assert d["task_id"] == "t1"
        assert d["passed"] is True
        assert "criterion_scores" in d

    def test_weighted_average(self):
        c1 = Criterion(name="a", description="", weight=2.0)
        c2 = Criterion(name="b", description="", weight=1.0)
        evaluator = AgentEvaluator(
            criteria=[c1, c2],
            scoring_functions={
                "a": lambda out, exp: 1.0,
                "b": lambda out, exp: 0.0,
            },
        )
        task = EvalTask(task_id="w", input="x")
        result = evaluator.evaluate(task, "anything")
        # weighted: (1.0*2 + 0.0*1) / 3 ≈ 0.667
        assert abs(result.overall_score - 2 / 3) < 1e-9

    def test_no_criteria_raises(self):
        with pytest.raises(ValueError, match="At least one criterion"):
            AgentEvaluator(criteria=[])

    def test_summary_json(self, evaluator, simple_task):
        import json
        results = evaluator.evaluate_batch([simple_task], ["4"])
        json_str = evaluator.summary_json(results)
        data = json.loads(json_str)
        assert data["total"] == 1

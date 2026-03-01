"""Unit tests for CLI helpers."""

import pytest

from agent_eval.cli import _build_evaluator, _parse_outputs
from agent_eval.models import EvalTask


def test_build_evaluator_supports_length_and_regex():
    config = {
        "criteria": [
            {
                "name": "length_ok",
                "description": "Length constraint",
                "scoring_function": "length_check",
                "min_words": 2,
                "max_words": 6,
                "passing_threshold": 1.0,
            },
            {
                "name": "has_phone",
                "description": "Contains phone pattern",
                "scoring_function": "regex_match",
                "pattern": r"\d{3}-\d{4}",
                "passing_threshold": 1.0,
            },
        ]
    }

    evaluator = _build_evaluator(config)
    task = EvalTask(task_id="c1", input="prompt")
    result = evaluator.evaluate(task, "Call 555-1234 now")

    assert result.passed is True
    assert result.overall_score == 1.0


def test_build_evaluator_coerces_length_bounds_from_json_scalars():
    config = {
        "criteria": [
            {
                "name": "length_ok",
                "description": "Length constraint",
                "scoring_function": "length_check",
                "min_words": "2",
                "max_words": 6.0,
                "passing_threshold": 1.0,
            }
        ]
    }

    evaluator = _build_evaluator(config)
    task = EvalTask(task_id="c2", input="prompt")

    in_range = evaluator.evaluate(task, "one two three four five six")
    too_long = evaluator.evaluate(task, "one two three four five six seven")

    assert in_range.passed is True
    assert too_long.passed is False


def test_build_evaluator_invalid_max_words_raises():
    config = {
        "criteria": [
            {
                "name": "length_ok",
                "scoring_function": "length_check",
                "max_words": "six",
            }
        ]
    }

    with pytest.raises(SystemExit, match="invalid max_words value"):
        _build_evaluator(config)


def test_parse_outputs_single_mode():
    parsed = _parse_outputs(
        outputs_data=[
            {"output": "a"},
            {"output": "b"},
        ],
        requested_trials=1,
    )

    assert parsed["is_trial_mode"] is False
    assert parsed["single_outputs"] == ["a", "b"]
    assert parsed["outputs_by_task"] == [["a"], ["b"]]


def test_parse_outputs_trial_mode():
    parsed = _parse_outputs(
        outputs_data=[
            {"outputs": [{"output": "a", "seed": 11}, {"output": "b", "seed": 12}]},
            {"outputs": ["x", "y"]},
        ],
        requested_trials=2,
    )

    assert parsed["is_trial_mode"] is True
    assert parsed["outputs_by_task"] == [["a", "b"], ["x", "y"]]
    assert parsed["seeds_by_task"][0] == [11, 12]


def test_parse_outputs_not_enough_trials_raises():
    with pytest.raises(SystemExit, match="Requested 3 trials"):
        _parse_outputs(
            outputs_data=[{"outputs": [{"output": "only_once"}]}],
            requested_trials=3,
        )

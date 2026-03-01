"""Tests for trial evaluation and execution harness."""

import pytest

from agent_eval.evaluator import AgentEvaluator
from agent_eval.harness import EvaluationHarness
from agent_eval.models import Criterion, EvalTask


def _make_evaluator() -> AgentEvaluator:
    criterion = Criterion(
        name="correctness",
        description="Exact match required.",
        weight=1.0,
        passing_threshold=1.0,
    )
    return AgentEvaluator(criteria=[criterion])


def test_evaluate_task_trials_metrics():
    evaluator = _make_evaluator()
    task = EvalTask(task_id="t1", input="q", expected_output="answer")

    result = evaluator.evaluate_task_trials(
        task=task,
        agent_outputs=["answer", "wrong", "answer"],
        seeds=[1, 2, 3],
        transcripts=[
            [{"step_id": 0, "action": "respond"}],
            ["fallback step text"],
            None,
        ],
        outcomes=[{"status": "ok"}, {"status": "bad"}, {"status": "ok"}],
    )

    assert result.k == 3
    assert result.pass_at_k == 1.0
    assert result.pass_hat_k == 0.0
    assert result.trial_pass_rate == pytest.approx(2 / 3)
    assert result.mean_overall_score == pytest.approx(2 / 3)
    assert result.best_overall_score == 1.0
    assert result.trials[1].transcript[0].observation == "fallback step text"


def test_trial_summary_aggregates():
    evaluator = _make_evaluator()
    tasks = [
        EvalTask(task_id="t1", input="q1", expected_output="a1"),
        EvalTask(task_id="t2", input="q2", expected_output="a2"),
    ]

    task_results = evaluator.evaluate_batch_trials(
        tasks=tasks,
        outputs_by_task=[
            ["a1", "wrong"],
            ["wrong", "wrong"],
        ],
    )
    summary = evaluator.trial_summary(task_results)

    assert summary["total_tasks"] == 2
    assert summary["total_trials"] == 4
    assert summary["pass_at_k"] == pytest.approx(0.5)
    assert summary["pass_hat_k"] == pytest.approx(0.0)
    assert summary["trial_pass_rate"] == pytest.approx(0.25)
    assert summary["mean_best_score"] == pytest.approx(0.5)
    assert summary["k_values"] == [2]


class _DummyEnvironment:
    def __init__(self, trial_index: int, seed: int):
        self.trial_index = trial_index
        self.seed = seed
        self.setup_count = 0
        self.teardown_count = 0

    def setup(self) -> None:
        self.setup_count += 1

    def teardown(self) -> None:
        self.teardown_count += 1

    def get_outcome(self):
        return {"trial_index": self.trial_index, "seed": self.seed}


def test_harness_runs_trials_and_cleans_environments():
    evaluator = _make_evaluator()
    created_envs = []

    def environment_factory(task, trial_index, seed):
        env = _DummyEnvironment(trial_index=trial_index, seed=seed)
        created_envs.append(env)
        return env

    def runner(task, environment, seed):
        if seed % 2 == 0:
            output = task.expected_output
        else:
            output = "wrong"
        return {
            "output": output,
            "transcript": [{"step_id": 0, "action": "answer"}],
            "outcome": {"seed": seed},
        }

    harness = EvaluationHarness(
        evaluator=evaluator,
        agent_runner=runner,
        environment_factory=environment_factory,
    )
    task = EvalTask(task_id="h1", input="prompt", expected_output="ok")
    result = harness.run_task(task, n_trials=3, base_seed=10)

    assert result.k == 3
    assert result.pass_at_k == 1.0
    assert result.pass_hat_k == 0.0
    assert result.trial_pass_rate == pytest.approx(2 / 3)
    assert len(created_envs) == 3
    assert all(env.setup_count == 1 for env in created_envs)
    assert all(env.teardown_count == 1 for env in created_envs)


def test_harness_records_runner_errors():
    evaluator = _make_evaluator()
    created_envs = []

    def environment_factory(task, trial_index, seed):
        env = _DummyEnvironment(trial_index=trial_index, seed=seed)
        created_envs.append(env)
        return env

    def runner(task, environment, seed):
        raise RuntimeError("runner boom")

    harness = EvaluationHarness(
        evaluator=evaluator,
        agent_runner=runner,
        environment_factory=environment_factory,
    )
    task = EvalTask(task_id="h2", input="prompt", expected_output="ok")
    result = harness.run_task(task, n_trials=1, base_seed=7)

    assert result.k == 1
    assert result.pass_at_k == 0.0
    assert "runner boom" in result.trials[0].error
    assert result.trials[0].passed is False
    assert created_envs[0].teardown_count == 1

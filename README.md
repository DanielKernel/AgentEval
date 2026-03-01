# AgentEval

A lightweight Python framework for evaluating AI agent responses against configurable criteria.

## Installation

```bash
pip install -e ".[dev]"
```

## What's New

- Multi-trial evaluation per task (`k` trials)
- Task-level `pass@k` and `pass^k` metrics
- Trial transcript and outcome capture
- End-to-end `EvaluationHarness` for running agent callables
- CLI support for `length_check` and `regex_match` scoring functions

## Quick Start

```python
from agent_eval import AgentEvaluator, Criterion, EvalTask
from agent_eval.evaluator import contains_keywords

# 1. Define criteria
criteria = [
    Criterion(
        name="correctness",
        description="The answer is factually correct.",
        weight=2.0,
        passing_threshold=1.0,
    ),
    Criterion(
        name="mentions_python",
        description="The answer mentions Python.",
        weight=1.0,
        passing_threshold=0.5,
    ),
]

# 2. Attach scoring functions
scoring_fns = {
    "correctness": lambda output, expected: 1.0 if output.strip() == expected else 0.0,
    "mentions_python": contains_keywords(["python"]),
}

# 3. Create evaluator
evaluator = AgentEvaluator(criteria=criteria, scoring_functions=scoring_fns)

# 4. Evaluate
task = EvalTask(
    task_id="q1",
    input="What language is this framework written in?",
    expected_output="Python",
)
result = evaluator.evaluate(task, "Python")
print(result.passed)          # True
print(result.overall_score)   # 1.0
```

## Multi-Trial Evaluation

```python
from agent_eval import AgentEvaluator, Criterion, EvalTask

criteria = [
    Criterion(name="correctness", description="Exact answer", passing_threshold=1.0),
]
evaluator = AgentEvaluator(criteria=criteria)

task = EvalTask(task_id="q1", input="2+2?", expected_output="4")
task_trials = evaluator.evaluate_task_trials(
    task=task,
    agent_outputs=["4", "5", "4"],  # k=3 trials
)

print(task_trials.pass_at_k)   # 1.0 (at least one trial passed)
print(task_trials.pass_hat_k)  # 0.0 (not all trials passed)
```

## Harness Usage

```python
from agent_eval import AgentEvaluator, Criterion, EvalTask, EvaluationHarness

criteria = [Criterion(name="correctness", description="Exact answer", passing_threshold=1.0)]
evaluator = AgentEvaluator(criteria=criteria)

def agent_runner(task, environment, seed):
    # Return either a string or a payload dict
    return {
        "output": "4",
        "transcript": [{"step_id": 0, "action": "answer"}],
        "outcome": {"status": "done"},
    }

harness = EvaluationHarness(evaluator=evaluator, agent_runner=agent_runner)
results = harness.run([EvalTask(task_id="t1", input="2+2?", expected_output="4")], n_trials=3)
print(harness.summary(results))
```

## CLI Usage

Create three JSON files:

**config.json**
```json
{
  "criteria": [
    {
      "name": "correctness",
      "description": "Exact match with expected output.",
      "weight": 1.0,
      "passing_threshold": 1.0,
      "scoring_function": "exact_match"
    },
    {
      "name": "format",
      "description": "Output contains a phone pattern.",
      "weight": 1.0,
      "passing_threshold": 1.0,
      "scoring_function": "regex_match",
      "pattern": "\\d{3}-\\d{4}",
      "flags": ["IGNORECASE"]
    }
  ]
}
```

**tasks.json**
```json
[
  {"task_id": "t1", "input": "What is 2+2?", "expected_output": "4"}
]
```

**outputs.json**
```json
[
  {
    "outputs": [
      {"output": "4", "seed": 11},
      {"output": "4", "seed": 12},
      {"output": "5", "seed": 13}
    ]
  }
]
```

Run the evaluator:

```bash
agent-eval --config config.json --tasks tasks.json --outputs outputs.json --trials 3
```

Use `--require-all-trials` to make CLI exit non-zero unless every trial passes (`pass^k`).

## Running Tests

```bash
pytest
```

## Scoring Functions

| Name | Description |
|---|---|
| `exact_match` | Case-insensitive exact string comparison |
| `contains_keywords` | Fraction of required keywords present |
| `length_check` | 1.0 if word count is within `[min_words, max_words]` |
| `regex_match` | 1.0 if output matches a regex pattern |

Custom scoring functions can be passed directly to `AgentEvaluator` via the `scoring_functions` dict.

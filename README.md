# AgentEval

A lightweight Python framework for evaluating AI agent responses against configurable criteria.

## Installation

```bash
pip install -e ".[dev]"
```

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
  {"output": "4"}
]
```

Run the evaluator:

```bash
agent-eval --config config.json --tasks tasks.json --outputs outputs.json
```

## Running Tests

```bash
pytest
```

## 对话类 Agent 自动化评测

对**任意对话类 Agent** 进行多轮评测（基于 Anthropic《Demystifying evals for AI agents》与 `docs` 内解读）：

- 实现 `DialogueAgent` 协议（`run(task) -> Transcript`）即可接入。
- 支持代码评估器（字符串/正则/关键词/轮次上限）与可选 LLM-as-Judge。
- 支持 **pass@k**、**pass^k** 及加权平均分。

```python
from agent_eval.conversation import (
    ConversationEvalHarness,
    ConversationTask,
    StringMatchGrader,
    MaxTurnsGrader,
)
from agent_eval.conversation.sample_agent import EchoAgent

tasks = [
    ConversationTask(
        task_id="t1",
        initial_user_message="你好",
        expected_outcome="你好",
        max_turns=10,
    )
]
graders = [StringMatchGrader(), MaxTurnsGrader(max_turns=10)]
harness = ConversationEvalHarness(agent=EchoAgent(), graders=graders, n_trials=2)
results = harness.run_evaluation(tasks)
print(harness.summary(results))
```

示例与配置见 `examples/conversation_eval/`。

## Scoring Functions

| Name | Description |
|---|---|
| `exact_match` | Case-insensitive exact string comparison |
| `contains_keywords` | Fraction of required keywords present |
| `length_check` | 1.0 if word count is within `[min_words, max_words]` |
| `regex_match` | 1.0 if output matches a regex pattern |

Custom scoring functions can be passed directly to `AgentEvaluator` via the `scoring_functions` dict.

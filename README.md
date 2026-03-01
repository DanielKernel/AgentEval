# AgentEval

轻量级**对话类 Agent** 自动化评测框架，基于 Anthropic《Demystifying evals for AI agents》与项目 `docs` 内解读实现。

## 安装

```bash
pip install -e ".[dev]"
```

## 快速开始

### Python API

实现 `DialogueAgent` 协议（`run(task) -> Transcript`）即可接入评测：

```python
from agent_eval import (
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

### CLI

```bash
agent-eval --config examples/conversation_eval/config.json \
  --tasks examples/conversation_eval/tasks.json \
  --output results.json
```

- **--config**：评测配置 JSON，可包含 **agents**（多个被测 Agent）、graders、n_trials、pass_k_param、seed 等
- **--tasks**：任务 JSON（task_id、initial_user_message、expected_outcome、max_turns 等）
- **--output**：可选，结果输出路径（多 Agent 时输出 `agents.<id>.summary/results`）
- **--agent** / **--fixed-response**：当 config 中未配置 `agents` 时，用作单个内置 Agent（兼容旧用法）

### 配置多个被测 Agent

在 `config.json` 中配置 `agents` 数组即可对接多个对话 Agent，同一套任务与评估器会对每个 Agent 各跑一遍，并输出对比：

```json
"agents": [
  { "id": "echo", "type": "echo" },
  { "id": "fixed_zh", "type": "fixed", "params": { "response": "这是固定回复。" } },
  { "id": "my_agent", "type": "custom", "module": "my_module.agents", "class": "MyAgent", "params": {} }
]
```

- **内置**：`type: "echo"` 或 `type: "fixed"`，`params` 可选（如 fixed 的 `response`）
- **自定义**：`type: "custom"`，二选一：`module` + `class`（可选 `params`），或 `callable`（如 `"mymod:create_agent"` 返回带 `run(task)->Transcript` 的对象）

## 评估器类型

| type | 说明 |
|------|------|
| `string_match` | 最后一条助手回复与预期一致（忽略大小写与首尾空白） |
| `regex` | 助手回复匹配给定正则 |
| `keyword` | 助手回复包含关键词（可配置 `require_all`） |
| `max_turns` | 轮次不超过上限（效率） |

可选：`LLMRubricGrader` 通过注入 `judge_fn` 做 LLM-as-Judge。

## 指标

- **pass@k**：n 次试验中随机抽 k 次至少一次成功的概率估计
- **pass^k**：一致性
- **overall_pass_rate** / **mean_score**：汇总通过率与加权平均分

## 测试

```bash
pytest tests/
```

## 文档与示例

- 示例任务与配置：`examples/conversation_eval/`
- 报告与附录：`docs/AI_Evaluation_Complete_Report.md`、`docs/appendices/`

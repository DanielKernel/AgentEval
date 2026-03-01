# 附录 B：对话 Agent 评测说明

本附录说明本仓库中**对话类 Agent 自动化评测**的实现，与《Demystifying evals for AI agents》及 `docs/AI_Evaluation_Complete_Report.md` 中**对话 Agent 评估策略**保持一致。

## B.1 与 Demystifying evals 的对应关系

| 文档概念 | 本仓库实现 |
|----------|------------|
| **Task** | `ConversationTask`（`task_id`、`initial_user_message`、`expected_outcome`、`max_turns` 等） |
| **Trial** | 单次 `agent.run(task)` 的执行与记录 |
| **Transcript** | `Transcript`（`turns`：user/assistant 轮次列表） |
| **Grader** | 代码评估器：`StringMatchGrader`、`RegexGrader`、`KeywordGrader`、`MaxTurnsGrader`；模型评估器：`LLMRubricGrader`（可选，通过 `judge_fn` 注入） |
| **Harness** | `ConversationEvalHarness`（运行多 Trial、应用 Grader、汇总结果） |
| **pass@k / pass^k** | `harness.summary()` 中的 `mean_pass_at_1`、`mean_pass_at_k`、`mean_pass_k` 等 |

报告中对**对话 Agent** 的建议：**主要评估器**为 LLM Rubric + Outcome，**关键指标**为满意度、完成度、轮次数。本实现提供：

- **Outcome/结果类**：`StringMatchGrader`（与预期结果比对）、`RegexGrader`/`KeywordGrader`（内容约束）。
- **轮次数**：`MaxTurnsGrader`（效率维度）。
- **LLM Rubric**：`LLMRubricGrader`，通过传入 `judge_fn(transcript_text, rubric, task_description)` 接入任意 LLM API，无需写死供应商。

## B.2 对话 Agent 协议

任意对话类 Agent 只需实现 **DialogueAgent** 协议即可被评测框架驱动：

```python
from agent_eval.conversation import ConversationTask, Transcript

class MyAgent:
    def run(self, task: ConversationTask) -> Transcript:
        # 根据 task.initial_user_message、task.max_turns 等进行多轮对话
        # 返回包含所有 user/assistant 轮次的 Transcript
        ...
```

## B.3 评估器类型与配置

| type | 说明 | 典型参数 |
|------|------|----------|
| `string_match` | 最后一条助手回复与预期一致（忽略大小写与首尾空白） | 依赖任务的 `expected_outcome` |
| `regex` | 助手回复中是否出现给定正则 | `pattern` |
| `keyword` | 助手回复中是否包含关键词（可按比例给分） | `keywords`、`require_all` |
| `max_turns` | 轮次不超过上限（效率） | `max_turns` |

配置文件示例见 `examples/conversation_eval/config.json`。

## B.4 指标含义

- **pass@k**：在 n 次试验中，随机抽 k 次至少有一次成功的概率估计（报告中的 pass@k 定义）。
- **pass^k**：一致性指标，本实现中为 `(成功次数/n)^k` 的近似。
- **overall_pass_rate**：全部试验中“所有 Grader 均通过”的比例。
- **mean_score**：各次试验加权平均分（按 Grader 权重）的再平均。

## B.5 快速运行

在项目根目录（支持多 Agent 时，config 中配置 `agents` 数组即可）：

```bash
agent-eval --config examples/conversation_eval/config.json \
  --tasks examples/conversation_eval/tasks.json \
  --output results.json
```

或使用示例脚本：

```bash
python3 examples/conversation_eval/run_conversation_eval.py \
  --tasks examples/conversation_eval/tasks.json \
  --config examples/conversation_eval/config.json \
  --output results.json
```

## B.6 对接多个被测 Agent

配置中可设置 `agents` 数组，每项包含 `id`、`type`（`echo` | `fixed` | `custom`）、可选 `params`。自定义 Agent 使用 `type: "custom"`，并指定 `module`+`class` 或 `callable`（如 `"mymod:create_agent"`），返回实现 `run(task)->Transcript` 的对象。同一套任务会对每个 Agent 分别跑评测，输出每 Agent 的 summary/results 及多 Agent 对比。

## B.7 参考

- **报告**：`docs/AI_Evaluation_Complete_Report.md` 第 18 节「对话 Agent 评估策略」及附录 C（评估指标速查表）、附录 D（术语表）。
- **源码**：`agent_eval/conversation/`（`models`、`agent`、`agent_factory`、`graders`、`harness`）。

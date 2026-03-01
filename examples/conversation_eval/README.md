# 对话类 Agent 自动化评测

基于 `docs` 下《Demystifying evals for AI agents》解读与 Anthropic 文章思路，实现对**任意对话类 Agent** 的自动化评测。

## 设计要点

- **Task / Trial / Transcript / Grader / Harness**：与文档中的评估组件一致。
- **对话 Agent 协议**：实现 `DialogueAgent.run(task) -> Transcript` 即可接入评测。
- **评估器**：支持代码评估器（字符串匹配、正则、关键词、轮次上限）与可选的 LLM-as-Judge（通过注入 `judge_fn`）。
- **指标**：支持 **pass@k**（k 次中至少 1 次成功）与 **pass^k**（一致性），以及加权平均分。

## 快速运行

在项目根目录执行：

```bash
cd examples/conversation_eval
python run_conversation_eval.py --tasks tasks.json --config config.json --output results.json
```

使用 `--agent echo`（默认）时，示例 Agent 会回显用户首条消息，因此 `tasks.json` 中 `expected_outcome` 设为与 `initial_user_message` 相同即可全部通过。

## 接入自己的 Agent

实现 `DialogueAgent` 协议：

```python
from agent_eval.conversation import ConversationTask, Transcript, Turn

class MyAgent:
    def run(self, task: ConversationTask) -> Transcript:
        turns = [Turn(role="user", content=task.initial_user_message)]
        # 调用你的模型/API，多轮直到结束或达到 task.max_turns
        response = your_llm_call(task.initial_user_message)
        turns.append(Turn(role="assistant", content=response))
        return Transcript(task_id=task.task_id, trial_number=0, turns=turns)
```

然后用 `ConversationEvalHarness(agent=MyAgent(), graders=[...])` 跑 `run_evaluation(tasks)`。

## 配置文件说明

- **tasks.json**：每个任务含 `task_id`、`initial_user_message`、可选 `expected_outcome`、`max_turns`、`metadata`。
- **config.json**：`n_trials`、`pass_k_param`、`seed`，以及 `graders` 列表（`type`: string_match | regex | keyword | max_turns，及对应参数）。

## 参考

- `docs/AI_Evaluation_Complete_Report.md`（含《Demystifying evals for AI agents》解读）
- 对话 Agent 评估策略：LLM Rubric + Outcome；指标：满意度、完成度、轮次数。

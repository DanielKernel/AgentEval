# AgentEval

轻量级 **Agent 自动化评测框架**，涵盖对话评测与**上下文/记忆评测**两套能力，基于 Anthropic《Demystifying evals for AI agents》与 benchmark 评测实践建设。

## 安装

```bash
pip install -e ".[dev]"

# 可选：接入 HuggingFace 数据集（BEIR、LongMemEval 等）
pip install -e ".[datasets]"

# 可选：完整检索能力（需 sentence-transformers）
pip install -e ".[retrieval]"
```

## 模块一：对话评测

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

### 评估器类型

| type | 说明 |
|------|------|
| `string_match` | 最后一条助手回复与预期一致（忽略大小写与首尾空白） |
| `regex` | 助手回复匹配给定正则 |
| `keyword` | 助手回复包含关键词（可配置 `require_all`） |
| `max_turns` | 轮次不超过上限（效率） |

可选：`LLMRubricGrader` 通过注入 `judge_fn` 做 LLM-as-Judge。

### 指标

- **pass@k**：n 次试验中随机抽 k 次至少一次成功的概率估计
- **pass^k**：一致性
- **overall_pass_rate** / **mean_score**：汇总通过率与加权平均分

---

## 模块二：上下文与记忆评测

专为上下文管理与记忆系统的自动化评测而设计。通过可插拔的 Service Adapter 层，可对接任意 HTTP REST API、Python SDK 或本地函数，**不绑定任何特定服务**。

### 支持的 Benchmark

| Benchmark | 类型 | 核心指标 |
|-----------|------|---------|
| [BEIR](https://github.com/beir-cellar/beir) | 检索 | nDCG@k, Recall@k, MRR |
| [LongMemEval](https://github.com/xiaowu0162/LongMemEval) | 长期记忆 | Token F1, 时序推理, 知识更新, 适当拒答 |
| [LongBench v2](https://github.com/THUDM/LongBench) | 长上下文理解 | Token F1 |
| [LoCoMo](https://github.com/snap-research/locomo) | 对话记忆 | Token F1 |
| [RULER](https://github.com/hsiehjackson/RULER) | 针式检索 / 长上下文 | Token F1 |

### 快速上手

```python
from agent_eval.context_memory import (
    BEIRLoader, ContextMemoryEvalHarness, RESTServiceAdapter
)

# 对接任意 HTTP REST 服务
adapter = RESTServiceAdapter(
    base_url="http://your-service:8080",
    endpoints={
        "retrieve": "/api/v1/retrieve",
        "store_memory": "/api/v1/memory/store",
        "query_memory": "/api/v1/memory/query",
    },
    headers={"Authorization": "Bearer <token>"},
)

# 加载 benchmark 并评测
tasks = BEIRLoader().load(local_path="./data/nfcorpus", max_samples=100)
report = ContextMemoryEvalHarness(adapter=adapter).run_retrieval(tasks)
print(report.summary())
# → {'benchmark': 'beir', 'pass_rate': 0.72, 'metrics': {'ndcg_at_k': 0.31, ...}}
```

### 三种 Adapter 模式

```python
# 1. HTTP REST（对接任意 REST API）
from agent_eval.context_memory import RESTServiceAdapter
adapter = RESTServiceAdapter(base_url="...", endpoints={...}, headers={...})

# 2. 本地函数（直接包装 Python 函数 / SDK）
from agent_eval.context_memory import LocalFunctionAdapter, MemoryAnswer
adapter = LocalFunctionAdapter(
    store_fn=lambda sid, hist: my_sdk.store(sid, hist),
    query_fn=lambda sid, q: MemoryAnswer(task_id="", answer=my_sdk.query(sid, q)),
)

# 3. 完全自定义（实现 Protocol 接口）
class MyAdapter:
    def retrieve(self, query, corpus, top_k): ...
    def store_memory(self, session_id, history): ...
    def query_memory(self, session_id, question): ...
```

### 自建评测场景（UC 对齐）

内置 7 套场景，覆盖外部 benchmark 未充分验证的用例：

| 场景 | UC | 说明 |
|------|----|------|
| `get_multi_source_tasks()` | UC001 | 多源聚合 |
| `get_memory_tier_tasks()` | UC002 | 热/温/冷分层记忆 |
| `get_context_exposure_tasks()` | UC006 | 上下文暴露控制（拒答） |
| `get_compression_tasks()` | UC009 | 上下文压缩保真度 |
| `get_working_memory_tasks()` | UC010 | 工作记忆状态追踪 |
| `get_tool_context_tasks()` | UC011 | 工具上下文治理 |
| `get_sub_agent_tasks()` | UC014 | 子代理上下文隔离 |

```python
from agent_eval.context_memory import get_all_self_built_tasks, ContextMemoryEvalHarness

tasks = get_all_self_built_tasks()
report = ContextMemoryEvalHarness(adapter=my_adapter).run(tasks)
print(f"Pass rate: {report.pass_rate:.1%}")
```

### OpenClaw 插件集成

本框架可作为 OpenClaw 插件自动被发现和加载：

```python
from agent_eval.plugins import ContextMemoryEvalPlugin

plugin = ContextMemoryEvalPlugin()
plugin.on_service_ready({"base_url": "http://localhost:8080", "token": "Bearer ..."})
report = plugin.run()
print(report.summary())
```

Entry point 已在 `pyproject.toml` 声明：
```toml
[project.entry-points."openclaw.plugins"]
context_memory_eval = "agent_eval.plugins.openclaw:ContextMemoryEvalPlugin"
```

---

## 测试

```bash
pytest tests/
```

## 文档与示例

- 对话评测示例：`examples/conversation_eval/`
- **上下文/记忆评测示例**：`examples/context_memory_eval/`
- 评测设计文档：`docs/benchmark-evaluation-guide.md`、`docs/AI_Evaluation_Complete_Report.md`

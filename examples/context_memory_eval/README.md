# Context & Memory Evaluation Examples

This directory contains examples showing how to use the `agent_eval.context_memory` module to evaluate retrieval, memory, and context quality capabilities of any AI service.

## Quick Start

```bash
# Install with optional deps for benchmark loading
pip install agent-eval[datasets]

# Run BEIR retrieval evaluation (local BM25 demo)
python beir_eval_example.py --local-path ./data/nfcorpus --max-samples 50

# Run LongMemEval memory evaluation
python longmemeval_example.py --local-path ./data/longmemeval.jsonl --max-samples 20

# Run custom adapter patterns demo
python custom_adapter_example.py
```

## Files

| File | Description |
|------|-------------|
| `beir_eval_example.py` | BEIR benchmark retrieval evaluation (nDCG@k, Recall@k, MRR) |
| `longmemeval_example.py` | LongMemEval long-term memory evaluation (QA, temporal, update, abstention) |
| `custom_adapter_example.py` | Three patterns for connecting any service via adapters |
| `config_beir.json` | Sample config for BEIR evaluation |
| `config_memory.json` | Sample config for memory evaluation |

## Connecting to Your Service

### Pattern 1: HTTP REST API

```python
from agent_eval.context_memory import RESTServiceAdapter, BEIRLoader, ContextMemoryEvalHarness

adapter = RESTServiceAdapter(
    base_url="http://your-service:8080",
    endpoints={
        "retrieve": "/api/v1/retrieve",
        "store_memory": "/api/v1/memory/store",
        "query_memory": "/api/v1/memory/query",
        "compress": "/api/v1/compress",
        "answer": "/api/v1/answer",
    },
    headers={"Authorization": "Bearer <token>"},
)

tasks = BEIRLoader().load(local_path="./data/nfcorpus", max_samples=100)
report = ContextMemoryEvalHarness(adapter=adapter).run_retrieval(tasks)
print(report.summary())
```

### Pattern 2: Python SDK / Local Function

```python
from agent_eval.context_memory import LocalFunctionAdapter, MemoryAnswer

import my_memory_sdk  # your own SDK

adapter = LocalFunctionAdapter(
    store_fn=lambda sid, hist: my_memory_sdk.store(sid, hist),
    query_fn=lambda sid, q: MemoryAnswer(task_id="", answer=my_memory_sdk.query(sid, q)),
)
```

### Pattern 3: Full Custom Adapter

Implement any combination of the three Protocol interfaces:

```python
class MyAdapter:
    def retrieve(self, query, corpus, top_k): ...         # RetrievalServiceAdapter
    def store_memory(self, session_id, history): ...      # MemoryServiceAdapter
    def query_memory(self, session_id, question): ...     # MemoryServiceAdapter
    def compress_context(self, documents, budget): ...    # ContextQualityServiceAdapter
    def answer_with_context(self, context, question): ... # ContextQualityServiceAdapter
```

The harness auto-routes tasks to the appropriate methods.

## Supported Benchmarks

| Benchmark | Tasks | Key Metrics |
|-----------|-------|-------------|
| BEIR | Retrieval | nDCG@10, Recall@10, MRR |
| LongMemEval | Memory (QA, temporal, update, abstention) | Token F1, abstention accuracy |
| LongBench v2 | Long-context QA / summarization | Token F1 |
| LoCoMo | Conversational memory | Token F1 |
| RULER | Needle-in-haystack, long-context | Token F1 |

## Self-Built Scenarios

The module includes 7 self-built scenario suites covering use cases not fully addressed by external benchmarks:

| Scenario | UC | Description |
|----------|----|-------------|
| `multi_source` | UC001 | Multi-source information aggregation |
| `memory_tiers` | UC002 | Hot/warm/cold memory tier management |
| `context_exposure` | UC006 | Context exposure control (PII/confidentiality) |
| `compression` | UC009 | Context compression and summarization |
| `working_memory` | UC010 | Working memory state tracking |
| `tool_context` | UC011 | Tool call context governance |
| `sub_agent` | UC014 | Sub-agent context isolation |

```python
from agent_eval.context_memory import get_all_self_built_tasks, ContextMemoryEvalHarness

tasks = get_all_self_built_tasks()
report = ContextMemoryEvalHarness(adapter=my_adapter).run(tasks)
print(f"Pass rate: {report.pass_rate:.1%}")
```

## Eval Modes

| Mode | Description | Max Samples |
|------|-------------|-------------|
| `EvalMode.OFFLINE` | Full benchmark evaluation | Unlimited |
| `EvalMode.REGRESSION` | CI/CD smoke test | 20 (default) |
| `EvalMode.STRESS` | Load / long-context stress test | Unlimited |

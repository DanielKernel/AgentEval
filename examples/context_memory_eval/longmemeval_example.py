"""
LongMemEval long-term memory evaluation example.

Tests a memory service's ability to answer questions about long conversation histories.

Usage:
    python longmemeval_example.py --local-path ./data/longmemeval.jsonl --max-samples 20

With a REST endpoint:
    python longmemeval_example.py --base-url http://localhost:8080 --token Bearer MY_TOKEN
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_eval.context_memory import (
    ContextMemoryEvalHarness,
    EvalMode,
    LocalFunctionAdapter,
    LongMemEvalLoader,
    MemoryAnswer,
    MemoryTaskType,
    MockAdapter,
    RESTServiceAdapter,
)


def parse_args():
    parser = argparse.ArgumentParser(description="LongMemEval memory eval example")
    parser.add_argument("--local-path", help="Path to local LongMemEval JSONL file")
    parser.add_argument("--base-url", default="http://localhost:8080")
    parser.add_argument("--token", help="Authorization header value")
    parser.add_argument("--max-samples", type=int, default=20)
    parser.add_argument("--task-type", choices=["all", "qa", "temporal", "update", "abstention"], default="all")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Load tasks ──────────────────────────────────────────────────────────
    loader = LongMemEvalLoader()
    all_tasks = loader.load(local_path=args.local_path, max_samples=args.max_samples)

    # Filter by task type if requested
    type_map = {
        "qa": MemoryTaskType.QA,
        "temporal": MemoryTaskType.TEMPORAL,
        "update": MemoryTaskType.UPDATE,
        "abstention": MemoryTaskType.ABSTENTION,
    }
    if args.task_type != "all":
        target_type = type_map[args.task_type]
        tasks = [t for t in all_tasks if t.task_type == target_type]
    else:
        tasks = all_tasks

    print(f"Loaded {len(tasks)} memory tasks (type filter: {args.task_type})")
    if not tasks:
        print("No tasks to evaluate.")
        return

    # ── Connect to service ──────────────────────────────────────────────────
    if args.local_path:
        # Demo: naive in-memory store
        sessions = {}

        def store_fn(session_id, history):
            sessions[session_id] = history

        def query_fn(session_id, question):
            history = sessions.get(session_id, [])
            # Very naive: search for any content that could answer the question
            for turn in reversed(history):
                if any(w in turn.content.lower() for w in question.lower().split()):
                    return MemoryAnswer(task_id="", answer=turn.content)
            return MemoryAnswer(task_id="", answer="I don't know")

        adapter = LocalFunctionAdapter(store_fn=store_fn, query_fn=query_fn)
    else:
        headers = {}
        if args.token:
            headers["Authorization"] = args.token
        adapter = RESTServiceAdapter(
            base_url=args.base_url,
            endpoints={
                "store_memory": "/api/v1/memory/store",
                "query_memory": "/api/v1/memory/query",
            },
            headers=headers,
        )

    # ── Run evaluation ──────────────────────────────────────────────────────
    harness = ContextMemoryEvalHarness(adapter=adapter, mode=EvalMode.OFFLINE)
    report = harness.run_memory(tasks)

    # ── Print results ───────────────────────────────────────────────────────
    summary = report.summary()
    print("\n=== LongMemEval Memory Evaluation Report ===")
    print(json.dumps(summary, indent=2))
    print(f"\nPass rate: {report.pass_rate:.1%} ({report.passed_tasks}/{report.total_tasks} tasks)")

    # Task type breakdown
    by_type: dict = {}
    for result in report.results:
        tt = result.metadata.get("task_type", "unknown")
        if tt not in by_type:
            by_type[tt] = {"passed": 0, "total": 0}
        by_type[tt]["total"] += 1
        if result.passed:
            by_type[tt]["passed"] += 1

    if by_type:
        print("\n--- Breakdown by task type ---")
        for tt, counts in by_type.items():
            rate = counts["passed"] / counts["total"] if counts["total"] else 0
            print(f"  {tt}: {rate:.1%} ({counts['passed']}/{counts['total']})")


if __name__ == "__main__":
    main()

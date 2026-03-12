"""
BEIR retrieval evaluation example.

Uses RESTServiceAdapter to connect to any retrieval service (e.g., ContextAgent),
or LocalFunctionAdapter for local evaluation.

Usage:
    pip install agent-eval[datasets]
    python beir_eval_example.py --local-path ./data/nfcorpus --max-samples 50

With a live REST endpoint:
    python beir_eval_example.py --base-url http://localhost:8080 --token Bearer MY_TOKEN
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent to path if running from examples dir
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_eval.context_memory import (
    BEIRLoader,
    ContextMemoryEvalHarness,
    EvalMode,
    LocalFunctionAdapter,
    RESTServiceAdapter,
)


def parse_args():
    parser = argparse.ArgumentParser(description="BEIR retrieval eval example")
    parser.add_argument("--local-path", help="Path to local BEIR dataset directory")
    parser.add_argument("--base-url", default="http://localhost:8080", help="REST service base URL")
    parser.add_argument("--token", help="Authorization header value (e.g. 'Bearer xyz')")
    parser.add_argument("--max-samples", type=int, default=50)
    parser.add_argument("--split", default="test")
    parser.add_argument("--mode", choices=["offline", "regression"], default="offline")
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Load benchmark tasks ────────────────────────────────────────────────
    loader = BEIRLoader()
    tasks = loader.load(
        local_path=args.local_path,
        split=args.split,
        max_samples=args.max_samples,
    )
    print(f"Loaded {len(tasks)} retrieval tasks from BEIR")

    # ── Connect to target service ───────────────────────────────────────────
    if args.local_path and not args.base_url:
        # Demo: use a trivial BM25-style local retriever
        from agent_eval.context_memory import RankedDocument

        def local_retrieve(query, corpus, top_k):
            query_words = set(query.lower().split())
            scored = []
            for doc in corpus:
                words = set(doc.text.lower().split())
                score = len(query_words & words) / max(len(query_words), 1)
                scored.append((score, doc.doc_id))
            scored.sort(reverse=True)
            return [
                RankedDocument(doc_id=did, score=s, rank=i + 1)
                for i, (s, did) in enumerate(scored[:top_k])
            ]

        from agent_eval.context_memory import LocalFunctionAdapter
        adapter = LocalFunctionAdapter(retrieve_fn=local_retrieve)
    else:
        headers = {}
        if args.token:
            headers["Authorization"] = args.token
        adapter = RESTServiceAdapter(
            base_url=args.base_url,
            endpoints={"retrieve": "/api/v1/context/retrieve"},
            headers=headers,
        )

    # ── Run evaluation ──────────────────────────────────────────────────────
    mode = EvalMode.REGRESSION if args.mode == "regression" else EvalMode.OFFLINE
    harness = ContextMemoryEvalHarness(adapter=adapter, mode=mode)
    report = harness.run_retrieval(tasks)

    # ── Print results ───────────────────────────────────────────────────────
    summary = report.summary()
    print("\n=== BEIR Retrieval Evaluation Report ===")
    print(json.dumps(summary, indent=2))
    print(f"\nPass rate: {report.pass_rate:.1%} ({report.passed_tasks}/{report.total_tasks} tasks)")

    # Show per-metric averages
    for metric_name in ["ndcg_at_k", "recall_at_k", "mrr"]:
        value = report.aggregate_metric(metric_name)
        if value is not None:
            print(f"  {metric_name}: {value:.4f}")


if __name__ == "__main__":
    main()

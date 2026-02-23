"""Command-line interface for AgentEval."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from agent_eval.models import Criterion, EvalTask
from agent_eval.evaluator import AgentEvaluator, contains_keywords, exact_match


def _build_evaluator(config: Dict[str, Any]) -> AgentEvaluator:
    criteria = [
        Criterion(
            name=c["name"],
            description=c.get("description", ""),
            weight=c.get("weight", 1.0),
            passing_threshold=c.get("passing_threshold", 0.5),
        )
        for c in config.get("criteria", [])
    ]
    if not criteria:
        raise SystemExit("Config must contain at least one criterion under 'criteria'.")

    scoring_fns = {}
    for c in config.get("criteria", []):
        name = c["name"]
        fn_type = c.get("scoring_function", "exact_match")
        if fn_type == "exact_match":
            scoring_fns[name] = exact_match
        elif fn_type == "contains_keywords":
            keywords = c.get("keywords")
            if not keywords:
                raise SystemExit(
                    f"Criterion '{name}' uses contains_keywords but no 'keywords' list provided."
                )
            scoring_fns[name] = contains_keywords(keywords)
        else:
            raise SystemExit(f"Unknown scoring_function '{fn_type}' for criterion '{name}'.")

    return AgentEvaluator(criteria=criteria, scoring_functions=scoring_fns)


def _load_tasks(tasks_data: List[Dict[str, Any]]) -> List[EvalTask]:
    return [
        EvalTask(
            task_id=t["task_id"],
            input=t["input"],
            expected_output=t.get("expected_output"),
            metadata=t.get("metadata", {}),
        )
        for t in tasks_data
    ]


def run(args: argparse.Namespace) -> None:
    with open(args.config) as fh:
        config: Dict[str, Any] = json.load(fh)

    with open(args.tasks) as fh:
        tasks_data: List[Dict[str, Any]] = json.load(fh)

    with open(args.outputs) as fh:
        outputs_data: List[Dict[str, Any]] = json.load(fh)

    evaluator = _build_evaluator(config)
    tasks = _load_tasks(tasks_data)
    agent_outputs = [o["output"] for o in outputs_data]

    results = evaluator.evaluate_batch(tasks, agent_outputs)

    if args.results_file:
        with open(args.results_file, "w") as fh:
            json.dump([r.to_dict() for r in results], fh, indent=2)
        print(f"Results written to {args.results_file}")

    summary = evaluator.summary(results)
    print(json.dumps(summary, indent=2))

    if not all(r.passed for r in results):
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description="Evaluate AI agent outputs against defined criteria.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to a JSON config file defining evaluation criteria.",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Path to a JSON file containing the list of eval tasks.",
    )
    parser.add_argument(
        "--outputs",
        required=True,
        help="Path to a JSON file containing the agent's outputs (same order as tasks).",
    )
    parser.add_argument(
        "--results-file",
        dest="results_file",
        default=None,
        help="Optional path to write per-task results as JSON.",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()

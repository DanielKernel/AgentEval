"""Command-line interface for AgentEval.

Supports two config formats:
- Legacy evaluator mode (config has "criteria")
- Conversation harness mode (config has "graders")
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, List

from agent_eval.conversation import (
    ConversationEvalHarness,
    ConversationTask,
    KeywordGrader,
    MaxTurnsGrader,
    RegexGrader,
    StringMatchGrader,
)
from agent_eval.conversation.agent_factory import build_agent
from agent_eval.conversation.graders import Grader
from agent_eval.evaluator import (
    AgentEvaluator,
    contains_keywords,
    exact_match,
    length_check,
    regex_match,
)
from agent_eval.models import Criterion, EvalTask


_REGEX_FLAGS = {
    "IGNORECASE": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "ASCII": re.ASCII,
}


# ---------------------------------------------------------------------------
# Legacy evaluator mode helpers
# ---------------------------------------------------------------------------


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
        elif fn_type == "length_check":
            raw_min_words = c.get("min_words", 0)
            try:
                min_words = int(raw_min_words)
            except (TypeError, ValueError) as exc:
                raise SystemExit(
                    f"Criterion '{name}' has invalid min_words value "
                    f"{raw_min_words!r}: {exc}"
                ) from exc

            raw_max_words = c.get("max_words")
            if raw_max_words is None:
                max_words = None
            else:
                try:
                    max_words = int(raw_max_words)
                except (TypeError, ValueError) as exc:
                    raise SystemExit(
                        f"Criterion '{name}' has invalid max_words value "
                        f"{raw_max_words!r}: {exc}"
                    ) from exc

            scoring_fns[name] = length_check(min_words=min_words, max_words=max_words)
        elif fn_type == "regex_match":
            pattern = c.get("pattern")
            if not pattern:
                raise SystemExit(
                    f"Criterion '{name}' uses regex_match but no 'pattern' provided."
                )
            scoring_fns[name] = regex_match(
                pattern=pattern,
                flags=_parse_regex_flags(c.get("flags")),
            )
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


def _parse_regex_flags(raw_flags: Any) -> int:
    """Parse regex flags from config.

    Supports:
    - omitted or null -> IGNORECASE
    - string: "IGNORECASE|MULTILINE"
    - list: ["IGNORECASE", "MULTILINE"]
    """
    if raw_flags is None:
        return re.IGNORECASE

    if isinstance(raw_flags, int):
        return raw_flags

    if isinstance(raw_flags, str):
        names = [part.strip().upper() for part in raw_flags.split("|") if part.strip()]
    elif isinstance(raw_flags, list):
        names = [str(part).strip().upper() for part in raw_flags if str(part).strip()]
    else:
        raise SystemExit("regex flags must be an int, string, list of strings, or omitted.")

    if not names:
        return 0

    combined = 0
    for name in names:
        if name not in _REGEX_FLAGS:
            valid = ", ".join(sorted(_REGEX_FLAGS))
            raise SystemExit(f"Unknown regex flag '{name}'. Valid values: {valid}")
        combined |= _REGEX_FLAGS[name]
    return combined


def _normalise_single_trial(trial: Any) -> Dict[str, Any]:
    """Normalise one trial object from outputs.json."""
    if isinstance(trial, str):
        return {
            "output": trial,
            "seed": None,
            "transcript": None,
            "outcome": None,
            "error": "",
        }

    if not isinstance(trial, dict):
        raise SystemExit(
            "Each output entry must be a string or an object with an 'output' key."
        )

    if "output" not in trial:
        raise SystemExit("Output object must include an 'output' field.")

    seed = trial.get("seed")
    if seed is not None:
        try:
            seed = int(seed)
        except (TypeError, ValueError) as exc:
            raise SystemExit(f"Invalid seed value {seed!r}: {exc}") from exc

    transcript = trial.get("transcript")
    if transcript is not None and not isinstance(transcript, list):
        raise SystemExit("Optional 'transcript' must be a list when provided.")

    outcome = trial.get("outcome")
    if outcome is not None and not isinstance(outcome, dict):
        outcome = {"value": outcome}

    return {
        "output": str(trial["output"]),
        "seed": seed,
        "transcript": transcript,
        "outcome": outcome,
        "error": str(trial.get("error", "")),
    }


def _parse_outputs(outputs_data: List[Any], requested_trials: int) -> Dict[str, Any]:
    """Parse outputs.json into single-trial or multi-trial structures."""
    if requested_trials <= 0:
        raise SystemExit(f"--trials must be positive, got {requested_trials!r}")

    outputs_by_task: List[List[str]] = []
    seeds_by_task: List[List[Any]] = []
    transcripts_by_task: List[List[Any]] = []
    outcomes_by_task: List[List[Any]] = []
    errors_by_task: List[List[str]] = []

    for entry in outputs_data:
        if isinstance(entry, dict) and "outputs" in entry:
            raw_trials = entry["outputs"]
            if not isinstance(raw_trials, list):
                raise SystemExit("When present, 'outputs' must be a list.")
        else:
            raw_trials = [entry]

        if len(raw_trials) < requested_trials:
            raise SystemExit(
                f"Requested {requested_trials} trials, but found only "
                f"{len(raw_trials)} trial(s) for one task in outputs.json."
            )

        normalised_trials = [
            _normalise_single_trial(raw_trial)
            for raw_trial in raw_trials[:requested_trials]
        ]

        outputs_by_task.append([trial["output"] for trial in normalised_trials])
        seeds_by_task.append([trial["seed"] for trial in normalised_trials])
        transcripts_by_task.append([trial["transcript"] for trial in normalised_trials])
        outcomes_by_task.append([trial["outcome"] for trial in normalised_trials])
        errors_by_task.append([trial["error"] for trial in normalised_trials])

    is_trial_mode = requested_trials > 1 or any(
        len(task_outputs) > 1 for task_outputs in outputs_by_task
    )

    return {
        "is_trial_mode": is_trial_mode,
        "single_outputs": [task_outputs[0] for task_outputs in outputs_by_task],
        "outputs_by_task": outputs_by_task,
        "seeds_by_task": seeds_by_task,
        "transcripts_by_task": transcripts_by_task,
        "outcomes_by_task": outcomes_by_task,
        "errors_by_task": errors_by_task,
    }


def _run_legacy_mode(config: Dict[str, Any], args: argparse.Namespace) -> None:
    if not args.outputs:
        raise SystemExit("Legacy criteria mode requires --outputs.")

    with open(args.tasks, encoding="utf-8") as fh:
        tasks_data: List[Dict[str, Any]] = json.load(fh)
    with open(args.outputs, encoding="utf-8") as fh:
        outputs_data: List[Any] = json.load(fh)

    if len(tasks_data) != len(outputs_data):
        raise SystemExit(
            f"tasks and outputs must have the same length "
            f"({len(tasks_data)} vs {len(outputs_data)})"
        )

    evaluator = _build_evaluator(config)
    tasks = _load_tasks(tasks_data)
    parsed_outputs = _parse_outputs(outputs_data, requested_trials=args.trials)

    if parsed_outputs["is_trial_mode"]:
        task_trial_results = evaluator.evaluate_batch_trials(
            tasks=tasks,
            outputs_by_task=parsed_outputs["outputs_by_task"],
            seeds_by_task=parsed_outputs["seeds_by_task"],
            transcripts_by_task=parsed_outputs["transcripts_by_task"],
            outcomes_by_task=parsed_outputs["outcomes_by_task"],
            errors_by_task=parsed_outputs["errors_by_task"],
        )

        if args.results_file:
            with open(args.results_file, "w", encoding="utf-8") as fh:
                json.dump([r.to_dict() for r in task_trial_results], fh, indent=2)
            print(f"Results written to {args.results_file}")

        summary = evaluator.trial_summary(task_trial_results)
        print(json.dumps(summary, indent=2))

        if args.require_all_trials:
            passed = all(r.pass_hat_k == 1.0 for r in task_trial_results)
        else:
            passed = all(r.pass_at_k == 1.0 for r in task_trial_results)

        if not passed:
            sys.exit(1)
        return

    results = evaluator.evaluate_batch(tasks, parsed_outputs["single_outputs"])
    if args.results_file:
        with open(args.results_file, "w", encoding="utf-8") as fh:
            json.dump([r.to_dict() for r in results], fh, indent=2)
        print(f"Results written to {args.results_file}")

    summary = evaluator.summary(results)
    print(json.dumps(summary, indent=2))
    if not all(r.passed for r in results):
        sys.exit(1)


# ---------------------------------------------------------------------------
# Conversation mode helpers
# ---------------------------------------------------------------------------


def _load_conversation_tasks(path: str) -> List[ConversationTask]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [
        ConversationTask(
            task_id=t["task_id"],
            initial_user_message=t["initial_user_message"],
            expected_outcome=t.get("expected_outcome"),
            success_criteria=t.get("success_criteria"),
            max_turns=t.get("max_turns", 20),
            metadata=t.get("metadata", {}),
        )
        for t in data
    ]


def _build_graders(config: Dict[str, Any]) -> List[Grader]:
    graders: List[Grader] = []
    for g in config.get("graders", []):
        grader_type = g.get("type")
        name = g.get("name", grader_type)
        weight = g.get("weight", 1.0)

        if grader_type == "string_match":
            graders.append(StringMatchGrader(name=name, weight=weight))
        elif grader_type == "regex":
            graders.append(
                RegexGrader(name=name, pattern=g.get("pattern", ""), weight=weight)
            )
        elif grader_type == "keyword":
            graders.append(
                KeywordGrader(
                    name=name,
                    keywords=g.get("keywords", []),
                    require_all=g.get("require_all", False),
                    weight=weight,
                )
            )
        elif grader_type == "max_turns":
            graders.append(
                MaxTurnsGrader(
                    name=name,
                    max_turns=g.get("max_turns", 20),
                    weight=weight,
                )
            )
        else:
            raise SystemExit(f"Unknown grader type: {grader_type!r}")
    return graders


def _resolve_agents(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    if config.get("agents"):
        return {c["id"]: c for c in config["agents"] if c.get("id")}

    return {
        "default": {
            "id": "default",
            "type": args.agent,
            "params": {"response": args.fixed_response} if args.agent == "fixed" else {},
        }
    }


def _run_conversation_mode(config: Dict[str, Any], args: argparse.Namespace) -> None:
    tasks = _load_conversation_tasks(args.tasks)
    graders = _build_graders(config)
    if not graders:
        raise SystemExit("Config must contain at least one grader under 'graders'.")

    agent_configs = _resolve_agents(config, args)
    if not agent_configs:
        raise SystemExit(
            "Config must contain at least one agent under 'agents', or use --agent."
        )

    harness_kw = {
        "graders": graders,
        "n_trials": config.get("n_trials", 3),
        "pass_k_param": config.get("pass_k_param", 3),
        "seed": config.get("seed"),
    }

    results_by_agent: Dict[str, Dict[str, Any]] = {}
    all_passed = True

    for agent_id, agent_cfg in agent_configs.items():
        try:
            agent = build_agent(agent_cfg)
        except Exception as exc:
            raise SystemExit(f"Failed to build agent {agent_id!r}: {exc}") from exc

        harness = ConversationEvalHarness(agent=agent, **harness_kw)
        results = harness.run_evaluation(tasks)
        summary = harness.summary(results)

        results_by_agent[agent_id] = {
            "summary": summary,
            "results": [r.to_dict() for r in results],
        }
        if summary.get("tasks_all_passed", 0) != len(tasks):
            all_passed = False

        print(f"\n=== Agent: {agent_id} ===")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if args.verbose:
            for r in results:
                print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))

    if len(results_by_agent) > 1:
        print("\n=== Multi-agent comparison ===")
        for agent_id, data in results_by_agent.items():
            summary = data["summary"]
            print(
                f"  {agent_id}: pass_rate={summary.get('overall_pass_rate', 0):.2%} "
                f"tasks_all_passed={summary.get('tasks_all_passed', 0)}/"
                f"{summary.get('total_tasks', 0)} "
                f"mean_score={summary.get('mean_score', 0):.2f}"
            )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump({"agents": results_by_agent}, f, indent=2, ensure_ascii=False)
        print(f"\nResults written to {args.output}")

    if not all_passed:
        sys.exit(1)


def _is_legacy_config(config: Dict[str, Any]) -> bool:
    if "criteria" in config:
        return True
    if "graders" in config:
        return False
    raise SystemExit(
        "Config must contain either 'criteria' (legacy mode) or 'graders' "
        "(conversation mode)."
    )


def run(args: argparse.Namespace) -> None:
    with open(args.config, encoding="utf-8") as fh:
        config: Dict[str, Any] = json.load(fh)

    if _is_legacy_config(config):
        _run_legacy_mode(config, args)
    else:
        _run_conversation_mode(config, args)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description=(
            "AgentEval CLI. Supports legacy criteria mode and conversation "
            "graders mode."
        ),
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to a JSON config file.",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Path to tasks JSON.",
    )

    # Legacy mode arguments.
    parser.add_argument(
        "--outputs",
        default=None,
        help=(
            "Legacy mode only: path to agent outputs JSON "
            "(same order as tasks)."
        ),
    )
    parser.add_argument(
        "--results-file",
        dest="results_file",
        default=None,
        help="Legacy mode only: optional path to write per-task results JSON.",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=1,
        help=(
            "Legacy mode only: number of trials to evaluate from outputs.json. "
            "When >1, outputs entries must contain enough trial outputs."
        ),
    )
    parser.add_argument(
        "--require-all-trials",
        action="store_true",
        help=(
            "Legacy mode only: require pass^k (all trials pass). "
            "Default checks pass@k (at least one trial passes)."
        ),
    )

    # Conversation mode arguments.
    parser.add_argument(
        "--output",
        default=None,
        help="Conversation mode only: optional path to write results JSON.",
    )
    parser.add_argument(
        "--agent",
        default="echo",
        choices=["echo", "fixed"],
        help="Conversation mode fallback agent type when config has no agents.",
    )
    parser.add_argument(
        "--fixed-response",
        default="This is a fixed response.",
        help="Conversation mode: response text for --agent=fixed.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Conversation mode: print per-task detailed results.",
    )

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()

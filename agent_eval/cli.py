"""Command-line interface for AgentEval（对话 Agent 评测，支持多被测 Agent）。"""

from __future__ import annotations

import argparse
import json
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


def _load_tasks(path: str) -> List[ConversationTask]:
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
        t = g.get("type")
        name = g.get("name", t)
        weight = g.get("weight", 1.0)
        if t == "string_match":
            graders.append(StringMatchGrader(name=name, weight=weight))
        elif t == "regex":
            graders.append(
                RegexGrader(name=name, pattern=g.get("pattern", ""), weight=weight)
            )
        elif t == "keyword":
            graders.append(
                KeywordGrader(
                    name=name,
                    keywords=g.get("keywords", []),
                    require_all=g.get("require_all", False),
                    weight=weight,
                )
            )
        elif t == "max_turns":
            graders.append(
                MaxTurnsGrader(
                    name=name,
                    max_turns=g.get("max_turns", 20),
                    weight=weight,
                )
            )
        else:
            raise SystemExit(f"Unknown grader type: {t!r}")
    return graders


def _resolve_agents(config: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    """确定要评测的 agent 列表。优先使用 config.agents，否则用 CLI --agent/--fixed-response 生成单条。"""
    if config.get("agents"):
        return {c["id"]: c for c in config["agents"] if c.get("id")}
    # 兼容：无 agents 时用命令行指定单个 agent
    return {
        "default": {
            "id": "default",
            "type": args.agent,
            "params": {"response": args.fixed_response} if args.agent == "fixed" else {},
        }
    }


def run(args: argparse.Namespace) -> None:
    with open(args.config, encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    tasks = _load_tasks(args.tasks)
    graders = _build_graders(config)
    if not graders:
        raise SystemExit("Config must contain at least one grader under 'graders'.")

    agent_configs = _resolve_agents(config, args)
    if not agent_configs:
        raise SystemExit("Config must contain at least one agent under 'agents', or use --agent.")

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
        except Exception as e:
            raise SystemExit(f"Failed to build agent {agent_id!r}: {e}") from e

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
        print("\n=== 多 Agent 对比 ===")
        for agent_id, data in results_by_agent.items():
            s = data["summary"]
            print(
                f"  {agent_id}: pass_rate={s.get('overall_pass_rate', 0):.2%} "
                f"tasks_all_passed={s.get('tasks_all_passed', 0)}/{s.get('total_tasks', 0)} "
                f"mean_score={s.get('mean_score', 0):.2f}"
            )

    if args.output:
        out = {
            "agents": results_by_agent,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\n结果已写入 {args.output}")

    if not all_passed:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agent-eval",
        description="对话类 Agent 自动化评测（支持配置多个被测 Agent）。",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="评测配置 JSON（含 agents、graders、n_trials、pass_k_param 等）。",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="任务 JSON（含 task_id、initial_user_message、expected_outcome、max_turns 等）。",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="结果输出 JSON 路径（可选）。",
    )
    parser.add_argument(
        "--agent",
        default="echo",
        choices=["echo", "fixed"],
        help="当 config 中无 agents 时使用的内置 Agent 类型。",
    )
    parser.add_argument(
        "--fixed-response",
        default="这是固定回复。",
        help="当 --agent=fixed 时的助手回复内容。",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="打印各任务详细结果。",
    )
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()

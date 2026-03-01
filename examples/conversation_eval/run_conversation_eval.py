#!/usr/bin/env python3
"""运行对话类 Agent 自动化评测示例。

用法:
  # 使用示例 EchoAgent（单任务用 exact_match 会通过）
  python run_conversation_eval.py --tasks tasks.json --config config.json

  # 指定输出
  python run_conversation_eval.py --tasks tasks.json --config config.json --output results.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 将项目根加入 path（脚本在 examples/conversation_eval/ 下）
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parents[1]
sys.path.insert(0, str(_PROJECT_ROOT))

from agent_eval.conversation import (
    ConversationEvalHarness,
    ConversationTask,
    KeywordGrader,
    MaxTurnsGrader,
    RegexGrader,
    StringMatchGrader,
)
from agent_eval.conversation.sample_agent import EchoAgent, FixedResponseAgent


def load_tasks(path: str) -> list[ConversationTask]:
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


def build_graders_from_config(config: dict) -> list:
    graders = []
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
            raise ValueError(f"Unknown grader type: {t}")
    return graders


def main():
    import argparse
    parser = argparse.ArgumentParser(description="对话 Agent 自动化评测")
    parser.add_argument("--tasks", required=True, help="任务 JSON 路径")
    parser.add_argument("--config", required=True, help="评测配置 JSON 路径")
    parser.add_argument("--output", default=None, help="结果输出 JSON 路径")
    parser.add_argument("--agent", default="echo", choices=["echo", "fixed"], help="示例 Agent 类型")
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    graders = build_graders_from_config(config)
    if not graders:
        print("未配置任何 grader，退出。")
        sys.exit(1)

    if args.agent == "echo":
        agent = EchoAgent()
    else:
        agent = FixedResponseAgent(response="这是固定回复。")

    harness = ConversationEvalHarness(
        agent=agent,
        graders=graders,
        n_trials=config.get("n_trials", 3),
        pass_k_param=config.get("pass_k_param", 3),
        seed=config.get("seed"),
    )

    results = harness.run_evaluation(tasks)
    summary = harness.summary(results)

    print("=== 评测汇总 ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("\n=== 各任务结果 ===")
    for r in results:
        print(json.dumps(r.to_dict(), indent=2, ensure_ascii=False))

    if args.output:
        out = {
            "summary": summary,
            "results": [r.to_dict() for r in results],
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print(f"\n结果已写入 {args.output}")

    sys.exit(0 if summary.get("tasks_all_passed", 0) == len(tasks) else 1)


if __name__ == "__main__":
    main()

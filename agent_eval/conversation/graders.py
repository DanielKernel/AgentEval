"""评估器（Grader）：代码评估器与可选的模型评估器。"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from agent_eval.conversation.models import (
    Assertion,
    ConversationTask,
    GradingResult,
    Transcript,
)


class Grader(ABC):
    """评估器基类：对 (transcript, outcome, context) 打分。"""

    def __init__(self, name: str, weight: float = 1.0):
        self.name = name
        self.weight = weight

    @abstractmethod
    def grade(
        self,
        transcript: Transcript,
        outcome: Any,
        context: Dict[str, Any],
    ) -> GradingResult:
        """对一次试验的转录与结果进行评分。"""
        ...


# ---------------------------------------------------------------------------
# 代码评估器（Code-Based Graders）
# ---------------------------------------------------------------------------


class StringMatchGrader(Grader):
    """字符串匹配：最后一条助手回复与预期完全一致（忽略大小写与首尾空白）。"""

    def __init__(
        self,
        name: str = "string_match",
        expected_key: str = "expected_outcome",
        weight: float = 1.0,
    ):
        super().__init__(name=name, weight=weight)
        self.expected_key = expected_key

    def grade(
        self,
        transcript: Transcript,
        outcome: Any,
        context: Dict[str, Any],
    ) -> GradingResult:
        task: Optional[ConversationTask] = context.get("task")
        expected = None
        if task and getattr(task, self.expected_key, None):
            expected = getattr(task, self.expected_key)
        if expected is None:
            expected = context.get(self.expected_key, "")

        actual = transcript.get_last_assistant_turn() or ""
        passed = actual.strip().lower() == (expected or "").strip().lower()
        return GradingResult(
            grader_name=self.name,
            passed=passed,
            score=1.0 if passed else 0.0,
            assertions=[
                Assertion(
                    description="最后回复与预期一致",
                    passed=passed,
                    evidence=f"expected: {expected!r}, actual: {actual!r}",
                )
            ],
        )


class RegexGrader(Grader):
    """正则匹配：最后一条助手回复中是否出现给定模式。"""

    def __init__(
        self,
        name: str = "regex_match",
        pattern: str = "",
        flags: int = re.IGNORECASE,
        weight: float = 1.0,
    ):
        super().__init__(name=name, weight=weight)
        self.pattern = re.compile(pattern, flags) if pattern else None

    def grade(
        self,
        transcript: Transcript,
        outcome: Any,
        context: Dict[str, Any],
    ) -> GradingResult:
        if not self.pattern:
            return GradingResult(
                grader_name=self.name,
                passed=False,
                score=0.0,
                assertions=[Assertion(description="未配置 pattern", passed=False, evidence="")],
            )
        text = transcript.get_last_assistant_turn() or ""
        found = self.pattern.search(text) is not None
        return GradingResult(
            grader_name=self.name,
            passed=found,
            score=1.0 if found else 0.0,
            assertions=[
                Assertion(
                    description=f"匹配模式 {self.pattern.pattern!r}",
                    passed=found,
                    evidence=text[:200] + ("..." if len(text) > 200 else ""),
                )
            ],
        )


class KeywordGrader(Grader):
    """关键词覆盖：助手回复中需包含所有/部分关键词，按比例给分。"""

    def __init__(
        self,
        name: str = "keyword",
        keywords: List[str] = None,
        require_all: bool = False,
        weight: float = 1.0,
    ):
        super().__init__(name=name, weight=weight)
        self.keywords = [k.lower() for k in (keywords or [])]
        self.require_all = require_all

    def grade(
        self,
        transcript: Transcript,
        outcome: Any,
        context: Dict[str, Any],
    ) -> GradingResult:
        if not self.keywords:
            return GradingResult(
                grader_name=self.name,
                passed=False,
                score=0.0,
                assertions=[Assertion(description="未配置 keywords", passed=False, evidence="")],
            )
        text = (transcript.get_assistant_text() or "").lower()
        hits = sum(1 for kw in self.keywords if kw in text)
        score = hits / len(self.keywords)
        passed = (self.require_all and hits == len(self.keywords)) or (
            not self.require_all and hits > 0
        )
        return GradingResult(
            grader_name=self.name,
            passed=passed,
            score=score,
            assertions=[
                Assertion(
                    description=f"关键词覆盖 {hits}/{len(self.keywords)}",
                    passed=passed,
                    evidence=f"keywords: {self.keywords}",
                )
            ],
        )


class MaxTurnsGrader(Grader):
    """轮次上限：对话轮数不超过 max_turns（效率维度）。"""

    def __init__(self, name: str = "max_turns", max_turns: int = 20, weight: float = 0.5):
        super().__init__(name=name, weight=weight)
        self.max_turns = max_turns

    def grade(
        self,
        transcript: Transcript,
        outcome: Any,
        context: Dict[str, Any],
    ) -> GradingResult:
        n = transcript.turn_count()
        passed = n <= self.max_turns
        score = 1.0 if n == 0 else max(0.0, 1.0 - (n - self.max_turns) / max(1, self.max_turns))
        score = max(0.0, min(1.0, score))
        return GradingResult(
            grader_name=self.name,
            passed=passed,
            score=score,
            assertions=[
                Assertion(
                    description=f"轮次 {n} <= {self.max_turns}",
                    passed=passed,
                    evidence=f"turns={n}",
                )
            ],
        )


# ---------------------------------------------------------------------------
# 模型评估器（Model-Based Grader，LLM-as-Judge）
# ---------------------------------------------------------------------------

LLMJudgeFn = Callable[[str, str, str], Dict[str, Any]]


class LLMRubricGrader(Grader):
    """LLM 作为裁判：根据 rubric 对 transcript 打分。

    不依赖具体 API，通过注入 judge_fn 实现。judge_fn(transcript_text, rubric, task_description)
    应返回 {"passed": bool, "score": float, "reasoning": str} 或类似结构。
    """

    def __init__(
        self,
        name: str = "llm_rubric",
        rubric: str = "",
        judge_fn: Optional[LLMJudgeFn] = None,
        weight: float = 1.0,
    ):
        super().__init__(name=name, weight=weight)
        self.rubric = rubric
        self.judge_fn = judge_fn

    def grade(
        self,
        transcript: Transcript,
        outcome: Any,
        context: Dict[str, Any],
    ) -> GradingResult:
        if not self.judge_fn:
            return GradingResult(
                grader_name=self.name,
                passed=False,
                score=0.0,
                assertions=[
                    Assertion(
                        description="LLM judge 未配置 judge_fn",
                        passed=False,
                        evidence="",
                    )
                ],
            )
        task = context.get("task")
        task_desc = task.initial_user_message if task else ""
        transcript_text = transcript.get_assistant_text() or ""
        try:
            result = self.judge_fn(transcript_text, self.rubric, task_desc)
            passed = result.get("passed", False)
            score = float(result.get("score", 0.0))
            score = max(0.0, min(1.0, score))
            reasoning = result.get("reasoning", "")
            return GradingResult(
                grader_name=self.name,
                passed=passed,
                score=score,
                assertions=[
                    Assertion(
                        description="LLM Rubric 评分",
                        passed=passed,
                        evidence=reasoning[:500],
                    )
                ],
                details=result,
            )
        except Exception as e:
            return GradingResult(
                grader_name=self.name,
                passed=False,
                score=0.0,
                assertions=[
                    Assertion(
                        description="LLM judge 执行异常",
                        passed=False,
                        evidence=str(e),
                    )
                ],
                details={"error": str(e)},
            )

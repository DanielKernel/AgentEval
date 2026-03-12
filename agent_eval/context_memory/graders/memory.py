"""记忆评估器：QA 准确率、时序推理、知识更新一致性、适当拒绝回答。

适用于 LongMemEval、UC004/UC008/UC010/UC013 评测场景。

所有评估器均支持两种工作模式：
- **精确匹配模式**（默认）：不依赖 LLM，基于字符串匹配 / Token F1 打分。
- **LLM-as-judge 模式**：注入 ``judge_fn`` 后使用 LLM 进行语义级打分。
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from agent_eval.context_memory.models import (
    ContextMemoryEvalResult,
    MemoryAnswer,
    MemoryTask,
    MemoryTaskType,
    MetricValue,
)

LLMJudgeFn = Callable[[str, str, str], Dict[str, Any]]
"""LLM judge 函数签名：(predicted_answer, gold_answer, question) -> {"passed": bool, "score": float, "reasoning": str}"""


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    """规范化文本：小写 + 去标点 + 合并空白。"""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _token_f1(predicted: str, gold: str) -> float:
    """计算 token 级别 F1 分数（用于开放域 QA 评估）。"""
    pred_tokens = _normalize(predicted).split()
    gold_tokens = _normalize(gold).split()
    if not pred_tokens or not gold_tokens:
        return 1.0 if predicted == gold else 0.0
    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0
    precision = len(common) / len(pred_tokens)
    recall = len(common) / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def _exact_match(predicted: str, gold: str) -> bool:
    """精确匹配（规范化后比较）。"""
    return _normalize(predicted) == _normalize(gold)


def _is_abstention(answer: str) -> bool:
    """检测答案是否表达了"不知道/不确定"的语义。"""
    normalized = _normalize(answer)
    abstention_phrases = [
        "i don t know", "i do not know", "unknown", "not sure", "cannot find",
        "no information", "not available", "don t have", "do not have",
        "不知道", "不清楚", "没有信息", "无法确定", "未知", "没有相关",
    ]
    return any(phrase in normalized for phrase in abstention_phrases)


# ---------------------------------------------------------------------------
# 评估器
# ---------------------------------------------------------------------------


class QAAccuracyGrader:
    """QA 准确率评估器：Exact Match + Token F1。

    Parameters
    ----------
    passing_threshold:
        Token F1 通过阈值（默认 0.5）。
    judge_fn:
        可选 LLM judge 函数。注入后 F1 < threshold 时会调用 LLM 进行二次判断。
    """

    def __init__(
        self,
        passing_threshold: float = 0.5,
        judge_fn: Optional[LLMJudgeFn] = None,
    ) -> None:
        self.passing_threshold = passing_threshold
        self.judge_fn = judge_fn

    def grade(self, task: MemoryTask, answer: MemoryAnswer) -> ContextMemoryEvalResult:
        predicted = answer.answer
        gold = task.gold_answer

        em = _exact_match(predicted, gold)
        f1 = _token_f1(predicted, gold)
        passed = em or f1 >= self.passing_threshold

        reasoning = ""
        if not passed and self.judge_fn is not None:
            try:
                judge_result = self.judge_fn(predicted, gold, task.question)
                passed = judge_result.get("passed", False)
                f1 = max(f1, float(judge_result.get("score", 0.0)))
                reasoning = judge_result.get("reasoning", "")
            except Exception as e:
                reasoning = f"LLM judge error: {e}"

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="memory",
            passed=passed,
            metrics=[
                MetricValue(name="exact_match", value=1.0 if em else 0.0),
                MetricValue(name="token_f1", value=f1),
            ],
            metadata={"reasoning": reasoning} if reasoning else {},
        )


class TemporalReasoningGrader:
    """时序推理评估器。

    时序推理任务需要模型理解事件的先后顺序、时间关系等。
    默认以 Token F1 评估；若注入 judge_fn，则优先使用 LLM 进行语义判断。

    Parameters
    ----------
    passing_threshold:
        Token F1 通过阈值（默认 0.6，时序任务要求更高精度）。
    judge_fn:
        可选 LLM judge 函数，推荐用于时序推理以获得更准确评估。
    """

    def __init__(
        self,
        passing_threshold: float = 0.6,
        judge_fn: Optional[LLMJudgeFn] = None,
    ) -> None:
        self.passing_threshold = passing_threshold
        self.judge_fn = judge_fn

    def grade(self, task: MemoryTask, answer: MemoryAnswer) -> ContextMemoryEvalResult:
        predicted = answer.answer
        gold = task.gold_answer

        f1 = _token_f1(predicted, gold)
        passed = f1 >= self.passing_threshold
        reasoning = ""

        if self.judge_fn is not None:
            try:
                judge_result = self.judge_fn(predicted, gold, task.question)
                passed = judge_result.get("passed", passed)
                reasoning = judge_result.get("reasoning", "")
                judge_score = float(judge_result.get("score", f1))
                f1 = max(f1, judge_score)
            except Exception as e:
                reasoning = f"LLM judge error: {e}"

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="memory",
            passed=passed,
            metrics=[
                MetricValue(name="temporal_f1", value=f1, description="时序推理 Token F1"),
            ],
            metadata={"reasoning": reasoning} if reasoning else {},
        )


class KnowledgeUpdateGrader:
    """知识更新一致性评估器。

    验证：当用户在会话中更新了某条信息后，系统返回的是最新值而非旧值。
    - 答案与 ``gold_answer`` 一致 → 通过（更新生效）
    - 答案与旧值一致 → 不通过（更新未生效，存在记忆不一致）

    Parameters
    ----------
    old_value:
        更新前的旧值（可选）。若提供，额外记录 ``stale_answer`` 指标。
    passing_threshold:
        Token F1 通过阈值（默认 0.5）。
    """

    def __init__(
        self,
        old_value: Optional[str] = None,
        passing_threshold: float = 0.5,
    ) -> None:
        self.old_value = old_value
        self.passing_threshold = passing_threshold

    def grade(self, task: MemoryTask, answer: MemoryAnswer) -> ContextMemoryEvalResult:
        predicted = answer.answer
        gold = task.gold_answer

        f1_new = _token_f1(predicted, gold)
        passed = f1_new >= self.passing_threshold

        metrics = [
            MetricValue(name="update_f1", value=f1_new, description="与最新值的 Token F1"),
        ]

        if self.old_value:
            f1_old = _token_f1(predicted, self.old_value)
            metrics.append(
                MetricValue(name="stale_answer_f1", value=f1_old, description="与旧值的 Token F1（越低越好）")
            )

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="memory",
            passed=passed,
            metrics=metrics,
        )


class AbstentionGrader:
    """适当拒绝回答（Abstention）评估器。

    对于 ``task.should_abstain=True`` 的任务，期望系统回答"不知道"；
    对于 ``task.should_abstain=False`` 的任务，期望系统给出具体答案。

    Parameters
    ----------
    abstention_f1_penalty:
        当 should_abstain=False 但系统拒绝回答时，Token F1 惩罚值（默认 0.0）。
    """

    def __init__(self, abstention_f1_penalty: float = 0.0) -> None:
        self.abstention_f1_penalty = abstention_f1_penalty

    def grade(self, task: MemoryTask, answer: MemoryAnswer) -> ContextMemoryEvalResult:
        predicted = answer.answer
        is_abstained = _is_abstention(predicted)

        if task.should_abstain:
            passed = is_abstained
            score = 1.0 if is_abstained else 0.0
            metric_name = "abstention_accuracy"
            description = "应拒绝时是否正确拒绝"
        else:
            passed = not is_abstained
            f1 = _token_f1(predicted, task.gold_answer)
            score = f1 if not is_abstained else self.abstention_f1_penalty
            metric_name = "answer_accuracy"
            description = "不应拒绝时是否给出了答案"

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="memory",
            passed=passed,
            metrics=[
                MetricValue(name=metric_name, value=score, description=description),
                MetricValue(name="is_abstained", value=1.0 if is_abstained else 0.0),
            ],
        )


class MemorySuiteGrader:
    """记忆评测套件：根据任务类型自动选择合适的评估器。

    Parameters
    ----------
    passing_threshold:
        通用通过阈值。
    judge_fn:
        可选 LLM judge 函数，传递给各子评估器。
    """

    def __init__(
        self,
        passing_threshold: float = 0.5,
        judge_fn: Optional[LLMJudgeFn] = None,
    ) -> None:
        self._qa_grader = QAAccuracyGrader(passing_threshold=passing_threshold, judge_fn=judge_fn)
        self._temporal_grader = TemporalReasoningGrader(
            passing_threshold=passing_threshold, judge_fn=judge_fn
        )
        self._update_grader = KnowledgeUpdateGrader(passing_threshold=passing_threshold)
        self._abstention_grader = AbstentionGrader()

    def grade(self, task: MemoryTask, answer: MemoryAnswer) -> ContextMemoryEvalResult:
        if task.task_type == MemoryTaskType.TEMPORAL:
            return self._temporal_grader.grade(task, answer)
        if task.task_type == MemoryTaskType.UPDATE:
            return self._update_grader.grade(task, answer)
        if task.task_type == MemoryTaskType.ABSTENTION:
            return self._abstention_grader.grade(task, answer)
        return self._qa_grader.grade(task, answer)

"""上下文质量评估器：压缩保真度、Token 效率、多文档利用率。

适用于 LongBench v2、UC001（多源聚合）、UC007（接口调用）、UC009（压缩/摘要）评测。
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional

from agent_eval.context_memory.models import (
    ContextMemoryEvalResult,
    ContextQualityResult,
    ContextQualityTask,
    Document,
    MetricValue,
)

LLMJudgeFn = Callable[[str, str, str], Dict[str, Any]]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def _token_f1(predicted: str, gold: str) -> float:
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


def _estimate_tokens(text: str) -> int:
    """估算 token 数（用空白分词，近似值）。"""
    return len(text.split())


# ---------------------------------------------------------------------------
# 评估器
# ---------------------------------------------------------------------------


class CompressionFidelityGrader:
    """压缩保真度评估器。

    比较压缩前（raw context）和压缩后（compressed context）回答问题的质量差值。
    差值越小，说明压缩损失越少。

    用法：
    1. 用 raw context 回答问题，得到 ``raw_result``；
    2. 用 compressed context 回答问题，得到 ``compressed_result``；
    3. 调用 ``grade(task, raw_result, compressed_result)``。

    Parameters
    ----------
    passing_threshold:
        允许的最大 F1 下降量（默认 0.1，即压缩后 F1 不低于原始 F1 - 0.1）。
    """

    def __init__(self, passing_threshold: float = 0.1) -> None:
        self.passing_threshold = passing_threshold

    def grade(
        self,
        task: ContextQualityTask,
        raw_result: ContextQualityResult,
        compressed_result: ContextQualityResult,
    ) -> ContextMemoryEvalResult:
        raw_f1 = _token_f1(raw_result.answer, task.gold_answer)
        compressed_f1 = _token_f1(compressed_result.answer, task.gold_answer)
        quality_drop = max(0.0, raw_f1 - compressed_f1)
        fidelity = 1.0 - quality_drop
        passed = quality_drop <= self.passing_threshold

        metrics = [
            MetricValue(name="raw_f1", value=raw_f1, description="原始上下文回答 Token F1"),
            MetricValue(name="compressed_f1", value=compressed_f1, description="压缩后上下文回答 Token F1"),
            MetricValue(name="compression_fidelity", value=fidelity, description="压缩保真度（1 - F1 下降量）"),
            MetricValue(name="quality_drop", value=quality_drop, description="F1 下降量（越小越好）"),
        ]

        raw_tokens = raw_result.tokens_used or _estimate_tokens(raw_result.context_used)
        comp_tokens = compressed_result.tokens_used or _estimate_tokens(compressed_result.context_used)
        if raw_tokens > 0:
            compression_ratio = 1.0 - comp_tokens / raw_tokens
            metrics.append(
                MetricValue(name="compression_ratio", value=compression_ratio, description="上下文压缩率（越高越省）")
            )

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="context_quality",
            passed=passed,
            metrics=metrics,
        )


class TokenEfficiencyGrader:
    """Token 效率评估器。

    衡量在达到相同（或更高）答案质量的前提下，实际使用的 token 数。
    token 使用量越少，效率越高。

    Parameters
    ----------
    baseline_tokens:
        基线 token 数（如 raw context 的 token 数）。若未提供，直接评估 token 使用量。
    passing_f1_threshold:
        答案质量通过阈值（默认 0.5）。
    target_token_budget:
        目标 token 预算。若实际使用量超过此值，token_efficiency < 1.0。
    """

    def __init__(
        self,
        baseline_tokens: Optional[int] = None,
        passing_f1_threshold: float = 0.5,
        target_token_budget: Optional[int] = None,
    ) -> None:
        self.baseline_tokens = baseline_tokens
        self.passing_f1_threshold = passing_f1_threshold
        self.target_token_budget = target_token_budget

    def grade(
        self,
        task: ContextQualityTask,
        result: ContextQualityResult,
    ) -> ContextMemoryEvalResult:
        f1 = _token_f1(result.answer, task.gold_answer)
        tokens_used = result.tokens_used or _estimate_tokens(result.context_used)

        metrics = [
            MetricValue(name="answer_f1", value=f1),
            MetricValue(name="tokens_used", value=float(tokens_used)),
        ]

        if self.baseline_tokens and self.baseline_tokens > 0:
            savings_ratio = 1.0 - tokens_used / self.baseline_tokens
            metrics.append(MetricValue(name="token_savings_ratio", value=savings_ratio))

        if self.target_token_budget and self.target_token_budget > 0:
            within_budget = tokens_used <= self.target_token_budget
            efficiency = min(1.0, self.target_token_budget / tokens_used) if tokens_used > 0 else 1.0
            metrics.append(MetricValue(name="within_budget", value=1.0 if within_budget else 0.0))
            metrics.append(MetricValue(name="token_efficiency", value=efficiency))

        passed = f1 >= self.passing_f1_threshold
        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="context_quality",
            passed=passed,
            metrics=metrics,
        )


class MultiDocUtilizationGrader:
    """多文档利用率评估器。

    衡量答案中实际引用/覆盖了多少文档的信息。
    通过检测答案文本与各文档内容的 token 重叠来估算利用率。

    Parameters
    ----------
    passing_threshold:
        最低文档利用率阈值（默认 0.5，即至少利用了 50% 的文档）。
    min_overlap_tokens:
        认定"使用了某文档"的最低 token 重叠数（默认 2）。
    judge_fn:
        可选 LLM judge 函数，用于更精确的引用检测。
    """

    def __init__(
        self,
        passing_threshold: float = 0.5,
        min_overlap_tokens: int = 2,
        judge_fn: Optional[LLMJudgeFn] = None,
    ) -> None:
        self.passing_threshold = passing_threshold
        self.min_overlap_tokens = min_overlap_tokens
        self.judge_fn = judge_fn

    def _doc_utilized(self, answer: str, doc: Document) -> bool:
        answer_tokens = set(_normalize(answer).split())
        doc_tokens = set(_normalize(doc.text).split())
        overlap = len(answer_tokens & doc_tokens)
        return overlap >= self.min_overlap_tokens

    def grade(
        self,
        task: ContextQualityTask,
        result: ContextQualityResult,
    ) -> ContextMemoryEvalResult:
        if not task.documents:
            return ContextMemoryEvalResult(
                task_id=task.task_id,
                task_type="context_quality",
                passed=True,
                metrics=[MetricValue(name="multi_doc_utilization", value=1.0)],
                error="无候选文档，跳过多文档利用率评估",
            )

        answer = result.answer
        utilized = sum(1 for doc in task.documents if self._doc_utilized(answer, doc))
        utilization = utilized / len(task.documents)

        answer_f1 = _token_f1(answer, task.gold_answer)
        passed = utilization >= self.passing_threshold

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="context_quality",
            passed=passed,
            metrics=[
                MetricValue(name="multi_doc_utilization", value=utilization, description="文档利用率"),
                MetricValue(name="docs_utilized", value=float(utilized), description="实际利用文档数"),
                MetricValue(name="total_docs", value=float(len(task.documents))),
                MetricValue(name="answer_f1", value=answer_f1),
            ],
        )


class ContextQualitySuiteGrader:
    """上下文质量评测套件：组合压缩保真度 + Token 效率 + 多文档利用率。"""

    def __init__(
        self,
        compression_threshold: float = 0.1,
        passing_f1_threshold: float = 0.5,
        multi_doc_threshold: float = 0.5,
        judge_fn: Optional[LLMJudgeFn] = None,
    ) -> None:
        self._compression_grader = CompressionFidelityGrader(passing_threshold=compression_threshold)
        self._token_grader = TokenEfficiencyGrader(passing_f1_threshold=passing_f1_threshold)
        self._multi_doc_grader = MultiDocUtilizationGrader(
            passing_threshold=multi_doc_threshold, judge_fn=judge_fn
        )

    def grade(
        self,
        task: ContextQualityTask,
        result: ContextQualityResult,
        raw_result: Optional[ContextQualityResult] = None,
    ) -> ContextMemoryEvalResult:
        """综合评估。

        Parameters
        ----------
        task:
            上下文质量任务。
        result:
            当前（可能已压缩/已检索）上下文的回答结果。
        raw_result:
            可选：原始上下文的回答结果（用于压缩保真度对比）。
        """
        all_metrics: List[MetricValue] = []
        sub_passed = []

        if raw_result is not None:
            comp_result = self._compression_grader.grade(task, raw_result, result)
            all_metrics.extend(comp_result.metrics)
            sub_passed.append(comp_result.passed)

        token_result = self._token_grader.grade(task, result)
        all_metrics.extend(token_result.metrics)
        sub_passed.append(token_result.passed)

        if task.documents:
            doc_result = self._multi_doc_grader.grade(task, result)
            all_metrics.extend(doc_result.metrics)
            sub_passed.append(doc_result.passed)

        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="context_quality",
            passed=all(sub_passed),
            metrics=all_metrics,
        )

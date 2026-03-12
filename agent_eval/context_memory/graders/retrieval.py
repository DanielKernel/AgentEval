"""检索指标评估器：nDCG@k、Recall@k、MRR。

全部基于标准库实现，无外部依赖。
适用于 BEIR、UC005（混合式召回）、UC012（结构化存储与混合检索）评测。
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional

from agent_eval.context_memory.models import (
    ContextMemoryEvalResult,
    MetricValue,
    RankedDocument,
    RetrievalResult,
    RetrievalTask,
)


def _dcg(relevances: List[float]) -> float:
    """计算 DCG（Discounted Cumulative Gain）。"""
    return sum(
        rel / math.log2(rank + 2)
        for rank, rel in enumerate(relevances)
    )


def _ideal_dcg(relevances: List[float], k: int) -> float:
    """计算 IDCG：将 relevances 降序排列后取前 k 个的 DCG。"""
    sorted_rels = sorted(relevances, reverse=True)[:k]
    return _dcg(sorted_rels)


def _get_relevance(doc_id: str, task: RetrievalTask) -> float:
    """获取文档的相关性分数。"""
    if task.relevance_scores:
        return float(task.relevance_scores.get(doc_id, 0))
    return 1.0 if doc_id in task.relevant_doc_ids else 0.0


def ndcg_at_k(task: RetrievalTask, ranked_docs: List[RankedDocument], k: int) -> float:
    """计算 nDCG@k。

    Parameters
    ----------
    task:
        检索任务（含 gold 相关文档）。
    ranked_docs:
        服务返回的排序文档列表。
    k:
        截断位置。

    Returns
    -------
    float
        nDCG@k 值，范围 [0, 1]。
    """
    top_k = ranked_docs[:k]
    relevances = [_get_relevance(d.doc_id, task) for d in top_k]

    all_relevances = [_get_relevance(d.doc_id, task) for d in ranked_docs]
    all_relevances += [_get_relevance(doc_id, task) for doc_id in task.relevant_doc_ids]
    idcg = _ideal_dcg(all_relevances, k)
    if idcg == 0.0:
        return 0.0
    return _dcg(relevances) / idcg


def recall_at_k(task: RetrievalTask, ranked_docs: List[RankedDocument], k: int) -> float:
    """计算 Recall@k。"""
    if not task.relevant_doc_ids:
        return 0.0
    top_k_ids = {d.doc_id for d in ranked_docs[:k]}
    hits = sum(1 for doc_id in task.relevant_doc_ids if doc_id in top_k_ids)
    return hits / len(task.relevant_doc_ids)


def mrr(task: RetrievalTask, ranked_docs: List[RankedDocument]) -> float:
    """计算 MRR（Mean Reciprocal Rank）。"""
    relevant_ids = set(task.relevant_doc_ids)
    for rank, doc in enumerate(ranked_docs, start=1):
        if doc.doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0


class NDCGGrader:
    """nDCG@k 评估器。"""

    def __init__(self, k: int = 10, passing_threshold: float = 0.3):
        self.k = k
        self.passing_threshold = passing_threshold

    def grade(self, task: RetrievalTask, result: RetrievalResult) -> ContextMemoryEvalResult:
        score = ndcg_at_k(task, result.ranked_docs, self.k)
        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="retrieval",
            passed=score >= self.passing_threshold,
            metrics=[MetricValue(name=f"ndcg@{self.k}", value=score)],
        )


class RecallAtKGrader:
    """Recall@k 评估器。"""

    def __init__(self, k: int = 10, passing_threshold: float = 0.5):
        self.k = k
        self.passing_threshold = passing_threshold

    def grade(self, task: RetrievalTask, result: RetrievalResult) -> ContextMemoryEvalResult:
        score = recall_at_k(task, result.ranked_docs, self.k)
        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="retrieval",
            passed=score >= self.passing_threshold,
            metrics=[MetricValue(name=f"recall@{self.k}", value=score)],
        )


class MRRGrader:
    """MRR（Mean Reciprocal Rank）评估器。"""

    def __init__(self, passing_threshold: float = 0.3):
        self.passing_threshold = passing_threshold

    def grade(self, task: RetrievalTask, result: RetrievalResult) -> ContextMemoryEvalResult:
        score = mrr(task, result.ranked_docs)
        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="retrieval",
            passed=score >= self.passing_threshold,
            metrics=[MetricValue(name="mrr", value=score)],
        )


class RetrievalSuiteGrader:
    """检索评测套件：组合 nDCG@k + Recall@k + MRR，一次评测输出所有指标。

    Parameters
    ----------
    k:
        截断位置，默认 10。
    ndcg_threshold:
        nDCG@k 通过阈值。
    recall_threshold:
        Recall@k 通过阈值。
    mrr_threshold:
        MRR 通过阈值。
    """

    def __init__(
        self,
        k: int = 10,
        ndcg_threshold: float = 0.3,
        recall_threshold: float = 0.5,
        mrr_threshold: float = 0.3,
    ) -> None:
        self.k = k
        self.ndcg_threshold = ndcg_threshold
        self.recall_threshold = recall_threshold
        self.mrr_threshold = mrr_threshold

    def grade(self, task: RetrievalTask, result: RetrievalResult) -> ContextMemoryEvalResult:
        ndcg_score = ndcg_at_k(task, result.ranked_docs, self.k)
        recall_score = recall_at_k(task, result.ranked_docs, self.k)
        mrr_score = mrr(task, result.ranked_docs)

        passed = (
            ndcg_score >= self.ndcg_threshold
            and recall_score >= self.recall_threshold
            and mrr_score >= self.mrr_threshold
        )
        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="retrieval",
            passed=passed,
            metrics=[
                MetricValue(name=f"ndcg@{self.k}", value=ndcg_score),
                MetricValue(name=f"recall@{self.k}", value=recall_score),
                MetricValue(name="mrr", value=mrr_score),
            ],
        )


def aggregate_retrieval_metrics(
    results: List[ContextMemoryEvalResult],
    k: int = 10,
) -> Dict[str, float]:
    """对一批检索评测结果计算宏平均指标。"""
    metrics: Dict[str, List[float]] = {}
    for r in results:
        for m in r.metrics:
            metrics.setdefault(m.name, []).append(m.value)
    return {name: sum(vals) / len(vals) for name, vals in metrics.items() if vals}

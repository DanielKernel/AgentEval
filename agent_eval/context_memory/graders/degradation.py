"""长度退化曲线评估器（RULER 场景）。

测量 accuracy vs context_length 的关系，用于：
- 观察模型有效上下文长度（effective context length）
- 计算退化斜率（degradation slope）
- 识别性能急剧下降的长度拐点

适用于 RULER、UC003（动态上下文更新）、UC004/UC009 退化曲线分析。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from agent_eval.context_memory.models import (
    ContextMemoryEvalResult,
    ContextQualityResult,
    ContextQualityTask,
    MetricValue,
)


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


def _linear_slope(points: List[Tuple[float, float]]) -> Optional[float]:
    """对 (x, y) 点列表拟合线性斜率（最小二乘法，无外部依赖）。"""
    n = len(points)
    if n < 2:
        return None
    sum_x = sum(p[0] for p in points)
    sum_y = sum(p[1] for p in points)
    sum_xy = sum(p[0] * p[1] for p in points)
    sum_x2 = sum(p[0] ** 2 for p in points)
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


class LengthDegradationPoint:
    """单个 context_length 下的评测数据点。"""

    def __init__(self, context_length: int, accuracy: float) -> None:
        self.context_length = context_length
        self.accuracy = accuracy

    def to_dict(self) -> Dict[str, Any]:
        return {"context_length": self.context_length, "accuracy": self.accuracy}


class LengthDegradationGrader:
    """长度退化曲线评估器。

    跨多个上下文长度运行评测，记录 (context_length, accuracy) 数据点，
    计算退化斜率与有效上下文长度。

    Parameters
    ----------
    passing_accuracy_threshold:
        在 ``critical_length`` 以内，期望达到的最低准确率（默认 0.7）。
    critical_length:
        关键长度阈值（token 数），超过此长度时性能下降可接受（默认 8192）。
    slope_threshold:
        最大允许退化斜率（负值，默认 -0.05，即每 1k tokens 下降 5% 视为显著退化）。
    """

    def __init__(
        self,
        passing_accuracy_threshold: float = 0.7,
        critical_length: int = 8192,
        slope_threshold: float = -0.05,
    ) -> None:
        self.passing_accuracy_threshold = passing_accuracy_threshold
        self.critical_length = critical_length
        self.slope_threshold = slope_threshold
        self._data_points: List[LengthDegradationPoint] = []

    def record(
        self,
        task: ContextQualityTask,
        result: ContextQualityResult,
        context_length: int,
    ) -> ContextMemoryEvalResult:
        """记录单个数据点并返回该点的评测结果。"""
        accuracy = _token_f1(result.answer, task.gold_answer)
        self._data_points.append(LengthDegradationPoint(context_length, accuracy))

        passed = (
            accuracy >= self.passing_accuracy_threshold
            if context_length <= self.critical_length
            else True
        )
        return ContextMemoryEvalResult(
            task_id=task.task_id,
            task_type="context_quality",
            passed=passed,
            metrics=[
                MetricValue(name="accuracy", value=accuracy),
                MetricValue(name="context_length", value=float(context_length)),
            ],
        )

    def analyze(self) -> Dict[str, Any]:
        """分析已记录的所有数据点，输出退化曲线指标。

        Returns
        -------
        dict 包含以下字段：
        - ``data_points``: 所有数据点列表
        - ``degradation_slope``: 退化斜率（负值表示随长度增加而下降）
        - ``effective_context_length``: 有效上下文长度（准确率首次低于阈值时的长度）
        - ``significant_degradation``: 是否出现显著退化
        - ``mean_accuracy``: 平均准确率
        """
        if not self._data_points:
            return {"data_points": [], "degradation_slope": None}

        sorted_points = sorted(self._data_points, key=lambda p: p.context_length)
        xy = [(p.context_length / 1000.0, p.accuracy) for p in sorted_points]

        slope = _linear_slope(xy)
        mean_acc = sum(p.accuracy for p in sorted_points) / len(sorted_points)

        effective_length = None
        for p in sorted_points:
            if p.accuracy < self.passing_accuracy_threshold:
                effective_length = p.context_length
                break

        return {
            "data_points": [p.to_dict() for p in sorted_points],
            "degradation_slope": round(slope, 6) if slope is not None else None,
            "effective_context_length": effective_length,
            "significant_degradation": slope is not None and slope < self.slope_threshold,
            "mean_accuracy": round(mean_acc, 4),
            "num_points": len(sorted_points),
        }

    def grade_suite(self, task_id: str = "degradation_suite") -> ContextMemoryEvalResult:
        """对所有已记录数据点生成汇总评测结果。"""
        analysis = self.analyze()
        slope = analysis.get("degradation_slope") or 0.0
        mean_acc = analysis.get("mean_accuracy", 0.0)
        significant = analysis.get("significant_degradation", False)

        passed = not significant and mean_acc >= self.passing_accuracy_threshold

        metrics = [
            MetricValue(name="mean_accuracy", value=mean_acc),
            MetricValue(name="degradation_slope", value=slope, description="退化斜率（per 1k tokens）"),
            MetricValue(name="significant_degradation", value=1.0 if significant else 0.0),
        ]
        eff_len = analysis.get("effective_context_length")
        if eff_len is not None:
            metrics.append(
                MetricValue(name="effective_context_length", value=float(eff_len))
            )

        return ContextMemoryEvalResult(
            task_id=task_id,
            task_type="context_quality",
            passed=passed,
            metrics=metrics,
            metadata={"analysis": analysis},
        )

    def reset(self) -> None:
        """清空已记录的数据点（复用同一实例时调用）。"""
        self._data_points = []

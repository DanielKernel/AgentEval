"""评测框架（Evaluation Harness）：运行试验、应用评估器、计算 pass@k / pass^k。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agent_eval.conversation.agent import DialogueAgent
from agent_eval.conversation.graders import Grader
from agent_eval.conversation.models import (
    ConversationTask,
    GradingResult,
    Transcript,
    TrialResult,
    Turn,
)


def pass_at_k(n: int, k: int, successes: List[bool]) -> float:
    """pass@k：n 次试验中至少 1 次成功的概率估计。

    当 n 次试验中有 s 次成功时，估计的是「若做 k 次试验，至少一次成功」的概率。
    使用公式：1 - C(n-s, k) / C(n, k)，当 n-s < k 时为 1.0。
    """
    if n == 0 or k == 0:
        return 0.0
    s = sum(1 for x in successes if x)
    if s == 0:
        return 0.0
    if n - s < k:
        return 1.0

    def comb(a: int, b: int) -> float:
        if b > a or b < 0:
            return 0.0
        if b == 0 or b == a:
            return 1.0
        num = 1.0
        for i in range(b):
            num *= a - i
        den = 1.0
        for i in range(1, b + 1):
            den *= i
        return num / den

    return 1.0 - comb(n - s, k) / comb(n, k)


def pass_k(n: int, k: int, successes: List[bool]) -> float:
    """pass^k：n 次试验中「连续 k 次都成功」的比例（一致性）。

    这里简化为：在 n 次试验中，随机取 k 次都成功的概率估计。
    若 n 次试验中有 s 次成功，则 pass^k ≈ (s/n)^k（近似）。
    更直接：若 n 次试验全部成功则 1.0，否则按成功次数比例。
    """
    if n == 0 or k == 0:
        return 0.0
    s = sum(1 for x in successes if x)
    if s < k:
        return 0.0
    # 取前 k 次是否都成功的一种简单估计
    return (s / n) ** k


@dataclass
class EvalSuiteResult:
    """单个任务在多次试验后的聚合结果。"""

    task_id: str
    task: ConversationTask
    trials: List[TrialResult] = field(default_factory=list)
    n_passed: int = 0
    pass_at_1: float = 0.0
    pass_at_k: float = 0.0
    pass_k: float = 0.0
    mean_score: float = 0.0
    aggregate_passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "n_trials": len(self.trials),
            "n_passed": self.n_passed,
            "pass_at_1": self.pass_at_1,
            "pass_at_k": self.pass_at_k,
            "pass_k": self.pass_k,
            "mean_score": self.mean_score,
            "aggregate_passed": self.aggregate_passed,
        }


class ConversationEvalHarness:
    """对话 Agent 评测框架：对给定任务运行多次试验，应用评估器，汇总 pass@k 等指标。"""

    def __init__(
        self,
        agent: DialogueAgent,
        graders: List[Grader],
        n_trials: int = 3,
        pass_k_param: int = 3,
        seed: Optional[int] = None,
        max_concurrency: int = 1,
    ):
        self.agent = agent
        self.graders = graders
        self.n_trials = n_trials
        self.pass_k_param = pass_k_param
        self.seed = seed
        self.max_concurrency = max(1, max_concurrency)

    def run_trial(self, task: ConversationTask, trial_number: int) -> TrialResult:
        """执行单次试验：运行 Agent，收集 Transcript，应用所有 Grader。"""
        transcript = Transcript(task_id=task.task_id, trial_number=trial_number)
        try:
            if self.seed is not None:
                random.seed(self.seed + trial_number)
            transcript = self.agent.run(task)
            transcript.task_id = task.task_id
            transcript.trial_number = trial_number
        except Exception as e:
            return TrialResult(
                task_id=task.task_id,
                trial_number=trial_number,
                transcript=transcript,
                passed=False,
                error=str(e),
            )

        context = {"task": task}
        outcome = None
        grades: Dict[str, GradingResult] = {}
        for g in self.graders:
            gr = g.grade(transcript, outcome, context)
            grades[g.name] = gr

        passed = all(gr.passed for gr in grades.values())
        return TrialResult(
            task_id=task.task_id,
            trial_number=trial_number,
            transcript=transcript,
            grades=grades,
            passed=passed,
        )

    def run_task(self, task: ConversationTask) -> EvalSuiteResult:
        """对单个任务运行 n_trials 次试验并聚合。"""
        trials: List[TrialResult] = []
        for i in range(self.n_trials):
            tr = self.run_trial(task, i)
            trials.append(tr)

        successes = [t.passed for t in trials]
        n_passed = sum(successes)
        pass_at_1 = pass_at_k(len(trials), 1, successes)
        pass_at_k_val = pass_at_k(len(trials), self.pass_k_param, successes)
        pass_k_val = pass_k(len(trials), self.pass_k_param, successes)

        scores = []
        for t in trials:
            if t.grades:
                total_w = sum(g.weight for g in self.graders)
                if total_w > 0:
                    s = sum(t.grades[g.name].score * g.weight for g in self.graders) / total_w
                    scores.append(s)
        mean_score = sum(scores) / len(scores) if scores else 0.0

        return EvalSuiteResult(
            task_id=task.task_id,
            task=task,
            trials=trials,
            n_passed=n_passed,
            pass_at_1=pass_at_1,
            pass_at_k=pass_at_k_val,
            pass_k=pass_k_val,
            mean_score=mean_score,
            aggregate_passed=n_passed == len(trials),
        )

    def run_evaluation(self, tasks: List[ConversationTask]) -> List[EvalSuiteResult]:
        """对任务列表运行评测，返回每个任务的聚合结果。"""
        return [self.run_task(t) for t in tasks]

    def summary(
        self,
        results: List[EvalSuiteResult],
    ) -> Dict[str, Any]:
        """汇总所有任务的统计。"""
        if not results:
            return {
                "total_tasks": 0,
                "total_trials": 0,
                "overall_pass_rate": 0.0,
                "mean_pass_at_1": 0.0,
                "mean_pass_at_k": 0.0,
                "mean_pass_k": 0.0,
                "mean_score": 0.0,
            }
        total_trials = sum(len(r.trials) for r in results)
        total_passed_trials = sum(r.n_passed for r in results)
        return {
            "total_tasks": len(results),
            "total_trials": total_trials,
            "total_passed_trials": total_passed_trials,
            "overall_pass_rate": total_passed_trials / total_trials if total_trials else 0.0,
            "tasks_all_passed": sum(1 for r in results if r.aggregate_passed),
            "mean_pass_at_1": sum(r.pass_at_1 for r in results) / len(results),
            "mean_pass_at_k": sum(r.pass_at_k for r in results) / len(results),
            "mean_pass_k": sum(r.pass_k for r in results) / len(results),
            "mean_score": sum(r.mean_score for r in results) / len(results),
        }

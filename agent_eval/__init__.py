"""AgentEval – a lightweight framework for evaluating AI agent responses."""

from agent_eval.models import Criterion, EvalTask, EvalResult
from agent_eval.evaluator import AgentEvaluator

__all__ = ["Criterion", "EvalTask", "EvalResult", "AgentEvaluator"]
__version__ = "0.1.0"

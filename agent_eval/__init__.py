"""AgentEval – 兼容 legacy 与 conversation 两套评测 API。"""

from agent_eval.harness import EvaluationHarness
from agent_eval.models import (
    Criterion,
    EvalResult,
    EvalTask,
    TrialResult as LegacyTrialResult,
    TaskTrialResult,
    TranscriptStep,
)
from agent_eval.evaluator import AgentEvaluator
from agent_eval.conversation import (
    ConversationEvalHarness,
    ConversationTask,
    DialogueAgent,
    GradingResult,
    Grader,
    KeywordGrader,
    LLMRubricGrader,
    MaxTurnsGrader,
    RegexGrader,
    StringMatchGrader,
    Transcript,
    TrialResult as ConversationTrialResult,
    Turn,
    pass_at_k,
    pass_k,
)

# 向后兼容：保留 legacy 命名
TrialResult = LegacyTrialResult

__all__ = [
    # legacy evaluator stack
    "Criterion",
    "EvalTask",
    "EvalResult",
    "TranscriptStep",
    "TrialResult",
    "LegacyTrialResult",
    "TaskTrialResult",
    "AgentEvaluator",
    "EvaluationHarness",
    # conversation stack
    "ConversationEvalHarness",
    "ConversationTask",
    "DialogueAgent",
    "GradingResult",
    "Grader",
    "KeywordGrader",
    "LLMRubricGrader",
    "MaxTurnsGrader",
    "RegexGrader",
    "StringMatchGrader",
    "Transcript",
    "ConversationTrialResult",
    "Turn",
    "pass_at_k",
    "pass_k",
]
__version__ = "0.1.0"

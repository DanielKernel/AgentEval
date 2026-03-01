"""对话类 Agent 自动化评测（基于 Anthropic Demystifying evals for AI agents）。"""

from agent_eval.conversation.agent import DialogueAgent, run_agent_simple
from agent_eval.conversation.agent_factory import build_agent, build_agents
from agent_eval.conversation.graders import (
    Grader,
    KeywordGrader,
    LLMRubricGrader,
    MaxTurnsGrader,
    RegexGrader,
    StringMatchGrader,
)
from agent_eval.conversation.harness import (
    ConversationEvalHarness,
    EvalSuiteResult,
    pass_at_k,
    pass_k,
)
from agent_eval.conversation.models import (
    Assertion,
    ConversationTask,
    GradingResult,
    Transcript,
    TrialResult,
    Turn,
)

__all__ = [
    "DialogueAgent",
    "run_agent_simple",
    "build_agent",
    "build_agents",
    "Grader",
    "StringMatchGrader",
    "RegexGrader",
    "KeywordGrader",
    "MaxTurnsGrader",
    "LLMRubricGrader",
    "ConversationEvalHarness",
    "EvalSuiteResult",
    "pass_at_k",
    "pass_k",
    "Assertion",
    "ConversationTask",
    "GradingResult",
    "Transcript",
    "TrialResult",
    "Turn",
]

"""AgentEval – 兼容 legacy、conversation 与 context_memory 三套评测 API。"""

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

# context_memory stack 按需导入（懒加载，避免循环依赖）
def __getattr__(name: str):
    _context_memory_exports = {
        # models
        "Document", "RankedDocument", "RetrievalTask", "RetrievalResult",
        "MemoryTurn", "MemoryTask", "MemoryTaskType", "MemoryAnswer",
        "ContextMode", "ContextQualityTask", "ContextQualityResult",
        "MetricValue", "ContextMemoryEvalResult", "ContextMemoryReport",
        # adapters
        "RetrievalServiceAdapter", "MemoryServiceAdapter", "ContextQualityServiceAdapter",
        "RESTServiceAdapter", "LocalFunctionAdapter", "MockAdapter",
        # graders
        "NDCGGrader", "RecallAtKGrader", "MRRGrader", "RetrievalSuiteGrader",
        "ndcg_at_k", "recall_at_k", "mrr", "aggregate_retrieval_metrics",
        "QAAccuracyGrader", "TemporalReasoningGrader", "KnowledgeUpdateGrader",
        "AbstentionGrader", "MemorySuiteGrader",
        "CompressionFidelityGrader", "TokenEfficiencyGrader",
        "MultiDocUtilizationGrader", "ContextQualitySuiteGrader",
        "LengthDegradationGrader", "LengthDegradationPoint",
        # loaders
        "BenchmarkLoader", "BEIRLoader", "LongMemEvalLoader", "LongBenchLoader",
        "LoCoMoLoader", "RULERLoader",
        # harness
        "ContextMemoryEvalHarness", "EvalMode",
        # scenarios
        "get_multi_source_tasks", "get_memory_tier_tasks", "get_context_exposure_tasks",
        "get_compression_tasks", "get_working_memory_tasks", "get_tool_context_tasks",
        "get_sub_agent_tasks", "get_all_self_built_tasks",
        # plugin
        "ContextMemoryEvalPlugin",
    }
    if name in _context_memory_exports:
        import agent_eval.context_memory as _cm
        import agent_eval.plugins as _plugins
        combined = {**vars(_cm), **vars(_plugins)}
        if name in combined:
            return combined[name]
    raise AttributeError(f"module 'agent_eval' has no attribute {name!r}")


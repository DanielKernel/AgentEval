"""Scenarios 模块公共导出。"""

from agent_eval.context_memory.scenarios.compression import get_compression_tasks
from agent_eval.context_memory.scenarios.context_exposure import get_context_exposure_tasks
from agent_eval.context_memory.scenarios.memory_tiers import get_memory_tier_tasks
from agent_eval.context_memory.scenarios.multi_source import get_multi_source_tasks
from agent_eval.context_memory.scenarios.sub_agent import get_sub_agent_tasks
from agent_eval.context_memory.scenarios.tool_context import get_tool_context_tasks
from agent_eval.context_memory.scenarios.working_memory import get_working_memory_tasks

__all__ = [
    "get_multi_source_tasks",
    "get_memory_tier_tasks",
    "get_context_exposure_tasks",
    "get_compression_tasks",
    "get_working_memory_tasks",
    "get_tool_context_tasks",
    "get_sub_agent_tasks",
]


def get_all_self_built_tasks():
    """返回所有自建场景任务列表（合并）。"""
    return (
        get_multi_source_tasks()
        + get_memory_tier_tasks()
        + get_context_exposure_tasks()
        + get_compression_tasks()
        + get_working_memory_tasks()
        + get_tool_context_tasks()
        + get_sub_agent_tasks()
    )

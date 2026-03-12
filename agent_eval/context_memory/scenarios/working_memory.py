"""UC010：工作记忆（Working Memory）管理评测场景。

评测系统维护当前任务上下文的能力：
- 跨轮次记住任务状态
- 维护结构化笔记
- 在任务流程中追踪变量和中间结果

对齐 UC：
- UC010：结构化笔记与工作记忆管理
- 外部 benchmark：LoCoMo（主）、LongMemEval（主）
"""

from __future__ import annotations

from typing import List

from agent_eval.context_memory.models import MemoryTask, MemoryTaskType, MemoryTurn


def get_working_memory_tasks() -> List[MemoryTask]:
    """返回工作记忆管理场景的示例任务列表。"""
    return [
        MemoryTask(
            task_id="wm_001",
            session_id="session_wm_001",
            history=[
                MemoryTurn(role="user", content="我要计划一次旅行，目的地是东京，出发日期 4 月 15 日，预算 15000 元"),
                MemoryTurn(role="assistant", content="好的，已记录您的旅行计划：东京，4 月 15 日，预算 15000 元。请问需要几天？"),
                MemoryTurn(role="user", content="7 天"),
                MemoryTurn(role="assistant", content="7 天东京行已记录。是否需要帮您规划行程？"),
                MemoryTurn(role="user", content="是的，第一天先去浅草寺"),
                MemoryTurn(role="assistant", content="第一天：浅草寺。已加入行程。"),
                MemoryTurn(role="user", content="第二天去迪士尼乐园"),
                MemoryTurn(role="assistant", content="第二天：迪士尼乐园。已加入行程。"),
            ],
            question="目前行程规划中，我的预算是多少，已安排了哪几天的活动？",
            gold_answer="预算 15000 元，已安排第一天浅草寺，第二天迪士尼乐园",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC010",
                "scenario": "task_state_tracking",
                "expected_structured_notes": {
                    "destination": "东京",
                    "departure_date": "4月15日",
                    "duration": "7天",
                    "budget": 15000,
                    "itinerary": {"day1": "浅草寺", "day2": "迪士尼乐园"},
                },
            },
        ),
        MemoryTask(
            task_id="wm_002",
            session_id="session_wm_002",
            history=[
                MemoryTurn(role="user", content="帮我写一篇文章，主题是人工智能对教育的影响"),
                MemoryTurn(role="assistant", content="好的，请问目标读者是谁？"),
                MemoryTurn(role="user", content="大学教授和教育从业者"),
                MemoryTurn(role="assistant", content="已记录。大约多少字？"),
                MemoryTurn(role="user", content="2000 字左右"),
                MemoryTurn(role="assistant", content="已记录。我先写引言部分……[引言内容]"),
                MemoryTurn(role="user", content="引言很好，继续写第一部分：AI 辅助个性化学习"),
                MemoryTurn(role="assistant", content="[第一部分内容]"),
            ],
            question="当前文章写作任务的目标读者和字数要求分别是什么，已完成了哪些部分？",
            gold_answer="目标读者：大学教授和教育从业者，字数：约 2000 字，已完成引言和第一部分",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC010",
                "scenario": "long_task_working_memory",
            },
        ),
        MemoryTask(
            task_id="wm_003",
            session_id="session_wm_003",
            history=[
                MemoryTurn(role="user", content="x = 42"),
                MemoryTurn(role="assistant", content="已记录变量 x = 42。"),
                MemoryTurn(role="user", content="y = x * 2"),
                MemoryTurn(role="assistant", content="y = 84，已记录。"),
                MemoryTurn(role="user", content="z = y + x"),
                MemoryTurn(role="assistant", content="z = 126，已记录。"),
            ],
            question="当前 x、y、z 的值分别是多少？",
            gold_answer="x=42, y=84, z=126",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC010",
                "scenario": "variable_tracking",
            },
        ),
    ]

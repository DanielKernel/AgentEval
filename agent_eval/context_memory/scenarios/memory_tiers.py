"""UC002：分层记忆管理评测场景（自建）。

评测系统对热/温/冷记忆分层路由的能力：
- 热层（Working Memory）：当前会话活跃信息，应最快召回
- 温层（Recent Memory）：近期会话记忆，较快召回
- 冷层（Long-term Memory）：长期存储，需显式检索

对齐 UC：
- UC002：分层分级记忆管理
- 外部 benchmark 覆盖不足，**以自建为主**
"""

from __future__ import annotations

from typing import List

from agent_eval.context_memory.models import MemoryTask, MemoryTaskType, MemoryTurn


def get_memory_tier_tasks() -> List[MemoryTask]:
    """返回分层记忆管理场景的示例任务列表。"""
    return [
        MemoryTask(
            task_id="tier_hot_001",
            session_id="session_tier_001",
            history=[
                MemoryTurn(role="user", content="我要预订明天下午三点的会议室 A"),
                MemoryTurn(role="assistant", content="好的，已为您预订明天下午 3 点的会议室 A，请确认。"),
                MemoryTurn(role="user", content="确认"),
            ],
            question="我刚才预订的是哪个会议室？",
            gold_answer="会议室 A",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC002",
                "memory_tier": "hot",
                "scenario": "working_memory_recall",
                "expected_latency_ms": 100,
            },
        ),
        MemoryTask(
            task_id="tier_warm_001",
            session_id="session_tier_002",
            history=[
                MemoryTurn(role="user", content="我上周提到的项目代号是 Phoenix", timestamp="2024-03-05T10:00:00"),
                MemoryTurn(role="assistant", content="已记录项目代号 Phoenix。"),
                MemoryTurn(role="user", content="今天有什么新进展？", timestamp="2024-03-12T10:00:00"),
                MemoryTurn(role="assistant", content="Phoenix 项目本周完成了阶段一评审。"),
            ],
            question="我提到的项目代号是什么？",
            gold_answer="Phoenix",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC002",
                "memory_tier": "warm",
                "scenario": "recent_memory_recall",
                "days_ago": 7,
            },
        ),
        MemoryTask(
            task_id="tier_cold_001",
            session_id="session_tier_003",
            history=[
                MemoryTurn(
                    role="user",
                    content="我的生日是 1990 年 5 月 15 日",
                    timestamp="2023-01-01T00:00:00",
                ),
                MemoryTurn(role="assistant", content="已记录您的生日为 1990 年 5 月 15 日。"),
            ],
            question="我的生日是哪天？",
            gold_answer="1990 年 5 月 15 日",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC002",
                "memory_tier": "cold",
                "scenario": "long_term_memory_recall",
                "days_ago": 365,
            },
        ),
        MemoryTask(
            task_id="tier_priority_001",
            session_id="session_tier_004",
            history=[
                MemoryTurn(
                    role="user",
                    content="我的联系电话是 135-0000-0001",
                    timestamp="2023-06-01T00:00:00",
                ),
                MemoryTurn(role="assistant", content="已记录联系电话 135-0000-0001。"),
                MemoryTurn(
                    role="user",
                    content="我换号了，新电话是 186-0000-0002",
                    timestamp="2024-03-01T00:00:00",
                ),
                MemoryTurn(role="assistant", content="已更新联系电话为 186-0000-0002。"),
            ],
            question="我的联系电话是多少？",
            gold_answer="186-0000-0002",
            task_type=MemoryTaskType.UPDATE,
            metadata={
                "uc": "UC002",
                "scenario": "tier_update_priority",
                "old_value": "135-0000-0001",
            },
        ),
    ]

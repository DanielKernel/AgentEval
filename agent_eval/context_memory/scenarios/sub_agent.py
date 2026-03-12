"""UC014：子代理上下文隔离与摘要回传评测场景（自建）。

评测系统在多代理架构中的上下文管理能力：
- 子代理执行的上下文与主代理的隔离
- 子代理结果摘要回传的准确性
- 跨代理信息边界的正确处理

对齐 UC：
- UC014：子代理上下文隔离与摘要回传
- 外部 benchmark 基本无法覆盖，**以自建为主**
"""

from __future__ import annotations

from typing import List

from agent_eval.context_memory.models import MemoryTask, MemoryTaskType, MemoryTurn


def get_sub_agent_tasks() -> List[MemoryTask]:
    """返回子代理上下文隔离与摘要回传场景的示例任务列表。"""
    return [
        MemoryTask(
            task_id="subagent_001",
            session_id="session_main_001",
            history=[
                MemoryTurn(role="user", content="帮我分析这三份报告的财务数据"),
                MemoryTurn(
                    role="assistant",
                    content=(
                        "[派发子代理] 子代理-财务分析 开始处理报告 1/2/3。\n"
                        "[子代理-1 内部上下文: 报告 1 详情: 收入=100万，支出=80万，利润=20万]\n"
                        "[子代理-2 内部上下文: 报告 2 详情: 收入=150万，支出=100万，利润=50万]\n"
                        "[子代理-3 内部上下文: 报告 3 详情: 收入=200万，支出=130万，利润=70万]\n"
                        "[子代理摘要回传] 三份报告总收入=450万，总利润=140万，利润率=31.1%"
                    ),
                    metadata={
                        "sub_agents_dispatched": 3,
                        "summary_returned": "三份报告总收入=450万，总利润=140万",
                    },
                ),
            ],
            question="三份报告的总收入和总利润是多少？",
            gold_answer="总收入 450 万，总利润 140 万",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC014",
                "scenario": "sub_agent_summary_passback",
                "expected_behavior": "主代理正确接收并使用子代理摘要",
            },
        ),
        MemoryTask(
            task_id="subagent_002",
            session_id="session_main_002",
            history=[
                MemoryTurn(role="user", content="同时查询北京和上海两个城市的天气"),
                MemoryTurn(
                    role="assistant",
                    content=(
                        "[子代理-北京 内部: 查询结果=晴天28°C]\n"
                        "[子代理-上海 内部: 查询结果=阴天22°C]\n"
                        "[摘要]: 北京晴天28°C，上海阴天22°C"
                    ),
                    metadata={"sub_agents": ["beijing_agent", "shanghai_agent"]},
                ),
            ],
            question="上海今天的天气和气温是？",
            gold_answer="阴天，22°C",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC014",
                "scenario": "parallel_sub_agent_isolation",
                "expected_behavior": "两个子代理结果互不干扰，各自准确回传",
            },
        ),
        MemoryTask(
            task_id="subagent_003",
            session_id="session_main_003",
            history=[
                MemoryTurn(role="user", content="安全扫描子代理发现了哪些漏洞？"),
                MemoryTurn(
                    role="assistant",
                    content=(
                        "[子代理-安全扫描 内部上下文（机密）: CVE-2024-001 高危漏洞，密码明文存储]\n"
                        "[摘要回传（脱敏）]: 发现 1 个安全风险，已通知安全团队，详情不便在此对话中暴露"
                    ),
                    metadata={
                        "sub_agent": "security_scan_agent",
                        "context_classification": "confidential",
                        "summary_sanitized": True,
                    },
                ),
            ],
            question="安全扫描子代理发现的具体漏洞 CVE 编号是什么？",
            gold_answer="",
            task_type=MemoryTaskType.ABSTENTION,
            should_abstain=True,
            metadata={
                "uc": "UC014",
                "scenario": "sub_agent_context_confidentiality",
                "expected_behavior": "子代理内部机密上下文不应被主对话上下文直接暴露",
            },
        ),
        MemoryTask(
            task_id="subagent_004",
            session_id="session_main_004",
            history=[
                MemoryTurn(role="user", content="调用代码执行子代理计算 Fibonacci(10)"),
                MemoryTurn(
                    role="assistant",
                    content=(
                        "[子代理-代码执行 内部: 执行 fib(10)，中间结果: 0,1,1,2,3,5,8,13,21,34,55]\n"
                        "[摘要回传]: Fibonacci(10) = 55"
                    ),
                    metadata={"sub_agent": "code_executor"},
                ),
                MemoryTurn(role="user", content="谢谢，这是正确的"),
                MemoryTurn(role="assistant", content="很高兴能帮到您！"),
                MemoryTurn(role="user", content="现在帮我分析销售数据"),
                MemoryTurn(role="assistant", content="好的，请提供销售数据。"),
            ],
            question="之前代码执行子代理计算的结果是多少？",
            gold_answer="55",
            task_type=MemoryTaskType.QA,
            metadata={
                "uc": "UC014",
                "scenario": "sub_agent_result_retention",
                "expected_behavior": "主代理能从之前的子代理摘要中召回结果",
            },
        ),
    ]

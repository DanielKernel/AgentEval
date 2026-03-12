"""OpenClaw 插件接口（预留架构）。

本模块实现 OpenClaw 平台的插件协议，使上下文/记忆评测套件可以作为插件被 OpenClaw 集成。

通过在 pyproject.toml 中声明 entry point，OpenClaw 可自动发现并加载此插件::

    [project.entry-points."openclaw.plugins"]
    context_memory_eval = "agent_eval.plugins.openclaw:ContextMemoryEvalPlugin"

当前为预留架构，具体接口细节在与 OpenClaw 联调时按实际协议调整。

用法（OpenClaw 内部调用，示例）::

    from agent_eval.plugins.openclaw import ContextMemoryEvalPlugin

    plugin = ContextMemoryEvalPlugin()
    suite = plugin.get_eval_suite()
    plugin.on_service_ready({"base_url": "http://localhost:8080", "token": "xxx"})
    report = plugin.run()
    print(plugin.get_report())
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_eval.context_memory.adapters.rest import RESTServiceAdapter
from agent_eval.context_memory.harness import ContextMemoryEvalHarness, EvalMode
from agent_eval.context_memory.models import ContextMemoryReport
from agent_eval.context_memory.scenarios import get_all_self_built_tasks


class ContextMemoryEvalPlugin:
    """OpenClaw 上下文/记忆评测插件。

    插件生命周期：
    1. ``get_eval_suite()`` — OpenClaw 查询可用评测套件
    2. ``on_service_ready(service_info)`` — OpenClaw 通知被测服务已就绪
    3. ``run()`` — 执行评测
    4. ``get_report()`` — 获取评测报告

    Attributes
    ----------
    PLUGIN_NAME:
        插件唯一名称（OpenClaw 用于标识）。
    PLUGIN_VERSION:
        插件版本。
    SUPPORTED_BENCHMARKS:
        插件支持的 benchmark 列表。
    """

    PLUGIN_NAME = "context_memory_eval"
    PLUGIN_VERSION = "0.1.0"
    SUPPORTED_BENCHMARKS = ["BEIR", "LongMemEval", "LongBench v2", "LoCoMo", "RULER", "custom"]

    def __init__(self) -> None:
        self._harness: Optional[ContextMemoryEvalHarness] = None
        self._last_report: Optional[ContextMemoryReport] = None
        self._service_info: Dict[str, Any] = {}
        self._eval_config: Dict[str, Any] = {}

    def get_eval_suite(self) -> Dict[str, Any]:
        """返回插件支持的评测套件描述，供 OpenClaw 展示和选择。

        Returns
        -------
        dict
            包含插件元信息和支持的 benchmark 列表。
        """
        return {
            "plugin_name": self.PLUGIN_NAME,
            "version": self.PLUGIN_VERSION,
            "description": "上下文与记忆自动化评测套件",
            "supported_benchmarks": self.SUPPORTED_BENCHMARKS,
            "supported_modes": [m.value for m in EvalMode],
            "uc_coverage": {
                "BEIR": ["UC005", "UC012"],
                "LongMemEval": ["UC004", "UC008", "UC010", "UC013"],
                "LongBench v2": ["UC001", "UC007", "UC009"],
                "LoCoMo": ["UC009", "UC010"],
                "RULER": ["UC003", "UC004", "UC009"],
                "custom": ["UC002", "UC006", "UC011", "UC014"],
            },
        }

    def on_service_ready(self, service_info: Dict[str, Any]) -> None:
        """OpenClaw 通知被测服务已就绪，插件根据服务信息构建 Adapter。

        Parameters
        ----------
        service_info:
            被测服务信息字典，预期包含：
            - ``base_url``：服务根 URL
            - ``token``（可选）：认证 token
            - ``endpoints``（可选）：端点映射
            - ``benchmark``（可选）：要运行的 benchmark 名称
            - ``mode``（可选）：评测模式（offline/regression/stress）
            - ``max_samples``（可选）：最大样本数
        """
        self._service_info = service_info
        base_url = service_info.get("base_url", "")
        token = service_info.get("token")
        endpoints = service_info.get("endpoints", {})

        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        adapter = RESTServiceAdapter(
            base_url=base_url,
            endpoints=endpoints,
            headers=headers,
        )

        benchmark_name = service_info.get("benchmark", "custom")
        mode = service_info.get("mode", EvalMode.REGRESSION)
        max_samples = service_info.get("max_samples")

        self._harness = ContextMemoryEvalHarness(
            adapter=adapter,
            benchmark_name=benchmark_name,
            mode=mode,
            max_samples=max_samples,
        )
        self._eval_config = service_info

    def configure(self, config: Dict[str, Any]) -> None:
        """直接配置插件（不通过 on_service_ready 的替代接口）。

        允许 OpenClaw 之外的调用方手动配置插件。
        """
        self.on_service_ready(config)

    def run(self, tasks: Optional[List[Any]] = None) -> ContextMemoryReport:
        """执行评测并返回报告。

        Parameters
        ----------
        tasks:
            评测任务列表。若为 None，使用内置自建场景任务。
        """
        if self._harness is None:
            raise RuntimeError(
                "插件未初始化。请先调用 on_service_ready() 或 configure() 配置服务信息。"
            )
        if tasks is None:
            tasks = get_all_self_built_tasks()
        self._last_report = self._harness.run(tasks)
        return self._last_report

    def get_report(self) -> Optional[Dict[str, Any]]:
        """获取最近一次评测报告（JSON 可序列化格式）。

        Returns
        -------
        dict or None
            报告字典，若尚未运行评测则返回 None。
        """
        if self._last_report is None:
            return None
        return self._last_report.to_dict()

    def get_plugin_info(self) -> Dict[str, Any]:
        """返回插件自描述信息（供 OpenClaw 插件管理界面展示）。"""
        return {
            "name": self.PLUGIN_NAME,
            "version": self.PLUGIN_VERSION,
            "entry_point": "agent_eval.plugins.openclaw:ContextMemoryEvalPlugin",
            "initialized": self._harness is not None,
            "last_report_available": self._last_report is not None,
        }

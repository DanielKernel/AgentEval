"""LongMemEval Benchmark Loader。

LongMemEval 是专门针对长期记忆系统的评测 benchmark，覆盖四类子任务：
- QA：跨 session 记忆召回
- TEMPORAL：时序推理
- UPDATE：知识更新一致性
- ABSTENTION：适当拒绝回答

加载优先级：
1. 若已安装 ``datasets`` 库，从 HuggingFace 加载
2. 否则降级为本地 JSON/JSONL

参考：https://huggingface.co/datasets/xiaowu0162/LongMemEval
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_eval.context_memory.loaders.base import BenchmarkLoader
from agent_eval.context_memory.models import MemoryTask, MemoryTaskType, MemoryTurn


_TASK_TYPE_MAP = {
    "single_session_user": MemoryTaskType.QA,
    "single_session_assistant": MemoryTaskType.QA,
    "multi_session": MemoryTaskType.QA,
    "temporal_reasoning": MemoryTaskType.TEMPORAL,
    "knowledge_update": MemoryTaskType.UPDATE,
    "absence_of_answer": MemoryTaskType.ABSTENTION,
}


class LongMemEvalLoader(BenchmarkLoader):
    """LongMemEval dataset loader，输出 ``MemoryTask`` 列表。

    Parameters
    ----------
    hf_dataset_name:
        HuggingFace dataset 名称（默认 ``"xiaowu0162/LongMemEval"``）。
    task_types:
        过滤指定任务类型（默认加载全部类型）。
    data_dir:
        本地缓存目录。
    """

    def __init__(
        self,
        hf_dataset_name: str = "xiaowu0162/LongMemEval",
        task_types: Optional[List[MemoryTaskType]] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.hf_dataset_name = hf_dataset_name
        self.task_types = set(task_types) if task_types else None
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".cache" / "agent_eval" / "longmemeval"

    def load(
        self,
        split: str = "test",
        max_samples: Optional[int] = None,
        local_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> List[MemoryTask]:
        if local_path:
            raw = self.load_from_local(local_path, max_samples)
            return self._apply_limit(self._convert(raw), max_samples)

        if self._check_library("datasets"):
            try:
                return self._load_from_hf(split, max_samples)
            except Exception:
                pass

        local_file = self.data_dir / f"{split}.jsonl"
        if local_file.exists():
            raw = self.load_from_local(local_file, max_samples)
            return self._apply_limit(self._convert(raw), max_samples)

        raise RuntimeError(
            f"无法加载 LongMemEval 数据集。\n"
            f"请安装 datasets 库（pip install datasets）或将数据下载到 {local_file}。\n"
            f"本地格式（JSONL）：每行包含 task_id, question, answer, history, task_type 字段。"
        )

    def _load_from_hf(self, split: str, max_samples: Optional[int]) -> List[MemoryTask]:
        from datasets import load_dataset

        dataset = load_dataset(self.hf_dataset_name, split=split)
        raw = list(dataset)
        return self._apply_limit(self._convert(raw), max_samples)

    def _convert(self, raw: List[Dict[str, Any]]) -> List[MemoryTask]:
        tasks: List[MemoryTask] = []
        for item in raw:
            task_type_str = item.get("task_type", "single_session_user")
            task_type = _TASK_TYPE_MAP.get(task_type_str, MemoryTaskType.QA)

            if self.task_types and task_type not in self.task_types:
                continue

            history = self._parse_history(item.get("history", []))
            should_abstain = task_type == MemoryTaskType.ABSTENTION

            tasks.append(
                MemoryTask(
                    task_id=str(item.get("question_id") or item.get("id", f"lme_{len(tasks)}")),
                    session_id=str(item.get("session_id", f"session_{len(tasks)}")),
                    history=history,
                    question=item.get("question", ""),
                    gold_answer=item.get("answer", ""),
                    task_type=task_type,
                    should_abstain=should_abstain,
                    metadata={"task_type_str": task_type_str},
                )
            )
        return tasks

    @staticmethod
    def _parse_history(history: Any) -> List[MemoryTurn]:
        """解析多种格式的历史对话记录。"""
        if not history:
            return []
        if isinstance(history, list):
            turns = []
            for item in history:
                if isinstance(item, dict):
                    turns.append(
                        MemoryTurn(
                            role=item.get("role", item.get("speaker", "user")),
                            content=item.get("content", item.get("utterance", "")),
                            timestamp=item.get("timestamp"),
                        )
                    )
                elif isinstance(item, str):
                    turns.append(MemoryTurn(role="user", content=item))
            return turns
        if isinstance(history, str):
            return [MemoryTurn(role="user", content=history)]
        return []

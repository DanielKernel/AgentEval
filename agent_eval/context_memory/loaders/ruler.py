"""RULER Benchmark Loader。

RULER（Realistic Long-context Understanding and Evaluation）
用于测量模型在不同上下文长度下的 accuracy 退化曲线，支持：
- NIAH（Needle-in-a-Haystack）变体
- 多针检索（Multi-hop）
- 问答任务

评测目标：
- accuracy vs context_length 曲线
- effective context length（有效上下文长度）
- degradation slope（退化斜率）

加载优先级：
1. 若已安装 ``datasets`` 库，从 HuggingFace 加载
2. 否则降级为本地 JSON/JSONL

参考：https://github.com/hsiehjackson/RULER
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from agent_eval.context_memory.loaders.base import BenchmarkLoader
from agent_eval.context_memory.models import ContextQualityTask, Document


class RULERLoader(BenchmarkLoader):
    """RULER dataset loader，输出 ``ContextQualityTask`` 列表（含 context_length 标注）。

    Parameters
    ----------
    hf_dataset_name:
        HuggingFace dataset 名称（默认 ``"hsiehjackson/RULER"``）。
    context_lengths:
        只加载指定长度的数据（默认全部长度）。
        常见长度如 ``[4096, 8192, 16384, 32768, 65536, 131072]``。
    task_type:
        RULER 子任务类型，如 ``"niah_single_1"``、``"qa_1"`` 等。
    data_dir:
        本地缓存目录。
    """

    RULER_LENGTHS = [4096, 8192, 16384, 32768, 65536, 131072]

    def __init__(
        self,
        hf_dataset_name: str = "hsiehjackson/RULER",
        context_lengths: Optional[List[int]] = None,
        task_type: Optional[str] = None,
        data_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.hf_dataset_name = hf_dataset_name
        self.context_lengths = set(context_lengths) if context_lengths else None
        self.task_type = task_type
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".cache" / "agent_eval" / "ruler"

    def load(
        self,
        split: str = "test",
        max_samples: Optional[int] = None,
        local_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> List[ContextQualityTask]:
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
            f"无法加载 RULER 数据集。\n"
            f"请安装 datasets 库（pip install datasets）或将数据下载到 {local_file}。\n"
            f"本地格式（JSONL）：每行包含 index, input, outputs, length, type 字段。"
        )

    def _load_from_hf(self, split: str, max_samples: Optional[int]) -> List[ContextQualityTask]:
        from datasets import load_dataset

        all_tasks: List[ContextQualityTask] = []
        subset = self.task_type or "niah_single_1"
        for length in (self.context_lengths or self.RULER_LENGTHS):
            try:
                dataset = load_dataset(self.hf_dataset_name, f"{subset}_{length}", split=split)
                tasks = self._convert(list(dataset), context_length=length)
                all_tasks.extend(tasks)
                if max_samples and len(all_tasks) >= max_samples:
                    break
            except Exception:
                continue
        return self._apply_limit(all_tasks, max_samples)

    def _convert(
        self,
        raw: List[Dict[str, Any]],
        context_length: Optional[int] = None,
    ) -> List[ContextQualityTask]:
        tasks: List[ContextQualityTask] = []
        for item in raw:
            cl = context_length or item.get("length") or item.get("context_length") or 0
            if self.context_lengths and cl not in self.context_lengths:
                continue

            input_text = item.get("input", "") or item.get("context", "")
            outputs = item.get("outputs", []) or item.get("answers", [])
            if isinstance(outputs, str):
                outputs = [outputs]
            gold_answer = outputs[0] if outputs else ""

            doc = Document(
                doc_id=str(item.get("index", f"ruler_{len(tasks)}")),
                text=input_text,
            )

            tasks.append(
                ContextQualityTask(
                    task_id=str(item.get("index", f"ruler_{len(tasks)}")),
                    question=item.get("query", item.get("question", "")),
                    gold_answer=gold_answer,
                    documents=[doc],
                    domain=item.get("type", self.task_type or "ruler"),
                    metadata={
                        "context_length": cl,
                        "all_answers": outputs,
                        "ruler_type": item.get("type", ""),
                    },
                )
            )
        return tasks

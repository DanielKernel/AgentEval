"""抽象 BenchmarkLoader 基类与本地 JSON/JSONL 降级加载逻辑。

设计原则：
- 优先使用外部库（datasets、beir 等）加载数据集
- 若外部库不可用，自动降级为从本地 JSON/JSONL 文件加载
- 所有 Loader 输出统一的框架内数据模型（RetrievalTask / MemoryTask / ContextQualityTask）
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Type, TypeVar, Union

T = TypeVar("T")


class BenchmarkLoader(ABC):
    """所有 benchmark loader 的抽象基类。

    子类须实现 :meth:`load` 方法。推荐先尝试用外部库加载，失败后降级到 :meth:`load_from_local`。
    """

    @abstractmethod
    def load(
        self,
        split: str = "test",
        max_samples: Optional[int] = None,
        local_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> List[Any]:
        """加载数据集，返回框架内任务对象列表。

        Parameters
        ----------
        split:
            数据集分片（如 "test"、"dev"）。
        max_samples:
            最大样本数（None 表示加载全量）。
        local_path:
            本地文件路径（用于降级加载）。
        """
        ...

    def load_from_local(
        self,
        local_path: Union[str, Path],
        max_samples: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """从本地 JSON 或 JSONL 文件加载原始数据。

        支持格式：
        - ``.json``：JSON 数组 ``[{...}, ...]``
        - ``.jsonl``：每行一个 JSON 对象

        Returns
        -------
        List[dict]
            原始数据字典列表（由子类进一步转换为任务模型）。
        """
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"本地数据文件不存在：{path}")

        raw: List[Dict[str, Any]] = []
        suffix = path.suffix.lower()

        if suffix == ".jsonl":
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        raw.append(json.loads(line))
                        if max_samples and len(raw) >= max_samples:
                            break
        elif suffix == ".json":
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                raw = data
            elif isinstance(data, dict):
                raw = list(data.values())
            else:
                raise ValueError(f"不支持的 JSON 格式：{type(data)}")
            if max_samples:
                raw = raw[:max_samples]
        else:
            raise ValueError(f"不支持的文件格式：{suffix}（仅支持 .json 和 .jsonl）")

        return raw

    @staticmethod
    def _check_library(lib_name: str) -> bool:
        """检查外部库是否可用。"""
        import importlib.util
        return importlib.util.find_spec(lib_name) is not None

    def _apply_limit(self, data: List[Any], max_samples: Optional[int]) -> List[Any]:
        """截取 max_samples 条数据。"""
        if max_samples is not None and max_samples > 0:
            return data[:max_samples]
        return data

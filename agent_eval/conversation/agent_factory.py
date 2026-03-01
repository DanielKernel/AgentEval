"""从配置构建被测对话 Agent，支持内置类型与自定义模块/可调用。"""

from __future__ import annotations

import importlib
from typing import Any, Dict, List

from agent_eval.conversation.agent import DialogueAgent
from agent_eval.conversation.sample_agent import EchoAgent, FixedResponseAgent


def build_agent(agent_config: Dict[str, Any]) -> DialogueAgent:
    """根据单条 agent 配置构建 DialogueAgent 实例。

    配置格式：
    - 内置
      - {"id": "xxx", "type": "echo"}
      - {"id": "xxx", "type": "fixed", "params": {"response": "固定回复"}}
    - 自定义（二选一）
      - {"id": "xxx", "type": "custom", "module": "mymod.agents", "class": "MyAgent", "params": {}}
      - {"id": "xxx", "type": "custom", "callable": "mymod:create_agent", "params": {}}
    """
    tid = agent_config.get("id", "default")
    type_ = agent_config.get("type", "echo")
    params = agent_config.get("params") or {}

    if type_ == "echo":
        return EchoAgent()
    if type_ == "fixed":
        return FixedResponseAgent(**params)
    if type_ == "custom":
        return _build_custom_agent(agent_config)
    raise ValueError(f"Unknown agent type: {type_!r} (agent id={tid!r})")


def _build_custom_agent(agent_config: Dict[str, Any]) -> DialogueAgent:
    module = agent_config.get("module")
    class_name = agent_config.get("class")
    callable_path = agent_config.get("callable")
    params = agent_config.get("params") or {}

    if callable_path:
        mod_path, _, attr = callable_path.partition(":")
        if not attr:
            raise ValueError(
                f"custom agent 'callable' must be 'module:callable_name', got {callable_path!r}"
            )
        mod = importlib.import_module(mod_path)
        fn = getattr(mod, attr)
        if not callable(fn):
            raise ValueError(f"custom agent callable {callable_path!r} is not callable")
        instance = fn(**params) if params else fn()
        if not (hasattr(instance, "run") and callable(getattr(instance, "run"))):
            raise ValueError(
                f"custom callable must return an object with a run(task)->Transcript method, got {type(instance)}"
            )
        return instance

    if module and class_name:
        mod = importlib.import_module(module)
        cls = getattr(mod, class_name)
        return cls(**params) if params else cls()

    raise ValueError(
        "custom agent must specify either 'module' + 'class' or 'callable'"
    )


def build_agents(agents_config: List[Dict[str, Any]]) -> Dict[str, DialogueAgent]:
    """根据 agents 列表配置构建多个 Agent，返回 id -> agent 的映射。"""
    out = {}
    for cfg in agents_config:
        aid = cfg.get("id", "default")
        if aid in out:
            raise ValueError(f"Duplicate agent id: {aid!r}")
        out[aid] = build_agent(cfg)
    return out

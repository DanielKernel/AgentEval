# 第 10 章：代码示例与教程

## 10.1 引言

### 10.1.1 实践学习的重要性

理论知识为理解 AI Agent 评测提供了基础，但真正的掌握来自实践。本章通过具体的代码示例和详细教程，帮助读者：

1. **快速上手**：从零开始建立评测环境
2. **深入理解**：通过实际代码学习核心概念
3. **解决实际问题**：针对常见场景提供解决方案
4. **构建自定义系统**：满足特定需求的评测框架

### 10.1.2 学习路径建议

根据不同的学习目标，建议采取以下路径：

- **初学者**：从 10.2 节基础环境搭建开始，逐步完成所有示例
- **有经验的开发者**：直接阅读 10.3-10.5 节，学习高级模式
- **特定需求用户**：针对性地学习相关章节（如工具使用、安全评估）

## 10.2 基础环境搭建教程

### 10.2.1 环境要求检查

#### 系统要求验证脚本
```python
# check_requirements.py
import sys
import subprocess
import platform

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    return version.major == 3 and version.minor >= 8

def check_docker():
    """检查 Docker 是否可用"""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_system_resources():
    """检查系统资源"""
    system = platform.system()

    if system == "Darwin":  # macOS
        cmd = ["sysctl", "-n", "hw.ncpu"]
    elif system == "Linux":
        cmd = ["nproc"]
    else:
        cmd = ["echo", "1"]

    try:
        cpu_count = int(subprocess.run(cmd, capture_output=True, text=True).stdout.strip())
        return cpu_count >= 4
    except:
        return False

def main():
    """主检查函数"""
    checks = {
        "Python 版本 (≥3.8)": check_python_version(),
        "Docker 可用性": check_docker(),
        "CPU 核心 (≥4)": check_system_resources()
    }

    print("=" * 50)
    print("AI Agent 评测环境要求检查")
    print("=" * 50)

    all_passed = True
    for check_name, result in checks.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{check_name}: {status}")
        if not result:
            all_passed = False

    print("=" * 50)

    if all_passed:
        print("所有检查通过，可以开始环境搭建！")
        return True
    else:
        print("部分检查失败，请先满足系统要求。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

### 10.2.2 基础评测环境搭建

#### 步骤 1：创建项目结构
```bash
# 创建项目目录
mkdir ai-agent-evaluation && cd ai-agent-evaluation

# 创建标准目录结构
mkdir -p src/{agents,environments,tasks,evaluation}
mkdir -p config/{agents,environments,tasks}
mkdir -p data/{raw,processed,results}
mkdir -p tests/{unit,integration}
mkdir -p docker/{images,compose}

# 创建基本文件
touch requirements.txt
touch Dockerfile
touch docker-compose.yml
touch setup.py
touch README.md
```

#### 步骤 2：编写基础依赖配置
```txt
# requirements.txt
# 核心依赖
numpy>=1.21.0
pandas>=1.3.0
scipy>=1.7.0

# 机器学习与AI
torch>=2.0.0
transformers>=4.30.0
openai>=0.28.0
anthropic>=0.5.0

# Web 与网络
requests>=2.28.0
beautifulsoup4>=4.11.0
selenium>=4.10.0
playwright>=1.36.0

# 数据与测试
pytest>=7.0.0
pytest-cov>=4.0.0
pandas>=1.5.0

# 工具与实用程序
python-dotenv>=1.0.0
pyyaml>=6.0
loguru>=0.7.0
```

#### 步骤 3：创建基础环境类
```python
# src/environments/base_environment.py
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BaseEnvironment(ABC):
    """基础环境抽象类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state = None
        self.observation_space = None
        self.action_space = None

    @abstractmethod
    def reset(self, seed: Optional[int] = None) -> Any:
        """
        重置环境到初始状态

        Args:
            seed: 随机种子，用于可重复性

        Returns:
            初始观察
        """
        pass

    @abstractmethod
    def step(self, action: Any) -> tuple:
        """
        执行动作并返回结果

        Args:
            action: 要执行的动作

        Returns:
            (observation, reward, done, info) 元组
        """
        pass

    @abstractmethod
    def render(self, mode: str = 'human') -> Optional[Any]:
        """
        渲染环境状态

        Args:
            mode: 渲染模式 ('human', 'rgb_array', 'ansi')

        Returns:
            渲染结果，取决于模式
        """
        pass

    def close(self):
        """清理环境资源"""
        logger.info("Closing environment")

    def get_state(self) -> Any:
        """获取当前环境状态"""
        return self.state

    def set_state(self, state: Any):
        """设置环境状态（用于精确控制）"""
        self.state = state
        logger.debug(f"Environment state set to: {state}")
```

#### 步骤 4：创建基础 Agent 类
```python
# src/agents/base_agent.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """基础 Agent 抽象类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.memory = []  # 存储交互历史
        self.tools = {}   # 可用工具

    @abstractmethod
    def act(self, observation: Any) -> Any:
        """
        根据观察选择动作

        Args:
            observation: 当前环境观察

        Returns:
            要执行的动作
        """
        pass

    def learn(self, experience: Dict[str, Any]):
        """
        从经验中学习

        Args:
            experience: 学习经验，包含观察、动作、奖励等
        """
        self.memory.append(experience)
        logger.debug(f"Agent learned from experience: {experience}")

    def register_tool(self, tool_name: str, tool: Any):
        """
        注册工具

        Args:
            tool_name: 工具名称
            tool: 工具对象
        """
        self.tools[tool_name] = tool
        logger.info(f"Tool registered: {tool_name}")

    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        使用工具

        Args:
            tool_name: 要使用的工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")

        tool = self.tools[tool_name]
        try:
            result = tool.execute(**kwargs)
            logger.debug(f"Tool {tool_name} executed successfully: {result}")
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            raise
```

#### 步骤 5：创建评测运行器
```python
# src/evaluation/evaluation_runner.py
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """评测结果数据类"""
    task_id: str
    success: bool
    score: float
    execution_time: float
    steps: int
    errors: List[str]
    metadata: Dict[str, Any]

class EvaluationRunner:
    """评测运行器"""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        # 初始化环境
        self.environment = self._create_environment()

        # 初始化 Agent
        self.agent = self._create_agent()

    def _create_environment(self):
        """创建环境实例"""
        env_config = self.config["environment"]
        env_module = __import__(
            f"src.environments.{env_config['type']}",
            fromlist=["Environment"]
        )
        return env_module.Environment(env_config["config"])

    def _create_agent(self):
        """创建 Agent 实例"""
        agent_config = self.config["agent"]
        agent_module = __import__(
            f"src.agents.{agent_config['type']}",
            fromlist=["Agent"]
        )
        return agent_module.Agent(agent_config["config"])

    def run_single_task(self, task: Dict[str, Any]) -> EvaluationResult:
        """
        运行单个任务评测

        Args:
            task: 任务定义

        Returns:
            评测结果
        """
        logger.info(f"Starting evaluation for task: {task['id']}")

        start_time = time.time()
        steps = 0
        errors = []

        try:
            # 重置环境
            observation = self.environment.reset(seed=task.get("seed"))

            # 执行任务
            done = False
            while not done:
                # Agent 选择动作
                action = self.agent.act(observation)

                # 执行动作
                observation, reward, done, info = self.environment.step(action)

                # 记录步骤
                steps += 1

                # 检查是否超步
                if steps > self.config.get("max_steps", 100):
                    done = True
                    errors.append("Exceeded maximum steps")

            # 评估任务完成度
            success, score = self._evaluate_task_completion(task)

        except Exception as e:
            logger.error(f"Task evaluation failed: {e}")
            success = False
            score = 0.0
            errors.append(str(e))

        # 计算执行时间
        execution_time = time.time() - start_time

        # 创建结果对象
        result = EvaluationResult(
            task_id=task["id"],
            success=success,
            score=score,
            execution_time=execution_time,
            steps=steps,
            errors=errors,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "agent_type": self.config["agent"]["type"],
                "environment_type": self.config["environment"]["type"]
            }
        )

        logger.info(f"Task evaluation completed: success={success}, score={score}")
        return result

    def _evaluate_task_completion(self, task: Dict[str, Any]) -> tuple:
        """
        评估任务完成度

        Args:
            task: 任务定义

        Returns:
            (success, score) 元组
        """
        # 获取当前环境状态
        current_state = self.environment.get_state()

        # 根据任务定义评估
        success_criteria = task.get("success_criteria", [])

        # 简单实现：检查所有条件是否满足
        criteria_met = []
        for criterion in success_criteria:
            try:
                met = self._check_criterion(criterion, current_state)
                criteria_met.append(met)
            except Exception as e:
                logger.warning(f"Criterion check failed: {e}")
                criteria_met.append(False)

        # 计算成功率和分数
        success = all(criteria_met)
        score = sum(criteria_met) / len(criteria_met) if criteria_met else 0.0

        return success, score

    def _check_criterion(self, criterion: Dict[str, Any], state: Any) -> bool:
        """
        检查单个条件

        Args:
            criterion: 条件定义
            state: 当前状态

        Returns:
            条件是否满足
        """
        # 简单实现：根据条件类型检查
        criterion_type = criterion.get("type")

        if criterion_type == "state_value":
            key = criterion["key"]
            expected = criterion["expected"]
            actual = state.get(key)

            if "comparison" in criterion:
                comp = criterion["comparison"]
                if comp == "equals":
                    return actual == expected
                elif comp == "greater_than":
                    return actual > expected
                elif comp == "less_than":
                    return actual < expected

            return actual == expected

        elif criterion_type == "action_performed":
            action_type = criterion["action_type"]
            # 检查 Agent 是否执行了特定动作
            # 需要根据具体实现进行调整
            return True

        else:
            logger.warning(f"Unknown criterion type: {criterion_type}")
            return False
```

### 10.2.3 运行第一个评测

#### 配置示例
```json
# config/evaluation_config.json
{
  "name": "basic_evaluation",
  "description": "基础评测示例",

  "environment": {
    "type": "simple_text",
    "config": {
      "initial_state": "Welcome to the text environment. You need to find the hidden word.",
      "target_word": "apple"
    }
  },

  "agent": {
    "type": "random_agent",
    "config": {
      "action_space": ["guess_a", "guess_b", "guess_c", "give_up"],
      "preferences": {
        "risk_tolerance": 0.5
      }
    }
  },

  "tasks": [
    {
      "id": "task_001",
      "description": "Find the hidden word in the text environment.",
      "success_criteria": [
        {
          "type": "state_value",
          "key": "word_found",
          "expected": true
        }
      ],
      "metadata": {
        "difficulty": "easy",
        "estimated_time": 60
      }
    }
  ],

  "evaluation": {
    "max_steps": 20,
    "timeout_seconds": 300,
    "metrics": ["success_rate", "average_score", "average_steps"]
  }
}
```

#### 运行脚本
```python
# run_evaluation.py
import json
import logging
from src.evaluation.evaluation_runner import EvaluationRunner

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    # 加载配置
    config_path = "config/evaluation_config.json"

    # 创建评测运行器
    runner = EvaluationRunner(config_path)

    # 加载任务
    with open(config_path, 'r') as f:
        config = json.load(f)

    tasks = config["tasks"]

    # 运行评测
    results = []
    for task in tasks:
        result = runner.run_single_task(task)
        results.append(result)

        # 输出结果
        print(f"Task {task['id']}:")
        print(f"  Success: {result.success}")
        print(f"  Score: {result.score:.2f}")
        print(f"  Steps: {result.steps}")
        print(f"  Time: {result.execution_time:.2f}s")
        print()

    # 生成总结
    success_count = sum(1 for r in results if r.success)
    total_tasks = len(results)
    success_rate = success_count / total_tasks if total_tasks > 0 else 0

    avg_score = sum(r.score for r in results) / total_tasks if total_tasks > 0 else 0
    avg_steps = sum(r.steps for r in results) / total_tasks if total_tasks > 0 else 0

    print("=" * 50)
    print("评测总结")
    print("=" * 50)
    print(f"任务总数: {total_tasks}")
    print(f"成功任务: {success_count}")
    print(f"成功率: {success_rate:.2%}")
    print(f"平均分数: {avg_score:.2f}")
    print(f"平均步骤数: {avg_steps:.1f}")

    # 保存结果
    output_data = {
        "summary": {
            "success_rate": success_rate,
            "average_score": avg_score,
            "average_steps": avg_steps
        },
        "detailed_results": [
            {
                "task_id": r.task_id,
                "success": r.success,
                "score": r.score,
                "execution_time": r.execution_time,
                "steps": r.steps,
                "errors": r.errors
            }
            for r in results
        ]
    }

    with open("data/results/evaluation_results.json", 'w') as f:
        json.dump(output_data, f, indent=2)

    print("\n结果已保存到: data/results/evaluation_results.json")

if __name__ == "__main__":
    main()
```

## 10.3 高级 Agent 实现教程

### 10.3.1 基于工具的 Agent

#### 工具定义框架
```python
# src/agents/tool_based_agent.py
from typing import Dict, Any, List, Optional
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class ToolBasedAgent(BaseAgent):
    """基于工具的 Agent"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.planning_model = self._load_planning_model()
        self.execution_model = self._load_execution_model()
        self.reasoning_history = []

    def _load_planning_model(self):
        """加载规划模型"""
        # 这里可以集成不同的模型
        model_type = self.config.get("planning_model", "default")

        if model_type == "llm":
            from src.models.llm_planner import LLMPlanner
            return LLMPlanner(self.config.get("llm_config", {}))
        else:
            from src.models.rule_based_planner import RuleBasedPlanner
            return RuleBasedPlanner()

    def _load_execution_model(self):
        """加载执行模型"""
        model_type = self.config.get("execution_model", "default")

        if model_type == "llm":
            from src.models.llm_executor import LLMExecutor
            return LLMExecutor(self.config.get("llm_config", {}))
        else:
            from src.models.rule_based_executor import RuleBasedExecutor
            return RuleBasedExecutor()

    def act(self, observation: Any) -> Any:
        """
        基于观察选择动作，包括工具使用

        Args:
            observation: 环境观察

        Returns:
            动作，可能包括工具调用
        """
        logger.debug(f"Agent received observation: {observation}")

        # 1. 分析观察
        analysis = self._analyze_observation(observation)

        # 2. 规划行动
        plan = self._plan_actions(analysis, observation)

        # 3. 选择当前动作
        current_action = self._select_current_action(plan)

        # 4. 记录推理历史
        self.reasoning_history.append({
            "observation": observation,
            "analysis": analysis,
            "plan": plan,
            "action": current_action
        })

        return current_action

    def _analyze_observation(self, observation: Any) -> Dict[str, Any]:
        """分析观察"""
        analysis = {
            "type": "unknown",
            "key_elements": [],
            "possible_actions": []
        }

        # 根据观察类型进行分析
        if isinstance(observation, str):
            # 文本观察
            analysis["type"] = "text"
            analysis["key_elements"] = self._extract_keywords(observation)
            analysis["possible_actions"] = self._suggest_text_actions(observation)

        elif isinstance(observation, dict):
            # 结构化观察
            analysis["type"] = "structured"
            analysis["key_elements"] = list(observation.keys())
            analysis["possible_actions"] = self._suggest_structured_actions(observation)

        return analysis

    def _plan_actions(self, analysis: Dict[str, Any], observation: Any) -> List[Dict[str, Any]]:
        """规划行动序列"""
        # 使用规划模型生成计划
        plan = self.planning_model.generate_plan(
            observation=observation,
            analysis=analysis,
            available_tools=self.tools
        )

        logger.debug(f"Generated plan with {len(plan)} steps")

        return plan

    def _select_current_action(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从计划中选择当前动作"""
        if not plan:
            return {"type": "no_action", "reason": "empty_plan"}

        # 选择计划中的第一个动作
        action = plan[0]

        # 如果是工具调用，验证工具可用性
        if action.get("type") == "tool_call":
            tool_name = action.get("tool_name")
            if tool_name not in self.tools:
                return {
                    "type": "error",
                    "reason": f"tool_not_found: {tool_name}"
                }

        return action

    def use_tool_with_planning(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        带规划的工具使用

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            执行结果和相关信息
        """
        # 检查工具是否可用
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"Tool {tool_name} not found",
                "reason": "tool_not_available"
            }

        # 获取工具
        tool = self.tools[tool_name]

        # 规划工具使用
        planning_result = self.planning_model.plan_tool_use(
            tool=tool,
            parameters=kwargs,
            context=self.reasoning_history
        )

        if not planning_result["feasible"]:
            return {
                "success": False,
                "error": planning_result["reason"],
                "reason": "planning_failed"
            }

        # 执行工具
        try:
            execution_result = tool.execute(**kwargs)

            # 记录工具使用
            tool_use_record = {
                "tool": tool_name,
                "parameters": kwargs,
                "result": execution_result,
                "planning_info": planning_result,
                "timestamp": datetime.now().isoformat()
            }

            self.memory.append(tool_use_record)

            return {
                "success": True,
                "result": execution_result,
                "planning_info": planning_result,
                "metadata": tool_use_record
            }

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")

            return {
                "success": False,
                "error": str(e),
                "reason": "execution_failed"
            }
```

### 10.3.2 实现示例工具

#### 计算器工具
```python
# src/tools/calculator.py
from typing import Any, Dict
import math
import operator

class CalculatorTool:
    """计算器工具"""

    def __init__(self):
        self.supported_operations = {
            'add': operator.add,
            'subtract': operator.sub,
            'multiply': operator.mul,
            'divide': operator.truediv,
            'power': operator.pow,
            'sqrt': math.sqrt,
            'log': math.log,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan
        }

    def execute(self, operation: str, **kwargs) -> Dict[str, Any]:
        """
        执行计算操作

        Args:
            operation: 操作类型
            **kwargs: 操作参数

        Returns:
            计算结果和元数据
        """
        if operation not in self.supported_operations:
            return {
                "success": False,
                "error": f"Unsupported operation: {operation}",
                "supported_operations": list(self.supported_operations.keys())
            }

        # 获取操作函数
        op_func = self.supported_operations[operation]

        try:
            # 根据操作类型处理参数
            if operation in ['add', 'subtract', 'multiply', 'divide', 'power']:
                if 'a' not in kwargs or 'b' not in kwargs:
                    return {
                        "success": False,
                        "error": f"Operation {operation} requires parameters 'a' and 'b'"
                    }
                result = op_func(kwargs['a'], kwargs['b'])

            elif operation in ['sqrt', 'log', 'sin', 'cos', 'tan']:
                if 'value' not in kwargs:
                    return {
                        "success": False,
                        "error": f"Operation {operation} requires parameter 'value'"
                    }

                # 特殊处理log函数
                if operation == 'log':
                    if 'base' in kwargs:
                        result = math.log(kwargs['value'], kwargs['base'])
                    else:
                        result = math.log(kwargs['value'])
                else:
                    result = op_func(kwargs['value'])

            else:
                return {
                    "success": False,
                    "error": f"Unexpected operation: {operation}"
                }

            # 构建响应
            response = {
                "success": True,
                "result": result,
                "operation": operation,
                "parameters": kwargs,
                "metadata": {
                    "operation_duration": "instant",
                    "result_type": type(result).__name__,
                    "precision": self._get_precision(result)
                }
            }

            return response

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "parameters": kwargs
            }

    def _get_precision(self, value: Any) -> str:
        """获取数值精度信息"""
        if isinstance(value, (int, float)):
            if isinstance(value, int):
                return "exact"
            else:
                # 检查是否为整数（如1.0）
                if value.is_integer():
                    return "exact"
                else:
                    return f"approx_{len(str(value).split('.')[1])}d"
        else:
            return "non-numeric"
```

#### 文件操作工具
```python
# src/tools/file_operations.py
import os
import json
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path
import hashlib

class FileOperationsTool:
    """文件操作工具"""

    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path).resolve()
        self.allowed_extensions = ['.txt', '.json', '.csv', '.py', '.md']
        self.max_file_size = 10 * 1024 * 1024  # 10MB

        # 确保基础目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        执行文件操作

        Args:
            action: 操作类型
            **kwargs: 操作参数

        Returns:
            操作结果
        """
        actions = {
            'read': self._read_file,
            'write': self._write_file,
            'list': self._list_files,
            'create': self._create_file,
            'delete': self._delete_file,
            'move': self._move_file,
            'copy': self._copy_file,
            'info': self._file_info
        }

        if action not in actions:
            return {
                "success": False,
                "error": f"Unsupported action: {action}",
                "supported_actions": list(actions.keys())
            }

        # 执行操作
        try:
            return actions[action](**kwargs)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action,
                "parameters": kwargs
            }

    def _validate_path(self, path: str) -> Path:
        """验证路径安全性"""
        target_path = (self.base_path / path).resolve()

        # 确保路径在基础目录内
        if not str(target_path).startswith(str(self.base_path)):
            raise ValueError("Path traversal attempt detected")

        # 检查文件扩展名
        if target_path.suffix and target_path.suffix not in self.allowed_extensions:
            raise ValueError(f"Unsupported file extension: {target_path.suffix}")

        return target_path

    def _read_file(self, path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """读取文件"""
        target_path = self._validate_path(path)

        if not target_path.exists():
            return {
                "success": False,
                "error": "File does not exist",
                "path": str(target_path)
            }

        # 检查文件大小
        file_size = target_path.stat().st_size
        if file_size > self.max_file_size:
            return {
                "success": False,
                "error": f"File too large: {file_size} > {self.max_file_size}",
                "path": str(target_path),
                "file_size": file_size
            }

        # 读取文件
        try:
            content = target_path.read_text(encoding=encoding)

            return {
                "success": True,
                "content": content,
                "encoding": encoding,
                "file_size": file_size,
                "modified_time": target_path.stat().st_mtime,
                "metadata": {
                    "file_type": target_path.suffix,
                    "hash": hashlib.md5(content.encode(encoding)).hexdigest()
                }
            }
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                content = target_path.read_bytes().decode('latin-1')
                return {
                    "success": True,
                    "content": content,
                    "encoding": "latin-1",
                    "warning": "File decoded with latin-1 encoding"
                }
            except:
                return {
                    "success": False,
                    "error": "Unable to decode file",
                    "path": str(target_path)
                }

    def _write_file(self, path: str, content: str, mode: str = 'w', encoding: str = 'utf-8') -> Dict[str, Any]:
        """写入文件"""
        target_path = self._validate_path(path)

        # 确保目录存在
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        try:
            if mode == 'a' and target_path.exists():
                with open(target_path, 'a', encoding=encoding) as f:
                    f.write(content)
            else:
                target_path.write_text(content, encoding=encoding)

            # 获取文件信息
            info = self._get_file_info(target_path)

            return {
                "success": True,
                "path": str(target_path),
                "file_size": info["file_size"],
                "modified_time": info["modified_time"],
                "metadata": {
                    "hash": hashlib.md5(content.encode(encoding)).hexdigest(),
                    "lines": len(content.splitlines())
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "path": str(target_path)
            }

    def _list_files(self, directory: str = '.', pattern: str = '*', recursive: bool = False) -> Dict[str, Any]:
        """列出文件"""
        target_dir = self._validate_path(directory)

        if not target_dir.exists():
            return {
                "success": False,
                "error": "Directory does not exist",
                "directory": str(target_dir)
            }

        if not target_dir.is_dir():
            return {
                "success": False,
                "error": "Path is not a directory",
                "path": str(target_dir)
            }

        # 查找文件
        if recursive:
            files = list(target_dir.rglob(pattern))
        else:
            files = list(target_dir.glob(pattern))

        # 过滤允许的文件类型
        filtered_files = [
            f for f in files
            if f.is_file() and (not f.suffix or f.suffix in self.allowed_extensions)
        ]

        # 获取文件信息
        file_infos = []
        for file_path in filtered_files:
            try:
                info = self._get_file_info(file_path)
                file_infos.append(info)
            except Exception as e:
                logger.warning(f"Failed to get info for {file_path}: {e}")

        return {
            "success": True,
            "directory": str(target_dir),
            "file_count": len(file_infos),
            "files": file_infos,
            "metadata": {
                "recursive": recursive,
                "pattern": pattern,
                "allowed_extensions": self.allowed_extensions
            }
        }

    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """获取文件信息"""
        stat = file_path.stat()

        return {
            "name": file_path.name,
            "path": str(file_path.relative_to(self.base_path)),
            "full_path": str(file_path),
            "size": stat.st_size,
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
            "extension": file_path.suffix,
            "parent": str(file_path.parent.relative_to(self.base_path))
        }
```

## 10.4 自定义评测环境教程

### 10.4.1 创建简单文本环境

```python
# src/environments/simple_text_environment.py
import random
from typing import Any, Dict, Optional
from .base_environment import BaseEnvironment

class SimpleTextEnvironment(BaseEnvironment):
    """简单文本环境"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # 环境配置
        self.max_steps = config.get("max_steps", 20)
        self.target_word = config.get("target_word", "secret")
        self.available_actions = config.get("available_actions", [
            "guess_letter", "guess_word", "hint", "quit"
        ])

        # 环境状态
        self.current_step = 0
        self.guessed_letters = set()
        self.guessed_words = []
        self.revealed_word = ["_" for _ in self.target_word]

    def reset(self, seed: Optional[int] = None) -> str:
        """
        重置环境

        Args:
            seed: 随机种子

        Returns:
            初始观察文本
        """
        if seed is not None:
            random.seed(seed)

        # 重置状态
        self.current_step = 0
        self.guessed_letters = set()
        self.guessed_words = []
        self.revealed_word = ["_" for _ in self.target_word]

        # 初始观察
        observation = self._get_observation()
        self.state = {
            "step": self.current_step,
            "guessed_letters": list(self.guessed_letters),
            "guessed_words": self.guessed_words,
            "revealed_word": self.revealed_word,
            "target_word": self.target_word
        }

        return observation

    def step(self, action: Dict[str, Any]) -> tuple:
        """
        执行动作

        Args:
            action: 动作字典

        Returns:
            (observation, reward, done, info) 元组
        """
        self.current_step += 1

        action_type = action.get("type", "unknown")
        success = False
        message = ""

        # 处理不同类型动作
        if action_type == "guess_letter":
            letter = action.get("letter", "").lower()
            success, message = self._process_letter_guess(letter)

        elif action_type == "guess_word":
            word = action.get("word", "").lower()
            success, message = self._process_word_guess(word)

        elif action_type == "hint":
            message = self._provide_hint()
            success = True

        elif action_type == "quit":
            message = "You quit the game."
            success = True

        else:
            message = f"Unknown action type: {action_type}"

        # 计算奖励
        reward = self._calculate_reward(success, action_type)

        # 检查是否完成
        done = self._is_done()

        # 更新状态
        self.state = {
            "step": self.current_step,
            "guessed_letters": list(self.guessed_letters),
            "guessed_words": self.guessed_words,
            "revealed_word": self.revealed_word,
            "target_word": self.target_word,
            "last_action": action,
            "last_success": success,
            "last_message": message
        }

        # 获取观察
        observation = self._get_observation()

        # 信息字典
        info = {
            "step": self.current_step,
            "success": success,
            "message": message,
            "guessed_letters": list(self.guessed_letters),
            "guessed_words": self.guessed_words,
            "revealed_word": "".join(self.revealed_word),
            "target_word": self.target_word,
            "max_steps": self.max_steps
        }

        return observation, reward, done, info

    def _process_letter_guess(self, letter: str) -> tuple:
        """处理字母猜测"""
        if len(letter) != 1 or not letter.isalpha():
            return False, "Please guess a single letter."

        if letter in self.guessed_letters:
            return False, f"You already guessed '{letter}'."

        self.guessed_letters.add(letter)

        # 检查字母是否在目标单词中
        if letter in self.target_word:
            # 更新显示单词
            for i, char in enumerate(self.target_word):
                if char == letter:
                    self.revealed_word[i] = letter

            revealed = "".join(self.revealed_word)
            return True, f"Good guess! The word is now: {revealed}"
        else:
            return False, f"Sorry, '{letter}' is not in the word."

    def _process_word_guess(self, word: str) -> tuple:
        """处理单词猜测"""
        self.guessed_words.append(word)

        if word == self.target_word:
            self.revealed_word = list(self.target_word)
            return True, f"Congratulations! You guessed the word: {self.target_word}"
        else:
            return False, f"Sorry, '{word}' is not the correct word."

    def _provide_hint(self) -> str:
        """提供提示"""
        # 随机选择未猜出的字母提供提示
        unrevealed_indices = [
            i for i, char in enumerate(self.revealed_word)
            if char == "_"
        ]

        if unrevealed_indices:
            hint_index = random.choice(unrevealed_indices)
            hint_letter = self.target_word[hint_index]

            # 更新显示单词
            self.revealed_word[hint_index] = hint_letter

            revealed = "".join(self.revealed_word)
            return f"Hint: letter '{hint_letter}' is in position {hint_index + 1}. Word: {revealed}"
        else:
            return "No more hints available."

    def _calculate_reward(self, success: bool, action_type: str) -> float:
        """计算奖励"""
        if action_type == "guess_word" and success:
            # 正确猜出完整单词
            return 10.0

        elif action_type == "guess_letter" and success:
            # 正确猜出字母
            correct_letters = sum(
                1 for char in self.target_word
                if char in self.guessed_letters
            )
            return correct_letters * 0.5

        elif action_type == "hint":
            # 使用提示
            return -0.5

        elif action_type == "quit":
            # 放弃游戏
            return -2.0

        else:
            # 错误猜测
            return -0.2

    def _is_done(self) -> bool:
        """检查是否完成"""
        # 达到最大步数
        if self.current_step >= self.max_steps:
            return True

        # 正确猜出单词
        if "".join(self.revealed_word) == self.target_word:
            return True

        # 猜过完整单词（无论对错）
        if self.guessed_words:
            return True

        return False

    def _get_observation(self) -> str:
        """获取观察文本"""
        revealed = "".join(self.revealed_word)

        observation_lines = [
            f"Step {self.current_step}/{self.max_steps}",
            f"Word: {revealed}",
            f"Guessed letters: {', '.join(sorted(self.guessed_letters))}",
            f"Guessed words: {', '.join(self.guessed_words)}",
            f"Available actions: {', '.join(self.available_actions)}",
            "",
            "What would you like to do?"
        ]

        return "\n".join(observation_lines)

    def render(self, mode: str = 'human') -> Optional[str]:
        """
        渲染环境

        Args:
            mode: 渲染模式 ('human', 'text')

        Returns:
            渲染结果
        """
        if mode == 'text':
            return self._get_observation()
        elif mode == 'human':
            # 在控制台显示
            print(self._get_observation())
            return None
        else:
            raise ValueError(f"Unsupported render mode: {mode}")
```

## 10.5 综合应用示例

### 10.5.1 完整的评测系统

#### 系统配置
```yaml
# config/full_evaluation_system.yaml
system:
  name: "comprehensive_agent_evaluation"
  version: "1.0.0"

environments:
  - name: "text_game"
    type: "simple_text_environment"
    config:
      target_word: "evaluation"
      max_steps: 15
      difficulty: "medium"

  - name: "calculator_test"
    type: "tool_environment"
    config:
      available_tools: ["calculator", "file_operations"]
      max_actions: 10

agents:
  - name: "llm_agent"
    type: "tool_based_agent"
    config:
      planning_model: "llm"
      execution_model: "llm"
      llm_config:
        model: "gpt-4"
        temperature: 0.2
        max_tokens: 1000
      tools:
        - "calculator"
        - "file_operations"

  - name: "rule_based_agent"
    type: "tool_based_agent"
    config:
      planning_model: "rule_based"
      execution_model: "rule_based"
      rules:
        - "if task involves calculation, use calculator"
        - "if task involves file operations, use file_operations"
      tools:
        - "calculator"
        - "file_operations"

tasks:
  - name: "word_game"
    environment: "text_game"
    description: "Guess the hidden word using letter guesses, word guesses, or hints."
    success_criteria:
      - "word guessed correctly"
      - "steps used <= 12"
    difficulty: "medium"

  - name: "math_and_file_task"
    environment: "calculator_test"
    description: "Calculate the square root of 256, then create a file with the result."
    success_criteria:
      - "calculation correct"
      - "file created successfully"
      - "file content matches result"
    difficulty: "easy"

evaluation:
  metrics:
    - name: "success_rate"
      weight: 0.4
      description: "Percentage of tasks successfully completed"

    - name: "efficiency_score"
      weight: 0.3
      description: "Average steps or actions per task"

    - name: "accuracy_score"
      weight: 0.2
      description: "Precision of answers or actions"

    - name: "safety_score"
      weight: 0.1
      description: "Absence of dangerous or inappropriate actions"

  execution:
    parallel_tasks: 4
    timeout_per_task: 300  # seconds
    max_retries: 2

  reporting:
    formats: ["html", "json", "csv"]
    output_dir: "./evaluation_results"
    include_details: true
```

#### 运行完整评测
```python
# run_full_evaluation.py
import yaml
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ComprehensiveEvaluationSystem:
    """综合评测系统"""

    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.results = []
        self.summary = {}

    async def evaluate_agent(self, agent_name: str, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """评估单个 Agent 在单个任务上的表现"""
        logger.info(f"Evaluating {agent_name} on task: {task_config['name']}")

        # 创建环境
        env_config = self.config["environments"][task_config["environment"]]
        environment = self._create_environment(env_config)

        # 创建 Agent
        agent_config = self.config["agents"][agent_name]
        agent = self._create_agent(agent_config)

        # 运行评测
        start_time = datetime.now()

        try:
            result = await self._run_single_evaluation(
                agent=agent,
                environment=environment,
                task_config=task_config
            )

            duration = (datetime.now() - start_time).total_seconds()

            return {
                "agent": agent_name,
                "task": task_config["name"],
                "success": result["success"],
                "score": result["score"],
                "duration": duration,
                "details": result["details"],
                "metadata": {
                    "evaluation_time": datetime.now().isoformat(),
                    "environment": task_config["environment"],
                    "difficulty": task_config.get("difficulty", "unknown")
                }
            }

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")

            return {
                "agent": agent_name,
                "task": task_config["name"],
                "success": False,
                "score": 0.0,
                "error": str(e),
                "duration": (datetime.now() - start_time).total_seconds(),
                "details": {"error": str(e)}
            }

    async def run_comprehensive_evaluation(self):
        """运行综合评测"""
        logger.info("Starting comprehensive evaluation")

        tasks = self.config["tasks"]
        agents = list(self.config["agents"].keys())

        # 创建所有评估任务
        evaluation_tasks = []
        for agent_name in agents:
            for task_config in tasks:
                evaluation_tasks.append(
                    self.evaluate_agent(agent_name, task_config)
                )

        # 并行运行评估
        results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        # 处理结果
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
            else:
                valid_results.append(result)

        self.results = valid_results

        # 生成总结
        self.summary = self._generate_summary()

        # 保存结果
        self._save_results()

        return self.summary

    def _generate_summary(self) -> Dict[str, Any]:
        """生成评测总结"""
        summary = {
            "overall": {
                "total_evaluations": len(self.results),
                "successful_evaluations": sum(1 for r in self.results if r["success"]),
                "average_score": sum(r["score"] for r in self.results) / len(self.results) if self.results else 0.0
            },
            "by_agent": {},
            "by_task": {},
            "timing": {
                "start_time": min(r["metadata"]["evaluation_time"] for r in self.results) if self.results else None,
                "end_time": max(r["metadata"]["evaluation_time"] for r in self.results) if self.results else None,
                "average_duration": sum(r["duration"] for r in self.results) / len(self.results) if self.results else 0.0
            }
        }

        # 按 Agent 汇总
        for agent_name in self.config["agents"].keys():
            agent_results = [r for r in self.results if r["agent"] == agent_name]
            if agent_results:
                summary["by_agent"][agent_name] = {
                    "task_count": len(agent_results),
                    "success_rate": sum(1 for r in agent_results if r["success"]) / len(agent_results),
                    "average_score": sum(r["score"] for r in agent_results) / len(agent_results),
                    "average_duration": sum(r["duration"] for r in agent_results) / len(agent_results)
                }

        # 按任务汇总
        for task_config in self.config["tasks"]:
            task_name = task_config["name"]
            task_results = [r for r in self.results if r["task"] == task_name]
            if task_results:
                summary["by_task"][task_name] = {
                    "agent_count": len(task_results),
                    "success_rate": sum(1 for r in task_results if r["success"]) / len(task_results),
                    "average_score": sum(r["score"] for r in task_results) / len(task_results),
                    "difficulty": task_config.get("difficulty", "unknown")
                }

        return summary

    def _save_results(self):
        """保存评测结果"""
        output_dir = self.config["evaluation"]["reporting"]["output_dir"]

        # 确保输出目录存在
        import os
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        detailed_path = os.path.join(output_dir, f"detailed_results_{timestamp}.json")
        with open(detailed_path, 'w') as f:
            json.dump({
                "config": self.config,
                "results": self.results
            }, f, indent=2)

        # 保存总结
        summary_path = os.path.join(output_dir, f"summary_{timestamp}.json")
        with open(summary_path, 'w') as f:
            json.dump(self.summary, f, indent=2)

        # 生成 HTML 报告
        html_path = os.path.join(output_dir, f"report_{timestamp}.html")
        self._generate_html_report(html_path)

        logger.info(f"Results saved to {output_dir}")

    def _generate_html_report(self, output_path: str):
        """生成 HTML 报告"""
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Agent Evaluation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .summary {{
            background-color: #e8f4fd;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
        }}
        .success {{
            color: green;
        }}
        .failure {{
            color: red;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Agent Evaluation Report</h1>
            <p>Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>System: {self.config['system']['name']} v{self.config['system']['version']}</p>
        </div>

        <div class="summary">
            <h2>Overall Summary</h2>
            <p>Total Evaluations: {self.summary['overall']['total_evaluations']}</p>
            <p>Successful Evaluations: {self.summary['overall']['successful_evaluations']}</p>
            <p>Average Score: {self.summary['overall']['average_score']:.2f}</p>
        </div>

        <div class="section">
            <h2>Performance by Agent</h2>
            <table>
                <tr>
                    <th>Agent</th>
                    <th>Tasks</th>
                    <th>Success Rate</th>
                    <th>Average Score</th>
                    <th>Average Duration</th>
                </tr>
        """

        for agent_name, stats in self.summary["by_agent"].items():
            html_content += f"""
                <tr>
                    <td>{agent_name}</td>
                    <td>{stats['task_count']}</td>
                    <td>{stats['success_rate']:.2%}</td>
                    <td>{stats['average_score']:.2f}</td>
                    <td>{stats['average_duration']:.2f}s</td>
                </tr>
            """

        html_content += """
            </table>
        </div>

        <div class="section">
            <h2>Performance by Task</h2>
            <table>
                <tr>
                    <th>Task</th>
                    <th>Agents</th>
                    <th>Success Rate</th>
                    <th>Average Score</th>
                    <th>Difficulty</th>
                </tr>
        """

        for task_name, stats in self.summary["by_task"].items():
            html_content += f"""
                <tr>
                    <td>{task_name}</td>
                    <td>{stats['agent_count']}</td>
                    <td>{stats['success_rate']:.2%}</td>
                    <td>{stats['average_score']:.2f}</td>
                    <td>{stats['difficulty']}</td>
                </tr>
            """

        html_content += """
            </table>
        </div>

        <div class="section">
            <h2>Detailed Results</h2>
            <p>For detailed results, please refer to the JSON output files.</p>
            <p>Total evaluations: {}</p>
        </div>
    </div>
</body>
</html>
        """.format(len(self.results))

        with open(output_path, 'w') as f:
            f.write(html_content)

async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 加载配置
    config_path = "config/full_evaluation_system.yaml"

    # 创建评测系统
    system = ComprehensiveEvaluationSystem(config_path)

    # 运行评测
    logger.info("Starting comprehensive evaluation...")
    summary = await system.run_comprehensive_evaluation()

    # 输出总结
    print("\n" + "="*60)
    print("COMPREHENSIVE EVALUATION SUMMARY")
    print("="*60)

    print(f"\nOverall:")
    print(f"  Total evaluations: {summary['overall']['total_evaluations']}")
    print(f"  Successful evaluations: {summary['overall']['successful_evaluations']}")
    print(f"  Average score: {summary['overall']['average_score']:.2f}")

    print(f"\nBy Agent:")
    for agent_name, stats in summary['by_agent'].items():
        print(f"  {agent_name}:")
        print(f"    Success rate: {stats['success_rate']:.2%}")
        print(f"    Average score: {stats['average_score']:.2f}")
        print(f"    Average duration: {stats['average_duration']:.2f}s")

    print(f"\nBy Task:")
    for task_name, stats in summary['by_task'].items():
        print(f"  {task_name}:")
        print(f"    Success rate: {stats['success_rate']:.2%}")
        print(f"    Average score: {stats['average_score']:.2f}")
        print(f"    Difficulty: {stats['difficulty']}")

    print("\n" + "="*60)
    print("Evaluation completed successfully!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
```

## 10.6 总结与进阶学习

### 10.6.1 学习成果检查

通过完成本章的教程和示例，你应该已经掌握了：

1. **基础环境搭建**：创建 AI Agent 评测的基本框架
2. **核心组件实现**：环境、Agent、评测运行器的开发
3. **工具集成**：为 Agent 添加和使用外部工具
4. **自定义环境**：构建特定场景的评测环境
5. **完整系统集成**：综合多个组件的完整评测系统

### 10.6.2 下一步学习建议

#### 深度技能提升
1. **高级 Agent 架构**：学习 ReAct、CoT 等高级模式
2. **分布式评测**：构建支持大规模并行评测的系统
3. **实时监控**：实现评测过程的实时跟踪和分析
4. **自动化优化**：开发自动调整评测参数的系统

#### 实践项目建议
1. **真实场景应用**：将评测系统应用到实际业务场景
2. **性能优化**：对评测系统进行性能和可扩展性优化
3. **社区贡献**：将改进贡献到开源项目
4. **研究创新**：基于实践经验提出新的评测方法

### 10.6.3 资源推荐

#### 开源项目
- **AgentBench**：全面的 Agent 评测基准
- **WebArena**：Web 交互 Agent 评测环境
- **τ-bench**：工具使用 Agent 评测基准

#### 学习资源
- **官方文档**：各开源项目的官方文档和教程
- **学术论文**：最新的评测方法研究论文
- **实践社区**：GitHub、Stack Overflow、相关论坛

#### 进阶工具
- **Docker & Kubernetes**：容器化和集群管理
- **Prometheus & Grafana**：监控和可视化
- **MLflow & Weights & Biases**：机器学习实验管理

### 10.6.4 最后建议

AI Agent 评测是一个实践性极强的领域，真正的掌握来自于：

1. **持续实践**：不断尝试和实现新的想法
2. **问题驱动**：从实际问题出发，寻找解决方案
3. **社区参与**：与他人交流、合作和分享
4. **迭代改进**：基于反馈和经验持续优化

记住，每一个复杂的系统都是从简单的组件开始的。从本章的基础示例出发，逐步构建和完善你自己的 AI Agent 评测系统。

**祝你在 AI Agent 评测的学习和实践中取得成功！**

---

**本章要点总结**：
- 提供了从环境搭建到完整系统实现的逐步教程
- 包含基础环境检查、项目结构创建、核心组件实现
- 实现了基于工具的 Agent 和自定义评测环境
- 展示了完整评测系统的配置和运行
- 提供了进阶学习建议和资源推荐
- 强调实践和持续改进的重要性
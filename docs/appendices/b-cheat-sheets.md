# 附录 B：速查表

## B.1 评测框架速查

### Anthropic 评测框架核心概念

| 概念 | 英文 | 定义 |
|------|------|------|
| 任务 | Task | 单个测试实例，包含输入和预期输出 |
| 试验 | Trial | Agent 对任务的单次尝试 |
| 评分器 | Grader | 评估 Agent 表现的系统 |
| 记录 | Transcript | 试验的完整交互记录 |
| 结果 | Outcome | 环境的最终状态 |

### 五步骤评测循环

```
1. 定义评测任务
2. 构建评测环境
3. 执行评测运行
4. 分析与评分
5. 迭代改进
```

### 评分器类型对比

| 类型 | 优势 | 局限 | 适用场景 |
|------|------|------|----------|
| 代码基础 | 快速、客观 | 脆弱性高 | 编程任务、数学计算 |
| 模型基础 | 灵活性强 | 非确定性 | 创意写作、对话质量 |
| 人工 | 质量最高 | 成本高 | 关键任务、研究验证 |

## B.2 评测基准对比速查

### 主要评测基准概览

| 基准名称 | 主要领域 | 任务数量 | 成功率（最佳模型） |
|------------|----------|----------|---------------------|
| SWE-bench | 软件工程 | 2,294 | 1.96% (Claude 2) |
| WebArena | 网页交互 | 812 | 14.41% (GPT-4) |
| τ-bench | 工具使用 | ~1,500 | 35-45% (航空) |
| AgentBench | 多领域 | 综合基准 | - |

### 基准选择决策树

```
开始
  │
  ├─ 评估软件工程能力？
  │    ├─ 是 → SWE-bench
  │    └─ 否 → 继续
  │
  ├─ 评估网页交互能力？
  │    ├─ 是 → WebArena
  │    └─ 否 → 继续
  │
  ├─ 评估工具使用和对话管理？
  │    ├─ 是 → τ-bench
  │    └─ 否 → 继续
  │
  └─ 需要多领域综合评估？
       └─ 是 → AgentBench
```

## B.3 代码片段速查

### 基础评测模板

```python
# 1. 创建基础环境
class BaseEnvironment:
    def __init__(self, config):
        self.config = config
        self.state = None

    def reset(self, seed=None):
        """重置环境"""
        pass

    def step(self, action):
        """执行动作"""
        pass

# 2. 创建基础 Agent
class BaseAgent:
    def __init__(self, config):
        self.config = config
        self.memory = []

    def act(self, observation):
        """选择动作"""
        pass

# 3. 运行评测
def run_evaluation(agent, environment, task):
    """运行单任务评测"""
    observation = environment.reset()
    done = False

    while not done:
        action = agent.act(observation)
        observation, reward, done, info = environment.step(action)

    return {
        "task": task,
        "final_observation": observation,
        "final_reward": reward
    }
```

### Docker 环境配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  evaluation:
    build: .
    volumes:
      - ./data:/app/data
      - ./results:/app/results
    environment:
      - MODEL=gpt-4
      - MAX_STEPS=100
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

## B.4 常用命令速查

### SWE-bench

```bash
# 安装
pip install -e .

# 下载数据集
python scripts/download_dataset.py --dataset_name swe-bench-lite

# 运行评估
python -m swebench.harness.run_evaluation \
    --dataset_name swe-bench-lite \
    --model gpt-4 \
    --output_dir results/
```

### WebArena

```bash
# 安装
pip install -r requirements.txt
playwright install chromium

# 启动环境
docker-compose up -d

# 运行评估
python run.py --prompt_file data/example.json
```

### τ-bench

```bash
# 安装
pip install -r requirements.txt

# 运行评估
python run.py \
    --domain airline \
    --agent_strategy react \
    --num_tasks 20
```

## B.5 指标计算速查

### 成功率指标

```python
# 基础成功率
success_rate = successful_tasks / total_tasks

# pass@k（在k次尝试中至少成功一次）
import math
def pass_at_k(n, c, k):
    """计算 pass@k"""
    if n - c < k:
        return 1.0
    return 1.0 - math.prod(1.0 - k / (n - i) for i in range(c))
```

### 效率指标

```python
# 平均执行时间
avg_time = sum(durations) / len(durations)

# 平均步数
avg_steps = sum(steps) / len(steps)

# 资源利用效率
efficiency = success_rate / (avg_time * avg_steps)
```

## B.6 常见错误速查

### 环境问题

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| 环境不一致 | 依赖版本不同 | 使用容器化，锁定依赖版本 |
| 端口冲突 | 多个服务使用同一端口 | 修改端口映射 |
| 超时 | 任务执行时间过长 | 增加超时时间或优化任务 |

### Agent 问题

| 错误 | 原因 | 解决方法 |
|------|------|----------|
| API 调用失败 | API key 无效或超限 | 检查 API key，管理调用频率 |
| 工具调用错误 | 工具未正确注册 | 验证工具配置 |
| 内存溢出 | 状态记忆过大 | 实现记忆压缩机制 |

## B.7 性能优化速查

### 评测效率优化

```python
# 1. 并行执行
from concurrent.futures import ThreadPoolExecutor

def parallel_evaluation(agent, tasks, workers=4):
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(
            lambda task: evaluate_task(agent, task),
            tasks
        ))
    return results

# 2. 结果缓存
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_evaluation(task_hash):
    return evaluate_task(task_hash)
```

### 资源优化

```yaml
# Docker 资源限制
services:
  evaluation:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## B.8 最佳实践速查

### 任务设计

- ✓ 使用真实用户场景
- ✓ 明确定义成功标准
- ✓ 平衡任务难度
- ✓ 提供参考解决方案

### 评估实施

- ✓ 从小规模开始（20-50任务）
- ✓ 确保环境可重复性
- ✓ 使用多种评分器
- ✓ 记录详细日志

### 结果分析

- ✓ 多维度分析
- ✓ 识别失败模式
- ✓ 生成可视化报告
- ✓ 提供可操作建议

---

**速查表使用指南**：
- 打印本附录作为参考
- 根据任务类型选择合适的基准
- 遇到问题时查阅错误速查部分
- 使用代码片段快速搭建评测环境

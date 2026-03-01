# 附录 A：安装指南

本文档与《Demystifying evals for AI agents》解读报告一致，面向 AI Agent 评测实践。首先说明**本项目 AgentEval** 的安装与验证，再提供可选的外部评测框架参考。

## A.0 本项目 AgentEval 安装与验证

### A.0.1 安装

```bash
# 克隆本仓库
git clone https://github.com/your-org/AgentEval.git
cd AgentEval

# 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows

# 可编辑模式安装
pip install -e .

# 开发与测试依赖（可选）
pip install -e ".[dev]"
```

### A.0.2 验证安装

```bash
# 运行对话评测单元测试
python3 -m pytest tests/ -v
```

### A.0.3 快速运行：对话 Agent 评测

与《Demystifying evals for AI agents》中**对话 Agent 评估策略**一致（Task / Trial / Transcript / Grader / Harness、pass@k、pass^k）。

**CLI：**

```bash
agent-eval --config examples/conversation_eval/config.json \
  --tasks examples/conversation_eval/tasks.json \
  --output results.json
```

**或使用示例脚本：**

```bash
python3 examples/conversation_eval/run_conversation_eval.py \
  --tasks examples/conversation_eval/tasks.json \
  --config examples/conversation_eval/config.json \
  --output results.json
```

详细说明见 [附录 B：对话 Agent 评测说明](b-conversation-agent-eval.md)。

---

## A.1 基础环境安装

### A.1.1 系统要求检查

#### 硬件要求
```bash
# 检查系统硬件配置
# Linux/Mac
lscpu  # 查看 CPU 信息
free -h  # 查看内存使用情况
df -h  # 查看磁盘空间

# Windows (通过 PowerShell)
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores
Get-CimInstance Win32_ComputerSystem | Select-Object TotalPhysicalMemory
Get-PSDrive C | Select-Object Used, Free
```

#### 软件要求
```bash
# 检查 Python 版本（本项目要求 3.9+，与 pyproject.toml 一致）
python3 --version  # 需要 3.9 或更高版本

# 检查 Git 安装
git --version

# 检查包管理器
pip --version  # 或 pip3 --version
```

> Docker 为可选，仅在使用外部评测框架（如 SWE-bench、WebArena）或容器化部署时需要。

### A.1.2 Python 环境配置

#### 创建虚拟环境
```bash
# 方法 1: 使用 venv (Python 自带)
python3 -m venv agent-eval-env

# 激活虚拟环境
# Linux/Mac
source agent-eval-env/bin/activate

# Windows
agent-eval-env\Scripts\activate

# 方法 2: 使用 conda (如果已安装)
conda create -n agent-eval-env python=3.10
conda activate agent-eval-env
```

#### 安装基础依赖

本项目 **AgentEval** 核心无额外运行时依赖（`pyproject.toml` 中 `dependencies = []`）。若仅运行单轮评测与对话评测示例，无需安装下列库。

以下为**可选**依赖，适用于扩展开发或与外部基准对接：

```bash
# 升级 pip
pip install --upgrade pip

# 可选：科学计算与数据分析
pip install numpy pandas

# 可选：对接外部基准或自建 LLM Judge 时
# pip install torch transformers  # 按需
# pip install openai anthropic   # 若使用 API 型 judge_fn
```

## A.2 外部评测框架安装（参考）

以下为《Demystifying evals for AI agents》报告中提到的**外部**评测基准/框架，非本项目运行所必需。需要复现报告中的基准实验时可参考安装。

### A.2.1 AgentBench 安装

#### 标准安装
```bash
# 克隆仓库
git clone https://github.com/THUDM/AgentBench.git
cd AgentBench

# 安装依赖
pip install -r requirements.txt

# 安装特定组件
pip install -e .  # 可编辑模式安装

# 设置环境变量
export AGENTBENCH_HOME=$(pwd)
export PYTHONPATH=$AGENTBENCH_HOME:$PYTHONPATH
```

#### Docker 部署
```bash
# 使用 Docker Compose
docker-compose -f extra/docker-compose.yml up -d

# 检查服务状态
docker-compose -f extra/docker-compose.yml ps

# 查看日志
docker-compose -f extra/docker-compose.yml logs -f
```

### A.2.2 SWE-bench 安装

#### 环境设置
```bash
# 克隆仓库
git clone https://github.com/princeton-nlp/SWE-bench.git
cd SWE-bench

# 安装依赖
pip install -e .

# 安装 Docker（如果尚未安装）
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# Mac
brew install docker docker-compose

# 验证 Docker 安装
docker run hello-world
```

#### 数据集下载
```bash
# 下载完整数据集（约 50GB）
python scripts/download_dataset.py --dataset_name swe-bench

# 下载 Lite 版本（约 5GB）
python scripts/download_dataset.py --dataset_name swe-bench-lite

# 下载 Verified 版本（约 10GB）
python scripts/download_dataset.py --dataset_name swe-bench-verified
```

### A.2.3 WebArena 安装

#### 本地安装
```bash
# 克隆仓库
git clone https://github.com/web-arena-x/webarena.git
cd webarena

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright
playwright install chromium

# 设置环境变量
export SHOPPING_ADMIN="http://localhost:3000"
export SHOPPING="http://localhost:3000"
export REDDIT="http://localhost:3001"
export GITLAB="http://localhost:3002"
export MAP="http://localhost:3003"
export WIKIPEDIA="http://localhost:3004"
```

#### Docker 快速启动
```bash
# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps

# 初始化数据库
docker-compose exec web python manage.py migrate

# 创建超级用户（可选）
docker-compose exec web python manage.py createsuperuser
```

### A.2.4 τ-bench 安装

```bash
# 克隆仓库
git clone https://github.com/sierra-research/tau-bench.git
cd tau-bench

# 安装依赖
pip install -r requirements.txt

# 安装额外的语言模型库
pip install openai anthropic

# 下载数据集
python scripts/download_data.py --dataset airline
python scripts/download_data.py --dataset retail

# 设置 API 密钥
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

## A.3 开发环境配置

### A.3.1 IDE 配置

#### VS Code 配置
```json
// .vscode/settings.json（本项目包名为 agent_eval，无 src 目录时可去掉 extraPaths）
{
    "python.defaultInterpreterPath": "./.venv/bin/python",
    "python.analysis.extraPaths": ["."],
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "python.testing.pytestArgs": ["tests", "-v"],
    "editor.formatOnSave": true
}
```

#### PyCharm 配置
1. 打开项目，选择 "Open"
2. 配置 Python 解释器：File → Settings → Project → Python Interpreter，选择 `.venv` 或 `agent-eval-env`
3. 配置运行配置：Run → Edit Configurations，添加 pytest，工作目录为项目根目录

### A.3.2 开发工具安装

#### 代码质量工具
```bash
# 代码格式化
pip install black isort

# 代码检查
pip install pylint flake8 mypy

# 类型检查
pip install mypy

# 安全扫描
pip install bandit safety

# 配置 pre-commit hooks
pip install pre-commit
pre-commit install
```

#### 测试工具
```bash
# 测试框架
pip install pytest pytest-cov pytest-xdist pytest-asyncio

# 测试数据生成
pip install faker hypothesis

# 性能测试
pip install locust py-spy
```

#### 文档工具
```bash
# 文档生成
pip install sphinx sphinx-rtd-theme

# API 文档
pip install pydoc-markdown mkdocs

# 代码文档
pip install docstring-parser
```

## A.4 故障排除指南

### A.4.1 常见安装问题

#### Python 包安装失败
```bash
# 问题：依赖冲突
# 解决方案：使用虚拟环境或 conda

# 问题：网络超时
# 解决方案：使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple package-name

# 问题：缺少系统库
# 解决方案：安装系统依赖
# Ubuntu/Debian
sudo apt-get install build-essential python3-dev
# Mac
brew install pkg-config
```

#### Docker 相关问题
```bash
# 问题：权限拒绝
# 解决方案：将用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker

# 问题：端口冲突
# 解决方案：修改端口映射
docker run -p 3001:3000 image-name

# 问题：磁盘空间不足
# 解决方案：清理 Docker 资源
docker system prune -a
```

### A.4.2 环境配置问题

#### 环境变量设置
```bash
# 检查环境变量
echo $PYTHONPATH
echo $AGENTBENCH_HOME

# 永久设置环境变量
# Linux/Mac: 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export PYTHONPATH="/path/to/project:$PYTHONPATH"' >> ~/.bashrc
source ~/.bashrc

# Windows: 系统属性 → 环境变量
```

#### 路径问题
```bash
# 检查 Python 路径
which python3
python3 -c "import sys; print(sys.path)"

# 添加项目路径
export PYTHONPATH="/path/to/your/project:$PYTHONPATH"

# 在代码中添加路径
import sys
sys.path.insert(0, '/path/to/your/project')
```

### A.4.3 性能优化建议

#### 资源配置优化
```yaml
# docker-compose.yml 中的资源限制
services:
  agent-eval:
    image: agent-eval:latest
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '2.0'
          memory: 4G
```

#### 缓存配置
```bash
# 使用 Docker 构建缓存
docker build --cache-from your-image:latest -t your-image:new .

# 使用 pip 缓存
pip install --cache-dir /path/to/cache package-name

# 使用数据缓存
import joblib
from functools import lru_cache
```

## A.5 验证安装

### A.5.1 基本功能验证

#### Python 环境验证
```python
# test_environment.py
import sys
import torch
import transformers

print(f"Python version: {sys.version}")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"Transformers version: {transformers.__version__}")

# 测试基本功能
import numpy as np
import pandas as pd

print("NumPy test:", np.array([1, 2, 3]).sum())
print("Pandas test:", pd.DataFrame({'a': [1, 2, 3]}).shape)

print("All tests passed!")
```

#### Docker 环境验证
```bash
# 测试 Docker 安装
docker run --rm hello-world

# 测试 Docker Compose
docker-compose --version

# 测试容器网络
docker run --rm alpine ping -c 3 google.com
```

### A.5.2 本项目功能验证

#### 对话 Agent 评测验证
```bash
# 方式一：CLI
agent-eval --config examples/conversation_eval/config.json \
  --tasks examples/conversation_eval/tasks.json
# 预期：overall_pass_rate 等汇总输出

# 方式二：示例脚本
python3 examples/conversation_eval/run_conversation_eval.py \
  --tasks examples/conversation_eval/tasks.json \
  --config examples/conversation_eval/config.json
```

#### 外部框架验证（可选）
```bash
# 运行测试套件
cd AgentBench
pytest tests/ -v
```

#### SWE-bench 验证
```bash
# 验证数据集
python -c "from swebench import get_dataset; print(get_dataset('swe-bench-lite'))"

# 运行简单测试
python scripts/run_simple_test.py
```

### A.5.3 性能基准测试（可选）

以下为可选性能测试，非本项目默认验证内容。

#### 系统性能测试
```bash
# CPU 性能测试
python -c "import numpy as np; a = np.random.rand(1000, 1000); b = np.random.rand(1000, 1000); %timeit np.dot(a, b)"

# GPU 性能测试（如果有）
python -c "import torch; device = 'cuda' if torch.cuda.is_available() else 'cpu'; x = torch.randn(1000, 1000, device=device); y = torch.randn(1000, 1000, device=device); %timeit torch.matmul(x, y)"
```

#### 内存使用测试
```python
# memory_test.py
import psutil
import os

process = psutil.Process(os.getpid())
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# 测试大内存操作
import numpy as np
large_array = np.random.rand(10000, 10000)
print(f"Array size: {large_array.nbytes / 1024 / 1024:.2f} MB")

process = psutil.Process(os.getpid())
print(f"Memory after allocation: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

## A.6 后续步骤

### A.6.1 学习资源

#### 本仓库文档
- **完整报告**：`docs/AI_Evaluation_Complete_Report.md`（含《Demystifying evals for AI agents》解读）
- **对话 Agent 评测**：`docs/appendices/b-conversation-agent-eval.md`、`examples/conversation_eval/README.md`

#### 外部基准与框架
- **AgentBench**: https://agentbench.readthedocs.io/
- **SWE-bench**: https://swebench.github.io/
- **WebArena**: https://webarena.dev/
- **τ-bench**: https://github.com/sierra-research/tau-bench

#### 教程和示例
- **快速开始指南**: 各项目的 `examples/` 目录
- **Jupyter notebooks**: 交互式学习示例
- **视频教程**: YouTube 上的相关频道

### A.6.2 社区支持

#### 讨论渠道
- **GitHub Issues**: 报告问题和功能请求
- **Discord/Slack**: 实时交流和讨论
- **Stack Overflow**: 技术问题解答
- **邮件列表**: 订阅更新和公告

#### 贡献指南
1. 阅读 `CONTRIBUTING.md` 文件
2. 了解代码风格和测试要求
3. 从简单的 bug 修复开始
4. 参与讨论和代码审查

### A.6.3 扩展学习

#### 进阶主题
1. **自定义评测环境开发**
2. **分布式评测系统设计**
3. **评测结果分析和可视化**
4. **生产环境部署和监控**

#### 相关技术
1. **容器化技术**：Docker, Kubernetes
2. **机器学习平台**：MLflow, Kubeflow
3. **监控系统**：Prometheus, Grafana
4. **CI/CD 管道**：GitHub Actions, GitLab CI

---

**安装指南要点总结**：
- **A.0** 说明本项目 AgentEval 的安装、验证及**对话 Agent 评测**的快速运行（CLI 与示例脚本）。
- 技术要求与 `pyproject.toml` 一致：Python 3.9+，无强制外部依赖。
- A.2 为外部评测框架参考，非本项目运行所必需。
- 本仓库仅支持对话类 Agent 评测，详见附录 B。
- 本评测当前仅面向本地/内网环境，不涉及云环境部署。
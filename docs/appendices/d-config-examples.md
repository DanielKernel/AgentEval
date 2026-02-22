# 附录 D：示例配置文件

## D.1 评测配置示例

### 基础评测配置

```yaml
# evaluation_config.yaml
version: "1.0"

# 评测基本信息
evaluation:
  name: "agent_performance_evaluation"
  description: "AI Agent 性能综合评估"
  date: "2024-02-22"

# 环境配置
environment:
  type: "docker"
  image: "agent-eval:latest"
  resources:
    cpu: 4
    memory: "8G"
    gpu: 1
  timeout: 300  # 秒

# Agent 配置
agent:
  type: "llm_agent"
  model: "gpt-4"
  temperature: 0.2
  max_tokens: 2000
  api_key: "${OPENAI_API_KEY}"

# 任务配置
tasks:
  source: "file"
  file: "data/tasks.jsonl"
  count: 100
  shuffle: true
  seed: 42

# 评估指标
metrics:
  - name: "success_rate"
    weight: 0.4
  - name: "efficiency"
    weight: 0.3
  - name: "accuracy"
    weight: 0.2
  - name: "safety"
    weight: 0.1

# 输出配置
output:
  directory: "./results"
  format: "json"
  include_details: true
  generate_report: true
```

### SWE-bench 配置

```yaml
# swebench_config.yaml
dataset:
  name: "swe-bench-lite"
  version: "1.0"

environment:
  type: "docker"
  base_image: "python:3.10-slim"
  timeout: 1800  # 30分钟

agent:
  name: "claude_agent"
  model: "claude-3-opus"
  max_retries: 3
  tools:
    - file_operations
    - git_operations
    - test_execution

evaluation:
  max_steps: 100
  skip_existing: false
  parallel: 4

scoring:
  test_suite: "pytest"
  timeout: 60
  coverage_threshold: 0.8
```

### WebArena 配置

```yaml
# webarena_config.yaml
websites:
  shopping:
    url: "http://localhost:3000"
    cookies: "data/shopping_cookies.json"
  reddit:
    url: "http://localhost:3001"
    cookies: "data/reddit_cookies.json"
  gitlab:
    url: "http://localhost:3002"
    cookies: "data/gitlab_cookies.json"
  wikipedia:
    url: "http://localhost:3003"
    cookies: "data/wikipedia_cookies.json"

agent:
  type: "browser_agent"
  headless: true
  screenshot: true
  max_actions: 50

tasks:
  categories:
    - "information_retrieval"
    - "website_navigation"
    - "content_interaction"
  difficulty:
    - "easy"
    - "medium"
    - "hard"

browser:
  type: "playwright"
  engine: "chromium"
  viewport:
    width: 1280
    height: 720
  timeout: 30000
```

### τ-bench 配置

```yaml
# tau_bench_config.yaml
domains:
  airline:
    tasks: 50
    user_strategy: "llm"
    agent_strategy: "react"
  retail:
    tasks: 50
    user_strategy: "verify"
    agent_strategy: "tool-calling"

agent:
  model: "gpt-4"
  temperature: 0.1
  max_turns: 20
  tools:
    - flight_search
    - booking_system
    - order_management
    - customer_support

user_simulator:
  model: "gpt-4"
  realism: "high"
  behavior_patterns:
    - "normal_interaction"
    - "challenging_questions"
    - "error_recovery"

evaluation:
  num_trials: 3
  pass_at_k: 5
  detailed_logging: true
```

## D.2 Docker 配置示例

### Dockerfile 示例

```dockerfile
# Dockerfile for Agent Evaluation
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV EVAL_HOME=/app

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "run_evaluation.py"]
```

### Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 评测主服务
  eval-service:
    build: .
    container_name: agent-eval
    volumes:
      - ./data:/app/data
      - ./results:/app/results
      - ./config:/app/config
    environment:
      - MODEL=gpt-4
      - MAX_WORKERS=4
      - LOG_LEVEL=INFO
    ports:
      - "8000:8000"
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    restart: unless-stopped

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: eval-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # PostgreSQL 数据库
  postgres:
    image: postgres:15-alpine
    container_name: eval-postgres
    environment:
      POSTGRES_PASSWORD: evalpass
      POSTGRES_DB: evaldb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  # 监控服务
  prometheus:
    image: prom/prometheus:latest
    container_name: eval-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  # 可视化
  grafana:
    image: grafana/grafana:latest
    container_name: eval-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

volumes:
  redis_data:
  postgres_data:
  grafana_data:
```

## D.3 工具配置示例

### OpenAI API 配置

```json
{
  "openai_config": {
    "api_key": "sk-proj-...",
    "model": "gpt-4",
    "temperature": 0.2,
    "max_tokens": 2000,
    "top_p": 0.9,
    "frequency_penalty": 0,
    "presence_penalty": 0,
    "timeout": 60,
    "retry": {
      "max_attempts": 3,
      "backoff_factor": 2
    }
  }
}
```

### Anthropic API 配置

```json
{
  "anthropic_config": {
    "api_key": "sk-ant-...",
    "model": "claude-3-opus",
    "temperature": 0.1,
    "max_tokens": 4096,
    "top_p": 0.9,
    "timeout": 120,
    "stream": false,
    "tools": {
      "enabled": true,
      "tool_choice": "auto"
    }
  }
}
```

### 数据库配置

```yaml
# database_config.yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  name: "evaldb"
  user: "eval_user"
  password: "eval_password"
  pool:
    min_size: 5
    max_size: 20
    timeout: 30
  tables:
    evaluations:
      columns:
        - id: UUID
        - timestamp: TIMESTAMP
        - agent_type: VARCHAR
        - task_id: VARCHAR
        - success: BOOLEAN
        - score: FLOAT
        - duration: FLOAT
      indexes:
        - "idx_timestamp": ["timestamp"]
        - "idx_agent": ["agent_type"]
    results:
      columns:
        - id: UUID
        - evaluation_id: UUID
        - task_id: VARCHAR
        - step_number: INTEGER
        - action: JSONB
        - observation: JSONB
        - reward: FLOAT
      indexes:
        - "idx_evaluation": ["evaluation_id"]
        - "idx_task": ["task_id"]
```

## D.4 监控配置示例

### Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'agent_eval'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'redis'
    static_configs:
      - targets: ['localhost:9121']
```

### 日志配置

```yaml
# logging_config.yaml
version: 1
formatters:
  standard:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/evaluation.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  '':
    level: INFO
    handlers: [console, file]
    propagate: false

  evaluation:
    level: DEBUG
    handlers: [file]
    propagate: false

  agent:
    level: INFO
    handlers: [console]
    propagate: false
```

## D.5 CI/CD 配置示例

### GitHub Actions 配置

```yaml
# .github/workflows/evaluation.yml
name: Agent Evaluation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # 每周日运行

jobs:
  evaluate:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        model: [gpt-4, claude-3-opus]
        dataset: [swe-bench-lite, webarena-sample]

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run evaluation
      env:
        MODEL: ${{ matrix.model }}
        DATASET: ${{ matrix.dataset }}
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        python run_evaluation.py \
          --model $MODEL \
          --dataset $DATASET \
          --output results/

    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: evaluation-results
        path: results/

    - name: Generate report
      run: |
        python generate_report.py --input results/ --output report.html

    - name: Upload report
      uses: actions/upload-artifact@v3
      with:
        name: evaluation-report
        path: report.html
```

## D.6 安全配置示例

### API 密钥管理

```bash
# .env.example
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
HUGGINGFACE_API_KEY=hf_...
DATABASE_URL=postgresql://user:pass@localhost:5432/db
LOG_LEVEL=INFO
```

### 权限配置

```yaml
# rbac_config.yaml
roles:
  admin:
    permissions:
      - "read:all"
      - "write:all"
      - "delete:all"
      - "manage:users"
  evaluator:
    permissions:
      - "read:all"
      - "write:evaluations"
      - "read:results"
  viewer:
    permissions:
      - "read:results"
      - "read:reports"

users:
  admin_user:
    role: admin
    permissions:
      - "manage:api_keys"
  evaluator_user:
    role: evaluator
    datasets:
      - "swe-bench"
      - "webarena"
  viewer_user:
    role: viewer
    datasets:
      - "all"
```

---

**配置文件使用建议**：
- 将敏感信息存储在环境变量或密钥管理系统中
- 根据实际需求调整资源限制和超时设置
- 定期审查和更新配置文件
- 使用版本控制管理配置变更
- 在不同环境（开发、测试、生产）中使用不同配置

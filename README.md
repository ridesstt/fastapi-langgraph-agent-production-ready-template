FastAPI LangGraph 代理模板

一个生产就绪的FastAPI模板，用于构建集成LangGraph的AI代理应用。该模板为构建可扩展、安全且可维护的AI代理服务提供了坚实基础。

🌟 功能特性

• 生产就绪架构

  • 采用FastAPI实现高性能异步API端点

  • LangGraph集成支持AI代理工作流

  • Langfuse提供LLM可观测性与监控

  • 结构化日志支持环境特定格式化

  • 可配置规则的速率限制

  • PostgreSQL数据持久化

  • Docker与Docker Compose支持

  • Prometheus指标与Grafana监控看板


• 安全防护

  • 基于JWT的身份验证

  • 会话管理

  • 输入净化

  • CORS配置

  • 速率限制保护


• 开发者体验

  • 环境特定配置

  • 完备的日志系统

  • 清晰的项目结构

  • 全面类型提示

  • 简易的本地开发设置


• 模型评估框架

  • 基于指标的自动化模型输出评估

  • 集成Langfuse进行追踪分析

  • 包含成功/失败指标的详细JSON报告

  • 交互式命令行界面

  • 可定制评估指标


🚀 快速开始

先决条件

• Python 3.13+

• PostgreSQL ([见数据库设置](#数据库设置))

• Docker与Docker Compose (可选)


环境配置

1. 克隆仓库：

```bash
git clone <仓库地址>
cd <项目目录>
```

2. 创建并激活虚拟环境：

```bash
uv sync
```

3. 复制示例环境文件：

```bash
cp .env.example .env.[development|staging|production] # 例如 .env.development
```

4. 更新`.env`文件中的配置（参考`.env.example`）

数据库设置

1. 创建PostgreSQL数据库（如Supabase或本地PostgreSQL）
2. 在`.env`文件中更新数据库连接字符串：

```bash
POSTGRES_URL="postgresql://:你的数据库密码@POSTGRES_HOST:POSTGRES_PORT/POSTGRES_DB"
```

• 无需手动创建表，ORM会自动处理。如遇问题可手动运行`schemas.sql`文件建表。


运行应用

本地开发

1. 安装依赖：

```bash
uv sync
```

2. 运行应用：

```bash
make [dev|staging|production] # 例如 make dev
```

3. 访问Swagger UI：

```bash
http://localhost:8000/docs
```

使用Docker

1. 通过Docker Compose构建运行：

```bash
make docker-build-env ENV=[development|staging|production] # 例如 make docker-build-env ENV=development
make docker-run-env ENV=[development|staging|production] # 例如 make docker-run-env ENV=development
```

2. 访问监控组件：

```bash
# Prometheus指标
http://localhost:9090

# Grafana看板
http://localhost:3000
默认凭证：
- 用户名：admin
- 密码：admin
```

Docker套件包含：

• FastAPI应用

• PostgreSQL数据库

• Prometheus指标收集

• Grafana指标可视化

• 预配置看板：

  • API性能指标

  • 速率限制统计

  • 数据库性能

  • 系统资源使用


📊 模型评估

项目内置强大的评估框架，用于持续追踪模型性能。评估器自动从Langfuse获取追踪记录，应用评估指标并生成详细报告。

执行评估

通过Makefile命令运行评估：

```bash
# 交互模式（逐步提示）
make eval [ENV=development|staging|production]

# 快速模式（使用默认设置）
make eval-quick [ENV=development|staging|production]

# 无报告生成模式
make eval-no-report [ENV=development|staging|production]
```

评估特性

• 交互式CLI：彩色输出与进度条的用户友好界面

• 灵活配置：支持预设默认值或运行时自定义

• 详细报告：包含以下内容的JSON报告：

  • 整体成功率

  • 各指标表现

  • 耗时信息

  • 追踪级成功/失败详情


定制指标

评估指标定义在`evals/metrics/prompts/`目录的markdown文件中：

1. 在prompts目录创建新markdown文件（如`my_metric.md`）
2. 定义评估标准与评分逻辑
3. 评估器将自动发现并应用新指标

查看报告

报告自动生成于`evals/reports/`目录，文件名含时间戳：

```
evals/reports/evaluation_report_YYYYMMDD_HHMMSS.json
```

每份报告包含：

• 汇总统计（总追踪数、成功率等）

• 各指标表现

• 用于调试的追踪级详细信息


🔧 配置说明

应用采用灵活的环境特定配置系统：

• `.env.development`


=============================================================================================================================

1. **项目架构**：
   - 这是一个生产级别的 FastAPI 应用，集成了 LangGraph 用于构建 AI Agent
   - 使用 Docker 进行容器化部署
   - 包含完整的监控系统（Prometheus）

2. **主要目录结构**：
   - `app/`: 主应用目录
     - `api/`: API 路由和端点定义
     - `core/`: 核心配置和设置
     - `models/`: 数据模型定义
     - `schemas/`: Pydantic 模型和验证
     - `services/`: 业务逻辑服务
     - `utils/`: 工具函数
     - `main.py`: 应用入口文件

3. **配置文件**：
   - `pyproject.toml`: Python 项目配置和依赖管理
   - `docker-compose.yml`: Docker 服务编排配置
   - `.env.example`: 环境变量示例文件
   - `Dockerfile`: Docker 镜像构建文件
   - `Makefile`: 项目构建和部署命令

4. **数据库**：
   - `schema.sql`: 数据库表结构定义

5. **监控和评估**：
   - `prometheus/`: Prometheus 监控配置
   - `evals/`: 评估相关文件

6. **开发工具**：
   - `.vscode/`: VS Code 编辑器配置
   - `.github/`: GitHub 相关配置（可能包含 CI/CD）
   - `scripts/`: 实用脚本

7. **其他重要文件**：
   - `README.md`: 项目文档
   - `.gitignore`: Git 忽略文件配置
   - `.dockerignore`: Docker 构建忽略文件

这个项目采用了现代化的 Python 项目结构，使用了 FastAPI 作为 Web 框架，并集成了 LangGraph 来构建 AI Agent。项目包含了完整的开发、测试、部署和监控工具链，适合用于生产环境。项目使用 Docker 进行容器化，便于部署和扩展，同时集成了 Prometheus 进行监控，确保系统的可靠性和可观测性。

如果你想了解某个具体部分的更多细节，我可以为你深入查看相关文件的内容。

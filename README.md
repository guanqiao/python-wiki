# Python Wiki

AI 驱动的 Wiki 文档生成器 - 对标 Qoder Wiki 的 Python 实现

## 功能特性

### 核心功能
- 自动文档生成 - 基于代码自动生成结构化 Markdown 文档
- 多语言解析 - 支持 Python、TypeScript、Java 代码解析
- 增量更新 - 智能检测代码变更，仅更新受影响部分
- Git 集成 - 支持 Git 目录双向同步和 Wiki 共享

### Mermaid 图表生成
- 架构图 (Architecture Diagram)
- 流程图 (Flowchart)
- 序列图 (Sequence Diagram)
- 类图 (Class Diagram)
- 状态转移图 (State Diagram)
- ER 图 (Entity Relationship)
- 组件图 (Component Diagram)
- 数据库 Schema 表

### LLM 配置
支持可配置的 LLM 对接：
- Endpoint URL
- API Key
- Model
- CA 证书
- Timeout / Max Retries

### GUI 界面
- PyQt6 桌面应用
- 项目管理面板
- LLM 配置界面
- 实时进度监控
- Markdown 预览（支持 Mermaid 渲染）

### 隐式知识提取
- 设计决策分析 - 识别代码中的设计决策及其理由
- 设计动机提取 - 理解代码设计背后的动机
- 技术债务检测 - 发现代码异味和潜在问题
- 架构决策记录 - 自动提取和记录架构决策
- 深度依赖分析 - 分析模块间耦合关系

### 多层记忆系统
- 全局记忆 - 用户级别的偏好和知识
- 项目记忆 - 项目特定的上下文信息
- 编码风格学习 - 自动学习项目编码规范
- 记忆优先级管理 - 智能管理记忆重要性

### 架构洞察
- 设计模式检测 - 自动识别常用设计模式
- 技术栈分析 - 分析项目使用的技术栈
- 业务逻辑分析 - 提取核心业务逻辑
- 架构演进追踪 - 记录架构变化历史

### 高性能搜索引擎
- 分层索引 - 多级索引结构优化检索效率
- 混合搜索 - 结合关键词和语义搜索
- 搜索缓存 - 智能缓存提升响应速度
- Whoosh 全文索引 - 高效文本检索
- 代码搜索引擎 - 快速代码检索
- 语义索引 - 基于向量相似度的语义搜索
- 跨模块搜索 - 支持跨文件/模块搜索

### Agent 系统
#### 基础 Agent 集成
- Search Memory 工具 - 为 AI Agent 提供知识检索能力
- 上下文增强器 - 智能补充相关上下文
- Wiki-Agent 桥接 - 与外部 Agent 系统集成

#### LangGraph Agent 系统
- 图构建器 - 构建复杂 Agent 工作流图
- 状态管理 - 管理 Agent 执行状态
- 检查点机制 - 支持执行状态持久化
- 节点执行器 - 执行各类 Agent 节点

#### Agent 工作流
- 任务编排 - 编排复杂任务流程
- 任务图 - 管理任务依赖关系
- 并行执行 - 支持任务并行处理

#### Agent 学习系统
- 反馈收集 - 收集用户反馈优化系统
- 自动优化 - 基于使用模式自动优化

### Wiki 质量管理
- 质量评分器 - 自动评估文档质量
- 改进建议器 - 智能生成改进建议

### LLM 模型管理
- 模型路由器 - 智能选择最适合的模型
- 模型能力分析 - 分析不同模型的能力特性

### 同步与变更检测
- 文档滞后检测 - 检测文档与代码的同步状态
- Git 变更检测 - 精确追踪代码变更
- 自动同步服务 - 自动保持文档同步

## 安装指南

### 环境要求

- Python >= 3.10
- Git

### 1. 克隆仓库

```bash
git clone https://github.com/guanqiao/python-wiki.git
cd python-wiki
```

### 2. 创建虚拟环境（推荐）

```bash
# 使用 venv
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

#### 方式一：使用 pip（推荐）

```bash
# 安装 poetry-core（构建依赖）
pip install poetry-core

# 安装项目（可编辑模式）
pip install -e . --no-build-isolation
```

#### 方式二：使用 Poetry

```bash
# 安装 Poetry
pip install poetry

# 安装项目依赖
poetry install
```

### 4. 验证安装

```bash
# 检查 CLI 是否可用
pywiki --help

# 或检查 GUI
pywiki-gui
```

### 常见问题

#### 1. Windows 上 PyQt6 安装问题

Windows 用户如果遇到 PyQt6 安装问题，确保系统已安装最新版本的 pip：

```bash
pip install --upgrade pip
```

#### 2. tree-sitter 版本兼容性

项目依赖 tree-sitter ^0.21.0，确保与 Python 3.10+ 兼容。如有版本冲突，请升级：

```bash
pip install tree-sitter>=0.21.0
```

## 使用方法

### GUI 模式

Python Wiki 提供了直观的图形界面，支持一键生成所有类型的文档。

#### 启动方式

**方式一：使用命令行入口**
```bash
pywiki-gui
```

**方式二：使用 Python 模块**
```bash
# Windows (使用 py launcher)
py -m pywiki.main

# Linux/Mac
python -m pywiki.main
```

**方式三：直接运行**
```bash
# 进入项目目录
cd python-wiki

# 运行 GUI
py src/pywiki/main.py
```

#### GUI 功能说明

- **项目管理**：创建、切换、删除项目
- **文档类型选择**：支持选择要生成的文档类型
- **一键生成**：一键生成所有选中的文档类型
- **进度监控**：实时显示文档生成进度
- **文档预览**：支持 Markdown 和 Mermaid 图表渲染
- **智能问答**：基于项目知识库的 AI 问答

#### 支持的文档类型

| 文档类型 | 说明 |
|---------|------|
| 概述 (overview) | 项目概述文档，包含项目介绍、功能特性等 |
| 技术栈 (tech-stack) | 项目使用的技术栈分析 |
| API 文档 (api) | API 接口文档 |
| 架构文档 (architecture) | 系统架构设计文档 |
| 模块文档 (module) | 各模块详细文档 |
| 数据库文档 (database) | 数据库 Schema 文档 |
| 配置文档 (configuration) | 配置项说明文档 |
| 开发文档 (development) | 开发指南文档 |
| 依赖文档 (dependencies) | 依赖关系文档 |
| 技术设计决策 (tsd) | 技术设计决策记录 |

### CLI 模式

```bash
# 初始化项目
pywiki init /path/to/project --name my-project

# 配置 LLM
pywiki config-llm --provider openai --api-key sk-xxx --model gpt-4

# 生成 Wiki
pywiki generate my-project

# 列出项目
pywiki list-projects

# 增量更新
pywiki update my-project
```

## 项目结构

```
python-wiki/
├── src/pywiki/
│   ├── agent/                # Agent 深度集成
│   │   ├── context_enricher.py      # 上下文增强器
│   │   ├── knowledge_query.py       # 知识查询
│   │   ├── search_memory.py         # 搜索记忆
│   │   ├── search_memory_tool.py    # 搜索记忆工具
│   │   └── wiki_agent_bridge.py     # Wiki-Agent 桥接
│   ├── agents/               # 智能代理系统
│   │   ├── langgraph/              # LangGraph Agent
│   │   │   ├── checkpointer.py     # 检查点机制
│   │   │   ├── graph_builder.py    # 图构建器
│   │   │   ├── nodes.py            # 节点定义
│   │   │   └── state.py            # 状态管理
│   │   ├── learning/               # 学习系统
│   │   │   ├── feedback.py         # 反馈收集
│   │   │   └── optimizer.py        # 自动优化
│   │   ├── workflow/               # 工作流系统
│   │   │   ├── executor.py         # 执行器
│   │   │   ├── orchestrator.py     # 编排器
│   │   │   └── task_graph.py       # 任务图
│   │   ├── architecture_agent.py   # 架构分析 Agent
│   │   ├── implicit_knowledge_agent.py  # 隐式知识 Agent
│   │   ├── memory_agent.py         # 记忆 Agent
│   │   ├── multilang_agent.py      # 多语言 Agent
│   │   └── orchestrator.py         # Agent 编排器
│   ├── cli/                  # CLI 命令
│   ├── config/               # 配置管理
│   ├── generators/           # 文档生成器
│   │   └── diagrams/         # Mermaid 图表
│   ├── gui/                  # GUI 界面
│   │   ├── dialogs/          # 对话框
│   │   └── panels/           # 面板组件
│   ├── insights/             # 架构洞察
│   ├── knowledge/            # 知识库 + 向量存储
│   │   ├── architecture_decision.py  # 架构决策
│   │   ├── dependency_analyzer.py    # 依赖分析
│   │   ├── design_decision.py        # 设计决策
│   │   ├── design_motivation.py      # 设计动机
│   │   ├── implicit_extractor.py     # 隐式知识提取器
│   │   ├── implicit_knowledge.py     # 隐式知识
│   │   ├── tech_debt_detector.py     # 技术债务检测
│   │   └── vector_store.py           # 向量存储
│   ├── llm/                  # LLM 服务层
│   │   ├── model_capability.py       # 模型能力分析
│   │   └── model_router.py           # 模型路由器
│   ├── memory/               # 多层记忆系统
│   │   ├── global_memory.py          # 全局记忆
│   │   ├── memory_entry.py           # 记忆条目
│   │   ├── memory_manager.py         # 记忆管理器
│   │   ├── memory_prioritizer.py     # 记忆优先级
│   │   ├── project_memory.py         # 项目记忆
│   │   └── style_learner.py          # 风格学习
│   ├── monitor/              # 监控系统
│   ├── parsers/              # 多语言解析器
│   ├── search/               # 高性能搜索引擎
│   │   ├── cache.py                  # 搜索缓存
│   │   ├── code_search_engine.py     # 代码搜索引擎
│   │   ├── cross_module_search.py    # 跨模块搜索
│   │   ├── engine.py                 # 搜索引擎核心
│   │   ├── hybrid_search.py          # 混合搜索
│   │   ├── semantic_indexer.py       # 语义索引
│   │   ├── tiered_index.py           # 分层索引
│   │   └── whoosh_index.py           # Whoosh 索引
│   ├── sync/                 # Git 同步
│   │   ├── auto_sync_service.py      # 自动同步服务
│   │   ├── change_detector.py        # 变更检测
│   │   ├── doc_lag_detector.py       # 文档滞后检测
│   │   ├── git_change_detector.py    # Git 变更检测
│   │   └── incremental_updater.py    # 增量更新
│   ├── utils/                # 工具函数
│   └── wiki/                 # Wiki 管理
│       ├── improvement_suggester.py  # 改进建议器
│       └── quality_scorer.py         # 质量评分器
├── tests/                    # 测试文件
│   ├── knowledge/            # 知识模块测试
│   └── parsers/              # 解析器测试
└── pyproject.toml            # 项目配置
```

## LLM 配置示例

```yaml
llm:
  provider: openai
  endpoint: https://api.openai.com/v1
  api_key: sk-xxx
  model: gpt-4
  ca_cert: /path/to/ca.pem  # 可选
  timeout: 60
  max_retries: 3
```

## 技术栈

- **GUI**: PyQt6 + PyQt6-WebEngine
- **代码解析**: tree-sitter (Python/TypeScript/Java)
- **向量存储**: FAISS
- **全文搜索**: Whoosh
- **LLM 框架**: LangChain
- **Agent 框架**: LangGraph
- **CLI**: Typer + Rich

## 开发

```bash
# 安装开发依赖
poetry install --with dev

# 运行测试
poetry run pytest

# 代码格式化
poetry run black src/

# 类型检查
poetry run mypy src/
```

## 对标 Qoder Wiki 功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 自动文档生成 | 完成 | 支持 Python/TypeScript/Java |
| Mermaid 图表 | 完成 | 8 种图表类型 |
| 增量更新 | 完成 | 智能变更检测 |
| Git 同步 | 完成 | 双向同步 |
| 隐式知识提取 | 完成 | 设计决策、技术债务、设计动机 |
| 多层记忆系统 | 完成 | 全局 + 项目级 + 优先级管理 |
| 架构洞察 | 完成 | 设计模式、技术栈、架构演进 |
| 高性能搜索 | 完成 | 分层索引、混合搜索、语义索引 |
| Agent 集成 | 完成 | LangGraph、工作流、学习系统 |
| Wiki 质量管理 | 完成 | 质量评分、改进建议 |
| LLM 模型管理 | 完成 | 模型路由、能力分析 |
| 同步检测 | 完成 | 文档滞后检测、Git 变更检测 |

## License

MIT

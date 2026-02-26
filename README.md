# Python Wiki

AI 驱动的 Wiki 文档生成器 - 对标 Qoder Wiki 的 Python 实现

## 功能特性

### 核心功能
- ✅ **自动文档生成** - 基于代码自动生成结构化 Markdown 文档
- ✅ **多语言解析** - 支持 Python、TypeScript、Java 代码解析
- ✅ **增量更新** - 智能检测代码变更，仅更新受影响部分
- ✅ **Git 集成** - 支持 Git 目录双向同步和 Wiki 共享

### Mermaid 图表生成
- ✅ 架构图 (Architecture Diagram)
- ✅ 流程图 (Flowchart)
- ✅ 序列图 (Sequence Diagram)
- ✅ 类图 (Class Diagram)
- ✅ 状态转移图 (State Diagram)
- ✅ ER 图 (Entity Relationship)
- ✅ 组件图 (Component Diagram)
- ✅ 数据库 Schema 表

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
- 技术债务检测 - 发现代码异味和潜在问题
- 深度依赖分析 - 分析模块间耦合关系

### 双层记忆系统
- 全局记忆 - 用户级别的偏好和知识
- 项目记忆 - 项目特定的上下文信息
- 编码风格学习 - 自动学习项目编码规范

### 架构洞察
- 设计模式检测 - 自动识别常用设计模式
- 技术栈分析 - 分析项目使用的技术栈
- 业务逻辑分析 - 提取核心业务逻辑
- 架构演进追踪 - 记录架构变化历史

### 高性能搜索
- 代码搜索引擎 - 快速代码检索
- 语义索引 - 基于向量相似度的语义搜索
- 跨模块搜索 - 支持跨文件/模块搜索

### Agent 集成
- Search Memory 工具 - 为 AI Agent 提供知识检索能力
- 上下文增强器 - 智能补充相关上下文
- Wiki-Agent 桥接 - 与外部 Agent 系统集成

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

```bash
pywiki-gui
```

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
│   ├── agent/            # Agent 深度集成
│   ├── agents/           # 智能代理
│   ├── cli/              # CLI 命令
│   ├── config/           # 配置管理
│   ├── generators/       # 文档生成器
│   │   └── diagrams/     # Mermaid 图表
│   ├── gui/              # GUI 界面
│   │   ├── dialogs/      # 对话框
│   │   └── panels/       # 面板组件
│   ├── insights/         # 架构洞察
│   ├── knowledge/        # 知识库 + 向量存储
│   ├── llm/              # LLM 服务层
│   ├── memory/           # 双层记忆系统
│   ├── monitor/          # 监控系统
│   ├── parsers/          # 多语言解析器
│   ├── search/           # 高性能搜索引擎
│   ├── sync/             # Git 同步
│   ├── utils/            # 工具函数
│   └── wiki/             # Wiki 管理
├── tests/                # 测试文件
└── pyproject.toml        # 项目配置
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
- **LLM 框架**: LangChain
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
| 自动文档生成 | ✅ | 支持 Python/TypeScript/Java |
| Mermaid 图表 | ✅ | 8 种图表类型 |
| 增量更新 | ✅ | 智能变更检测 |
| Git 同步 | ✅ | 双向同步 |
| 隐式知识提取 | ✅ | 设计决策、技术债务 |
| 双层记忆系统 | ✅ | 全局 + 项目级 |
| 架构洞察 | ✅ | 设计模式、技术栈 |
| 高性能搜索 | ✅ | 语义索引 |
| Agent 集成 | ✅ | Search Memory 工具 |

## License

MIT

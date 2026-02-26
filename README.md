# Python Wiki

AI 驱动的 Wiki 文档生成器 - 对标 Qoder Wiki 的 Python 实现

## 功能特性

### 核心功能
- ✅ **自动文档生成** - 基于代码自动生成结构化文档
- ✅ **多语言支持** - 支持中文/英文文档生成
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

### 知识库
- 向量存储 (ChromaDB)
- 语义搜索
- Agent 集成

## 安装

```bash
# 使用 Poetry 安装
poetry install

# 或使用 pip
pip install -e .
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
│   ├── cli/              # CLI 命令
│   ├── config/           # 配置管理
│   ├── llm/              # LLM 服务层
│   ├── parsers/          # 代码解析器
│   ├── generators/       # 文档生成器
│   │   └── diagrams/     # Mermaid 图表
│   ├── wiki/             # Wiki 管理
│   ├── sync/             # Git 同步
│   ├── knowledge/        # 知识库
│   ├── gui/              # GUI 界面
│   ├── monitor/          # 监控系统
│   └── utils/            # 工具函数
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

## License

MIT

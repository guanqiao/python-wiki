# Python Wiki 开发计划 - 完整对标 Qoder Wiki

## 项目概述
使用 Python 技术栈实现 Qoder Wiki 的全部功能，包含 GUI 界面、可配置 LLM、实时监控、Mermaid 图表生成、知识图谱、Agent 集成。

---

## 一、Qoder Wiki 功能对标分析

| 功能模块 | Qoder 功能 | Python Wiki 实现 |
|---------|-----------|-----------------|
| **文档生成** | 工程架构、模块关系、API手册、依赖关系、技术文档 | ✅ 支持 |
| **图表生成** | 架构图、组件图、时序图、类图、流程图、ER图 | ✅ Mermaid 格式 |
| **知识管理** | 隐性知识显性化、设计决策、深层依赖 | ✅ 支持 |
| **增量更新** | 持续跟踪代码变更、自动检测文档滞后 | ✅ 支持 |
| **Wiki 共享** | 推送到代码仓库、团队协作共建 | ✅ 支持 |
| **编辑与导出** | 手工修改、导出功能 | ✅ 支持 |
| **Agent 集成** | Search Memory 工具、深层次代码库感知 | ✅ 支持 |
| **多语言** | 中文/英文 | ✅ 支持 |
| **记忆系统** | 个人习惯、项目上下文、解决方案记忆 | ✅ 支持 |
| **问答能力** | 自然语言查询、快速定位 | ✅ 支持 |
| **GUI 界面** | IDE 集成 | ✅ PyQt6 |
| **LLM 配置** | 内置 | ✅ 可配置 endpoint/api_key/model/ca |
| **进度监控** | 内置 | ✅ 实时监控 |

---

## 二、核心功能模块详解

### 1. 代码解析器 (Parser)
- Python AST 解析（主目标）
- 多语言扩展支持（TypeScript/Java/Go）
- 提取类、函数、模块、依赖关系
- 数据库模型提取（ORM 分析）

### 2. Wiki 文档生成
- AI 驱动的智能文档生成
- 多语言支持（中文/英文）
- **Markdown 格式输出**
- 文档类型：
  - 工程架构文档
  - 模块关系文档
  - API 手册
  - 依赖关系文档
  - 技术文档

### 3. Mermaid 图表生成
| 图表类型 | 说明 |
|---------|------|
| **架构图** | 系统分层架构、组件关系图 |
| **组件图** | 模块组件关系 |
| **流程图** | 业务流程、代码执行流程 |
| **序列图** | API 调用、模块交互序列 |
| **类图** | 类结构、继承关系 |
| **状态转移图** | 状态机、生命周期状态 |
| **DB Schema Table** | 数据库表结构展示 |
| **ER 图** | 实体关系图、表关联关系 |

### 4. 知识管理
- **隐性知识显性化**：从代码中提取设计决策、架构考量
- **设计决策记录 (ADR)**：记录架构决策及其背景
- **深层依赖关系**：分析模块间的隐式依赖

### 5. 增量更新系统
- 文件变更检测（哈希缓存）
- 影响分析
- 仅更新变更部分
- **文档滞后检测与提醒**

### 6. Git 集成
- Git 目录双向同步
- 自动监控代码变更
- Wiki 共享（`.python-wiki/repowiki`）
- 团队协作共建

### 7. LLM 服务层（可配置）
```yaml
llm:
  provider: openai  # openai, azure, anthropic, custom
  endpoint: https://api.openai.com/v1
  api_key: sk-xxx
  model: gpt-4
  ca_cert: /path/to/ca.pem  # 可选
  timeout: 60
  max_retries: 3
```

### 8. 知识库与搜索
- 向量存储（ChromaDB）
- 语义搜索
- 混合搜索
- **Search Memory 工具**（Agent 集成）

### 9. 记忆系统
- **个人偏好记忆**：代码风格、命名规范
- **项目上下文记忆**：架构设计、业务逻辑
- **问题解决方案库**：历史问题与解决方法

### 10. GUI 界面
- 项目管理面板
- LLM 配置界面
- Wiki 生成进度实时监控
- 文档预览与编辑（支持 Mermaid 渲染）
- 设置面板
- **问答面板**（自然语言查询）

### 11. 实时监控
- Wiki 生成进度条
- 阶段状态显示
- 错误日志实时展示
- 性能指标统计
- 文件处理统计

### 12. 导出功能
- Markdown 导出
- HTML 导出
- PDF 导出

---

## 三、技术栈

| 组件 | 技术选型 |
|------|----------|
| 语言 | Python 3.10+ |
| GUI | PyQt6 / PySide6 |
| CLI | Click / Typer |
| 代码解析 | AST, tree-sitter |
| LLM | LangChain / LiteLLM |
| 向量存储 | ChromaDB |
| 配置 | Pydantic Settings |
| 测试 | pytest |
| 包管理 | Poetry |
| Mermaid 渲染 | QWebEngineView |
| PDF 导出 | WeasyPrint |

---

## 四、开发阶段

### Phase 1: 项目基础（Day 1-2）
- 项目初始化（pyproject.toml）
- 配置管理系统
- LLM 服务抽象层（支持自定义 endpoint/api_key/model/ca）

### Phase 2: GUI 框架（Day 3-4）
- PyQt6 主窗口框架
- 项目管理界面
- LLM 配置界面
- 设置面板

### Phase 3: 代码解析（Day 5-7）
- Python AST 解析器
- 代码结构提取
- 依赖关系分析
- 数据库模型提取（ORM 分析）

### Phase 4: Mermaid 图表生成（Day 8-12）
- 架构图生成器
- 组件图生成器
- 流程图生成器
- 序列图生成器
- 类图生成器
- 状态转移图生成器
- DB Schema Table 生成器
- ER 图生成器

### Phase 5: Wiki 文档生成（Day 13-16）
- 文档模板系统
- AI 文档生成
- 多语言支持
- Markdown 输出
- 图表嵌入
- **隐性知识提取**

### Phase 6: 知识库与记忆系统（Day 17-19）
- 向量存储
- 语义搜索
- 记忆系统
- **Search Memory 工具**

### Phase 7: 增量更新（Day 20-21）
- 变更检测
- 影响分析
- 增量生成
- **文档滞后检测与提醒**

### Phase 8: Git 集成（Day 22-23）
- Git 监控
- 双向同步
- Wiki 共享
- 团队协作

### Phase 9: 导出功能（Day 24）
- Markdown 导出
- HTML 导出
- PDF 导出

### Phase 10: 监控完善（Day 25-26）
- 实时进度显示
- 日志系统
- Mermaid 预览渲染
- 性能统计

### Phase 11: CLI 工具（Day 27）
- 命令行接口
- 进度显示

### Phase 12: 测试与文档（Day 28-30）
- 单元测试
- 集成测试
- 使用文档

---

## 五、目录结构

```
python-wiki/
├── src/
│   └── pywiki/
│       ├── __init__.py
│       ├── main.py              # GUI 入口
│       ├── cli/                 # CLI 命令
│       ├── config/              # 配置管理
│       ├── llm/                 # LLM 服务层
│       ├── parsers/             # 代码解析器
│       │   ├── python.py        # Python 解析
│       │   ├── typescript.py    # TS 解析
│       │   └── orm.py           # ORM 模型提取
│       ├── generators/          # 文档生成器
│       │   ├── markdown.py      # Markdown 生成
│       │   ├── knowledge.py     # 知识提取
│       │   └── diagrams/        # Mermaid 图表
│       │       ├── architecture.py
│       │       ├── component.py
│       │       ├── flowchart.py
│       │       ├── sequence.py
│       │       ├── class_diagram.py
│       │       ├── state.py
│       │       ├── db_schema.py
│       │       └── er_diagram.py
│       ├── wiki/                # Wiki 管理
│       │   ├── manager.py       # Wiki 管理器
│       │   ├── storage.py       # 存储服务
│       │   ├── history.py       # 版本历史
│       │   └── export.py        # 导出功能
│       ├── sync/                # Git 同步
│       ├── knowledge/           # 知识库
│       │   ├── vector_store.py  # 向量存储
│       │   ├── search.py        # 搜索服务
│       │   └── memory.py        # 记忆系统
│       ├── memory/              # 记忆系统
│       │   ├── personal.py      # 个人偏好
│       │   ├── project.py       # 项目上下文
│       │   └── solutions.py     # 解决方案库
│       ├── agent/               # Agent 集成
│       │   └── search_memory.py # Search Memory 工具
│       ├── gui/                 # GUI 界面
│       │   ├── main_window.py
│       │   ├── panels/
│       │   │   ├── project.py
│       │   │   ├── config.py
│       │   │   ├── preview.py
│       │   │   ├── qa.py        # 问答面板
│       │   │   └── settings.py
│       │   ├── widgets/
│       │   └── preview/         # Mermaid 预览
│       ├── monitor/             # 监控系统
│       │   ├── progress.py
│       │   ├── logger.py
│       │   └── metrics.py
│       └── utils/
├── tests/
├── pyproject.toml
└── README.md
```

---

## 六、GUI 界面设计

### 主窗口布局
```
┌─────────────────────────────────────────────────────────────┐
│  File  Edit  View  Tools  Help                      [_][□][X]│
├─────────────────────────────────────────────────────────────┤
│ ┌───────────┬───────────────────────────────────────────────┤
│ │           │ ┌─────────────────────────────────────────────┤
│ │ 项目列表   │ │ [文档预览] [问答] [设置]                    │
│ │           │ ├─────────────────────────────────────────────┤
│ │ □ proj1   │ │ ## 系统架构                                  │
│ │ □ proj2   │ │ ```mermaid                                  │
│ │           │ │ graph TB                                    │
│ │           │ │   A[前端] --> B[API网关]                    │
│ │           │ │   B --> C[业务服务]                         │
│ │           │ │ ```                                         │
│ │           │ │ [Mermaid 图表实时渲染]                       │
│ │           │ │                                             │
│ │ [新建项目] │ │ [生成Wiki] [更新] [同步Git] [导出▼]        │
│ ├───────────┴───────────────────────────────────────────────┤
│ │ 进度监控                                                   │
│ │ ████████████████░░░░░░░░ 65%                              │
│ │ 阶段: 生成ER图 | 文件: 130/200 | 耗时: 5m32s              │
│ │ [实时日志 ▼]                                               │
│ └───────────────────────────────────────────────────────────┤
│ 状态: 运行中 | LLM: GPT-4 | 上次更新: 2026-02-26 10:30      │
└─────────────────────────────────────────────────────────────┘
```

### 问答面板
```
┌─────────────────────────────────────────┐
│ 💬 问答                                  │
├─────────────────────────────────────────┤
│ 输入问题查询项目知识库...                │
│ ┌─────────────────────────────────────┐ │
│ │ 用户认证是如何实现的？               │ │
│ └─────────────────────────────────────┘ │
│ [发送]                                   │
├─────────────────────────────────────────┤
│ 🤖 回答:                                 │
│ 用户认证采用 JWT 方式实现：              │
│ 1. 用户登录时生成 access_token          │
│ 2. token 有效期 2 小时                   │
│ 3. 支持 refresh_token 刷新机制          │
│                                         │
│ 相关代码:                                │
│ - src/auth/jwt_handler.py              │
│ - src/middleware/auth_middleware.py    │
└─────────────────────────────────────────┘
```

---

## 七、验收标准
- ✅ GUI 界面完整可用
- ✅ LLM 配置支持 endpoint/api_key/model/ca
- ✅ Wiki 生成过程实时监控
- ✅ 支持 8 种 Mermaid 图表生成
- ✅ Markdown 文档输出
- ✅ 隐性知识显性化
- ✅ 记忆系统
- ✅ Search Memory 工具（Agent 集成）
- ✅ 文档滞后检测与提醒
- ✅ 导出功能（MD/HTML/PDF）
- ✅ 问答功能
- ✅ 测试覆盖率 ≥ 80%
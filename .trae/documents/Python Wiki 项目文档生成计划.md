## 对标 Qoder Wiki 文档生成能力 - 实现计划

### Qoder Wiki 文档类型分析

根据调研，Qoder Wiki 自动生成以下文档类型：

| 文档类型 | 内容描述 |
|---------|---------|
| **项目概述 (Overview)** | 功能说明、技术栈、架构图 |
| **模块说明 (Modules)** | 各包职责、核心类说明 |
| **API 文档** | 控制器接口、请求参数、响应格式 |
| **配置说明 (Configuration)** | 配置文件含义、环境变量 |
| **开发指南 (Development Guide)** | 环境搭建、构建命令、部署流程 |
| **数据库设计 (Database)** | E-R 图、表结构、字段说明 |
| **架构文档 (Architecture)** | 系统架构、组件图、依赖关系 |
| **外部依赖 (Dependencies)** | 第三方库、版本要求、用途说明 |
| **UML 图表** | 组件图、时序图、类图、流程图 |

---

### 实现方案

#### 1. 文档目录结构设计

```
.python-wiki/repowiki/
├── index.md                    # Wiki 首页/索引
├── overview.md                 # 项目概述
├── tech-stack.md              # 技术栈分析
├── architecture/               # 架构文档
│   ├── system-architecture.md  # 系统架构
│   ├── module-structure.md     # 模块结构
│   └── dependency-graph.md     # 依赖关系图
├── api/                        # API 文档
│   ├── index.md               # API 索引
│   └── modules/               # 各模块 API
├── modules/                    # 模块文档
│   └── {module-name}/         # 按模块组织
├── database/                   # 数据库文档
│   ├── er-diagram.md          # E-R 图
│   └── schema.md              # 表结构
├── configuration/              # 配置文档
│   ├── environment.md         # 环境配置
│   └── config-reference.md    # 配置参考
├── development/                # 开发指南
│   ├── getting-started.md     # 快速开始
│   ├── build.md               # 构建指南
│   └── deployment.md          # 部署指南
├── dependencies/               # 依赖文档
│   ├── external.md            # 外部依赖
│   └── internal.md            # 内部依赖
├── diagrams/                   # Mermaid 图表
│   ├── architecture.mmd       # 架构图
│   ├── flowchart.mmd          # 流程图
│   ├── sequence.mmd           # 时序图
│   ├── class.mmd              # 类图
│   └── component.mmd          # 组件图
└── tsd/                        # 技术设计文档
    ├── design-decisions.md    # 设计决策
    └── tech-debt.md           # 技术债务
```

#### 2. 新增文件清单

**文档生成器模块** (`src/pywiki/generators/docs/`)
```
generators/docs/
├── __init__.py
├── base.py                    # 文档生成器基类
├── overview_generator.py      # 项目概述生成器
├── techstack_generator.py     # 技术栈文档生成器
├── api_generator.py           # API 文档生成器
├── architecture_generator.py  # 架构文档生成器
├── module_generator.py        # 模块文档生成器
├── database_generator.py      # 数据库文档生成器
├── config_generator.py        # 配置文档生成器
├── development_generator.py   # 开发指南生成器
├── dependencies_generator.py  # 依赖文档生成器
├── tsd_generator.py           # TSD 技术设计文档生成器
└── templates/                 # Jinja2 模板
    ├── overview.md.j2
    ├── tech-stack.md.j2
    ├── api.md.j2
    ├── architecture.md.j2
    ├── module.md.j2
    ├── database.md.j2
    ├── config.md.j2
    ├── development.md.j2
    ├── dependencies.md.j2
    └── tsd.md.j2
```

**文档生成 Agent** (`src/pywiki/agents/documentation_agent.py`)
- 继承 `BaseAgent`
- 协调各文档生成器
- 集成 LLM 进行智能内容生成

#### 3. 修改文件

| 文件 | 修改内容 |
|------|---------|
| `src/pywiki/wiki/manager.py` | 添加 `generate_docs()` 方法 |
| `src/pywiki/cli/main.py` | 添加 `generate-docs` CLI 命令 |
| `src/pywiki/__init__.py` | 导出新类 |
| `src/pywiki/generators/__init__.py` | 导出文档生成器 |

#### 4. 测试文件

```
tests/
├── generators/
│   └── docs/
│       ├── __init__.py
│       ├── test_overview_generator.py
│       ├── test_techstack_generator.py
│       ├── test_api_generator.py
│       └── test_architecture_generator.py
└── agents/
    └── test_documentation_agent.py
```

---

### 执行步骤

1. **创建文档生成器基类和模板**
2. **实现各类文档生成器**（按优先级）
   - Overview Generator（高）
   - TechStack Generator（高）
   - API Generator（高）
   - Architecture Generator（高）
   - Module Generator（高）
   - Dependencies Generator（中）
   - Config Generator（中）
   - Development Generator（中）
   - Database Generator（中）
   - TSD Generator（中）
3. **创建 DocumentationAgent**
4. **扩展 WikiManager**
5. **扩展 CLI 命令**
6. **编写测试用例**
7. **运行测试验证**
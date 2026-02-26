# Python Wiki 对标 Qoder Wiki 差距分析

## 一、功能对比矩阵

| 功能模块 | Qoder Wiki | Python Wiki 现状 | 状态 |
|---------|-----------|-----------------|------|
| **自动文档生成** | 架构图谱、模块关系、API手册、依赖关系 | ✅ 已实现 | 完成 |
| **Mermaid 图表** | 架构图、流程图、序列图、类图等 | ✅ 8种图表已实现 | 完成 |
| **增量更新** | Git HEAD变更检测、智能合并 | ✅ 已实现 | 完成 |
| **Wiki 共享** | 推送到Git仓库、团队协作 | ✅ 已实现 | 完成 |
| **多语言支持** | 中文/英文 | ✅ 已实现 | 完成 |
| **文档导出** | Markdown/HTML/PDF | ✅ 已实现 | 完成 |
| **GUI 界面** | IDE集成 | ✅ PyQt6 已实现 | 完成 |
| **LLM 配置** | 内置 | ✅ 可配置 endpoint/api_key/model/ca | 完成 |
| **进度监控** | 实时进度、日志 | ✅ 已实现 | 完成 |
| **隐性知识显性化** | 设计决策、架构考量、技术债务 | ⚠️ 部分实现 | **需增强** |
| **记忆系统** | 双层记忆（全局+项目）、编码风格记忆 | ⚠️ 基础实现 | **需增强** |
| **架构洞察** | 设计模式识别、技术栈分析 | ⚠️ 需增强 | **需增强** |
| **高性能检索** | 10万文件级检索、跨模块语义理解 | ⚠️ 需增强 | **需增强** |
| **Search Memory** | Agent深度集成、知识库查询 | ⚠️ 基础实现 | **需增强** |

---

## 二、需要增强的功能

### 1. 隐性知识显性化（高优先级）
**Qoder 功能：**
- 设计决策提取：从代码中推断"为什么这样设计"
- 架构考量分析：识别架构模式及其原因
- 技术债务识别：发现潜在问题和改进空间
- 深层依赖关系：分析模块间的隐式依赖

**需要新增：**
```
src/pywiki/knowledge/
├── implicit_knowledge.py    # 隐性知识提取器
├── design_decision.py       # 设计决策分析
├── tech_debt_detector.py    # 技术债务检测
└── dependency_analyzer.py   # 深层依赖分析
```

### 2. 双层记忆系统（高优先级）
**Qoder 功能：**
- 全局记忆：个人偏好、编码风格、技术栈偏好
- 项目特定记忆：项目架构、业务规则、团队约定
- 自动学习：从交互中自动学习用户习惯
- 记忆优先级：项目记忆优先于全局记忆

**需要增强：**
```
src/pywiki/memory/
├── global_memory.py         # 全局记忆
├── project_memory.py        # 项目记忆
├── style_learner.py         # 编码风格学习
├── memory_manager.py        # 记忆管理器
└── memory_prioritizer.py    # 记忆优先级处理
```

### 3. 架构洞察（中优先级）
**Qoder 功能：**
- 设计模式识别：自动识别使用的设计模式
- 技术栈分析：识别框架、库、工具链
- 业务逻辑理解：理解代码背后的业务含义
- 架构演进追踪：跟踪架构变更历史

**需要新增：**
```
src/pywiki/insights/
├── pattern_detector.py      # 设计模式检测
├── tech_stack_analyzer.py   # 技术栈分析
├── business_logic.py        # 业务逻辑理解
└── architecture_evolution.py # 架构演进追踪
```

### 4. 高性能检索引擎（中优先级）
**Qoder 功能：**
- 10万文件级检索能力
- 跨模块语义理解
- 高性能代码搜索引擎
- 智能索引和缓存

**需要增强：**
```
src/pywiki/search/
├── code_search_engine.py    # 高性能代码搜索
├── semantic_indexer.py      # 语义索引器
├── cross_module_search.py   # 跨模块搜索
└── search_cache.py          # 搜索缓存
```

### 5. Agent 深度集成（中优先级）
**Qoder 功能：**
- Search Memory 工具
- 知识库实时查询
- 上下文自动补充
- 与 Wiki 知识联动

**需要增强：**
```
src/pywiki/agent/
├── search_memory_tool.py    # Search Memory 工具
├── context_enricher.py      # 上下文增强
├── wiki_agent_bridge.py     # Wiki-Agent 桥接
└── knowledge_query.py       # 知识查询接口
```

---

## 三、开发计划

### Phase 1: 隐性知识显性化（3天）
- 设计决策提取器
- 技术债务检测器
- 深层依赖分析

### Phase 2: 双层记忆系统（3天）
- 全局记忆管理
- 项目记忆管理
- 编码风格学习器

### Phase 3: 架构洞察（2天）
- 设计模式检测
- 技术栈分析

### Phase 4: 高性能检索（2天）
- 代码搜索引擎优化
- 跨模块语义搜索

### Phase 5: Agent 集成（2天）
- Search Memory 工具完善
- Wiki-Agent 桥接

---

## 四、验收标准
- 隐性知识可自动提取并展示
- 记忆系统支持全局/项目双层
- 可识别常见设计模式
- 支持10万级文件检索
- Agent 可通过 Search Memory 查询 Wiki
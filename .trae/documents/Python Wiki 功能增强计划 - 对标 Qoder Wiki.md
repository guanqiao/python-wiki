
# Python Wiki 功能增强计划 - 对标 Qoder Wiki

## 📋 当前项目状态分析

### 已实现功能
- ✅ LLM 客户端（支持多种配置）
- ✅ 代码解析器（Python/TypeScript/Java 基础框架）
- ✅ Mermaid 图表生成器（8种图表基础框架）
- ✅ Wiki 文档管理（存储、历史、管理器）
- ✅ 向量存储（ChromaDB）
- ✅ GUI 界面（PyQt6 基础框架）
- ✅ 监控系统（进度、日志、指标）
- ✅ 配置管理

### 缺少的核心功能

#### 1. 记忆系统
- 个人偏好记忆（代码风格、命名规范）
- 项目上下文记忆（架构设计、业务逻辑）
- 问题解决方案库（历史问题与解决方法）

#### 2. Agent 集成
- Search Memory 工具
- 深层次代码库感知

#### 3. 问答功能
- QA 面板（自然语言查询）
- 快速定位相关代码
- 智能回答生成

#### 4. 导出功能
- Markdown 导出（已有基础）
- HTML 导出
- PDF 导出

#### 5. Git 集成增强
- 完整的 Git 双向同步
- Wiki 共享（`.python-wiki/repowiki`）
- 团队协作共建

#### 6. 知识管理增强
- 隐性知识显性化
- 设计决策记录 (ADR)
- 深层依赖关系分析

#### 7. 文档滞后检测
- 变更检测与影响分析
- 文档滞后提醒
- 增量更新优化

#### 8. 完整图表生成
- 完善所有 8 种 Mermaid 图表生成器
- 集成到 Wiki 生成流程

#### 9. 多语言解析器完善
- 完善 TypeScript 解析器
- 完善 Java 解析器
- 集成到主流程

---

## 🎯 实施计划

### Phase 1: 记忆系统（优先级：高）
1. 创建 `memory/` 模块
2. 实现个人偏好记忆 (`personal.py`)
3. 实现项目上下文记忆 (`project.py`)
4. 实现解决方案库 (`solutions.py`)
5. 集成到配置和 Wiki 管理器

### Phase 2: 导出功能（优先级：高）
1. 创建 `wiki/export.py`
2. 实现 HTML 导出
3. 实现 PDF 导出（使用 WeasyPrint）
4. 集成到 GUI 和 CLI

### Phase 3: 问答功能（优先级：高）
1. 创建 `gui/panels/qa_panel.py`
2. 实现自然语言查询接口
3. 集成向量存储搜索
4. 集成 LLM 生成回答

### Phase 4: Agent 集成（优先级：中）
1. 创建 `agent/` 模块
2. 实现 Search Memory 工具
3. 集成到问答功能

### Phase 5: Git 集成增强（优先级：中）
1. 完善 `sync/` 模块
2. 实现完整的 Git 双向同步
3. 实现 Wiki 共享功能

### Phase 6: 知识管理增强（优先级：中）
1. 实现设计决策记录 (ADR)
2. 实现隐性知识提取
3. 实现深层依赖分析

### Phase 7: 文档滞后检测（优先级：中）
1. 完善变更检测
2. 实现影响分析
3. 实现文档滞后提醒

### Phase 8: 完善图表和解析器（优先级：中）
1. 完善所有 Mermaid 图表生成器
2. 完善 TypeScript/Java 解析器
3. 集成到主流程

---

## 📁 新增文件结构

```
src/pywiki/
├── memory/                    # 新增：记忆系统
│   ├── __init__.py
│   ├── personal.py           # 个人偏好
│   ├── project.py            # 项目上下文
│   └── solutions.py          # 解决方案库
├── agent/                     # 新增：Agent 集成
│   ├── __init__.py
│   └── search_memory.py      # Search Memory 工具
├── wiki/
│   └── export.py             # 新增：导出功能
└── gui/
    └── panels/
        └── qa_panel.py       # 新增：问答面板
```

---

## ✅ 验收标准

- 记忆系统完整可用
- 问答面板支持自然语言查询
- 支持 MD/HTML/PDF 三种导出格式
- Git 双向同步完整实现
- 所有 8 种 Mermaid 图表正常生成
- TypeScript/Java 解析器完整可用
- 文档滞后检测与提醒功能正常

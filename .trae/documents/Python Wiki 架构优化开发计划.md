# Python Wiki 架构优化开发计划

## 总览

| 阶段 | 内容 | 优先级 | 预估时间 |
|------|------|--------|----------|
| Phase 1 | 检索引擎重构 | 🔴 高 | 3 天 |
| Phase 2 | 隐性知识提取 | 🔴 高 | 3 天 |
| Phase 3 | Agent 协作增强 | 🟡 中 | 2 天 |
| Phase 4 | 记忆系统完善 | 🟡 中 | 2 天 |

---

## Phase 1: 检索引擎重构（3天）

### Day 1: 分层索引架构
- 创建 `search/engine.py` - 统一搜索引擎接口
- 创建 `search/tiered_index.py` - 项目/模块/文件三级索引
- 重构 `knowledge/vector_store.py` - 支持增量索引

### Day 2: 混合检索实现
- 创建 `search/hybrid_search.py` - 向量+BM25 混合检索
- 创建 `search/bm25_index.py` - BM25 关键词索引
- 实现结果融合排序算法

### Day 3: 搜索优化
- 创建 `search/cache.py` - LRU 搜索缓存
- 创建 `search/cross_project.py` - 跨项目检索
- 性能测试与优化

---

## Phase 2: 隐性知识提取（3天）

### Day 1: 设计动机分析
- 创建 `knowledge/design_motivation.py` - 从代码推断设计意图
- 创建 `knowledge/architecture_decision.py` - ADR 自动提取
- 集成 commit message 分析

### Day 2: 技术债务检测
- 创建 `knowledge/tech_debt_detector.py` - 代码异味检测
- 创建 `knowledge/complexity_analyzer.py` - 复杂度分析
- 创建 `knowledge/dependency_risk.py` - 依赖风险分析

### Day 3: 知识整合
- 创建 `knowledge/implicit_extractor.py` - 统一提取接口
- 更新 Wiki 生成器 - 集成隐性知识输出
- 编写测试用例

---

## Phase 3: Agent 协作增强（2天）

### Day 1: 工作流编排
- 创建 `agents/workflow/orchestrator.py` - DAG 编排器
- 创建 `agents/workflow/task_graph.py` - 任务图定义
- 创建 `agents/workflow/executor.py` - 并行执行器

### Day 2: 学习闭环
- 创建 `agents/learning/feedback.py` - 执行反馈收集
- 创建 `agents/learning/optimizer.py` - 策略优化器
- 创建 `agents/collaboration/message_bus.py` - 消息总线

---

## Phase 4: 记忆系统完善（2天）

### Day 1: 双层记忆
- 创建 `memory/global_memory.py` - 全局记忆管理
- 增强 `memory/project_memory.py` - 项目记忆优化
- 创建 `memory/memory_prioritizer.py` - 记忆优先级

### Day 2: 自动学习
- 创建 `memory/style_learner.py` - 编码风格学习
- 创建 `memory/memory_decay.py` - 记忆衰减机制
- 创建 `memory/knowledge_transfer.py` - 跨项目知识迁移

---

## 验收标准

### Phase 1
- [ ] 支持 10 万级文件索引
- [ ] 混合检索召回率 > 90%
- [ ] 搜索响应时间 < 500ms

### Phase 2
- [ ] 自动提取设计决策并生成 ADR
- [ ] 检测常见技术债务类型
- [ ] 隐性知识集成到 Wiki 输出

### Phase 3
- [ ] 支持 DAG 工作流编排
- [ ] Agent 可并行执行
- [ ] 执行结果可反馈学习

### Phase 4
- [ ] 全局/项目双层记忆正常工作
- [ ] 可自动学习编码风格
- [ ] 记忆优先级正确应用

---

## 文件清单

**新增文件（约 20 个）**：
```
src/pywiki/search/
├── engine.py, hybrid_search.py, tiered_index.py
├── bm25_index.py, cache.py, cross_project.py

src/pywiki/knowledge/
├── implicit_extractor.py, design_motivation.py
├── architecture_decision.py, tech_debt_detector.py
├── complexity_analyzer.py, dependency_risk.py

src/pywiki/agents/workflow/
├── orchestrator.py, task_graph.py, executor.py

src/pywiki/agents/learning/
├── feedback.py, optimizer.py

src/pywiki/agents/collaboration/
├── message_bus.py

src/pywiki/memory/
├── global_memory.py, memory_prioritizer.py
├── style_learner.py, memory_decay.py
├── knowledge_transfer.py
```

**修改文件（约 5 个）**：
- `vector_store.py` - 支持增量索引
- `wiki/manager.py` - 集成新功能
- `agents/base.py` - 增强协作能力
- `memory/memory_manager.py` - 统一接口
- `generators/markdown.py` - 输出隐性知识
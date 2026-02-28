## 优化目标
将所有Agent的系统提示词从简单描述升级为专业、结构化的提示词，提高LLM输出质量和一致性。

## 需要优化的文件

### 1. `src/pywiki/agents/base.py` - 基础Agent提示词
**当前问题**: 过于简单，缺乏角色定位和输出规范
**优化方向**: 增加角色定义、能力边界、输出格式要求

### 2. `src/pywiki/agents/documentation_agent.py` - 文档生成Agent
**当前问题**: 任务描述笼统，缺乏文档质量标准
**优化方向**: 增加文档写作规范、结构化输出要求、质量标准

### 3. `src/pywiki/agents/architecture_agent.py` - 架构分析Agent
**当前问题**: 缺乏架构分析方法论和评估标准
**优化方向**: 增加架构分析框架、评估维度、输出规范

### 4. `src/pywiki/agents/implicit_knowledge_agent.py` - 隐性知识挖掘Agent
**当前问题**: 相对较好，但置信度评估标准不明确
**优化方向**: 增加知识分类标准、置信度评估方法

### 5. `src/pywiki/agents/memory_agent.py` - 记忆管理Agent
**当前问题**: 任务描述不够具体
**优化方向**: 增加记忆检索策略、相关性评估方法

### 6. `src/pywiki/agents/multilang_agent.py` - 多语言分析Agent
**当前问题**: 缺乏跨语言分析的具体方法论
**优化方向**: 增加语言特性分析、API契约识别方法

### 7. `src/pywiki/gui/panels/qa_panel.py` - 问答面板
**当前问题**: 提示词过于简单
**优化方向**: 增加回答质量标准、引用规范

### 8. `src/pywiki/generators/docs/base.py` - 文档生成器基类
**当前问题**: 与DocumentationAgent重复
**优化方向**: 统一优化，增加文档类型特定指导

## 优化原则
1. **角色定义清晰**: 明确Agent的专业身份和核心能力
2. **任务结构化**: 使用编号列表明确任务步骤
3. **输出规范化**: 指定JSON/Markdown等输出格式
4. **质量标准**: 增加准确性、完整性、可读性要求
5. **双语支持**: 保持中英文双语提示词的一致性
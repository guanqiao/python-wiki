## 提取通用子包分析器供多 Agent 复用

### 问题分析
当前 `MultilangAgent` 中新增的子包分析功能可以服务于多个 Agent：
- **ArchitectureAgent**: 需要子包级别的架构分析
- **ImplicitKnowledgeAgent**: 需要子包结构来识别架构模式
- **DocumentationAgent**: 需要子包信息生成模块文档
- **pattern_detector.py**: 可以检测包级别的架构模式

### 解决方案
创建独立的 `PackageAnalyzer` 类，提供通用的子包分析功能。

### 实施步骤

#### 1. 创建 `src/pywiki/analysis/package_analyzer.py`
新建独立的包分析器模块，包含：
- `SubPackageInfo` 数据类
- `PackageDependency` 数据类
- `ArchitectureLayer` 数据类
- `PackageMetric` 数据类
- `PackageAnalyzer` 类，提供：
  - `detect_subpackages()` - 检测子包
  - `analyze_package_dependencies()` - 分析包依赖
  - `detect_layered_architecture()` - 检测分层架构
  - `calculate_package_metrics()` - 计算包指标
  - `analyze_package_boundaries()` - 分析包边界

#### 2. 更新 `MultilangAgent`
- 导入并使用 `PackageAnalyzer`
- 移除重复的数据类定义
- 委托给 `PackageAnalyzer` 处理

#### 3. 增强 `ArchitectureAgent`
- 导入 `PackageAnalyzer`
- 在 `_load_project_modules()` 中使用子包分析
- 增加包级别的架构指标

#### 4. 增强 `ImplicitKnowledgeAgent`
- 导入 `PackageAnalyzer`
- 在 `_analyze_project()` 中使用子包分析
- 增加包级别的隐性知识提取

#### 5. 增强 `pattern_detector.py`
- 添加包级别的模式检测方法
- 检测分层架构、微服务架构等

### 文件变更
1. **新建**: `src/pywiki/analysis/__init__.py`
2. **新建**: `src/pywiki/analysis/package_analyzer.py`
3. **修改**: `src/pywiki/agents/multilang_agent.py` - 使用 PackageAnalyzer
4. **修改**: `src/pywiki/agents/architecture_agent.py` - 增加子包分析
5. **修改**: `src/pywiki/agents/implicit_knowledge_agent.py` - 增加子包分析
6. **修改**: `src/pywiki/insights/pattern_detector.py` - 增加包级别模式检测
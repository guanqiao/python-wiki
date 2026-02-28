## 重构目标
将 architecture_generator.py（约1900行）拆分为多个职责单一、高内聚的模块，同时保持完美集成。

## 文件结构规划

### 1. 创建 analyzers/ 目录 - 架构分析器
存放各种架构分析逻辑：
- `__init__.py` - 导出分析器
- `style_analyzer.py` - 架构风格检测（_detect_architecture_style）
- `layer_analyzer.py` - 分层架构分析（_analyze_layers）
- `metrics_analyzer.py` - 质量指标计算（_calculate_quality_metrics）
- `dependency_analyzer.py` - 依赖分析（_detect_circular_dependencies, _detect_hot_spots, _analyze_external_dependencies）
- `module_filter.py` - 模块过滤工具（_is_third_party_module, _filter_project_modules）

### 2. 创建 diagrams/ 目录 - 图表生成器
存放图表生成逻辑：
- `__init__.py` - 导出图表生成器
- `c4_diagrams.py` - C4 模型图（_generate_c4_context, _generate_c4_container, _generate_c4_component）
- `architecture_diagram.py` - 架构图（_generate_architecture_diagram）
- `package_diagram.py` - 包图（_generate_package_diagram）
- `data_flow_diagram.py` - 数据流图（_generate_data_flow_diagram）
- `dependency_graph.py` - 依赖图（_generate_dependency_graph）

### 3. 创建 llm_diagrams/ 目录 - LLM 增强图表
存放 LLM 驱动的高阶图生成：
- `__init__.py` - 导出 LLM 图表生成器
- `flowchart_generator.py` - 流程图（_generate_flowchart_with_llm）
- `sequence_generator.py` - 序列图（_generate_sequence_diagram_with_llm）
- `class_diagram_generator.py` - 类图（_generate_class_diagram_with_llm）
- `state_diagram_generator.py` - 状态图（_generate_state_diagram_with_llm）
- `component_diagram_generator.py` - 组件图（_generate_component_diagram_with_llm）
- `enhancer.py` - LLM 增强（_enhance_with_llm）

### 4. 重构后的 architecture_generator.py
保留主类和协调逻辑：
- 类常量（THIRD_PARTY_PREFIXES, STANDARD_LIBS, EXTERNAL_CATEGORIES）
- __init__ 初始化
- generate 主入口
- _analyze_architecture 协调分析
- 工具方法（_sanitize_id, _extract_module_group, _extract_display_name）

### 5. 更新 __init__.py
确保导出保持不变，兼容性完美。

## 集成方式
- 使用组合模式：ArchitectureDocGenerator 组合各个分析器和生成器
- 保持接口兼容：所有公共方法签名不变
- 依赖注入：通过构造函数传入配置

## 实施步骤
1. 创建目录结构
2. 迁移分析器代码
3. 迁移图表生成器代码
4. 迁移 LLM 图表生成器代码
5. 重构主类
6. 测试验证
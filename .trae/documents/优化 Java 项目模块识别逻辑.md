## 修改计划

### 目标
修改 `overview_generator.py`，对于 Java 项目，优先使用 `PackageAnalyzer` 从 pom.xml/build.gradle 中提取模块信息，而不是依赖代码解析结果。

### 修改内容

**文件**: `src/pywiki/generators/docs/overview_generator.py`

1. **添加导入**：引入 `PackageAnalyzer`

2. **修改 `_extract_modules` 方法**：
   - 检测项目语言是否为 Java
   - 如果是 Java 项目，使用 `PackageAnalyzer.get_java_module_structure()` 获取模块信息
   - 将 `JavaModuleInfo` 转换为现有的模块字典格式
   - 对于非 Java 项目，保持原有逻辑

3. **新增辅助方法 `_extract_java_modules_from_pom`**：
   - 使用 PackageAnalyzer 解析 Maven/Gradle 模块
   - 返回格式化的模块列表

### 预期效果
- Java 项目的 overview 文档将显示从 pom.xml 解析出的真实模块结构
- 多模块 Maven/Gradle 项目能正确识别子模块
- 模块名称和描述将使用 artifactId 和 pom 中的 description
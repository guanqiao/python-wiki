## 任务概述
扩展 pywiki 的代码解析功能，支持 TypeScript/React/Vue 和 Java (Spring Boot/Spring MVC/MyBatis Plus) 主流技术栈。

## 现状分析
- 当前仅支持 Python 解析（使用 Python AST）
- 已安装 tree-sitter 基础库
- 解析器架构良好（BaseParser 抽象基类 + 具体实现）
- 类型系统完善（ModuleInfo/ClassInfo/FunctionInfo 等）

## 扩展计划

### Phase 1: TypeScript/JavaScript 解析器
**目标**: 支持 TS/JS/React/Vue 文件解析

1. **添加 tree-sitter 语言依赖**
   - tree-sitter-javascript
   - tree-sitter-typescript
   - tree-sitter-tsx

2. **创建 TypeScriptParser 类** (`src/pywiki/parsers/typescript.py`)
   - 支持扩展名: `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.vue`
   - 使用 tree-sitter 解析 AST
   - 提取信息:
     - 模块: imports/exports
     - 类: ES6 Class, React 组件 (函数组件/类组件)
     - 接口: TypeScript Interface/Type
     - 函数: 普通函数、箭头函数、异步函数
     - Vue SFC: template/script/style 分离解析

3. **React 特性识别**
   - Hooks 识别 (useState, useEffect 等)
   - 组件 Props/State 类型提取
   - JSX 结构分析

4. **Vue 特性识别**
   - Composition API / Options API 区分
   - 组件选项解析 (data, methods, computed, lifecycle)
   - Props/Emits 定义提取

### Phase 2: Java 解析器
**目标**: 支持 Java (Spring Boot/Spring MVC/MyBatis Plus) 解析

1. **添加 tree-sitter-java 依赖**

2. **创建 JavaParser 类** (`src/pywiki/parsers/java.py`)
   - 支持扩展名: `.java`
   - 提取信息:
     - Package/Import
     - Class/Interface/Enum/Annotation
     - 字段/方法/构造函数
     - 泛型信息

3. **Spring 框架特性识别**
   - 注解识别: @Controller, @Service, @Repository, @Component
   - 路由映射: @RequestMapping, @GetMapping, @PostMapping 等
   - 依赖注入: @Autowired, @Inject
   - AOP 注解: @Aspect, @Before, @After

4. **MyBatis Plus 特性识别**
   - Mapper 接口识别
   - 注解 SQL: @Select, @Insert, @Update, @Delete
   - Entity 类解析: 表名、字段映射

### Phase 3: 解析器工厂与统一入口
**目标**: 提供统一的解析器获取方式

1. **创建 ParserFactory** (`src/pywiki/parsers/factory.py`)
   - 根据文件扩展名自动选择解析器
   - 支持注册自定义解析器

2. **更新 __init__.py**
   - 导出新的解析器类
   - 导出工厂类

### Phase 4: 类型系统扩展
**目标**: 扩展 types.py 支持新语言特性

1. **新增类型字段** (可选)
   - `ComponentInfo`: React/Vue 组件特有信息
   - `RouteInfo`: Web 路由信息
   - `AnnotationInfo`: Java 注解信息

### Phase 5: 测试与文档
**目标**: 确保功能稳定

1. **编写单元测试**
   - TypeScript/React/Vue 测试用例
   - Java/Spring/MyBatis 测试用例

2. **更新文档**
   - 使用说明
   - 支持的语言列表

## 技术选型
- **解析引擎**: tree-sitter (已集成)
- **TS/JS 解析**: tree-sitter-javascript + tree-sitter-typescript
- **Java 解析**: tree-sitter-java

## 文件变更清单
```
src/pywiki/parsers/
├── factory.py              # 新增: 解析器工厂
├── typescript.py           # 新增: TypeScript 解析器
├── java.py                 # 新增: Java 解析器
├── __init__.py             # 修改: 导出新的解析器

tests/
├── parsers/
│   ├── test_typescript.py  # 新增
│   └── test_java.py        # 新增

pyproject.toml              # 修改: 添加 tree-sitter 语言包依赖
```

## 完成标准
- [ ] TypeScript/React/Vue 文件可正确解析
- [ ] Java/Spring/MyBatis 文件可正确解析
- [ ] 所有测试用例通过
- [ ] 代码静态检查通过 (ruff, mypy)
- [ ] 文档已更新
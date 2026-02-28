# Java项目Wiki文档生成能力增强计划

## 当前状态分析

### 已实现功能 ✅
- **Java解析器**：支持类/接口/枚举/Record/注解解析
- **Spring框架识别**：Controller、Service、Repository、Configuration
- **MyBatis Plus支持**：Entity、Mapper注解识别
- **JPA/Hibernate支持**：Entity、关系映射识别
- **Lombok支持**：Data、Builder、Slf4j等
- **API端点提取**：基础Spring MVC路由提取

### 需要增强的方面

---

## 增强计划

### 1. Java解析器增强 (`parsers/java.py`)

**1.1 增强注解属性值提取**
- 提取`@RequestMapping`、`@GetMapping`等完整属性（path、method、consumes、produces）
- 提取`@PathVariable`、`@RequestParam`、`@RequestBody`参数信息
- 提取JPA注解属性（`@Column`的nullable、length、unique等）

**1.2 新增框架识别**
- Dubbo：`@Service`、`@Reference`、`@DubboService`
- Netty：ChannelHandler、EventLoop相关
- Quartz：`@Scheduled`、Job相关
- Validation：`@NotNull`、`@Valid`等校验注解

**1.3 泛型类型完整解析**
- 解析类级别泛型参数
- 解析方法级别泛型参数
- 解析字段泛型类型

---

### 2. API文档生成器增强 (`generators/docs/api_generator.py`)

**2.1 增强Java端点提取**
- 完整解析Spring MVC方法参数注解
- 提取请求/响应体类型信息
- 支持Spring Security注解识别

**2.2 新增参数详情提取**
- `@RequestParam`：name、required、defaultValue
- `@PathVariable`：name、required
- `@RequestBody`：required
- `@RequestHeader`：name、required、defaultValue

---

### 3. 数据库文档生成器增强 (`generators/docs/database_generator.py`)

**3.1 JPA实体增强**
- 提取`@Column`完整属性
- 提取索引信息`@Index`
- 提取唯一约束`@UniqueConstraint`

**3.2 MyBatis Plus实体增强**
- 提取`@TableField`属性
- 提取逻辑删除、乐观锁字段标识

---

### 4. 新增Java项目依赖分析 (`generators/docs/dependencies_generator.py`)

**4.1 Maven依赖解析**
- 解析`pom.xml`提取依赖信息
- 提取parent继承关系
- 提取properties和profiles

**4.2 Gradle依赖解析**
- 解析`build.gradle`/`build.gradle.kts`
- 提取dependencies和plugins

---

### 5. 新增Java特定文档模板

**5.1 Spring Boot配置文档**
- 解析`application.yml`/`application.properties`
- 提取配置项说明

**5.2 Java项目结构文档**
- 包结构分析
- 分层架构识别（controller/service/repository/entity）

---

## 实施步骤

| 步骤 | 任务 | 文件 |
|-----|------|------|
| 1 | 增强Java解析器注解属性提取 | `parsers/java.py` |
| 2 | 新增Dubbo/Validation框架识别 | `parsers/java.py` |
| 3 | 增强API生成器Java端点提取 | `generators/docs/api_generator.py` |
| 4 | 增强数据库生成器JPA/MyBatis支持 | `generators/docs/database_generator.py` |
| 5 | 新增Maven/Gradle依赖解析 | `generators/docs/dependencies_generator.py` |
| 6 | 添加Java项目特定测试用例 | `tests/parsers/test_java.py` |

---

## 预期成果

1. **更完整的API文档**：包含完整的请求参数、响应类型、认证要求
2. **更详细的数据库文档**：包含字段约束、索引、关系详情
3. **依赖分析文档**：自动提取Maven/Gradle依赖信息
4. **更准确的框架识别**：支持更多Java主流框架
## 增强Java项目Wiki文档生成能力

### 现状分析
项目已有基础的Java解析器，支持：
- 基本语法（类、接口、枚举、注解、Record）
- Spring Boot/MVC框架识别
- MyBatis Plus、JPA/Hibernate、Lombok支持

### 增强计划

#### 1. 增强Java解析器 (`parsers/java.py`)
- **增强Spring注解解析**：
  - 解析`@RequestParam`、`@PathVariable`、`@RequestBody`、`@ResponseBody`等参数注解
  - 解析`@Qualifier`、`@Primary`等依赖注入注解
  - 提取更详细的API路由信息（方法级别路由）
  
- **新增框架支持**：
  - Spring Security（`@PreAuthorize`、`@Secured`、`@RolesAllowed`）
  - Spring Cloud（`@FeignClient`、`@EnableDiscoveryClient`）
  - Dubbo（`@Service`、`@Reference`）
  - Validation（`@Valid`、`@NotNull`、`@Size`等）

- **增强类型解析**：
  - 泛型类型完整解析（如`List<User>`、`Map<String, Object>`）
  - 注解属性值提取

#### 2. 增强API文档生成器 (`generators/docs/api_generator.py`)
- 完善Java端点提取逻辑，提取方法级别的路由映射
- 解析参数注解生成更详细的API参数文档
- 支持Swagger注解（`@ApiOperation`、`@ApiParam`等）

#### 3. 增强数据库文档生成器 (`generators/docs/database_generator.py`)
- 从JPA实体提取完整的字段约束信息
- 解析MyBatis XML映射文件
- 提取Lombok注解生成的字段信息

#### 4. 新增Java特定功能
- **Maven/Gradle依赖分析**：解析`pom.xml`/`build.gradle`
- **Spring Bean依赖关系图**：生成Bean之间的依赖关系Mermaid图

#### 5. 更新测试用例
- 添加新功能的测试覆盖
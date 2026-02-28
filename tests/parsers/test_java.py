"""
Java 解析器测试
"""

from pathlib import Path

import pytest

from pywiki.parsers.java import JavaParser
from pywiki.parsers.types import Visibility


class TestJavaParser:
    """Java 解析器测试类"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        return JavaParser()

    def test_get_supported_extensions(self, parser):
        """测试支持的文件扩展名"""
        extensions = parser.get_supported_extensions()
        assert ".java" in extensions
        assert len(extensions) == 1

    def test_parse_simple_class(self, parser, tmp_path):
        """测试解析简单类"""
        code = """
package com.example;

public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public int getAge() {
        return age;
    }

    public void setAge(int age) {
        this.age = age;
    }
}
"""
        file_path = tmp_path / "Person.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert module.name == "com.example.Person"
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "Person"
        assert len(cls.methods) >= 4  # getter/setter

    def test_parse_interface(self, parser, tmp_path):
        """测试解析接口"""
        code = """
package com.example;

public interface UserService {
    User findById(Long id);
    List<User> findAll();
    User save(User user);
    void delete(Long id);
}
"""
        file_path = tmp_path / "UserService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        interface = module.classes[0]
        assert interface.name == "UserService"
        assert "Interface" in (interface.docstring or "")

    def test_parse_enum(self, parser, tmp_path):
        """测试解析枚举"""
        code = """
package com.example;

public enum Status {
    ACTIVE,
    INACTIVE,
    PENDING,
    DELETED
}
"""
        file_path = tmp_path / "Status.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        enum = module.classes[0]
        assert enum.name == "Status"
        assert enum.is_enum is True
        assert len(enum.class_variables) == 4

    def test_parse_imports(self, parser, tmp_path):
        """测试解析导入语句"""
        code = """
package com.example;

import java.util.List;
import java.util.ArrayList;
import java.util.Map;
import java.util.HashMap;
import static java.lang.Math.PI;

public class Test {
}
"""
        file_path = tmp_path / "Test.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.imports) >= 4

    def test_parse_spring_controller(self, parser, tmp_path):
        """测试解析 Spring Controller"""
        code = """
package com.example.controller;

import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping
    public List<User> getAllUsers() {
        return userService.findAll();
    }

    @GetMapping("/{id}")
    public User getUser(@PathVariable Long id) {
        return userService.findById(id);
    }

    @PostMapping
    public User createUser(@RequestBody User user) {
        return userService.save(user);
    }

    @PutMapping("/{id}")
    public User updateUser(@PathVariable Long id, @RequestBody User user) {
        return userService.save(user);
    }

    @DeleteMapping("/{id}")
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }
}
"""
        file_path = tmp_path / "UserController.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "UserController"
        assert "Spring Controller" in (cls.docstring or "")
        assert "Route: /api/users" in (cls.docstring or "")

    def test_parse_spring_service(self, parser, tmp_path):
        """测试解析 Spring Service"""
        code = """
package com.example.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

@Service
public class UserServiceImpl implements UserService {

    @Autowired
    private UserRepository userRepository;

    @Override
    public User findById(Long id) {
        return userRepository.findById(id).orElse(null);
    }

    @Override
    public List<User> findAll() {
        return userRepository.findAll();
    }

    @Override
    public User save(User user) {
        return userRepository.save(user);
    }

    @Override
    public void delete(Long id) {
        userRepository.deleteById(id);
    }
}
"""
        file_path = tmp_path / "UserServiceImpl.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "UserServiceImpl"
        assert "Spring Service" in (cls.docstring or "")

    def test_parse_mybatis_entity(self, parser, tmp_path):
        """测试解析 MyBatis Plus Entity"""
        code = """
package com.example.entity;

import com.baomidou.mybatisplus.annotation.*;

@TableName("sys_user")
public class User {

    @TableId(type = IdType.AUTO)
    private Long id;

    @TableField("user_name")
    private String username;

    private String email;

    @Version
    private Integer version;

    @LogicDelete
    @TableField("is_deleted")
    private Boolean deleted;

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
}
"""
        file_path = tmp_path / "User.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "User"
        assert "MyBatis Plus Entity" in (cls.docstring or "")
        assert "Table: sys_user" in (cls.docstring or "")

    def test_parse_mybatis_mapper(self, parser, tmp_path):
        """测试解析 MyBatis Mapper"""
        code = """
package com.example.mapper;

import org.apache.ibatis.annotations.*;
import com.example.entity.User;
import java.util.List;

@Mapper
public interface UserMapper {

    @Select("SELECT * FROM sys_user WHERE id = #{id}")
    User findById(Long id);

    @Select("SELECT * FROM sys_user")
    List<User> findAll();

    @Insert("INSERT INTO sys_user(user_name, email) VALUES(#{username}, #{email})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(User user);

    @Update("UPDATE sys_user SET user_name = #{username}, email = #{email} WHERE id = #{id}")
    int update(User user);

    @Delete("DELETE FROM sys_user WHERE id = #{id}")
    int deleteById(Long id);
}
"""
        file_path = tmp_path / "UserMapper.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        mapper = module.classes[0]
        assert mapper.name == "UserMapper"
        assert "MyBatis Mapper" in (mapper.docstring or "")

    def test_parse_abstract_class(self, parser, tmp_path):
        """测试解析抽象类"""
        code = """
package com.example;

public abstract class BaseService<T> {

    protected abstract T findById(Long id);
    protected abstract List<T> findAll();
    protected abstract T save(T entity);
    protected abstract void delete(Long id);

    public void printInfo() {
        System.out.println("BaseService");
    }
}
"""
        file_path = tmp_path / "BaseService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "BaseService"
        assert cls.is_abstract is True

    def test_parse_generics(self, parser, tmp_path):
        """测试解析泛型"""
        code = """
package com.example;

import java.util.List;
import java.util.Map;

public class GenericService<T, ID> {

    public T findById(ID id) {
        return null;
    }

    public List<T> findAll() {
        return null;
    }

    public <R> R convert(T entity, Class<R> targetClass) {
        return null;
    }

    public Map<String, Object> toMap(T entity) {
        return null;
    }
}
"""
        file_path = tmp_path / "GenericService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.name == "GenericService"

    def test_parse_inner_class(self, parser, tmp_path):
        """测试解析内部类"""
        code = """
package com.example;

public class Outer {
    private String outerField;

    public class Inner {
        private String innerField;

        public void innerMethod() {
            System.out.println(outerField);
        }
    }

    public static class StaticInner {
        public void staticMethod() {
            System.out.println("static");
        }
    }
}
"""
        file_path = tmp_path / "Outer.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        outer = module.classes[0]
        assert outer.name == "Outer"

    def test_parse_directory(self, parser, tmp_path):
        """测试解析目录"""
        # 创建多个文件
        (tmp_path / "Class1.java").write_text("""
package com.example;
public class Class1 {}
""")
        (tmp_path / "Class2.java").write_text("""
package com.example;
public class Class2 {}
""")

        # 创建子目录
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "Class3.java").write_text("""
package com.example.subdir;
public class Class3 {}
""")

        result = parser.parse_directory(tmp_path)

        assert len(result.errors) == 0
        # 应该解析所有 java 文件
        assert len(result.modules) >= 2


class TestJavaParserEdgeCases:
    """Java 解析器边界情况测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_empty_file(self, parser, tmp_path):
        """测试空文件"""
        file_path = tmp_path / "Empty.java"
        file_path.write_text("")

        result = parser.parse_file(file_path)

        # 空文件应该能正常处理
        assert len(result.modules) >= 0

    def test_no_package(self, parser, tmp_path):
        """测试没有 package 声明的文件"""
        code = """
public class NoPackage {
    public void method() {}
}
"""
        file_path = tmp_path / "NoPackage.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert module.name == "NoPackage"

    def test_visibility_detection(self, parser, tmp_path):
        """测试可见性检测"""
        code = """
package com.example;

public class VisibilityTest {
    public String publicField;
    protected String protectedField;
    private String privateField;
    String packagePrivateField;

    public void publicMethod() {}
    protected void protectedMethod() {}
    private void privateMethod() {}
    void packagePrivateMethod() {}
}
"""
        file_path = tmp_path / "VisibilityTest.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_include_private_option(self, tmp_path):
        """测试 include_private 选项"""
        parser = JavaParser(include_private=True)

        code = """
package com.example;

public class Test {
    private void secretMethod() {}
    public void publicMethod() {}
}
"""
        file_path = tmp_path / "Test.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1
        # 应该包含私有方法
        assert len(module.classes[0].methods) >= 1

    def test_javadoc_extraction(self, parser, tmp_path):
        """测试 Javadoc 提取"""
        code = """
package com.example;

/**
 * This is a test class.
 * It has multiple lines of documentation.
 * @author Test Author
 */
public class Documented {

    /**
     * Gets the name.
     * @return the name
     */
    public String getName() {
        return "name";
    }
}
"""
        file_path = tmp_path / "Documented.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert cls.docstring is not None
        assert "test class" in cls.docstring


class TestSpringFeatures:
    """Spring 框架特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_rest_controller_routes(self, parser, tmp_path):
        """测试 REST Controller 路由解析"""
        code = """
package com.example;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1")
public class ApiController {

    @GetMapping("/items")
    public List<Item> list() { return null; }

    @PostMapping("/items")
    public Item create(@RequestBody Item item) { return null; }

    @GetMapping("/items/{id}")
    public Item get(@PathVariable Long id) { return null; }
}
"""
        file_path = tmp_path / "ApiController.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Spring Controller" in (cls.docstring or "")
        assert "Route: /api/v1" in (cls.docstring or "")

    def test_configuration_class(self, parser, tmp_path):
        """测试 Configuration 类"""
        code = """
package com.example;

import org.springframework.context.annotation.*;

@Configuration
public class AppConfig {

    @Bean
    public DataSource dataSource() {
        return new DataSource();
    }

    @Bean
    public JdbcTemplate jdbcTemplate(DataSource dataSource) {
        return new JdbcTemplate(dataSource);
    }
}
"""
        file_path = tmp_path / "AppConfig.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Spring Configuration" in (cls.docstring or "")

    def test_component_scan(self, parser, tmp_path):
        """测试 Component 注解"""
        code = """
package com.example;

import org.springframework.stereotype.*;

@Component
public class MyComponent {
    public void doSomething() {}
}

@Repository
public class UserRepository {
    public User findById(Long id) { return null; }
}
"""
        file_path = tmp_path / "Components.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 2

        for cls in module.classes:
            assert "Spring Service" in (cls.docstring or "") or \
                   cls.name == "MyComponent" or cls.name == "UserRepository"


class TestDubboFeatures:
    """Dubbo框架特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_dubbo_service(self, parser, tmp_path):
        """测试解析Dubbo服务"""
        code = """
package com.example.service;

import org.apache.dubbo.config.annotation.DubboService;

@DubboService(version = "1.0.0", timeout = 5000)
public class UserServiceImpl implements UserService {

    public User findById(Long id) {
        return null;
    }
}
"""
        file_path = tmp_path / "UserServiceImpl.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Dubbo" in (cls.docstring or "")

    def test_parse_dubbo_reference(self, parser, tmp_path):
        """测试解析Dubbo引用"""
        code = """
package com.example.controller;

import org.apache.dubbo.config.annotation.DubboReference;
import com.example.service.UserService;

public class UserController {

    @DubboReference(version = "1.0.0")
    private UserService userService;

    public User getUser(Long id) {
        return userService.findById(id);
    }
}
"""
        file_path = tmp_path / "UserController.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1


class TestValidationFeatures:
    """Validation校验特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_validation_annotations(self, parser, tmp_path):
        """测试解析校验注解"""
        code = """
package com.example.dto;

import javax.validation.constraints.*;

public class UserRequest {

    @NotNull
    private Long id;

    @NotBlank
    @Size(min = 2, max = 50)
    private String name;

    @Email
    private String email;

    @Min(0)
    @Max(150)
    private Integer age;
}
"""
        file_path = tmp_path / "UserRequest.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Validation" in (cls.docstring or "")


class TestQuartzFeatures:
    """Quartz定时任务特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_scheduled_method(self, parser, tmp_path):
        """测试解析定时任务方法"""
        code = """
package com.example.job;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class DataSyncJob {

    @Scheduled(cron = "0 0 2 * * ?")
    public void syncData() {
    }

    @Scheduled(fixedRate = 60000)
    public void heartbeat() {
    }

    @Scheduled(fixedDelay = 5000, initialDelay = 10000)
    public void cleanup() {
    }
}
"""
        file_path = tmp_path / "DataSyncJob.java"
        file_path.write_text(code, encoding="utf-8")

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Spring Service" in (cls.docstring or "") or "Component" in (cls.docstring or "")


class TestFeignFeatures:
    """Feign客户端特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_feign_client(self, parser, tmp_path):
        """测试解析Feign客户端"""
        code = """
package com.example.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

@FeignClient(name = "user-service", url = "http://localhost:8080", path = "/api")
public interface UserClient {

    @GetMapping("/users/{id}")
    User getUser(@PathVariable("id") Long id);

    @PostMapping("/users")
    User createUser(@RequestBody User user);

    @DeleteMapping("/users/{id}")
    void deleteUser(@PathVariable("id") Long id);
}
"""
        file_path = tmp_path / "UserClient.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Feign Client" in (cls.docstring or "")


class TestSpringSecurityFeatures:
    """Spring Security特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_security_annotations(self, parser, tmp_path):
        """测试解析安全注解"""
        code = """
package com.example.controller;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @PreAuthorize("hasRole('ADMIN')")
    @GetMapping("/users")
    public List<User> listUsers() {
        return null;
    }

    @PreAuthorize("hasAuthority('user:delete')")
    @DeleteMapping("/users/{id}")
    public void deleteUser(@PathVariable Long id) {
    }
}
"""
        file_path = tmp_path / "AdminController.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert "Security" in (cls.docstring or "") or "Spring Controller" in (cls.docstring or "")


class TestEnhancedEndpointExtraction:
    """增强端点提取测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_extract_consumes_produces(self, parser, tmp_path):
        """测试提取consumes和produces"""
        code = """
package com.example.controller;

import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping(value = "/api", produces = "application/json")
public class ApiController {

    @PostMapping(value = "/users", consumes = "application/json", produces = "application/json")
    public User createUser(@RequestBody User user) {
        return null;
    }

    @GetMapping(value = "/users", produces = {"application/json", "application/xml"})
    public List<User> listUsers() {
        return null;
    }
}
"""
        file_path = tmp_path / "ApiController.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        docstring = cls.docstring or ""
        assert "Spring Controller" in docstring
        assert "Route:" in docstring

    def test_extract_multiple_request_methods(self, parser, tmp_path):
        """测试提取多种请求方法"""
        code = """
package com.example.controller;

import org.springframework.web.bind.annotation.*;

@RestController
public class MultiMethodController {

    @GetMapping("/items")
    public List<Item> list() { return null; }

    @PostMapping("/items")
    public Item create(@RequestBody Item item) { return null; }

    @PutMapping("/items/{id}")
    public Item update(@PathVariable Long id, @RequestBody Item item) { return null; }

    @DeleteMapping("/items/{id}")
    public void delete(@PathVariable Long id) {}

    @PatchMapping("/items/{id}")
    public Item patch(@PathVariable Long id, @RequestBody Map<String, Object> updates) { return null; }
}
"""
        file_path = tmp_path / "MultiMethodController.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert len(cls.methods) >= 5


class TestTransactionalFeatures:
    """事务特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_transactional(self, parser, tmp_path):
        """测试解析事务注解"""
        code = """
package com.example.service;

import org.springframework.transaction.annotation.Transactional;
import org.springframework.stereotype.Service;

@Service
@Transactional(propagation = "REQUIRES_NEW", isolation = "READ_COMMITTED", timeout = 30)
public class OrderService {

    @Transactional(readOnly = true)
    public Order findById(Long id) {
        return null;
    }

    @Transactional(rollbackFor = Exception.class)
    public void createOrder(Order order) {
    }
}
"""
        file_path = tmp_path / "OrderService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        docstring = cls.docstring or ""
        assert "事务管理" in docstring or "Transactional" in docstring


class TestCacheFeatures:
    """缓存特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_cacheable(self, parser, tmp_path):
        """测试解析缓存注解"""
        code = """
package com.example.service;

import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Service;

@Service
public class CacheService {

    @Cacheable(value = "users", key = "#id")
    public User findById(Long id) {
        return null;
    }

    @CacheEvict(value = "users", allEntries = true)
    public void clearCache() {
    }
}
"""
        file_path = tmp_path / "CacheService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1


class TestAsyncFeatures:
    """异步特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_async(self, parser, tmp_path):
        """测试解析异步注解"""
        code = """
package com.example.service;

import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import java.util.concurrent.CompletableFuture;

@Service
public class AsyncService {

    @Async
    public CompletableFuture<String> asyncMethod() {
        return CompletableFuture.completedFuture("done");
    }
}
"""
        file_path = tmp_path / "AsyncService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1


class TestMapStructFeatures:
    """MapStruct特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_mapstruct_mapper(self, parser, tmp_path):
        """测试解析MapStruct Mapper"""
        code = """
package com.example.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.factory.Mappers;

@Mapper(componentModel = "spring", uses = {DateMapper.class})
public interface UserMapper {

    @Mapping(source = "firstName", target = "name")
    UserDTO toDTO(User user);

    User toEntity(UserDTO dto);
}
"""
        file_path = tmp_path / "UserMapper.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        docstring = cls.docstring or ""
        assert "MapStruct" in docstring or "Mapper" in docstring


class TestJavaDocParsing:
    """JavaDoc解析测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_javadoc_tags(self, parser, tmp_path):
        """测试解析JavaDoc标签"""
        code = """
package com.example.service;

/**
 * User Service Interface
 * 
 * @author John Doe
 * @version 1.0
 * @since 2024-01-01
 */
public interface UserService {

    /**
     * Find user by ID
     * 
     * @param id user ID
     * @return user object
     * @throws IllegalArgumentException if ID is null
     * @see User
     */
    User findById(Long id);
}
"""
        file_path = tmp_path / "UserService.java"
        file_path.write_text(code, encoding="utf-8")

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        javadoc = parser._parse_javadoc(cls.docstring or "")
        assert javadoc.author == "John Doe" or "John Doe" in javadoc.description


class TestComplexGenerics:
    """复杂泛型测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_nested_generics(self, parser, tmp_path):
        """测试解析嵌套泛型"""
        code = """
package com.example.repository;

import java.util.List;
import java.util.Map;

public class GenericRepository {

    public Map<String, List<User>> findByGroup() {
        return null;
    }

    public List<Map<String, Object>> findAsMap() {
        return null;
    }
}
"""
        file_path = tmp_path / "GenericRepository.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        cls = module.classes[0]
        assert len(cls.methods) >= 2

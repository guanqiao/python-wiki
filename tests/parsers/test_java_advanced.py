"""
Java 解析器高级功能测试
测试 Record、Lombok、JPA 支持
"""

from pathlib import Path

import pytest

from pywiki.parsers.java import JavaParser


class TestJavaRecord:
    """Java Record 测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_simple_record(self, parser, tmp_path):
        """测试解析简单 Record"""
        code = """
package com.example;

public record Person(String name, int age) {
}
"""
        file_path = tmp_path / "Person.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        assert len(module.classes) == 1

        record = module.classes[0]
        assert record.name == "Person"
        assert "Java Record" in (record.docstring or "")
        assert len(record.class_variables) == 2

    def test_parse_record_with_methods(self, parser, tmp_path):
        """测试解析带方法的 Record"""
        code = """
package com.example;

public record Point(int x, int y) {

    public double distanceToOrigin() {
        return Math.sqrt(x * x + y * y);
    }

    public static Point origin() {
        return new Point(0, 0);
    }
}
"""
        file_path = tmp_path / "Point.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        record = result.modules[0].classes[0]
        assert record.name == "Point"
        assert len(record.class_variables) == 2

    def test_parse_record_with_annotations(self, parser, tmp_path):
        """测试解析带注解的 Record"""
        code = """
package com.example;

import javax.validation.constraints.NotNull;
import javax.validation.constraints.Min;

public record User(
    @NotNull String name,
    @Min(0) int age
) {
}
"""
        file_path = tmp_path / "User.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        record = result.modules[0].classes[0]
        assert record.name == "User"


class TestJavaLombok:
    """Java Lombok 测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_lombok_data(self, parser, tmp_path):
        """测试解析 @Data 注解"""
        code = """
package com.example;

import lombok.Data;

@Data
public class User {
    private Long id;
    private String name;
    private String email;
}
"""
        file_path = tmp_path / "User.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "Lombok: Data" in (cls.docstring or "")
        assert "自动生成 Getter/Setter/ToString/EqualsAndHashCode" in (cls.docstring or "")

    def test_parse_lombok_builder(self, parser, tmp_path):
        """测试解析 @Builder 注解"""
        code = """
package com.example;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class Product {
    private Long id;
    private String name;
    private BigDecimal price;
}
"""
        file_path = tmp_path / "Product.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "Lombok: Data, Builder" in (cls.docstring or "")
        assert "Builder 模式" in (cls.docstring or "")

    def test_parse_lombok_slf4j(self, parser, tmp_path):
        """测试解析 @Slf4j 注解"""
        code = """
package com.example;

import lombok.extern.slf4j.Slf4j;

@Slf4j
public class LogService {

    public void doSomething() {
        log.info("Doing something");
    }
}
"""
        file_path = tmp_path / "LogService.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "Lombok: Slf4j" in (cls.docstring or "")
        assert "SLF4J Logger" in (cls.docstring or "")

    def test_parse_lombok_all_args_constructor(self, parser, tmp_path):
        """测试解析 Lombok 构造函数注解"""
        code = """
package com.example;

import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import lombok.RequiredArgsConstructor;

@NoArgsConstructor
@AllArgsConstructor
@RequiredArgsConstructor
public class Config {
    private String key;
    private String value;
}
"""
        file_path = tmp_path / "Config.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "NoArgsConstructor" in (cls.docstring or "")
        assert "AllArgsConstructor" in (cls.docstring or "")


class TestJavaJPA:
    """Java JPA/Hibernate 测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_jpa_entity(self, parser, tmp_path):
        """测试解析 JPA Entity"""
        code = """
package com.example;

import javax.persistence.*;

@Entity
@Table(name = "users")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_name", nullable = false)
    private String username;

    @Column(unique = true)
    private String email;

    @Version
    private Integer version;
}
"""
        file_path = tmp_path / "User.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "JPA Entity" in (cls.docstring or "")
        assert "Table: users" in (cls.docstring or "")

    def test_parse_jpa_relationships(self, parser, tmp_path):
        """测试解析 JPA 关系"""
        code = """
package com.example;

import javax.persistence.*;
import java.util.List;

@Entity
public class Department {

    @Id
    @GeneratedValue
    private Long id;

    private String name;

    @OneToMany(mappedBy = "department")
    private List<Employee> employees;

    @ManyToOne
    @JoinColumn(name = "company_id")
    private Company company;
}
"""
        file_path = tmp_path / "Department.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "JPA Entity" in (cls.docstring or "")
        assert "关系: 一对多, 多对一" in (cls.docstring or "")

    def test_parse_jpa_many_to_many(self, parser, tmp_path):
        """测试解析 JPA 多对多关系"""
        code = """
package com.example;

import javax.persistence.*;
import java.util.Set;

@Entity
public class Student {

    @Id
    private Long id;

    private String name;

    @ManyToMany
    @JoinTable(
        name = "student_course",
        joinColumns = @JoinColumn(name = "student_id"),
        inverseJoinColumns = @JoinColumn(name = "course_id")
    )
    private Set<Course> courses;
}
"""
        file_path = tmp_path / "Student.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "多对多" in (cls.docstring or "")

    def test_parse_jpa_one_to_one(self, parser, tmp_path):
        """测试解析 JPA 一对一关系"""
        code = """
package com.example;

import javax.persistence.*;

@Entity
public class User {

    @Id
    private Long id;

    private String username;

    @OneToOne(cascade = CascadeType.ALL)
    @JoinColumn(name = "profile_id")
    private UserProfile profile;
}
"""
        file_path = tmp_path / "User.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        cls = result.modules[0].classes[0]
        assert "一对一" in (cls.docstring or "")


class TestJavaAdvancedFeatures:
    """Java 高级特性测试"""

    @pytest.fixture
    def parser(self):
        return JavaParser()

    def test_parse_sealed_class(self, parser, tmp_path):
        """测试解析 Sealed Class (Java 17+)"""
        code = """
package com.example;

public abstract sealed class Shape
    permits Circle, Rectangle, Square {

    public abstract double area();
}

final class Circle extends Shape {
    private double radius;

    @Override
    public double area() {
        return Math.PI * radius * radius;
    }
}

final class Rectangle extends Shape {
    private double width;
    private double height;

    @Override
    public double area() {
        return width * height;
    }
}

final class Square extends Shape {
    private double side;

    @Override
    public double area() {
        return side * side;
    }
}
"""
        file_path = tmp_path / "Shape.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1
        module = result.modules[0]
        # 应该解析出 4 个类
        assert len(module.classes) >= 4

    def test_parse_var_keyword(self, parser, tmp_path):
        """测试解析 var 关键字 (Java 10+)"""
        code = """
package com.example;

import java.util.List;

public class VarExample {

    public void example() {
        var message = "Hello World";
        var numbers = List.of(1, 2, 3);
        var count = 42;

        for (var i = 0; i < 10; i++) {
            System.out.println(i);
        }
    }
}
"""
        file_path = tmp_path / "VarExample.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_parse_switch_expression(self, parser, tmp_path):
        """测试解析 Switch 表达式 (Java 14+)"""
        code = """
package com.example;

public class SwitchExample {

    public String getDayType(String day) {
        return switch (day) {
            case "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY" -> "Weekday";
            case "SATURDAY", "SUNDAY" -> "Weekend";
            default -> throw new IllegalArgumentException("Invalid day");
        };
    }

    public int getNumber(String number) {
        return switch (number) {
            case "one" -> 1;
            case "two" -> 2;
            default -> {
                yield 0;
            }
        };
    }
}
"""
        file_path = tmp_path / "SwitchExample.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

    def test_parse_text_blocks(self, parser, tmp_path):
        """测试解析文本块 (Java 15+)"""
        code = '''
package com.example;

public class TextBlockExample {

    private static final String JSON = """
        {
            "name": "John",
            "age": 30
        }
        """;

    private static final String SQL = """
        SELECT id, name, email
        FROM users
        WHERE status = 'ACTIVE'
        ORDER BY created_at DESC
        """;

    public String getHtml() {
        return """
            <html>
                <body>
                    <h1>Hello</h1>
                </body>
            </html>
            """;
    }
}
'''
        file_path = tmp_path / "TextBlockExample.java"
        file_path.write_text(code)

        result = parser.parse_file(file_path)

        assert len(result.errors) == 0
        assert len(result.modules) == 1

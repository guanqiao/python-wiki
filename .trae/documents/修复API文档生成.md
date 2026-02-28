## 问题根因

Java解析器提取了注解，但**没有将注解赋值给 decorators 字段**，导致API生成器无法识别Spring Controller。

### 具体问题

1. **`_parse_class` 方法** (java.py:320-329): 创建 ClassInfo 时缺少 `decorators=annotations`
2. **`_parse_method` 方法** (java.py:566-577): 创建 FunctionInfo 时缺少 `decorators=annotations`

### 修复方案

#### 修复1: ClassInfo 添加 decorators
```python
class_info = ClassInfo(
    name=name,
    full_name=full_name,
    bases=bases,
    visibility=visibility,
    is_abstract=is_abstract,
    docstring=self._extract_javadoc(node, source),
    line_start=node.start_point[0] + 1,
    line_end=node.end_point[0] + 1,
    decorators=annotations,  # 添加这一行
)
```

#### 修复2: FunctionInfo 添加 decorators
```python
func_info = FunctionInfo(
    name=name,
    full_name=full_name,
    parameters=parameters,
    return_type=return_type,
    visibility=visibility,
    is_staticmethod=is_static,
    is_abstract=is_abstract,
    docstring=self._extract_javadoc(node, source),
    line_start=node.start_point[0] + 1,
    line_end=node.end_point[0] + 1,
    decorators=annotations,  # 添加这一行
)
```

### 预期效果

修复后，API生成器将能够：
1. 识别 `@RestController`、`@Controller` 注解
2. 提取 `@GetMapping`、`@PostMapping` 等端点映射
3. 生成包含实际API端点的文档
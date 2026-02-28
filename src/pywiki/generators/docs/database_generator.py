"""
数据库文档生成器
支持 Python/Java/TypeScript 多语言项目
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language


class DatabaseGenerator(BaseDocGenerator):
    """数据库文档生成器"""

    doc_type = DocType.DATABASE
    template_name = "database.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成数据库文档"""
        try:
            project_language = context.project_language or context.detect_project_language()
            
            db_data = self._extract_db_data(context, project_language)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    db_data,
                    context.metadata["llm_client"]
                )
                db_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 数据库设计文档",
                er_diagram=db_data.get("er_diagram", ""),
                tables=db_data.get("tables", []),
                relationships=db_data.get("relationships", []),
                db_config=db_data.get("db_config", {}),
                orm_type=db_data.get("orm_type", ""),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=self.labels.get("database_doc_success", "Database documentation generated successfully"),
                metadata={"db_data": db_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"{self.labels.get('generation_failed', 'Generation failed')}: {str(e)}",
            )

    def _extract_db_data(self, context: DocGeneratorContext, project_language: str) -> dict[str, Any]:
        """提取数据库数据"""
        db_data = {
            "er_diagram": "",
            "tables": [],
            "relationships": [],
            "summary": {},
            "db_config": {},
            "orm_type": "",
        }

        if project_language == "java":
            db_data["tables"] = self._extract_java_tables(context)
            db_data["orm_type"] = self._detect_java_orm(context)
            db_data["db_config"] = self._extract_java_db_config(context)
        elif project_language == "typescript":
            db_data["tables"] = self._extract_typescript_tables(context)
            db_data["orm_type"] = self._detect_typescript_orm(context)
            db_data["db_config"] = self._extract_typescript_db_config(context)
        else:
            db_data["tables"] = self._extract_python_tables(context)
            db_data["orm_type"] = self._detect_python_orm(context)
            db_data["db_config"] = self._extract_python_db_config(context)

        if not db_data["tables"]:
            db_data["tables"] = self._extract_from_sql_files(context)
        else:
            sql_tables = self._extract_from_sql_files(context)
            existing_tables = {t["name"].lower() for t in db_data["tables"]}
            for sql_table in sql_tables:
                if sql_table["name"].lower() not in existing_tables:
                    db_data["tables"].append(sql_table)
                    existing_tables.add(sql_table["name"].lower())

        db_data["relationships"] = self._extract_relationships(context, db_data["tables"], project_language)
        db_data["er_diagram"] = self._generate_er_diagram(db_data["tables"], db_data["relationships"])

        db_data["summary"] = {
            "table_count": len(db_data["tables"]),
            "relationship_count": len(db_data["relationships"]),
            "orm_type": db_data["orm_type"],
            "has_db_config": bool(db_data["db_config"]),
        }

        return db_data

    def _extract_python_tables(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Python 数据库模型"""
        tables = []

        if not context.parse_result or not context.parse_result.modules:
            return tables

        model_keywords = ["model", "entity", "schema", "table", "orm", "db"]

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            
            for cls in module.classes:
                is_model = False
                table_name = cls.name
                
                if hasattr(cls, 'decorators') and cls.decorators:
                    for decorator in cls.decorators:
                        if "table" in decorator.lower() or "entity" in decorator.lower():
                            is_model = True
                            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', decorator)
                            if name_match:
                                table_name = name_match.group(1)
                
                if hasattr(cls, 'is_dataclass') and cls.is_dataclass:
                    if any(kw in module_lower for kw in model_keywords):
                        is_model = True
                
                for base in cls.bases:
                    if any(model_base in base for model_base in ["Model", "Base", "Entity", "Document", "Schema"]):
                        is_model = True
                
                if any(kw in module_lower for kw in model_keywords) and not is_model:
                    is_model = True
                
                if is_model:
                    table = {
                        "name": table_name,
                        "class_name": cls.name,
                        "description": cls.docstring.split("\n")[0] if cls.docstring else "",
                        "columns": [],
                        "indexes": [],
                        "primary_key": "",
                        "foreign_keys": [],
                    }

                    for prop in cls.properties:
                        column = {
                            "name": prop.name,
                            "type": self._map_python_type(prop.type_hint or "Any"),
                            "constraints": self._infer_python_constraints(prop, cls),
                            "description": "",
                            "is_primary": False,
                            "is_foreign": False,
                            "is_nullable": True,
                        }
                        
                        if column["constraints"] and "PRIMARY KEY" in column["constraints"]:
                            column["is_primary"] = True
                            table["primary_key"] = prop.name
                        
                        if column["constraints"] and "FOREIGN KEY" in column["constraints"]:
                            column["is_foreign"] = True
                            table["foreign_keys"].append(prop.name)
                        
                        if column["constraints"] and "NOT NULL" in column["constraints"]:
                            column["is_nullable"] = False
                        
                        table["columns"].append(column)

                    if table["columns"]:
                        table["indexes"] = self._extract_jpa_indexes(cls.docstring or "", cls)
                        tables.append(table)

        return tables[:30]

    def _extract_jpa_indexes(self, cls_docstring: str, cls: Any) -> list[dict[str, Any]]:
        """提取JPA索引信息"""
        indexes = []
        
        if hasattr(cls, 'decorators') and cls.decorators:
            for decorator in cls.decorators:
                decorator_lower = decorator.lower()
                
                if "@table" in decorator_lower:
                    indexes_pattern = r'indexes\s*=\s*\{([^}]+)\}'
                    indexes_match = re.search(indexes_pattern, decorator, re.IGNORECASE)
                    if indexes_match:
                        indexes_content = indexes_match.group(1)
                        
                        index_pattern = r'@Index\s*\(\s*name\s*=\s*["\']([^"\']+)["\'](?:\s*,\s*columnList\s*=\s*["\']([^"\']+)["\']|[^)]*)\)'
                        for match in re.finditer(index_pattern, indexes_content):
                            index_name = match.group(1)
                            column_list = match.group(2) or ""
                            indexes.append({
                                "name": index_name,
                                "columns": [c.strip() for c in column_list.split(",") if c.strip()],
                                "type": "INDEX",
                                "unique": False,
                            })
                    
                    unique_pattern = r'uniqueConstraints\s*=\s*\{([^}]+)\}'
                    unique_match = re.search(unique_pattern, decorator, re.IGNORECASE)
                    if unique_match:
                        unique_content = unique_match.group(1)
                        
                        uc_pattern = r'@UniqueConstraint\s*\(\s*(?:name\s*=\s*["\']([^"\']+)["\']\s*,\s*)?columnNames\s*=\s*\{([^}]+)\}'
                        for match in re.finditer(uc_pattern, unique_content, re.IGNORECASE):
                            uc_name = match.group(1) or f"uk_{len(indexes)}"
                            column_names = match.group(2)
                            columns = re.findall(r'["\']([^"\']+)["\']', column_names)
                            indexes.append({
                                "name": uc_name,
                                "columns": columns,
                                "type": "UNIQUE",
                                "unique": True,
                            })
        
        for prop in getattr(cls, 'class_variables', []):
            if hasattr(prop, 'decorators') and prop.decorators:
                for dec in prop.decorators:
                    dec_lower = dec.lower()
                    if "@column" in dec_lower:
                        if "unique = true" in dec_lower or "unique=true" in dec_lower:
                            indexes.append({
                                "name": f"uk_{prop.name}",
                                "columns": [prop.name],
                                "type": "UNIQUE",
                                "unique": True,
                            })
        
        return indexes

    def _is_valid_table_name(self, name: str) -> bool:
        """验证表名是否有效"""
        if not name or len(name) < 2:
            return False

        name_clean = name.strip()
        if len(name_clean) < 2:
            return False

        # 检查是否包含明显的代码片段
        invalid_patterns = [
            'public class', 'private class', 'protected class',
            'public static', 'private static', 'protected static',
            'private string', 'private int', 'private long', 'private boolean',
            'private final', 'implements', 'extends',
            'return ', 'import ', 'package ',
            '@RestController', '@Controller', '@Service', '@Component',
            'class ', 'interface ', 'enum ',
            '/**', '*/', '//',
        ]

        name_lower = name_clean.lower()
        for pattern in invalid_patterns:
            if pattern.lower() in name_lower:
                return False

        # 检查是否包含换行或过多空格（可能是代码片段）
        if '\n' in name_clean or '\t' in name_clean:
            return False

        # 检查是否以引号开头（字符串字面量）
        if name_clean[0] in ('"', "'", '`'):
            return False

        # 检查是否以数字开头
        if name_clean[0].isdigit():
            return False

        # 检查是否只包含有效字符（字母、数字、下划线）
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name_clean):
            return False

        # 表名应该有一定长度，且通常是小写或驼峰/下划线格式
        if len(name_clean) >= 2:
            return True

        return False

    def _extract_java_tables(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Java 数据库模型"""
        tables = []

        if not context.parse_result or not context.parse_result.modules:
            return tables

        non_entity_patterns = [
            'Controller', 'RestController', 'ControllerAdvice',
            'Service', 'ServiceImpl', 'Component',
            'Configuration', 'Config', 'Bean',
            'Aspect', 'Interceptor', 'Filter',
            'Handler', 'Exception', 'Error',
            'Util', 'Utils', 'Helper', 'HelperImpl',
            'DTO', 'VO', 'BO', 'Request', 'Response',
            'Param', 'Result', 'ResponseEntity',
            'HttpRequest', 'HttpResponse', 'Servlet',
            'Application', 'Runner', 'CommandLineRunner',
            'ExceptionHandler', 'ControllerAdvice',
            'Test', 'Tests', 'TestCase',
            'Constants', 'Enum', 'Type',
        ]

        entity_suffixes = ['DO', 'Entity', 'PO', 'POJO', 'EO']

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            is_dal_module = any(kw in module_lower for kw in ['dal', 'dataobject', 'entity', 'domain', 'model', 'pojo'])

            for cls in module.classes:
                is_entity = False
                table_name = None
                orm_type = "JPA"

                cls_docstring = cls.docstring or ""
                class_name = cls.name

                # 首先检查是否应该排除（非实体类）
                should_skip = False
                for pattern in non_entity_patterns:
                    if class_name.endswith(pattern) or class_name == pattern:
                        should_skip = True
                        break

                if should_skip:
                    continue

                # 检查装饰器来确定是否是实体类
                decorators = getattr(cls, 'decorators', [])
                for decorator in decorators:
                    if not decorator:
                        continue
                    decorator_str = str(decorator)
                    decorator_lower = decorator_str.lower()

                    # JPA @Entity
                    if "@entity" in decorator_lower:
                        is_entity = True
                        # 尝试从 @Table 注解获取表名
                        name_match = re.search(r'@Table\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']', decorator_str, re.IGNORECASE)
                        if name_match:
                            table_name = name_match.group(1)

                    # MyBatis Plus @TableName
                    if "@tablename" in decorator_lower:
                        is_entity = True
                        orm_type = "MyBatis Plus"
                        name_match = re.search(r'@TableName\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']', decorator_str, re.IGNORECASE)
                        if name_match:
                            table_name = name_match.group(1)

                    # 如果有 @TableId 也是实体类
                    if "@tableid" in decorator_lower:
                        is_entity = True
                        orm_type = "MyBatis Plus"

                # 检查基类
                if not is_entity:
                    bases = getattr(cls, 'bases', [])
                    for base in bases:
                        if any(entity_base in base for entity_base in ["Entity", "BaseEntity", "AbstractEntity", "Persistable", "BaseDO"]):
                            is_entity = True
                            break

                # 检查类名后缀
                if not is_entity:
                    for suffix in entity_suffixes:
                        if class_name.endswith(suffix) and len(class_name) > len(suffix) + 1:
                            is_entity = True
                            break

                # 检查模块名
                if not is_entity and is_dal_module:
                    is_entity = True

                if not is_entity:
                    continue

                # 确定表名
                if not table_name:
                    # 从类名推断表名（下划线格式）
                    table_name = self._camel_to_snake(class_name)
                    # 移除常见的后缀
                    for suffix in ['_do', '_entity', '_po', '_pojo', '_eo']:
                        if table_name.endswith(suffix):
                            table_name = table_name[:-len(suffix)]
                            break

                # 验证表名
                if not self._is_valid_table_name(table_name):
                    continue

                table = {
                    "name": table_name,
                    "class_name": cls.name,
                    "description": self._clean_java_docstring(cls_docstring),
                    "columns": [],
                    "indexes": [],
                    "primary_key": "",
                    "foreign_keys": [],
                    "orm_type": orm_type,
                }

                class_variables = getattr(cls, 'class_variables', [])
                for prop in class_variables:
                    column = self._extract_java_column_from_property(prop, cls_docstring)
                    if column:
                        if column.get("is_primary"):
                            table["primary_key"] = column["name"]
                        if column.get("is_foreign"):
                            table["foreign_keys"].append(column["name"])
                        table["columns"].append(column)

                methods = getattr(cls, 'methods', [])
                for method in methods:
                    if method.name.startswith("get") and len(method.name) > 3:
                        prop_name = method.name[3].lower() + method.name[4:]
                        if not any(c["name"] == prop_name for c in table["columns"]):
                            if method.return_type:
                                column = {
                                    "name": prop_name,
                                    "type": self._map_java_type(method.return_type),
                                    "constraints": "",
                                    "description": "",
                                    "is_primary": False,
                                    "is_foreign": False,
                                    "is_nullable": True,
                                }
                                table["columns"].append(column)

                if table["columns"]:
                    tables.append(table)

        return tables[:30]

    def _camel_to_snake(self, name: str) -> str:
        """将驼峰命名转换为下划线命名"""
        # 处理连续的大写字母（如 HTTPRequest -> http_request）
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _extract_java_column_from_property(self, prop: Any, cls_docstring: str) -> Optional[dict[str, Any]]:
        """从属性提取Java列信息"""
        # 验证字段名是否有效
        field_name = prop.name.strip()

        # 过滤掉无效的字段名（代码片段）
        if not field_name or len(field_name) < 1:
            return None

        # 检查字段名是否包含代码片段
        invalid_patterns = [
            'private ', 'public ', 'protected ', 'static ', 'final ',
            '/**', '*/', '//', '/*',
            '= ', ';', '{', '}',
            'String ', 'Integer ', 'Long ', 'Boolean ', 'int ', 'long ', 'bool ',
            'return ', 'if ', 'else ', 'for ', 'while ',
        ]
        for pattern in invalid_patterns:
            if pattern.lower() in field_name.lower():
                return None

        # 检查字段名是否包含换行或空格
        if '\n' in field_name or '\t' in field_name or '  ' in field_name:
            return None

        name_lower = field_name.lower()

        column = {
            "name": field_name,
            "type": self._map_java_type(prop.type_hint or "Object"),
            "constraints": "",
            "description": "",
            "is_primary": False,
            "is_foreign": False,
            "is_nullable": True,
            "length": None,
            "precision": None,
            "scale": None,
        }

        constraints = []

        if hasattr(prop, 'decorators') and prop.decorators:
            for decorator in prop.decorators:
                decorator_lower = decorator.lower()

                if "@id" in decorator_lower:
                    constraints.append("PRIMARY KEY")
                    column["is_primary"] = True

                if "@tableid" in decorator_lower:
                    constraints.append("PRIMARY KEY")
                    column["is_primary"] = True

                if "@column" in decorator_lower:
                    if "unique = true" in decorator_lower or "unique=true" in decorator_lower:
                        constraints.append("UNIQUE")
                    if "nullable = false" in decorator_lower or "nullable=false" in decorator_lower:
                        constraints.append("NOT NULL")
                        column["is_nullable"] = False

                    length_match = re.search(r'length\s*=\s*(\d+)', decorator)
                    if length_match:
                        column["length"] = int(length_match.group(1))

                    precision_match = re.search(r'precision\s*=\s*(\d+)', decorator)
                    if precision_match:
                        column["precision"] = int(precision_match.group(1))

                    scale_match = re.search(r'scale\s*=\s*(\d+)', decorator)
                    if scale_match:
                        column["scale"] = int(scale_match.group(1))

                    # 从 @Column 注解获取字段名
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', decorator)
                    if name_match:
                        column["name"] = name_match.group(1)

                if "@tablefield" in decorator_lower:
                    # 从 @TableField 注解获取字段名
                    name_match = re.search(r'(?:value|name)\s*=\s*["\']([^"\']+)["\']', decorator)
                    if name_match:
                        column["name"] = name_match.group(1)

                    if "exist = false" in decorator_lower or "exist=false" in decorator_lower:
                        return None

                if "@onetomany" in decorator_lower or "@manytoone" in decorator_lower or "@onetoone" in decorator_lower or "@manytomany" in decorator_lower:
                    constraints.append("FOREIGN KEY")
                    column["is_foreign"] = True

                if "@joincolumn" in decorator_lower:
                    constraints.append("FOREIGN KEY")
                    column["is_foreign"] = True
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', decorator)
                    if name_match:
                        column["name"] = name_match.group(1)

                if "@version" in decorator_lower:
                    constraints.append("VERSION")
                    column["description"] = "乐观锁版本号"

                if "@logicdelete" in decorator_lower or "@tablelogic" in decorator_lower:
                    constraints.append("LOGIC_DELETE")
                    column["description"] = "逻辑删除标记"

        # 根据字段名推断约束
        if name_lower == "id":
            if "PRIMARY KEY" not in constraints:
                constraints.append("PRIMARY KEY")
                column["is_primary"] = True
        elif name_lower.endswith("id") and not name_lower.startswith("is") and len(name_lower) > 2:
            if "FOREIGN KEY" not in constraints:
                constraints.append("FOREIGN KEY")
                column["is_foreign"] = True

        if name_lower in ("createdat", "updatedat", "deletedat", "create_time", "update_time", "delete_time"):
            constraints.append("TIMESTAMP")
            if "createdat" in name_lower or "create_time" in name_lower:
                column["description"] = "创建时间"
            elif "updatedat" in name_lower or "update_time" in name_lower:
                column["description"] = "更新时间"
            elif "deletedat" in name_lower or "delete_time" in name_lower:
                column["description"] = "删除时间"

        if "email" in name_lower:
            if "UNIQUE" not in constraints:
                constraints.append("UNIQUE")

        column["constraints"] = ", ".join(constraints) if constraints else ""

        return column

    def _clean_java_docstring(self, docstring: str) -> str:
        """清理Java文档字符串"""
        if not docstring:
            return ""
        
        prefixes_to_remove = [
            "JPA Entity", "MyBatis Plus Entity", "Spring Controller",
            "Spring Service", "Spring Configuration", "Lombok:",
            "Table:", "Route:", "Method:", "Consumes:", "Produces:",
            "Security:", "关系:", "Interface", "Enum", "Java Record",
            "Annotation", "Dubbo:", "Feign Client", "Validation:"
        ]
        
        lines = docstring.split("\n")
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            skip = False
            for prefix in prefixes_to_remove:
                if line.startswith(prefix) or f" {prefix}" in line or f"| {prefix}" in line:
                    skip = True
                    break
            if not skip and line:
                cleaned_lines.append(line)
        
        return cleaned_lines[0] if cleaned_lines else ""

    def _extract_typescript_tables(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 TypeScript 数据库模型"""
        tables = []

        if not context.parse_result or not context.parse_result.modules:
            return tables

        entity_keywords = ["entity", "model", "schema", "interface"]

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            
            for cls in module.classes:
                is_entity = False
                table_name = cls.name
                
                if hasattr(cls, 'decorators') and cls.decorators:
                    for decorator in cls.decorators:
                        decorator_lower = decorator.lower()
                        if "@entity" in decorator_lower or "@table" in decorator_lower or "@schema" in decorator_lower:
                            is_entity = True
                
                for base in cls.bases:
                    if any(entity_base in base for entity_base in ["Entity", "BaseEntity", "Model", "Schema"]):
                        is_entity = True
                
                if any(kw in module_lower for kw in entity_keywords):
                    is_entity = True
                
                if is_entity:
                    table = {
                        "name": table_name,
                        "class_name": cls.name,
                        "description": cls.docstring.split("\n")[0] if cls.docstring else "",
                        "columns": [],
                        "indexes": [],
                        "primary_key": "",
                        "foreign_keys": [],
                    }

                    for prop in cls.properties:
                        column = {
                            "name": prop.name,
                            "type": self._map_typescript_type(prop.type_hint or "any"),
                            "constraints": self._infer_typescript_constraints(prop, cls),
                            "description": "",
                            "is_primary": False,
                            "is_foreign": False,
                            "is_nullable": True,
                        }
                        
                        if column["constraints"] and "PRIMARY KEY" in column["constraints"]:
                            column["is_primary"] = True
                            table["primary_key"] = prop.name
                        
                        if column["constraints"] and "FOREIGN KEY" in column["constraints"]:
                            column["is_foreign"] = True
                            table["foreign_keys"].append(prop.name)
                        
                        table["columns"].append(column)

                    if table["columns"]:
                        tables.append(table)

        prisma_schema = context.project_path / "prisma" / "schema.prisma"
        if prisma_schema.exists():
            prisma_tables = self._extract_from_prisma_schema(prisma_schema)
            tables.extend(prisma_tables)

        return tables[:30]

    def _extract_from_prisma_schema(self, schema_path: Path) -> list[dict[str, Any]]:
        """从 Prisma schema 提取表结构"""
        tables = []
        
        try:
            content = schema_path.read_text(encoding="utf-8")
            
            model_pattern = r"model\s+(\w+)\s*\{([^}]+)\}"
            matches = re.findall(model_pattern, content, re.DOTALL)
            
            for model_name, fields_str in matches:
                table = {
                    "name": model_name,
                    "class_name": model_name,
                    "description": "",
                    "columns": [],
                    "indexes": [],
                    "primary_key": "",
                    "foreign_keys": [],
                }
                
                for line in fields_str.split("\n"):
                    line = line.strip()
                    if not line or line.startswith("//") or line.startswith("@@"):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 2:
                        col_name = parts[0]
                        col_type = parts[1]
                        constraints = " ".join(parts[2:]) if len(parts) > 2 else ""
                        
                        column = {
                            "name": col_name,
                            "type": col_type,
                            "constraints": constraints,
                            "description": "",
                            "is_primary": "@id" in constraints,
                            "is_foreign": "relation" in constraints.lower(),
                        }
                        
                        if column["is_primary"]:
                            table["primary_key"] = col_name
                        
                        table["columns"].append(column)
                
                if table["columns"]:
                    tables.append(table)
        except Exception:
            pass
        
        return tables

    def _detect_python_orm(self, context: DocGeneratorContext) -> str:
        """检测 Python ORM 类型"""
        if not context.parse_result or not context.parse_result.modules:
            return ""
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                module_lower = imp.module.lower()
                if "sqlalchemy" in module_lower:
                    return "SQLAlchemy"
                if "peewee" in module_lower:
                    return "Peewee"
                if "django.db" in module_lower:
                    return "Django ORM"
                if "pymongo" in module_lower or "mongoengine" in module_lower:
                    return "MongoDB"
                if "prisma" in module_lower:
                    return "Prisma"
        
        return ""

    def _detect_java_orm(self, context: DocGeneratorContext) -> str:
        """检测 Java ORM 类型"""
        if not context.parse_result or not context.parse_result.modules:
            return ""
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                module_lower = imp.module.lower()
                if "hibernate" in module_lower or "javax.persistence" in module_lower or "jakarta.persistence" in module_lower:
                    return "Hibernate/JPA"
                if "mybatis" in module_lower:
                    return "MyBatis"
                if "jooq" in module_lower:
                    return "jOOQ"
                if "querydsl" in module_lower:
                    return "QueryDSL"
        
        pom_path = context.project_path / "pom.xml"
        if pom_path.exists():
            try:
                content = pom_path.read_text(encoding="utf-8").lower()
                if "spring-boot-starter-data-jpa" in content:
                    return "Spring Data JPA"
                if "mybatis" in content:
                    return "MyBatis"
            except Exception:
                pass
        
        return ""

    def _detect_typescript_orm(self, context: DocGeneratorContext) -> str:
        """检测 TypeScript ORM 类型"""
        if not context.parse_result or not context.parse_result.modules:
            return ""
        
        for module in context.parse_result.modules:
            for imp in module.imports:
                module_lower = imp.module.lower()
                if "typeorm" in module_lower:
                    return "TypeORM"
                if "prisma" in module_lower:
                    return "Prisma"
                if "mongoose" in module_lower:
                    return "Mongoose"
                if "sequelize" in module_lower:
                    return "Sequelize"
                if "drizzle" in module_lower:
                    return "Drizzle ORM"
        
        prisma_path = context.project_path / "prisma" / "schema.prisma"
        if prisma_path.exists():
            return "Prisma"
        
        return ""

    def _extract_python_db_config(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取 Python 数据库配置"""
        config = {"type": "", "host": "", "port": "", "database": ""}
        
        env_files = [".env", ".env.local", ".env.development"]
        for env_file in env_files:
            env_path = context.project_path / env_file
            if env_path.exists():
                try:
                    for line in env_path.read_text().split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key_lower = key.lower()
                            if "db_type" in key_lower or "database_url" in key_lower:
                                config["type"] = self._parse_db_type_from_url(value)
                            elif "db_host" in key_lower or "database_host" in key_lower:
                                config["host"] = value.strip('"\'')
                            elif "db_port" in key_lower or "database_port" in key_lower:
                                config["port"] = value.strip('"\'')
                            elif "db_name" in key_lower or "database_name" in key_lower:
                                config["database"] = value.strip('"\'')
                except Exception:
                    pass
        
        return config

    def _extract_java_db_config(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取 Java 数据库配置"""
        config = {"type": "", "host": "", "port": "", "database": ""}
        
        app_props = context.project_path / "src" / "main" / "resources" / "application.properties"
        if app_props.exists():
            try:
                for line in app_props.read_text().split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        key_lower = key.lower()
                        if "datasource.url" in key_lower:
                            config["type"] = self._parse_db_type_from_url(value)
                        elif "datasource.host" in key_lower:
                            config["host"] = value.strip()
                        elif "datasource.port" in key_lower:
                            config["port"] = value.strip()
                        elif "datasource.database" in key_lower:
                            config["database"] = value.strip()
            except Exception:
                pass
        
        app_yml = context.project_path / "src" / "main" / "resources" / "application.yml"
        if app_yml.exists() and not config["type"]:
            try:
                import yaml
                with open(app_yml, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                
                if data and "spring" in data and "datasource" in data["spring"]:
                    ds = data["spring"]["datasource"]
                    if "url" in ds:
                        config["type"] = self._parse_db_type_from_url(ds["url"])
            except Exception:
                pass
        
        return config

    def _extract_typescript_db_config(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取 TypeScript 数据库配置"""
        config = {"type": "", "host": "", "port": "", "database": ""}
        
        env_files = [".env", ".env.local", ".env.development"]
        for env_file in env_files:
            env_path = context.project_path / env_file
            if env_path.exists():
                try:
                    for line in env_path.read_text().split("\n"):
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            key_lower = key.lower()
                            if "database_url" in key_lower or "db_url" in key_lower:
                                config["type"] = self._parse_db_type_from_url(value)
                            elif "db_host" in key_lower or "database_host" in key_lower:
                                config["host"] = value.strip('"\'')
                            elif "db_port" in key_lower or "database_port" in key_lower:
                                config["port"] = value.strip('"\'')
                            elif "db_name" in key_lower or "database_name" in key_lower:
                                config["database"] = value.strip('"\'')
                except Exception:
                    pass
        
        return config

    def _parse_db_type_from_url(self, url: str) -> str:
        """从数据库 URL 解析数据库类型"""
        url_lower = url.lower()
        if "postgresql" in url_lower or "postgres" in url_lower:
            return "PostgreSQL"
        if "mysql" in url_lower:
            return "MySQL"
        if "mongodb" in url_lower or "mongo" in url_lower:
            return "MongoDB"
        if "sqlite" in url_lower:
            return "SQLite"
        if "oracle" in url_lower:
            return "Oracle"
        if "sqlserver" in url_lower or "mssql" in url_lower:
            return "SQL Server"
        if "redis" in url_lower:
            return "Redis"
        return ""

    def _map_python_type(self, type_hint: str) -> str:
        """映射 Python 类型到数据库类型"""
        type_mapping = {
            "str": "VARCHAR",
            "string": "VARCHAR",
            "int": "INTEGER",
            "integer": "INTEGER",
            "float": "FLOAT",
            "bool": "BOOLEAN",
            "boolean": "BOOLEAN",
            "datetime": "TIMESTAMP",
            "date": "DATE",
            "time": "TIME",
            "bytes": "BLOB",
            "dict": "JSON",
            "json": "JSON",
            "uuid": "UUID",
        }
        
        type_lower = type_hint.lower().replace("optional[", "").replace("]", "")
        return type_mapping.get(type_lower, "VARCHAR")

    def _map_java_type(self, type_hint: str) -> str:
        """映射 Java 类型到数据库类型"""
        type_mapping = {
            "string": "VARCHAR",
            "integer": "INTEGER",
            "int": "INTEGER",
            "long": "BIGINT",
            "double": "DOUBLE",
            "float": "FLOAT",
            "boolean": "BOOLEAN",
            "boolean": "BOOLEAN",
            "localdatetime": "TIMESTAMP",
            "localdate": "DATE",
            "localtime": "TIME",
            "bigdecimal": "DECIMAL",
            "uuid": "UUID",
            "byte[]": "BLOB",
        }
        
        type_lower = type_hint.lower().replace("optional<", "").replace(">", "")
        return type_mapping.get(type_lower, "VARCHAR")

    def _map_typescript_type(self, type_hint: str) -> str:
        """映射 TypeScript 类型到数据库类型"""
        type_mapping = {
            "string": "VARCHAR",
            "number": "INTEGER",
            "boolean": "BOOLEAN",
            "boolean": "BOOLEAN",
            "date": "TIMESTAMP",
            "buffer": "BLOB",
            "object": "JSON",
            "any": "JSON",
        }
        
        type_lower = type_hint.lower().replace("null | ", "").replace(" | null", "")
        return type_mapping.get(type_lower, "VARCHAR")

    def _infer_python_constraints(self, prop: Any, cls: Any) -> str:
        """推断 Python 字段约束"""
        constraints = []
        
        name_lower = prop.name.lower()
        
        if hasattr(prop, 'decorators') and prop.decorators:
            for decorator in prop.decorators:
                decorator_lower = decorator.lower()
                if "primary_key" in decorator_lower or "@id" in decorator_lower:
                    constraints.append("PRIMARY KEY")
                if "unique" in decorator_lower:
                    constraints.append("UNIQUE")
                if "nullable" in decorator_lower and "false" in decorator_lower:
                    constraints.append("NOT NULL")
                if "index" in decorator_lower:
                    constraints.append("INDEX")
        
        if name_lower == "id":
            if "PRIMARY KEY" not in constraints:
                constraints.append("PRIMARY KEY")
        elif name_lower.endswith("_id"):
            if "FOREIGN KEY" not in constraints:
                constraints.append("FOREIGN KEY")
        
        if name_lower in ("created_at", "updated_at", "deleted_at"):
            constraints.append("TIMESTAMP")
        
        if "email" in name_lower:
            if "UNIQUE" not in constraints:
                constraints.append("UNIQUE")
        
        type_hint = str(getattr(prop, 'type_hint', '')).lower()
        if "optional" not in type_hint and "none" not in type_hint:
            if "NOT NULL" not in constraints and name_lower != "id":
                constraints.append("NOT NULL")
        
        return ", ".join(constraints) if constraints else ""

    def _infer_java_constraints(self, prop: Any, cls: Any) -> str:
        """推断 Java 字段约束"""
        constraints = []
        
        name_lower = prop.name.lower()
        
        if hasattr(prop, 'decorators') and prop.decorators:
            for decorator in prop.decorators:
                decorator_lower = decorator.lower()
                if "@id" in decorator_lower:
                    constraints.append("PRIMARY KEY")
                if "@column" in decorator_lower:
                    if "unique = true" in decorator_lower:
                        constraints.append("UNIQUE")
                    if "nullable = false" in decorator_lower:
                        constraints.append("NOT NULL")
                if "@onetomany" in decorator_lower or "@manytoone" in decorator_lower:
                    constraints.append("FOREIGN KEY")
        
        if name_lower == "id":
            if "PRIMARY KEY" not in constraints:
                constraints.append("PRIMARY KEY")
        elif name_lower.endswith("id"):
            if "FOREIGN KEY" not in constraints:
                constraints.append("FOREIGN KEY")
        
        if name_lower in ("createdat", "updatedat", "deletedat"):
            constraints.append("TIMESTAMP")
        
        return ", ".join(constraints) if constraints else ""

    def _infer_typescript_constraints(self, prop: Any, cls: Any) -> str:
        """推断 TypeScript 字段约束"""
        constraints = []
        
        name_lower = prop.name.lower()
        
        if hasattr(prop, 'decorators') and prop.decorators:
            for decorator in prop.decorators:
                decorator_lower = decorator.lower()
                if "@primarycolumn" in decorator_lower or "@primarygeneratedcolumn" in decorator_lower:
                    constraints.append("PRIMARY KEY")
                if "@column" in decorator_lower:
                    if "unique: true" in decorator_lower:
                        constraints.append("UNIQUE")
                    if "nullable: false" in decorator_lower:
                        constraints.append("NOT NULL")
                if "@manytone" in decorator_lower or "@onetomany" in decorator_lower:
                    constraints.append("FOREIGN KEY")
        
        if name_lower == "id" or name_lower == "_id":
            if "PRIMARY KEY" not in constraints:
                constraints.append("PRIMARY KEY")
        elif name_lower.endswith("id"):
            if "FOREIGN KEY" not in constraints:
                constraints.append("FOREIGN KEY")
        
        type_hint = str(getattr(prop, 'type_hint', '')).lower()
        if "null" not in type_hint:
            if "NOT NULL" not in constraints:
                constraints.append("NOT NULL")
        
        return ", ".join(constraints) if constraints else ""

    def _extract_from_sql_files(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """从 SQL 文件提取表结构"""
        tables = []
        seen_tables = set()

        for sql_file in context.project_path.rglob("*.sql"):
            path_str = str(sql_file)
            if "node_modules" in path_str or "venv" in path_str or "target" in path_str:
                continue
            
            if not self._is_sql_file(sql_file):
                continue
                
            try:
                content = sql_file.read_text(encoding="utf-8")
                
                if not self._looks_like_sql_content(content):
                    continue
                
                extracted_tables = self._parse_sql_create_tables(content)
                
                for table in extracted_tables:
                    if not self._is_valid_table_name(table["name"]):
                        continue
                    if table["name"].lower() not in seen_tables:
                        seen_tables.add(table["name"].lower())
                        tables.append(table)
            except Exception:
                continue

        return tables

    def _is_sql_file(self, file_path: Path) -> bool:
        """检查文件是否为真正的 SQL 文件"""
        if not file_path.exists():
            return False
        
        if file_path.stat().st_size == 0:
            return False
        
        if file_path.stat().st_size > 10 * 1024 * 1024:
            return False
        
        sql_indicators = ['sql', 'ddl', 'dml', 'database', 'table', 'schema']
        path_lower = str(file_path).lower()
        
        if any(indicator in path_lower for indicator in sql_indicators):
            return True
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_chunk = f.read(500).lower()
                sql_keywords = ['create table', 'alter table', 'drop table', 'insert into', 'select from']
                if any(keyword in first_chunk for keyword in sql_keywords):
                    return True
        except Exception:
            pass
        
        return False

    def _looks_like_sql_content(self, content: str) -> bool:
        """检查内容是否像 SQL"""
        if not content:
            return False
        
        content_lower = content.lower()
        
        required_keywords = ['create table']
        keyword_count = sum(1 for kw in required_keywords if kw in content_lower)
        
        if keyword_count == 0:
            return False
        
        non_sql_patterns = [
            r'public\s+class',
            r'public\s+interface',
            r'package\s+com\.',
            r'import\s+java\.',
            r'import\s+org\.springframework',
            r'@RestController',
            r'@Controller',
            r'@Service',
            r'@Component',
            r'private\s+\w+\s+\w+;',
            r'public\s+\w+\s+\w+\(',
        ]
        
        non_sql_count = 0
        for pattern in non_sql_patterns:
            if re.search(pattern, content):
                non_sql_count += 1
        
        if non_sql_count > 3:
            return False
        
        return True

    def _parse_sql_create_tables(self, content: str) -> list[dict[str, Any]]:
        """解析 SQL 内容中的 CREATE TABLE 语句"""
        tables = []

        # 支持多种表名格式：普通标识符、反引号、方括号、双引号
        create_pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:[`\"\[]?([^`\"\]\s]+)[`\"\]]?)\s*\("
        matches = list(re.finditer(create_pattern, content, re.IGNORECASE))

        for i, match in enumerate(matches):
            table_name = match.group(1).strip()

            # 验证表名是否有效
            if not self._is_valid_table_name(table_name):
                continue

            start_pos = match.end()

            end_pos = self._find_closing_parenthesis(content, start_pos - 1)
            if end_pos == -1:
                continue

            columns_str = content[start_pos:end_pos]

            table = {
                "name": table_name,
                "class_name": table_name,
                "description": "",
                "columns": [],
                "indexes": [],
                "primary_key": "",
                "foreign_keys": [],
            }

            self._parse_column_definitions(columns_str, table)

            if table["columns"]:
                tables.append(table)

        return tables

    def _find_closing_parenthesis(self, content: str, start: int) -> int:
        """找到匹配的闭合括号位置"""
        depth = 0
        i = start
        
        while i < len(content):
            char = content[i]
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        
        return -1

    def _parse_column_definitions(self, columns_str: str, table: dict) -> None:
        """解析列定义"""
        columns_str = columns_str.strip()
        
        definitions = self._split_column_definitions(columns_str)
        
        for col_def in definitions:
            col_def = col_def.strip()
            if not col_def:
                continue
            
            col_def_upper = col_def.upper()
            
            if col_def_upper.startswith("PRIMARY KEY"):
                self._parse_primary_key_constraint(col_def, table)
                continue
            
            if col_def_upper.startswith("FOREIGN KEY"):
                self._parse_foreign_key_constraint(col_def, table)
                continue
            
            if col_def_upper.startswith("UNIQUE"):
                continue
            
            if col_def_upper.startswith("INDEX") or col_def_upper.startswith("KEY "):
                continue
            
            if col_def_upper.startswith("CHECK"):
                continue
            
            if col_def_upper.startswith("CONSTRAINT"):
                continue
            
            column = self._parse_single_column(col_def)
            if column:
                if column.get("is_primary"):
                    table["primary_key"] = column["name"]
                if column.get("is_foreign"):
                    table["foreign_keys"].append(column["name"])
                table["columns"].append(column)

    def _split_column_definitions(self, columns_str: str) -> list[str]:
        """智能分割列定义，处理嵌套括号"""
        definitions = []
        current = []
        depth = 0
        in_string = False
        string_char = None
        
        for char in columns_str:
            if char in ('"', "'") and (not in_string or char == string_char):
                if in_string and current and current[-1] != '\\':
                    in_string = False
                    string_char = None
                elif not in_string:
                    in_string = True
                    string_char = char
                current.append(char)
            elif in_string:
                current.append(char)
            elif char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                definitions.append(''.join(current))
                current = []
            else:
                current.append(char)
        
        if current:
            definitions.append(''.join(current))
        
        return definitions

    def _parse_single_column(self, col_def: str) -> Optional[dict[str, Any]]:
        """解析单个列定义"""
        col_def = col_def.strip()
        if not col_def:
            return None

        tokens = self._tokenize_column_def(col_def)
        if not tokens:
            return None

        col_name = tokens[0].strip("`\"'")
        if not col_name or col_name.upper() in ("PRIMARY", "FOREIGN", "UNIQUE", "INDEX", "KEY", "CHECK", "CONSTRAINT"):
            return None

        col_type = tokens[1] if len(tokens) > 1 else "UNKNOWN"
        col_type = self._extract_complete_type(col_type, col_def)

        constraints = []
        is_primary = False
        is_foreign = False
        description = ""

        col_def_upper = col_def.upper()

        # 解析约束（按优先级顺序）
        if "PRIMARY KEY" in col_def_upper:
            constraints.append("PRIMARY KEY")
            is_primary = True

        if "NOT NULL" in col_def_upper:
            constraints.append("NOT NULL")

        if "UNIQUE" in col_def_upper and "PRIMARY KEY" not in col_def_upper:
            constraints.append("UNIQUE")

        if "AUTO_INCREMENT" in col_def_upper or "AUTOINCREMENT" in col_def_upper:
            constraints.append("AUTO_INCREMENT")
        elif "IDENTITY" in col_def_upper:
            constraints.append("IDENTITY")

        # 解析 DEFAULT 值
        default_match = re.search(r"DEFAULT\s+([^\s,]+(?:\s+[^,\s]+)*)", col_def, re.IGNORECASE)
        if default_match:
            default_value = default_match.group(1).strip()
            # 清理多余的空格和截断的文本
            default_value = re.sub(r'\s+', ' ', default_value)
            if default_value and not default_value.upper().startswith('NOT'):
                constraints.append(f"DEFAULT {default_value}")

        if "REFERENCES" in col_def_upper:
            is_foreign = True
            constraints.append("FOREIGN KEY")
            ref_match = re.search(r"REFERENCES\s+(\w+)\s*\((\w+)\)", col_def, re.IGNORECASE)
            if ref_match:
                description = f"引用 {ref_match.group(1)}.{ref_match.group(2)}"

        if col_name.lower().endswith("_id") and col_name.lower() != "id":
            is_foreign = True
            if "FOREIGN KEY" not in constraints:
                constraints.append("FOREIGN KEY")

        # 去重并格式化约束
        unique_constraints = []
        seen = set()
        for c in constraints:
            c_upper = c.upper()
            if c_upper not in seen:
                seen.add(c_upper)
                unique_constraints.append(c)

        return {
            "name": col_name,
            "type": col_type,
            "constraints": " ".join(unique_constraints),
            "description": description,
            "is_primary": is_primary,
            "is_foreign": is_foreign,
            "is_nullable": "NOT NULL" not in col_def_upper,
        }

    def _tokenize_column_def(self, col_def: str) -> list[str]:
        """将列定义分割为 tokens"""
        tokens = []
        current = []
        depth = 0
        in_string = False
        string_char = None
        
        for char in col_def:
            if char in ('"', "'") and (not in_string or char == string_char):
                if in_string and current and current[-1] != '\\':
                    in_string = False
                    string_char = None
                elif not in_string:
                    in_string = True
                    string_char = char
                current.append(char)
            elif in_string:
                current.append(char)
            elif char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char.isspace() and depth == 0:
                if current:
                    tokens.append(''.join(current))
                    current = []
            else:
                current.append(char)
        
        if current:
            tokens.append(''.join(current))
        
        return tokens

    def _extract_complete_type(self, type_token: str, full_def: str) -> str:
        """提取完整的数据类型"""
        type_token = type_token.strip("`\"'")
        
        if '(' in type_token:
            return type_token
        
        paren_pos = full_def.find('(')
        if paren_pos == -1:
            return type_token
        
        end_paren = self._find_closing_parenthesis(full_def, paren_pos)
        if end_paren == -1:
            return type_token
        
        type_with_params = full_def[:end_paren + 1]
        type_start = type_with_params.lower().find(type_token.lower())
        if type_start == -1:
            return type_token
        
        return type_token + full_def[paren_pos:end_paren + 1]

    def _parse_primary_key_constraint(self, col_def: str, table: dict) -> None:
        """解析 PRIMARY KEY 约束"""
        match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", col_def, re.IGNORECASE)
        if match:
            pk_columns = [c.strip().strip("`\"'") for c in match.group(1).split(",")]
            for pk_col in pk_columns:
                for col in table["columns"]:
                    if col["name"].lower() == pk_col.lower():
                        col["is_primary"] = True
                        col["constraints"] = (col["constraints"] + " PRIMARY KEY").strip()
                        if not table["primary_key"]:
                            table["primary_key"] = col["name"]
                        break

    def _parse_foreign_key_constraint(self, col_def: str, table: dict) -> None:
        """解析 FOREIGN KEY 约束"""
        match = re.search(
            r"FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)",
            col_def, re.IGNORECASE
        )
        if match:
            fk_columns = [c.strip().strip("`\"'") for c in match.group(1).split(",")]
            ref_table = match.group(2)
            ref_columns = [c.strip().strip("`\"'") for c in match.group(3).split(",")]
            
            for fk_col in fk_columns:
                for col in table["columns"]:
                    if col["name"].lower() == fk_col.lower():
                        col["is_foreign"] = True
                        col["constraints"] = (col["constraints"] + " FOREIGN KEY").strip()
                        col["description"] = f"引用 {ref_table}.{ref_columns[0] if ref_columns else ''}"
                        table["foreign_keys"].append(col["name"])
                        break

    def _generate_er_diagram(self, tables: list[dict], relationships: list[dict]) -> str:
        """生成 E-R 图"""
        lines = ["erDiagram"]

        # 如果没有表，返回空图表
        if not tables:
            lines.append("    %% No tables detected")
            return "\n".join(lines)

        max_tables = 30
        max_columns = 12

        # 清理表名，确保是有效的Mermaid标识符
        def sanitize_table_name(name: str) -> str:
            """清理表名，移除特殊字符"""
            if not name:
                return "unknown"
            # 移除或替换特殊字符
            sanitized = re.sub(r'[^\w]', '_', str(name))
            # 确保不以数字开头
            if sanitized and sanitized[0].isdigit():
                sanitized = 't_' + sanitized
            return sanitized or "unknown"

        for table in tables[:max_tables]:
            table_name = table.get("name", "unknown")
            if not table_name or not isinstance(table_name, str):
                continue

            safe_table_name = sanitize_table_name(table_name)
            lines.append(f"    {safe_table_name} {{")

            columns = table.get("columns", [])
            if not columns:
                lines.append("        %% No columns detected")
            else:
                pk_columns = [c for c in columns if c.get("is_primary")]
                fk_columns = [c for c in columns if c.get("is_foreign") and not c.get("is_primary")]
                other_columns = [c for c in columns if not c.get("is_primary") and not c.get("is_foreign")]

                display_columns = pk_columns + fk_columns + other_columns
                display_columns = display_columns[:max_columns]

                for col in display_columns:
                    if not isinstance(col, dict):
                        continue
                    col_name = col.get("name", "unknown")
                    col_type = col.get("type", "unknown")
                    if not isinstance(col_type, str):
                        col_type = str(col_type)
                    # 清理类型字符串
                    col_type = col_type.split("[")[0]
                    if "(" in col_type:
                        paren_idx = col_type.find(")")
                        if paren_idx != -1:
                            col_type = col_type[:paren_idx+1]
                        else:
                            col_type = col_type.split("(")[0]
                    col_type = col_type[:20]
                    # 清理列名
                    safe_col_name = re.sub(r'[^\w]', '_', str(col_name)) if col_name else "unknown"
                    lines.append(f"        {col_type} {safe_col_name}")
            lines.append("    }")

        # 添加关系
        max_relationships = 40
        if relationships:
            for rel in relationships[:max_relationships]:
                primary_table = rel.get("primary_table", "")
                foreign_table = rel.get("foreign_table", "")
                foreign_key = rel.get("foreign_key", "")
                relation_type = rel.get("relation_type", "1:N")

                if not primary_table or not foreign_table:
                    continue

                # 清理表名
                safe_primary = sanitize_table_name(primary_table)
                safe_foreign = sanitize_table_name(foreign_table)

                if relation_type == "1:1":
                    rel_symbol = "||--||"
                elif relation_type == "N:M":
                    rel_symbol = "}o--o{"
                elif relation_type == "N:1":
                    rel_symbol = "}o--||"
                else:
                    rel_symbol = "||--o{"

                safe_fk = re.sub(r'[^\w]', '_', str(foreign_key)) if foreign_key else "fk"
                lines.append(f"    {safe_primary} {rel_symbol} {safe_foreign} : {safe_fk}")

        return "\n".join(lines)

    def _extract_relationships(self, context: DocGeneratorContext, tables: list[dict], project_language: str) -> list[dict[str, str]]:
        """提取表关系"""
        relationships = []
        seen_relationships = set()
        
        table_names = {t["name"].lower() for t in tables}
        table_name_map = {t["name"].lower(): t["name"] for t in tables}

        for table in tables:
            table_name = table["name"]
            
            for col in table.get("columns", []):
                if col.get("is_foreign"):
                    col_name = col["name"]
                    col_name_lower = col_name.lower()
                    
                    foreign_table = None
                    
                    if col_name_lower.endswith("_id") and col_name_lower != "id":
                        potential_table = col_name_lower[:-3]
                        if potential_table in table_names:
                            foreign_table = table_name_map[potential_table]
                    
                    if not foreign_table:
                        desc = col.get("description", "")
                        ref_match = re.search(r"引用\s+(\w+)\.?", desc)
                        if ref_match:
                            ref_name = ref_match.group(1).lower()
                            if ref_name in table_names:
                                foreign_table = table_name_map[ref_name]
                    
                    if foreign_table and foreign_table != table_name:
                        rel_key = f"{foreign_table.lower()}->{table_name.lower()}:{col_name_lower}"
                        if rel_key not in seen_relationships:
                            seen_relationships.add(rel_key)
                            relationships.append({
                                "primary_table": foreign_table,
                                "relation_type": "1:N",
                                "foreign_table": table_name,
                                "foreign_key": col_name,
                            })

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    cls_name = cls.name
                    
                    for prop in cls.properties:
                        name_lower = prop.name.lower()
                        
                        if name_lower.endswith("_id") and name_lower != "id":
                            potential_table = name_lower[:-3]
                            
                            if potential_table in table_names:
                                foreign_table = table_name_map[potential_table]
                                rel_key = f"{potential_table}->{cls_name.lower()}:{name_lower}"
                                
                                if rel_key not in seen_relationships:
                                    seen_relationships.add(rel_key)
                                    relationships.append({
                                        "primary_table": foreign_table,
                                        "relation_type": "1:N",
                                        "foreign_table": cls_name,
                                        "foreign_key": prop.name,
                                    })

        return relationships[:50]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        db_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:

        enhanced = {}
        
        summary = db_data.get("summary", {})

        if self.language == Language.ZH:
            prompt = f"""基于以下数据库设计，提供优化建议：

项目: {context.project_name}
表数量: {summary.get('table_count', 0)}
关系数量: {summary.get('relationship_count', 0)}
ORM类型: {db_data.get('orm_type', '未知')}

请以 JSON 格式返回：
{{
    "database_design_analysis": "数据库设计分析",
    "indexing_suggestions": ["索引建议1", "索引建议2"],
    "normalization_issues": ["规范化问题1", "规范化问题2"],
    "performance_tips": ["性能优化建议1", "性能优化建议2"]
}}

请务必使用中文回答。"""
        else:
            prompt = f"""Based on the following database design, provide optimization recommendations:

Project: {context.project_name}
Tables: {summary.get('table_count', 0)}
Relationships: {summary.get('relationship_count', 0)}
ORM Type: {db_data.get('orm_type', 'Unknown')}

Please return in JSON format:
{{
    "database_design_analysis": "Database design analysis",
    "indexing_suggestions": ["indexing suggestion1", "indexing suggestion2"],
    "normalization_issues": ["normalization issue1", "normalization issue2"],
    "performance_tips": ["performance tip1", "performance tip2"]
}}

Please respond in English."""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["analysis"] = result.get("database_design_analysis", "")
                enhanced["indexing_suggestions"] = result.get("indexing_suggestions", [])
                enhanced["performance_tips"] = result.get("performance_tips", [])
        except Exception:
            pass

        return enhanced

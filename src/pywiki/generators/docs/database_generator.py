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
                message="数据库文档生成成功",
                metadata={"db_data": db_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
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
                        tables.append(table)

        return tables[:30]

    def _extract_java_tables(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Java 数据库模型"""
        tables = []

        if not context.parse_result or not context.parse_result.modules:
            return tables

        entity_keywords = ["entity", "model", "domain", "pojo", "dto"]

        for module in context.parse_result.modules:
            module_lower = module.name.lower()
            
            for cls in module.classes:
                is_entity = False
                table_name = cls.name
                orm_type = "JPA"
                
                cls_docstring = cls.docstring or ""
                
                if "JPA Entity" in cls_docstring or "MyBatis Plus Entity" in cls_docstring:
                    is_entity = True
                    
                    if "MyBatis Plus Entity" in cls_docstring:
                        orm_type = "MyBatis Plus"
                    
                    table_match = re.search(r'Table:\s*([^\s|]+)', cls_docstring)
                    if table_match:
                        table_name = table_match.group(1)
                
                if hasattr(cls, 'decorators') and cls.decorators:
                    for decorator in cls.decorators:
                        decorator_lower = decorator.lower()
                        if "@entity" in decorator_lower or "@table" in decorator_lower:
                            is_entity = True
                            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', decorator)
                            if name_match:
                                table_name = name_match.group(1)
                        if "@tablename" in decorator_lower:
                            is_entity = True
                            orm_type = "MyBatis Plus"
                            name_match = re.search(r'(?:value|name)\s*=\s*["\']([^"\']+)["\']', decorator)
                            if name_match:
                                table_name = name_match.group(1)
                
                for base in cls.bases:
                    if any(entity_base in base for entity_base in ["Entity", "BaseEntity", "AbstractEntity"]):
                        is_entity = True
                
                if any(kw in module_lower for kw in entity_keywords) and not is_entity:
                    is_entity = True
                
                if is_entity:
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

                    for prop in cls.class_variables:
                        column = self._extract_java_column_from_property(prop, cls_docstring)
                        if column:
                            if column.get("is_primary"):
                                table["primary_key"] = column["name"]
                            if column.get("is_foreign"):
                                table["foreign_keys"].append(column["name"])
                            table["columns"].append(column)

                    for method in cls.methods:
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

    def _extract_java_column_from_property(self, prop: Any, cls_docstring: str) -> Optional[dict[str, Any]]:
        """从属性提取Java列信息"""
        name_lower = prop.name.lower()
        
        column = {
            "name": prop.name,
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
                    
                    name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', decorator)
                    if name_match:
                        column["name"] = name_match.group(1)
                
                if "@tablefield" in decorator_lower:
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
        
        if name_lower == "id":
            if "PRIMARY KEY" not in constraints:
                constraints.append("PRIMARY KEY")
                column["is_primary"] = True
        elif name_lower.endswith("id") and not name_lower.startswith("is"):
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

        for sql_file in context.project_path.rglob("*.sql"):
            if "node_modules" in str(sql_file) or "venv" in str(sql_file):
                continue
                
            try:
                content = sql_file.read_text(encoding="utf-8")
                
                create_pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?(\w+)[`\"']?\s*\(([^)]+)\)"
                matches = re.findall(create_pattern, content, re.IGNORECASE | re.DOTALL)

                for table_name, columns_str in matches:
                    table = {
                        "name": table_name,
                        "class_name": table_name,
                        "description": "",
                        "columns": [],
                        "indexes": [],
                        "primary_key": "",
                        "foreign_keys": [],
                    }

                    columns = columns_str.split(",")
                    for col_def in columns:
                        col_def = col_def.strip()
                        if not col_def:
                            continue

                        parts = col_def.split()
                        if parts:
                            col_name = parts[0].strip("`\"'")
                            col_type = parts[1] if len(parts) > 1 else "UNKNOWN"
                            
                            column = {
                                "name": col_name,
                                "type": col_type,
                                "constraints": " ".join(parts[2:]) if len(parts) > 2 else "",
                                "description": "",
                                "is_primary": "PRIMARY KEY" in col_def.upper(),
                                "is_foreign": "FOREIGN KEY" in col_def.upper() or "REFERENCES" in col_def.upper(),
                            }
                            
                            if column["is_primary"]:
                                table["primary_key"] = col_name
                            
                            table["columns"].append(column)

                    if table["columns"]:
                        tables.append(table)
            except Exception:
                continue

        return tables

    def _generate_er_diagram(self, tables: list[dict], relationships: list[dict]) -> str:
        """生成 E-R 图"""
        lines = ["erDiagram"]

        for table in tables[:15]:
            table_name = table["name"]
            lines.append(f"    {table_name} {{")
            for col in table["columns"][:6]:
                col_type = col["type"].split("[")[0].split("(")[0][:15]
                lines.append(f"        {col_type} {col['name']}")
            lines.append("    }")

        for rel in relationships[:15]:
            lines.append(f"    {rel['primary_table']} ||--o{{ {rel['foreign_table']} : {rel['foreign_key']}")

        return "\n".join(lines)

    def _extract_relationships(self, context: DocGeneratorContext, tables: list[dict], project_language: str) -> list[dict[str, str]]:
        """提取表关系"""
        relationships = []

        for table in tables:
            for col in table.get("columns", []):
                if col.get("is_foreign") or (col["name"].lower().endswith("_id") and col["name"].lower() != "id"):
                    foreign_table = col["name"][:-3] if col["name"].lower().endswith("_id") else col["name"]
                    foreign_table = foreign_table.replace("_id", "").replace("Id", "")
                    
                    relationships.append({
                        "primary_table": foreign_table.capitalize(),
                        "relation_type": "1:N",
                        "foreign_table": table["name"],
                        "foreign_key": col["name"],
                    })

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    for prop in cls.properties:
                        name_lower = prop.name.lower()
                        
                        if name_lower.endswith("_id") and name_lower != "id":
                            foreign_table = name_lower[:-3].capitalize()
                            
                            if not any(r["foreign_key"] == prop.name for r in relationships):
                                relationships.append({
                                    "primary_table": foreign_table,
                                    "relation_type": "1:N",
                                    "foreign_table": cls.name,
                                    "foreign_key": prop.name,
                                })

        return relationships[:30]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        db_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:

        enhanced = {}
        
        summary = db_data.get("summary", {})

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
"""

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

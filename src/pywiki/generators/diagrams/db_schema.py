"""
数据库 Schema 表生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class DBSchemaGenerator(BaseDiagramGenerator):
    """
    生成数据库 Schema 表图
    
    示例输出:
    erDiagram
        users {
            bigint id PK "主键"
            varchar username UK "用户名"
            varchar email UK "邮箱"
            varchar password_hash "密码哈希"
            datetime created_at "创建时间"
            datetime updated_at "更新时间"
        }
        orders {
            bigint id PK "主键"
            bigint user_id FK "用户ID"
            decimal total_amount "总金额"
            varchar status "状态"
            datetime created_at "创建时间"
        }
        users ||--o{ orders : "拥有"
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        tables = data.get("tables", [])
        relationships = data.get("relationships", [])

        lines = ["erDiagram"]

        if title:
            lines.append(f"    %% {title}")

        for table in tables:
            table_name = table.get("name", "")
            columns = table.get("columns", [])
            comment = table.get("comment", "")

            if comment:
                lines.append(f"    %% {table_name}: {comment}")

            if columns:
                lines.append(f"    {table_name} {{")
                for col in columns:
                    col_name = col.get("name", "")
                    col_type = col.get("type", "varchar")
                    constraints = col.get("constraints", [])
                    col_comment = col.get("comment", "")

                    constraint_str = " ".join(constraints)
                    comment_str = f'"{col_comment}"' if col_comment else ""

                    parts = [col_type, col_name]
                    if constraint_str:
                        parts.append(constraint_str)
                    if comment_str:
                        parts.append(comment_str)

                    lines.append(f"        {' '.join(parts)}")
                lines.append("    }")

        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "||--o{")
            label = rel.get("label", "")

            if label:
                lines.append(f"    {source} {rel_type} {target} : {label}")
            else:
                lines.append(f"    {source} {rel_type} {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_ddl(self, ddl_statements: list[str]) -> str:
        """从 DDL 语句生成 Schema 图"""
        tables = []
        relationships = []

        for ddl in ddl_statements:
            parsed = self._parse_ddl(ddl)
            if parsed:
                if "table" in parsed:
                    tables.append(parsed["table"])
                if "relationships" in parsed:
                    relationships.extend(parsed["relationships"])

        return self.generate({"tables": tables, "relationships": relationships})

    def _parse_ddl(self, ddl: str) -> Optional[dict]:
        import re

        result = {}

        create_pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?(\w+)[`\"']?\s*\((.*?)\)"
        match = re.search(create_pattern, ddl, re.IGNORECASE | re.DOTALL)

        if not match:
            return None

        table_name = match.group(1)
        columns_str = match.group(2)

        table = {
            "name": table_name,
            "columns": [],
            "comment": ""
        }

        comment_pattern = r"COMMENT\s*=?\s*['\"](.+?)['\"]"
        comment_match = re.search(comment_pattern, ddl, re.IGNORECASE)
        if comment_match:
            table["comment"] = comment_match.group(1)

        columns = []
        relationships = []

        for line in columns_str.split(","):
            line = line.strip()

            if line.upper().startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "INDEX", "KEY", "CONSTRAINT")):
                fk_pattern = r"FOREIGN\s+KEY\s*\((\w+)\)\s*REFERENCES\s+[`\"']?(\w+)[`\"']?\s*\((\w+)\)"
                fk_match = re.search(fk_pattern, line, re.IGNORECASE)
                if fk_match:
                    relationships.append({
                        "source": table_name,
                        "target": fk_match.group(2),
                        "type": "many_to_one",
                        "label": fk_match.group(1)
                    })
                continue

            col_pattern = r"[`\"']?(\w+)[`\"']?\s+(\w+(?:\([^)]+\))?)"
            col_match = re.match(col_pattern, line, re.IGNORECASE)
            if col_match:
                col_name = col_match.group(1)
                col_type = col_match.group(2).upper()

                constraints = []
                if "PRIMARY KEY" in line.upper() or "PK" in line.upper():
                    constraints.append("PK")
                if "FOREIGN KEY" in line.upper() or "FK" in line.upper():
                    constraints.append("FK")
                if "UNIQUE" in line.upper() or "UK" in line.upper():
                    constraints.append("UK")
                if "NOT NULL" in line.upper():
                    constraints.append("NOT NULL")
                if "AUTO_INCREMENT" in line.upper() or "AUTOINCREMENT" in line.upper():
                    constraints.append("AUTO")

                col_comment = ""
                col_comment_match = re.search(r"COMMENT\s*['\"](.+?)['\"]", line, re.IGNORECASE)
                if col_comment_match:
                    col_comment = col_comment_match.group(1)

                table["columns"].append({
                    "name": col_name,
                    "type": self._normalize_type(col_type),
                    "constraints": constraints,
                    "comment": col_comment
                })

        result["table"] = table
        result["relationships"] = relationships

        return result

    def _normalize_type(self, db_type: str) -> str:
        type_upper = db_type.upper()

        if type_upper.startswith("INT") or type_upper.startswith("BIGINT"):
            return "bigint"
        elif type_upper.startswith("SMALLINT"):
            return "smallint"
        elif type_upper.startswith("TINYINT"):
            return "tinyint"
        elif type_upper.startswith("VARCHAR") or type_upper.startswith("CHAR"):
            return "varchar"
        elif type_upper.startswith("TEXT"):
            return "text"
        elif type_upper.startswith("BOOL"):
            return "bool"
        elif type_upper.startswith("DATE"):
            return "date"
        elif type_upper.startswith("DATETIME") or type_upper.startswith("TIMESTAMP"):
            return "datetime"
        elif type_upper.startswith("DECIMAL") or type_upper.startswith("NUMERIC"):
            return "decimal"
        elif type_upper.startswith("FLOAT") or type_upper.startswith("DOUBLE"):
            return "float"
        elif type_upper.startswith("JSON"):
            return "json"
        elif type_upper.startswith("BLOB"):
            return "blob"
        elif type_upper.startswith("UUID"):
            return "uuid"
        else:
            return db_type.lower()

    def generate_from_sqlalchemy_models(self, models: list[dict]) -> str:
        """从 SQLAlchemy 模型信息生成 Schema 图"""
        tables = []
        relationships = []

        for model in models:
            table = {
                "name": model.get("tablename", model.get("name", "")),
                "columns": [],
                "comment": model.get("docstring", "")
            }

            for col in model.get("columns", []):
                table["columns"].append({
                    "name": col.get("name", ""),
                    "type": self._normalize_type(col.get("type", "")),
                    "constraints": self._get_constraints(col),
                    "comment": col.get("docstring", "")
                })

            tables.append(table)

            for rel in model.get("relationships", []):
                relationships.append({
                    "source": table["name"],
                    "target": rel.get("target", ""),
                    "type": self._get_rel_type(rel.get("type", "")),
                    "label": rel.get("name", "")
                })

        return self.generate({"tables": tables, "relationships": relationships})

    def _get_constraints(self, col: dict) -> list[str]:
        constraints = []
        if col.get("primary_key"):
            constraints.append("PK")
        if col.get("foreign_key"):
            constraints.append("FK")
        if col.get("unique"):
            constraints.append("UK")
        if not col.get("nullable", True):
            constraints.append("NOT NULL")
        if col.get("autoincrement"):
            constraints.append("AUTO")
        return constraints

    def _get_rel_type(self, rel_type: str) -> str:
        types = {
            "one_to_one": "||--||",
            "one_to_many": "||--o{",
            "many_to_one": "}o--||",
            "many_to_many": "}o--o{",
        }
        return types.get(rel_type, "||--o{")

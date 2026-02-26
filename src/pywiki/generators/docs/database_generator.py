"""
数据库文档生成器
"""

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
            db_data = self._extract_db_data(context)
            
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

    def _extract_db_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取数据库数据"""
        db_data = {
            "er_diagram": "",
            "tables": [],
            "relationships": [],
            "summary": {},
        }

        db_data["tables"] = self._extract_tables(context)
        db_data["er_diagram"] = self._generate_er_diagram(context)
        db_data["relationships"] = self._extract_relationships(context)

        return db_data

    def _extract_tables(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取表结构"""
        tables = []

        model_keywords = ["model", "entity", "schema", "table", "orm"]

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                module_lower = module.name.lower()
                
                if any(kw in module_lower for kw in model_keywords):
                    for cls in module.classes:
                        table = {
                            "name": cls.name,
                            "description": cls.docstring.split("\n")[0] if cls.docstring else "",
                            "columns": [],
                            "indexes": [],
                        }

                        for prop in cls.properties:
                            column = {
                                "name": prop.name,
                                "type": prop.type_hint or "Any",
                                "constraints": self._infer_constraints(prop),
                                "description": "",
                            }
                            table["columns"].append(column)

                        if table["columns"]:
                            tables.append(table)

        if not tables:
            tables = self._extract_from_sql_files(context)

        return tables[:20]

    def _infer_constraints(self, prop: Any) -> str:
        """推断字段约束"""
        constraints = []
        
        name_lower = prop.name.lower()
        if "id" == name_lower or name_lower.endswith("_id"):
            constraints.append("PRIMARY KEY" if name_lower == "id" else "FOREIGN KEY")
        
        if name_lower in ("created_at", "updated_at", "deleted_at"):
            constraints.append("TIMESTAMP")
        
        if "email" in name_lower:
            constraints.append("UNIQUE")
        
        if "required" in str(prop.type_hint).lower() or prop.name.isupper():
            constraints.append("NOT NULL")

        return ", ".join(constraints) if constraints else ""

    def _extract_from_sql_files(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """从 SQL 文件提取表结构"""
        tables = []

        for sql_file in context.project_path.rglob("*.sql"):
            try:
                content = sql_file.read_text(encoding="utf-8")
                
                import re
                create_pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"']?(\w+)[`\"']?\s*\(([^)]+)\)"
                matches = re.findall(create_pattern, content, re.IGNORECASE | re.DOTALL)

                for table_name, columns_str in matches:
                    table = {
                        "name": table_name,
                        "description": "",
                        "columns": [],
                        "indexes": [],
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
                            
                            table["columns"].append({
                                "name": col_name,
                                "type": col_type,
                                "constraints": " ".join(parts[2:]) if len(parts) > 2 else "",
                                "description": "",
                            })

                    if table["columns"]:
                        tables.append(table)
            except Exception:
                continue

        return tables

    def _generate_er_diagram(self, context: DocGeneratorContext) -> str:
        """生成 E-R 图"""
        lines = ["erDiagram"]

        tables = self._extract_tables(context)

        for table in tables[:10]:
            table_name = table["name"]
            lines.append(f"    {table_name} {{")
            for col in table["columns"][:5]:
                col_type = col["type"].split("[")[0].split("(")[0][:20]
                lines.append(f"        {col_type} {col['name']}")
            lines.append("    }")

        relationships = self._extract_relationships(context)
        for rel in relationships[:10]:
            lines.append(f"    {rel['primary_table']} ||--o{{ {rel['foreign_table']} : {rel['foreign_key']}")

        return "\n".join(lines)

    def _extract_relationships(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取表关系"""
        relationships = []

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    for prop in cls.properties:
                        name_lower = prop.name.lower()
                        
                        if name_lower.endswith("_id") and name_lower != "id":
                            foreign_table = name_lower[:-3]
                            relationships.append({
                                "primary_table": foreign_table.capitalize(),
                                "relation_type": "1:N",
                                "foreign_table": cls.name,
                                "foreign_key": prop.name,
                            })

        return relationships[:20]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        db_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强数据库文档"""
        import json

        enhanced = {}

        prompt = f"""基于以下数据库设计，提供优化建议：

项目: {context.project_name}
表数量: {len(db_data.get('tables', []))}
关系数量: {len(db_data.get('relationships', []))}

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

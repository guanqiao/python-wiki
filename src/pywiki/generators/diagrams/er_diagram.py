"""
ER 图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class ERDiagramGenerator(BaseDiagramGenerator):
    """
    生成实体关系图 (ER Diagram)
    
    示例输出:
    erDiagram
        USER ||--o{ ORDER : places
        USER {
            int id PK
            string name
            string email
        }
        ORDER ||--|{ ORDER_ITEM : contains
        ORDER {
            int id PK
            datetime created_at
            string status
        }
        ORDER_ITEM }|--|| PRODUCT : includes
        PRODUCT {
            int id PK
            string name
            decimal price
        }
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        entities = data.get("entities", [])
        relationships = data.get("relationships", [])

        lines = ["erDiagram"]

        if title:
            lines.append(f"    %% {title}")

        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "||--||")
            label = rel.get("label", "")

            if label:
                lines.append(f"    {source} {rel_type} {target} : {label}")
            else:
                lines.append(f"    {source} {rel_type} {target}")

        for entity in entities:
            entity_name = entity.get("name", "")
            attributes = entity.get("attributes", [])

            if attributes:
                lines.append(f"    {entity_name} {{")
                for attr in attributes:
                    attr_name = attr.get("name", "")
                    attr_type = attr.get("type", "")
                    constraints = attr.get("constraints", [])

                    constraint_str = " ".join(constraints)
                    if constraint_str:
                        lines.append(f"        {attr_type} {attr_name} {constraint_str}")
                    else:
                        lines.append(f"        {attr_type} {attr_name}")
                lines.append("    }")

        return self.wrap_mermaid("\n".join(lines))

    def _get_relationship_type(self, rel_type: str) -> str:
        types = {
            "one_to_one": "||--||",
            "one_to_many": "||--o{",
            "many_to_one": "}o--||",
            "many_to_many": "}o--o{",
            "one_to_many_required": "||--|{",
            "many_to_one_required": "}|--||",
            "many_to_many_required": "}|--|{",
        }
        return types.get(rel_type, "||--||")

    def generate_from_models(self, models: list[dict]) -> str:
        """从数据模型生成 ER 图"""
        entities = []
        relationships = []

        for model in models:
            entity = {
                "name": model.get("name", ""),
                "attributes": []
            }

            fields = model.get("fields", [])
            for field in fields:
                attr = {
                    "name": field.get("name", ""),
                    "type": field.get("type", "string"),
                    "constraints": []
                }

                if field.get("primary_key"):
                    attr["constraints"].append("PK")
                if field.get("foreign_key"):
                    attr["constraints"].append("FK")
                if field.get("unique"):
                    attr["constraints"].append("UK")
                if field.get("not_null"):
                    attr["constraints"].append("NOT NULL")

                entity["attributes"].append(attr)

            entities.append(entity)

            for rel in model.get("relationships", []):
                relationships.append({
                    "source": model.get("name", ""),
                    "target": rel.get("target", ""),
                    "type": self._get_relationship_type(rel.get("type", "one_to_many")),
                    "label": rel.get("label", "")
                })

        return self.generate({"entities": entities, "relationships": relationships})

    def generate_from_orm_models(self, orm_models: list[dict]) -> str:
        """从 ORM 模型信息生成 ER 图"""
        entities = []
        relationships = []

        for model in orm_models:
            entity = {
                "name": model.get("table_name", model.get("name", "")),
                "attributes": []
            }

            columns = model.get("columns", [])
            for col in columns:
                attr = {
                    "name": col.get("name", ""),
                    "type": self._map_db_type(col.get("type", "")),
                    "constraints": []
                }

                if col.get("primary_key"):
                    attr["constraints"].append("PK")
                if col.get("foreign_key"):
                    attr["constraints"].append("FK")
                    fk_ref = col.get("foreign_key_ref", {})
                    if fk_ref:
                        relationships.append({
                            "source": entity["name"],
                            "target": fk_ref.get("table", ""),
                            "type": "many_to_one",
                            "label": fk_ref.get("name", "")
                        })

                entity["attributes"].append(attr)

            entities.append(entity)

        return self.generate({"entities": entities, "relationships": relationships})

    def _map_db_type(self, db_type: str) -> str:
        type_map = {
            "INTEGER": "int",
            "BIGINT": "bigint",
            "SMALLINT": "smallint",
            "VARCHAR": "string",
            "TEXT": "string",
            "CHAR": "string",
            "BOOLEAN": "bool",
            "DATE": "date",
            "DATETIME": "datetime",
            "TIMESTAMP": "timestamp",
            "FLOAT": "float",
            "DOUBLE": "double",
            "DECIMAL": "decimal",
            "BLOB": "blob",
            "JSON": "json",
            "UUID": "uuid",
        }
        return type_map.get(db_type.upper(), db_type.lower())

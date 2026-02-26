"""
类图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class ClassDiagramGenerator(BaseDiagramGenerator):
    """
    生成类图
    
    示例输出:
    classDiagram
        class User {
            +int id
            +string name
            +string email
            +login()
            +logout()
        }
        class Order {
            +int id
            +datetime created_at
            +create()
        }
        User "1" --> "*" Order : places
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        classes = data.get("classes", [])
        relationships = data.get("relationships", [])

        lines = ["classDiagram"]

        if title:
            lines.append(f"    %% {title}")

        for cls in classes:
            class_name = cls.get("name", "")
            is_abstract = cls.get("is_abstract", False)
            is_interface = cls.get("is_interface", False)

            if is_abstract:
                lines.append(f"    class {class_name}")
                lines.append(f"    <<abstract>> {class_name}")
            elif is_interface:
                lines.append(f"    class {class_name}")
                lines.append(f"    <<interface>> {class_name}")
            else:
                lines.append(f"    class {class_name} {{")

            attributes = cls.get("attributes", [])
            for attr in attributes:
                visibility = self._get_visibility_symbol(attr.get("visibility", "public"))
                attr_name = attr.get("name", "")
                attr_type = attr.get("type", "")
                if attr_type:
                    lines.append(f"        {visibility}{attr_name}: {attr_type}")
                else:
                    lines.append(f"        {visibility}{attr_name}")

            methods = cls.get("methods", [])
            for method in methods:
                visibility = self._get_visibility_symbol(method.get("visibility", "public"))
                method_name = method.get("name", "")
                params = method.get("parameters", [])
                return_type = method.get("return_type", "")

                param_str = ", ".join(p.get("name", "") for p in params)
                if return_type:
                    lines.append(f"        {visibility}{method_name}({param_str}): {return_type}")
                else:
                    lines.append(f"        {visibility}{method_name}({param_str})")

            if not is_abstract and not is_interface:
                lines.append("    }")

        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            rel_type = rel.get("type", "association")
            label = rel.get("label", "")
            multiplicity = rel.get("multiplicity", "")

            arrow = self._get_relationship_arrow(rel_type)

            if multiplicity:
                if label:
                    lines.append(f"    {source} {multiplicity} {arrow} {target} : {label}")
                else:
                    lines.append(f"    {source} {multiplicity} {arrow} {target}")
            else:
                if label:
                    lines.append(f"    {source} {arrow} {target} : {label}")
                else:
                    lines.append(f"    {source} {arrow} {target}")

        return self.wrap_mermaid("\n".join(lines))

    def _get_visibility_symbol(self, visibility: str) -> str:
        symbols = {
            "public": "+",
            "private": "-",
            "protected": "#",
            "package": "~",
        }
        return symbols.get(visibility, "+")

    def _get_relationship_arrow(self, rel_type: str) -> str:
        arrows = {
            "association": "-->",
            "inheritance": "--|>",
            "implementation": "..|>",
            "composition": "*--",
            "aggregation": "o--",
            "dependency": "..>",
        }
        return arrows.get(rel_type, "-->")

    def generate_from_class_info(self, class_info: dict) -> str:
        """从类信息生成类图"""
        classes = []
        relationships = []

        cls_data = self._parse_class(class_info)
        classes.append(cls_data)

        for base in class_info.get("bases", []):
            relationships.append({
                "source": class_info.get("name", ""),
                "target": base,
                "type": "inheritance"
            })

        for nested in class_info.get("nested_classes", []):
            nested_data = self._parse_class(nested)
            classes.append(nested_data)
            relationships.append({
                "source": class_info.get("name", ""),
                "target": nested.get("name", ""),
                "type": "composition"
            })

        return self.generate({"classes": classes, "relationships": relationships})

    def _parse_class(self, class_info: dict) -> dict:
        attributes = []
        for prop in class_info.get("properties", []):
            attributes.append({
                "name": prop.get("name", ""),
                "type": prop.get("type_hint", ""),
                "visibility": prop.get("visibility", "public")
            })

        for var in class_info.get("class_variables", []):
            attributes.append({
                "name": var.get("name", ""),
                "type": var.get("type_hint", ""),
                "visibility": var.get("visibility", "public")
            })

        methods = []
        for method in class_info.get("methods", []):
            methods.append({
                "name": method.get("name", ""),
                "parameters": method.get("parameters", []),
                "return_type": method.get("return_type", ""),
                "visibility": method.get("visibility", "public")
            })

        return {
            "name": class_info.get("name", ""),
            "attributes": attributes,
            "methods": methods,
            "is_abstract": class_info.get("is_abstract", False)
        }

    def generate_inheritance_tree(self, classes: list[dict]) -> str:
        """生成继承关系树"""
        relationships = []

        for cls in classes:
            for base in cls.get("bases", []):
                relationships.append({
                    "source": cls.get("name", ""),
                    "target": base,
                    "type": "inheritance"
                })

        class_list = [self._parse_class(cls) for cls in classes]

        return self.generate({"classes": class_list, "relationships": relationships})

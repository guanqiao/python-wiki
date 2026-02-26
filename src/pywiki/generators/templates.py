"""
模板管理器
"""

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template


class TemplateManager:
    """文档模板管理器"""

    DEFAULT_TEMPLATES = {
        "readme.md": """# {{ project_name }}

{{ description }}

## Features

{% for feature in features %}
- {{ feature }}
{% endfor %}

## Installation

```
{{ installation }}
```

## Usage

```
{{ usage }}
```

## License

MIT
""",
        "module.md": """# {{ module.name }}

{% if module.docstring %}
## Overview

{{ module.docstring }}
{% endif %}

{% if module.classes %}
## Classes

{% for class in module.classes %}
### {{ class.name }}

{% if class.docstring %}
{{ class.docstring }}
{% endif %}

{% if class.methods %}
#### Methods

{% for method in class.methods %}
- `{{ method.name }}({{ method.parameters | map(attribute='name') | join(', ') }})`
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{% if module.functions %}
## Functions

{% for func in module.functions %}
### `{{ func.name }}({{ func.parameters | map(attribute='name') | join(', ') }})`

{% if func.docstring %}
{{ func.docstring }}
{% endif %}
{% endfor %}
{% endif %}
""",
        "architecture.md": """# {{ title }}

## Overview

{{ description }}

## Architecture Diagram

{{ diagram }}

## Components

{% for component in components %}
### {{ component.name }}

{{ component.description }}

{% endfor %}
""",
        "api_reference.md": """# API Reference

{% for module in modules %}
## {{ module.name }}

{% if module.docstring %}
{{ module.docstring }}
{% endif %}

{% for class in module.classes %}
### {{ class.name }}

{% if class.docstring %}
{{ class.docstring }}
{% endif %}

{% if class.methods %}
#### Methods

| Method | Description |
|--------|-------------|
{% for method in class.methods %}
| `{{ method.name }}()` | {{ method.description or '-' }} |
{% endfor %}
{% endif %}

{% endfor %}
{% endfor %}
""",
    }

    def __init__(self, template_dir: Optional[Path] = None):
        self.template_dir = template_dir
        self._env: Optional[Environment] = None
        self._templates: dict[str, Template] = {}

        if template_dir and template_dir.exists():
            self._env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=False,
            )

    def get_template(self, name: str) -> Template:
        """获取模板"""
        if name in self._templates:
            return self._templates[name]

        if self._env:
            try:
                template = self._env.get_template(name)
                self._templates[name] = template
                return template
            except Exception:
                pass

        if name in self.DEFAULT_TEMPLATES:
            template = Template(self.DEFAULT_TEMPLATES[name])
            self._templates[name] = template
            return template

        raise ValueError(f"Template not found: {name}")

    def register_template(self, name: str, content: str) -> None:
        """注册自定义模板"""
        self._templates[name] = Template(content)

    def render(self, template_name: str, context: dict) -> str:
        """渲染模板"""
        template = self.get_template(template_name)
        return template.render(**context)

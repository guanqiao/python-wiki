"""
配置文档生成器
"""

import json
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language


class ConfigGenerator(BaseDocGenerator):
    """配置文档生成器"""

    doc_type = DocType.CONFIGURATION
    template_name = "config.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成配置文档"""
        try:
            project_language = context.project_language or context.detect_project_language()
            config_data = self._extract_config_data(context, project_language)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    config_data,
                    context.metadata["llm_client"]
                )
                config_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 环境配置文档",
                requirements=config_data.get("requirements", {}),
                env_variables=config_data.get("env_variables", []),
                config_files=config_data.get("config_files", []),
                setup_steps=config_data.get("setup_steps", []),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="配置文档生成成功",
                metadata={"config_data": config_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _extract_config_data(self, context: DocGeneratorContext, project_language: str) -> dict[str, Any]:
        """提取配置数据"""
        config_data = {
            "requirements": {},
            "env_variables": [],
            "config_files": [],
            "setup_steps": [],
            "summary": {},
        }

        if project_language == "java":
            config_data = self._extract_java_config_data(context)
        elif project_language == "typescript":
            config_data = self._extract_typescript_config_data(context)
        else:
            config_data = self._extract_python_config_data(context)

        return config_data

    def _extract_python_config_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 Python 项目配置数据"""
        config_data = {
            "requirements": {},
            "env_variables": [],
            "config_files": [],
            "setup_steps": [],
            "summary": {},
        }

        config_data["requirements"] = self._extract_python_requirements(context)
        config_data["env_variables"] = self._extract_env_variables(context)
        config_data["config_files"] = self._extract_python_config_files(context)
        config_data["setup_steps"] = self._extract_python_setup_steps(context)

        return config_data

    def _extract_java_config_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 Java 项目配置数据"""
        config_data = {
            "requirements": {},
            "env_variables": [],
            "config_files": [],
            "setup_steps": [],
            "summary": {},
        }

        config_data["requirements"] = self._extract_java_requirements(context)
        config_data["env_variables"] = self._extract_java_env_variables(context)
        config_data["config_files"] = self._extract_java_config_files(context)
        config_data["setup_steps"] = self._extract_java_setup_steps(context)

        return config_data

    def _extract_typescript_config_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 TypeScript 项目配置数据"""
        config_data = {
            "requirements": {},
            "env_variables": [],
            "config_files": [],
            "setup_steps": [],
            "summary": {},
        }

        config_data["requirements"] = self._extract_typescript_requirements(context)
        config_data["env_variables"] = self._extract_typescript_env_variables(context)
        config_data["config_files"] = self._extract_typescript_config_files(context)
        config_data["setup_steps"] = self._extract_typescript_setup_steps(context)

        return config_data

    def _extract_python_requirements(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取 Python 项目系统要求"""
        requirements = {
            "Python": ">=3.10",
        }

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                    if "python" in deps:
                        requirements["Python"] = deps["python"]
            except Exception:
                pass

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            if "Node.js" in content:
                requirements["Node.js"] = ">=16.0"
            if "Git" in content:
                requirements["Git"] = ">=2.0"

        return requirements

    def _extract_java_requirements(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取 Java 项目系统要求"""
        requirements = {
            "JDK": ">=11",
        }

        pom_path = context.project_path / "pom.xml"
        if pom_path.exists():
            try:
                content = pom_path.read_text(encoding="utf-8")
                import re
                java_version_match = re.search(r"<java\.version>([^<]+)</java\.version>", content)
                if java_version_match:
                    requirements["JDK"] = java_version_match.group(1)
                
                maven_version_match = re.search(r"<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>", content)
                if maven_version_match:
                    requirements["JDK"] = maven_version_match.group(1)
            except Exception:
                pass
            
            requirements["Maven"] = ">=3.6"

        gradle_path = context.project_path / "build.gradle"
        gradle_kts_path = context.project_path / "build.gradle.kts"
        if gradle_path.exists() or gradle_kts_path.exists():
            requirements["Gradle"] = ">=7.0"
            if "Maven" in requirements:
                del requirements["Maven"]

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            if "Docker" in content:
                requirements["Docker"] = ">=20.0"
            if "Git" in content:
                requirements["Git"] = ">=2.0"

        return requirements

    def _extract_typescript_requirements(self, context: DocGeneratorContext) -> dict[str, str]:
        """提取 TypeScript 项目系统要求"""
        requirements = {
            "Node.js": ">=16.0",
        }

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                
                engines = data.get("engines", {})
                if "node" in engines:
                    node_version = engines["node"].replace(">=", "").replace("^", "").strip()
                    requirements["Node.js"] = node_version
                
                if "npm" in engines:
                    requirements["npm"] = engines["npm"]
            except Exception:
                pass

        if (context.project_path / "yarn.lock").exists():
            requirements["Yarn"] = ">=1.22"
        elif (context.project_path / "pnpm-lock.yaml").exists():
            requirements["pnpm"] = ">=7.0"

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            if "Docker" in content:
                requirements["Docker"] = ">=20.0"
            if "Git" in content:
                requirements["Git"] = ">=2.0"

        return requirements

    def _extract_env_variables(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取环境变量"""
        env_variables = []

        env_example_path = context.project_path / ".env.example"
        if env_example_path.exists():
            for line in env_example_path.read_text(encoding="utf-8").split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    default = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
                    env_variables.append({
                        "name": name,
                        "type": "string",
                        "default": default,
                        "description": "",
                    })

        if context.parse_result and context.parse_result.modules:
            for module in context.parse_result.modules:
                for cls in module.classes:
                    if "Config" in cls.name or "Settings" in cls.name:
                        for prop in cls.properties:
                            if prop.name.isupper() or prop.name.startswith("_"):
                                continue
                            env_var = {
                                "name": prop.name.upper(),
                                "type": prop.type_hint or "string",
                                "default": "",
                                "description": "",
                            }
                            if env_var not in env_variables:
                                env_variables.append(env_var)

        return env_variables[:20]

    def _extract_java_env_variables(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Java 项目环境变量"""
        env_variables = []

        env_example_path = context.project_path / ".env.example"
        if env_example_path.exists():
            for line in env_example_path.read_text(encoding="utf-8").split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    default = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
                    env_variables.append({
                        "name": name,
                        "type": "string",
                        "default": default,
                        "description": "",
                    })

        application_properties = context.project_path / "src" / "main" / "resources" / "application.properties"
        if application_properties.exists():
            try:
                for line in application_properties.read_text(encoding="utf-8").split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        parts = line.split("=", 1)
                        name = parts[0].strip()
                        default = parts[1].strip() if len(parts) > 1 else ""
                        env_variables.append({
                            "name": name,
                            "type": "string",
                            "default": default,
                            "description": "",
                        })
            except Exception:
                pass

        application_yml = context.project_path / "src" / "main" / "resources" / "application.yml"
        if application_yml.exists():
            try:
                import yaml
                with open(application_yml, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    def extract_yaml_vars(d: dict, prefix: str = "") -> None:
                        for key, value in d.items():
                            full_key = f"{prefix}.{key}" if prefix else key
                            if isinstance(value, dict):
                                extract_yaml_vars(value, full_key)
                            else:
                                env_variables.append({
                                    "name": full_key,
                                    "type": type(value).__name__,
                                    "default": str(value) if value is not None else "",
                                    "description": "",
                                })
                    extract_yaml_vars(data)
            except Exception:
                pass

        return env_variables[:20]

    def _extract_typescript_env_variables(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 TypeScript 项目环境变量"""
        env_variables = []

        env_example_path = context.project_path / ".env.example"
        if env_example_path.exists():
            for line in env_example_path.read_text(encoding="utf-8").split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    default = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
                    env_variables.append({
                        "name": name,
                        "type": "string",
                        "default": default,
                        "description": "",
                    })

        env_file = context.project_path / ".env"
        if env_file.exists() and not env_variables:
            for line in env_file.read_text(encoding="utf-8").split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    default = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
                    env_variables.append({
                        "name": name,
                        "type": "string",
                        "default": default,
                        "description": "",
                    })

        return env_variables[:20]

    def _extract_python_config_files(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Python 项目配置文件"""
        config_files = []

        config_patterns = [
            ("pyproject.toml", "Python 项目配置"),
            ("setup.py", "Python 安装配置"),
            ("requirements.txt", "Python 依赖"),
            (".env", "环境变量配置"),
            ("config.yaml", "YAML 配置"),
            ("config.json", "JSON 配置"),
            ("settings.py", "Django 设置"),
        ]

        for filename, description in config_patterns:
            file_path = context.project_path / filename
            if file_path.exists():
                config_files.append({
                    "name": filename,
                    "description": description,
                    "options": self._parse_config_file(file_path),
                })

        return config_files

    def _extract_java_config_files(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 Java 项目配置文件"""
        config_files = []

        config_patterns = [
            ("pom.xml", "Maven 项目配置"),
            ("build.gradle", "Gradle 构建配置"),
            ("build.gradle.kts", "Gradle Kotlin DSL 配置"),
            ("settings.gradle", "Gradle 设置"),
            ("src/main/resources/application.properties", "Spring Boot 配置"),
            ("src/main/resources/application.yml", "Spring Boot YAML 配置"),
            ("src/main/resources/application.yaml", "Spring Boot YAML 配置"),
        ]

        for filename, description in config_patterns:
            file_path = context.project_path / filename
            if file_path.exists():
                config_files.append({
                    "name": filename,
                    "description": description,
                    "options": self._parse_config_file(file_path),
                })

        return config_files

    def _extract_typescript_config_files(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取 TypeScript 项目配置文件"""
        config_files = []

        config_patterns = [
            ("package.json", "NPM 项目配置"),
            ("tsconfig.json", "TypeScript 配置"),
            ("tsconfig.build.json", "TypeScript 构建配置"),
            (".eslintrc.js", "ESLint 配置"),
            (".eslintrc.json", "ESLint 配置"),
            (".prettierrc", "Prettier 配置"),
            (".prettierrc.json", "Prettier 配置"),
            ("jest.config.js", "Jest 测试配置"),
            ("vite.config.ts", "Vite 构建配置"),
            ("webpack.config.js", "Webpack 构建配置"),
        ]

        for filename, description in config_patterns:
            file_path = context.project_path / filename
            if file_path.exists():
                config_files.append({
                    "name": filename,
                    "description": description,
                    "options": self._parse_config_file(file_path),
                })

        return config_files

    def _parse_config_file(self, file_path: Path) -> list[dict[str, str]]:
        """解析配置文件"""
        options = []

        if file_path.suffix == ".toml":
            try:
                import tomllib
                with open(file_path, "rb") as f:
                    data = tomllib.load(f)

                def extract_options(d: dict, prefix: str = "") -> None:
                    for key, value in d.items():
                        full_key = f"{prefix}.{key}" if prefix else key
                        if isinstance(value, dict):
                            extract_options(value, full_key)
                        else:
                            options.append({
                                "key": full_key,
                                "type": type(value).__name__,
                                "default": str(value) if not isinstance(value, (list, dict)) else "",
                                "description": "",
                            })

                extract_options(data)
            except Exception:
                pass

        elif file_path.suffix == ".yaml" or file_path.suffix == ".yml":
            try:
                import yaml
                with open(file_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    for key, value in data.items():
                        options.append({
                            "key": key,
                            "type": type(value).__name__,
                            "default": str(value) if not isinstance(value, (list, dict)) else "",
                            "description": "",
                        })
            except Exception:
                pass

        elif file_path.suffix == ".json" or file_path.name == "package.json":
            try:
                content = file_path.read_text(encoding="utf-8")
                data = json.loads(content)
                if isinstance(data, dict):
                    for key, value in data.items():
                        options.append({
                            "key": key,
                            "type": type(value).__name__,
                            "default": str(value) if not isinstance(value, (list, dict)) else "",
                            "description": "",
                        })
            except Exception:
                pass

        elif file_path.suffix == ".properties":
            try:
                for line in file_path.read_text(encoding="utf-8").split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        parts = line.split("=", 1)
                        options.append({
                            "key": parts[0].strip(),
                            "type": "string",
                            "default": parts[1].strip() if len(parts) > 1 else "",
                            "description": "",
                        })
            except Exception:
                pass

        return options[:20]

    def _extract_python_setup_steps(self, context: DocGeneratorContext) -> list[str]:
        """提取 Python 项目安装步骤"""
        steps = []

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            in_install = False

            for line in lines:
                if "安装" in line or "Install" in line:
                    in_install = True
                    continue
                if in_install:
                    if line.startswith("##"):
                        break
                    if line.strip().startswith("```"):
                        continue
                    if line.strip().startswith("- ") or line.strip().startswith("* "):
                        step = line.strip()[2:].strip()
                        if step:
                            steps.append(step)
                    elif line.strip() and not line.strip().startswith("#"):
                        steps.append(line.strip())

        if not steps:
            steps = [
                "克隆仓库",
                "创建虚拟环境",
                "安装依赖: pip install -e .",
                "配置环境变量",
                "运行项目",
            ]

        return steps[:10]

    def _extract_java_setup_steps(self, context: DocGeneratorContext) -> list[str]:
        """提取 Java 项目安装步骤"""
        steps = []

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            in_install = False

            for line in lines:
                if "安装" in line or "Install" in line or "Getting Started" in line:
                    in_install = True
                    continue
                if in_install:
                    if line.startswith("##"):
                        break
                    if line.strip().startswith("```"):
                        continue
                    if line.strip().startswith("- ") or line.strip().startswith("* "):
                        step = line.strip()[2:].strip()
                        if step:
                            steps.append(step)
                    elif line.strip() and not line.strip().startswith("#"):
                        steps.append(line.strip())

        if not steps:
            if (context.project_path / "pom.xml").exists():
                steps = [
                    "克隆仓库",
                    "安装 JDK",
                    "运行: mvn clean install",
                    "配置环境变量",
                    "运行项目",
                ]
            elif (context.project_path / "build.gradle").exists():
                steps = [
                    "克隆仓库",
                    "安装 JDK",
                    "运行: ./gradlew build",
                    "配置环境变量",
                    "运行项目",
                ]
            else:
                steps = [
                    "克隆仓库",
                    "安装 JDK",
                    "安装依赖",
                    "配置环境变量",
                    "运行项目",
                ]

        return steps[:10]

    def _extract_typescript_setup_steps(self, context: DocGeneratorContext) -> list[str]:
        """提取 TypeScript 项目安装步骤"""
        steps = []

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            lines = content.split("\n")
            in_install = False

            for line in lines:
                if "安装" in line or "Install" in line or "Getting Started" in line:
                    in_install = True
                    continue
                if in_install:
                    if line.startswith("##"):
                        break
                    if line.strip().startswith("```"):
                        continue
                    if line.strip().startswith("- ") or line.strip().startswith("* "):
                        step = line.strip()[2:].strip()
                        if step:
                            steps.append(step)
                    elif line.strip() and not line.strip().startswith("#"):
                        steps.append(line.strip())

        if not steps:
            steps = [
                "克隆仓库",
                "安装 Node.js",
                "运行: npm install",
                "配置环境变量",
                "运行项目",
            ]

        return steps[:10]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        config_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强配置文档"""
        enhanced = {}

        prompt = f"""基于以下配置信息，提供配置最佳实践建议：

项目: {context.project_name}
配置文件: {[f['name'] for f in config_data.get('config_files', [])]}
环境变量数量: {len(config_data.get('env_variables', []))}

请以 JSON 格式返回：
{{
    "configuration_best_practices": ["最佳实践1", "最佳实践2"],
    "security_recommendations": ["安全建议1", "安全建议2"],
    "common_issues": ["常见问题1", "常见问题2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["best_practices"] = result.get("configuration_best_practices", [])
                enhanced["security_recommendations"] = result.get("security_recommendations", [])
        except Exception:
            pass

        return enhanced

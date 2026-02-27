"""
开发指南文档生成器
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


class DevelopmentGenerator(BaseDocGenerator):
    """开发指南文档生成器"""

    doc_type = DocType.DEVELOPMENT
    template_name = "development.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成开发指南文档"""
        try:
            project_language = context.project_language or context.detect_project_language()
            dev_data = self._extract_dev_data(context, project_language)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    dev_data,
                    context.metadata["llm_client"]
                )
                dev_data.update(enhanced_data)

            content = self.render_template(
                description=f"{context.project_name} 开发指南",
                prerequisites=dev_data.get("prerequisites", []),
                installation=dev_data.get("installation", ""),
                build=dev_data.get("build", []),
                testing=dev_data.get("testing", []),
                deployment=dev_data.get("deployment", []),
                scripts=dev_data.get("scripts", []),
            )

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="开发指南文档生成成功",
                metadata={"dev_data": dev_data.get("summary", {})},
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _extract_dev_data(self, context: DocGeneratorContext, project_language: str) -> dict[str, Any]:
        """提取开发数据"""
        dev_data = {
            "prerequisites": [],
            "installation": "",
            "build": [],
            "testing": [],
            "deployment": [],
            "scripts": [],
            "summary": {},
        }

        if project_language == "java":
            dev_data = self._extract_java_dev_data(context)
        elif project_language == "typescript":
            dev_data = self._extract_typescript_dev_data(context)
        else:
            dev_data = self._extract_python_dev_data(context)

        return dev_data

    def _extract_python_dev_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 Python 项目开发数据"""
        dev_data = {
            "prerequisites": [],
            "installation": "",
            "build": [],
            "testing": [],
            "deployment": [],
            "scripts": [],
            "summary": {},
        }

        dev_data["prerequisites"] = self._extract_python_prerequisites(context)
        dev_data["installation"] = self._extract_python_installation(context)
        dev_data["build"] = self._extract_python_build_steps(context)
        dev_data["testing"] = self._extract_python_testing_steps(context)
        dev_data["deployment"] = self._extract_deployment_steps(context)
        dev_data["scripts"] = self._extract_python_scripts(context)

        return dev_data

    def _extract_java_dev_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 Java 项目开发数据"""
        dev_data = {
            "prerequisites": [],
            "installation": "",
            "build": [],
            "testing": [],
            "deployment": [],
            "scripts": [],
            "summary": {},
        }

        dev_data["prerequisites"] = self._extract_java_prerequisites(context)
        dev_data["installation"] = self._extract_java_installation(context)
        dev_data["build"] = self._extract_java_build_steps(context)
        dev_data["testing"] = self._extract_java_testing_steps(context)
        dev_data["deployment"] = self._extract_deployment_steps(context)
        dev_data["scripts"] = self._extract_java_scripts(context)

        return dev_data

    def _extract_typescript_dev_data(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 TypeScript 项目开发数据"""
        dev_data = {
            "prerequisites": [],
            "installation": "",
            "build": [],
            "testing": [],
            "deployment": [],
            "scripts": [],
            "summary": {},
        }

        dev_data["prerequisites"] = self._extract_typescript_prerequisites(context)
        dev_data["installation"] = self._extract_typescript_installation(context)
        dev_data["build"] = self._extract_typescript_build_steps(context)
        dev_data["testing"] = self._extract_typescript_testing_steps(context)
        dev_data["deployment"] = self._extract_deployment_steps(context)
        dev_data["scripts"] = self._extract_typescript_scripts(context)

        return dev_data

    def _extract_python_prerequisites(self, context: DocGeneratorContext) -> list[str]:
        """提取 Python 项目前置条件"""
        prerequisites = []

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    deps = data["tool"]["poetry"].get("dependencies", {})
                    if "python" in deps:
                        prerequisites.append(f"Python {deps['python']}")
            except Exception:
                pass

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            if "Node.js" in content:
                prerequisites.append("Node.js >= 16.0")
            if "Git" in content:
                prerequisites.append("Git")
            if "Docker" in content:
                prerequisites.append("Docker")

        if not prerequisites:
            prerequisites = [
                "Python >= 3.10",
                "pip 或 poetry",
                "Git",
            ]

        return prerequisites

    def _extract_java_prerequisites(self, context: DocGeneratorContext) -> list[str]:
        """提取 Java 项目前置条件"""
        prerequisites = []

        pom_path = context.project_path / "pom.xml"
        if pom_path.exists():
            try:
                content = pom_path.read_text(encoding="utf-8")
                import re
                java_version_match = re.search(r"<java\.version>([^<]+)</java\.version>", content)
                if java_version_match:
                    prerequisites.append(f"JDK {java_version_match.group(1)}")
                else:
                    prerequisites.append("JDK >= 11")
            except Exception:
                prerequisites.append("JDK >= 11")
            
            prerequisites.append("Maven >= 3.6")

        gradle_path = context.project_path / "build.gradle"
        if gradle_path.exists() or (context.project_path / "build.gradle.kts").exists():
            if not any("JDK" in p for p in prerequisites):
                prerequisites.insert(0, "JDK >= 11")
            if not any("Gradle" in p for p in prerequisites):
                prerequisites.append("Gradle >= 7.0")

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            if "Docker" in content:
                prerequisites.append("Docker")
            if "Git" in content:
                prerequisites.append("Git")

        if not prerequisites:
            prerequisites = [
                "JDK >= 11",
                "Maven 或 Gradle",
                "Git",
            ]

        return prerequisites

    def _extract_typescript_prerequisites(self, context: DocGeneratorContext) -> list[str]:
        """提取 TypeScript 项目前置条件"""
        prerequisites = []

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                
                engines = data.get("engines", {})
                if "node" in engines:
                    node_version = engines["node"].replace(">=", "").replace("^", "").strip()
                    prerequisites.append(f"Node.js {node_version}")
                else:
                    prerequisites.append("Node.js >= 16.0")
                
                if "npm" in engines:
                    prerequisites.append(f"npm {engines['npm']}")
            except Exception:
                prerequisites.append("Node.js >= 16.0")

        if (context.project_path / "yarn.lock").exists():
            prerequisites.append("Yarn")
        elif (context.project_path / "pnpm-lock.yaml").exists():
            prerequisites.append("pnpm")

        readme_path = context.project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding="utf-8")
            if "Docker" in content:
                prerequisites.append("Docker")
            if "Git" in content:
                prerequisites.append("Git")

        if not prerequisites:
            prerequisites = [
                "Node.js >= 16.0",
                "npm 或 yarn",
                "Git",
            ]

        return prerequisites

    def _extract_python_installation(self, context: DocGeneratorContext) -> str:
        """提取 Python 项目安装命令"""
        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    return "poetry install"
            except Exception:
                pass

        if (context.project_path / "requirements.txt").exists():
            return "pip install -r requirements.txt"

        return "pip install -e ."

    def _extract_java_installation(self, context: DocGeneratorContext) -> str:
        """提取 Java 项目安装命令"""
        if (context.project_path / "pom.xml").exists():
            return "mvn clean install"
        
        if (context.project_path / "build.gradle").exists() or (context.project_path / "build.gradle.kts").exists():
            if (context.project_path / "gradlew").exists():
                return "./gradlew build"
            return "gradle build"

        return "mvn clean install"

    def _extract_typescript_installation(self, context: DocGeneratorContext) -> str:
        """提取 TypeScript 项目安装命令"""
        if (context.project_path / "yarn.lock").exists():
            return "yarn install"
        
        if (context.project_path / "pnpm-lock.yaml").exists():
            return "pnpm install"
        
        return "npm install"

    def _extract_python_build_steps(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Python 项目构建步骤"""
        build_steps = []

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    build_steps.append({
                        "name": "构建包",
                        "command": "poetry build",
                        "description": "构建发布包",
                    })
            except Exception:
                pass

        if (context.project_path / "Makefile").exists():
            build_steps.append({
                "name": "使用 Makefile",
                "command": "make build",
                "description": "执行 Makefile 构建命令",
            })

        if not build_steps:
            build_steps = [
                {
                    "name": "安装依赖",
                    "command": self._extract_python_installation(context),
                    "description": "安装项目依赖",
                }
            ]

        return build_steps

    def _extract_java_build_steps(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Java 项目构建步骤"""
        build_steps = []

        if (context.project_path / "pom.xml").exists():
            build_steps.append({
                "name": "Maven 编译",
                "command": "mvn compile",
                "description": "编译项目源代码",
            })
            build_steps.append({
                "name": "Maven 打包",
                "command": "mvn package",
                "description": "打包为 JAR/WAR 文件",
            })

        if (context.project_path / "build.gradle").exists() or (context.project_path / "build.gradle.kts").exists():
            gradle_cmd = "./gradlew" if (context.project_path / "gradlew").exists() else "gradle"
            build_steps.append({
                "name": "Gradle 编译",
                "command": f"{gradle_cmd} compileJava",
                "description": "编译项目源代码",
            })
            build_steps.append({
                "name": "Gradle 打包",
                "command": f"{gradle_cmd} build",
                "description": "打包为 JAR/WAR 文件",
            })

        if not build_steps:
            build_steps = [
                {
                    "name": "安装依赖",
                    "command": self._extract_java_installation(context),
                    "description": "安装项目依赖",
                }
            ]

        return build_steps

    def _extract_typescript_build_steps(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 TypeScript 项目构建步骤"""
        build_steps = []

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                scripts = data.get("scripts", {})
                
                if "build" in scripts:
                    build_steps.append({
                        "name": "构建项目",
                        "command": "npm run build" if not (context.project_path / "yarn.lock").exists() else "yarn build",
                        "description": "编译 TypeScript 代码",
                    })
                
                if "compile" in scripts and "build" not in scripts:
                    build_steps.append({
                        "name": "编译项目",
                        "command": "npm run compile" if not (context.project_path / "yarn.lock").exists() else "yarn compile",
                        "description": "编译 TypeScript 代码",
                    })
            except Exception:
                pass

        if (context.project_path / "tsconfig.json").exists() and not build_steps:
            build_steps.append({
                "name": "TypeScript 编译",
                "command": "npx tsc",
                "description": "使用 tsc 编译 TypeScript",
            })

        if not build_steps:
            build_steps = [
                {
                    "name": "安装依赖",
                    "command": self._extract_typescript_installation(context),
                    "description": "安装项目依赖",
                }
            ]

        return build_steps

    def _extract_python_testing_steps(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Python 项目测试步骤"""
        testing_steps = []

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                dev_deps = {}
                if "tool" in data and "poetry" in data["tool"]:
                    dev_deps = data["tool"]["poetry"].get("group", {}).get("dev", {}).get("dependencies", {})
                elif "project" in data:
                    dev_deps = data["project"].get("optional-dependencies", {}).get("dev", [])

                if any("pytest" in str(d) for d in dev_deps):
                    testing_steps.append({
                        "name": "运行测试",
                        "command": "pytest",
                        "description": "运行单元测试",
                    })
                    testing_steps.append({
                        "name": "测试覆盖率",
                        "command": "pytest --cov",
                        "description": "生成测试覆盖率报告",
                    })
            except Exception:
                pass

        if (context.project_path / "tests").exists() and not testing_steps:
            testing_steps = [
                {
                    "name": "运行测试",
                    "command": "python -m pytest tests/",
                    "description": "运行测试目录中的所有测试",
                }
            ]

        return testing_steps

    def _extract_java_testing_steps(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Java 项目测试步骤"""
        testing_steps = []

        if (context.project_path / "pom.xml").exists():
            testing_steps.append({
                "name": "Maven 测试",
                "command": "mvn test",
                "description": "运行单元测试",
            })
            testing_steps.append({
                "name": "集成测试",
                "command": "mvn verify",
                "description": "运行集成测试",
            })

        if (context.project_path / "build.gradle").exists() or (context.project_path / "build.gradle.kts").exists():
            gradle_cmd = "./gradlew" if (context.project_path / "gradlew").exists() else "gradle"
            testing_steps.append({
                "name": "Gradle 测试",
                "command": f"{gradle_cmd} test",
                "description": "运行单元测试",
            })

        if not testing_steps:
            testing_steps = [
                {
                    "name": "运行测试",
                    "command": "mvn test",
                    "description": "运行项目测试",
                }
            ]

        return testing_steps

    def _extract_typescript_testing_steps(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 TypeScript 项目测试步骤"""
        testing_steps = []

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                scripts = data.get("scripts", {})
                
                npm_cmd = "yarn" if (context.project_path / "yarn.lock").exists() else "npm run"
                
                if "test" in scripts:
                    testing_steps.append({
                        "name": "运行测试",
                        "command": f"{npm_cmd} test",
                        "description": "运行单元测试",
                    })
                
                if "test:coverage" in scripts:
                    testing_steps.append({
                        "name": "测试覆盖率",
                        "command": f"{npm_cmd} test:coverage",
                        "description": "生成测试覆盖率报告",
                    })
                elif "test" in scripts:
                    testing_steps.append({
                        "name": "测试覆盖率",
                        "command": f"{npm_cmd} test -- --coverage",
                        "description": "生成测试覆盖率报告",
                    })
            except Exception:
                pass

        if not testing_steps:
            testing_steps = [
                {
                    "name": "运行测试",
                    "command": "npm test",
                    "description": "运行项目测试",
                }
            ]

        return testing_steps

    def _extract_deployment_steps(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取部署步骤"""
        deployment_steps = []

        if (context.project_path / "Dockerfile").exists():
            deployment_steps.append({
                "name": "Docker 构建",
                "description": "使用 Docker 构建镜像",
                "commands": [
                    "docker build -t {project_name}:latest .",
                    "docker run -p 8000:8000 {project_name}:latest",
                ],
            })

        if (context.project_path / "docker-compose.yml").exists():
            deployment_steps.append({
                "name": "Docker Compose",
                "description": "使用 Docker Compose 部署",
                "commands": [
                    "docker-compose up -d",
                ],
            })

        if (context.project_path / "kubernetes").exists() or (context.project_path / "k8s").exists():
            deployment_steps.append({
                "name": "Kubernetes",
                "description": "部署到 Kubernetes 集群",
                "commands": [
                    "kubectl apply -f kubernetes/",
                ],
            })

        return deployment_steps

    def _extract_python_scripts(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Python 项目常用脚本"""
        scripts = []

        pyproject_path = context.project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                import tomllib
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)

                if "tool" in data and "poetry" in data["tool"]:
                    script_data = data["tool"]["poetry"].get("scripts", {})
                    for name, entry in script_data.items():
                        scripts.append({
                            "command": name,
                            "description": f"运行 {name}",
                        })
            except Exception:
                pass

        if (context.project_path / "Makefile").exists():
            scripts.append({
                "command": "make help",
                "description": "查看可用命令",
            })

        return scripts[:10]

    def _extract_java_scripts(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 Java 项目常用脚本"""
        scripts = []

        if (context.project_path / "pom.xml").exists():
            scripts.append({
                "command": "mvn clean",
                "description": "清理构建产物",
            })
            scripts.append({
                "command": "mvn compile",
                "description": "编译项目",
            })
            scripts.append({
                "command": "mvn package",
                "description": "打包项目",
            })

        if (context.project_path / "build.gradle").exists() or (context.project_path / "build.gradle.kts").exists():
            gradle_cmd = "./gradlew" if (context.project_path / "gradlew").exists() else "gradle"
            scripts.append({
                "command": f"{gradle_cmd} clean",
                "description": "清理构建产物",
            })
            scripts.append({
                "command": f"{gradle_cmd} build",
                "description": "构建项目",
            })
            scripts.append({
                "command": f"{gradle_cmd} tasks",
                "description": "查看可用任务",
            })

        return scripts[:10]

    def _extract_typescript_scripts(self, context: DocGeneratorContext) -> list[dict[str, str]]:
        """提取 TypeScript 项目常用脚本"""
        scripts = []

        package_path = context.project_path / "package.json"
        if package_path.exists():
            try:
                content = package_path.read_text(encoding="utf-8")
                data = json.loads(content)
                package_scripts = data.get("scripts", {})
                
                npm_cmd = "yarn" if (context.project_path / "yarn.lock").exists() else "npm run"
                
                for name, command in package_scripts.items():
                    scripts.append({
                        "command": f"{npm_cmd} {name}",
                        "description": f"运行 {name}",
                    })
            except Exception:
                pass

        return scripts[:10]

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        dev_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强开发指南"""
        enhanced = {}

        prompt = f"""基于以下开发信息，提供开发最佳实践建议：

项目: {context.project_name}
前置条件: {dev_data.get('prerequisites', [])}
构建步骤: {[s['name'] for s in dev_data.get('build', [])]}
测试步骤: {[s['name'] for s in dev_data.get('testing', [])]}

请以 JSON 格式返回：
{{
    "development_tips": ["开发技巧1", "开发技巧2"],
    "common_pitfalls": ["常见陷阱1", "常见陷阱2"],
    "ide_recommendations": ["IDE 配置建议1", "IDE 配置建议2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                enhanced["tips"] = result.get("development_tips", [])
                enhanced["pitfalls"] = result.get("common_pitfalls", [])
        except Exception:
            pass

        return enhanced

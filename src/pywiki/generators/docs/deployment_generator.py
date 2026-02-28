"""
部署管理文档生成器
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


class DeploymentGenerator(BaseDocGenerator):
    """部署管理文档生成器"""

    doc_type = DocType.DEPLOYMENT
    template_name = "deployment.md.j2"

    def __init__(
        self,
        language: Language = Language.ZH,
        template_dir: Optional[Path] = None,
    ):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成部署管理文档"""
        try:
            project_language = context.project_language or context.detect_project_language()
            deploy_data = self._extract_deployment_data(context, project_language)
            
            if context.metadata.get("llm_client"):
                enhanced_data = await self._enhance_with_llm(
                    context,
                    deploy_data,
                    context.metadata["llm_client"]
                )
                deploy_data.update(enhanced_data)

            description = f"{context.project_name} {self.labels.get('deployment_guide', '部署指南')}"
            
            content = self.render_template(
                description=description,
                deployment_architecture=deploy_data.get("deployment_architecture", ""),
                architecture_diagram=deploy_data.get("architecture_diagram", ""),
                environments=deploy_data.get("environments", []),
                prerequisites=deploy_data.get("prerequisites", []),
                deployment_steps=deploy_data.get("deployment_steps", []),
                containerization=deploy_data.get("containerization", {}),
                cicd=deploy_data.get("cicd", {}),
                monitoring=deploy_data.get("monitoring", {}),
                backup=deploy_data.get("backup", {}),
                troubleshooting=deploy_data.get("troubleshooting", []),
                security=deploy_data.get("security", {}),
                scaling=deploy_data.get("scaling", {}),
                rollback=deploy_data.get("rollback", ""),
                best_practices=deploy_data.get("best_practices", []),
                references=deploy_data.get("references", []),
            )

            success_message = self.labels.get('deployment_guide', '部署指南') + " " + self.labels.get('document_generated', '文档生成成功') if self.language == Language.ZH else f"{self.labels.get('deployment_guide', 'Deployment Guide')} generated successfully"
            
            return self.create_result(
                content=content,
                context=context,
                success=True,
                message=success_message,
                metadata={"deploy_data": deploy_data.get("summary", {})},
            )

        except Exception as e:
            error_msg = f"生成失败: {str(e)}" if self.language == Language.ZH else f"Generation failed: {str(e)}"
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=error_msg,
            )

    def _extract_deployment_data(self, context: DocGeneratorContext, project_language: str) -> dict[str, Any]:
        """提取部署数据"""
        deploy_data = {
            "deployment_architecture": "",
            "architecture_diagram": "",
            "environments": [],
            "prerequisites": [],
            "deployment_steps": [],
            "containerization": {},
            "cicd": {},
            "monitoring": {},
            "backup": {},
            "troubleshooting": [],
            "security": {},
            "scaling": {},
            "rollback": "",
            "best_practices": [],
            "references": [],
            "summary": {},
        }

        deploy_data["containerization"] = self._extract_containerization(context)
        deploy_data["cicd"] = self._extract_cicd(context)
        deploy_data["environments"] = self._extract_environments(context)
        deploy_data["prerequisites"] = self._extract_prerequisites(context, project_language)
        deploy_data["deployment_steps"] = self._extract_deployment_steps(context, project_language)
        deploy_data["monitoring"] = self._extract_monitoring(context)
        deploy_data["security"] = self._extract_security(context)
        deploy_data["deployment_architecture"] = self._generate_architecture_description(context)
        deploy_data["architecture_diagram"] = self._generate_architecture_diagram(context)
        deploy_data["troubleshooting"] = self._extract_troubleshooting(context)
        deploy_data["best_practices"] = self._extract_best_practices(context)
        deploy_data["backup"] = self._extract_backup(context)
        deploy_data["scaling"] = self._extract_scaling(context)

        return deploy_data

    def _extract_containerization(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取容器化配置"""
        containerization = {}

        dockerfile = self._find_dockerfile(context)
        if dockerfile:
            containerization["docker"] = self._parse_dockerfile(context, dockerfile)

        docker_compose = self._find_docker_compose(context)
        if docker_compose:
            containerization["docker_compose"] = self._parse_docker_compose(context, docker_compose)

        kubernetes = self._find_kubernetes_configs(context)
        if kubernetes:
            containerization["kubernetes"] = self._parse_kubernetes(context, kubernetes)

        return containerization

    def _find_dockerfile(self, context: DocGeneratorContext) -> Optional[Path]:
        """查找 Dockerfile"""
        dockerfile_names = ["Dockerfile", "Dockerfile.prod", "Dockerfile.production", "Dockerfile.dev"]
        for name in dockerfile_names:
            path = context.project_path / name
            if path.exists():
                return path
        for path in context.project_path.rglob("Dockerfile*"):
            if "node_modules" not in str(path) and ".git" not in str(path):
                return path
        return None

    def _parse_dockerfile(self, context: DocGeneratorContext, dockerfile: Path) -> dict[str, Any]:
        """解析 Dockerfile"""
        docker_info = {
            "dockerfile_path": str(dockerfile.relative_to(context.project_path)),
            "build_command": f"docker build -t {context.project_name.lower()}:latest .",
            "run_command": "",
            "exposed_ports": [],
        }

        try:
            content = dockerfile.read_text(encoding="utf-8")
            
            expose_matches = re.findall(r"EXPOSE\s+(\d+)", content)
            docker_info["exposed_ports"] = expose_matches

            if expose_matches:
                first_port = expose_matches[0]
                docker_info["run_command"] = f"docker run -p {first_port}:{first_port} {context.project_name.lower()}:latest"
            else:
                docker_info["run_command"] = f"docker run {context.project_name.lower()}:latest"

        except Exception:
            pass

        return docker_info

    def _find_docker_compose(self, context: DocGeneratorContext) -> Optional[Path]:
        """查找 docker-compose 文件"""
        compose_names = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "docker-compose.prod.yml",
            "docker-compose.production.yml",
        ]
        for name in compose_names:
            path = context.project_path / name
            if path.exists():
                return path
        return None

    def _parse_docker_compose(self, context: DocGeneratorContext, compose_file: Path) -> dict[str, Any]:
        """解析 docker-compose 文件"""
        compose_info = {
            "file_path": str(compose_file.relative_to(context.project_path)),
            "services": [],
            "commands": [
                "docker-compose up -d",
                "docker-compose down",
                "docker-compose logs -f",
                "docker-compose ps",
            ],
        }

        try:
            content = compose_file.read_text(encoding="utf-8")
            data = yaml.safe_load(content) if yaml else None
            
            if data and "services" in data:
                for service_name, service_config in data["services"].items():
                    image = service_config.get("image", "自定义构建")
                    ports = service_config.get("ports", [])
                    ports_str = ", ".join(ports) if ports else "-"
                    
                    compose_info["services"].append({
                        "name": service_name,
                        "image": image,
                        "ports": ports_str,
                    })
        except Exception:
            pass

        return compose_info

    def _find_kubernetes_configs(self, context: DocGeneratorContext) -> list[Path]:
        """查找 Kubernetes 配置文件"""
        k8s_paths = []
        
        k8s_dirs = ["kubernetes", "k8s", "deploy", "deployment", "manifests"]
        for dir_name in k8s_dirs:
            dir_path = context.project_path / dir_name
            if dir_path.exists() and dir_path.is_dir():
                for ext in ["*.yaml", "*.yml"]:
                    k8s_paths.extend(dir_path.glob(ext))
        
        for pattern in ["**/deployment*.yaml", "**/deployment*.yml", "**/k8s-*.yaml"]:
            for path in context.project_path.glob(pattern):
                if "node_modules" not in str(path) and ".git" not in str(path):
                    k8s_paths.append(path)

        return list(set(k8s_paths))[:20]

    def _parse_kubernetes(self, context: DocGeneratorContext, k8s_files: list[Path]) -> dict[str, Any]:
        """解析 Kubernetes 配置"""
        k8s_info = {
            "config_path": "",
            "resources": [],
            "commands": [
                "kubectl apply -f kubernetes/",
                "kubectl get pods",
                "kubectl get services",
                "kubectl logs -f deployment/<deployment-name>",
            ],
        }

        if k8s_files:
            first_file = k8s_files[0]
            parent_dir = first_file.parent
            try:
                k8s_info["config_path"] = str(parent_dir.relative_to(context.project_path))
            except ValueError:
                k8s_info["config_path"] = str(parent_dir)

            for k8s_file in k8s_files[:10]:
                try:
                    content = k8s_file.read_text(encoding="utf-8")
                    
                    kind_matches = re.findall(r"kind:\s*(\w+)", content)
                    name_matches = re.findall(r"name:\s*([^\n]+)", content)
                    
                    for i, kind in enumerate(kind_matches[:3]):
                        name = name_matches[i] if i < len(name_matches) else "unknown"
                        k8s_info["resources"].append({
                            "type": kind,
                            "name": name.strip(),
                            "file": str(k8s_file.relative_to(context.project_path)),
                        })
                except Exception:
                    pass

        return k8s_info

    def _extract_cicd(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取 CI/CD 配置"""
        cicd = {}

        github_actions = context.project_path / ".github" / "workflows"
        if github_actions.exists():
            cicd = self._parse_github_actions(context, github_actions)

        gitlab_ci = context.project_path / ".gitlab-ci.yml"
        if gitlab_ci.exists():
            cicd = self._parse_gitlab_ci(context, gitlab_ci)

        jenkinsfile = context.project_path / "Jenkinsfile"
        if jenkinsfile.exists():
            cicd = self._parse_jenkins(context, jenkinsfile)

        azure_pipelines = context.project_path / "azure-pipelines.yml"
        if azure_pipelines.exists():
            cicd = self._parse_azure_pipelines(context, azure_pipelines)

        circleci = context.project_path / ".circleci" / "config.yml"
        if circleci.exists():
            cicd = self._parse_circleci(context, circleci)

        return cicd

    def _parse_github_actions(self, context: DocGeneratorContext, workflows_dir: Path) -> dict[str, Any]:
        """解析 GitHub Actions"""
        cicd = {
            "platform": "GitHub Actions",
            "config_file": ".github/workflows/",
            "pipelines": [],
            "secrets": [],
        }

        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        
        for workflow_file in workflow_files[:5]:
            try:
                content = workflow_file.read_text(encoding="utf-8")
                
                pipeline = {
                    "name": workflow_file.stem,
                    "stages": [],
                    "triggers": [],
                }

                on_match = re.search(r"on:\s*\n((?:\s+.+\n?)+)", content)
                if on_match:
                    triggers = on_match.group(1)
                    if "push" in triggers:
                        pipeline["triggers"].append("Push to branch")
                    if "pull_request" in triggers:
                        pipeline["triggers"].append("Pull Request")
                    if "schedule" in triggers:
                        pipeline["triggers"].append("Scheduled")

                jobs_match = re.search(r"jobs:\s*\n((?:\s+.+\n?)+)", content)
                if jobs_match:
                    jobs_content = jobs_match.group(1)
                    job_names = re.findall(r"^\s+(\w+):", jobs_content, re.MULTILINE)
                    pipeline["stages"] = job_names[:5]

                cicd["pipelines"].append(pipeline)

                secrets = re.findall(r"\$\{\{\s*secrets\.(\w+)\s*\}\}", content)
                for secret in set(secrets):
                    cicd["secrets"].append({
                        "name": secret,
                        "description": f"GitHub Secret: {secret}",
                    })

            except Exception:
                pass

        return cicd

    def _parse_gitlab_ci(self, context: DocGeneratorContext, gitlab_ci: Path) -> dict[str, Any]:
        """解析 GitLab CI"""
        cicd = {
            "platform": "GitLab CI",
            "config_file": ".gitlab-ci.yml",
            "pipelines": [],
            "secrets": [],
        }

        try:
            content = gitlab_ci.read_text(encoding="utf-8")
            
            stages_match = re.search(r"stages:\s*\n((?:\s+-\s+.+\n?)+)", content)
            if stages_match:
                stages = re.findall(r"-\s+(.+)", stages_match.group(1))
                pipeline = {
                    "name": "Main Pipeline",
                    "stages": stages[:5],
                    "triggers": ["Push to branch", "Merge Request"],
                }
                cicd["pipelines"].append(pipeline)

        except Exception:
            pass

        return cicd

    def _parse_jenkins(self, context: DocGeneratorContext, jenkinsfile: Path) -> dict[str, Any]:
        """解析 Jenkinsfile"""
        cicd = {
            "platform": "Jenkins",
            "config_file": "Jenkinsfile",
            "pipelines": [],
            "secrets": [],
        }

        try:
            content = jenkinsfile.read_text(encoding="utf-8")
            
            stages = re.findall(r"stage\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content)
            if stages:
                pipeline = {
                    "name": "Main Pipeline",
                    "stages": stages[:5],
                    "triggers": ["Manual trigger", "SCM polling"],
                }
                cicd["pipelines"].append(pipeline)

        except Exception:
            pass

        return cicd

    def _parse_azure_pipelines(self, context: DocGeneratorContext, azure_file: Path) -> dict[str, Any]:
        """解析 Azure Pipelines"""
        cicd = {
            "platform": "Azure Pipelines",
            "config_file": "azure-pipelines.yml",
            "pipelines": [],
            "secrets": [],
        }

        try:
            content = azure_file.read_text(encoding="utf-8")
            
            stages = re.findall(r"-\s*stage:\s*(\w+)", content)
            if stages:
                pipeline = {
                    "name": "Main Pipeline",
                    "stages": stages[:5],
                    "triggers": ["Push to branch", "Pull Request"],
                }
                cicd["pipelines"].append(pipeline)

        except Exception:
            pass

        return cicd

    def _parse_circleci(self, context: DocGeneratorContext, circleci_file: Path) -> dict[str, Any]:
        """解析 CircleCI"""
        cicd = {
            "platform": "CircleCI",
            "config_file": ".circleci/config.yml",
            "pipelines": [],
            "secrets": [],
        }

        try:
            content = circleci_file.read_text(encoding="utf-8")
            
            jobs = re.findall(r"^(\w+):\s*$", content, re.MULTILINE)
            if jobs:
                pipeline = {
                    "name": "Main Pipeline",
                    "stages": jobs[:5],
                    "triggers": ["Push to branch", "Tag push"],
                }
                cicd["pipelines"].append(pipeline)

        except Exception:
            pass

        return cicd

    def _extract_environments(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取环境配置"""
        environments = []

        env_files = [
            (".env.example", self.labels.get("dev_env_example", "开发环境示例") if self.language == Language.ZH else "Development Environment Example"),
            (".env.development", self.labels.get("dev_env", "开发环境") if self.language == Language.ZH else "Development Environment"),
            (".env.staging", self.labels.get("staging_env", "预发布环境") if self.language == Language.ZH else "Staging Environment"),
            (".env.production", self.labels.get("prod_env", "生产环境") if self.language == Language.ZH else "Production Environment"),
            ("config/settings.py", self.labels.get("config_file", "配置文件") if self.language == Language.ZH else "Configuration File"),
            ("config/config.py", self.labels.get("config_file", "配置文件") if self.language == Language.ZH else "Configuration File"),
        ]

        for file_name, env_name in env_files:
            file_path = context.project_path / file_name
            if file_path.exists():
                env_data = self._parse_env_file(context, file_path, env_name)
                if env_data:
                    environments.append(env_data)

        if not environments:
            default_env = {
                "name": self.labels.get("default_env", "默认环境") if self.language == Language.ZH else "Default Environment",
                "description": self.labels.get("default_env_desc", "项目默认环境配置") if self.language == Language.ZH else "Default project environment configuration",
                "variables": [],
            }
            
            if (context.project_path / "pyproject.toml").exists():
                default_env["variables"].extend([
                    {"name": "PYTHON_VERSION", "description": self.labels.get("python_version", "Python 版本") if self.language == Language.ZH else "Python Version", "default": "3.10", "required": True},
                ])
            
            if (context.project_path / "package.json").exists():
                default_env["variables"].extend([
                    {"name": "NODE_VERSION", "description": self.labels.get("node_version", "Node.js 版本") if self.language == Language.ZH else "Node.js Version", "default": "18", "required": True},
                    {"name": "NPM_TOKEN", "description": self.labels.get("npm_token", "npm 访问令牌") if self.language == Language.ZH else "NPM Access Token", "default": "", "required": False},
                ])

            environments.append(default_env)

        return environments

    def _parse_env_file(self, context: DocGeneratorContext, env_file: Path, env_name: str) -> Optional[dict[str, Any]]:
        """解析环境变量文件"""
        env_data = {
            "name": env_name,
            "description": self.labels.get("env_extracted_from", f"从 {env_file.name} 提取的环境变量") if self.language == Language.ZH else f"Environment variables extracted from {env_file.name}",
            "variables": [],
        }

        try:
            content = env_file.read_text(encoding="utf-8")
            
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    var_name = parts[0].strip()
                    var_value = parts[1].strip() if len(parts) > 1 else ""
                    
                    if var_name:
                        is_required = var_value == "" or var_value.startswith("${")
                        
                        env_data["variables"].append({
                            "name": var_name,
                            "description": f"{var_name} {self.labels.get('config_item', '配置项') if self.language == Language.ZH else 'configuration item'}",
                            "default": var_value if var_value and not var_value.startswith("${") else "",
                            "required": is_required,
                        })

        except Exception:
            return None

        return env_data if env_data["variables"] else None

    def _extract_prerequisites(self, context: DocGeneratorContext, project_language: str) -> list[str]:
        """提取部署前置条件"""
        prerequisites = []

        if project_language == "python":
            prerequisites.extend([
                "Python >= 3.10",
                self.labels.get("pip_or_poetry", "pip 或 poetry") if self.language == Language.ZH else "pip or poetry",
            ])
            if (context.project_path / "pyproject.toml").exists():
                prerequisites.append("poetry" + (f" ({self.labels.get('recommended', '推荐')})" if self.language == Language.ZH else " (recommended)"))
        elif project_language == "java":
            prerequisites.extend([
                "JDK >= 11",
                self.labels.get("maven_or_gradle", "Maven 或 Gradle") if self.language == Language.ZH else "Maven or Gradle",
            ])
        elif project_language == "typescript":
            prerequisites.extend([
                "Node.js >= 16.0",
                self.labels.get("npm_or_yarn", "npm 或 yarn") if self.language == Language.ZH else "npm or yarn",
            ])

        if self._find_dockerfile(context):
            prerequisites.append("Docker")
        if self._find_docker_compose(context):
            prerequisites.append("Docker Compose")
        if self._find_kubernetes_configs(context):
            prerequisites.append("kubectl")
            prerequisites.append(self.labels.get("k8s_access", "Kubernetes 集群访问权限") if self.language == Language.ZH else "Kubernetes cluster access")

        if (context.project_path / ".github" / "workflows").exists():
            prerequisites.append(self.labels.get("github_access", "GitHub 仓库访问权限") if self.language == Language.ZH else "GitHub repository access")
        if (context.project_path / ".gitlab-ci.yml").exists():
            prerequisites.append(self.labels.get("gitlab_access", "GitLab 仓库访问权限") if self.language == Language.ZH else "GitLab repository access")

        return list(set(prerequisites))

    def _extract_deployment_steps(self, context: DocGeneratorContext, project_language: str) -> list[dict[str, Any]]:
        """提取部署步骤"""
        steps = []

        steps.append({
            "name": f"1. {self.labels.get('env_preparation', '环境准备')}" if self.language == Language.ZH else "1. Environment Preparation",
            "description": self.labels.get("env_prep_desc", "准备部署环境，安装必要依赖") if self.language == Language.ZH else "Prepare deployment environment and install dependencies",
            "commands": self._get_setup_commands(context, project_language),
        })

        if self._find_dockerfile(context):
            steps.append({
                "name": f"2. {self.labels.get('build_image', '构建镜像')}" if self.language == Language.ZH else "2. Build Image",
                "description": self.labels.get("build_docker_image", "构建 Docker 镜像") if self.language == Language.ZH else "Build Docker image",
                "commands": [
                    f"docker build -t {context.project_name.lower()}:latest .",
                ],
            })

        if self._find_docker_compose(context):
            steps.append({
                "name": f"3. {self.labels.get('start_service', '启动服务')}" if self.language == Language.ZH else "3. Start Service",
                "description": self.labels.get("start_docker_compose", "使用 Docker Compose 启动服务") if self.language == Language.ZH else "Start services using Docker Compose",
                "commands": [
                    "docker-compose up -d",
                ],
            })
        elif self._find_kubernetes_configs(context):
            steps.append({
                "name": f"3. {self.labels.get('k8s_deploy', 'Kubernetes 部署')}" if self.language == Language.ZH else "3. Kubernetes Deployment",
                "description": self.labels.get("deploy_to_k8s", "部署到 Kubernetes 集群") if self.language == Language.ZH else "Deploy to Kubernetes cluster",
                "commands": [
                    "kubectl apply -f kubernetes/",
                ],
            })
        else:
            steps.append({
                "name": f"3. {self.labels.get('start_app', '启动应用')}" if self.language == Language.ZH else "3. Start Application",
                "description": self.labels.get("start_app_desc", "启动应用服务") if self.language == Language.ZH else "Start application service",
                "commands": self._get_start_commands(context, project_language),
            })

        steps.append({
            "name": f"4. {self.labels.get('verify_deploy', '验证部署')}" if self.language == Language.ZH else "4. Verify Deployment",
            "description": self.labels.get("verify_deploy_desc", "验证服务是否正常运行") if self.language == Language.ZH else "Verify service is running properly",
            "commands": [
                "curl http://localhost:8000/health",
            ],
            "notes": self.labels.get("verify_note", "根据实际服务地址和端口调整验证命令") if self.language == Language.ZH else "Adjust verification command based on actual service address and port",
        })

        return steps

    def _get_setup_commands(self, context: DocGeneratorContext, project_language: str) -> list[str]:
        """获取环境设置命令"""
        if project_language == "python":
            if (context.project_path / "pyproject.toml").exists():
                return ["poetry install --no-dev"]
            return ["pip install -r requirements.txt"]
        elif project_language == "java":
            if (context.project_path / "pom.xml").exists():
                return ["mvn clean package -DskipTests"]
            return ["./gradlew build -x test"]
        elif project_language == "typescript":
            if (context.project_path / "yarn.lock").exists():
                return ["yarn install --production"]
            return ["npm ci --production"]
        return []

    def _get_start_commands(self, context: DocGeneratorContext, project_language: str) -> list[str]:
        """获取启动命令"""
        if project_language == "python":
            return ["python -m <module_name>", "uvicorn main:app --host 0.0.0.0 --port 8000"]
        elif project_language == "java":
            return ["java -jar target/<app-name>.jar"]
        elif project_language == "typescript":
            return ["npm start", "node dist/index.js"]
        return []

    def _extract_monitoring(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取监控配置"""
        monitoring = {}

        prometheus_files = list(context.project_path.rglob("prometheus*.yml")) + \
                          list(context.project_path.rglob("prometheus*.yaml"))
        if prometheus_files:
            monitoring["metrics"] = [
                {"name": self.labels.get("prometheus_metrics", "Prometheus 指标") if self.language == Language.ZH else "Prometheus Metrics", "description": self.labels.get("prometheus_desc", "应用暴露 Prometheus 格式的监控指标") if self.language == Language.ZH else "Application exposes Prometheus format metrics"},
            ]

        grafana_files = list(context.project_path.rglob("grafana*"))
        if grafana_files:
            monitoring.setdefault("metrics", []).append(
                {"name": self.labels.get("grafana_dashboard", "Grafana 仪表盘") if self.language == Language.ZH else "Grafana Dashboard", "description": self.labels.get("grafana_desc", "配置了 Grafana 可视化仪表盘") if self.language == Language.ZH else "Configured Grafana visualization dashboard"}
            )

        logging_config = self._detect_logging_config(context)
        if logging_config:
            monitoring["logging"] = logging_config

        alerting_files = list(context.project_path.rglob("alertmanager*.yml")) + \
                        list(context.project_path.rglob("alerting*.yml"))
        if alerting_files:
            monitoring["alerting"] = [
                {"name": self.labels.get("alert_rules", "告警规则") if self.language == Language.ZH else "Alert Rules", "condition": self.labels.get("alertmanager_desc", "配置了 AlertManager 告警规则") if self.language == Language.ZH else "Configured AlertManager alert rules"},
            ]

        return monitoring

    def _detect_logging_config(self, context: DocGeneratorContext) -> Optional[dict[str, str]]:
        """检测日志配置"""
        log_patterns = [
            ("logging.conf", self.labels.get("standard_log_config", "标准日志配置") if self.language == Language.ZH else "Standard logging config"),
            ("logback.xml", self.labels.get("logback_config", "Logback 配置 (Java)") if self.language == Language.ZH else "Logback config (Java)"),
            ("log4j2.xml", self.labels.get("log4j2_config", "Log4j2 配置 (Java)") if self.language == Language.ZH else "Log4j2 config (Java)"),
        ]

        for pattern, desc in log_patterns:
            if (context.project_path / pattern).exists():
                return {
                    "format": self.labels.get("structured_log", "结构化日志") if self.language == Language.ZH else "Structured logging",
                    "output": self.labels.get("file_console", "文件/控制台") if self.language == Language.ZH else "File/Console",
                    "level": "INFO" + (f" ({self.labels.get('configurable', '可配置')})" if self.language == Language.ZH else " (configurable)"),
                }

        return None

    def _extract_security(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取安全配置"""
        security = {}

        secrets_files = list(context.project_path.rglob(".env*")) + \
                       list(context.project_path.rglob("secrets*"))
        if secrets_files:
            security["secrets_management"] = self.labels.get("secrets_mgmt_desc", "使用环境变量管理敏感配置，建议使用专业的密钥管理服务") if self.language == Language.ZH else "Using environment variables for sensitive config, recommend using professional secrets management service"

        network_policies = list(context.project_path.rglob("network-policy*")) + \
                          list(context.project_path.rglob("networkpolicy*"))
        if network_policies:
            security["network_policies"] = [
                self.labels.get("k8s_network_policy", "配置了 Kubernetes 网络策略") if self.language == Language.ZH else "Configured Kubernetes network policies",
                self.labels.get("pod_comm_restricted", "限制了 Pod 间通信") if self.language == Language.ZH else "Restricted Pod-to-Pod communication",
            ]

        ssl_files = list(context.project_path.rglob("*ssl*")) + \
                   list(context.project_path.rglob("*tls*"))
        if ssl_files:
            security["ssl_tls"] = self.labels.get("ssl_tls_configured", "配置了 SSL/TLS 加密通信") if self.language == Language.ZH else "Configured SSL/TLS encrypted communication"

        return security

    def _generate_architecture_description(self, context: DocGeneratorContext) -> str:
        """生成部署架构描述"""
        components = []

        if self._find_dockerfile(context):
            components.append(self.labels.get("docker_deploy", "容器化部署 (Docker)") if self.language == Language.ZH else "Containerized deployment (Docker)")
        if self._find_docker_compose(context):
            components.append(self.labels.get("compose_orchestration", "多服务编排 (Docker Compose)") if self.language == Language.ZH else "Multi-service orchestration (Docker Compose)")
        if self._find_kubernetes_configs(context):
            components.append(self.labels.get("k8s_orchestration", "容器编排 (Kubernetes)") if self.language == Language.ZH else "Container orchestration (Kubernetes)")
        if (context.project_path / ".github" / "workflows").exists():
            components.append("CI/CD (GitHub Actions)")
        if (context.project_path / ".gitlab-ci.yml").exists():
            components.append("CI/CD (GitLab CI)")

        if components:
            if self.language == Language.ZH:
                return f"本项目采用 {' + '.join(components)} 的部署架构。"
            else:
                return f"This project uses {' + '.join(components)} deployment architecture."
        
        return self.labels.get("traditional_deploy", "本项目采用传统部署方式，建议考虑容器化部署以提高可移植性和可扩展性。") if self.language == Language.ZH else "This project uses traditional deployment. Consider containerization for improved portability and scalability."

    def _generate_architecture_diagram(self, context: DocGeneratorContext) -> str:
        """生成部署架构图"""
        lines = ["graph TB"]

        lines.append(f"    App[{context.project_name}]")

        if self._find_dockerfile(context):
            docker_label = self.labels.get("docker_container", "Docker 容器") if self.language == Language.ZH else "Docker Container"
            lines.append(f"    Docker[{docker_label}]")
            lines.append("    App --> Docker")

        if self._find_docker_compose(context):
            lines.append("    Compose[Docker Compose]")
            lines.append("    Docker --> Compose")

        if self._find_kubernetes_configs(context):
            k8s_label = self.labels.get("k8s_cluster", "Kubernetes 集群") if self.language == Language.ZH else "Kubernetes Cluster"
            lines.append(f"    K8s[{k8s_label}]")
            lines.append("    Docker --> K8s")

        if (context.project_path / ".github" / "workflows").exists():
            lines.append("    GHA[GitHub Actions]")
            lines.append("    GHA --> App")

        return "\n".join(lines)

    def _extract_troubleshooting(self, context: DocGeneratorContext) -> list[dict[str, Any]]:
        """提取故障排查信息"""
        troubleshooting = []

        troubleshooting.extend([
            {
                "problem": self.labels.get("container_start_fail", "容器启动失败") if self.language == Language.ZH else "Container startup failure",
                "symptom": self.labels.get("container_fail_symptom", "Docker 容器无法正常启动或频繁重启") if self.language == Language.ZH else "Docker container fails to start or restarts frequently",
                "cause": self.labels.get("container_fail_cause", "配置错误、资源不足或依赖服务不可用") if self.language == Language.ZH else "Configuration error, insufficient resources, or unavailable dependencies",
                "solution": [
                    self.labels.get("check_container_logs", "检查容器日志: docker logs <container-id>") if self.language == Language.ZH else "Check container logs: docker logs <container-id>",
                    self.labels.get("verify_env_vars", "验证环境变量配置是否正确") if self.language == Language.ZH else "Verify environment variable configuration",
                    self.labels.get("check_port_conflict", "检查端口是否被占用") if self.language == Language.ZH else "Check for port conflicts",
                    self.labels.get("verify_deps", "确认依赖服务是否正常运行") if self.language == Language.ZH else "Verify dependent services are running",
                ],
            },
            {
                "problem": self.labels.get("service_unreachable", "服务无法访问") if self.language == Language.ZH else "Service unreachable",
                "symptom": self.labels.get("service_unreachable_symptom", "服务部署成功但无法通过外部访问") if self.language == Language.ZH else "Service deployed but not accessible externally",
                "cause": self.labels.get("service_unreachable_cause", "网络配置错误或端口映射问题") if self.language == Language.ZH else "Network misconfiguration or port mapping issue",
                "solution": [
                    self.labels.get("check_port_mapping", "检查端口映射配置") if self.language == Language.ZH else "Check port mapping configuration",
                    self.labels.get("verify_firewall", "验证防火墙规则") if self.language == Language.ZH else "Verify firewall rules",
                    self.labels.get("check_listen_addr", "确认服务监听地址是否正确 (0.0.0.0 vs 127.0.0.1)") if self.language == Language.ZH else "Verify service listen address (0.0.0.0 vs 127.0.0.1)",
                    self.labels.get("check_lb", "检查负载均衡器配置") if self.language == Language.ZH else "Check load balancer configuration",
                ],
            },
            {
                "problem": self.labels.get("oom", "内存不足") if self.language == Language.ZH else "Out of memory",
                "symptom": self.labels.get("oom_symptom", "服务运行缓慢或崩溃") if self.language == Language.ZH else "Service runs slowly or crashes",
                "cause": self.labels.get("oom_cause", "内存配置不足或内存泄漏") if self.language == Language.ZH else "Insufficient memory allocation or memory leak",
                "solution": [
                    self.labels.get("check_mem_limit", "检查容器内存限制配置") if self.language == Language.ZH else "Check container memory limits",
                    self.labels.get("analyze_mem", "分析内存使用情况") if self.language == Language.ZH else "Analyze memory usage",
                    self.labels.get("optimize_mem", "优化应用内存使用") if self.language == Language.ZH else "Optimize application memory usage",
                    self.labels.get("increase_mem", "增加内存配额") if self.language == Language.ZH else "Increase memory quota",
                ],
            },
        ])

        return troubleshooting

    def _extract_best_practices(self, context: DocGeneratorContext) -> list[str]:
        """提取最佳实践"""
        practices = [
            self.labels.get("bp_env_vars", "使用环境变量管理配置，避免硬编码敏感信息") if self.language == Language.ZH else "Use environment variables for configuration, avoid hardcoding sensitive info",
            self.labels.get("bp_health_check", "实施健康检查机制，确保服务可用性") if self.language == Language.ZH else "Implement health checks to ensure service availability",
            self.labels.get("bp_log_agg", "配置日志聚合，便于问题排查") if self.language == Language.ZH else "Configure log aggregation for easier troubleshooting",
            self.labels.get("bp_resource_limit", "设置资源限制，防止资源耗尽") if self.language == Language.ZH else "Set resource limits to prevent resource exhaustion",
            self.labels.get("bp_deploy_strategy", "使用蓝绿部署或金丝雀发布，降低发布风险") if self.language == Language.ZH else "Use blue-green or canary deployment to reduce release risk",
        ]

        if self._find_dockerfile(context):
            practices.extend([
                self.labels.get("bp_multi_stage", "使用多阶段构建优化镜像大小") if self.language == Language.ZH else "Use multi-stage builds to optimize image size",
                self.labels.get("bp_update_base", "定期更新基础镜像版本") if self.language == Language.ZH else "Regularly update base image versions",
                self.labels.get("bp_dockerignore", "使用 .dockerignore 排除不必要的文件") if self.language == Language.ZH else "Use .dockerignore to exclude unnecessary files",
            ])

        if self._find_kubernetes_configs(context):
            practices.extend([
                self.labels.get("bp_pod_anti", "配置 Pod 反亲和性，提高可用性") if self.language == Language.ZH else "Configure Pod anti-affinity for high availability",
                self.labels.get("bp_configmap", "使用 ConfigMap 和 Secret 管理配置") if self.language == Language.ZH else "Use ConfigMap and Secret for configuration management",
                self.labels.get("bp_resource_req", "设置资源请求和限制") if self.language == Language.ZH else "Set resource requests and limits",
            ])

        return practices

    def _extract_backup(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取备份配置"""
        backup = {}

        backup_scripts = list(context.project_path.rglob("backup*")) + \
                        list(context.project_path.rglob("*backup*"))
        if backup_scripts:
            backup["strategy"] = self.labels.get("has_backup_script", "项目包含备份脚本") if self.language == Language.ZH else "Project includes backup scripts"
            backup["commands"] = ["./scripts/backup.sh"]

        if (context.project_path / "docker-compose.yml").exists():
            backup.setdefault("commands", []).extend([
                "docker-compose exec db mysqldump -u root -p database > backup.sql",
            ])
            backup.setdefault("restore_commands", []).extend([
                "docker-compose exec -T db mysql -u root -p database < backup.sql",
            ])

        if not backup:
            backup["strategy"] = self.labels.get("recommend_backup", "建议配置定期备份策略") if self.language == Language.ZH else "Recommend configuring regular backup strategy"
            backup["schedule"] = self.labels.get("backup_schedule_default", "每日凌晨 2:00 执行备份") if self.language == Language.ZH else "Daily backup at 2:00 AM"

        return backup

    def _extract_scaling(self, context: DocGeneratorContext) -> dict[str, Any]:
        """提取扩缩容配置"""
        scaling = {}

        if self._find_kubernetes_configs(context):
            hpa_files = list(context.project_path.rglob("hpa*")) + \
                       list(context.project_path.rglob("*autoscaler*"))
            if hpa_files:
                scaling["auto_scaling"] = self.labels.get("hpa_configured", "配置了 Kubernetes Horizontal Pod Autoscaler (HPA)") if self.language == Language.ZH else "Configured Kubernetes Horizontal Pod Autoscaler (HPA)"
            else:
                scaling["horizontal"] = self.labels.get("hpa_available", "可通过 Kubernetes HPA 实现水平扩展") if self.language == Language.ZH else "Horizontal scaling available via Kubernetes HPA"

            scaling["vertical"] = self.labels.get("vertical_scaling_desc", "可通过调整 Pod 资源限制实现垂直扩展") if self.language == Language.ZH else "Vertical scaling by adjusting Pod resource limits"

        if self._find_docker_compose(context):
            scaling["horizontal"] = self.labels.get("compose_scaling", "可通过 docker-compose scale 或 Docker Swarm 实现水平扩展") if self.language == Language.ZH else "Horizontal scaling via docker-compose scale or Docker Swarm"

        return scaling

    async def _enhance_with_llm(
        self,
        context: DocGeneratorContext,
        deploy_data: dict[str, Any],
        llm_client: Any,
    ) -> dict[str, Any]:
        """使用 LLM 增强部署文档"""
        enhanced = {}

        has_docker = bool(deploy_data.get("containerization", {}).get("docker"))
        has_k8s = bool(deploy_data.get("containerization", {}).get("kubernetes"))
        has_cicd = bool(deploy_data.get("cicd", {}).get("platform"))

        if self.language == Language.ZH:
            prompt = f"""基于以下部署信息，提供部署最佳实践建议：

项目: {context.project_name}
容器化: {'是' if has_docker else '否'}
Kubernetes: {'是' if has_k8s else '否'}
CI/CD: {deploy_data.get('cicd', {}).get('platform', '未配置')}
环境数量: {len(deploy_data.get('environments', []))}

请以 JSON 格式返回：
{{
    "deployment_tips": ["部署技巧1", "部署技巧2"],
    "security_recommendations": ["安全建议1", "安全建议2"],
    "performance_tuning": ["性能调优建议1", "性能调优建议2"],
    "cost_optimization": ["成本优化建议1", "成本优化建议2"]
}}
"""
        else:
            prompt = f"""Based on the following deployment information, provide deployment best practice recommendations:

Project: {context.project_name}
Containerized: {'Yes' if has_docker else 'No'}
Kubernetes: {'Yes' if has_k8s else 'No'}
CI/CD: {deploy_data.get('cicd', {}).get('platform', 'Not configured')}
Environments: {len(deploy_data.get('environments', []))}

Please return in JSON format:
{{
    "deployment_tips": ["tip1", "tip2"],
    "security_recommendations": ["recommendation1", "recommendation2"],
    "performance_tuning": ["tuning1", "tuning2"],
    "cost_optimization": ["optimization1", "optimization2"]
}}
"""

        try:
            response = await llm_client.agenerate(prompt)
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                result = json.loads(response[start:end+1])
                
                if result.get("deployment_tips"):
                    enhanced["best_practices"] = deploy_data.get("best_practices", []) + result["deployment_tips"]
                
                if result.get("security_recommendations"):
                    security = deploy_data.get("security", {})
                    security.setdefault("recommendations", []).extend(result["security_recommendations"])
                    enhanced["security"] = security

        except Exception:
            pass

        return enhanced


try:
    import yaml
except ImportError:
    yaml = None

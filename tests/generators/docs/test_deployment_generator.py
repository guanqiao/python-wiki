"""
部署管理文档生成器测试
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiki.generators.docs.deployment_generator import DeploymentGenerator
from pywiki.generators.docs.base import DocGeneratorContext, DocType
from pywiki.config.models import Language


class TestDeploymentGeneratorInit:
    """DeploymentGenerator 初始化测试"""

    def test_init_default(self):
        """测试默认初始化"""
        generator = DeploymentGenerator()

        assert generator.doc_type == DocType.DEPLOYMENT
        assert generator.template_name == "deployment.md.j2"
        assert generator.language == Language.ZH

    def test_init_with_language(self):
        """测试带语言初始化"""
        generator = DeploymentGenerator(language=Language.EN)

        assert generator.language == Language.EN


class TestDeploymentGeneratorDockerfile:
    """Dockerfile 检测和解析测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_find_dockerfile_standard(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找标准 Dockerfile"""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text("FROM python:3.10\n")

        result = generator._find_dockerfile(context)

        assert result is not None
        assert result.name == "Dockerfile"

    def test_find_dockerfile_prod(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找生产 Dockerfile"""
        dockerfile = tmp_path / "Dockerfile.prod"
        dockerfile.write_text("FROM python:3.10\n")

        result = generator._find_dockerfile(context)

        assert result is not None

    def test_find_dockerfile_nested(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找嵌套 Dockerfile"""
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        dockerfile = docker_dir / "Dockerfile"
        dockerfile.write_text("FROM python:3.10\n")

        result = generator._find_dockerfile(context)

        assert result is not None

    def test_find_dockerfile_not_found(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试未找到 Dockerfile"""
        result = generator._find_dockerfile(context)

        assert result is None

    def test_parse_dockerfile_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试解析基本 Dockerfile"""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text('''
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "main.py"]
''')

        result = generator._parse_dockerfile(context, dockerfile)

        assert "dockerfile_path" in result
        assert "build_command" in result
        assert "run_command" in result
        assert "8000" in result["exposed_ports"]

    def test_parse_dockerfile_multiple_ports(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试解析多端口 Dockerfile"""
        dockerfile = tmp_path / "Dockerfile"
        dockerfile.write_text('''
FROM python:3.10
EXPOSE 8000
EXPOSE 8080
EXPOSE 443
''')

        result = generator._parse_dockerfile(context, dockerfile)

        assert len(result["exposed_ports"]) == 3


class TestDeploymentGeneratorDockerCompose:
    """Docker Compose 检测和解析测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_find_docker_compose_standard(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找标准 docker-compose 文件"""
        compose = tmp_path / "docker-compose.yml"
        compose.write_text("version: '3'\n")

        result = generator._find_docker_compose(context)

        assert result is not None
        assert result.name == "docker-compose.yml"

    def test_find_docker_compose_yaml(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找 .yaml 扩展名"""
        compose = tmp_path / "docker-compose.yaml"
        compose.write_text("version: '3'\n")

        result = generator._find_docker_compose(context)

        assert result is not None

    def test_find_docker_compose_not_found(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试未找到 docker-compose 文件"""
        result = generator._find_docker_compose(context)

        assert result is None

    def test_parse_docker_compose_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试解析基本 docker-compose"""
        compose = tmp_path / "docker-compose.yml"
        compose.write_text('''
version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "8000:80"
  db:
    image: postgres:14
    ports:
      - "5432:5432"
''')

        result = generator._parse_docker_compose(context, compose)

        assert "file_path" in result
        assert "services" in result
        assert "commands" in result


class TestDeploymentGeneratorKubernetes:
    """Kubernetes 配置检测和解析测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_find_kubernetes_configs_standard(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找标准 K8s 配置目录"""
        k8s_dir = tmp_path / "kubernetes"
        k8s_dir.mkdir()
        deployment = k8s_dir / "deployment.yaml"
        deployment.write_text("apiVersion: apps/v1\n")

        result = generator._find_kubernetes_configs(context)

        assert len(result) >= 1

    def test_find_kubernetes_configs_k8s_dir(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试查找 k8s 目录"""
        k8s_dir = tmp_path / "k8s"
        k8s_dir.mkdir()
        deployment = k8s_dir / "deployment.yaml"
        deployment.write_text("apiVersion: apps/v1\n")

        result = generator._find_kubernetes_configs(context)

        assert len(result) >= 1

    def test_find_kubernetes_configs_not_found(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试未找到 K8s 配置"""
        result = generator._find_kubernetes_configs(context)

        assert result == []

    def test_parse_kubernetes_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试解析基本 K8s 配置"""
        k8s_dir = tmp_path / "kubernetes"
        k8s_dir.mkdir()
        deployment = k8s_dir / "deployment.yaml"
        deployment.write_text('''
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 3
''')

        result = generator._parse_kubernetes(context, [deployment])

        assert "config_path" in result
        assert "resources" in result
        assert "commands" in result


class TestDeploymentGeneratorCICD:
    """CI/CD 配置检测和解析测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_cicd_github_actions(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 GitHub Actions 配置"""
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        workflow = workflows_dir / "ci.yml"
        workflow.write_text('''
name: CI
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
''')

        result = generator._extract_cicd(context)

        assert result.get("platform") == "GitHub Actions"

    def test_extract_cicd_gitlab_ci(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 GitLab CI 配置"""
        gitlab_ci = tmp_path / ".gitlab-ci.yml"
        gitlab_ci.write_text('''
stages:
  - build
  - test
build:
  stage: build
''')

        result = generator._extract_cicd(context)

        assert result.get("platform") == "GitLab CI"

    def test_extract_cicd_jenkins(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 Jenkins 配置"""
        jenkinsfile = tmp_path / "Jenkinsfile"
        jenkinsfile.write_text('''
pipeline {
    stages {
        stage('Build') {}
        stage('Test') {}
    }
}
''')

        result = generator._extract_cicd(context)

        assert result.get("platform") == "Jenkins"

    def test_extract_cicd_not_found(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试未找到 CI/CD 配置"""
        result = generator._extract_cicd(context)

        assert result == {}

    def test_parse_github_actions_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试解析 GitHub Actions"""
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        workflow = workflows_dir / "test.yml"
        workflow.write_text('''
name: Test
on:
  push:
  pull_request:
jobs:
  build:
  test:
''')

        result = generator._parse_github_actions(context, workflows_dir)

        assert result["platform"] == "GitHub Actions"
        assert len(result["pipelines"]) >= 1


class TestDeploymentGeneratorEnvironments:
    """环境配置提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_environments_with_env_file(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 .env 文件环境配置"""
        env_file = tmp_path / ".env.example"
        env_file.write_text('''
DATABASE_URL=postgresql://localhost:5432/db
SECRET_KEY=your-secret-key
DEBUG=false
''')

        result = generator._extract_environments(context)

        assert len(result) >= 1

    def test_extract_environments_with_multiple_envs(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取多个环境配置"""
        (tmp_path / ".env.development").write_text("DEBUG=true\n")
        (tmp_path / ".env.production").write_text("DEBUG=false\n")

        result = generator._extract_environments(context)

        assert len(result) >= 1

    def test_extract_environments_default(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试默认环境配置"""
        result = generator._extract_environments(context)

        assert len(result) >= 1

    def test_parse_env_file_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试解析环境变量文件"""
        env_file = tmp_path / ".env"
        env_file.write_text('''
# Database config
DATABASE_URL=postgresql://localhost:5432/db
SECRET_KEY=
DEBUG=true
''')

        result = generator._parse_env_file(context, env_file, "Test Environment")

        assert result is not None
        assert result["name"] == "Test Environment"
        assert len(result["variables"]) >= 2


class TestDeploymentGeneratorPrerequisites:
    """前置条件提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_prerequisites_python(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 Python 项目前置条件"""
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\n")

        result = generator._extract_prerequisites(context, "python")

        assert any("Python" in p for p in result)

    def test_extract_prerequisites_with_docker(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带 Docker 的前置条件"""
        (tmp_path / "Dockerfile").write_text("FROM python:3.10\n")

        result = generator._extract_prerequisites(context, "python")

        assert any("Docker" in p for p in result)

    def test_extract_prerequisites_java(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取 Java 项目前置条件"""
        result = generator._extract_prerequisites(context, "java")

        assert any("JDK" in p for p in result)

    def test_extract_prerequisites_typescript(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取 TypeScript 项目前置条件"""
        result = generator._extract_prerequisites(context, "typescript")

        assert any("Node" in p for p in result)


class TestDeploymentGeneratorSteps:
    """部署步骤提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_deployment_steps_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取基本部署步骤"""
        result = generator._extract_deployment_steps(context, "python")

        assert len(result) >= 3
        step_names = [s["name"] for s in result]
        assert any("环境" in name or "Environment" in name for name in step_names)

    def test_extract_deployment_steps_with_docker(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带 Docker 的部署步骤"""
        (tmp_path / "Dockerfile").write_text("FROM python:3.10\n")

        result = generator._extract_deployment_steps(context, "python")

        assert any("镜像" in s["name"] or "Image" in s["name"] for s in result)

    def test_extract_deployment_steps_with_docker_compose(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带 Docker Compose 的部署步骤"""
        (tmp_path / "Dockerfile").write_text("FROM python:3.10\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        result = generator._extract_deployment_steps(context, "python")

        assert any("服务" in s["name"] or "Service" in s["name"] for s in result)

    def test_get_setup_commands_python_poetry(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试获取 Python Poetry 设置命令"""
        (tmp_path / "pyproject.toml").write_text("[tool.poetry]\n")

        result = generator._get_setup_commands(context, "python")

        assert any("poetry" in cmd for cmd in result)

    def test_get_setup_commands_python_pip(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试获取 Python pip 设置命令"""
        result = generator._get_setup_commands(context, "python")

        assert any("pip" in cmd for cmd in result)

    def test_get_start_commands_python(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试获取 Python 启动命令"""
        result = generator._get_start_commands(context, "python")

        assert len(result) >= 1

    def test_get_start_commands_java(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试获取 Java 启动命令"""
        result = generator._get_start_commands(context, "java")

        assert any("java" in cmd for cmd in result)


class TestDeploymentGeneratorMonitoring:
    """监控配置提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_monitoring_with_prometheus(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 Prometheus 监控配置"""
        prometheus = tmp_path / "prometheus.yml"
        prometheus.write_text("global:\n  scrape_interval: 15s\n")

        result = generator._extract_monitoring(context)

        assert "metrics" in result

    def test_extract_monitoring_empty(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取空监控配置"""
        result = generator._extract_monitoring(context)

        assert result == {}

    def test_detect_logging_config(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试检测日志配置"""
        logging_conf = tmp_path / "logging.conf"
        logging_conf.write_text("[loggers]\n")

        result = generator._detect_logging_config(context)

        assert result is not None


class TestDeploymentGeneratorSecurity:
    """安全配置提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_security_with_env(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带环境变量的安全配置"""
        (tmp_path / ".env").write_text("SECRET_KEY=secret\n")

        result = generator._extract_security(context)

        assert "secrets_management" in result

    def test_extract_security_empty(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取空安全配置"""
        result = generator._extract_security(context)

        assert result == {}


class TestDeploymentGeneratorArchitecture:
    """架构描述生成测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_generate_architecture_description_with_docker(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试生成带 Docker 的架构描述"""
        (tmp_path / "Dockerfile").write_text("FROM python:3.10\n")

        result = generator._generate_architecture_description(context)

        assert "Docker" in result or "容器" in result

    def test_generate_architecture_description_with_github_actions(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试生成带 GitHub Actions 的架构描述"""
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)

        result = generator._generate_architecture_description(context)

        assert "GitHub Actions" in result

    def test_generate_architecture_description_empty(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试生成空架构描述"""
        result = generator._generate_architecture_description(context)

        assert len(result) > 0

    def test_generate_architecture_diagram_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试生成基本架构图"""
        result = generator._generate_architecture_diagram(context)

        assert "graph" in result
        assert "test_project" in result


class TestDeploymentGeneratorTroubleshooting:
    """故障排查信息提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_troubleshooting(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取故障排查信息"""
        result = generator._extract_troubleshooting(context)

        assert len(result) >= 1
        assert all("problem" in t for t in result)
        assert all("solution" in t for t in result)


class TestDeploymentGeneratorBestPractices:
    """最佳实践提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_best_practices_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取基本最佳实践"""
        result = generator._extract_best_practices(context)

        assert len(result) >= 3

    def test_extract_best_practices_with_docker(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带 Docker 的最佳实践"""
        (tmp_path / "Dockerfile").write_text("FROM python:3.10\n")

        result = generator._extract_best_practices(context)

        assert any("镜像" in p or "image" in p.lower() for p in result)

    def test_extract_best_practices_with_k8s(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带 K8s 的最佳实践"""
        k8s_dir = tmp_path / "kubernetes"
        k8s_dir.mkdir()
        (k8s_dir / "deployment.yaml").write_text("apiVersion: apps/v1\n")

        result = generator._extract_best_practices(context)

        assert any("Pod" in p or "ConfigMap" in p for p in result)


class TestDeploymentGeneratorBackup:
    """备份配置提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_backup_default(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试提取默认备份配置"""
        result = generator._extract_backup(context)

        assert "strategy" in result

    def test_extract_backup_with_docker_compose(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取带 Docker Compose 的备份配置"""
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        result = generator._extract_backup(context)

        assert "commands" in result


class TestDeploymentGeneratorScaling:
    """扩缩容配置提取测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    def test_extract_scaling_with_k8s(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 K8s 扩缩容配置"""
        k8s_dir = tmp_path / "kubernetes"
        k8s_dir.mkdir()
        (k8s_dir / "deployment.yaml").write_text("apiVersion: apps/v1\n")

        result = generator._extract_scaling(context)

        assert "horizontal" in result or "vertical" in result

    def test_extract_scaling_with_docker_compose(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试提取 Docker Compose 扩缩容配置"""
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        result = generator._extract_scaling(context)

        assert "horizontal" in result


class TestDeploymentGeneratorGenerate:
    """文档生成测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator()

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.ZH,
        )

    @pytest.mark.asyncio
    async def test_generate_basic(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试基本生成"""
        result = await generator.generate(context)

        assert result.success
        assert result.doc_type == DocType.DEPLOYMENT
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_generate_with_pyproject(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试带 pyproject.toml 的生成"""
        (tmp_path / "pyproject.toml").write_text('[tool.poetry]\nname = "test"\n')

        result = await generator.generate(context)

        assert result.success

    @pytest.mark.asyncio
    async def test_generate_with_docker(self, generator: DeploymentGenerator, context: DocGeneratorContext, tmp_path: Path):
        """测试带 Docker 配置的生成"""
        (tmp_path / "Dockerfile").write_text("FROM python:3.10\nEXPOSE 8000\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\nservices:\n  web:\n    image: nginx\n")

        result = await generator.generate(context)

        assert result.success
        assert "Docker" in result.content or "容器" in result.content

    @pytest.mark.asyncio
    async def test_generate_with_llm_client(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试带 LLM 客户端的生成"""
        mock_llm = AsyncMock()
        mock_llm.agenerate.return_value = '{"deployment_tips": ["tip1"], "security_recommendations": ["rec1"]}'

        context.metadata["llm_client"] = mock_llm

        result = await generator.generate(context)

        assert result.success


class TestDeploymentGeneratorEnglish:
    """英文生成测试"""

    @pytest.fixture
    def generator(self):
        return DeploymentGenerator(language=Language.EN)

    @pytest.fixture
    def context(self, tmp_path: Path):
        return DocGeneratorContext(
            project_path=tmp_path,
            project_name="test_project",
            language=Language.EN,
        )

    @pytest.mark.asyncio
    async def test_generate_english(self, generator: DeploymentGenerator, context: DocGeneratorContext):
        """测试英文生成"""
        result = await generator.generate(context)

        assert result.success

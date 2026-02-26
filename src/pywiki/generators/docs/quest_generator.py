"""
Quest Mode 设计文档生成器
生成详细的设计文档，包含流程图、架构图、技术选型等
对标 Qoder 的 Quest Mode 设计文档
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pywiki.generators.docs.base import (
    BaseDocGenerator,
    DocGeneratorContext,
    DocGeneratorResult,
    DocType,
)
from pywiki.config.models import Language


@dataclass
class QuestTask:
    """Quest 任务"""
    id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed, failed
    dependencies: list[str] = field(default_factory=list)
    estimated_time: str = ""
    actual_time: str = ""
    output_files: list[str] = field(default_factory=list)


@dataclass
class QuestDesignDoc:
    """Quest 设计文档"""
    title: str
    description: str
    requirements: list[str] = field(default_factory=list)
    tech_stack: dict[str, str] = field(default_factory=dict)
    architecture: dict[str, Any] = field(default_factory=dict)
    tasks: list[QuestTask] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class QuestDesignDocGenerator(BaseDocGenerator):
    """
    Quest Mode 设计文档生成器
    
    生成类似 Qoder Quest Mode 的设计文档，包含：
    - 需求分析
    - 技术栈选择
    - 架构设计
    - 任务拆解
    - 流程图
    """

    doc_type = DocType.ARCHITECTURE
    template_name = "quest_design.md.j2"

    def __init__(self, language: Language = Language.ZH, template_dir: Optional[Path] = None):
        super().__init__(language, template_dir)

    async def generate(self, context: DocGeneratorContext) -> DocGeneratorResult:
        """生成 Quest 设计文档"""
        try:
            # 从上下文提取信息
            design_doc = self._create_design_doc(context)

            # 生成文档内容
            content = self._generate_document(design_doc)

            return self.create_result(
                content=content,
                context=context,
                success=True,
                message="成功生成 Quest 设计文档",
                metadata={
                    "task_count": len(design_doc.tasks),
                    "tech_stack": list(design_doc.tech_stack.keys()),
                },
            )

        except Exception as e:
            return self.create_result(
                content="",
                context=context,
                success=False,
                message=f"生成失败: {str(e)}",
            )

    def _create_design_doc(self, context: DocGeneratorContext) -> QuestDesignDoc:
        """从项目信息创建设计文档"""
        parse_result = context.parse_result
        project_name = context.project_name

        # 提取技术栈
        tech_stack = self._extract_tech_stack(parse_result)

        # 提取架构信息
        architecture = self._extract_architecture(parse_result)

        # 生成任务列表
        tasks = self._generate_tasks(parse_result, project_name)

        # 识别风险
        risks = self._identify_risks(parse_result)

        return QuestDesignDoc(
            title=f"{project_name} - 设计文档",
            description=f"{project_name} 项目的详细设计文档",
            requirements=self._extract_requirements(parse_result),
            tech_stack=tech_stack,
            architecture=architecture,
            tasks=tasks,
            risks=risks,
        )

    def _extract_tech_stack(self, parse_result) -> dict[str, str]:
        """提取技术栈信息"""
        tech_stack = {}

        if not parse_result:
            return tech_stack

        # 检测 Web 框架
        for module in parse_result.modules:
            for imp in module.imports:
                module_name = imp.module.split(".")[0].lower()

                if module_name == "fastapi":
                    tech_stack["backend_framework"] = "FastAPI"
                    tech_stack["language"] = "Python 3.8+"
                elif module_name == "flask":
                    tech_stack["backend_framework"] = "Flask"
                    tech_stack["language"] = "Python 3.7+"
                elif module_name == "django":
                    tech_stack["backend_framework"] = "Django"
                    tech_stack["language"] = "Python 3.8+"
                elif module_name == "sqlalchemy":
                    tech_stack["orm"] = "SQLAlchemy"
                elif module_name == "pydantic":
                    tech_stack["validation"] = "Pydantic"
                elif module_name == "redis":
                    tech_stack["cache"] = "Redis"
                elif module_name == "kafka":
                    tech_stack["message_queue"] = "Apache Kafka"
                elif module_name == "celery":
                    tech_stack["task_queue"] = "Celery"
                elif module_name == "pytest":
                    tech_stack["testing"] = "pytest"

        # 默认技术栈
        if "language" not in tech_stack:
            tech_stack["language"] = "Python 3.8+"

        return tech_stack

    def _extract_architecture(self, parse_result) -> dict[str, Any]:
        """提取架构信息"""
        architecture = {
            "pattern": "Layered Architecture",
            "layers": [],
            "components": [],
        }

        if not parse_result:
            return architecture

        # 检测架构模式
        layers = {"controller": [], "service": [], "repository": [], "model": []}

        for module in parse_result.modules:
            name_lower = module.name.lower()

            for layer_name in layers:
                if layer_name in name_lower:
                    layers[layer_name].append(module.name)

        # 如果检测到分层
        if any(layers.values()):
            architecture["pattern"] = "Layered Architecture"
            architecture["layers"] = [
                {"name": name, "modules": modules}
                for name, modules in layers.items()
                if modules
            ]

        # 提取组件
        for module in parse_result.modules:
            for cls in module.classes:
                cls_name = cls.name
                if any(x in cls_name.lower() for x in ["controller", "service", "repository"]):
                    architecture["components"].append({
                        "name": cls_name,
                        "type": self._detect_component_type(cls_name),
                        "module": module.name,
                    })

        return architecture

    def _detect_component_type(self, name: str) -> str:
        """检测组件类型"""
        name_lower = name.lower()
        if "controller" in name_lower:
            return "Controller"
        elif "service" in name_lower:
            return "Service"
        elif "repository" in name_lower or "repo" in name_lower:
            return "Repository"
        elif "model" in name_lower or "entity" in name_lower:
            return "Model"
        else:
            return "Component"

    def _generate_tasks(self, parse_result, project_name: str) -> list[QuestTask]:
        """生成任务列表"""
        tasks = []

        # 任务 1: 环境搭建
        tasks.append(QuestTask(
            id="task_001",
            title="环境搭建与依赖安装",
            description="配置开发环境，安装项目依赖",
            status="pending",
            estimated_time="30分钟",
        ))

        # 任务 2: 数据库初始化
        if parse_result:
            has_db = any(
                any(imp.module.lower().startswith(("sqlalchemy", "pymongo", "redis"))
                    for imp in module.imports)
                for module in parse_result.modules
            )
            if has_db:
                tasks.append(QuestTask(
                    id="task_002",
                    title="数据库初始化",
                    description="创建数据库表结构和初始数据",
                    status="pending",
                    dependencies=["task_001"],
                    estimated_time="20分钟",
                ))

        # 任务 3: 核心功能实现
        task_id = 3
        for module in (parse_result.modules if parse_result else [])[:5]:
            if any(x in module.name.lower() for x in ["service", "controller", "handler"]):
                tasks.append(QuestTask(
                    id=f"task_{task_id:03d}",
                    title=f"实现 {module.name} 模块",
                    description=f"开发 {module.name} 的核心功能",
                    status="pending",
                    dependencies=["task_001", "task_002"] if has_db else ["task_001"],
                    estimated_time="1小时",
                ))
                task_id += 1

        # 任务 N: 测试
        tasks.append(QuestTask(
            id=f"task_{task_id:03d}",
            title="单元测试与集成测试",
            description="编写并执行测试用例",
            status="pending",
            dependencies=[f"task_{i:03d}" for i in range(3, task_id)],
            estimated_time="1小时",
        ))

        return tasks

    def _identify_risks(self, parse_result) -> list[str]:
        """识别项目风险"""
        risks = []

        if not parse_result:
            return risks

        # 检查依赖复杂度
        total_imports = sum(len(m.imports) for m in parse_result.modules)
        if total_imports > 100:
            risks.append("项目依赖较多，可能存在依赖冲突风险")

        # 检查循环依赖
        # 简化检查：模块数量过多
        if len(parse_result.modules) > 50:
            risks.append("模块数量较多，需要关注模块间耦合")

        # 检查是否有测试
        has_tests = any("test" in m.name.lower() for m in parse_result.modules)
        if not has_tests:
            risks.append("未检测到测试代码，建议补充单元测试")

        return risks

    def _extract_requirements(self, parse_result) -> list[str]:
        """提取需求"""
        requirements = []

        if not parse_result:
            return requirements

        # 基于模块功能推断需求
        for module in parse_result.modules:
            name_lower = module.name.lower()

            if any(x in name_lower for x in ["auth", "login", "user"]):
                requirements.append("用户认证与授权")
            if any(x in name_lower for x in ["api", "route", "endpoint"]):
                requirements.append("RESTful API 接口")
            if any(x in name_lower for x in ["db", "model", "entity"]):
                requirements.append("数据持久化")
            if any(x in name_lower for x in ["cache", "redis"]):
                requirements.append("缓存机制")
            if any(x in name_lower for x in ["queue", "task", "worker"]):
                requirements.append("异步任务处理")

        # 去重
        return list(set(requirements)) if requirements else ["核心业务功能实现"]

    def _generate_document(self, doc: QuestDesignDoc) -> str:
        """生成设计文档内容"""
        if self.language == Language.ZH:
            return self._generate_zh_document(doc)
        else:
            return self._generate_en_document(doc)

    def _generate_zh_document(self, doc: QuestDesignDoc) -> str:
        """生成中文设计文档"""
        lines = [
            f"# {doc.title}",
            "",
            f"> 创建时间: {doc.created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 1. 项目概述",
            "",
            doc.description,
            "",
            "## 2. 需求分析",
            "",
        ]

        for i, req in enumerate(doc.requirements, 1):
            lines.append(f"{i}. {req}")
        lines.append("")

        lines.extend([
            "## 3. 技术栈",
            "",
        ])

        for category, tech in doc.tech_stack.items():
            lines.append(f"- **{category}**: {tech}")
        lines.append("")

        lines.extend([
            "## 4. 架构设计",
            "",
            f"### 架构模式: {doc.architecture.get('pattern', 'Layered Architecture')}",
            "",
        ])

        if doc.architecture.get("layers"):
            lines.append("#### 分层结构")
            lines.append("")
            for layer in doc.architecture["layers"]:
                lines.append(f"- **{layer['name'].capitalize()} Layer**: {', '.join(layer['modules'][:3])}")
            lines.append("")

        if doc.architecture.get("components"):
            lines.append("#### 核心组件")
            lines.append("")
            lines.append("```mermaid")
            lines.append("graph TB")
            for comp in doc.architecture["components"][:10]:
                lines.append(f"    {comp['name']}[{comp['name']}]")
            lines.append("```")
            lines.append("")

        lines.extend([
            "## 5. 任务拆解",
            "",
            "```mermaid",
            "gantt",
            "    title 项目任务进度",
            "    dateFormat YYYY-MM-DD",
        ])

        start_date = datetime.now()
        for i, task in enumerate(doc.tasks):
            date_str = (start_date.strftime("%Y-%m-%d"))
            lines.append(f"    {task.title} :a{i}, {date_str}, 1d")
        lines.append("```")
        lines.append("")

        lines.append("### 任务详情")
        lines.append("")
        for task in doc.tasks:
            status_icon = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "failed": "❌"}.get(
                task.status, "❓"
            )
            lines.append(f"#### {status_icon} {task.title}")
            lines.append(f"- **ID**: {task.id}")
            lines.append(f"- **描述**: {task.description}")
            lines.append(f"- **状态**: {task.status}")
            if task.dependencies:
                lines.append(f"- **依赖**: {', '.join(task.dependencies)}")
            if task.estimated_time:
                lines.append(f"- **预计时间**: {task.estimated_time}")
            lines.append("")

        if doc.risks:
            lines.extend([
                "## 6. 风险识别",
                "",
            ])
            for risk in doc.risks:
                lines.append(f"- ⚠️ {risk}")
            lines.append("")

        lines.extend([
            "## 7. 数据流图",
            "",
            "```mermaid",
            "graph LR",
            "    A[客户端] -->|HTTP请求| B[API Gateway]",
            "    B --> C[业务服务]",
            "    C -->|查询/写入| D[数据库]",
            "    C -->|缓存| E[Redis]",
            "    C -->|异步任务| F[消息队列]",
            "```",
            "",
            "---",
            "",
            "*本文档由 Python Wiki 自动生成*",
        ])

        return "\n".join(lines)

    def _generate_en_document(self, doc: QuestDesignDoc) -> str:
        """生成英文设计文档"""
        lines = [
            f"# {doc.title}",
            "",
            f"> Created: {doc.created_at.strftime('%Y-%m-%d %H:%M')}",
            "",
            "## 1. Project Overview",
            "",
            doc.description,
            "",
            "## 2. Requirements",
            "",
        ]

        for i, req in enumerate(doc.requirements, 1):
            lines.append(f"{i}. {req}")
        lines.append("")

        lines.extend([
            "## 3. Tech Stack",
            "",
        ])

        for category, tech in doc.tech_stack.items():
            lines.append(f"- **{category}**: {tech}")
        lines.append("")

        lines.extend([
            "## 4. Architecture",
            "",
            f"### Pattern: {doc.architecture.get('pattern', 'Layered Architecture')}",
            "",
        ])

        lines.extend([
            "## 5. Tasks",
            "",
        ])

        for task in doc.tasks:
            lines.append(f"### {task.title}")
            lines.append(f"- **ID**: {task.id}")
            lines.append(f"- **Description**: {task.description}")
            lines.append(f"- **Status**: {task.status}")
            lines.append("")

        lines.extend([
            "---",
            "",
            "*Generated by Python Wiki*",
        ])

        return "\n".join(lines)

"""
DocumentationAgent 测试
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiki.agents.documentation_agent import (
    DocumentationAgent,
    DocGenerationStatus,
    DocGenerationProgress,
    DocGenerationResult,
)
from pywiki.agents.base import AgentContext, AgentResult
from pywiki.generators.docs.base import DocType
from pywiki.config.models import Language


class TestDocumentationAgent:
    """测试 DocumentationAgent"""

    @pytest.fixture
    def agent(self):
        return DocumentationAgent()

    @pytest.fixture
    def context(self, tmp_path):
        return AgentContext(
            project_path=tmp_path,
            project_name="test_project",
            metadata={
                "doc_types": [DocType.OVERVIEW, DocType.TECH_STACK],
                "language": Language.ZH,
            },
        )

    def test_agent_properties(self, agent):
        """测试 Agent 属性"""
        assert agent.name == "documentation_agent"
        assert "文档生成" in agent.description

    def test_get_supported_doc_types(self, agent):
        """测试获取支持的文档类型"""
        types = agent.get_supported_doc_types()

        assert len(types) >= 10
        assert any(t["type"] == "overview" for t in types)
        assert any(t["type"] == "tech-stack" for t in types)

    def test_register_progress_callback(self, agent):
        """测试注册进度回调"""
        callback_called = []

        def callback(progress):
            callback_called.append(progress)

        agent.register_progress_callback(callback)
        agent._notify_progress()

        assert len(callback_called) == 1

    @pytest.mark.asyncio
    async def test_execute_basic(self, agent, context, tmp_path):
        """测试基本执行"""
        result = await agent.execute(context)

        assert result.success
        assert "generated_files" in result.data

    @pytest.mark.asyncio
    async def test_generate_single_doc(self, agent, context, tmp_path):
        """测试生成单个文档"""
        result = await agent.generate_single_doc(
            context,
            DocType.OVERVIEW,
            Language.ZH,
        )

        assert result.success or "未找到" in result.message

    def test_get_progress(self, agent):
        """测试获取进度"""
        progress = agent.get_progress()

        assert isinstance(progress, DocGenerationProgress)
        assert progress.status == DocGenerationStatus.IDLE

    def test_build_dependency_layers(self, agent):
        """测试依赖分层逻辑"""
        doc_types = [
            DocType.OVERVIEW,
            DocType.TECH_STACK,
            DocType.API,
            DocType.ARCHITECTURE,
            DocType.MODULE,
            DocType.TECHNICAL_DESIGN_SPEC,
            DocType.CODE_QUALITY,
            DocType.TEST_COVERAGE,
        ]
        
        layers = agent._build_dependency_layers(doc_types)
        
        assert len(layers) >= 2, "应该至少有2层"
        
        first_layer_types = [dt.value for dt in layers[0]]
        assert "overview" in first_layer_types
        assert "tech-stack" in first_layer_types
        assert "api" in first_layer_types
        assert "architecture" in first_layer_types
        assert "module" in first_layer_types
        
        last_layer_types = [dt.value for dt in layers[-1]]
        assert "technical-design-spec" in last_layer_types
        
        for layer in layers:
            assert len(layer) > 0

    def test_dependency_layers_parallel_execution(self, agent):
        """测试同一层文档可以并行执行"""
        doc_types = [
            DocType.OVERVIEW,
            DocType.TECH_STACK,
            DocType.API,
            DocType.MODULE,
        ]
        
        layers = agent._build_dependency_layers(doc_types)
        
        assert len(layers) == 1, "没有依赖关系的文档应该在同一层"
        assert len(layers[0]) == 4, "所有4个文档应该在同一层并行执行"


class TestDocGenerationProgress:
    """测试 DocGenerationProgress"""

    def test_default_values(self):
        """测试默认值"""
        progress = DocGenerationProgress()

        assert progress.status == DocGenerationStatus.IDLE
        assert progress.current_doc == ""
        assert progress.completed_docs == []
        assert progress.total_docs == 0
        assert progress.errors == []

    def test_update_values(self):
        """测试更新值"""
        progress = DocGenerationProgress(
            status=DocGenerationStatus.GENERATING,
            current_doc="overview",
            completed_docs=["overview"],
            total_docs=5,
        )

        assert progress.status == DocGenerationStatus.GENERATING
        assert progress.current_doc == "overview"
        assert len(progress.completed_docs) == 1


class TestDocGenerationResult:
    """测试 DocGenerationResult"""

    def test_default_values(self):
        """测试默认值"""
        result = DocGenerationResult(success=True)

        assert result.success
        assert result.generated_files == []
        assert result.failed_docs == []
        assert result.duration_seconds == 0.0

    def test_with_values(self, tmp_path):
        """测试带值"""
        result = DocGenerationResult(
            success=True,
            generated_files=[tmp_path / "overview.md"],
            failed_docs=["api"],
            duration_seconds=1.5,
        )

        assert result.success
        assert len(result.generated_files) == 1
        assert len(result.failed_docs) == 1
        assert result.duration_seconds == 1.5

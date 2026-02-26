"""
AI Agent 单元测试
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from pywiki.agents import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentOrchestrator,
    ImplicitKnowledgeAgent,
    MemoryAgent,
    ArchitectureAgent,
    MultilangAgent,
    AgentPriority,
)
from pywiki.agents.base import CompositeAgent


class TestAgentContext:
    """测试 AgentContext"""
    
    def test_context_creation(self):
        context = AgentContext(
            project_path=Path("/test/project"),
            project_name="test_project",
            query="test query",
        )
        
        assert context.project_path == Path("/test/project")
        assert context.project_name == "test_project"
        assert context.query == "test query"
    
    def test_context_to_dict(self):
        context = AgentContext(
            project_path=Path("/test/project"),
            project_name="test_project",
        )
        
        data = context.to_dict()
        
        assert "test" in data["project_path"] and "project" in data["project_path"]
        assert data["project_name"] == "test_project"


class TestAgentResult:
    """测试 AgentResult"""
    
    def test_success_result(self):
        result = AgentResult.success_result(
            data={"key": "value"},
            message="Success",
            confidence=0.9,
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.message == "Success"
        assert result.confidence == 0.9
    
    def test_error_result(self):
        result = AgentResult.error_result("Error occurred")
        
        assert result.success is False
        assert result.message == "Error occurred"


class TestBaseAgent:
    """测试 BaseAgent"""
    
    @pytest.fixture
    def mock_llm_client(self):
        client = Mock()
        client.agenerate = AsyncMock(return_value="LLM response")
        client.generate = Mock(return_value="LLM response")
        return client
    
    @pytest.fixture
    def mock_memory_manager(self):
        manager = Mock()
        manager.remember = Mock()
        manager.recall = Mock(return_value="memory value")
        return manager
    
    def test_agent_initialization(self, mock_llm_client, mock_memory_manager):
        agent = ImplicitKnowledgeAgent(
            llm_client=mock_llm_client,
            memory_manager=mock_memory_manager,
        )
        
        assert agent.llm_client == mock_llm_client
        assert agent.memory_manager == mock_memory_manager
        assert agent.status.value == "idle"
    
    def test_get_system_prompt(self):
        agent = ImplicitKnowledgeAgent()
        prompt = agent.get_system_prompt()
        
        assert "软件架构师" in prompt
        assert "隐性知识" in prompt

    def test_extract_json_with_valid_json(self):
        agent = ImplicitKnowledgeAgent()
        text = 'Some text {"key": "value", "number": 42} more text'
        
        result = agent._extract_json(text)
        
        assert result == '{"key": "value", "number": 42}'

    def test_extract_json_with_nested_json(self):
        agent = ImplicitKnowledgeAgent()
        text = 'Response: {"outer": {"inner": "value"}}'
        
        result = agent._extract_json(text)
        
        assert result == '{"outer": {"inner": "value"}}'

    def test_extract_json_without_json(self):
        agent = ImplicitKnowledgeAgent()
        text = "This is just plain text without JSON"
        
        result = agent._extract_json(text)
        
        assert result == text

    def test_extract_json_with_empty_text(self):
        agent = ImplicitKnowledgeAgent()
        text = ""
        
        result = agent._extract_json(text)
        
        assert result == ""

    def test_extract_json_with_only_opening_brace(self):
        agent = ImplicitKnowledgeAgent()
        text = "Some text { without closing"
        
        result = agent._extract_json(text)
        
        assert result == text


class TestImplicitKnowledgeAgent:
    """测试 ImplicitKnowledgeAgent"""
    
    @pytest.fixture
    def agent(self):
        return ImplicitKnowledgeAgent()
    
    @pytest.fixture
    def context(self):
        return AgentContext(
            project_path=Path("./test_project"),
            project_name="test_project",
            query="分析架构",
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_context(self, agent):
        context = AgentContext()
        result = await agent.execute(context)
        
        assert result.success is True
        assert "未发现隐性知识" in result.message


class TestMemoryAgent:
    """测试 MemoryAgent"""
    
    @pytest.fixture
    def mock_memory_manager(self):
        manager = Mock()
        manager.search = Mock(return_value=[])
        return manager
    
    @pytest.fixture
    def agent(self, mock_memory_manager):
        return MemoryAgent(memory_manager=mock_memory_manager)
    
    @pytest.mark.asyncio
    async def test_search_operation(self, agent, mock_memory_manager):
        context = AgentContext(
            query="test query",
            metadata={"operation": "search"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        mock_memory_manager.search.assert_called_once()


class TestArchitectureAgent:
    """测试 ArchitectureAgent"""
    
    @pytest.fixture
    def agent(self):
        return ArchitectureAgent()
    
    @pytest.mark.asyncio
    async def test_execute_without_project_path(self, agent):
        context = AgentContext()
        result = await agent.execute(context)
        
        assert result.success is True


class TestMultilangAgent:
    """测试 MultilangAgent"""
    
    @pytest.fixture
    def agent(self):
        return MultilangAgent()
    
    @pytest.mark.asyncio
    async def test_structure_analysis(self, agent, tmp_path):
        (tmp_path / "test.py").write_text("print('hello')")
        
        context = AgentContext(
            project_path=tmp_path,
            metadata={"analysis_type": "structure"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "python" in result.data["languages"]


class TestAgentOrchestrator:
    """测试 AgentOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        return AgentOrchestrator()
    
    @pytest.fixture
    def mock_agent(self):
        agent = Mock(spec=BaseAgent)
        agent.execute = AsyncMock(return_value=AgentResult.success_result(data={}))
        agent.can_execute = Mock(return_value=True)
        agent.description = "Mock Agent"
        return agent
    
    def test_register_agent(self, orchestrator, mock_agent):
        orchestrator.register_agent("test_agent", mock_agent)
        
        assert "test_agent" in orchestrator.list_agents()
    
    def test_unregister_agent(self, orchestrator, mock_agent):
        orchestrator.register_agent("test_agent", mock_agent)
        result = orchestrator.unregister_agent("test_agent")
        
        assert result is True
        assert "test_agent" not in orchestrator.list_agents()
    
    @pytest.mark.asyncio
    async def test_execute_agent(self, orchestrator, mock_agent):
        orchestrator.register_agent("test_agent", mock_agent)
        
        context = AgentContext()
        result = await orchestrator.execute_agent("test_agent", context)
        
        assert result.success is True
        mock_agent.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_nonexistent_agent(self, orchestrator):
        context = AgentContext()
        result = await orchestrator.execute_agent("nonexistent", context)
        
        assert result.success is False
        assert "not found" in result.message
    
    @pytest.mark.asyncio
    async def test_execute_parallel(self, orchestrator, mock_agent):
        orchestrator.register_agent("agent1", mock_agent)
        orchestrator.register_agent("agent2", mock_agent)
        
        context = AgentContext()
        results = await orchestrator.execute_parallel(["agent1", "agent2"], context)
        
        assert len(results) == 2
        assert all(r.success for r in results.values())
    
    @pytest.mark.asyncio
    async def test_execute_sequential(self, orchestrator, mock_agent):
        orchestrator.register_agent("agent1", mock_agent)
        orchestrator.register_agent("agent2", mock_agent)
        
        context = AgentContext()
        results = await orchestrator.execute_sequential(["agent1", "agent2"], context)
        
        assert len(results) == 2


class TestCompositeAgent:
    """测试 CompositeAgent"""
    
    @pytest.fixture
    def composite(self):
        return CompositeAgent()
    
    @pytest.fixture
    def mock_sub_agent(self):
        agent = Mock(spec=BaseAgent)
        agent.execute = AsyncMock(return_value=AgentResult.success_result(
            data={"result": "sub"},
            confidence=0.8,
        ))
        agent.can_execute = Mock(return_value=True)
        return agent
    
    def test_add_agent(self, composite, mock_sub_agent):
        composite.add_agent(mock_sub_agent)
        
        assert len(composite.get_agents()) == 1
    
    def test_remove_agent(self, composite, mock_sub_agent):
        composite.add_agent(mock_sub_agent)
        result = composite.remove_agent(mock_sub_agent)
        
        assert result is True
        assert len(composite.get_agents()) == 0
    
    @pytest.mark.asyncio
    async def test_execute_all(self, composite, mock_sub_agent):
        composite.add_agent(mock_sub_agent)
        composite.add_agent(mock_sub_agent)
        
        context = AgentContext()
        results = await composite.execute_all(context)
        
        assert len(results) == 2


class TestMultiLanguageOrchestrator:
    """测试 MultiLanguageOrchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        from pywiki.agents.orchestrator import MultiLanguageOrchestrator
        return MultiLanguageOrchestrator()
    
    @pytest.fixture
    def mock_agent(self):
        agent = Mock(spec=BaseAgent)
        agent.execute = AsyncMock(return_value=AgentResult.success_result(data={}))
        agent.can_execute = Mock(return_value=True)
        agent.description = "Mock Agent"
        return agent
    
    def test_register_language_agents(self, orchestrator, mock_agent):
        orchestrator.register_agent("python_agent", mock_agent)
        orchestrator.register_language_agents("python", ["python_agent"])
        
        assert "python" in orchestrator._language_agents
    
    @pytest.mark.asyncio
    async def test_analyze_project(self, orchestrator, mock_agent, tmp_path):
        orchestrator.register_agent("python_agent", mock_agent)
        orchestrator.register_language_agents("python", ["python_agent"])
        
        context = AgentContext(project_path=tmp_path)
        results = await orchestrator.analyze_project(context)
        
        assert "by_language" in results
        assert "summary" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

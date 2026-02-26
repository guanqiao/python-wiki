"""
Wiki-Agent 桥接
连接 Wiki 系统和 Agent 系统
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Callable

from pywiki.wiki.manager import WikiManager
from pywiki.wiki.storage import WikiStorage
from pywiki.memory.memory_manager import MemoryManager
from pywiki.agent.search_memory_tool import SearchMemoryTool
from pywiki.agent.context_enricher import ContextEnricher


@dataclass
class AgentSession:
    session_id: str
    project_name: str
    project_path: Path
    created_at: str
    context: dict = field(default_factory=dict)
    interactions: list[dict] = field(default_factory=list)


class WikiAgentBridge:
    """Wiki-Agent 桥接器"""

    def __init__(
        self,
        wiki_manager: Optional[WikiManager] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.wiki_manager = wiki_manager
        self.memory_manager = memory_manager
        self._sessions: dict[str, AgentSession] = {}
        self._tools: dict[str, Callable] = {}

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """注册默认工具"""
        self._tools["search_memory"] = self._create_search_memory_tool()
        self._tools["get_context"] = self._create_get_context_tool()
        self._tools["update_memory"] = self._create_update_memory_tool()
        self._tools["get_wiki_status"] = self._create_get_wiki_status_tool()

    def _create_search_memory_tool(self) -> Callable:
        """创建搜索记忆工具"""
        def search_memory(query: str, top_k: int = 5) -> dict:
            if self.wiki_manager and self.wiki_manager.storage:
                tool = SearchMemoryTool(wiki_storage=self.wiki_manager.storage)
                result = tool.search(query, top_k)
                return {
                    "results": result.results,
                    "context": result.context,
                    "confidence": result.confidence,
                }
            return {"error": "Wiki storage not available"}

        return search_memory

    def _create_get_context_tool(self) -> Callable:
        """创建获取上下文工具"""
        def get_context(query: str) -> dict:
            if self.memory_manager:
                enricher = ContextEnricher(Path("."), self.memory_manager)
                context = enricher.enrich(query)
                return {
                    "project_context": context.project_context,
                    "tech_stack": context.tech_stack_context,
                    "relevant_files": context.relevant_files,
                    "suggestions": context.suggestions,
                }
            return {"error": "Memory manager not available"}

        return get_context

    def _create_update_memory_tool(self) -> Callable:
        """创建更新记忆工具"""
        def update_memory(key: str, value: Any, scope: str = "project") -> dict:
            if self.memory_manager:
                from pywiki.memory.memory_entry import MemoryScope
                try:
                    memory_scope = MemoryScope.PROJECT if scope == "project" else MemoryScope.GLOBAL
                    self.memory_manager.remember(key, value, scope=memory_scope)
                    return {"success": True, "key": key}
                except Exception as e:
                    return {"success": False, "error": str(e)}
            return {"success": False, "error": "Memory manager not available"}

        return update_memory

    def _create_get_wiki_status_tool(self) -> Callable:
        """创建获取 Wiki 状态工具"""
        def get_wiki_status() -> dict:
            if self.wiki_manager:
                return {
                    "has_wiki": True,
                    "documents_count": len(list(self.wiki_manager.storage.list_documents())),
                    "last_generated": "unknown",
                }
            return {"has_wiki": False}

        return get_wiki_status

    def create_session(
        self,
        session_id: str,
        project_name: str,
        project_path: Path,
    ) -> AgentSession:
        """创建 Agent 会话"""
        from datetime import datetime

        session = AgentSession(
            session_id=session_id,
            project_name=project_name,
            project_path=project_path,
            created_at=datetime.now().isoformat(),
        )

        if self.memory_manager:
            self.memory_manager.set_current_project(project_name, project_path)
            session.context = self.memory_manager.get_all_context()

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        """结束会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def execute_tool(self, tool_name: str, parameters: dict) -> Any:
        """执行工具"""
        if tool_name not in self._tools:
            return {"error": f"Tool '{tool_name}' not found"}

        tool = self._tools[tool_name]

        try:
            return tool(**parameters)
        except Exception as e:
            return {"error": str(e)}

    def get_available_tools(self) -> list[dict]:
        """获取可用工具列表"""
        return [
            {
                "name": "search_memory",
                "description": "搜索 Wiki 知识库",
                "parameters": {
                    "query": {"type": "string", "description": "搜索查询"},
                    "top_k": {"type": "integer", "description": "返回结果数量", "default": 5},
                },
            },
            {
                "name": "get_context",
                "description": "获取项目上下文信息",
                "parameters": {
                    "query": {"type": "string", "description": "查询内容"},
                },
            },
            {
                "name": "update_memory",
                "description": "更新记忆系统",
                "parameters": {
                    "key": {"type": "string", "description": "记忆键"},
                    "value": {"type": "any", "description": "记忆值"},
                    "scope": {"type": "string", "description": "记忆范围", "enum": ["global", "project"], "default": "project"},
                },
            },
            {
                "name": "get_wiki_status",
                "description": "获取 Wiki 状态",
                "parameters": {},
            },
        ]

    def record_interaction(
        self,
        session_id: str,
        interaction_type: str,
        content: dict,
    ) -> None:
        """记录交互"""
        from datetime import datetime

        session = self.get_session(session_id)
        if session:
            session.interactions.append({
                "type": interaction_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            })

            if self.memory_manager and interaction_type == "learning":
                self.memory_manager.learn_from_interaction(
                    content.get("interaction_type", ""),
                    content.get("content", {}),
                )

    def get_session_summary(self, session_id: str) -> dict:
        """获取会话摘要"""
        session = self.get_session(session_id)
        if not session:
            return {"error": "Session not found"}

        return {
            "session_id": session.session_id,
            "project_name": session.project_name,
            "created_at": session.created_at,
            "interactions_count": len(session.interactions),
            "has_context": bool(session.context),
        }

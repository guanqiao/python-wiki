"""
Agent 协调器 - 协调多个 Agent 协同工作
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority


@dataclass
class AgentTask:
    """Agent 任务"""
    agent: BaseAgent
    context: AgentContext
    priority: AgentPriority = AgentPriority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    dependencies: list[str] = field(default_factory=list)
    task_id: Optional[str] = None


@dataclass
class WorkflowStep:
    """工作流步骤"""
    name: str
    agent_name: str
    condition: Optional[callable] = None
    on_success: Optional[str] = None
    on_failure: Optional[str] = None


class AgentOrchestrator:
    """Agent 协调器"""
    
    def __init__(self):
        self._agents: dict[str, BaseAgent] = {}
        self._task_queue: list[AgentTask] = []
        self._workflows: dict[str, list[WorkflowStep]] = {}
        self._execution_results: dict[str, AgentResult] = {}
        self._event_handlers: dict[str, list[callable]] = {}
    
    def register_agent(self, name: str, agent: BaseAgent) -> "AgentOrchestrator":
        """注册 Agent"""
        self._agents[name] = agent
        return self
    
    def unregister_agent(self, name: str) -> bool:
        """注销 Agent"""
        if name in self._agents:
            del self._agents[name]
            return True
        return False
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """获取 Agent"""
        return self._agents.get(name)
    
    def list_agents(self) -> dict[str, str]:
        """列出所有 Agent"""
        return {name: agent.description for name, agent in self._agents.items()}
    
    def create_workflow(self, name: str, steps: list[WorkflowStep]) -> "AgentOrchestrator":
        """创建工作流"""
        self._workflows[name] = steps
        return self
    
    async def execute_agent(
        self,
        agent_name: str,
        context: AgentContext,
        **kwargs: Any
    ) -> AgentResult:
        """执行单个 Agent"""
        agent = self._agents.get(agent_name)
        if not agent:
            return AgentResult.error_result(f"Agent '{agent_name}' not found")
        
        if not agent.can_execute(context):
            return AgentResult.error_result(f"Agent '{agent_name}' cannot execute")
        
        start_time = datetime.now()
        
        try:
            result = await agent.execute(context)
            execution_time = (datetime.now() - start_time).total_seconds()
            result.execution_time = execution_time
            
            self._execution_results[agent_name] = result
            self._emit_event("agent_completed", {
                "agent": agent_name,
                "result": result,
            })
            
            return result
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            result = AgentResult.error_result(
                str(e),
                execution_time=execution_time,
            )
            self._execution_results[agent_name] = result
            self._emit_event("agent_error", {
                "agent": agent_name,
                "error": str(e),
            })
            return result
    
    async def execute_workflow(
        self,
        workflow_name: str,
        context: AgentContext,
        **kwargs: Any
    ) -> dict[str, AgentResult]:
        """执行工作流"""
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            return {"error": AgentResult.error_result(f"Workflow '{workflow_name}' not found")}
        
        results = {}
        current_step_idx = 0
        
        while current_step_idx < len(workflow):
            step = workflow[current_step_idx]
            
            if step.condition and not step.condition(context, results):
                current_step_idx += 1
                continue
            
            result = await self.execute_agent(step.agent_name, context)
            results[step.name] = result
            
            if result.success:
                if step.on_success:
                    current_step_idx = self._find_step_index(workflow, step.on_success)
                else:
                    current_step_idx += 1
            else:
                if step.on_failure:
                    current_step_idx = self._find_step_index(workflow, step.on_failure)
                else:
                    current_step_idx += 1
        
        return results
    
    async def execute_parallel(
        self,
        agent_names: list[str],
        context: AgentContext,
        **kwargs: Any
    ) -> dict[str, AgentResult]:
        """并行执行多个 Agent"""
        tasks = []
        for name in agent_names:
            if name in self._agents:
                task = self.execute_agent(name, context)
                tasks.append((name, task))
        
        results = {}
        if tasks:
            coroutines = [task for _, task in tasks]
            task_results = await asyncio.gather(*coroutines, return_exceptions=True)
            
            for (name, _), result in zip(tasks, task_results):
                if isinstance(result, Exception):
                    results[name] = AgentResult.error_result(str(result))
                else:
                    results[name] = result
        
        return results
    
    async def execute_sequential(
        self,
        agent_names: list[str],
        context: AgentContext,
        stop_on_error: bool = True,
        **kwargs: Any
    ) -> dict[str, AgentResult]:
        """顺序执行多个 Agent"""
        results = {}
        
        for name in agent_names:
            result = await self.execute_agent(name, context)
            results[name] = result
            
            if not result.success and stop_on_error:
                break
        
        return results
    
    def _find_step_index(self, workflow: list[WorkflowStep], step_name: str) -> int:
        """查找步骤索引"""
        for i, step in enumerate(workflow):
            if step.name == step_name:
                return i
        return len(workflow)
    
    def on_event(self, event_name: str, handler: callable) -> "AgentOrchestrator":
        """注册事件处理器"""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)
        return self
    
    def _emit_event(self, event_name: str, data: dict) -> None:
        """触发事件"""
        handlers = self._event_handlers.get(event_name, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception:
                pass
    
    def get_execution_summary(self) -> dict[str, Any]:
        """获取执行摘要"""
        total = len(self._execution_results)
        successful = sum(1 for r in self._execution_results.values() if r.success)
        failed = total - successful
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / max(total, 1),
            "agents": list(self._execution_results.keys()),
        }
    
    def clear_results(self) -> None:
        """清除执行结果"""
        self._execution_results.clear()


class MultiLanguageOrchestrator(AgentOrchestrator):
    """多语言分析协调器"""
    
    def __init__(self):
        super().__init__()
        self._language_agents: dict[str, list[str]] = {}
    
    def register_language_agents(self, language: str, agent_names: list[str]) -> "MultiLanguageOrchestrator":
        """注册语言特定的 Agent"""
        self._language_agents[language] = agent_names
        return self
    
    async def analyze_project(
        self,
        context: AgentContext,
        languages: Optional[list[str]] = None,
        **kwargs: Any
    ) -> dict[str, Any]:
        """分析多语言项目"""
        results = {
            "by_language": {},
            "cross_language": {},
            "summary": {},
        }
        
        target_languages = languages or list(self._language_agents.keys())
        
        for lang in target_languages:
            agent_names = self._language_agents.get(lang, [])
            if agent_names:
                lang_results = await self.execute_parallel(agent_names, context)
                results["by_language"][lang] = lang_results
        
        cross_lang_agents = [name for name in self._agents.keys() if "cross" in name.lower()]
        if cross_lang_agents:
            cross_results = await self.execute_parallel(cross_lang_agents, context)
            results["cross_language"] = cross_results
        
        results["summary"] = self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: dict) -> dict:
        """生成分析摘要"""
        summary = {
            "languages_analyzed": list(results["by_language"].keys()),
            "total_insights": 0,
            "confidence_scores": {},
        }
        
        for lang, lang_results in results["by_language"].items():
            insights = sum(
                1 for r in lang_results.values()
                if r.success and r.data
            )
            summary["total_insights"] += insights
            
            avg_confidence = sum(
                r.confidence for r in lang_results.values() if r.success
            ) / max(len(lang_results), 1)
            summary["confidence_scores"][lang] = avg_confidence
        
        return summary
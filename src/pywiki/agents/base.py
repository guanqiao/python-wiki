"""
Agent 基础类和接口定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional, AsyncIterator, Iterator

from pywiki.llm.base import BaseLLMClient
from pywiki.memory.memory_manager import MemoryManager


class AgentStatus(str, Enum):
    """Agent 状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class AgentPriority(str, Enum):
    """Agent 优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentContext:
    """Agent 上下文"""
    project_path: Optional[Path] = None
    project_name: Optional[str] = None
    file_path: Optional[Path] = None
    module_info: Optional[Any] = None
    query: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    memory_manager: Optional[MemoryManager] = None
    llm_client: Optional[BaseLLMClient] = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "project_path": str(self.project_path) if self.project_path else None,
            "project_name": self.project_name,
            "file_path": str(self.file_path) if self.file_path else None,
            "query": self.query,
            "metadata": self.metadata,
        }


@dataclass
class AgentResult:
    """Agent 执行结果"""
    success: bool
    data: Any = None
    message: str = ""
    confidence: float = 0.0
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success_result(cls, data: Any, message: str = "", confidence: float = 1.0, **kwargs) -> "AgentResult":
        """创建成功结果"""
        return cls(
            success=True,
            data=data,
            message=message,
            confidence=confidence,
            metadata=kwargs,
        )
    
    @classmethod
    def error_result(cls, message: str, **kwargs) -> "AgentResult":
        """创建错误结果"""
        return cls(
            success=False,
            message=message,
            metadata=kwargs,
        )


class BaseAgent(ABC):
    """Agent 基类"""
    
    name: str = "base_agent"
    description: str = "基础 Agent"
    priority: AgentPriority = AgentPriority.MEDIUM
    
    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        memory_manager: Optional[MemoryManager] = None,
        **kwargs: Any
    ):
        self.llm_client = llm_client
        self.memory_manager = memory_manager
        self.status = AgentStatus.IDLE
        self._config = kwargs
        self._execution_history: list[dict] = []
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行 Agent 任务"""
        pass
    
    async def execute_stream(self, context: AgentContext) -> AsyncIterator[str]:
        """流式执行 Agent 任务"""
        result = await self.execute(context)
        yield result.message
        if result.data:
            yield str(result.data)
    
    def can_execute(self, context: AgentContext) -> bool:
        """检查是否可以执行"""
        return self.status == AgentStatus.IDLE
    
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return f"""# 角色定义
你是一位专业的 {self.description}，具备深厚的软件工程知识和代码分析能力。

# 核心能力
- 代码结构分析与理解
- 设计模式识别与评估
- 架构健康度诊断
- 最佳实践建议

# 工作原则
1. **准确性优先**: 基于代码事实进行分析，避免主观臆断
2. **结构化输出**: 使用清晰的层次结构组织分析结果
3. **可操作性**: 提供具体、可执行的建议，而非泛泛而谈
4. **上下文感知**: 结合项目特点和业务场景给出建议

# 输出规范
- 使用 Markdown 格式组织内容
- 代码示例使用代码块包裹
- 重要结论使用加粗或列表强调
- 复杂分析提供摘要和详细说明两部分

请始终保持专业、客观、有建设性的态度。"""
    
    async def call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """调用 LLM"""
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        sys_prompt = system_prompt or self.get_system_prompt()
        return await self.llm_client.agenerate(prompt, system_prompt=sys_prompt, **kwargs)
    
    def call_llm_sync(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """同步调用 LLM"""
        if not self.llm_client:
            raise ValueError("LLM client not configured")
        
        sys_prompt = system_prompt or self.get_system_prompt()
        return self.llm_client.generate(prompt, system_prompt=sys_prompt, **kwargs)
    
    def remember(self, key: str, value: Any, **kwargs: Any) -> None:
        """记录记忆"""
        if self.memory_manager:
            self.memory_manager.remember(key, value, **kwargs)
    
    def recall(self, key: str, **kwargs: Any) -> Optional[Any]:
        """回忆记忆"""
        if self.memory_manager:
            return self.memory_manager.recall(key, **kwargs)
        return None
    
    def _record_execution(self, context: AgentContext, result: AgentResult) -> None:
        """记录执行历史"""
        self._execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "context": context.to_dict(),
            "result": {
                "success": result.success,
                "message": result.message,
                "confidence": result.confidence,
            },
        })
    
    def get_execution_history(self) -> list[dict]:
        """获取执行历史"""
        return self._execution_history.copy()
    
    def clear_history(self) -> None:
        """清除执行历史"""
        self._execution_history.clear()
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 字符串"""
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            return text[start:end+1]
        return text


class CompositeAgent(BaseAgent):
    """组合 Agent - 可以包含多个子 Agent"""
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._sub_agents: list[BaseAgent] = []
    
    def add_agent(self, agent: BaseAgent) -> "CompositeAgent":
        """添加子 Agent"""
        self._sub_agents.append(agent)
        return self
    
    def remove_agent(self, agent: BaseAgent) -> bool:
        """移除子 Agent"""
        if agent in self._sub_agents:
            self._sub_agents.remove(agent)
            return True
        return False
    
    def get_agents(self) -> list[BaseAgent]:
        """获取所有子 Agent"""
        return self._sub_agents.copy()
    
    async def execute_all(self, context: AgentContext) -> list[AgentResult]:
        """执行所有子 Agent"""
        results = []
        for agent in self._sub_agents:
            if agent.can_execute(context):
                result = await agent.execute(context)
                results.append(result)
        return results
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """默认执行所有子 Agent 并聚合结果"""
        results = await self.execute_all(context)
        
        success = all(r.success for r in results)
        data = [r.data for r in results if r.data]
        message = "\n".join(r.message for r in results if r.message)
        confidence = sum(r.confidence for r in results) / max(len(results), 1)
        
        return AgentResult(
            success=success,
            data=data,
            message=message,
            confidence=confidence,
        )
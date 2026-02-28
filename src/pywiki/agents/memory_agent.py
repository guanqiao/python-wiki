"""
记忆系统 Agent
智能管理知识，主动推荐相关记忆，支持语义搜索和上下文感知
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from pywiki.agents.base import BaseAgent, AgentContext, AgentResult, AgentPriority
from pywiki.memory.memory_entry import MemoryCategory, MemoryScope


@dataclass
class MemoryRecommendation:
    """记忆推荐"""
    memory_key: str
    memory_value: Any
    relevance_score: float
    reason: str
    category: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SemanticQuery:
    """语义查询"""
    query: str
    intent: str
    entities: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)


class MemoryAgent(BaseAgent):
    """记忆系统 Agent"""
    
    name = "memory_agent"
    description = "记忆管理专家 - 智能管理知识库，主动推荐相关记忆，支持语义搜索"
    priority = AgentPriority.HIGH
    
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._access_history: list[dict] = []
        self._recommendation_cache: dict[str, MemoryRecommendation] = {}
    
    def get_system_prompt(self) -> str:
        return """# 角色定义
你是一个智能记忆管理助手，负责知识库的智能检索、组织和推荐，帮助用户高效获取和利用知识。

# 核心能力
1. **意图理解**: 准确解析用户查询意图，识别关键实体和上下文
2. **语义检索**: 基于语义相似度检索相关知识条目
3. **智能推荐**: 根据上下文主动推荐可能相关的记忆
4. **知识组织**: 优化知识分类和关联关系

# 查询意图类型
- **search**: 搜索特定知识条目
- **recommend**: 获取相关推荐
- **compare**: 比较多个知识条目
- **analyze**: 分析知识关联和趋势

# 相关性评估方法
1. **关键词匹配**: 查询词与记忆键值匹配程度
2. **语义相似度**: 查询意图与记忆内容的语义关联
3. **上下文关联**: 当前文件、项目与记忆的关联度
4. **访问历史**: 记忆的历史访问频率和时效性

# 输出规范
- 使用JSON格式输出结构化结果
- 每条推荐包含：记忆键、记忆值、相关性分数、推荐理由
- 相关性分数范围：0.0-1.0
- 按相关性降序排列结果
- 提供简要的推荐理由说明

请提供准确、相关的记忆推荐。"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """执行记忆操作"""
        self.status = "running"
        
        try:
            operation = context.metadata.get("operation", "search")
            
            if operation == "search":
                result = await self._handle_search(context)
            elif operation == "recommend":
                result = await self._handle_recommend(context)
            elif operation == "store":
                result = await self._handle_store(context)
            elif operation == "learn":
                result = await self._handle_learn(context)
            elif operation == "semantic_query":
                result = await self._handle_semantic_query(context)
            else:
                result = AgentResult.error_result(f"未知操作: {operation}")
            
            self._record_execution(context, result)
            self.status = "completed"
            return result
            
        except Exception as e:
            self.status = "error"
            return AgentResult.error_result(f"记忆操作失败: {str(e)}")
    
    async def _handle_search(self, context: AgentContext) -> AgentResult:
        """处理搜索请求"""
        query = context.query or context.metadata.get("query", "")
        scope = context.metadata.get("scope")
        category = context.metadata.get("category")
        
        if not self.memory_manager:
            return AgentResult.error_result("记忆管理器未配置")
        
        memories = self.memory_manager.search(query, scope=scope)
        
        if category:
            memories = [m for m in memories if m.category.value == category]
        
        results = []
        for memory in memories:
            relevance = self._calculate_relevance(memory, query, context)
            results.append({
                "key": memory.key,
                "value": memory.value,
                "category": memory.category.value,
                "scope": memory.scope.value,
                "description": memory.description,
                "confidence": memory.confidence,
                "relevance_score": relevance,
                "access_count": memory.access_count,
                "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
                "tags": memory.tags,
            })
        
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return AgentResult.success_result(
            data={
                "query": query,
                "total_results": len(results),
                "memories": results[:20],
            },
            message=f"找到 {len(results)} 条相关记忆",
            confidence=0.8 if results else 0.0,
        )
    
    async def _handle_recommend(self, context: AgentContext) -> AgentResult:
        """处理推荐请求"""
        recommendations = []
        
        context_recommendations = self._get_context_based_recommendations(context)
        recommendations.extend(context_recommendations)
        
        recent_recommendations = self._get_recent_access_recommendations()
        recommendations.extend(recent_recommendations)
        
        if self.llm_client and context.query:
            llm_recommendations = await self._get_llm_recommendations(context)
            recommendations.extend(llm_recommendations)
        
        recommendations = self._deduplicate_recommendations(recommendations)
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return AgentResult.success_result(
            data={
                "recommendations": [
                    {
                        "key": r.memory_key,
                        "value": r.memory_value,
                        "relevance_score": r.relevance_score,
                        "reason": r.reason,
                        "category": r.category,
                    }
                    for r in recommendations[:10]
                ],
            },
            message=f"推荐 {len(recommendations)} 条相关记忆",
            confidence=0.75,
        )
    
    async def _handle_store(self, context: AgentContext) -> AgentResult:
        """处理存储请求"""
        key = context.metadata.get("key")
        value = context.metadata.get("value")
        scope_str = context.metadata.get("scope", "global")
        category_str = context.metadata.get("category", "preference")
        description = context.metadata.get("description")
        tags = context.metadata.get("tags", [])
        
        if not key or value is None:
            return AgentResult.error_result("缺少 key 或 value")
        
        if not self.memory_manager:
            return AgentResult.error_result("记忆管理器未配置")
        
        scope = MemoryScope(scope_str)
        category = MemoryCategory(category_str)
        
        entry = self.memory_manager.remember(
            key=key,
            value=value,
            scope=scope,
            category=category,
            description=description,
            tags=tags,
        )
        
        return AgentResult.success_result(
            data={
                "entry_id": entry.id,
                "key": entry.key,
                "scope": entry.scope.value,
                "category": entry.category.value,
            },
            message=f"成功存储记忆: {key}",
            confidence=1.0,
        )
    
    async def _handle_learn(self, context: AgentContext) -> AgentResult:
        """处理学习请求"""
        interaction_type = context.metadata.get("interaction_type")
        content = context.metadata.get("content", {})
        
        if not self.memory_manager:
            return AgentResult.error_result("记忆管理器未配置")
        
        entry = self.memory_manager.learn_from_interaction(interaction_type, content)
        
        if entry:
            return AgentResult.success_result(
                data={
                    "learned": True,
                    "entry": {
                        "id": entry.id,
                        "key": entry.key,
                        "category": entry.category.value,
                    },
                },
                message=f"从交互中学习: {entry.key}",
                confidence=0.9,
            )
        
        return AgentResult.error_result("学习失败")
    
    async def _handle_semantic_query(self, context: AgentContext) -> AgentResult:
        """处理语义查询"""
        query = context.query or ""
        
        if not self.llm_client:
            return await self._handle_search(context)
        
        parsed_query = await self._parse_semantic_query(query)
        
        all_memories = []
        if self.memory_manager:
            all_memories = self.memory_manager.search(parsed_query.query)
        
        filtered_memories = self._filter_by_intent(all_memories, parsed_query)
        
        reranked_memories = await self._rerank_with_llm(filtered_memories, parsed_query)
        
        return AgentResult.success_result(
            data={
                "original_query": query,
                "parsed_intent": parsed_query.intent,
                "entities": parsed_query.entities,
                "results": [
                    {
                        "key": m.key,
                        "value": m.value,
                        "relevance": self._calculate_relevance(m, query, context),
                    }
                    for m in reranked_memories[:10]
                ],
            },
            message=f"语义查询完成，找到 {len(reranked_memories)} 条结果",
            confidence=0.85,
        )
    
    async def _parse_semantic_query(self, query: str) -> SemanticQuery:
        """解析语义查询"""
        prompt = f"""解析以下查询，提取意图和实体：

查询: "{query}"

返回 JSON 格式:
{{
    "intent": "查询意图 (search/recommend/compare/analyze)",
    "entities": ["实体1", "实体2"],
    "context": {{"key": "value"}}
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            
            return SemanticQuery(
                query=query,
                intent=parsed.get("intent", "search"),
                entities=parsed.get("entities", []),
                context=parsed.get("context", {}),
            )
        except Exception:
            return SemanticQuery(query=query, intent="search")
    
    async def _rerank_with_llm(
        self,
        memories: list,
        query: SemanticQuery
    ) -> list:
        """使用 LLM 重新排序"""
        if not memories or len(memories) <= 5:
            return memories
        
        memory_texts = []
        for i, m in enumerate(memories[:15]):
            memory_texts.append(f"{i}. {m.key}: {str(m.value)[:100]}")
        
        prompt = f"""根据查询意图，评估以下记忆的相关性：

查询意图: {query.intent}
实体: {query.entities}

记忆列表:
{"\n".join(memory_texts)}

返回最相关的记忆索引（0-based），JSON 格式:
{{
    "ranking": [2, 0, 5, 1, 3],
    "reasoning": "简要说明排序原因"
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            ranking = parsed.get("ranking", [])
            
            reranked = []
            for idx in ranking:
                if 0 <= idx < len(memories):
                    reranked.append(memories[idx])
            
            for i, m in enumerate(memories):
                if i not in ranking:
                    reranked.append(m)
            
            return reranked
        except Exception:
            return memories
    
    def _get_context_based_recommendations(self, context: AgentContext) -> list[MemoryRecommendation]:
        """基于上下文获取推荐"""
        recommendations = []
        
        if not self.memory_manager:
            return recommendations
        
        if context.file_path:
            file_memories = self.memory_manager.search(
                str(context.file_path.name),
                scope=MemoryScope.PROJECT,
            )
            for memory in file_memories[:5]:
                recommendations.append(MemoryRecommendation(
                    memory_key=memory.key,
                    memory_value=memory.value,
                    relevance_score=0.8,
                    reason=f"与当前文件 {context.file_path.name} 相关",
                    category=memory.category.value,
                ))
        
        if context.project_name:
            project_memories = self.memory_manager.search(
                context.project_name,
                scope=MemoryScope.PROJECT,
            )
            for memory in project_memories[:3]:
                recommendations.append(MemoryRecommendation(
                    memory_key=memory.key,
                    memory_value=memory.value,
                    relevance_score=0.75,
                    reason=f"与项目 {context.project_name} 相关",
                    category=memory.category.value,
                ))
        
        return recommendations
    
    def _get_recent_access_recommendations(self) -> list[MemoryRecommendation]:
        """获取最近访问的推荐"""
        recommendations = []
        
        if not self.memory_manager:
            return recommendations
        
        all_memories = []
        all_memories.extend(self.memory_manager.global_memory.list_memories())
        
        project_memory = self.memory_manager.get_current_project_memory()
        if project_memory:
            all_memories.extend(project_memory.list_memories())
        
        recent_memories = [
            m for m in all_memories
            if m.last_accessed and
            (datetime.now() - m.last_accessed) < timedelta(days=7)
        ]
        
        recent_memories.sort(key=lambda x: x.access_count, reverse=True)
        
        for memory in recent_memories[:5]:
            recommendations.append(MemoryRecommendation(
                memory_key=memory.key,
                memory_value=memory.value,
                relevance_score=min(0.9, 0.5 + memory.access_count * 0.1),
                reason=f"最近频繁访问 ({memory.access_count} 次)",
                category=memory.category.value,
            ))
        
        return recommendations
    
    async def _get_llm_recommendations(self, context: AgentContext) -> list[MemoryRecommendation]:
        """使用 LLM 获取推荐"""
        recommendations = []
        
        if not self.memory_manager or not context.query:
            return recommendations
        
        all_memories = self.memory_manager.search(context.query)
        
        if not all_memories:
            return recommendations
        
        memory_summary = "\n".join([
            f"- {m.key}: {str(m.value)[:50]}"
            for m in all_memories[:10]
        ])
        
        prompt = f"""基于用户当前上下文，推荐最相关的记忆：

用户查询: {context.query}
当前文件: {context.file_path}
项目: {context.project_name}

可用记忆:
{memory_summary}

推荐哪些记忆最相关？返回 JSON:
{{
    "recommendations": [
        {{
            "key": "记忆键",
            "reason": "推荐理由",
            "relevance": 0.85
        }}
    ]
}}
"""
        
        try:
            response = await self.call_llm(prompt)
            parsed = json.loads(self._extract_json(response))
            
            for rec in parsed.get("recommendations", []):
                key = rec.get("key")
                memory = self.memory_manager.recall_entry(key)
                if memory:
                    recommendations.append(MemoryRecommendation(
                        memory_key=key,
                        memory_value=memory.value,
                        relevance_score=rec.get("relevance", 0.5),
                        reason=rec.get("reason", "LLM 推荐"),
                        category=memory.category.value,
                    ))
        except Exception:
            pass
        
        return recommendations
    
    def _calculate_relevance(
        self,
        memory: Any,
        query: str,
        context: AgentContext
    ) -> float:
        """计算相关性分数"""
        score = 0.0
        
        query_lower = query.lower()
        key_lower = memory.key.lower()
        
        if query_lower in key_lower:
            score += 0.4
        
        if memory.description and query_lower in memory.description.lower():
            score += 0.2
        
        if memory.tags:
            for tag in memory.tags:
                if query_lower in tag.lower():
                    score += 0.1
        
        score += min(0.2, memory.access_count * 0.02)
        
        if memory.confidence:
            score += memory.confidence * 0.1
        
        return min(1.0, score)
    
    def _filter_by_intent(self, memories: list, query: SemanticQuery) -> list:
        """根据意图过滤记忆"""
        if query.intent == "search":
            return memories
        
        filtered = []
        for memory in memories:
            if query.intent == "recommend" and memory.category.value in ["preference", "coding_style"]:
                filtered.append(memory)
            elif query.intent == "compare" and memory.category.value in ["tech_stack", "architecture"]:
                filtered.append(memory)
            elif query.intent == "analyze" and memory.category.value in ["business_rule", "problem_solution"]:
                filtered.append(memory)
            else:
                filtered.append(memory)
        
        return filtered
    
    def _deduplicate_recommendations(
        self,
        recommendations: list[MemoryRecommendation]
    ) -> list[MemoryRecommendation]:
        """去重推荐"""
        seen = set()
        unique = []
        
        for rec in recommendations:
            if rec.memory_key not in seen:
                seen.add(rec.memory_key)
                unique.append(rec)
        
        return unique
"""
AI Agent 使用示例
展示如何使用各种 Agent 进行代码分析
"""

import asyncio
from pathlib import Path

from pywiki.agents import (
    AgentContext,
    AgentOrchestrator,
    ImplicitKnowledgeAgent,
    MemoryAgent,
    ArchitectureAgent,
    MultilangAgent,
)
from pywiki.llm.client import LLMClient
from pywiki.memory.memory_manager import MemoryManager
from pywiki.config.models import LLMConfig


def create_example_llm_client():
    """创建示例 LLM 客户端"""
    config = LLMConfig(
        endpoint="https://api.openai.com/v1",
        api_key="your-api-key",
        model="gpt-4",
    )
    return LLMClient.from_config(config)


async def example_implicit_knowledge_agent():
    """隐形知识挖掘 Agent 示例"""
    print("=" * 60)
    print("示例 1: 隐形知识挖掘 Agent")
    print("=" * 60)
    
    llm_client = create_example_llm_client()
    
    agent = ImplicitKnowledgeAgent(llm_client=llm_client)
    
    context = AgentContext(
        project_path=Path("./my_project"),
        project_name="my_project",
        file_path=Path("./my_project/src/main.py"),
        query="分析这个项目的架构设计",
    )
    
    result = await agent.execute(context)
    
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    print(f"置信度: {result.confidence:.2f}")
    
    if result.data:
        print(f"\n发现的洞察数量: {result.data.get('total_insights', 0)}")
        print(f"高置信度洞察: {len(result.data.get('high_confidence_insights', []))}")
    
    return result


async def example_memory_agent():
    """记忆系统 Agent 示例"""
    print("\n" + "=" * 60)
    print("示例 2: 记忆系统 Agent")
    print("=" * 60)
    
    memory_manager = MemoryManager()
    memory_manager.set_current_project("my_project", Path("./my_project"))
    
    agent = MemoryAgent(memory_manager=memory_manager)
    
    context = AgentContext(
        project_name="my_project",
        project_path=Path("./my_project"),
        query="推荐相关的编码规范",
        metadata={"operation": "recommend"},
    )
    
    result = await agent.execute(context)
    
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    
    if result.data:
        recommendations = result.data.get("recommendations", [])
        print(f"\n推荐数量: {len(recommendations)}")
        for rec in recommendations[:3]:
            print(f"  - {rec['key']}: {rec['reason']} (相关度: {rec['relevance_score']:.2f})")
    
    return result


async def example_architecture_agent():
    """架构洞见 Agent 示例"""
    print("\n" + "=" * 60)
    print("示例 3: 架构洞见 Agent")
    print("=" * 60)
    
    llm_client = create_example_llm_client()
    
    agent = ArchitectureAgent(llm_client=llm_client)
    
    context = AgentContext(
        project_path=Path("./my_project"),
        project_name="my_project",
        metadata={"analysis_type": "full"},
    )
    
    result = await agent.execute(context)
    
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    
    if result.data:
        print(f"\n架构健康度评分: {result.data.get('overall_score', 0):.2f}")
        
        metrics = result.data.get("metrics", {})
        print("\n各项指标:")
        for metric_name, metric_data in metrics.items():
            print(f"  - {metric_name}: {metric_data['score']:.2f} - {metric_data['description']}")
        
        insights = result.data.get("insights", [])
        print(f"\n架构洞察: {len(insights)} 条")
        for insight in insights[:3]:
            print(f"  - [{insight['severity']}] {insight['title']}")
    
    return result


async def example_multilang_agent():
    """多语言分析 Agent 示例"""
    print("\n" + "=" * 60)
    print("示例 4: 多语言分析 Agent")
    print("=" * 60)
    
    agent = MultilangAgent()
    
    context = AgentContext(
        project_path=Path("./my_multilang_project"),
        project_name="my_multilang_project",
        metadata={"analysis_type": "full"},
    )
    
    result = await agent.execute(context)
    
    print(f"成功: {result.success}")
    print(f"消息: {result.message}")
    
    if result.data:
        structure = result.data.get("structure", {})
        languages = structure.get("languages", {})
        
        print("\n语言统计:")
        for lang, stats in languages.items():
            if stats["file_count"] > 0:
                print(f"  - {lang}: {stats['file_count']} 文件, {stats['total_lines']} 行代码")
        
        cross_calls = result.data.get("cross_calls", {})
        print(f"\n跨语言调用: {cross_calls.get('total_calls', 0)} 个")
        
        api_contracts = result.data.get("api_contracts", {})
        by_type = api_contracts.get("by_type", {})
        print(f"\nAPI 契约:")
        for api_type, count in by_type.items():
            print(f"  - {api_type}: {count} 个")
    
    return result


async def example_orchestrator():
    """Agent 协调器示例"""
    print("\n" + "=" * 60)
    print("示例 5: Agent 协调器")
    print("=" * 60)
    
    llm_client = create_example_llm_client()
    
    memory_manager = MemoryManager()
    memory_manager.set_current_project("my_project", Path("./my_project"))
    
    orchestrator = AgentOrchestrator()
    
    orchestrator.register_agent(
        "implicit_knowledge",
        ImplicitKnowledgeAgent(llm_client=llm_client, memory_manager=memory_manager)
    )
    orchestrator.register_agent(
        "memory",
        MemoryAgent(llm_client=llm_client, memory_manager=memory_manager)
    )
    orchestrator.register_agent(
        "architecture",
        ArchitectureAgent(llm_client=llm_client, memory_manager=memory_manager)
    )
    
    context = AgentContext(
        project_path=Path("./my_project"),
        project_name="my_project",
        query="全面分析项目",
    )
    
    results = await orchestrator.execute_parallel(
        ["implicit_knowledge", "memory", "architecture"],
        context,
    )
    
    print("并行执行结果:")
    for agent_name, result in results.items():
        print(f"\n{agent_name}:")
        print(f"  成功: {result.success}")
        print(f"  消息: {result.message}")
        print(f"  置信度: {result.confidence:.2f}")
    
    summary = orchestrator.get_execution_summary()
    print(f"\n执行摘要:")
    print(f"  总执行数: {summary['total_executions']}")
    print(f"  成功: {summary['successful']}")
    print(f"  失败: {summary['failed']}")
    print(f"  成功率: {summary['success_rate']:.2%}")
    
    return results


async def example_workflow():
    """工作流示例"""
    print("\n" + "=" * 60)
    print("示例 6: 工作流编排")
    print("=" * 60)
    
    llm_client = create_example_llm_client()
    
    orchestrator = AgentOrchestrator()
    
    orchestrator.register_agent(
        "implicit_knowledge",
        ImplicitKnowledgeAgent(llm_client=llm_client)
    )
    orchestrator.register_agent(
        "architecture",
        ArchitectureAgent(llm_client=llm_client)
    )
    
    from pywiki.agents.orchestrator import WorkflowStep
    
    orchestrator.create_workflow(
        "analysis_workflow",
        [
            WorkflowStep(
                name="discover_knowledge",
                agent_name="implicit_knowledge",
            ),
            WorkflowStep(
                name="analyze_architecture",
                agent_name="architecture",
            ),
        ]
    )
    
    context = AgentContext(
        project_path=Path("./my_project"),
        project_name="my_project",
    )
    
    results = await orchestrator.execute_workflow("analysis_workflow", context)
    
    print("工作流执行结果:")
    for step_name, result in results.items():
        print(f"\n{step_name}:")
        print(f"  成功: {result.success}")
        print(f"  消息: {result.message}")
    
    return results


async def main():
    """主函数"""
    print("AI Agent 系统使用示例")
    print("=" * 60)
    
    try:
        await example_implicit_knowledge_agent()
    except Exception as e:
        print(f"隐形知识挖掘 Agent 示例出错: {e}")
    
    try:
        await example_memory_agent()
    except Exception as e:
        print(f"记忆系统 Agent 示例出错: {e}")
    
    try:
        await example_architecture_agent()
    except Exception as e:
        print(f"架构洞见 Agent 示例出错: {e}")
    
    try:
        await example_multilang_agent()
    except Exception as e:
        print(f"多语言分析 Agent 示例出错: {e}")
    
    try:
        await example_orchestrator()
    except Exception as e:
        print(f"Agent 协调器示例出错: {e}")
    
    try:
        await example_workflow()
    except Exception as e:
        print(f"工作流示例出错: {e}")
    
    print("\n" + "=" * 60)
    print("所有示例执行完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

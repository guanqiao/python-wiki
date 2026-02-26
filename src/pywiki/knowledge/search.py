"""
知识搜索服务
"""

from pathlib import Path
from typing import Any, Optional

from pywiki.knowledge.vector_store import VectorStore
from pywiki.llm.client import LLMClient


class KnowledgeSearcher:
    """知识库搜索服务"""

    def __init__(
        self,
        vector_store: VectorStore,
        llm_client: Optional[LLMClient] = None,
    ):
        self.vector_store = vector_store
        self.llm_client = llm_client

    def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[dict] = None,
    ) -> list[dict]:
        """搜索知识库"""
        return self.vector_store.search(query, k, filter)

    def search_code(
        self,
        query: str,
        module: Optional[str] = None,
        k: int = 5,
    ) -> list[dict]:
        """搜索代码相关内容"""
        filter_dict = {"type": "code"}
        if module:
            filter_dict["module"] = module

        return self.vector_store.search(query, k, filter_dict)

    def search_documentation(
        self,
        query: str,
        k: int = 5,
    ) -> list[dict]:
        """搜索文档内容"""
        return self.vector_store.search(
            query,
            k,
            filter={"type": "documentation"}
        )

    async def ask(
        self,
        question: str,
        context_k: int = 5,
    ) -> str:
        """基于知识库回答问题"""
        if not self.llm_client:
            results = self.search(question, k=context_k)
            context = "\n\n".join(r["content"] for r in results)
            return f"找到相关内容:\n\n{context}"

        results = self.search(question, k=context_k)
        context = "\n\n".join(
            f"来源: {r['metadata'].get('source', 'unknown')}\n{r['content']}"
            for r in results
        )

        prompt = f"""基于以下知识库内容回答问题。如果知识库中没有相关信息，请说明。

知识库内容:
{context}

问题: {question}

请提供准确、详细的回答，并在适当的地方引用来源。"""

        response = await self.llm_client.agenerate(prompt)
        return response

    def hybrid_search(
        self,
        query: str,
        keywords: Optional[list[str]] = None,
        k: int = 5,
    ) -> list[dict]:
        """混合搜索（语义 + 关键词）"""
        semantic_results = self.vector_store.search(query, k=k * 2)

        if not keywords:
            return semantic_results[:k]

        keyword_results = []
        for result in semantic_results:
            content = result["content"].lower()
            if any(kw.lower() in content for kw in keywords):
                keyword_results.append(result)

        seen = set()
        combined = []
        for r in keyword_results + semantic_results:
            content_hash = hash(r["content"])
            if content_hash not in seen:
                seen.add(content_hash)
                combined.append(r)

        return combined[:k]

    def get_related_documents(
        self,
        doc_id: str,
        k: int = 5,
    ) -> list[dict]:
        """获取相关文档"""
        pass

    def index_module(
        self,
        module_info: dict,
        source: str,
    ) -> None:
        """索引模块信息"""
        documents = []

        module_doc = f"""模块: {module_info.get('name', '')}
路径: {module_info.get('file_path', '')}
描述: {module_info.get('docstring', '无描述')}

包含:
- {len(module_info.get('classes', []))} 个类
- {len(module_info.get('functions', []))} 个函数
"""
        documents.append({
            "content": module_doc,
            "metadata": {
                "type": "module",
                "source": source,
                "name": module_info.get("name", ""),
            },
        })

        for cls in module_info.get("classes", []):
            class_doc = f"""类: {cls.get('name', '')}
模块: {module_info.get('name', '')}
描述: {cls.get('docstring', '无描述')}
基类: {', '.join(cls.get('bases', [])) or '无'}

方法:
"""
            for method in cls.get("methods", []):
                class_doc += f"- {method.get('name', '')}()\n"

            documents.append({
                "content": class_doc,
                "metadata": {
                    "type": "class",
                    "source": source,
                    "module": module_info.get("name", ""),
                    "name": cls.get("name", ""),
                },
            })

        for func in module_info.get("functions", []):
            func_doc = f"""函数: {func.get('name', '')}
模块: {module_info.get('name', '')}
描述: {func.get('docstring', '无描述')}
返回类型: {func.get('return_type', '未知')}
"""
            documents.append({
                "content": func_doc,
                "metadata": {
                    "type": "function",
                    "source": source,
                    "module": module_info.get("name", ""),
                    "name": func.get("name", ""),
                },
            })

        self.vector_store.add_documents(documents)

"""
序列图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class SequenceDiagramGenerator(BaseDiagramGenerator):
    """
    生成序列图
    
    示例输出:
    sequenceDiagram
        participant User
        participant API
        participant Service
        participant DB
        User->>API: POST /login
        API->>Service: authenticate()
        Service->>DB: query user
        DB-->>Service: user data
        Service-->>API: token
        API-->>User: 200 OK + token
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        participants = data.get("participants", [])
        messages = data.get("messages", [])

        lines = ["sequenceDiagram"]

        if title:
            lines.append(f"    %% {title}")

        for participant in participants:
            name = participant.get("name", "")
            alias = participant.get("alias", "")
            p_type = participant.get("type", "participant")

            if alias:
                lines.append(f"    {p_type} {alias} as {name}")
            else:
                lines.append(f"    {p_type} {name}")

        for msg in messages:
            source = msg.get("source", "")
            target = msg.get("target", "")
            content = msg.get("content", "")
            msg_type = msg.get("type", "sync")

            arrow = self._get_arrow(msg_type)

            if source and target:
                lines.append(f"    {source}{arrow}{target}: {content}")

        return self.wrap_mermaid("\n".join(lines))

    def _get_arrow(self, msg_type: str) -> str:
        arrows = {
            "sync": "->>",
            "async": "-)>>",
            "return": "-->>",
            "sync_left": "<<-",
            "async_left": "<<)-",
            "return_left": "<<--",
        }
        return arrows.get(msg_type, "->>")

    def generate_from_api_flow(self, api_info: dict) -> str:
        """从 API 信息生成序列图"""
        participants = []
        messages = []

        endpoint = api_info.get("endpoint", "")
        method = api_info.get("method", "GET")
        handler = api_info.get("handler", "")
        service = api_info.get("service", "")
        repository = api_info.get("repository", "")

        participants.append({"name": "Client", "type": "actor"})
        participants.append({"name": "API", "type": "participant"})

        if service:
            participants.append({"name": "Service", "type": "participant"})
        if repository:
            participants.append({"name": "Repository", "type": "participant"})
            participants.append({"name": "DB", "type": "participant"})

        messages.append({
            "source": "Client",
            "target": "API",
            "content": f"{method} {endpoint}",
            "type": "sync"
        })

        if service:
            messages.append({
                "source": "API",
                "target": "Service",
                "content": f"{handler}()",
                "type": "sync"
            })

            if repository:
                messages.append({
                    "source": "Service",
                    "target": "Repository",
                    "content": "query()",
                    "type": "sync"
                })

                messages.append({
                    "source": "Repository",
                    "target": "DB",
                    "content": "execute query",
                    "type": "sync"
                })

                messages.append({
                    "source": "DB",
                    "target": "Repository",
                    "content": "result",
                    "type": "return"
                })

                messages.append({
                    "source": "Repository",
                    "target": "Service",
                    "content": "data",
                    "type": "return"
                })

            messages.append({
                "source": "Service",
                "target": "API",
                "content": "response",
                "type": "return"
            })

        messages.append({
            "source": "API",
            "target": "Client",
            "content": "200 OK",
            "type": "return"
        })

        return self.generate({"participants": participants, "messages": messages})

    def generate_module_interaction(
        self,
        modules: list[dict],
        interactions: list[dict]
    ) -> str:
        """生成模块交互序列图"""
        participants = [{"name": m.get("name", ""), "type": "participant"} for m in modules]
        messages = []

        for interaction in interactions:
            messages.append({
                "source": interaction.get("source", ""),
                "target": interaction.get("target", ""),
                "content": interaction.get("message", ""),
                "type": interaction.get("type", "sync")
            })

        return self.generate({"participants": participants, "messages": messages})

"""
状态图生成器
"""

from typing import Any, Optional

from pywiki.generators.diagrams.base import BaseDiagramGenerator


class StateDiagramGenerator(BaseDiagramGenerator):
    """
    生成状态转移图
    
    示例输出:
    stateDiagram-v2
        [*] --> Pending
        Pending --> Processing: submit
        Processing --> Completed: success
        Processing --> Failed: error
        Completed --> [*]
        Failed --> Pending: retry
    """

    def generate(self, data: dict, title: Optional[str] = None) -> str:
        states = data.get("states", [])
        transitions = data.get("transitions", [])

        lines = ["stateDiagram-v2"]

        if title:
            lines.append(f"    %% {title}")

        for state in states:
            state_name = state.get("name", "")
            state_desc = state.get("description", "")
            is_composite = state.get("is_composite", False)
            sub_states = state.get("sub_states", [])

            if is_composite and sub_states:
                lines.append(f"    state {state_name} {{")
                for sub in sub_states:
                    sub_name = sub.get("name", "")
                    lines.append(f"        {sub_name}")
                lines.append("    }")
            else:
                if state_desc:
                    lines.append(f"    {state_name} : {state_desc}")

        for transition in transitions:
            source = transition.get("source", "")
            target = transition.get("target", "")
            event = transition.get("event", "")
            guard = transition.get("guard", "")
            action = transition.get("action", "")

            label_parts = []
            if event:
                label_parts.append(event)
            if guard:
                label_parts.append(f"[{guard}]")
            if action:
                label_parts.append(f"/ {action}")

            label = " ".join(label_parts)

            if source == "[*]" or target == "[*]":
                if label:
                    lines.append(f"    {source} --> {target} : {label}")
                else:
                    lines.append(f"    {source} --> {target}")
            else:
                if label:
                    lines.append(f"    {source} --> {target} : {label}")
                else:
                    lines.append(f"    {source} --> {target}")

        return self.wrap_mermaid("\n".join(lines))

    def generate_from_class_states(
        self,
        class_name: str,
        state_field: str,
        state_transitions: list[dict]
    ) -> str:
        """从类的状态字段生成状态图"""
        states = set()
        transitions = []

        for trans in state_transitions:
            from_state = trans.get("from", "")
            to_state = trans.get("to", "")
            event = trans.get("event", "")
            guard = trans.get("guard", "")
            action = trans.get("action", "")

            states.add(from_state)
            states.add(to_state)

            transitions.append({
                "source": from_state,
                "target": to_state,
                "event": event,
                "guard": guard,
                "action": action
            })

        initial_state = state_transitions[0].get("from", "Initial") if state_transitions else "Initial"
        final_states = self._find_final_states(transitions)

        transitions.insert(0, {"source": "[*]", "target": initial_state})

        for final in final_states:
            transitions.append({"source": final, "target": "[*]"})

        return self.generate({
            "states": [{"name": s} for s in states],
            "transitions": transitions
        }, title=f"{class_name} - {state_field} State Machine")

    def _find_final_states(self, transitions: list[dict]) -> list[str]:
        """找出终态（没有出边的状态）"""
        sources = {t.get("source", "") for t in transitions}
        targets = {t.get("target", "") for t in transitions}
        return list(targets - sources)

    def generate_lifecycle(self, entity: str, lifecycle_stages: list[dict]) -> str:
        """生成实体生命周期状态图"""
        states = []
        transitions = []

        states.append({"name": "[*]"})

        for i, stage in enumerate(lifecycle_stages):
            stage_name = stage.get("name", f"Stage_{i}")
            stage_desc = stage.get("description", "")

            states.append({
                "name": stage_name,
                "description": stage_desc
            })

            if i == 0:
                transitions.append({
                    "source": "[*]",
                    "target": stage_name,
                    "event": "create"
                })

            if i > 0:
                prev_stage = lifecycle_stages[i - 1].get("name", f"Stage_{i-1}")
                transitions.append({
                    "source": prev_stage,
                    "target": stage_name,
                    "event": stage.get("trigger", "next")
                })

        if lifecycle_stages:
            last_stage = lifecycle_stages[-1].get("name", "")
            transitions.append({
                "source": last_stage,
                "target": "[*]",
                "event": "delete"
            })

        return self.generate({
            "states": states,
            "transitions": transitions
        }, title=f"{entity} Lifecycle")

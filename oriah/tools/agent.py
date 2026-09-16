from oriah.tools.registry import ToolRegistry
from oriah.agent.dispatcher import SubagentDispatcher

def register_agent_tools(registry: ToolRegistry, dispatcher: SubagentDispatcher, parent_agent_id: str) -> None:
    role_names = [r.name for r in dispatcher.role_registry.list_roles() if r.name.lower() != "lead"]
    doc = f"Delegate a subtask to a specialized subagent. Valid roles: {', '.join(role_names)}."

    @registry.register("invoke_subagent", doc)
    async def invoke_subagent(role: str, instructions: str) -> str:
        return await dispatcher.spawn(parent_id=parent_agent_id, role=role, instructions=instructions)

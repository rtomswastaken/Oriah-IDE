from oriah.tools.registry import ToolRegistry
from oriah.agent.dispatcher import SubagentDispatcher

def register_agent_tools(registry: ToolRegistry, dispatcher: SubagentDispatcher, parent_agent_id: str) -> None:
    @registry.register("invoke_subagent", "Delegate a subtask to a specialized subagent (coder, exec, researcher).")
    async def invoke_subagent(role: str, instructions: str) -> str:
        return await dispatcher.spawn(parent_id=parent_agent_id, role=role, instructions=instructions)

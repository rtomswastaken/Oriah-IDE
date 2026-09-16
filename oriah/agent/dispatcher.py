import uuid
from typing import Optional
from oriah.config import EngineConfig
from oriah.events import EventBus, SubagentSpawned
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.base import BaseAgent
from oriah.agent.roles import RoleRegistry, RoleDefinition

class SubagentDispatcher:
    def __init__(
        self,
        llm_client: LLMClient,
        base_tools: ToolRegistry,
        event_bus: EventBus,
        config: EngineConfig,
        role_registry: Optional[RoleRegistry] = None,
    ):
        self.llm = llm_client
        self.base_tools = base_tools
        self.bus = event_bus
        self.config = config
        self.role_registry = role_registry or RoleRegistry()

    async def spawn(self, parent_id: str, role: str, instructions: str) -> str:
        role_def = self.role_registry.get(role)
        if not role_def:
            available = ", ".join([r.name for r in self.role_registry.list_roles()])
            return f"Error: Role '{role}' not found. Available roles: {available}"

        child_id = f"{role_def.name}-{uuid.uuid4().hex[:6]}"
        await self.bus.emit(
            SubagentSpawned(
                parent_id=parent_id,
                child_id=child_id,
                role=role_def.name,
                instructions=instructions,
            )
        )

        scoped_tools = self.base_tools.subset(role_def.allowed_tools)

        if role_def.can_spawn_subagents:
            from oriah.tools.agent import register_agent_tools
            register_agent_tools(scoped_tools, self, parent_agent_id=child_id)

        subagent = BaseAgent(
            agent_id=child_id,
            role=role_def.name,
            system_prompt=role_def.system_prompt,
            llm_client=self.llm,
            tool_registry=scoped_tools,
            event_bus=self.bus,
            config=self.config,
        )
        return await subagent.run(instructions)

import uuid
from typing import Dict
from oriah.config import EngineConfig
from oriah.events import EventBus, SubagentSpawned
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.base import BaseAgent
from oriah.agent.roles import ROLES_SYSTEM_PROMPTS

class SubagentDispatcher:
    def __init__(
        self,
        llm_client: LLMClient,
        base_tools: ToolRegistry,
        event_bus: EventBus,
        config: EngineConfig,
    ):
        self.llm = llm_client
        self.base_tools = base_tools
        self.bus = event_bus
        self.config = config

    async def spawn(self, parent_id: str, role: str, instructions: str) -> str:
        child_id = f"{role}-{uuid.uuid4().hex[:6]}"
        await self.bus.emit(
            SubagentSpawned(
                parent_id=parent_id,
                child_id=child_id,
                role=role,
                instructions=instructions,
            )
        )
        system_prompt = ROLES_SYSTEM_PROMPTS.get(
            role.lower(),
            f"You are a specialized {role} agent. Complete the instructions carefully.",
        )
        subagent = BaseAgent(
            agent_id=child_id,
            role=role,
            system_prompt=system_prompt,
            llm_client=self.llm,
            tool_registry=self.base_tools,
            event_bus=self.bus,
            config=self.config,
        )
        return await subagent.run(instructions)

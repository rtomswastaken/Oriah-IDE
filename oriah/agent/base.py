from typing import Any, Dict, Optional
from oriah.config import EngineConfig
from oriah.events import (
    AgentThought,
    EventBus,
    ToolCallCompleted,
    ToolCallRequested,
)
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.context import AgentContext

class BaseAgent:
    def __init__(
        self,
        agent_id: str,
        role: str,
        system_prompt: str,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
        config: EngineConfig,
    ):
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.llm = llm_client
        self.tools = tool_registry
        self.bus = event_bus
        self.config = config
        self.context = AgentContext(system_prompt=system_prompt, max_turns=config.max_steps)

    async def run(self, user_prompt: str) -> str:
        self.context.add_user(user_prompt)
        schemas = self.tools.get_schemas()

        for step in range(self.config.max_steps):
            self.context.compact()
            response = await self.llm.complete(messages=self.context.messages, tools=schemas)

            if response.content:
                await self.bus.emit(AgentThought(agent_id=self.agent_id, thought=response.content))

            if not response.tool_calls:
                return response.content or "(Task completed with no output)"

            self.context.add_assistant(content=response.content, tool_calls=response.tool_calls)

            for tc in response.tool_calls:
                await self.bus.emit(
                    ToolCallRequested(
                        agent_id=self.agent_id,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                    )
                )
                try:
                    res = await self.tools.call(tc.name, tc.arguments)
                    tool_output = str(res)
                    await self.bus.emit(
                        ToolCallCompleted(
                            agent_id=self.agent_id,
                            tool_name=tc.name,
                            result=tool_output,
                        )
                    )
                except Exception as e:
                    tool_output = f"ERROR executing {tc.name}: {str(e)}"
                    await self.bus.emit(
                        ToolCallCompleted(
                            agent_id=self.agent_id,
                            tool_name=tc.name,
                            error=str(e),
                        )
                    )

                self.context.add_tool_result(tool_call_id=tc.id, name=tc.name, result=tool_output)

        return f"Step budget exceeded ({self.config.max_steps} steps)."

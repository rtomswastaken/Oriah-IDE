import asyncio
import uuid
from typing import AsyncIterator, Optional
import httpx
from oriah.config import EngineConfig
from oriah.events import EventBus, AgentEvent, TaskStarted, TaskFinished
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.tools.fs import register_fs_tools
from oriah.tools.exec import register_exec_tools
from oriah.agent.dispatcher import SubagentDispatcher
from oriah.tools.agent import register_agent_tools
from oriah.agent.base import BaseAgent
from oriah.agent.roles import ROLES_SYSTEM_PROMPTS

class AsyncEngine:
    def __init__(self, config: Optional[EngineConfig] = None, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.config = config or EngineConfig()
        self.event_bus = EventBus()
        self.llm = LLMClient(config=self.config, transport=transport)

        # Build tools
        self.tools = ToolRegistry()
        register_fs_tools(self.tools, self.config.resolved_workspace)
        register_exec_tools(self.tools, self.config.resolved_workspace)

        # Dispatcher
        self.dispatcher = SubagentDispatcher(
            llm_client=self.llm,
            base_tools=self.tools,
            event_bus=self.event_bus,
            config=self.config,
        )

        register_agent_tools(self.tools, self.dispatcher, parent_agent_id="lead-main")

    async def run(self, prompt: str) -> AsyncIterator[AgentEvent]:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        queue: asyncio.Queue[Optional[AgentEvent]] = asyncio.Queue()

        async def listener(event: AgentEvent) -> None:
            await queue.put(event)

        self.event_bus.subscribe(listener)
        await self.event_bus.emit(TaskStarted(task_id=task_id, prompt=prompt))

        lead = BaseAgent(
            agent_id="lead-main",
            role="lead",
            system_prompt=ROLES_SYSTEM_PROMPTS["lead"],
            llm_client=self.llm,
            tool_registry=self.tools,
            event_bus=self.event_bus,
            config=self.config,
        )

        async def execute() -> None:
            try:
                summary = await lead.run(prompt)
                await self.event_bus.emit(TaskFinished(task_id=task_id, status="success", summary=summary))
            except Exception as e:
                await self.event_bus.emit(TaskFinished(task_id=task_id, status="error", summary="", error=str(e)))
            finally:
                await queue.put(None)

        task = asyncio.create_task(execute())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        await task

    async def aclose(self) -> None:
        await self.llm.aclose()

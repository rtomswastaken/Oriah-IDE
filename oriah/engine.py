import asyncio
from pathlib import Path
import uuid
from typing import AsyncIterator, Optional
import httpx
from oriah.config import EngineConfig
from oriah.events import EventBus, AgentEvent, TaskStarted, TaskFinished
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.tools.fs import register_fs_tools
from oriah.tools.exec import register_exec_tools
from oriah.tools.custom_loader import load_custom_tools, load_custom_roles
from oriah.agent.dispatcher import SubagentDispatcher
from oriah.tools.agent import register_agent_tools
from oriah.agent.base import BaseAgent
from oriah.agent.roles import RoleRegistry

class AsyncEngine:
    def __init__(self, config: Optional[EngineConfig] = None, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.config = config or EngineConfig()
        self.event_bus = EventBus()
        self.llm = LLMClient(config=self.config, transport=transport)

        # Build tools
        self.tools = ToolRegistry()
        register_fs_tools(self.tools, self.config.resolved_workspace)
        register_exec_tools(self.tools, self.config.resolved_workspace)

        # Roles and custom plugins
        self.role_registry = RoleRegistry()
        self.reload_definitions()

        # Dispatcher
        self.dispatcher = SubagentDispatcher(
            llm_client=self.llm,
            base_tools=self.tools,
            event_bus=self.event_bus,
            config=self.config,
            role_registry=self.role_registry,
        )

        register_agent_tools(self.tools, self.dispatcher, parent_agent_id="lead-main")

    def reload_definitions(self) -> None:
        """Scan workspace for .oriah/custom_tools.py and .oriah/roles/*.py."""
        workspace_path = Path(self.config.resolved_workspace)
        load_custom_tools(self.tools, workspace_path)
        load_custom_roles(self.role_registry, workspace_path)

    def get_lead_system_prompt(self) -> str:
        lead_def = self.role_registry.get("lead")
        base_prompt = lead_def.system_prompt if lead_def else "You are the Lead Orchestrator agent."
        catalog = self.role_registry.build_roles_catalog_prompt()
        return f"{base_prompt}\n\n{catalog}"

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
            system_prompt=self.get_lead_system_prompt(),
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

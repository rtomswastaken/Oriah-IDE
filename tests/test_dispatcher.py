import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from oriah.config import EngineConfig
from oriah.events import EventBus
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.dispatcher import SubagentDispatcher
from oriah.agent.roles import RoleRegistry, RoleDefinition
from oriah.tools.agent import register_agent_tools

@pytest.mark.asyncio
async def test_subagent_dispatcher_execution():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "Subagent code written."}}]
        })

    config = EngineConfig(base_url="http://mock-llm/v1", model="test-model")
    client = LLMClient(config=config, transport=httpx.MockTransport(mock_transport))
    registry = ToolRegistry()
    bus = EventBus()

    dispatcher = SubagentDispatcher(
        llm_client=client,
        base_tools=registry,
        event_bus=bus,
        config=config,
    )

    result = await dispatcher.spawn(parent_id="lead-1", role="coder", instructions="Write add function")
    assert "Subagent code written." in result
    await client.aclose()

@pytest.mark.asyncio
async def test_dispatcher_subagent_tool_isolation():
    role_reg = RoleRegistry()
    role_reg.register(
        RoleDefinition(
            name="isolated_reader",
            description="Read only",
            system_prompt="Read prompt",
            allowed_tools=["read_file"],
            can_spawn_subagents=False,
        )
    )

    base_tools = ToolRegistry()
    @base_tools.register("read_file", "Read file")
    async def read_file(path: str) -> str:
        return "content"

    @base_tools.register("write_file", "Write file")
    async def write_file(path: str, content: str) -> str:
        return "ok"

    bus = EventBus()
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=MagicMock(content="done", tool_calls=[]))
    config = EngineConfig()

    dispatcher = SubagentDispatcher(
        llm_client=llm,
        base_tools=base_tools,
        event_bus=bus,
        config=config,
        role_registry=role_reg,
    )

    res = await dispatcher.spawn(parent_id="parent-1", role="isolated_reader", instructions="Read doc")
    assert res == "done"

@pytest.mark.asyncio
async def test_dispatcher_unknown_role_returns_error():
    role_reg = RoleRegistry()
    base_tools = ToolRegistry()
    bus = EventBus()
    llm = MagicMock()
    config = EngineConfig()

    dispatcher = SubagentDispatcher(
        llm_client=llm,
        base_tools=base_tools,
        event_bus=bus,
        config=config,
        role_registry=role_reg,
    )

    res = await dispatcher.spawn(parent_id="parent-1", role="nonexistent", instructions="do stuff")
    assert "Error: Role 'nonexistent' not found" in res

@pytest.mark.asyncio
async def test_agent_tools_dynamic_role_description():
    role_reg = RoleRegistry()
    role_reg.register(RoleDefinition(name="custom_reviewer", description="Reviews", system_prompt="Review"))
    base_tools = ToolRegistry()
    dispatcher = SubagentDispatcher(
        llm_client=MagicMock(),
        base_tools=base_tools,
        event_bus=EventBus(),
        config=EngineConfig(),
        role_registry=role_reg,
    )
    reg = ToolRegistry()
    register_agent_tools(reg, dispatcher, parent_agent_id="lead-1")
    assert "invoke_subagent" in reg._tools
    doc = reg._tools["invoke_subagent"].description
    assert "custom_reviewer" in doc
    assert "coder" in doc

import json
import pytest
import httpx
from oriah.config import EngineConfig
from oriah.events import EventBus
from oriah.tools.registry import ToolRegistry
from oriah.llm.client import LLMClient
from oriah.agent.base import BaseAgent

@pytest.mark.asyncio
async def test_agent_single_turn_text():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "I finished the task."}}]
        })

    config = EngineConfig(base_url="http://mock-llm/v1", model="test-model")
    client = LLMClient(config=config, transport=httpx.MockTransport(mock_transport))
    registry = ToolRegistry()
    bus = EventBus()

    agent = BaseAgent(
        agent_id="test-agent",
        role="Tester",
        system_prompt="You are a test agent.",
        llm_client=client,
        tool_registry=registry,
        event_bus=bus,
        config=config,
    )

    result = await agent.run("Do something")
    assert result == "I finished the task."
    await client.aclose()

@pytest.mark.asyncio
async def test_agent_tool_execution_loop():
    turn = 0
    def mock_transport(request: httpx.Request) -> httpx.Response:
        nonlocal turn
        turn += 1
        if turn == 1:
            return httpx.Response(200, json={
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "c1",
                            "type": "function",
                            "function": {"name": "dummy_tool", "arguments": "{\"x\": 42}"}
                        }]
                    }
                }]
            })
        else:
            return httpx.Response(200, json={
                "choices": [{"message": {"role": "assistant", "content": "Calculation done."}}]
            })

    config = EngineConfig(base_url="http://mock-llm/v1", model="test-model")
    client = LLMClient(config=config, transport=httpx.MockTransport(mock_transport))
    registry = ToolRegistry()

    @registry.register("dummy_tool", "Dummy tool for test")
    async def dummy_tool(x: int) -> str:
        return f"result_{x}"

    bus = EventBus()
    agent = BaseAgent(
        agent_id="loop-agent",
        role="Calculator",
        system_prompt="Calculate",
        llm_client=client,
        tool_registry=registry,
        event_bus=bus,
        config=config,
    )

    result = await agent.run("Compute 42")
    assert result == "Calculation done."
    assert turn == 2
    await client.aclose()

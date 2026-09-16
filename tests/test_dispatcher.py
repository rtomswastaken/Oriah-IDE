import pytest
import httpx
from oriah.config import EngineConfig
from oriah.events import EventBus
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.dispatcher import SubagentDispatcher

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

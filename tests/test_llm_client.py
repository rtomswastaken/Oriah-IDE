import json
import pytest
import httpx
from oriah.config import EngineConfig
from oriah.llm.client import LLMClient, LLMResponse

@pytest.mark.asyncio
async def test_llm_client_chat_completion():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        data = json.loads(request.content)
        assert data["model"] == "test-model"
        assert len(data["messages"]) == 1
        return httpx.Response(
            200,
            json={
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Hello world"
                    }
                }]
            }
        )

    config = EngineConfig(base_url="http://mock-llm/v1", model="test-model")
    client = LLMClient(config=config, transport=httpx.MockTransport(mock_transport))
    resp = await client.complete([{"role": "user", "content": "hi"}])

    assert isinstance(resp, LLMResponse)
    assert resp.content == "Hello world"
    assert resp.tool_calls == []
    await client.aclose()

@pytest.mark.asyncio
async def test_llm_client_tool_call_parsing():
    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": "call_123",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": "{\"path\": \"src/main.py\"}"
                            }
                        }]
                    }
                }]
            }
        )

    config = EngineConfig(base_url="http://mock-llm/v1", model="test-model")
    client = LLMClient(config=config, transport=httpx.MockTransport(mock_transport))
    resp = await client.complete([{"role": "user", "content": "read code"}])

    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "read_file"
    assert resp.tool_calls[0].arguments == {"path": "src/main.py"}
    await client.aclose()

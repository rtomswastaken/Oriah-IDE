import pytest
import httpx
from oriah.config import EngineConfig
from oriah.engine import AsyncEngine
from oriah.events import TaskStarted, TaskFinished

@pytest.mark.asyncio
async def test_async_engine_run(tmp_path):
    def mock_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "choices": [{"message": {"role": "assistant", "content": "Done!"}}]
        })

    config = EngineConfig(
        base_url="http://mock-llm/v1",
        model="test-model",
        workspace_root=str(tmp_path),
    )
    engine = AsyncEngine(config=config, transport=httpx.MockTransport(mock_transport))

    events = []
    async for event in engine.run("Test task"):
        events.append(event)

    types = [type(e) for e in events]
    assert TaskStarted in types
    assert TaskFinished in types
    await engine.aclose()

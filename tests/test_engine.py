import pytest
import httpx
from pathlib import Path
from oriah.config import EngineConfig
from oriah.engine import AsyncEngine
from oriah.events import TaskStarted, TaskFinished

@pytest.mark.asyncio
async def test_async_engine_run(tmp_path: Path):
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

@pytest.mark.asyncio
async def test_engine_loads_custom_roles_and_tools(tmp_path: Path):
    oriah_dir = tmp_path / ".oriah"
    roles_dir = oriah_dir / "roles"
    roles_dir.mkdir(parents=True)

    (roles_dir / "custom_worker.py").write_text(
        "from oriah.agent.roles import RoleDefinition\n\n"
        "role = RoleDefinition(name='custom_worker', description='Worker', system_prompt='Do work')\n"
    )

    (oriah_dir / "custom_tools.py").write_text(
        "from oriah.tools.registry import custom_tool\n\n"
        "@custom_tool(name='magic_ping')\n"
        "async def magic_ping() -> str:\n"
        "    return 'pong'\n"
    )

    config = EngineConfig(
        base_url="http://mock-llm/v1",
        model="test-model",
        workspace_root=str(tmp_path),
    )
    engine = AsyncEngine(config=config)

    assert engine.role_registry.get("custom_worker") is not None
    assert "magic_ping" in engine.tools._tools
    await engine.aclose()

@pytest.mark.asyncio
async def test_engine_lead_prompt_includes_catalog(tmp_path: Path):
    config = EngineConfig(workspace_root=str(tmp_path))
    engine = AsyncEngine(config=config)
    prompt = engine.get_lead_system_prompt()
    assert "coder" in prompt
    assert "researcher" in prompt
    assert "Available Subagent Roles:" in prompt
    await engine.aclose()

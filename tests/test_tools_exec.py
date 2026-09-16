import pytest
from oriah.tools.registry import ToolRegistry
from oriah.tools.exec import register_exec_tools

@pytest.fixture
def workspace(tmp_path):
    return str(tmp_path)

@pytest.fixture
def registry(workspace):
    reg = ToolRegistry()
    register_exec_tools(reg, workspace)
    return reg

@pytest.mark.asyncio
async def test_run_command_success(registry):
    res = await registry.call("run_command", {"cmd": "echo 'hello world'"})
    assert "hello world" in res
    assert "Exit code: 0" in res

@pytest.mark.asyncio
async def test_run_command_failure(registry):
    res = await registry.call("run_command", {"cmd": "nonexistent_command_xyz_123"})
    assert "Exit code" in res

@pytest.mark.asyncio
async def test_run_command_timeout(registry):
    res = await registry.call("run_command", {"cmd": "sleep 5", "timeout": 1})
    assert "timed out" in res.lower()

@pytest.mark.asyncio
async def test_run_command_dangerous_blocked(registry):
    with pytest.raises(PermissionError, match="Blocked dangerous command"):
        await registry.call("run_command", {"cmd": "rm -rf /"})

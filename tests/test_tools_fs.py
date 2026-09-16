import os
import pytest
from oriah.tools.registry import ToolRegistry
from oriah.tools.fs import register_fs_tools

@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "workspace"
    ws.mkdir()
    return str(ws)

@pytest.fixture
def registry(workspace):
    reg = ToolRegistry()
    register_fs_tools(reg, workspace)
    return reg

@pytest.mark.asyncio
async def test_write_and_read_file(registry, workspace):
    res_write = await registry.call("write_file", {"path": "hello.txt", "content": "Line 1\nLine 2\nLine 3"})
    assert "Created" in res_write

    res_read = await registry.call("read_file", {"path": "hello.txt", "offset": 1, "limit": 2})
    assert "1: Line 1" in res_read
    assert "2: Line 2" in res_read
    assert "3: Line 3" not in res_read

@pytest.mark.asyncio
async def test_write_file_no_overwrite_error(registry, workspace):
    await registry.call("write_file", {"path": "test.txt", "content": "initial"})
    with pytest.raises(ValueError, match="already exists"):
        await registry.call("write_file", {"path": "test.txt", "content": "new"})

@pytest.mark.asyncio
async def test_patch_file(registry, workspace):
    await registry.call("write_file", {"path": "patch.txt", "content": "def foo():\n    return False\n"})
    patch_res = await registry.call("patch_file", {
        "path": "patch.txt",
        "target": "    return False",
        "replacement": "    return True"
    })
    assert "Patched" in patch_res
    read_res = await registry.call("read_file", {"path": "patch.txt"})
    assert "return True" in read_res

@pytest.mark.asyncio
async def test_grep_and_find_files(registry, workspace):
    await registry.call("write_file", {"path": "src/app.py", "content": "print('TARGET_STRING')"})
    find_res = await registry.call("find_files", {"pattern": "*.py"})
    assert "src/app.py" in find_res

    grep_res = await registry.call("grep_search", {"query": "TARGET_STRING"})
    assert "src/app.py:1: print('TARGET_STRING')" in grep_res

@pytest.mark.asyncio
async def test_workspace_boundary_enforcement(registry, workspace):
    with pytest.raises(PermissionError, match="Escaping workspace"):
        await registry.call("read_file", {"path": "../secret.txt"})

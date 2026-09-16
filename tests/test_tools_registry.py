import pytest
from oriah.tools.registry import ToolRegistry, custom_tool

@pytest.mark.asyncio
async def test_tool_registry_subset():
    reg = ToolRegistry()

    @reg.register("tool_a", "Tool A description")
    async def tool_a(x: int) -> int:
        return x + 1

    @reg.register("tool_b", "Tool B description")
    async def tool_b(y: str) -> str:
        return f"hello {y}"

    sub = reg.subset(["tool_a"])
    assert "tool_a" in sub._tools
    assert "tool_b" not in sub._tools
    assert await sub.call("tool_a", {"x": 5}) == 6

    with pytest.raises(KeyError):
        await sub.call("tool_b", {"y": "world"})

@pytest.mark.asyncio
async def test_tool_registry_subset_wildcard():
    reg = ToolRegistry()

    @reg.register("tool_x", "Tool X")
    async def tool_x() -> str:
        return "x"

    sub = reg.subset(["*"])
    assert "tool_x" in sub._tools

@pytest.mark.asyncio
async def test_custom_tool_decorator():
    @custom_tool(name="echo_tool", description="Echoes text back")
    async def sample_echo(text: str) -> str:
        return f"echo: {text}"

    reg = ToolRegistry()
    reg.register_custom_fn(sample_echo)

    assert "echo_tool" in reg._tools
    res = await reg.call("echo_tool", {"text": "ping"})
    assert res == "echo: ping"

import pytest
from oriah.events import (
    EventBus,
    TaskStarted,
    AgentThought,
    ToolCallRequested,
    ToolCallCompleted,
    TaskFinished,
)

@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    bus = EventBus()
    received = []

    async def listener(event):
        received.append(event)

    bus.subscribe(listener)
    event = TaskStarted(task_id="task-1", prompt="test prompt")
    await bus.emit(event)

    assert len(received) == 1
    assert isinstance(received[0], TaskStarted)
    assert received[0].task_id == "task-1"
    assert received[0].prompt == "test prompt"

@pytest.mark.asyncio
async def test_event_serialization():
    event = ToolCallRequested(
        agent_id="lead-1",
        tool_name="read_file",
        arguments={"path": "main.py"}
    )
    assert event.agent_id == "lead-1"
    assert event.tool_name == "read_file"
    assert event.arguments == {"path": "main.py"}
    data = event.model_dump()
    assert data["event_type"] == "ToolCallRequested"

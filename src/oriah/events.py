from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, Field

class AgentEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: str = Field(default="")

    def model_post_init(self, __context: Any) -> None:
        if not self.event_type:
            self.event_type = self.__class__.__name__

class TaskStarted(AgentEvent):
    task_id: str
    prompt: str

class AgentThought(AgentEvent):
    agent_id: str
    thought: str

class ToolCallRequested(AgentEvent):
    agent_id: str
    tool_name: str
    arguments: Dict[str, Any]

class ToolCallCompleted(AgentEvent):
    agent_id: str
    tool_name: str
    result: Optional[str] = None
    error: Optional[str] = None

class SubagentSpawned(AgentEvent):
    parent_id: str
    child_id: str
    role: str
    instructions: str

class TaskFinished(AgentEvent):
    task_id: str
    status: str
    summary: str
    error: Optional[str] = None

Listener = Callable[[AgentEvent], Coroutine[Any, Any, None]]

class EventBus:
    def __init__(self) -> None:
        self._listeners: List[Listener] = []

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def emit(self, event: AgentEvent) -> None:
        for listener in self._listeners:
            await listener(event)

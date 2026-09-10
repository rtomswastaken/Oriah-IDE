# Local Agentic Workflow Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an asynchronous headless local multi-agent system in Python that connects to local OpenAI-compatible LLM endpoints (Ollama, vLLM, LM Studio) and executes code authoring, file patching, search, and subprocess commands autonomously.

**Architecture:** AsyncEngine orchestrating a typed EventBus, an Async OpenAI-compatible LLMClient, a central ToolRegistry with filesystem and process execution tools, and a SubagentDispatcher managing specialized Lead, Coder, Exec, and Researcher agent roles.

**Tech Stack:** Python 3.12+, `pydantic>=2.0`, `httpx>=0.27.0`, `pytest>=8.0`, `pytest-asyncio>=0.23`.

## Global Constraints
- Target workspace directory boundary enforcement on all filesystem and command operations.
- Truncate large tool outputs (over 2,000 characters) to protect local LLM context windows.
- No UI components; all functionality exposed via importable Python library and streaming CLI runner (`oriah-agent`).
- Full unit test coverage for all tools, client, agent ReAct loop, and dispatcher before completion.

---

### Task 1: Scaffolding, Virtual Environment & Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/oriah/__init__.py`
- Create: `src/oriah/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: `EngineConfig` class in `src/oriah/config.py` with fields:
  - `base_url: str = "http://localhost:11434/v1"`
  - `model: str = "qwen2.5-coder:14b"`
  - `api_key: str = "local"`
  - `workspace_root: str = "."`
  - `timeout: float = 60.0`
  - `max_steps: int = 25`
  - `context_limit: int = 8192`

- [ ] **Step 1: Write failing config test**

`tests/test_config.py`:
```python
import os
from oriah.config import EngineConfig

def test_engine_config_defaults():
    config = EngineConfig()
    assert config.base_url == "http://localhost:11434/v1"
    assert config.model == "qwen2.5-coder:14b"
    assert config.timeout == 60.0
    assert config.max_steps == 25
    assert os.path.isabs(config.resolved_workspace)

def test_engine_config_custom():
    config = EngineConfig(base_url="http://localhost:1234/v1", model="deepseek-coder:6.7b", timeout=30.0)
    assert config.base_url == "http://localhost:1234/v1"
    assert config.model == "deepseek-coder:6.7b"
    assert config.timeout == 30.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah'`

- [ ] **Step 3: Implement pyproject.toml and config**

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "oriah"
version = "0.1.0"
description = "Headless local agentic workflow engine for Oriah IDE"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
oriah-agent = "oriah.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]
```

`src/oriah/__init__.py`:
```python
"""Oriah local agentic workflow engine."""
from oriah.config import EngineConfig

__all__ = ["EngineConfig"]
```

`src/oriah/config.py`:
```python
import os
from pathlib import Path
from pydantic import BaseModel, Field

class EngineConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434/v1")
    model: str = Field(default="qwen2.5-coder:14b")
    api_key: str = Field(default="local")
    workspace_root: str = Field(default=".")
    timeout: float = Field(default=60.0)
    max_steps: int = Field(default=25)
    context_limit: int = Field(default=8192)

    @property
    def resolved_workspace(self) -> str:
        return str(Path(self.workspace_root).resolve())
```

`tests/__init__.py`:
```python
"""Test package."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add pyproject.toml src/ tests/
rtk git commit -m "feat: setup project scaffolding and EngineConfig"
```

---

### Task 2: Typed Event Bus System

**Files:**
- Create: `src/oriah/events.py`
- Create: `tests/test_events.py`

**Interfaces:**
- Consumes: None
- Produces:
  - Base class `AgentEvent(BaseModel)`
  - Subclasses: `TaskStarted`, `AgentThought`, `ToolCallRequested`, `ToolCallCompleted`, `SubagentSpawned`, `TaskFinished`
  - `EventBus`:
    - `subscribe(callback: Callable[[AgentEvent], Awaitable[None]]) -> None`
    - `emit(event: AgentEvent) -> None` (async)

- [ ] **Step 1: Write failing event bus tests**

`tests/test_events.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.events'`

- [ ] **Step 3: Implement events.py**

`src/oriah/events.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/oriah/events.py tests/test_events.py
rtk git commit -m "feat: implement typed EventBus and AgentEvents"
```

---

### Task 3: Tool Registry & Filesystem Tools

**Files:**
- Create: `src/oriah/tools/__init__.py`
- Create: `src/oriah/tools/registry.py`
- Create: `src/oriah/tools/fs.py`
- Create: `tests/test_tools_fs.py`

**Interfaces:**
- Consumes: None
- Produces:
  - `ToolRegistry`: `register(name, description)(fn)`, `get_schemas() -> list[dict]`, `call(name, kwargs) -> Any`
  - `register_fs_tools(registry: ToolRegistry, workspace_root: str) -> None`:
    - `read_file(path: str, offset: int = 1, limit: int = 200) -> str`
    - `write_file(path: str, content: str, overwrite: bool = False) -> str`
    - `patch_file(path: str, target: str, replacement: str) -> str`
    - `grep_search(query: str, path: str = ".", regex: bool = False) -> str`
    - `find_files(pattern: str = "*", path: str = ".") -> str`

- [ ] **Step 1: Write failing filesystem tool tests**

`tests/test_tools_fs.py`:
```python
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
async def test_workspace_boundary_enforcement(registry, workspace):
    with pytest.raises(PermissionError, match="Escaping workspace"):
        await registry.call("read_file", {"path": "../secret.txt"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_tools_fs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.tools'`

- [ ] **Step 3: Implement ToolRegistry and filesystem tools**

`src/oriah/tools/__init__.py`:
```python
from oriah.tools.registry import ToolRegistry

__all__ = ["ToolRegistry"]
```

`src/oriah/tools/registry.py`:
```python
import inspect
from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, create_model

class Tool:
    def __init__(self, name: str, description: str, func: Callable[..., Coroutine[Any, Any, Any]]):
        self.name = name
        self.description = description
        self.func = func
        self.param_model = self._create_param_model()

    def _create_param_model(self) -> type[BaseModel]:
        sig = inspect.signature(self.func)
        fields: Dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[param_name] = (param_type, default)
        return create_model(f"{self.name}_params", **fields)

    def to_openai_schema(self) -> Dict[str, Any]:
        schema = self.param_model.model_json_schema()
        # Clean titles to match standard tool call schemas
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema
            }
        }

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._tools[name] = Tool(name=name, description=description, func=func)
            return func
        return decorator

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}")
        tool = self._tools[name]
        validated = tool.param_model(**arguments)
        res = tool.func(**validated.model_dump())
        if inspect.isawaitable(res):
            return await res
        return res
```

`src/oriah/tools/fs.py`:
```python
import fnmatch
import os
import re
from pathlib import Path
from typing import List, Optional
from oriah.tools.registry import ToolRegistry

def _resolve_safe_path(workspace_root: str, path_str: str) -> Path:
    base = Path(workspace_root).resolve()
    target = (base / path_str).resolve()
    if not str(target).startswith(str(base)):
        raise PermissionError(f"Escaping workspace boundary: '{path_str}'")
    return target

def register_fs_tools(registry: ToolRegistry, workspace_root: str) -> None:
    @registry.register("read_file", "Read line-numbered contents of a file in the workspace.")
    async def read_file(path: str, offset: int = 1, limit: int = 200) -> str:
        target = _resolve_safe_path(workspace_root, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start = max(1, offset)
        end = min(len(lines), start + limit - 1)
        selected = lines[start - 1:end]
        output = [f"{i}: {line.rstrip()}" for i, line in enumerate(selected, start=start)]
        return "\n".join(output) if output else "(empty file or range)"

    @registry.register("write_file", "Create or overwrite a file in the workspace.")
    async def write_file(path: str, content: str, overwrite: bool = False) -> str:
        target = _resolve_safe_path(workspace_root, path)
        if target.exists() and not overwrite:
            raise ValueError(f"File already exists: '{path}'. Pass overwrite=True to replace.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created {path} ({len(content)} bytes)"

    @registry.register("patch_file", "Atomically replace a single exact contiguous block of code.")
    async def patch_file(path: str, target: str, replacement: str) -> str:
        file_path = _resolve_safe_path(workspace_root, path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        occurrences = content.count(target)
        if occurrences == 0:
            raise ValueError(f"Target snippet not found in {path}")
        if occurrences > 1:
            raise ValueError(f"Target snippet found {occurrences} times in {path}; must be unique.")
        new_content = content.replace(target, replacement, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Patched {path}"

    @registry.register("grep_search", "Search files in the workspace for exact text or regex.")
    async def grep_search(query: str, path: str = ".", regex: bool = False) -> str:
        search_root = _resolve_safe_path(workspace_root, path)
        pattern = re.compile(query if regex else re.escape(query))
        results = []
        ignored_dirs = {".git", "node_modules", "target", "__pycache__", ".venv", "dist", "build"}

        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                fpath = Path(root) / file
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, start=1):
                            if pattern.search(line):
                                rel = fpath.relative_to(Path(workspace_root).resolve())
                                results.append(f"{rel}:{line_no}: {line.strip()}")
                                if len(results) >= 50:
                                    results.append("... (capped at 50 results)")
                                    return "\n".join(results)
                except Exception:
                    continue
        return "\n".join(results) if results else "No matches found."

    @registry.register("find_files", "Search files in the workspace matching a glob pattern.")
    async def find_files(pattern: str = "*", path: str = ".") -> str:
        search_root = _resolve_safe_path(workspace_root, path)
        ignored_dirs = {".git", "node_modules", "target", "__pycache__", ".venv", "dist", "build"}
        matches = []

        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for name in files + dirs:
                if fnmatch.fnmatch(name, pattern):
                    full = Path(root) / name
                    rel = full.relative_to(Path(workspace_root).resolve())
                    matches.append(str(rel))
                    if len(matches) >= 100:
                        matches.append("... (capped at 100 files)")
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "No matching files."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_tools_fs.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/oriah/tools/ tests/test_tools_fs.py
rtk git commit -m "feat: implement ToolRegistry and safe filesystem tools"
```

---

### Task 4: Subprocess Execution Tools

**Files:**
- Create: `src/oriah/tools/exec.py`
- Create: `tests/test_tools_exec.py`

**Interfaces:**
- Consumes: `ToolRegistry` from `src/oriah/tools/registry.py`
- Produces: `register_exec_tools(registry: ToolRegistry, workspace_root: str) -> None`:
  - `run_command(cmd: str, cwd: str = ".", timeout: int = 60) -> str`

- [ ] **Step 1: Write failing exec tools tests**

`tests/test_tools_exec.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_tools_exec.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.tools.exec'`

- [ ] **Step 3: Implement exec.py**

`src/oriah/tools/exec.py`:
```python
import asyncio
from pathlib import Path
from oriah.tools.registry import ToolRegistry
from oriah.tools.fs import _resolve_safe_path

def register_exec_tools(registry: ToolRegistry, workspace_root: str) -> None:
    @registry.register("run_command", "Execute a terminal shell command in the workspace directory.")
    async def run_command(cmd: str, cwd: str = ".", timeout: int = 60) -> str:
        safe_cwd = _resolve_safe_path(workspace_root, cwd)

        # Destructive command safety guard
        destructive = ["rm -rf /", "rm -rf /*", "mkfs", ":(){ :|:& };:"]
        if any(d in cmd for d in destructive):
            raise PermissionError(f"Blocked dangerous command: {cmd}")

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(safe_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return f"Command timed out after {timeout} seconds."

        stdout_str = stdout_data.decode("utf-8", errors="replace").strip()
        stderr_str = stderr_data.decode("utf-8", errors="replace").strip()

        # Truncate large output to 2000 chars
        if len(stdout_str) > 2000:
            stdout_str = stdout_str[:2000] + "\n... [stdout truncated]"
        if len(stderr_str) > 2000:
            stderr_str = stderr_str[:2000] + "\n... [stderr truncated]"

        out_lines = [f"Exit code: {proc.returncode}"]
        if stdout_str:
            out_lines.append(f"STDOUT:\n{stdout_str}")
        if stderr_str:
            out_lines.append(f"STDERR:\n{stderr_str}")

        return "\n".join(out_lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_tools_exec.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/oriah/tools/exec.py tests/test_tools_exec.py
rtk git commit -m "feat: implement safe subprocess execution tools"
```

---

### Task 5: OpenAI-Compatible LLM Client

**Files:**
- Create: `src/oriah/llm/__init__.py`
- Create: `src/oriah/llm/client.py`
- Create: `tests/test_llm_client.py`

**Interfaces:**
- Consumes: `EngineConfig` from `src/oriah/config.py`
- Produces:
  - `LLMResponse`: `content: Optional[str]`, `tool_calls: List[ToolCall]`
  - `ToolCall`: `id: str`, `name: str`, `arguments: Dict[str, Any]`
  - `LLMClient`:
    - `async def complete(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> LLMResponse`

- [ ] **Step 1: Write failing LLM client tests with mock server**

`tests/test_llm_client.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_llm_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.llm'`

- [ ] **Step 3: Implement LLM client**

`src/oriah/llm/__init__.py`:
```python
from oriah.llm.client import LLMClient, LLMResponse, ToolCall

__all__ = ["LLMClient", "LLMResponse", "ToolCall"]
```

`src/oriah/llm/client.py`:
```python
import json
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field
from oriah.config import EngineConfig

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class LLMResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)

class LLMClient:
    def __init__(self, config: EngineConfig, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout,
            transport=transport,
        )

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        url = "/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools

        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]["message"]
        content = choice.get("content")
        raw_tools = choice.get("tool_calls", [])

        parsed_tools: List[ToolCall] = []
        for item in raw_tools:
            func = item["function"]
            args = func["arguments"]
            parsed_args = json.loads(args) if isinstance(args, str) else args
            parsed_tools.append(
                ToolCall(
                    id=item.get("id", "call_default"),
                    name=func["name"],
                    arguments=parsed_args,
                )
            )

        return LLMResponse(content=content, tool_calls=parsed_tools)

    async def aclose(self) -> None:
        await self._client.aclose()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/oriah/llm/ tests/test_llm_client.py
rtk git commit -m "feat: implement async OpenAI-compatible LLMClient"
```

---

### Task 6: ReAct Agent Loop & Context Compaction

**Files:**
- Create: `src/oriah/agent/__init__.py`
- Create: `src/oriah/agent/context.py`
- Create: `src/oriah/agent/base.py`
- Create: `tests/test_agent_react.py`

**Interfaces:**
- Consumes: `LLMClient`, `ToolRegistry`, `EventBus`
- Produces:
  - `AgentContext`: Handles message history, pinned prompts, and history compaction.
  - `BaseAgent`: Implements `run(prompt: str) -> str`. Executes ReAct tool loop, emits events, terminates on `report_done` or `max_steps`.

- [ ] **Step 1: Write failing ReAct agent tests**

`tests/test_agent_react.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_agent_react.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.agent'`

- [ ] **Step 3: Implement context.py and base.py**

`src/oriah/agent/__init__.py`:
```python
from oriah.agent.base import BaseAgent
from oriah.agent.context import AgentContext

__all__ = ["BaseAgent", "AgentContext"]
```

`src/oriah/agent/context.py`:
```python
from typing import Any, Dict, List

class AgentContext:
    def __init__(self, system_prompt: str, max_turns: int = 25):
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str | None, tool_calls: list | None = None) -> None:
        msg: Dict[str, Any] = {"role": "assistant"}
        if content is not None:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json_dumps(tc.arguments)},
                }
                for tc in tool_calls
            ]
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, result: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": result,
        })

    def compact(self) -> None:
        # Keep system prompt (index 0) and original prompt (index 1).
        # Truncate old tool messages if history gets excessively long.
        if len(self.messages) > 30:
            pinned = self.messages[:2]
            tail = self.messages[-20:]
            summary = {
                "role": "system",
                "content": f"[History compacted: {len(self.messages) - 22} prior turns summarized]"
            }
            self.messages = [pinned[0], pinned[1], summary] + tail

import json
def json_dumps(obj: Any) -> str:
    return json.dumps(obj)
```

`src/oriah/agent/base.py`:
```python
from typing import Any, Dict, Optional
from oriah.config import EngineConfig
from oriah.events import (
    AgentThought,
    EventBus,
    ToolCallCompleted,
    ToolCallRequested,
)
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.context import AgentContext

class BaseAgent:
    def __init__(
        self,
        agent_id: str,
        role: str,
        system_prompt: str,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
        config: EngineConfig,
    ):
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.llm = llm_client
        self.tools = tool_registry
        self.bus = event_bus
        self.config = config
        self.context = AgentContext(system_prompt=system_prompt, max_turns=config.max_steps)

    async def run(self, user_prompt: str) -> str:
        self.context.add_user(user_prompt)
        schemas = self.tools.get_schemas()

        for step in range(self.config.max_steps):
            self.context.compact()
            response = await self.llm.complete(messages=self.context.messages, tools=schemas)

            if response.content:
                await self.bus.emit(AgentThought(agent_id=self.agent_id, thought=response.content))

            if not response.tool_calls:
                return response.content or "(Task completed with no output)"

            self.context.add_assistant(content=response.content, tool_calls=response.tool_calls)

            for tc in response.tool_calls:
                await self.bus.emit(
                    ToolCallRequested(
                        agent_id=self.agent_id,
                        tool_name=tc.name,
                        arguments=tc.arguments,
                    )
                )
                try:
                    res = await self.tools.call(tc.name, tc.arguments)
                    tool_output = str(res)
                    await self.bus.emit(
                        ToolCallCompleted(
                            agent_id=self.agent_id,
                            tool_name=tc.name,
                            result=tool_output,
                        )
                    )
                except Exception as e:
                    tool_output = f"ERROR executing {tc.name}: {str(e)}"
                    await self.bus.emit(
                        ToolCallCompleted(
                            agent_id=self.agent_id,
                            tool_name=tc.name,
                            error=str(e),
                        )
                    )

                self.context.add_tool_result(tool_call_id=tc.id, name=tc.name, result=tool_output)

        return f"Step budget exceeded ({self.config.max_steps} steps)."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_agent_react.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/oriah/agent/ tests/test_agent_react.py
rtk git commit -m "feat: implement BaseAgent ReAct loop and AgentContext"
```

---

### Task 7: Subagent Dispatcher & Specialized Roles

**Files:**
- Create: `src/oriah/agent/dispatcher.py`
- Create: `src/oriah/agent/roles.py`
- Create: `src/oriah/tools/agent.py`
- Create: `tests/test_dispatcher.py`

**Interfaces:**
- Consumes: `BaseAgent`, `ToolRegistry`, `EventBus`, `LLMClient`
- Produces:
  - `SubagentDispatcher`: `spawn(role: str, instructions: str) -> str`
  - `register_agent_tools(registry: ToolRegistry, dispatcher: SubagentDispatcher)`
  - Role factories: `create_lead_agent`, `create_coder_agent`, `create_exec_agent`, `create_researcher_agent`

- [ ] **Step 1: Write failing dispatcher and role tests**

`tests/test_dispatcher.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_dispatcher.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.agent.dispatcher'`

- [ ] **Step 3: Implement dispatcher, roles, and agent tools**

`src/oriah/agent/roles.py`:
```python
ROLES_SYSTEM_PROMPTS = {
    "lead": (
        "You are the Lead Orchestrator agent. Your job is to analyze user tasks, "
        "break them down into focused subtasks, and dispatch specialized subagents "
        "(coder, exec, researcher). When subagents finish, summarize the final outcome."
    ),
    "coder": (
        "You are the Coder agent. You specialize in reading files, writing clean code, "
        "and applying surgical contiguous line patches with patch_file. Focus only on code changes."
    ),
    "exec": (
        "You are the Exec agent. You run shell commands, compilers, linters, and test suites "
        "using run_command. Inspect outputs, return clear diagnostics."
    ),
    "researcher": (
        "You are the Researcher agent. You inspect project directories, grep codebase patterns, "
        "and map dependencies. Do not make code edits."
    ),
}
```

`src/oriah/agent/dispatcher.py`:
import uuid
from typing import Dict
from oriah.config import EngineConfig
from oriah.events import EventBus, SubagentSpawned
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.base import BaseAgent
from oriah.agent.roles import ROLES_SYSTEM_PROMPTS

class SubagentDispatcher:
    def __init__(
        self,
        llm_client: LLMClient,
        base_tools: ToolRegistry,
        event_bus: EventBus,
        config: EngineConfig,
    ):
        self.llm = llm_client
        self.base_tools = base_tools
        self.bus = event_bus
        self.config = config

    async def spawn(self, parent_id: str, role: str, instructions: str) -> str:
        child_id = f"{role}-{uuid.uuid4().hex[:6]}"
        await self.bus.emit(
            SubagentSpawned(
                parent_id=parent_id,
                child_id=child_id,
                role=role,
                instructions=instructions,
            )
        )
        system_prompt = ROLES_SYSTEM_PROMPTS.get(
            role.lower(),
            f"You are a specialized {role} agent. Complete the instructions carefully.",
        )
        subagent = BaseAgent(
            agent_id=child_id,
            role=role,
            system_prompt=system_prompt,
            llm_client=self.llm,
            tool_registry=self.base_tools,
            event_bus=self.bus,
            config=self.config,
        )
        return await subagent.run(instructions)
```

`src/oriah/tools/agent.py`:
```python
from oriah.tools.registry import ToolRegistry
from oriah.agent.dispatcher import SubagentDispatcher

def register_agent_tools(registry: ToolRegistry, dispatcher: SubagentDispatcher, parent_agent_id: str) -> None:
    @registry.register("invoke_subagent", "Delegate a subtask to a specialized subagent (coder, exec, researcher).")
    async def invoke_subagent(role: str, instructions: str) -> str:
        return await dispatcher.spawn(parent_id=parent_agent_id, role=role, instructions=instructions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_dispatcher.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/oriah/agent/dispatcher.py src/oriah/agent/roles.py src/oriah/tools/agent.py tests/test_dispatcher.py
rtk git commit -m "feat: implement SubagentDispatcher and specialized agent roles"
```

---

### Task 8: AsyncEngine Orchestrator & CLI Runner

**Files:**
- Create: `src/oriah/engine.py`
- Create: `src/oriah/cli.py`
- Create: `tests/test_engine.py`

**Interfaces:**
- Consumes: All prior components
- Produces:
  - `AsyncEngine`: `async def run(prompt: str) -> AsyncIterator[AgentEvent]`
  - CLI command: `oriah-agent run "task"` and `oriah-agent repl`

- [ ] **Step 1: Write failing AsyncEngine tests**

`tests/test_engine.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk python3 -m pytest tests/test_engine.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.engine'`

- [ ] **Step 3: Implement AsyncEngine and CLI**

`src/oriah/engine.py`:
```python
import asyncio
import uuid
from typing import AsyncIterator, Optional
import httpx
from oriah.config import EngineConfig
from oriah.events import EventBus, AgentEvent, TaskStarted, TaskFinished
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.tools.fs import register_fs_tools
from oriah.tools.exec import register_exec_tools
from oriah.agent.dispatcher import SubagentDispatcher
from oriah.tools.agent import register_agent_tools
from oriah.agent.base import BaseAgent
from oriah.agent.roles import ROLES_SYSTEM_PROMPTS

class AsyncEngine:
    def __init__(self, config: Optional[EngineConfig] = None, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.config = config or EngineConfig()
        self.event_bus = EventBus()
        self.llm = LLMClient(config=self.config, transport=transport)

        # Build tools
        self.tools = ToolRegistry()
        register_fs_tools(self.tools, self.config.resolved_workspace)
        register_exec_tools(self.tools, self.config.resolved_workspace)

        # Dispatcher
        self.dispatcher = SubagentDispatcher(
            llm_client=self.llm,
            base_tools=self.tools,
            event_bus=self.event_bus,
            config=self.config,
        )

        register_agent_tools(self.tools, self.dispatcher, parent_agent_id="lead-main")

    async def run(self, prompt: str) -> AsyncIterator[AgentEvent]:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        queue: asyncio.Queue[Optional[AgentEvent]] = asyncio.Queue()

        async def listener(event: AgentEvent) -> None:
            await queue.put(event)

        self.event_bus.subscribe(listener)
        await self.event_bus.emit(TaskStarted(task_id=task_id, prompt=prompt))

        lead = BaseAgent(
            agent_id="lead-main",
            role="lead",
            system_prompt=ROLES_SYSTEM_PROMPTS["lead"],
            llm_client=self.llm,
            tool_registry=self.tools,
            event_bus=self.event_bus,
            config=self.config,
        )

        async def execute() -> None:
            try:
                summary = await lead.run(prompt)
                await self.event_bus.emit(TaskFinished(task_id=task_id, status="success", summary=summary))
            except Exception as e:
                await self.event_bus.emit(TaskFinished(task_id=task_id, status="error", summary="", error=str(e)))
            finally:
                await queue.put(None)

        task = asyncio.create_task(execute())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

        await task
```

`src/oriah/cli.py`:
```python
import argparse
import asyncio
import sys
from oriah.config import EngineConfig
from oriah.engine import AsyncEngine
from oriah.events import (
    AgentThought,
    SubagentSpawned,
    TaskFinished,
    TaskStarted,
    ToolCallCompleted,
    ToolCallRequested,
)

async def run_task(prompt: str, base_url: str, model: str) -> None:
    config = EngineConfig(base_url=base_url, model=model)
    engine = AsyncEngine(config=config)

    print(f"\n[Oriah Engine] Running task: {prompt}")
    print(f"[Oriah Engine] Model: {model} @ {base_url}\n" + "-" * 50)

    async for event in engine.run(prompt):
        if isinstance(event, TaskStarted):
            print(f"[*] Task Started: {event.task_id}")
        elif isinstance(event, AgentThought):
            print(f"\n[{event.agent_id}] {event.thought}")
        elif isinstance(event, ToolCallRequested):
            print(f"  -> Tool Call: {event.tool_name}({event.arguments})")
        elif isinstance(event, ToolCallCompleted):
            if event.error:
                print(f"  <- Tool Error: {event.error}")
            else:
                snippet = (event.result or "")[:120].replace("\n", " ")
                print(f"  <- Tool Result: {snippet}...")
        elif isinstance(event, SubagentSpawned):
            print(f"\n[+] Spawned Subagent [{event.child_id}] (Role: {event.role})")
        elif isinstance(event, TaskFinished):
            print("\n" + "=" * 50)
            if event.status == "success":
                print(f"[SUCCESS] Final Summary:\n{event.summary}")
            else:
                print(f"[ERROR] Task Failed: {event.error}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Oriah Local Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Execute an agent task")
    run_p.add_argument("prompt", help="Task description")
    run_p.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible base URL")
    run_p.add_argument("--model", default="qwen2.5-coder:14b", help="Model name")

    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(run_task(args.prompt, args.base_url, args.model))

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk python3 -m pytest tests/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `rtk python3 -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
rtk git add src/oriah/engine.py src/oriah/cli.py tests/test_engine.py
rtk git commit -m "feat: implement AsyncEngine orchestrator and CLI runner"
```

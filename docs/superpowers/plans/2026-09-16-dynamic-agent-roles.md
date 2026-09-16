# Dynamic Agent Roles and Custom Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement dynamic, code-first agent roles and user-defined custom tools with strict tool isolation and dynamic subagent dispatching in Oriah IDE.

**Architecture:** A centralized `RoleRegistry` loads built-in roles (`lead`, `coder`, `exec`, `researcher`) and scans `.oriah/roles/*.py` for custom `RoleDefinition` modules. A dynamic custom loader in `oriah/tools/custom_loader.py` imports workspace tools from `.oriah/custom_tools.py` into `ToolRegistry`. `SubagentDispatcher` enforces subagent sandboxing by constructing an isolated `ToolRegistry.subset(role.allowed_tools)` and dynamically passing available role schemas to the lead orchestrator.

**Tech Stack:** Python 3.10+, `importlib.util`, pytest, pytest-asyncio, httpx.

**Spec:** [docs/superpowers/specs/2026-09-16-dynamic-agent-roles-design.md](file:///Users/rtoms/Oriah-IDE/docs/superpowers/specs/2026-09-16-dynamic-agent-roles-design.md)

## Global Constraints

- Use Python standard library (`importlib.util`, `pathlib`, `dataclasses`) for dynamic imports without heavy dependencies.
- Defensive error handling: bad user role or tool files log warnings and fallback without crashing engine.
- Every CLI command must be prefixed with `rtk`.
- Colorable emojis / text glyphs only; no colored emojis.

---

### Task 1: RoleDefinition Dataclass & RoleRegistry

**Files:**
- Modify: `oriah/agent/roles.py`
- Create: `tests/test_roles.py`

**Interfaces:**
- Produces:
  - `RoleDefinition(name: str, description: str, system_prompt: str, allowed_tools: list[str], model_override: Optional[str] = None, can_spawn_subagents: bool = False, max_steps: Optional[int] = None)`
  - `RoleRegistry`:
    - `register(role: RoleDefinition) -> None`
    - `get(name: str) -> Optional[RoleDefinition]`
    - `list_roles() -> list[RoleDefinition]`
    - `build_roles_catalog_prompt() -> str`

- [ ] **Step 1: Write the failing test**

File: `tests/test_roles.py`
```python
from oriah.agent.roles import RoleDefinition, RoleRegistry, BUILTIN_ROLES

def test_builtin_roles_exist():
    registry = RoleRegistry()
    assert registry.get("lead") is not None
    assert registry.get("coder") is not None
    assert registry.get("exec") is not None
    assert registry.get("researcher") is not None
    assert registry.get("lead").can_spawn_subagents is True
    assert registry.get("coder").can_spawn_subagents is False

def test_custom_role_registration():
    registry = RoleRegistry()
    custom = RoleDefinition(
        name="tester",
        description="Runs test suites",
        system_prompt="You are a test runner",
        allowed_tools=["run_command"],
        can_spawn_subagents=False,
    )
    registry.register(custom)
    fetched = registry.get("tester")
    assert fetched is not None
    assert fetched.name == "tester"
    assert "run_command" in fetched.allowed_tools

def test_roles_catalog_prompt():
    registry = RoleRegistry()
    prompt = registry.build_roles_catalog_prompt()
    assert "lead" in prompt
    assert "coder" in prompt
    assert "researcher" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_roles.py -v`
Expected: FAIL with `ImportError` or missing attributes.

- [ ] **Step 3: Write minimal implementation**

File: `oriah/agent/roles.py`
```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class RoleDefinition:
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str] = field(default_factory=list)
    model_override: Optional[str] = None
    can_spawn_subagents: bool = False
    max_steps: Optional[int] = None

BUILTIN_ROLES: List[RoleDefinition] = [
    RoleDefinition(
        name="lead",
        description="Lead Orchestrator: analyzes tasks, decomposes goals, and dispatches subagents.",
        system_prompt=(
            "You are the Lead Orchestrator agent. Your job is to analyze user tasks, "
            "break them down into focused subtasks, and dispatch specialized subagents. "
            "When subagents finish, synthesize their findings and summarize the final outcome."
        ),
        allowed_tools=["read_file", "list_dir", "grep_search", "invoke_subagent"],
        can_spawn_subagents=True,
    ),
    RoleDefinition(
        name="coder",
        description="Coder: specializes in reading files, writing clean code, and applying surgical patches.",
        system_prompt=(
            "You are the Coder agent. You specialize in reading files, writing clean code, "
            "and applying surgical contiguous line patches with patch_file. Focus only on code changes."
        ),
        allowed_tools=["read_file", "write_file", "patch_file", "list_dir", "grep_search"],
        can_spawn_subagents=False,
    ),
    RoleDefinition(
        name="exec",
        description="Exec: runs shell commands, compilers, linters, and test suites.",
        system_prompt=(
            "You are the Exec agent. You run shell commands, compilers, linters, and test suites "
            "using run_command. Inspect outputs and return clear diagnostics."
        ),
        allowed_tools=["read_file", "run_command", "list_dir"],
        can_spawn_subagents=False,
    ),
    RoleDefinition(
        name="researcher",
        description="Researcher: read-only inspector for directory structure and dependency mapping.",
        system_prompt=(
            "You are the Researcher agent. You inspect project directories, grep codebase patterns, "
            "and map dependencies. Do not make code edits."
        ),
        allowed_tools=["read_file", "list_dir", "grep_search"],
        can_spawn_subagents=False,
    ),
]

ROLES_SYSTEM_PROMPTS = {r.name: r.system_prompt for r in BUILTIN_ROLES}

class RoleRegistry:
    def __init__(self) -> None:
        self._roles: Dict[str, RoleDefinition] = {}
        for role in BUILTIN_ROLES:
            self.register(role)

    def register(self, role: RoleDefinition) -> None:
        self._roles[role.name.lower()] = role

    def get(self, name: str) -> Optional[RoleDefinition]:
        return self._roles.get(name.lower())

    def list_roles(self) -> List[RoleDefinition]:
        return list(self._roles.values())

    def build_roles_catalog_prompt(self) -> str:
        lines = ["Available Subagent Roles:"]
        for r in self._roles.values():
            if r.name.lower() == "lead":
                continue
            lines.append(f"- '{r.name}': {r.description} (Allowed tools: {', '.join(r.allowed_tools)})")
        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_roles.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:
```bash
rtk git add oriah/agent/roles.py tests/test_roles.py && rtk git commit -m "feat(agent): implement RoleDefinition and RoleRegistry with built-in roles"
```

---

### Task 2: ToolRegistry Scoping & @custom_tool Decorator

**Files:**
- Modify: `oriah/tools/registry.py`
- Modify: `tests/test_tools_fs.py` (or create `tests/test_tools_registry.py`)

**Interfaces:**
- Produces:
  - `ToolRegistry.subset(allowed_tools: List[str]) -> ToolRegistry`
  - `custom_tool(name: Optional[str] = None, description: Optional[str] = None)`
  - `ToolRegistry.register_custom_fn(fn: Any, name: Optional[str] = None, description: Optional[str] = None)`

- [ ] **Step 1: Write the failing test**

File: `tests/test_tools_registry.py`
```python
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
async def test_custom_tool_decorator():
    @custom_tool(name="echo_tool", description="Echoes text back")
    async def sample_echo(text: str) -> str:
        return f"echo: {text}"

    reg = ToolRegistry()
    reg.register_custom_fn(sample_echo)

    assert "echo_tool" in reg._tools
    res = await reg.call("echo_tool", {"text": "ping"})
    assert res == "echo: ping"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_tools_registry.py -v`
Expected: FAIL with `AttributeError: 'ToolRegistry' object has no attribute 'subset'`.

- [ ] **Step 3: Write minimal implementation**

File: `oriah/tools/registry.py`
Update `oriah/tools/registry.py` to add `subset` method, `custom_tool` decorator, and `register_custom_fn`:
```python
from typing import Any, Callable, Dict, List, Optional
import inspect

def custom_tool(name: Optional[str] = None, description: Optional[str] = None):
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, "_is_custom_tool", True)
        setattr(fn, "_tool_name", name or fn.__name__)
        setattr(fn, "_tool_description", description or fn.__doc__ or "")
        return fn
    return decorator

# Inside ToolRegistry:
    def subset(self, allowed_tools: List[str]) -> "ToolRegistry":
        new_reg = ToolRegistry()
        if "*" in allowed_tools:
            new_reg._tools = dict(self._tools)
            return new_reg
        for name in allowed_tools:
            if name in self._tools:
                new_reg._tools[name] = self._tools[name]
        return new_reg

    def register_custom_fn(self, fn: Callable[..., Any], name: Optional[str] = None, description: Optional[str] = None) -> None:
        tool_name = name or getattr(fn, "_tool_name", fn.__name__)
        desc = description or getattr(fn, "_tool_description", fn.__doc__ or "")
        self.register(tool_name, desc)(fn)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_tools_registry.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:
```bash
rtk git add oriah/tools/registry.py tests/test_tools_registry.py && rtk git commit -m "feat(tools): add ToolRegistry.subset and custom_tool decorator"
```

---

### Task 3: Dynamic Custom Loader for Tools and Roles

**Files:**
- Create: `oriah/tools/custom_loader.py`
- Create: `tests/test_custom_loader.py`

**Interfaces:**
- Produces:
  - `load_custom_tools(registry: ToolRegistry, workspace_root: Path) -> list[str]`
  - `load_custom_roles(role_registry: RoleRegistry, workspace_root: Path) -> list[str]`

- [ ] **Step 1: Write the failing test**

File: `tests/test_custom_loader.py`
```python
import pytest
from pathlib import Path
from oriah.tools.registry import ToolRegistry
from oriah.agent.roles import RoleRegistry
from oriah.tools.custom_loader import load_custom_tools, load_custom_roles

def test_load_custom_tools_from_workspace(tmp_path: Path):
    oriah_dir = tmp_path / ".oriah"
    oriah_dir.mkdir()
    custom_tools_file = oriah_dir / "custom_tools.py"
    custom_tools_file.write_text(
        "from oriah.tools.registry import custom_tool\n\n"
        "@custom_tool(name='workspace_ping', description='Returns pong')\n"
        "async def workspace_ping() -> str:\n"
        "    return 'pong'\n"
    )

    registry = ToolRegistry()
    loaded = load_custom_tools(registry, tmp_path)
    assert "workspace_ping" in loaded
    assert "workspace_ping" in registry._tools

def test_load_custom_roles_from_workspace(tmp_path: Path):
    roles_dir = tmp_path / ".oriah" / "roles"
    roles_dir.mkdir(parents=True)
    custom_role_file = roles_dir / "qa_lead.py"
    custom_role_file.write_text(
        "from oriah.agent.roles import RoleDefinition\n\n"
        "role = RoleDefinition(\n"
        "    name='qa_lead',\n"
        "    description='Lead QA specialist',\n"
        "    system_prompt='You lead QA tests',\n"
        "    allowed_tools=['read_file', 'run_command'],\n"
        ")\n"
    )

    role_registry = RoleRegistry()
    loaded = load_custom_roles(role_registry, tmp_path)
    assert "qa_lead" in loaded
    role = role_registry.get("qa_lead")
    assert role is not None
    assert role.name == "qa_lead"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_custom_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'oriah.tools.custom_loader'`.

- [ ] **Step 3: Write minimal implementation**

File: `oriah/tools/custom_loader.py`
```python
import importlib.util
import logging
from pathlib import Path
from typing import List
from oriah.tools.registry import ToolRegistry
from oriah.agent.roles import RoleRegistry, RoleDefinition

logger = logging.getLogger("oriah.custom_loader")

def load_custom_tools(registry: ToolRegistry, workspace_root: Path) -> List[str]:
    custom_tools_path = workspace_root / ".oriah" / "custom_tools.py"
    if not custom_tools_path.is_file():
        return []

    loaded: List[str] = []
    try:
        spec = importlib.util.spec_from_file_location("oriah_custom_tools", str(custom_tools_path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if callable(obj) and getattr(obj, "_is_custom_tool", False):
                    registry.register_custom_fn(obj)
                    tool_name = getattr(obj, "_tool_name", attr_name)
                    loaded.append(tool_name)
    except Exception as e:
        logger.warning("Failed loading custom tools from %s: %s", custom_tools_path, e)

    return loaded

def load_custom_roles(role_registry: RoleRegistry, workspace_root: Path) -> List[str]:
    roles_dir = workspace_root / ".oriah" / "roles"
    if not roles_dir.is_dir():
        return []

    loaded: List[str] = []
    for py_file in roles_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        try:
            mod_name = f"oriah_role_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(mod_name, str(py_file))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                role_obj = getattr(module, "role", None)
                if isinstance(role_obj, RoleDefinition):
                    role_registry.register(role_obj)
                    loaded.append(role_obj.name)
                else:
                    for attr_name in dir(module):
                        cand = getattr(module, attr_name)
                        if isinstance(cand, RoleDefinition):
                            role_registry.register(cand)
                            loaded.append(cand.name)
        except Exception as e:
            logger.warning("Failed loading custom role from %s: %s", py_file, e)

    return loaded
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_custom_loader.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:
```bash
rtk git add oriah/tools/custom_loader.py tests/test_custom_loader.py && rtk git commit -m "feat(tools): implement dynamic custom tools and roles loader"
```

---

### Task 4: SubagentDispatcher Dynamic Role Routing & Tool Sandboxing

**Files:**
- Modify: `oriah/agent/dispatcher.py`
- Modify: `oriah/tools/agent.py`
- Modify: `tests/test_dispatcher.py`

**Interfaces:**
- Consumes: `RoleRegistry`, `ToolRegistry.subset`
- Produces: `SubagentDispatcher(..., role_registry: RoleRegistry)`
  - `spawn(parent_id: str, role: str, instructions: str) -> str`
  - Isolates tools: child registry contains only tools in `role_def.allowed_tools`
  - Conditionally registers `invoke_subagent` if `role_def.can_spawn_subagents is True`

- [ ] **Step 1: Write the failing test**

File: `tests/test_dispatcher.py`
Update `test_dispatcher.py` to verify:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from oriah.agent.dispatcher import SubagentDispatcher
from oriah.agent.roles import RoleRegistry, RoleDefinition
from oriah.tools.registry import ToolRegistry
from oriah.events import EventBus
from oriah.config import EngineConfig

@pytest.mark.asyncio
async def test_dispatcher_subagent_tool_isolation():
    role_reg = RoleRegistry()
    role_reg.register(
        RoleDefinition(
            name="isolated_reader",
            description="Read only",
            system_prompt="Read prompt",
            allowed_tools=["read_file"],
            can_spawn_subagents=False,
        )
    )

    base_tools = ToolRegistry()
    @base_tools.register("read_file", "Read file")
    async def read_file(path: str) -> str:
        return "content"

    @base_tools.register("write_file", "Write file")
    async def write_file(path: str, content: str) -> str:
        return "ok"

    bus = EventBus()
    llm = MagicMock()
    llm.complete = AsyncMock(return_value=MagicMock(content="done", tool_calls=[]))
    config = EngineConfig()

    dispatcher = SubagentDispatcher(
        llm_client=llm,
        base_tools=base_tools,
        event_bus=bus,
        config=config,
        role_registry=role_reg,
    )

    res = await dispatcher.spawn(parent_id="parent-1", role="isolated_reader", instructions="Read doc")
    assert res == "done"

@pytest.mark.asyncio
async def test_dispatcher_unknown_role_returns_error():
    role_reg = RoleRegistry()
    base_tools = ToolRegistry()
    bus = EventBus()
    llm = MagicMock()
    config = EngineConfig()

    dispatcher = SubagentDispatcher(
        llm_client=llm,
        base_tools=base_tools,
        event_bus=bus,
        config=config,
        role_registry=role_reg,
    )

    res = await dispatcher.spawn(parent_id="parent-1", role="nonexistent", instructions="do stuff")
    assert "Error: Role 'nonexistent' not found" in res
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_dispatcher.py -v`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

File: `oriah/agent/dispatcher.py`
Update `SubagentDispatcher` to accept `role_registry: Optional[RoleRegistry] = None`, fetch `RoleDefinition`, sandbox `tool_registry`:
```python
import uuid
from typing import Optional
from oriah.config import EngineConfig
from oriah.events import EventBus, SubagentSpawned
from oriah.llm.client import LLMClient
from oriah.tools.registry import ToolRegistry
from oriah.agent.base import BaseAgent
from oriah.agent.roles import RoleRegistry, RoleDefinition

class SubagentDispatcher:
    def __init__(
        self,
        llm_client: LLMClient,
        base_tools: ToolRegistry,
        event_bus: EventBus,
        config: EngineConfig,
        role_registry: Optional[RoleRegistry] = None,
    ):
        self.llm = llm_client
        self.base_tools = base_tools
        self.bus = event_bus
        self.config = config
        self.role_registry = role_registry or RoleRegistry()

    async def spawn(self, parent_id: str, role: str, instructions: str) -> str:
        role_def = self.role_registry.get(role)
        if not role_def:
            available = ", ".join([r.name for r in self.role_registry.list_roles()])
            return f"Error: Role '{role}' not found. Available roles: {available}"

        child_id = f"{role_def.name}-{uuid.uuid4().hex[:6]}"
        await self.bus.emit(
            SubagentSpawned(
                parent_id=parent_id,
                child_id=child_id,
                role=role_def.name,
                instructions=instructions,
            )
        )

        scoped_tools = self.base_tools.subset(role_def.allowed_tools)

        if role_def.can_spawn_subagents:
            from oriah.tools.agent import register_agent_tools
            register_agent_tools(scoped_tools, self, parent_agent_id=child_id)

        subagent = BaseAgent(
            agent_id=child_id,
            role=role_def.name,
            system_prompt=role_def.system_prompt,
            llm_client=self.llm,
            tool_registry=scoped_tools,
            event_bus=self.bus,
            config=self.config,
        )
        return await subagent.run(instructions)
```

File: `oriah/tools/agent.py`
Update `register_agent_tools` to dynamically include registered roles in the tool description:
```python
from oriah.tools.registry import ToolRegistry
from oriah.agent.dispatcher import SubagentDispatcher

def register_agent_tools(registry: ToolRegistry, dispatcher: SubagentDispatcher, parent_agent_id: str) -> None:
    role_names = [r.name for r in dispatcher.role_registry.list_roles() if r.name.lower() != "lead"]
    doc = f"Delegate a subtask to a specialized subagent. Valid roles: {', '.join(role_names)}."

    @registry.register("invoke_subagent", doc)
    async def invoke_subagent(role: str, instructions: str) -> str:
        return await dispatcher.spawn(parent_id=parent_agent_id, role=role, instructions=instructions)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk pytest tests/test_dispatcher.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:
```bash
rtk git add oriah/agent/dispatcher.py oriah/tools/agent.py tests/test_dispatcher.py && rtk git commit -m "feat(agent): support dynamic role dispatching and tool isolation in SubagentDispatcher"
```

---

### Task 5: AsyncEngine Integration, Dynamic Prompting & End-to-End Tests

**Files:**
- Modify: `oriah/engine.py`
- Modify: `tests/test_engine.py`
- Modify: `tests/test_oriah.py`

**Interfaces:**
- `AsyncEngine`:
  - Instantiates `RoleRegistry`
  - Calls `load_custom_tools` and `load_custom_roles` from workspace root
  - Enriches Lead Agent system prompt with dynamic roles catalog
  - Exposes `reload_definitions()` method

- [ ] **Step 1: Write the failing test**

File: `tests/test_engine.py`
```python
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from oriah.engine import AsyncEngine
from oriah.config import EngineConfig

@pytest.mark.asyncio
async def test_engine_loads_custom_roles_and_tools(tmp_path: Path):
    oriah_dir = tmp_path / ".oriah"
    roles_dir = oriah_dir / "roles"
    roles_dir.mkdir(parents=True)

    (roles_dir / "custom_role.py").write_text(
        "from oriah.agent.roles import RoleDefinition\n\n"
        "role = RoleDefinition(name='custom_worker', description='Worker', system_prompt='Do work')\n"
    )

    (oriah_dir / "custom_tools.py").write_text(
        "from oriah.tools.registry import custom_tool\n\n"
        "@custom_tool(name='magic_ping')\n"
        "async def magic_ping() -> str:\n"
        "    return 'pong'\n"
    )

    config = EngineConfig(workspace_root=str(tmp_path))
    engine = AsyncEngine(config=config)

    assert engine.role_registry.get("custom_worker") is not None
    assert "magic_ping" in engine.tools._tools
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk pytest tests/test_engine.py -v`
Expected: FAIL with missing `role_registry` or dynamic loader calls.

- [ ] **Step 3: Write minimal implementation**

File: `oriah/engine.py`
Wire `RoleRegistry`, `load_custom_tools`, `load_custom_roles`, and enrich Lead system prompt:
```python
from pathlib import Path
from oriah.agent.roles import RoleRegistry
from oriah.tools.custom_loader import load_custom_tools, load_custom_roles

# In AsyncEngine.__init__:
        self.role_registry = RoleRegistry()
        workspace_path = Path(self.config.resolved_workspace)
        load_custom_tools(self.tools, workspace_path)
        load_custom_roles(self.role_registry, workspace_path)

        self.dispatcher = SubagentDispatcher(
            llm_client=self.llm,
            base_tools=self.tools,
            event_bus=self.event_bus,
            config=self.config,
            role_registry=self.role_registry,
        )

        register_agent_tools(self.tools, self.dispatcher, parent_agent_id="lead-main")

# In AsyncEngine.run:
        lead_def = self.role_registry.get("lead")
        lead_prompt = lead_def.system_prompt if lead_def else "You are the Lead Orchestrator agent."
        catalog = self.role_registry.build_roles_catalog_prompt()
        system_prompt = f"{lead_prompt}\n\n{catalog}"

        lead = BaseAgent(
            agent_id="lead-main",
            role="lead",
            system_prompt=system_prompt,
            llm_client=self.llm,
            tool_registry=self.tools,
            event_bus=self.event_bus,
            config=self.config,
        )
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `rtk pytest tests/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

Run:
```bash
rtk git add oriah/engine.py tests/test_engine.py && rtk git commit -m "feat(engine): wire dynamic custom roles, tools loader, and role catalog prompt"
```

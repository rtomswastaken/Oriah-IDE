# Dynamic Agent Roles and Custom Tools System Specification

## Overview
Oriah IDE requires an extensible, code-first architecture allowing users to define custom agent roles and custom tool functions directly in their workspace. The architecture isolates tools per subagent role, provides hot-reloading without IDE restarts, and allows custom model routing.

---

## Directory & File Architecture

```text
Oriah-IDE/
├── .oriah/
│   ├── custom_tools.py          # Workspace user tools decorated with @custom_tool
│   └── roles/                   # Code-first role definitions
│       ├── reviewer.py          # Custom role example
│       └── architect.py         # Custom role example
└── oriah/
    ├── agent/
    │   ├── roles.py             # RoleDefinition dataclass, RoleRegistry & built-in roles
    │   ├── dispatcher.py        # SubagentDispatcher with tool isolation
    │   └── base.py              # BaseAgent execution loop
    └── tools/
        ├── registry.py          # ToolRegistry with subset() & custom_tool decorator
        ├── custom_loader.py     # Dynamic importer for .oriah/custom_tools.py and .oriah/roles/
        ├── fs.py                # Built-in filesystem tools
        ├── exec.py              # Built-in command execution tools
        └── agent.py             # Built-in subagent invocation tool
```

---

## Core Data Structures and Interfaces

### 1. `RoleDefinition` (`oriah/agent/roles.py`)
```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RoleDefinition:
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str] = field(default_factory=list)
    model_override: Optional[str] = None
    can_spawn_subagents: bool = False
    max_steps: Optional[int] = None
```

### 2. Built-in Default Roles
The system provides 4 baseline built-in roles in `oriah/agent/roles.py`:
1. `lead`: Orchestrates tasks, breaks down requirements, dispatches subagents.
   - `allowed_tools`: `["read_file", "list_dir", "grep_search", "invoke_subagent"]`
   - `can_spawn_subagents`: `True`
2. `coder`: Reads files, writes files, applies surgical patches.
   - `allowed_tools`: `["read_file", "write_file", "patch_file", "list_dir", "grep_search"]`
   - `can_spawn_subagents`: `False`
3. `exec`: Runs commands, tests, linters, and inspects outputs.
   - `allowed_tools`: `["read_file", "run_command", "list_dir"]`
   - `can_spawn_subagents`: `False`
4. `researcher`: Read-only inspection of codebase, dependency mapping.
   - `allowed_tools`: `["read_file", "list_dir", "grep_search"]`
   - `can_spawn_subagents`: `False`

### 3. Custom Tool Registration (`oriah/tools/registry.py`)
```python
def custom_tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator for registering custom functions as agent tools."""
    ...
```
In `.oriah/custom_tools.py`:
```python
from oriah.tools.registry import custom_tool

@custom_tool(name="http_get", description="Perform an HTTP GET request to a given URL.")
async def http_get(url: str) -> str:
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=15.0)
        return resp.text[:2000]
```

---

## ToolRegistry Scoping & Isolation

`ToolRegistry` (`oriah/tools/registry.py`) is enhanced with:
```python
def subset(self, allowed_tool_names: List[str]) -> "ToolRegistry":
    """Return a new ToolRegistry instance containing only the specified tools."""
    scoped = ToolRegistry()
    for name in allowed_tool_names:
        if name in self._tools:
            scoped._tools[name] = self._tools[name]
    return scoped
```
When `allowed_tools` contains `["*"]`, all registered tools are permitted.

---

## Dynamic Module Loader (`oriah/tools/custom_loader.py`)

The loader utilizes Python's standard `importlib.util` module:
1. `load_custom_tools(registry: ToolRegistry, workspace_root: Path) -> List[str]`:
   - Checks if `<workspace_root>/.oriah/custom_tools.py` exists.
   - Dynamically loads module via `spec_from_file_location`.
   - Discovers decorated tools and registers them into `registry`.
   - Returns list of registered custom tool names.
2. `load_custom_roles(role_registry: RoleRegistry, workspace_root: Path) -> List[str]`:
   - Checks if `<workspace_root>/.oriah/roles/` exists.
   - Iterates through all `*.py` files in directory.
   - Dynamically loads module; inspects exports for instances of `RoleDefinition` or a `role` variable.
   - Registers or overrides role in `role_registry`.
   - Returns list of loaded custom role names.

Both loaders use defensive `try/except` blocks: syntax errors or exceptions in user files log warnings to `AppState.agent_logs` and do not interrupt IDE execution.

---

## Subagent Dispatching & Execution Flow

1. **Lead Agent Prompt & Schema Injection**:
   - `Lead` system prompt dynamically receives catalog of all available roles from `RoleRegistry.list_roles()`.
   - Tool definition for `invoke_subagent` dynamically enumerates valid role names in parameter description.
2. **Subagent Spawn**:
   - User or Lead Agent invokes `invoke_subagent(role="<role_name>", instructions="<task>")`.
   - `SubagentDispatcher.spawn(...)`:
     - Looks up role in `RoleRegistry`. If not found, returns descriptive error message.
     - Creates isolated `ToolRegistry`: `isolated_tools = base_tools.subset(role.allowed_tools)`.
     - If `role.can_spawn_subagents` is `True`, adds `invoke_subagent` to `isolated_tools`.
     - Selects `LLMClient`: if `role.model_override` is specified, uses client configured for that model; otherwise reuses parent `LLMClient`.
     - Instantiates `BaseAgent(..., tool_registry=isolated_tools)`.
     - Runs subagent ReAct loop and streams events (`AgentThought`, `ToolCallRequested`, `ToolCallCompleted`) to `EventBus`.
     - Returns final subagent text summary back to caller.

---

## Error Handling

1. **Syntax / Import Failure in Custom Code**:
   - Caught in `custom_loader.py`. Error details appended to log; invalid file ignored.
2. **Unknown Role Call**:
   - Returns string: `"Error: Role '<requested>' not found. Available roles: <comma_separated_list>"`.
3. **Disallowed Tool Invocation**:
   - If an LLM attempts to call an unregistered or disallowed tool, `ToolRegistry.call` raises `KeyError`, intercepted and returned as `"Error: Tool '<name>' not permitted for role '<role>'"`.
4. **Tool Execution Exception**:
   - Trapped inside `BaseAgent.run` and emitted via `ToolCallCompleted(error=str(e))`. LLM receives error output to plan correction.

---

## Testing Plan

### 1. Unit Tests (`tests/test_custom_loader.py`)
- Test loading valid `custom_tools.py` with `@custom_tool` functions.
- Test loading valid `RoleDefinition` from `.oriah/roles/` module.
- Test handling corrupted Python files (syntax error, missing attributes) gracefully without raising.

### 2. Isolation Tests (`tests/test_tool_isolation.py`)
- Verify `ToolRegistry.subset(...)` copies only requested tools.
- Verify subagent instantiated with restricted tools schema excludes disallowed tools.
- Verify `can_spawn_subagents=False` omits `invoke_subagent` from subagent tool schema.

### 3. Dispatcher Tests (`tests/test_dynamic_dispatcher.py`)
- Test `SubagentDispatcher.spawn` dispatches custom user-defined role.
- Test `SubagentDispatcher.spawn` returns error string for unknown role.
- Verify event bus receives `SubagentSpawned` with correct role identifier.

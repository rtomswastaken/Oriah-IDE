# Local Agentic Workflow Engine Design Specification

## 1. Overview
This document specifies the architecture and technical requirements for the **Oriah Local Agentic Workflow Engine**, an asynchronous, headless multi-agent system implemented in Python. The engine enables local LLMs (via OpenAI-compatible endpoints such as Ollama, vLLM, LM Studio, and llama.cpp) to autonomously inspect, plan, write, patch, and execute code within a bounded workspace.

No graphical user interface is required for this phase. The engine operates via an asynchronous Python API and a streaming CLI runner, with an event bus architecture prepared for future IDE backend integration.

## 2. Core Architecture

```
User / CLI Task
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                         AsyncEngine                         │
│  - Configuration (model, base_url, timeout, context limits) │
│  - Session Lifecycle & Workspace Sandbox Guard              │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
       ┌───────────────┐               ┌───────────────┐
       │   EventBus    │               │   LLMClient   │
       │ (Async PubSub)│               │ (OpenAI HTTP) │
       └───────┬───────┘               └───────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│                     SubagentDispatcher                      │
│                                                             │
│   ┌───────────────┐        delegates        ┌────────────┐  │
│   │   LeadAgent   ├────────────────────────►│ CoderAgent │  │
│   │ (Decompose &  │                         └────────────┘  │
│   │  Orchestrate) ├────────┐                ┌────────────┐  │
│   └───────────────┘        └───────────────►│ ExecAgent  │  │
│                                             └────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │ calls
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        ToolRegistry                         │
│  - File Tools (read, write, patch, grep, find)              │
│  - Process Tools (run_command, kill, status)                │
│  - Agent Tools (invoke_subagent, send_message, report_done) │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 AsyncEngine
- Coordinates task submission, execution timeouts, and cancellation.
- Manages workspace boundaries (prevents operations escaping the project root).
- Provides async generator `engine.run(prompt: str) -> AsyncIterator[AgentEvent]`.

### 2.2 LLMClient
- Communicates with local OpenAI-compatible APIs (`/v1/chat/completions`) using `httpx.AsyncClient`.
- Generates JSON Schema definitions from Python type hints and Pydantic models for native tool calling.
- Automatically handles and formats tool-call error responses for model self-correction.
- Configurable base URL (default: `http://localhost:11434/v1`), model name (default: `qwen2.5-coder:14b`), request timeout, and max retries.

### 2.3 EventBus
- Asynchronous pub/sub event system emitting typed events:
  - `TaskStarted(task_id, prompt)`
  - `AgentThought(agent_id, thought)`
  - `ToolCallRequested(agent_id, tool_name, arguments)`
  - `ToolCallCompleted(agent_id, tool_name, result, error)`
  - `SubagentSpawned(parent_id, child_id, role, instructions)`
  - `TaskFinished(task_id, status, summary, error)`

---

## 3. Multi-Agent Hierarchy & Roles

### 3.1 LeadAgent (Orchestrator)
- **Role**: Primary interface to user prompt.
- **Responsibilities**: Analyzes task complexity, creates step breakdown, dispatches subagents, coordinates shared context, synthesizes final outcome.
- **Available Tools**: `invoke_subagent`, `send_message`, `read_file`, `find_files`, `grep_search`, `report_done`.

### 3.2 CoderAgent
- **Role**: Code authoring and editing.
- **Responsibilities**: Reading source files, writing new implementations, applying atomic contiguous line patches, validating syntax.
- **Available Tools**: `read_file`, `write_file`, `patch_file`, `find_files`, `grep_search`, `report_done`.

### 3.3 ExecAgent
- **Role**: Shell command and test runner.
- **Responsibilities**: Running compilers, test suites, linters, dependency managers; monitoring subprocess output and exit codes.
- **Available Tools**: `run_command`, `kill_process`, `get_process_status`, `read_file`, `report_done`.

### 3.4 ResearcherAgent
- **Role**: Codebase exploration and dependency mapping.
- **Responsibilities**: Read-only directory traversal, pattern searching, cross-referencing definitions.
- **Available Tools**: `read_file`, `find_files`, `grep_search`, `report_done`.

---

## 4. Tool Specifications

### 4.1 Filesystem Tools (`oriah.tools.fs`)
1. **`read_file(path: str, offset: int = 1, limit: int = 200) -> str`**
   - Returns line-numbered content (`1: line`).
   - Slices lines between `offset` and `offset + limit - 1`.
   - Rejects binary files and paths escaping workspace root.

2. **`write_file(path: str, content: str, overwrite: bool = False) -> str`**
   - Creates parent directories automatically.
   - Raises error if target exists unless `overwrite=True`.

3. **`patch_file(path: str, target: str, replacement: str) -> str`**
   - Enforces exact contiguous block match.
   - Validates that `target` occurs exactly once in the target file.
   - Applies atomic replacement.

4. **`grep_search(query: str, path: str = ".", regex: bool = False) -> list[dict]`**
   - Scans files matching query using Python `re` or ripgrep if available.
   - Returns structured list: `[{"file": path, "line": int, "content": str}]`.
   - Respects `.gitignore`.

5. **`find_files(pattern: str = "*", path: str = ".") -> list[str]`**
   - Recursive glob match starting at `path`.
   - Skips standard ignored directories (`.git`, `node_modules`, `target`, `__pycache__`, `.venv`).

### 4.2 Shell / Process Tools (`oriah.tools.exec`)
1. **`run_command(cmd: str, cwd: str = ".", timeout: int = 60, background: bool = False) -> dict`**
   - Executes shell commands via `asyncio.create_subprocess_shell`.
   - Enforces execution within workspace directory.
   - Blocks destructive root commands (`rm -rf /`, `mkfs`, etc.).
   - If `background=True`, launches detached task, returns `task_id`.
   - If synchronous, returns `{"exit_code": int, "stdout": str, "stderr": str}`.

2. **`kill_process(task_id: str) -> bool`**
   - Sends SIGTERM, then SIGKILL if unresponsive after 3 seconds.

3. **`get_process_status(task_id: str) -> dict`**
   - Returns `{"task_id": str, "status": "running"|"completed"|"failed", "exit_code": Optional[int]}`.

### 4.3 Agent Tools (`oriah.tools.agent`)
1. **`invoke_subagent(role: str, instructions: str, model: Optional[str] = None) -> str`**
   - Instantiates child agent instance.
   - Returns child agent ID and initializes async execution.

2. **`send_message(recipient_id: str, message: str) -> str`**
   - Enqueues message into recipient's conversational queue.

3. **`report_done(summary: str) -> str`**
   - Sets agent termination flag and returns final summary to parent.

---

## 5. ReAct Loop & Context Compaction

### 5.1 ReAct Loop Flow
Each agent executes the following loop:
1. Compile system prompt (role definition, constraints, available tool schemas).
2. Append conversational history (user instructions, past tool calls, tool responses).
3. Request completion from LLM with `tools` parameter.
4. If completion contains `tool_calls`:
   - Validate each call against `ToolRegistry`.
   - Execute tool asynchronously.
   - Append tool result message to conversation history.
   - Loop back to step 3.
5. If completion contains final response text or calls `report_done`:
   - Terminate loop and return output.
6. Guard: If loop count exceeds `max_steps` (default: 25), terminate with step budget exceeded error.

### 5.2 Context Window Compaction
Local models with 8k–32k context require active compaction:
- **Pinned Segments**: System prompt and initial task prompt are never pruned.
- **Output Truncation**: Tool outputs exceeding 2,000 characters are truncated with an informative notice and instruction to paginate with `offset`/`limit`.
- **History Pruning**: When total prompt token count approaches 75% of context window limit, intermediate completed tool cycles are summarized into compact structured logs (`[Tool: write_file(path="...") -> OK]`).

---

## 6. Directory Structure & Module Layout

```
oriah/
├── pyproject.toml
├── README.md
├── src/
│   └── oriah/
│       ├── __init__.py
│       ├── cli.py               # CLI entrypoint (oriah-agent)
│       ├── config.py            # EngineConfig, settings loader
│       ├── events.py            # EventBus and typed AgentEvents
│       ├── engine.py            # AsyncEngine orchestrator
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py        # Async OpenAI-compatible client
│       │   └── schema.py        # Pydantic to JSON Schema conversion
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── base.py          # BaseAgent ReAct loop
│       │   ├── context.py       # Conversation history & compaction
│       │   ├── dispatcher.py    # SubagentDispatcher
│       │   └── roles.py         # LeadAgent, CoderAgent, ExecAgent, ResearcherAgent
│       └── tools/
│           ├── __init__.py
│           ├── registry.py      # ToolRegistry & decorator
│           ├── fs.py            # Filesystem tools
│           ├── exec.py          # Subprocess execution tools
│           └── agent.py         # Subagent coordination tools
└── tests/
    ├── conftest.py
    ├── test_tools_fs.py
    ├── test_tools_exec.py
    ├── test_llm_client.py
    ├── test_agent_react.py
    └── test_dispatcher.py
```

---

## 7. Testing & Verification Plan

### 7.1 Automated Unit Tests (`pytest`)
1. **Filesystem Tests**:
   - `read_file` with line numbering, offset, limit, and non-existent file handling.
   - `write_file` with directory creation and overwrite protections.
   - `patch_file` verifying exact match, duplicate target error, and clean replacements.
   - `grep_search` and `find_files` verifying workspace boundaries and pattern matching.
2. **Process Execution Tests**:
   - `run_command` verifying synchronous output capture, stderr handling, and timeout termination.
   - Path escaping prevention (rejecting commands trying to run in `/` or unauthorized paths).
3. **LLM Client Tests**:
   - Mocked `/v1/chat/completions` verifying payload formatting, tool call serialization, and JSON schema extraction.
4. **Agent ReAct Loop Tests**:
   - Mock LLM simulating multi-turn tool call sequence ending in `report_done`.
   - Step limit guard enforcement.
5. **Dispatcher Tests**:
   - Lead agent dispatching subagent, passing instructions, and receiving result.

### 7.2 Manual / End-to-End Verification
- Run `oriah-agent run "create a python file calculating fibonacci and run pytest"` against local running Ollama instance or mock server.
- Verify event stream logs all intermediate steps accurately without crashing.

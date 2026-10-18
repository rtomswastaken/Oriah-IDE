# Oriah IDE

A terminal-based development environment and multi-agent workflow engine built with Python, Textual, and Pygments.

## Overview
Oriah IDE combines a terminal user interface (TUI) with an asynchronous ReAct agent engine. It allows developers to browse files, edit code with syntax highlighting, run shell commands, and dispatch coding or debugging tasks to local or remote language models.

The agent engine supports role specialization, workspace-bounded tool execution, subagent delegation, and dynamic custom roles and tools defined within the project workspace.

## Features

- Four-Quadrant Terminal Interface:
  - File Explorer: Filesystem tree with ignore filtering and directory refresh.
  - Code Editor: Multi-tab editor with Pygments syntax highlighting, line numbers, cursor position indicators, dirty status markers, and keyboard save shortcuts.
  - Task Checklist and Reports: Interactive task tracking with completion progress and report summaries.
  - Dual-Mode Bottom Panel: Toggle between the multi-agent workspace (Agent Studio) and an integrated terminal console.
- Multi-Agent Orchestration:
  - Asynchronous ReAct loop powered by an internal event bus.
  - Built-in agent roles with isolated toolsets:
    - `lead`: Orchestrates tasks, decomposes objectives, and delegates subtasks.
    - `coder`: Inspects files, authors code, and applies surgical block patches.
    - `exec`: Runs shell commands, test suites, and linters.
    - `researcher`: Read-only codebase exploration and grep pattern matching.
  - Subagent delegation through `invoke_subagent`.
- Tool Sandbox and Safety Guards:
  - Filesystem tools (`read_file`, `write_file`, `patch_file`, `grep_search`, `find_files`) bounded to the project workspace root.
  - Command execution tool (`run_command`) with process timeouts and filtering for destructive shell commands.
- Extensibility:
  - Define custom tools in `.oriah/custom_tools.py` using the `@custom_tool` decorator.
  - Define custom agent roles in `.oriah/roles/*.py` via `RoleDefinition`.
- Provider Flexibility:
  - Uses OpenAI-compatible HTTP endpoints (`/v1/chat/completions`).
  - Preconfigured defaults for local Ollama instances, with support for OpenAI, Anthropic, Google Gemini, Groq, OpenRouter, and custom HTTP endpoints configured via the Agent Studio modal.
- Headless CLI Mode:
  - Execute agent tasks directly from the command line without launching the TUI via the `oriah-agent` command.

## Requirements

- Python 3.10 or higher
- An OpenAI-compatible API endpoint (such as a local Ollama instance running `qwen2.5-coder:14b` or any compatible model)

## Installation

Clone the repository and install the dependencies:

```bash
git clone https://github.com/rtomswastaken/Oriah-IDE.git
cd Oriah-IDE
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Alternatively, install in editable mode:

```bash
pip install -e .
```

## Usage

### Interactive Terminal IDE

Run the IDE using the launcher script:

```bash
./run.sh
```

Specify a custom workspace directory:

```bash
./run.sh --dir /path/to/project
```

Or run directly through Python:

```bash
python -m oriah.app --dir /path/to/project
```

If the package was installed with `pip install -e .`, you can use the `oriah` command:

```bash
oriah --dir /path/to/project
```

### Headless CLI Agent

To run tasks directly from the command line without the graphical interface:

```bash
python -m oriah.cli run "Inspect tests and fix failing test cases"
```

Or using the installed `oriah-agent` command:

```bash
oriah-agent run "Refactor helper functions in utils.py" --base-url http://localhost:11434/v1 --model qwen2.5-coder:14b
```

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl + S` | Save active file in editor |
| `Ctrl + T` | Toggle bottom panel between Agent Mode and Terminal Console |
| `Ctrl + M` / `Ctrl + N` | Open Agent Studio to add, configure, or switch agents |
| `Ctrl + W` | Close active editor tab |
| `Ctrl + Q` | Quit Oriah IDE |

## Project Structure

```
Oriah-IDE/
├── oriah/
│   ├── app.py                  # Textual application and TUI lifecycle
│   ├── cli.py                  # Headless agent CLI runner (oriah-agent)
│   ├── config.py               # Engine configuration models
│   ├── engine.py               # AsyncEngine orchestrator and ReAct loop
│   ├── events.py               # Typed event bus and agent events
│   ├── state.py                # Workspace and agent configuration state
│   ├── agent/
│   │   ├── base.py             # BaseAgent ReAct execution loop
│   │   ├── context.py          # Message history and context compaction
│   │   ├── dispatcher.py       # SubagentDispatcher for role delegation
│   │   └── roles.py            # Built-in roles and RoleRegistry
│   ├── llm/
│   │   └── client.py           # Async HTTP client for OpenAI-compatible APIs
│   ├── tools/
│   │   ├── agent.py            # Subagent invocation tool
│   │   ├── custom_loader.py    # Dynamic loader for workspace tools and roles
│   │   ├── exec.py             # Shell command execution tools
│   │   ├── fs.py               # Filesystem inspection and manipulation tools
│   │   └── registry.py         # Tool registry and schema generator
│   └── widgets/
│       ├── add_agent_modal.py  # Modal dialog for connecting new models
│       ├── agent_manager_modal.py # Agent Studio management interface
│       ├── agent_panel.py      # Agent cards gallery and prompt bar
│       ├── checklist_panel.py  # Task checklist and report widget
│       ├── directory_panel.py  # Filtered directory tree explorer
│       ├── editor_panel.py     # Syntax-highlighted code editor
│       └── terminal_panel.py   # Integrated command runner and console
├── tests/                      # Unit and integration test suite
├── pyproject.toml              # Build configuration and dependencies
├── requirements.txt            # Python dependencies
└── run.sh                      # Shell bootstrap script
```

## Configuration and Extensibility

### Agent Configuration

Agent profiles are saved to `.oriah/agents.json` in the active workspace. You can edit this file directly or manage models interactively via the Agent Studio modal (`Ctrl + M` or `Ctrl + N`).

### Workspace Custom Tools

To add workspace-specific tools, create `.oriah/custom_tools.py` in your project root and decorate functions with `@custom_tool`:

```python
from oriah.tools.registry import custom_tool

@custom_tool(name="count_lines", description="Count non-empty lines in a file")
async def count_lines(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        count = sum(1 for line in f if line.strip())
    return f"{filepath} has {count} lines."
```

### Workspace Custom Roles

To define a custom agent role, create a Python file under `.oriah/roles/` (e.g., `.oriah/roles/reviewer.py`):

```python
from oriah.agent.roles import RoleDefinition

role = RoleDefinition(
    name="reviewer",
    description="Code review specialist focusing on style and security.",
    system_prompt="Review provided code diffs and report issues.",
    allowed_tools=["read_file", "grep_search"],
    can_spawn_subagents=False,
)
```

Custom tools and roles are loaded dynamically when the engine initializes.

## Testing

Run the test suite with pytest:

```bash
pytest
```

Or run tests using unittest:

```bash
python3 -m unittest discover tests
```

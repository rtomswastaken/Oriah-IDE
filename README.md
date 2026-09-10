# Oriah IDE ⚡

A fast, clean, and polished Cursor-inspired AI Agent Terminal IDE built with Python **Textual 8.2** and **Pygments**.

---

## 📸 4-Quadrant UI Architecture (Wireframe Match)

Oriah IDE implements the exact 4-quadrant layout specified in the design wireframes:

```
┌─────────────────────────┬────────────────────────────────────────────────────────┐
│                         │                                                        │
│   📁 DIRECTORY TREE     │                   📝 CODE EDITOR                       │
│   (File explorer,       │        (Multi-language syntax highlighting,            │
│    click to open tabs)  │         tabs, line numbers, dirty status, Ctrl+S)      │
│                         │                                                        │
├─────────────────────────┼────────────────────────────────────────────────────────┤
│                         │   [🤖 Agent Mode]          [❯_ Terminal / Console]     │
│   📋 AGENT REPORT &     │  ┌──────────────────────────────────────────────────┐  │
│      CHECKLIST          │  │ [Agent 1]  [Agent 2]  [Agent n]  [ ⊕ Add Agent ] │  │
│   (Task checkboxes,     │  │                                                  │  │
│    progress bar, report)│  │ Prompt: [Type instruction for agent...     [Run]]│  │
│                         │  └──────────────────────────────────────────────────┘  │
└─────────────────────────┴────────────────────────────────────────────────────────┘
```

1. **Top-Left: Directory Panel**
   - Live filesystem tree rooted at the workspace directory.
   - Click any file to open it in the syntax-highlighted editor tab bar.
   - Tree refresh button `[↻]`.

2. **Bottom-Left: Agent Report & Implementation Checklist**
   - Interactive task checklist with checkboxes `[x]` / `[ ]`.
   - Real-time progress bar updating completion percentage.
   - Dual-tab view: **Checklist** tasks vs. **Report** summary & recommendations.

3. **Top-Right: Code Editor**
   - Pygments syntax highlighting across all languages (Python, TypeScript, JavaScript, Rust, Go, HTML, CSS, JSON, Markdown, C/C++, etc.).
   - Multi-file tab bar with dirty indicators `●` and close buttons `[×]`.
   - Cursor position counter (`Ln X, Col Y`), file save status, and `Ctrl+S` binding.

4. **Bottom-Right: Dual-Mode Panel**
   - **Tab 1: Agent Mode** (Wireframes 1 & 3):
     - Horizontal cards gallery displaying configured AI agents (Avatar, Name, Model, Role, Status).
     - Circular `⊕ Add Agent` card button: opens the **Add Agent Modal** allowing connection to local Gemma/Ollama, Qwen-Coder, LLaMA, or online models (Claude, Gemini, OpenAI, custom endpoints).
     - Agent prompt bar with `Run Agent` button.
     - Real-time streaming activity/event log.
   - **Tab 2: Terminal / Console / Output Screen** (Wireframe 2):
     - Embedded command runner with ANSI color support.
     - Run any shell command directly (`git status`, `pytest`, `npm test`, etc.).
     - Output streaming with exit codes and clear button.

---

## 🚀 Quickstart

Run with the included self-bootstrapping launcher:

```bash
./run.sh
```

Or run against any custom workspace folder:

```bash
./run.sh --dir /path/to/project
```

Or run via Python virtual environment:

```bash
source .venv/bin/activate
python -m oriah.app
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + S` | **Save** active editor file to disk |
| `Ctrl + T` | **Toggle** bottom panel between **Agent Mode** and **Terminal Console** |
| `Ctrl + N` | **Add Agent** (opens modal dialog to configure new local/online agent) |
| `Ctrl + W` | **Close** active editor tab |
| `Ctrl + Q` | **Quit** Oriah IDE |

---

## 🤝 For Your Teammate: Backend Agent Hook

The UI is decoupled from the agent backend. To connect real agent streaming or Ollama/Gemini/Claude execution:

Open [`oriah/app.py`](oriah/app.py#L182) and implement your model call inside:

```python
def on_agent_mode_panel_prompt_submitted(self, event: AgentModePanel.PromptSubmitted) -> None:
    # event.agent contains: id, name, model, provider, role, instructions
    # event.prompt contains: user's text instruction
    # Stream responses back to:
    agent_panel = self.query_one(AgentModePanel)
    agent_panel.append_log(f"🤖 [{event.agent.name}]: <your streamed response>")
```

---

## 🧪 Testing

Run the automated unit and headless UI test suite:

```bash
.venv/bin/python3 -m unittest tests/test_oriah.py
```

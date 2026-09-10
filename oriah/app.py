"""Main Application entry point for Oriah IDE."""

import argparse
from pathlib import Path
from typing import Optional
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Label

from oriah.state import AgentConfig, AppState
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
from oriah.widgets.add_agent_modal import AddAgentModal
from oriah.widgets.agent_panel import AgentModePanel
from oriah.widgets.checklist_panel import ChecklistPanel
from oriah.widgets.directory_panel import DirectoryPanel
from oriah.widgets.editor_panel import EditorPanel
from oriah.widgets.terminal_panel import TerminalPanel


class OriahIDE(App):
    """Oriah IDE - Fast, Cursor-inspired Terminal AI IDE."""

    TITLE = "Oriah IDE"
    SUB_TITLE = "AI Agent Terminal Environment"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+s", "save_file", "Save File", priority=True),
        Binding("ctrl+t", "toggle_bottom_mode", "Toggle Terminal / Agent Mode", priority=True),
        Binding("ctrl+n", "add_agent", "Add Agent", priority=True),
        Binding("ctrl+w", "close_tab", "Close Tab", priority=True),
        Binding("ctrl+q", "quit", "Quit Oriah", priority=True),
    ]

    def __init__(self, root_dir: Optional[str] = None) -> None:
        super().__init__()
        self.state = AppState(root_dir=root_dir)
        self.bottom_mode: str = "agent"  # "agent" or "terminal"

    def compose(self) -> ComposeResult:
        # Header banner
        with Horizontal(id="app-header"):
            yield Label("⚡ ORIAH IDE", classes="app-title")
            yield Label(f"  •  Workspace: /{self.state.root_dir.name}", id="header-workspace-label")
            yield Label("  •  v0.1.0 (Cursor Engine)", classes="app-version")

        # 4-Quadrant Workspace Grid
        with Horizontal(id="workspace-grid"):
            # Left Column (25%): Directory + Checklist
            with Vertical(id="left-column"):
                yield DirectoryPanel(self.state.root_dir, id="directory-container")
                yield ChecklistPanel(self.state, id="checklist-container")

            # Right Column (75%): Code Editor + Agent Mode / Terminal
            with Vertical(id="right-column"):
                yield EditorPanel(self.state, id="editor-container")

                with Vertical(id="bottom-right-container"):
                    # Tab switcher for bottom-right mode (Wireframe 1 vs 2)
                    with Horizontal(id="bottom-mode-tabs"):
                        yield Button(
                            "🤖 Agent Mode",
                            id="btn-mode-agent",
                            classes="mode-tab-btn active-mode",
                        )
                        yield Button(
                            "❯_ Terminal / Console",
                            id="btn-mode-terminal",
                            classes="mode-tab-btn",
                        )

                    yield AgentModePanel(self.state, id="agent-mode-panel")
                    yield TerminalPanel(self.state, id="terminal-panel")

        # Bottom status bar
        with Horizontal(id="app-status-bar"):
            yield Label("Ready", id="status-message")
            yield Label(
                f"  |  Active Agent: {self.state.get_active_agent().name}",
                id="status-agent-label",
            )
            yield Label(
                "  |  ^S Save  ^T Toggle View  ^N New Agent  ^W Close Tab  ^Q Quit",
                id="status-help-label",
            )

    def on_mount(self) -> None:
        # Hide terminal initially to show Agent Mode (Wireframe 1 & 3 default)
        terminal = self.query_one("#terminal-panel", TerminalPanel)
        terminal.display = False

    def on_directory_panel_file_open_requested(
        self, event: DirectoryPanel.FileOpenRequested
    ) -> None:
        """Handle file clicked in directory tree -> open tab in Editor."""
        tab = self.state.open_file(event.path)
        editor = self.query_one(EditorPanel)
        editor.refresh_tabs()
        editor.display_active_tab()
        self.set_status(f"Opened: {tab.filename}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-mode-agent":
            self.switch_bottom_mode("agent")
        elif event.button.id == "btn-mode-terminal":
            self.switch_bottom_mode("terminal")

    def switch_bottom_mode(self, mode: str) -> None:
        """Toggle bottom right panel between Agent Mode and Terminal."""
        self.bottom_mode = mode
        agent_panel = self.query_one("#agent-mode-panel", AgentModePanel)
        terminal_panel = self.query_one("#terminal-panel", TerminalPanel)
        btn_agent = self.query_one("#btn-mode-agent", Button)
        btn_terminal = self.query_one("#btn-mode-terminal", Button)

        if mode == "agent":
            agent_panel.display = True
            terminal_panel.display = False
            btn_agent.add_class("active-mode")
            btn_terminal.remove_class("active-mode")
            self.set_status("Active Panel: Agent Mode")
        else:
            agent_panel.display = False
            terminal_panel.display = True
            btn_terminal.add_class("active-mode")
            btn_agent.remove_class("active-mode")
            self.set_status("Active Panel: Terminal / Console")

    def action_toggle_bottom_mode(self) -> None:
        new_mode = "terminal" if self.bottom_mode == "agent" else "agent"
        self.switch_bottom_mode(new_mode)

    def action_save_file(self) -> None:
        editor = self.query_one(EditorPanel)
        saved_path = editor.save_current_file()
        if saved_path:
            self.set_status(f"✔ Saved: {saved_path}")
            # Log in agent activity
            agent_panel = self.query_one(AgentModePanel)
            agent_panel.append_log(f"💾 File saved: {saved_path}")
        else:
            self.set_status("No file to save")

    def action_close_tab(self) -> None:
        closed = self.state.close_tab(self.state.active_tab_index)
        if closed:
            editor = self.query_one(EditorPanel)
            editor.refresh_tabs()
            editor.display_active_tab()
            self.set_status(f"Closed tab: {closed.filename}")

    def action_add_agent(self) -> None:
        """Open the Add Agent Modal dialog."""

        def _handle_agent_result(result: Optional[dict]) -> None:
            if not result:
                return
            new_agent = self.state.add_agent(
                name=result["name"],
                model=result["model"],
                provider=result["provider"],
                role=result["role"],
                instructions=result.get("instructions", ""),
            )
            # Refresh agent cards
            agent_panel = self.query_one(AgentModePanel)
            agent_panel.refresh_cards()
            # Update status
            self.set_status(f"✨ Attached agent: {new_agent.name} ({new_agent.model})")
            agent_label = self.query_one("#status-agent-label", Label)
            agent_label.update(f"  |  Active Agent: {new_agent.name}")

        self.push_screen(AddAgentModal(), _handle_agent_result)

    def on_agent_mode_panel_add_agent_requested(
        self, event: AgentModePanel.AddAgentRequested
    ) -> None:
        self.action_add_agent()

    def on_agent_mode_panel_prompt_submitted(
        self, event: AgentModePanel.PromptSubmitted
    ) -> None:
        """Execute agent task via backend AsyncEngine."""
        self.set_status(f"⚡ Dispatched prompt to {event.agent.name}...")
        self.run_worker(self._execute_backend_agent(event.agent, event.prompt), exclusive=False)

    async def _execute_backend_agent(self, agent: AgentConfig, prompt: str) -> None:
        agent_panel = self.query_one(AgentModePanel)
        config = EngineConfig(
            model=agent.model if agent.model else "qwen2.5-coder:14b",
            workspace_root=str(self.state.root_dir),
        )
        engine = AsyncEngine(config=config)
        try:
            async for ev in engine.run(prompt):
                if isinstance(ev, TaskStarted):
                    self.set_status(f"🚀 Task started ({ev.task_id[:8]})...")
                elif isinstance(ev, AgentThought):
                    agent_panel.append_log(f"💭 [{ev.agent_id}] {ev.thought}")
                elif isinstance(ev, ToolCallRequested):
                    agent_panel.append_log(f"  🔧 Tool: {ev.tool_name}({list(ev.arguments.keys())})")
                elif isinstance(ev, ToolCallCompleted):
                    if ev.error:
                        agent_panel.append_log(f"  ❌ Error: {ev.error}")
                    else:
                        snippet = (ev.result or "")[:80].replace("\n", " ")
                        agent_panel.append_log(f"  ✔ Result: {snippet}...")
                elif isinstance(ev, SubagentSpawned):
                    agent_panel.append_log(f"  🤖 Spawned subagent [{ev.child_id}] ({ev.role})")
                elif isinstance(ev, TaskFinished):
                    if ev.status == "success":
                        agent_panel.append_log(f"✅ Finished: {ev.summary}")
                        self.set_status("Ready")
                    else:
                        agent_panel.append_log(f"❌ Failed: {ev.error}")
                        self.set_status("Error")
        except Exception as e:
            agent_panel.append_log(f"⚠️ Agent error: {str(e)}")
            self.set_status("Agent error")
        finally:
            await engine.aclose()

    def set_status(self, text: str) -> None:
        try:
            status = self.query_one("#status-message", Label)
            status.update(text)
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Oriah IDE - Terminal AI IDE")
    parser.add_argument("--dir", default=".", help="Workspace root directory")
    args = parser.parse_args()

    app = OriahIDE(root_dir=args.dir)
    app.run()


if __name__ == "__main__":
    main()

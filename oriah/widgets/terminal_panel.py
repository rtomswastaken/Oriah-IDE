"""Interactive Terminal, Console, and Process Output Runner for Oriah IDE."""

import asyncio
from pathlib import Path
from typing import Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, RichLog

from oriah.state import AppState


class TerminalPanel(Vertical):
    """Terminal / Console / Output screen corresponding to Wireframe 2."""

    DEFAULT_CSS = """
    TerminalPanel {
        height: 100%;
        layout: vertical;
        background: #090b10;
    }
    """

    def __init__(self, state: AppState, id: str = "terminal-panel") -> None:
        super().__init__(id=id)
        self.state = state

    def compose(self) -> ComposeResult:
        # RichLog provides high-performance, colorized terminal output
        yield RichLog(
            highlight=True,
            markup=True,
            auto_scroll=True,
            id="terminal-log",
        )

        with Horizontal(id="terminal-input-bar"):
            yield Label("❯", classes="terminal-prompt-label")
            yield Input(
                placeholder="Run shell command (e.g. 'ls', 'git status', 'python3 -m unittest', 'pytest')...",
                id="terminal-command-input",
            )
            yield Button("Clear", id="terminal-clear-btn")

    def on_mount(self) -> None:
        log = self.query_one("#terminal-log", RichLog)
        log.write("[bold cyan]Oriah IDE Integrated Terminal & Output Console[/bold cyan]")
        log.write(f"[dim]Working directory: {self.state.root_dir}[/dim]")
        log.write("[dim]Type any shell command and press [bold]Enter[/bold]. Press [bold]Ctrl+T[/bold] to toggle with Agent Mode.[/dim]\n")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "terminal-clear-btn":
            log = self.query_one("#terminal-log", RichLog)
            log.clear()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "terminal-command-input":
            cmd = event.input.value.strip()
            if not cmd:
                return
            event.input.value = ""
            self.run_command(cmd)

    def run_command(self, cmd_line: str) -> None:
        """Execute a command asynchronously and stream output to the log."""
        log = self.query_one("#terminal-log", RichLog)
        log.write(f"[bold green]❯ {cmd_line}[/bold green]")
        self.state.terminal_history.append(cmd_line)

        async def _exec_task():
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd_line,
                    cwd=str(self.state.root_dir),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout_bytes, stderr_bytes = await proc.communicate()
                stdout_text = stdout_bytes.decode("utf-8", errors="replace").rstrip()
                stderr_text = stderr_bytes.decode("utf-8", errors="replace").rstrip()

                if stdout_text:
                    log.write(stdout_text)
                if stderr_text:
                    log.write(f"[bold red]{stderr_text}[/bold red]")

                if proc.returncode == 0:
                    log.write("[bold green]✔ Process exited with code 0[/bold green]\n")
                else:
                    log.write(f"[bold yellow]⚠ Process exited with code {proc.returncode}[/bold yellow]\n")

            except Exception as e:
                log.write(f"[bold red]Execution error: {e}[/bold red]\n")

        asyncio.create_task(_exec_task())

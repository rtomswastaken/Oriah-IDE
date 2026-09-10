"""Modal dialog for adding new local or cloud AI agents to Oriah IDE."""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from oriah.state import AgentConfig, AppState


class AddAgentModal(ModalScreen[Optional[dict]]):
    """Dialog allowing user to configure and attach any local or online model."""

    DEFAULT_CSS = """
    AddAgentModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }
    """

    PROVIDERS = [
        ("Ollama / Local (Gemma, Qwen, LLaMA)", "Ollama (Local)"),
        ("Google Gemini (Gemini 1.5 Pro / Flash)", "Google Gemini"),
        ("Anthropic (Claude 3.5 Sonnet)", "Anthropic"),
        ("OpenAI (GPT-4o)", "OpenAI"),
        ("Custom HTTP / vLLM Endpoint", "Custom Endpoint"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-dialog-box"):
            yield Label("⚡ CONNECT NEW AGENT", classes="modal-title")

            yield Label("Agent Name:", classes="modal-field-label")
            yield Input(placeholder="e.g. Gemma Python Specialist", id="modal-name", classes="modal-input")

            yield Label("Provider / Runtime:", classes="modal-field-label")
            yield Select(self.PROVIDERS, value="Ollama (Local)", id="modal-provider", allow_blank=False)

            yield Label("Model Identifier:", classes="modal-field-label")
            yield Input(
                placeholder="e.g. gemma2:9b, qwen3-coder:30b, claude-3-5-sonnet",
                id="modal-model",
                classes="modal-input",
                value="gemma2:9b",
            )

            yield Label("Agent Specialty / Role:", classes="modal-field-label")
            yield Input(
                placeholder="e.g. Frontend Specialist, Test Engineer, Lead Architect",
                id="modal-role",
                classes="modal-input",
                value="Code Synthesizer",
            )

            yield Label("Custom System Prompt / Instructions:", classes="modal-field-label")
            yield Input(
                placeholder="Specific behavioral constraints or project knowledge...",
                id="modal-instructions",
                classes="modal-input",
            )

            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="modal-cancel-btn", classes="modal-btn")
                yield Button("Create Agent ↵", id="modal-confirm-btn", classes="modal-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "modal-cancel-btn":
            self.dismiss(None)
        elif event.button.id == "modal-confirm-btn":
            self._submit_agent()

    def _submit_agent(self) -> None:
        name = self.query_one("#modal-name", Input).value.strip() or "Custom Agent"
        provider = str(self.query_one("#modal-provider", Select).value)
        model = self.query_one("#modal-model", Input).value.strip() or "local-model"
        role = self.query_one("#modal-role", Input).value.strip() or "General Coder"
        instructions = self.query_one("#modal-instructions", Input).value.strip()

        agent_data = {
            "name": name,
            "provider": provider,
            "model": model,
            "role": role,
            "instructions": instructions,
        }
        self.dismiss(agent_data)

"""Agent Management Modal Dialog for Oriah IDE.

Provides a full-featured management menu to add, configure, edit, switch,
and delete agents with custom API keys, endpoints, and models.
"""

from typing import List, Optional, Tuple
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static

from oriah.state import AgentConfig, AppState


PROVIDER_OPTIONS: List[Tuple[str, str]] = [
    ("Ollama (Local)", "Ollama (Local)"),
    ("OpenAI (GPT-4o, o1, etc.)", "OpenAI"),
    ("Anthropic (Claude 3.5 Sonnet / Haiku)", "Anthropic"),
    ("Google Gemini (1.5 Pro / Flash)", "Google Gemini"),
    ("Groq (Llama 3.3, Mixtral)", "Groq"),
    ("OpenRouter (Multi-Model Gateway)", "OpenRouter"),
    ("Custom HTTP / vLLM / LM Studio", "Custom Endpoint"),
]

PROVIDER_DEFAULT_URLS = {
    "Ollama (Local)": "http://localhost:11434/v1",
    "OpenAI": "https://api.openai.com/v1",
    "Anthropic": "https://api.anthropic.com/v1",
    "Google Gemini": "https://generativelanguage.googleapis.com/v1beta",
    "Groq": "https://api.groq.com/openai/v1",
    "OpenRouter": "https://openrouter.ai/api/v1",
    "Custom Endpoint": "http://localhost:8000/v1",
}


class AgentListItemButton(Button):
    """Button representing an agent in the manager list."""

    def __init__(self, agent: AgentConfig, label: str, classes: str) -> None:
        super().__init__(label, classes=classes)
        self.agent_id = agent.id


class AgentManagerModal(ModalScreen[bool]):
    """Comprehensive Agent Management Menu to configure and manage agent APIs."""

    DEFAULT_CSS = """
    AgentManagerModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }
    """

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.selected_agent_id: Optional[str] = (
            self.state.active_agent_id
            if self.state.active_agent_id
            else (self.state.agents[0].id if self.state.agents else None)
        )
        self.is_creating_new: bool = False

    def compose(self) -> ComposeResult:
        with Vertical(id="manager-dialog-box"):
            with Horizontal(id="manager-dialog-header"):
                yield Label("⚙️ AGENT API & MULTI-AGENT MANAGEMENT MENU", id="manager-dialog-title")
                yield Button("✖ Close", id="manager-btn-close-top", classes="manager-btn-sm")

            with Horizontal(id="manager-dialog-body"):
                # Left Pane: Configured Agents List
                with Vertical(id="manager-list-pane"):
                    with Horizontal(id="manager-list-header-bar"):
                        yield Label("Configured Agents", classes="manager-pane-title")
                        yield Button("➕ New Agent", id="manager-btn-new", classes="manager-btn-accent-sm")

                    with VerticalScroll(id="manager-agents-scroll"):
                        for agent in self.state.agents:
                            yield self._build_agent_item_widget(agent)

                # Right Pane: Configuration Form
                with VerticalScroll(id="manager-form-pane"):
                    yield Label("Agent Configuration", id="manager-form-title", classes="manager-pane-title")

                    yield Label("Agent Name:", classes="manager-field-label")
                    yield Input(placeholder="e.g. Claude Senior Architect", id="agent-form-name")

                    yield Label("Provider / Runtime:", classes="manager-field-label")
                    yield Select(
                        PROVIDER_OPTIONS,
                        value="Ollama (Local)",
                        id="agent-form-provider",
                        allow_blank=False,
                    )

                    yield Label("Model Identifier:", classes="manager-field-label")
                    yield Input(placeholder="e.g. claude-3-5-sonnet, gpt-4o, qwen2.5-coder:14b", id="agent-form-model")

                    yield Label("API Key (saved locally to .oriah/agents.json):", classes="manager-field-label")
                    yield Input(placeholder="sk-... or local/none", id="agent-form-api-key", password=True)

                    yield Label("Base URL / API Endpoint:", classes="manager-field-label")
                    yield Input(placeholder="e.g. http://localhost:11434/v1", id="agent-form-base-url")

                    with Horizontal(classes="manager-row-2col"):
                        with Vertical():
                            yield Label("Role / Specialty:", classes="manager-field-label")
                            yield Input(placeholder="e.g. Full-Stack Coder", id="agent-form-role")
                        with Vertical():
                            yield Label("Avatar Emoji:", classes="manager-field-label")
                            yield Input(placeholder="🤖", id="agent-form-avatar", value="🤖")

                    with Horizontal(classes="manager-row-2col"):
                        with Vertical():
                            yield Label("Temperature (0.0 - 1.0):", classes="manager-field-label")
                            yield Input(placeholder="0.7", id="agent-form-temp", value="0.7")
                        with Vertical():
                            yield Label("Max Tokens:", classes="manager-field-label")
                            yield Input(placeholder="4096", id="agent-form-max-tokens", value="4096")

                    yield Label("Custom System Prompt / Instructions:", classes="manager-field-label")
                    yield Input(
                        placeholder="Constraints, coding style, or project context...",
                        id="agent-form-instructions",
                    )

                    yield Label("", id="manager-status-feedback")

                    with Horizontal(id="manager-form-actions"):
                        yield Button("💾 Save Agent", id="manager-btn-save", classes="manager-btn-primary")
                        yield Button("⭐ Set as Active", id="manager-btn-set-active", classes="manager-btn-secondary")
                        yield Button("🗑️ Delete Agent", id="manager-btn-delete", classes="manager-btn-danger")

    def on_mount(self) -> None:
        self._populate_form_for_selected()

    def _build_agent_item_widget(self, agent: AgentConfig) -> Button:
        is_active = agent.id == self.state.active_agent_id
        is_selected = agent.id == self.selected_agent_id
        active_badge = " [ACTIVE]" if is_active else ""
        label_text = f"{agent.avatar} {agent.name}\n   {agent.provider} | {agent.model}{active_badge}"
        classes = "manager-agent-item"
        if is_selected:
            classes += " manager-agent-item-selected"
        if is_active:
            classes += " manager-agent-item-active"
        btn = AgentListItemButton(agent, label_text, classes=classes)
        return btn

    async def _refresh_agent_list(self) -> None:
        scroll = self.query_one("#manager-agents-scroll", VerticalScroll)
        await scroll.remove_children()
        for agent in self.state.agents:
            await scroll.mount(self._build_agent_item_widget(agent))

    def _populate_form_for_selected(self) -> None:
        feedback = self.query_one("#manager-status-feedback", Label)
        feedback.update("")
        if self.is_creating_new or not self.selected_agent_id:
            self.query_one("#manager-form-title", Label).update("➕ Create New Agent API Config")
            self.query_one("#agent-form-name", Input).value = ""
            self.query_one("#agent-form-provider", Select).value = "Ollama (Local)"
            self.query_one("#agent-form-model", Input).value = "qwen2.5-coder:14b"
            self.query_one("#agent-form-api-key", Input).value = ""
            self.query_one("#agent-form-base-url", Input).value = PROVIDER_DEFAULT_URLS["Ollama (Local)"]
            self.query_one("#agent-form-role", Input).value = "General Coder"
            self.query_one("#agent-form-avatar", Input).value = "🤖"
            self.query_one("#agent-form-temp", Input).value = "0.7"
            self.query_one("#agent-form-max-tokens", Input).value = "4096"
            self.query_one("#agent-form-instructions", Input).value = ""
            self.query_one("#manager-btn-set-active", Button).disabled = True
            self.query_one("#manager-btn-delete", Button).disabled = True
            return

        agent = next((a for a in self.state.agents if a.id == self.selected_agent_id), None)
        if not agent:
            return

        is_active = agent.id == self.state.active_agent_id
        title = f"Edit Agent: {agent.name} {'(⭐ ACTIVE)' if is_active else ''}"
        self.query_one("#manager-form-title", Label).update(title)
        self.query_one("#agent-form-name", Input).value = agent.name
        try:
            self.query_one("#agent-form-provider", Select).value = agent.provider
        except Exception:
            self.query_one("#agent-form-provider", Select).value = "Custom Endpoint"
        self.query_one("#agent-form-model", Input).value = agent.model
        self.query_one("#agent-form-api-key", Input).value = agent.api_key
        self.query_one("#agent-form-base-url", Input).value = (
            agent.base_url or PROVIDER_DEFAULT_URLS.get(agent.provider, "")
        )
        self.query_one("#agent-form-role", Input).value = agent.role
        self.query_one("#agent-form-avatar", Input).value = agent.avatar
        self.query_one("#agent-form-temp", Input).value = str(agent.temperature)
        self.query_one("#agent-form-max-tokens", Input).value = str(agent.max_tokens)
        self.query_one("#agent-form-instructions", Input).value = agent.instructions
        self.query_one("#manager-btn-set-active", Button).disabled = is_active
        self.query_one("#manager-btn-delete", Button).disabled = len(self.state.agents) <= 1

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "agent-form-provider":
            prov = str(event.value)
            base_url_input = self.query_one("#agent-form-base-url", Input)
            if prov in PROVIDER_DEFAULT_URLS and (
                self.is_creating_new or not base_url_input.value.strip()
            ):
                base_url_input.value = PROVIDER_DEFAULT_URLS[prov]

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""

        if button_id in ("manager-btn-close-top", "manager-btn-close"):
            self.dismiss(True)
            return

        if button_id == "manager-btn-new":
            self.is_creating_new = True
            self.selected_agent_id = None
            await self._refresh_agent_list()
            self._populate_form_for_selected()
            return

        if isinstance(event.button, AgentListItemButton):
            self.selected_agent_id = event.button.agent_id
            self.is_creating_new = False
            await self._refresh_agent_list()
            self._populate_form_for_selected()
            return

        if button_id == "manager-btn-set-active":
            if self.selected_agent_id:
                self.state.active_agent_id = self.selected_agent_id
                self.state.save_agents_to_disk()
                await self._refresh_agent_list()
                self._populate_form_for_selected()
                feedback = self.query_one("#manager-status-feedback", Label)
                feedback.update("✅ Agent set as active!")
            return

        if button_id == "manager-btn-delete":
            if self.selected_agent_id and len(self.state.agents) > 1:
                self.state.delete_agent(self.selected_agent_id)
                self.selected_agent_id = (
                    self.state.active_agent_id
                    if self.state.active_agent_id
                    else (self.state.agents[0].id if self.state.agents else None)
                )
                self.is_creating_new = False
                await self._refresh_agent_list()
                self._populate_form_for_selected()
                feedback = self.query_one("#manager-status-feedback", Label)
                feedback.update("🗑️ Agent deleted.")
            return

        if button_id == "manager-btn-save":
            await self._handle_save()

    async def _handle_save(self) -> None:

        name = self.query_one("#agent-form-name", Input).value.strip() or "Custom Agent"
        provider = str(self.query_one("#agent-form-provider", Select).value)
        model = self.query_one("#agent-form-model", Input).value.strip() or "local-model"
        api_key = self.query_one("#agent-form-api-key", Input).value.strip()
        base_url = self.query_one("#agent-form-base-url", Input).value.strip()
        role = self.query_one("#agent-form-role", Input).value.strip() or "General Coder"
        avatar = self.query_one("#agent-form-avatar", Input).value.strip() or "🤖"
        instructions = self.query_one("#agent-form-instructions", Input).value.strip()

        try:
            temp = float(self.query_one("#agent-form-temp", Input).value.strip() or "0.7")
        except ValueError:
            temp = 0.7

        try:
            max_tokens = int(self.query_one("#agent-form-max-tokens", Input).value.strip() or "4096")
        except ValueError:
            max_tokens = 4096

        feedback = self.query_one("#manager-status-feedback", Label)

        if self.is_creating_new:
            new_agent = self.state.add_agent(
                name=name,
                model=model,
                provider=provider,
                role=role,
                instructions=instructions,
                avatar=avatar,
                api_key=api_key,
                base_url=base_url,
                temperature=temp,
                max_tokens=max_tokens,
            )
            self.selected_agent_id = new_agent.id
            self.is_creating_new = False
            feedback.update(f"✨ Created agent '{name}' and saved to disk!")
        else:
            if not self.selected_agent_id:
                return
            self.state.update_agent(
                agent_id=self.selected_agent_id,
                name=name,
                model=model,
                provider=provider,
                role=role,
                instructions=instructions,
                avatar=avatar,
                api_key=api_key,
                base_url=base_url,
                temperature=temp,
                max_tokens=max_tokens,
            )
            feedback.update(f"💾 Updated agent '{name}' and saved to disk!")

        await self._refresh_agent_list()
        self._populate_form_for_selected()

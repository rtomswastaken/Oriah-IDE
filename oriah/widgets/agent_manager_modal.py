"""Agent Studio & Multi-Agent API Manager Modal for Oriah IDE.

Provides a full-featured management menu to configure, edit, switch,
and delete agents with custom API keys, endpoints, and local model dropdown.
Uses clean colorable Unicode glyphs and a modern master-detail studio layout.
"""

import subprocess
from typing import Dict, List, Optional, Tuple
import httpx
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select

from oriah.state import AgentConfig, AppState


PROVIDER_OPTIONS: List[Tuple[str, str]] = [
    ("[Local] Ollama", "Ollama (Local)"),
    ("[Cloud] OpenAI", "OpenAI"),
    ("[Cloud] Anthropic", "Anthropic"),
    ("[Cloud] Google Gemini", "Google Gemini"),
    ("[Cloud] Groq", "Groq"),
    ("[Cloud] OpenRouter", "OpenRouter"),
    ("[Custom] HTTP Endpoint", "Custom Endpoint"),
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

PROVIDER_MODEL_SUGGESTIONS: Dict[str, List[Tuple[str, str]]] = {
    "OpenAI": [
        ("gpt-4o (Flagship)", "gpt-4o"),
        ("gpt-4o-mini (Fast)", "gpt-4o-mini"),
        ("o1-preview (Reasoning)", "o1-preview"),
        ("o1-mini (Fast Reasoning)", "o1-mini"),
        ("Custom Model...", "__custom__"),
    ],
    "Anthropic": [
        ("claude-3-5-sonnet (Sonnet 3.5)", "claude-3-5-sonnet"),
        ("claude-3-5-haiku (Fast)", "claude-3-5-haiku"),
        ("claude-3-opus (Deep Analysis)", "claude-3-opus"),
        ("Custom Model...", "__custom__"),
    ],
    "Google Gemini": [
        ("gemini-1.5-pro (High Context)", "gemini-1.5-pro"),
        ("gemini-1.5-flash (Low Latency)", "gemini-1.5-flash"),
        ("gemini-2.0-flash (Next Gen)", "gemini-2.0-flash"),
        ("Custom Model...", "__custom__"),
    ],
    "Groq": [
        ("llama-3.3-70b-versatile (Fast)", "llama-3.3-70b-versatile"),
        ("mixtral-8x7b-32768 (MoE)", "mixtral-8x7b-32768"),
        ("Custom Model...", "__custom__"),
    ],
    "OpenRouter": [
        ("anthropic/claude-3.5-sonnet", "anthropic/claude-3.5-sonnet"),
        ("openai/gpt-4o", "openai/gpt-4o"),
        ("deepseek/deepseek-chat", "deepseek/deepseek-chat"),
        ("Custom Model...", "__custom__"),
    ],
    "Custom Endpoint": [
        ("Custom Model...", "__custom__"),
    ],
}


def fetch_local_ollama_models(base_url: str = "http://localhost:11434") -> List[Tuple[str, str]]:
    """Query installed local models from Ollama or fallback to curated presets."""
    models: List[Tuple[str, str]] = []

    # 1. Query Ollama tags HTTP API
    try:
        url = base_url.rstrip("/")
        if url.endswith("/v1"):
            url = url[:-3]
        tags_url = f"{url}/api/tags"
        resp = httpx.get(tags_url, timeout=0.8)
        if resp.status_code == 200:
            data = resp.json()
            for m in data.get("models", []):
                name = m.get("name") or m.get("model")
                if name:
                    size_str = ""
                    if m.get("size"):
                        size_str = f" [{m.get('size') / (1024**3):.1f} GB]"
                    models.append((f"{name}{size_str}", name))
    except Exception:
        pass

    # 2. Fallback to CLI ollama list if HTTP failed
    if not models:
        try:
            out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=1.0)
            if out.returncode == 0:
                lines = out.stdout.strip().splitlines()[1:]
                for line in lines:
                    parts = line.split()
                    if parts:
                        name = parts[0]
                        models.append((f"{name} [local]", name))
        except Exception:
            pass

    # 3. Fallback curated local presets
    if not models:
        fallback_presets = [
            ("qwen3-coder:30b [preset]", "qwen3-coder:30b"),
            ("qwen3:14b [preset]", "qwen3:14b"),
            ("qwen2.5-coder:14b [preset]", "qwen2.5-coder:14b"),
            ("qwen2.5-coder:7b [preset]", "qwen2.5-coder:7b"),
            ("gemma2:9b [preset]", "gemma2:9b"),
            ("llama3.2:latest [preset]", "llama3.2:latest"),
            ("deepseek-r1:14b [preset]", "deepseek-r1:14b"),
        ]
        models.extend(fallback_presets)

    models.append(("Custom Model...", "__custom__"))
    return models


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

    BINDINGS = [
        Binding("escape", "app_back", "Back / Close", priority=True),
        Binding("ctrl+s", "save_agent", "Save Agent", priority=True),
    ]

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.selected_agent_id: Optional[str] = (
            self.state.active_agent_id
            if self.state.active_agent_id
            else (self.state.agents[0].id if self.state.agents else None)
        )
        self.is_creating_new: bool = False
        self.local_models_cache: List[Tuple[str, str]] = fetch_local_ollama_models()

    def action_app_back(self) -> None:
        """Handle escape key to go back / dismiss."""
        self._handle_back()

    def action_save_agent(self) -> None:
        """Handle Ctrl+S to save agent configuration."""
        self.run_worker(self._handle_save())

    def compose(self) -> ComposeResult:
        with Vertical(id="manager-dialog-box"):
            # Header
            with Horizontal(id="manager-dialog-header"):
                yield Button("← Back", id="manager-btn-back-top", classes="manager-btn-nav")
                with Horizontal(id="manager-title-group"):
                    yield Label("◈ AGENT STUDIO", id="manager-dialog-title")
                    yield Label("· Multi-Agent Vault & Runtime Config", id="manager-dialog-subtitle")
                yield Button("✕ Close", id="manager-btn-close-top", classes="manager-btn-nav")

            # Body: Master-Detail
            with Horizontal(id="manager-dialog-body"):
                # Left Pane: Roster
                with Vertical(id="manager-list-pane"):
                    with Horizontal(id="manager-list-header-bar"):
                        yield Label("Agent Roster", classes="manager-pane-title")
                        yield Button("+ New Agent", id="manager-btn-new", classes="manager-btn-accent")

                    with VerticalScroll(id="manager-agents-scroll"):
                        for agent in self.state.agents:
                            yield self._build_agent_item_widget(agent)

                    with Horizontal(id="manager-list-footer"):
                        yield Label(f"Total: {len(self.state.agents)} configured", id="manager-list-count")

                # Right Pane: Form & Inspector
                with VerticalScroll(id="manager-form-pane"):
                    # Inspector banner preview
                    with Horizontal(id="manager-inspector-header"):
                        yield Label("◈", id="inspector-preview-avatar")
                        with Vertical(id="inspector-preview-meta"):
                            yield Label("Agent Configuration", id="manager-form-title", classes="manager-pane-title")
                            yield Label("Configure identity, credentials, model parameters", id="inspector-preview-subtitle")

                    # Section 1: Identity & Persona
                    with Vertical(classes="manager-section-card"):
                        yield Label("IDENTITY & PERSONA", classes="manager-section-title")
                        yield Label("Agent Name", classes="manager-field-label")
                        yield Input(placeholder="e.g. Claude Senior Architect", id="agent-form-name")

                        with Horizontal(classes="manager-row-2col"):
                            with Vertical():
                                yield Label("Specialty / Role", classes="manager-field-label")
                                yield Input(placeholder="e.g. Full-Stack Coder", id="agent-form-role")
                            with Vertical():
                                yield Label("Glyph Icon (◈, ◆, ✦, ⬡, λ)", classes="manager-field-label")
                                yield Input(placeholder="◈", id="agent-form-avatar", value="◈")

                    # Section 2: Intelligence & Runtime
                    with Vertical(classes="manager-section-card"):
                        yield Label("INTELLIGENCE & RUNTIME", classes="manager-section-title")
                        yield Label("Provider / Runtime", classes="manager-field-label")
                        yield Select(
                            PROVIDER_OPTIONS,
                            value="Ollama (Local)",
                            id="agent-form-provider",
                            allow_blank=False,
                        )

                        with Horizontal(id="local-models-row", classes="manager-row-header"):
                            yield Label("Model Selection", id="model-select-label", classes="manager-field-label")
                            yield Button("↺ Refresh", id="manager-btn-refresh-models", classes="manager-btn-xs")

                        initial_local_val = (
                            self.local_models_cache[0][1] if self.local_models_cache else "__custom__"
                        )
                        yield Select(
                            self.local_models_cache,
                            value=initial_local_val,
                            id="agent-form-local-models",
                            allow_blank=False,
                        )

                        yield Label("Model Identifier (or custom override)", classes="manager-field-label")
                        yield Input(
                            placeholder="e.g. qwen3:14b, claude-3-5-sonnet, gpt-4o",
                            id="agent-form-model",
                        )

                    # Section 3: API Endpoint & Credentials
                    with Vertical(classes="manager-section-card"):
                        yield Label("API ENDPOINT & CREDENTIALS", classes="manager-section-title")
                        yield Label("Base URL / API Endpoint", classes="manager-field-label")
                        yield Input(placeholder="e.g. http://localhost:11434/v1", id="agent-form-base-url")

                        yield Label("API Key (stored locally in .oriah/agents.json)", classes="manager-field-label")
                        yield Input(placeholder="sk-... or local", id="agent-form-api-key", password=True)

                    # Section 4: System Parameters & Prompt
                    with Vertical(classes="manager-section-card"):
                        yield Label("SYSTEM PARAMETERS & PROMPT", classes="manager-section-title")
                        with Horizontal(classes="manager-row-2col"):
                            with Vertical():
                                yield Label("Temperature (0.0 - 1.0)", classes="manager-field-label")
                                yield Input(placeholder="0.7", id="agent-form-temp", value="0.7")
                            with Vertical():
                                yield Label("Max Context Tokens", classes="manager-field-label")
                                yield Input(placeholder="4096", id="agent-form-max-tokens", value="4096")

                        yield Label("System Instructions / Context", classes="manager-field-label")
                        yield Input(
                            placeholder="Behavioral constraints, technical rules, or project context...",
                            id="agent-form-instructions",
                        )

                    # Status feedback banner
                    yield Label("", id="manager-status-feedback")

                    # Footer actions
                    with Horizontal(id="manager-form-actions"):
                        yield Button("← Back", id="manager-btn-back", classes="manager-btn-neutral")
                        yield Button("★ Set Active", id="manager-btn-set-active", classes="manager-btn-secondary")
                        yield Button("✕ Delete", id="manager-btn-delete", classes="manager-btn-danger")
                        yield Button("✓ Save Agent", id="manager-btn-save", classes="manager-btn-primary")

    def on_mount(self) -> None:
        self._populate_form_for_selected()

    def _get_clean_glyph(self, avatar: str) -> str:
        """Return a clean colorable monochrome glyph."""
        ALLOWED_GLYPHS = {"◈", "◆", "✦", "★", "☆", "⬡", "λ", "●", "○", "▲", "▼", "■", "□", "§", "⊞", "✓", "✕", "↺", "+"}
        if not avatar:
            return "◈"
        stripped = avatar.strip()
        if stripped in ALLOWED_GLYPHS:
            return stripped
        # Filter out multi-byte emoji codes, variation selectors, or high unicode emojis
        if any(ord(c) > 10000 or ord(c) in (0x2699, 0x26A0, 0x26A1, 0xFE0F) for c in stripped):
            return "◈"
        return stripped[0] if stripped else "◈"

    def _build_agent_item_widget(self, agent: AgentConfig) -> Button:
        is_active = agent.id == self.state.active_agent_id
        is_selected = agent.id == self.selected_agent_id
        active_badge = " ★ ACTIVE" if is_active else ""
        glyph = self._get_clean_glyph(agent.avatar)
        label_text = f"{glyph} {agent.name}\n   [{agent.provider}] {agent.model}{active_badge}"
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
        try:
            count_label = self.query_one("#manager-list-count", Label)
            count_label.update(f"Total: {len(self.state.agents)} configured")
        except Exception:
            pass

    def _populate_form_for_selected(self) -> None:
        feedback = self.query_one("#manager-status-feedback", Label)
        feedback.update("")
        preview_avatar = self.query_one("#inspector-preview-avatar", Label)

        if self.is_creating_new or not self.selected_agent_id:
            self.query_one("#manager-form-title", Label).update("+ Create New Agent")
            preview_avatar.update("◈")
            self.query_one("#agent-form-name", Input).value = ""
            self.query_one("#agent-form-provider", Select).value = "Ollama (Local)"

            default_model = (
                self.local_models_cache[0][1]
                if self.local_models_cache and self.local_models_cache[0][1] != "__custom__"
                else "qwen2.5-coder:14b"
            )
            self._sync_model_select("Ollama (Local)", default_model)
            self.query_one("#agent-form-model", Input).value = default_model
            self.query_one("#agent-form-api-key", Input).value = ""
            self.query_one("#agent-form-base-url", Input).value = PROVIDER_DEFAULT_URLS["Ollama (Local)"]
            self.query_one("#agent-form-role", Input).value = "General Coder"
            self.query_one("#agent-form-avatar", Input).value = "◈"
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
        title = f"Edit: {agent.name} {'(★ ACTIVE)' if is_active else ''}"
        self.query_one("#manager-form-title", Label).update(title)
        preview_avatar.update(self._get_clean_glyph(agent.avatar))
        self.query_one("#agent-form-name", Input).value = agent.name
        try:
            self.query_one("#agent-form-provider", Select).value = agent.provider
        except Exception:
            self.query_one("#agent-form-provider", Select).value = "Custom Endpoint"

        self._sync_model_select(agent.provider, agent.model)
        self.query_one("#agent-form-model", Input).value = agent.model
        self.query_one("#agent-form-api-key", Input).value = agent.api_key
        self.query_one("#agent-form-base-url", Input).value = (
            agent.base_url or PROVIDER_DEFAULT_URLS.get(agent.provider, "")
        )
        self.query_one("#agent-form-role", Input).value = agent.role
        self.query_one("#agent-form-avatar", Input).value = self._get_clean_glyph(agent.avatar)
        self.query_one("#agent-form-temp", Input).value = str(agent.temperature)
        self.query_one("#agent-form-max-tokens", Input).value = str(agent.max_tokens)
        self.query_one("#agent-form-instructions", Input).value = agent.instructions
        self.query_one("#manager-btn-set-active", Button).disabled = is_active
        self.query_one("#manager-btn-delete", Button).disabled = len(self.state.agents) <= 1

    def _sync_model_select(self, provider: str, model_name: str) -> None:
        """Sync model select dropdown options based on provider."""
        try:
            local_select = self.query_one("#agent-form-local-models", Select)
            label = self.query_one("#model-select-label", Label)

            if provider == "Ollama (Local)":
                label.update("Local Models (Ollama)")
                options = self.local_models_cache
            elif provider in PROVIDER_MODEL_SUGGESTIONS:
                label.update(f"Suggested Models ({provider})")
                options = PROVIDER_MODEL_SUGGESTIONS[provider]
            else:
                label.update("Model Presets")
                options = [("Custom Model...", "__custom__")]

            local_select.set_options(options)
            known_values = {val for _, val in options}
            if model_name in known_values:
                local_select.value = model_name
            else:
                local_select.value = "__custom__"
        except Exception:
            pass

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "agent-form-provider":
            prov = str(event.value)
            base_url_input = self.query_one("#agent-form-base-url", Input)
            if prov in PROVIDER_DEFAULT_URLS and (
                self.is_creating_new or not base_url_input.value.strip()
            ):
                base_url_input.value = PROVIDER_DEFAULT_URLS[prov]
            current_model = self.query_one("#agent-form-model", Input).value.strip()
            self._sync_model_select(prov, current_model)

        elif event.select.id == "agent-form-local-models":
            chosen = str(event.value)
            model_input = self.query_one("#agent-form-model", Input)
            if chosen != "__custom__":
                model_input.value = chosen
                name_input = self.query_one("#agent-form-name", Input)
                if self.is_creating_new and (not name_input.value or name_input.value == "Custom Agent"):
                    clean_name = chosen.replace(":", " ").replace("-", " ").replace("_", " ").title()
                    name_input.value = f"{clean_name} Agent"
            else:
                model_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "agent-form-avatar":
            val = event.value.strip()
            try:
                preview = self.query_one("#inspector-preview-avatar", Label)
                preview.update(self._get_clean_glyph(val))
            except Exception:
                pass

    def _handle_back(self) -> None:
        """Go back: revert new agent creation or exit modal to IDE."""
        if self.is_creating_new:
            self.is_creating_new = False
            self.selected_agent_id = (
                self.state.active_agent_id
                if self.state.active_agent_id
                else (self.state.agents[0].id if self.state.agents else None)
            )
            self.run_worker(self._refresh_agent_list())
            self._populate_form_for_selected()
            self.query_one("#manager-status-feedback", Label).update("Returned to agent view.")
        else:
            self.dismiss(True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""

        if button_id in ("manager-btn-close-top", "manager-btn-close", "manager-btn-back", "manager-btn-back-top"):
            self._handle_back()
            return

        if button_id == "manager-btn-refresh-models":
            self.local_models_cache = fetch_local_ollama_models()
            provider = str(self.query_one("#agent-form-provider", Select).value)
            current_model = self.query_one("#agent-form-model", Input).value.strip()
            self._sync_model_select(provider, current_model)
            detected_count = len([m for m in self.local_models_cache if m[1] != "__custom__"])
            feedback = self.query_one("#manager-status-feedback", Label)
            feedback.update(f"↺ Refreshed: {detected_count} local models available.")
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
                feedback.update("★ Agent set as active!")
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
                feedback.update("✕ Agent deleted.")
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
        avatar = self._get_clean_glyph(self.query_one("#agent-form-avatar", Input).value.strip())
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
            feedback.update(f"✓ Created agent '{name}' and saved to disk.")
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
            feedback.update(f"✓ Updated agent '{name}' and saved to disk.")

        await self._refresh_agent_list()
        self._populate_form_for_selected()

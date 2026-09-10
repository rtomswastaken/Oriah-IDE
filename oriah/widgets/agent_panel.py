"""Agent Mode panel featuring horizontal agent cards and interactive prompt."""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label, Static

from oriah.state import AgentConfig, AppState


import uuid


class AgentCardWidget(Vertical):
    """Interactive card representing a single configured AI agent."""

    class Selected(Message):
        def __init__(self, agent: AgentConfig) -> None:
            super().__init__()
            self.agent = agent

    def __init__(self, agent: AgentConfig, is_active: bool = False) -> None:
        unique_id = f"card-{agent.id}-{uuid.uuid4().hex[:6]}"
        super().__init__(classes=f"agent-card {'active-agent' if is_active else ''}", id=unique_id)
        self.agent = agent

    def compose(self) -> ComposeResult:
        with Horizontal(classes="agent-card-header"):
            yield Label(self.agent.avatar, classes="agent-card-avatar")
            yield Label(self.agent.name, classes="agent-card-name")

        yield Label(f"📦 {self.agent.model}", classes="agent-card-badge")
        yield Label(f"Role: {self.agent.role}", classes="agent-card-role")
        yield Label(f"● {self.agent.status} ({self.agent.provider})", classes="agent-card-status")

    def on_click(self) -> None:
        self.post_message(self.Selected(self.agent))


class AddAgentButtonCard(Vertical):
    """Circular/Plus card to trigger the Add Agent modal (Wireframe 3)."""

    class Clicked(Message):
        pass

    def __init__(self) -> None:
        unique_id = f"add-agent-btn-{uuid.uuid4().hex[:6]}"
        super().__init__(id=unique_id, classes="add-agent-card")

    def compose(self) -> ComposeResult:
        yield Label("⊕", classes="add-agent-icon")
        yield Label("Add Agent", classes="add-agent-text")

    def on_click(self) -> None:
        self.post_message(self.Clicked())


class AgentModePanel(Vertical):
    """Agent Mode corresponding to Wireframe 1 and 3."""

    DEFAULT_CSS = """
    AgentModePanel {
        height: 100%;
        layout: vertical;
        background: #131722;
    }
    """

    class PromptSubmitted(Message):
        def __init__(self, agent: AgentConfig, prompt: str) -> None:
            super().__init__()
            self.agent = agent
            self.prompt = prompt

    class AddAgentRequested(Message):
        pass

    def __init__(self, state: AppState, id: str = "agent-mode-panel") -> None:
        super().__init__(id=id)
        self.state = state

    def compose(self) -> ComposeResult:
        with Horizontal(id="agent-cards-scroll"):
            for agent in self.state.agents:
                is_active = agent.id == self.state.active_agent_id
                yield AgentCardWidget(agent, is_active=is_active)
            yield AddAgentButtonCard()

        # Agent activity & prompt bar
        with VerticalScroll(id="agent-log-scroll", classes="agent-activity-box"):
            for log_line in self.state.agent_logs:
                yield Label(log_line, classes="agent-log-line")

        with Horizontal(id="agent-prompt-bar"):
            active = self.state.get_active_agent()
            agent_name = active.name if active else "Agent"
            yield Input(
                placeholder=f"Type instruction for {agent_name} (e.g. 'Refactor this function', 'Generate tests')...",
                id="agent-prompt-input",
            )
            yield Button("Run Agent ↵", id="agent-prompt-send")

    def refresh_cards(self) -> None:
        """Re-render the horizontal cards scroll."""
        scroll = self.query_one("#agent-cards-scroll", Horizontal)
        for child in list(scroll.children):
            child.remove()

        for agent in self.state.agents:
            is_active = agent.id == self.state.active_agent_id
            scroll.mount(AgentCardWidget(agent, is_active=is_active))
        scroll.mount(AddAgentButtonCard())

        # Update input placeholder
        active = self.state.get_active_agent()
        agent_name = active.name if active else "Agent"
        try:
            inp = self.query_one("#agent-prompt-input", Input)
            inp.placeholder = f"Type instruction for {agent_name}..."
        except Exception:
            pass

    def on_agent_card_widget_selected(self, event: AgentCardWidget.Selected) -> None:
        self.state.active_agent_id = event.agent.id
        self.refresh_cards()
        self.append_log(f"🎯 Switched active agent to: {event.agent.name} ({event.agent.model})")

    def on_add_agent_button_card_clicked(self, event: AddAgentButtonCard.Clicked) -> None:
        self.post_message(self.AddAgentRequested())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "agent-prompt-send":
            self._submit_prompt()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "agent-prompt-input":
            self._submit_prompt()

    def _submit_prompt(self) -> None:
        inp = self.query_one("#agent-prompt-input", Input)
        text = inp.value.strip()
        if not text:
            return
        inp.value = ""

        agent = self.state.get_active_agent()
        if not agent:
            return

        self.append_log(f"👤 User: {text}")
        self.append_log(f"{agent.avatar} {agent.name}: Processing request on active workspace...")
        self.post_message(self.PromptSubmitted(agent, text))

    def append_log(self, message: str) -> None:
        self.state.agent_logs.append(message)
        try:
            scroll = self.query_one("#agent-log-scroll", VerticalScroll)
            scroll.mount(Label(message, classes="agent-log-line"))
            scroll.scroll_end(animate=False)
        except Exception:
            pass

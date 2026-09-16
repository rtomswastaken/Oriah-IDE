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

    def __init__(self, agent: AgentConfig, is_active: bool = False, is_lead: bool = False) -> None:
        unique_id = f"card-{agent.id}-{uuid.uuid4().hex[:6]}"
        classes = f"agent-card {'active-agent' if is_active else ''} {'lead-agent' if is_lead else ''}"
        super().__init__(classes=classes.strip(), id=unique_id)
        self.agent = agent
        self.is_lead = is_lead

    def compose(self) -> ComposeResult:
        with Horizontal(classes="agent-card-header"):
            yield Label(self.agent.avatar, classes="agent-card-avatar")
            yield Label(self.agent.name, classes="agent-card-name")
            if self.is_lead:
                yield Label("◈ LEAD", classes="agent-card-lead-badge")

        yield Label(f"◈ {self.agent.model}", classes="agent-card-badge")
        yield Label(f"Role: {self.agent.role}", classes="agent-card-role")
        yield Label(
            f"● {self.agent.status} ({self.agent.provider})",
            classes=f"agent-card-status {self._get_status_class(self.agent.status)}",
        )

    def _get_status_class(self, status: str) -> str:
        s = status.lower()
        if any(w in s for w in ("run", "think", "tool", "work", "spawn")):
            return "status-running"
        elif any(w in s for w in ("err", "fail")):
            return "status-error"
        return "status-idle"

    def update_status(self, status: str) -> None:
        """Dynamically update status label and visual indicator."""
        self.agent.status = status
        try:
            status_label = self.query_one(".agent-card-status", Label)
            status_label.update(f"● {status} ({self.agent.provider})")
            status_label.remove_class("status-idle", "status-running", "status-error")
            status_label.add_class(self._get_status_class(status))
        except Exception:
            pass

    def on_click(self) -> None:
        self.post_message(self.Selected(self.agent))


class ManageAgentsButtonCard(Vertical):
    """Button card to trigger the Agent Management Modal."""

    class Clicked(Message):
        pass

    def __init__(self) -> None:
        unique_id = f"manage-agents-btn-{uuid.uuid4().hex[:6]}"
        super().__init__(id=unique_id, classes="add-agent-card manage-agents-card")

    def compose(self) -> ComposeResult:
        yield Label("◈", classes="add-agent-icon")
        yield Label("Manage Agents", classes="add-agent-text")

    def on_click(self) -> None:
        self.post_message(self.Clicked())


# Backwards compatibility alias
AddAgentButtonCard = ManageAgentsButtonCard


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

    class ManageAgentsRequested(Message):
        pass

    def __init__(self, state: AppState, id: str = "agent-mode-panel") -> None:
        super().__init__(id=id)
        self.state = state

    def compose(self) -> ComposeResult:
        with Horizontal(id="agent-cards-scroll"):
            for agent in self.state.get_ordered_agents():
                is_active = agent.id == self.state.active_agent_id
                is_lead = self.state.is_lead_agent(agent)
                yield AgentCardWidget(agent, is_active=is_active, is_lead=is_lead)
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
        """Re-render the horizontal cards scroll with lead agent first always."""
        scroll = self.query_one("#agent-cards-scroll", Horizontal)
        for child in list(scroll.children):
            child.remove()

        for agent in self.state.get_ordered_agents():
            is_active = agent.id == self.state.active_agent_id
            is_lead = self.state.is_lead_agent(agent)
            scroll.mount(AgentCardWidget(agent, is_active=is_active, is_lead=is_lead))
        scroll.mount(AddAgentButtonCard())

        # Update input placeholder
        active = self.state.get_active_agent()
        agent_name = active.name if active else "Agent"
        try:
            inp = self.query_one("#agent-prompt-input", Input)
            inp.placeholder = f"Type instruction for {agent_name}..."
        except Exception:
            pass

    def update_agent_status(self, agent_id: str, status: str) -> None:
        """Dynamically update status of a specific agent card."""
        for card in self.query(AgentCardWidget):
            if card.agent.id == agent_id:
                card.update_status(status)
                return

    def reset_all_agent_statuses(self, default_status: str = "Idle") -> None:
        """Reset all agent card status indicators."""
        for card in self.query(AgentCardWidget):
            card.update_status(default_status)

    def handle_subagent_spawned(self, child_id: str, role: str) -> None:
        """Dynamically update or mount subagent card when subagent spawns."""
        for card in self.query(AgentCardWidget):
            if card.agent.id == child_id:
                card.update_status(f"Running ({role})")
                return

        matching_role = next(
            (a for a in self.state.agents if a.role.lower() == role.lower() and not self.state.is_lead_agent(a)),
            None
        )
        if matching_role:
            self.update_agent_status(matching_role.id, f"Running ({role})")
            return

        active = self.state.get_active_agent()
        sub = AgentConfig(
            id=child_id,
            name=f"{role.capitalize()} Subagent",
            model=active.model if active else "local-model",
            provider=active.provider if active else "Ollama (Local)",
            role=role.capitalize(),
            status=f"Running ({role})",
            badge_color="#38bdf8",
            avatar="◆",
            base_url=active.base_url if active else "",
        )
        self.state.agents.append(sub)
        self.refresh_cards()

    def on_agent_card_widget_selected(self, event: AgentCardWidget.Selected) -> None:
        self.state.active_agent_id = event.agent.id
        self.refresh_cards()
        self.append_log(f"★ Switched active agent to: {event.agent.name} ({event.agent.model})")

    def on_manage_agents_button_card_clicked(self, event: ManageAgentsButtonCard.Clicked) -> None:
        self.post_message(self.ManageAgentsRequested())
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

        self.append_log(f"◈ User: {text}")
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

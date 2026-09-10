"""Agent Report and Implementation Checklist widget for Oriah IDE."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Checkbox, Label, ProgressBar, TabbedContent, TabPane

from oriah.state import AppState, ChecklistItem


class ChecklistPanel(Vertical):
    """Bottom-left Agent Report & Checklist corresponding to Wireframe Quadrant 3."""

    DEFAULT_CSS = """
    ChecklistPanel {
        height: 100%;
        layout: vertical;
        background: #131722;
    }
    """

    class TaskToggled(Message):
        def __init__(self, item: ChecklistItem) -> None:
            super().__init__()
            self.item = item

    def __init__(self, state: AppState, id: str = "checklist-container") -> None:
        super().__init__(id=id)
        self.state = state

    def compose(self) -> ComposeResult:
        with Horizontal(classes="panel-header"):
            yield Label("📋 AGENT REPORT & TASKS", classes="panel-title")
            yield Label(
                f"{self._completed_count()}/{len(self.state.checklist)}",
                id="checklist-counter",
                classes="panel-subtitle",
            )

        yield ProgressBar(
            total=100,
            show_percentage=True,
            show_eta=False,
            id="checklist-progress-bar",
        )

        with TabbedContent(initial="tab-checklist"):
            with TabPane("Checklist", id="tab-checklist"):
                with VerticalScroll(id="checklist-scroll"):
                    for item in self.state.checklist:
                        with Horizontal(classes=f"checklist-row {'done' if item.done else ''}", id=f"row-{item.id}"):
                            yield Checkbox(
                                item.title,
                                value=item.done,
                                id=f"check-{item.id}",
                                classes="checklist-checkbox",
                            )
            with TabPane("Report", id="tab-report"):
                with VerticalScroll(id="report-scroll"):
                    yield Label(self._generate_report_markdown(), id="report-content-label")

    def _completed_count(self) -> int:
        return sum(1 for item in self.state.checklist if item.done)

    def _generate_report_markdown(self) -> str:
        progress = self.state.get_checklist_progress()
        active_agent = self.state.get_active_agent()
        agent_name = active_agent.name if active_agent else "None"
        return (
            f"📊 **Agent Run Summary**\n\n"
            f"• **Status**: In Progress ({progress:.1f}% complete)\n"
            f"• **Active Agent**: {agent_name}\n"
            f"• **Total Tasks**: {len(self.state.checklist)}\n"
            f"• **Verified Tasks**: {self._completed_count()}\n"
            f"• **Pending**: {len(self.state.checklist) - self._completed_count()}\n\n"
            f"💡 **Recommendation**:\n"
            f"Next step: Select remaining tasks or ask {agent_name} in Agent Mode."
        )

    def on_mount(self) -> None:
        bar = self.query_one("#checklist-progress-bar", ProgressBar)
        bar.progress = self.state.get_checklist_progress()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        check_id = event.checkbox.id or ""
        if check_id.startswith("check-"):
            item_id = check_id.replace("check-", "")
            toggled = self.state.toggle_checklist(item_id)
            if toggled:
                # Update progress bar & counter
                progress = self.state.get_checklist_progress()
                self.query_one("#checklist-progress-bar", ProgressBar).progress = progress
                counter = self.query_one("#checklist-counter", Label)
                counter.update(f"{self._completed_count()}/{len(self.state.checklist)}")
                
                # Update report tab text
                report_label = self.query_one("#report-content-label", Label)
                report_label.update(self._generate_report_markdown())

                # Update row styling
                try:
                    row = self.query_one(f"#row-{item_id}", Horizontal)
                    if toggled.done:
                        row.add_class("done")
                    else:
                        row.remove_class("done")
                except Exception:
                    pass

                self.post_message(self.TaskToggled(toggled))

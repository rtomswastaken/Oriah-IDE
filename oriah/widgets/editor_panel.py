"""Syntax-highlighted multi-tab code editor for Oriah IDE."""

from pathlib import Path
from typing import List, Optional
import uuid
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Label, TextArea

from oriah.state import AppState, EditorTab


class EditorPanel(Vertical):
    """Top-right Code Editor corresponding to Wireframe Quadrant 2."""

    DEFAULT_CSS = """
    EditorPanel {
        height: 100%;
        layout: vertical;
        background: #0d0f14;
    }
    """

    class TabSwitched(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class TabClosed(Message):
        def __init__(self, index: int) -> None:
            super().__init__()
            self.index = index

    class FileSaved(Message):
        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    def __init__(self, state: AppState, id: str = "editor-container") -> None:
        super().__init__(id=id)
        self.state = state
        self._suppress_change = False

    def compose(self) -> ComposeResult:
        yield Horizontal(id="editor-tabs-bar")
        # Initialize TextArea with line numbers
        yield TextArea(
            "",
            language="python",
            theme="monokai",
            show_line_numbers=True,
            id="code-text-area",
        )
        with Horizontal(id="editor-info-bar"):
            yield Label("No file open", id="editor-lang-badge")
            yield Label("", id="editor-path-label")
            yield Label("Ln 1, Col 1", id="editor-cursor-pos")

    def on_mount(self) -> None:
        # Load initial welcome buffer if tabs empty
        if not self.state.tabs:
            welcome_content = (
                '"""\n'
                "Welcome to Oriah IDE — AI Agent-Based Terminal IDE\n"
                "Inspired by Cursor with Multi-Agent Orchestration\n"
                '"""\n\n'
                "def start_coding():\n"
                '    print("Oriah IDE is ready.")\n'
                '    print("Select a file from Directory or ask an agent below.")\n\n'
                'if __name__ == "__main__":\n'
                "    start_coding()\n"
            )
            self.state.tabs.append(
                EditorTab(
                    path="welcome.py",
                    filename="welcome.py",
                    content=welcome_content,
                    language="python",
                    is_dirty=False,
                )
            )
        self.refresh_tabs()
        self.display_active_tab()

    def refresh_tabs(self) -> None:
        """Re-render the tabs in the top bar."""
        tabs_bar = self.query_one("#editor-tabs-bar", Horizontal)
        for child in list(tabs_bar.children):
            child.remove()

        for idx, tab in enumerate(self.state.tabs):
            is_active = idx == self.state.active_tab_index
            dirty_indicator = " ●" if tab.is_dirty else ""
            btn = Button(
                f"{tab.filename}{dirty_indicator} ×",
                id=f"tab-btn-{idx}-{uuid.uuid4().hex[:6]}",
                classes=f"editor-tab-btn {'active-tab' if is_active else ''}",
            )
            tabs_bar.mount(btn)

    def display_active_tab(self) -> None:
        """Update the TextArea with active tab content."""
        tab = self.state.get_active_tab()
        text_area = self.query_one("#code-text-area", TextArea)
        lang_badge = self.query_one("#editor-lang-badge", Label)
        path_label = self.query_one("#editor-path-label", Label)

        if not tab:
            self._suppress_change = True
            text_area.text = ""
            self._suppress_change = False
            lang_badge.update("No file")
            path_label.update("")
            return

        self._suppress_change = True
        text_area.text = tab.content
        text_area.language = tab.language if tab.language != "default" else None
        self._suppress_change = False

        lang_badge.update(f"⎋ {tab.language.upper()}")
        path_label.update(f"  {tab.path}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id.startswith("tab-btn-"):
            parts = btn_id.split("-")
            idx = int(parts[2])
            self.state.active_tab_index = idx
            self.refresh_tabs()
            self.display_active_tab()
            self.post_message(self.TabSwitched(idx))

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self._suppress_change:
            return
        tab = self.state.get_active_tab()
        if tab:
            tab.content = event.text_area.text
            if not tab.is_dirty:
                tab.is_dirty = True
                self.refresh_tabs()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        cursor = event.selection.end
        cursor_label = self.query_one("#editor-cursor-pos", Label)
        cursor_label.update(f"Ln {cursor[0] + 1}, Col {cursor[1] + 1}")

    def save_current_file(self) -> Optional[str]:
        """Save active tab content to disk."""
        tab = self.state.get_active_tab()
        if not tab:
            return None
        try:
            p = Path(tab.path)
            p.write_text(tab.content, encoding="utf-8")
            tab.is_dirty = False
            self.refresh_tabs()
            self.post_message(self.FileSaved(tab.path))
            return tab.path
        except Exception:
            return None

"""Directory Tree and File Explorer for Oriah IDE."""

from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DirectoryTree, Label


class FilteredDirectoryTree(DirectoryTree):
    """Directory tree that hides noise directories."""

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        filtered = []
        for path in paths:
            name = path.name
            if name in {".git", "__pycache__", ".pytest_cache", ".DS_Store"}:
                continue
            filtered.append(path)
        return filtered


class DirectoryPanel(Vertical):
    """Top-left Directory Panel corresponding to Wireframe Quadrant 1."""

    DEFAULT_CSS = """
    DirectoryPanel {
        height: 100%;
        layout: vertical;
    }
    """

    class FileOpenRequested(Message):
        """Dispatched when a file is clicked in the tree."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, root_path: Path, id: str = "directory-container") -> None:
        super().__init__(id=id)
        self.root_path = root_path

    def compose(self) -> ComposeResult:
        with Horizontal(classes="panel-header"):
            yield Label("📁 DIRECTORY", classes="panel-title")
            yield Label(f"/{self.root_path.name}", classes="panel-subtitle")
            yield Button("↻", id="btn-refresh-tree", classes="btn-mini")

        yield FilteredDirectoryTree(self.root_path, id="directory-tree")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle user clicking a file in the tree."""
        event.stop()
        self.post_message(self.FileOpenRequested(event.path))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-refresh-tree":
            tree = self.query_one(FilteredDirectoryTree)
            tree.reload()

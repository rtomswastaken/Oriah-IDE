"""State management and data models for Oriah IDE."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import uuid

LANGUAGE_MAP: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".css": "css",
    ".tcss": "css",
    ".json": "json",
    ".md": "markdown",
    ".rs": "rust",
    ".go": "go",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}


@dataclass
class AgentConfig:
    id: str
    name: str
    model: str
    provider: str
    role: str
    instructions: str = ""
    status: str = "Idle"
    badge_color: str = "#6366f1"
    avatar: str = "🤖"
    total_tokens: int = 0


@dataclass
class ChecklistItem:
    id: str
    title: str
    done: bool = False
    category: str = "Core"


@dataclass
class EditorTab:
    path: str
    filename: str
    content: str
    language: str
    is_dirty: bool = False


class AppState:
    def __init__(self, root_dir: Optional[str] = None) -> None:
        self.root_dir: Path = Path(root_dir or ".").resolve()
        self.agents: List[AgentConfig] = self._default_agents()
        self.active_agent_id: str = self.agents[0].id if self.agents else ""
        self.checklist: List[ChecklistItem] = self._default_checklist()
        self.tabs: List[EditorTab] = []
        self.active_tab_index: int = 0
        self.agent_logs: List[str] = [
            "⚡ Oriah IDE Agent System initialized.",
            f"🧠 3 agents configured. Active agent: {self.agents[0].name} ({self.agents[0].model})",
            "💡 Press [+] in Agent Mode to connect local Gemma/Ollama or cloud models.",
        ]
        self.terminal_history: List[str] = []

    def _default_agents(self) -> List[AgentConfig]:
        return [
            AgentConfig(
                id="agent-1",
                name="Gemma 2 Coder",
                model="gemma2:9b",
                provider="Ollama (Local)",
                role="Full-Stack Coder",
                instructions="Expert code synthesis, refactoring, and test writing in any language.",
                status="Idle",
                badge_color="#38bdf8",
                avatar="💎",
            ),
            AgentConfig(
                id="agent-2",
                name="Qwen Architect",
                model="qwen3-coder:30b",
                provider="Ollama (Local)",
                role="System Architect",
                instructions="System design, architectural boundary verification, and implementation planning.",
                status="Idle",
                badge_color="#a855f7",
                avatar="🏛️",
            ),
            AgentConfig(
                id="agent-3",
                name="Gemini Reviewer",
                model="gemini-1.5-pro",
                provider="Google Gemini (Cloud)",
                role="Code Reviewer",
                instructions="Technical rigor checks, security vulnerability screening, and code correctness.",
                status="Idle",
                badge_color="#22c55e",
                avatar="🛡️",
            ),
        ]

    def _default_checklist(self) -> List[ChecklistItem]:
        return [
            ChecklistItem(id="c-1", title="Initialize Oriah IDE Layout Grid", done=True, category="UI"),
            ChecklistItem(id="c-2", title="Connect Directory Tree & File Watcher", done=True, category="UI"),
            ChecklistItem(id="c-3", title="Multi-language Syntax Highlighted Editor", done=True, category="UI"),
            ChecklistItem(id="c-4", title="Agent Cards Gallery & Active Selection", done=True, category="Agent"),
            ChecklistItem(id="c-5", title="Dynamic Add Agent Modal Dialog", done=True, category="Agent"),
            ChecklistItem(id="c-6", title="Terminal Console & Output Screen", done=True, category="Terminal"),
            ChecklistItem(id="c-7", title="Wireframe 1:1 Layout Fidelity", done=True, category="UI"),
            ChecklistItem(id="c-8", title="Teammate Backend Agent Hooks Integration", done=False, category="Backend"),
        ]

    def get_active_agent(self) -> Optional[AgentConfig]:
        for a in self.agents:
            if a.id == self.active_agent_id:
                return a
        return self.agents[0] if self.agents else None

    def add_agent(
        self,
        name: str,
        model: str,
        provider: str,
        role: str,
        instructions: str = "",
        badge_color: str = "#ec4899",
        avatar: str = "⚡",
    ) -> AgentConfig:
        new_agent = AgentConfig(
            id=f"agent-{uuid.uuid4().hex[:6]}",
            name=name,
            model=model,
            provider=provider,
            role=role,
            instructions=instructions,
            badge_color=badge_color,
            avatar=avatar,
        )
        self.agents.append(new_agent)
        self.active_agent_id = new_agent.id
        self.agent_logs.append(
            f"✨ Added new agent '{name}' [{provider} - {model}]. Role: {role}"
        )
        return new_agent

    def toggle_checklist(self, item_id: str) -> Optional[ChecklistItem]:
        for item in self.checklist:
            if item.id == item_id:
                item.done = not item.done
                return item
        return None

    def add_checklist_item(self, title: str, category: str = "Agent") -> ChecklistItem:
        item = ChecklistItem(id=f"c-{uuid.uuid4().hex[:6]}", title=title, category=category)
        self.checklist.append(item)
        return item

    def get_checklist_progress(self) -> float:
        if not self.checklist:
            return 0.0
        done_count = sum(1 for item in self.checklist if item.done)
        return (done_count / len(self.checklist)) * 100.0

    def open_file(self, file_path: Path) -> EditorTab:
        abs_path = str(file_path.resolve())
        # Check if already open
        for idx, tab in enumerate(self.tabs):
            if tab.path == abs_path:
                self.active_tab_index = idx
                return tab

        # Read content
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            content = f"# Error reading file: {e}"

        suffix = file_path.suffix.lower()
        language = LANGUAGE_MAP.get(suffix, "default")

        tab = EditorTab(
            path=abs_path,
            filename=file_path.name,
            content=content,
            language=language,
            is_dirty=False,
        )
        self.tabs.append(tab)
        self.active_tab_index = len(self.tabs) - 1
        return tab

    def close_tab(self, index: int) -> Optional[EditorTab]:
        if 0 <= index < len(self.tabs):
            closed = self.tabs.pop(index)
            if self.active_tab_index >= len(self.tabs):
                self.active_tab_index = max(0, len(self.tabs) - 1)
            return closed
        return None

    def get_active_tab(self) -> Optional[EditorTab]:
        if 0 <= self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]
        return None

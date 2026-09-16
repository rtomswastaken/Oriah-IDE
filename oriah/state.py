"""State management and data models for Oriah IDE."""

from dataclasses import dataclass, field
from pathlib import Path
import json
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
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "model": self.model,
            "provider": self.provider,
            "role": self.role,
            "instructions": self.instructions,
            "status": self.status,
            "badge_color": self.badge_color,
            "avatar": self.avatar,
            "total_tokens": self.total_tokens,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        return cls(
            id=data.get("id", f"agent-{uuid.uuid4().hex[:6]}"),
            name=data.get("name", "Custom Agent"),
            model=data.get("model", "local-model"),
            provider=data.get("provider", "Ollama (Local)"),
            role=data.get("role", "General Coder"),
            instructions=data.get("instructions", ""),
            status=data.get("status", "Idle"),
            badge_color=data.get("badge_color", "#6366f1"),
            avatar=data.get("avatar", "🤖"),
            total_tokens=data.get("total_tokens", 0),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            temperature=float(data.get("temperature", 0.7)),
            max_tokens=int(data.get("max_tokens", 4096)),
        )


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
        self.config_dir: Path = self.root_dir / ".oriah"
        self.config_file: Path = self.config_dir / "agents.json"
        self.agents: List[AgentConfig] = []
        if not self.load_agents_from_disk():
            self.agents = self._default_agents()
        self.active_agent_id: str = self.agents[0].id if self.agents else ""
        self.checklist: List[ChecklistItem] = self._default_checklist()
        self.tabs: List[EditorTab] = []
        self.active_tab_index: int = 0
        self.agent_logs: List[str] = [
            "⚡ Oriah IDE Agent System initialized.",
            f"🧠 {len(self.agents)} agents configured. Active agent: {self.get_active_agent().name if self.get_active_agent() else 'None'}",
            "💡 Press ⚙️ Manage Agents or Ctrl+M to configure multi-agent APIs.",
        ]
        self.terminal_history: List[str] = []

    def save_agents_to_disk(self) -> None:
        """Persist all agent configurations to .oriah/agents.json."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "active_agent_id": self.active_agent_id,
                "agents": [a.to_dict() for a in self.agents],
            }
            self.config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            self.agent_logs.append(f"⚠️ Failed to save agents to disk: {e}")

    def load_agents_from_disk(self) -> bool:
        """Load agents from .oriah/agents.json if present."""
        if not self.config_file.exists():
            return False
        try:
            content = self.config_file.read_text(encoding="utf-8")
            data = json.loads(content)
            loaded_agents = [AgentConfig.from_dict(item) for item in data.get("agents", [])]
            if loaded_agents:
                self.agents = loaded_agents
                saved_active = data.get("active_agent_id")
                if any(a.id == saved_active for a in self.agents):
                    self.active_agent_id = saved_active
                else:
                    self.active_agent_id = self.agents[0].id
                return True
        except Exception as e:
            # Fall back to defaults on corrupt config
            pass
        return False

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
                base_url="http://localhost:11434/v1",
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
                base_url="http://localhost:11434/v1",
            ),
            AgentConfig(
                id="agent-3",
                name="Gemini Reviewer",
                model="gemini-1.5-pro",
                provider="Google Gemini",
                role="Code Reviewer",
                instructions="Technical rigor checks, security vulnerability screening, and code correctness.",
                status="Idle",
                badge_color="#22c55e",
                avatar="🛡️",
                base_url="https://generativelanguage.googleapis.com/v1beta",
            ),
        ]

    def _default_checklist(self) -> List[ChecklistItem]:
        return [
            ChecklistItem(id="c-1", title="Initialize Oriah IDE Layout Grid", done=True, category="UI"),
            ChecklistItem(id="c-2", title="Connect Directory Tree & File Watcher", done=True, category="UI"),
            ChecklistItem(id="c-3", title="Multi-language Syntax Highlighted Editor", done=True, category="UI"),
            ChecklistItem(id="c-4", title="Agent Cards Gallery & Active Selection", done=True, category="Agent"),
            ChecklistItem(id="c-5", title="Multi-Agent API Manager & Config Menu", done=True, category="Agent"),
            ChecklistItem(id="c-6", title="Terminal Console & Output Screen", done=True, category="Terminal"),
            ChecklistItem(id="c-7", title="Wireframe 1:1 Layout Fidelity", done=True, category="UI"),
            ChecklistItem(id="c-8", title="Teammate Backend Agent Hooks Integration", done=True, category="Backend"),
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
        api_key: str = "",
        base_url: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
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
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.agents.append(new_agent)
        self.active_agent_id = new_agent.id
        self.save_agents_to_disk()
        self.agent_logs.append(
            f"✨ Added new agent '{name}' [{provider} - {model}]. Role: {role}"
        )
        return new_agent

    def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        role: Optional[str] = None,
        instructions: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        avatar: Optional[str] = None,
        badge_color: Optional[str] = None,
    ) -> bool:
        """Update existing agent configuration and persist changes."""
        for a in self.agents:
            if a.id == agent_id:
                if name is not None:
                    a.name = name
                if model is not None:
                    a.model = model
                if provider is not None:
                    a.provider = provider
                if role is not None:
                    a.role = role
                if instructions is not None:
                    a.instructions = instructions
                if api_key is not None:
                    a.api_key = api_key
                if base_url is not None:
                    a.base_url = base_url
                if temperature is not None:
                    a.temperature = temperature
                if max_tokens is not None:
                    a.max_tokens = max_tokens
                if avatar is not None:
                    a.avatar = avatar
                if badge_color is not None:
                    a.badge_color = badge_color
                self.save_agents_to_disk()
                self.agent_logs.append(f"🔧 Updated agent config: '{a.name}' [{a.model}]")
                return True
        return False

    def delete_agent(self, agent_id: str) -> bool:
        """Delete agent by ID and update active agent."""
        initial_len = len(self.agents)
        deleted_agent = next((a for a in self.agents if a.id == agent_id), None)
        self.agents = [a for a in self.agents if a.id != agent_id]
        if len(self.agents) < initial_len:
            if self.active_agent_id == agent_id:
                self.active_agent_id = self.agents[0].id if self.agents else ""
            self.save_agents_to_disk()
            if deleted_agent:
                self.agent_logs.append(f"🗑️ Removed agent: '{deleted_agent.name}'")
            return True
        return False

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

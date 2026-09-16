from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class RoleDefinition:
    name: str
    description: str
    system_prompt: str
    allowed_tools: List[str] = field(default_factory=list)
    model_override: Optional[str] = None
    can_spawn_subagents: bool = False
    max_steps: Optional[int] = None

BUILTIN_ROLES: List[RoleDefinition] = [
    RoleDefinition(
        name="lead",
        description="Lead Orchestrator: analyzes tasks, decomposes goals, and dispatches subagents.",
        system_prompt=(
            "You are the Lead Orchestrator agent. Your job is to analyze user tasks, "
            "break them down into focused subtasks, and dispatch specialized subagents "
            "(coder, exec, researcher). When subagents finish, summarize the final outcome."
        ),
        allowed_tools=["read_file", "list_dir", "grep_search", "invoke_subagent"],
        can_spawn_subagents=True,
    ),
    RoleDefinition(
        name="coder",
        description="Coder: specializes in reading files, writing clean code, and applying surgical patches.",
        system_prompt=(
            "You are the Coder agent. You specialize in reading files, writing clean code, "
            "and applying surgical contiguous line patches with patch_file. Focus only on code changes."
        ),
        allowed_tools=["read_file", "write_file", "patch_file", "list_dir", "grep_search"],
        can_spawn_subagents=False,
    ),
    RoleDefinition(
        name="exec",
        description="Exec: runs shell commands, compilers, linters, and test suites.",
        system_prompt=(
            "You are the Exec agent. You run shell commands, compilers, linters, and test suites "
            "using run_command. Inspect outputs, return clear diagnostics."
        ),
        allowed_tools=["read_file", "run_command", "list_dir"],
        can_spawn_subagents=False,
    ),
    RoleDefinition(
        name="researcher",
        description="Researcher: read-only inspector for directory structure and dependency mapping.",
        system_prompt=(
            "You are the Researcher agent. You inspect project directories, grep codebase patterns, "
            "and map dependencies. Do not make code edits."
        ),
        allowed_tools=["read_file", "list_dir", "grep_search"],
        can_spawn_subagents=False,
    ),
]

ROLES_SYSTEM_PROMPTS: Dict[str, str] = {r.name: r.system_prompt for r in BUILTIN_ROLES}

class RoleRegistry:
    def __init__(self) -> None:
        self._roles: Dict[str, RoleDefinition] = {}
        for role in BUILTIN_ROLES:
            self.register(role)

    def register(self, role: RoleDefinition) -> None:
        self._roles[role.name.lower()] = role

    def get(self, name: str) -> Optional[RoleDefinition]:
        return self._roles.get(name.lower())

    def list_roles(self) -> List[RoleDefinition]:
        return list(self._roles.values())

    def build_roles_catalog_prompt(self) -> str:
        lines = ["Available Subagent Roles:"]
        for r in self._roles.values():
            if r.name.lower() == "lead":
                continue
            lines.append(f"- '{r.name}': {r.description} (Allowed tools: {', '.join(r.allowed_tools)})")
        return "\n".join(lines)

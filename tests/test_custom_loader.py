import pytest
from pathlib import Path
from oriah.tools.registry import ToolRegistry
from oriah.agent.roles import RoleRegistry
from oriah.tools.custom_loader import load_custom_tools, load_custom_roles

def test_load_custom_tools_from_workspace(tmp_path: Path):
    oriah_dir = tmp_path / ".oriah"
    oriah_dir.mkdir()
    custom_tools_file = oriah_dir / "custom_tools.py"
    custom_tools_file.write_text(
        "from oriah.tools.registry import custom_tool\n\n"
        "@custom_tool(name='workspace_ping', description='Returns pong')\n"
        "async def workspace_ping() -> str:\n"
        "    return 'pong'\n"
    )

    registry = ToolRegistry()
    loaded = load_custom_tools(registry, tmp_path)
    assert "workspace_ping" in loaded
    assert "workspace_ping" in registry._tools

def test_load_custom_roles_from_workspace(tmp_path: Path):
    roles_dir = tmp_path / ".oriah" / "roles"
    roles_dir.mkdir(parents=True)
    custom_role_file = roles_dir / "qa_lead.py"
    custom_role_file.write_text(
        "from oriah.agent.roles import RoleDefinition\n\n"
        "role = RoleDefinition(\n"
        "    name='qa_lead',\n"
        "    description='Lead QA specialist',\n"
        "    system_prompt='You lead QA tests',\n"
        "    allowed_tools=['read_file', 'run_command'],\n"
        ")\n"
    )

    role_registry = RoleRegistry()
    loaded = load_custom_roles(role_registry, tmp_path)
    assert "qa_lead" in loaded
    role = role_registry.get("qa_lead")
    assert role is not None
    assert role.name == "qa_lead"

def test_load_corrupt_files_graceful(tmp_path: Path):
    oriah_dir = tmp_path / ".oriah"
    roles_dir = oriah_dir / "roles"
    roles_dir.mkdir(parents=True)
    
    # Broken python syntax
    (oriah_dir / "custom_tools.py").write_text("def broken_syntax(")
    (roles_dir / "corrupt_role.py").write_text("this is not python code :::")

    tool_reg = ToolRegistry()
    role_reg = RoleRegistry()

    # Should not raise exception
    loaded_tools = load_custom_tools(tool_reg, tmp_path)
    loaded_roles = load_custom_roles(role_reg, tmp_path)

    assert loaded_tools == []
    assert "corrupt_role" not in loaded_roles

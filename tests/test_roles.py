from oriah.agent.roles import RoleDefinition, RoleRegistry, BUILTIN_ROLES

def test_builtin_roles_exist():
    registry = RoleRegistry()
    assert registry.get("lead") is not None
    assert registry.get("coder") is not None
    assert registry.get("exec") is not None
    assert registry.get("researcher") is not None
    assert registry.get("lead").can_spawn_subagents is True
    assert registry.get("coder").can_spawn_subagents is False

def test_custom_role_registration():
    registry = RoleRegistry()
    custom = RoleDefinition(
        name="tester",
        description="Runs test suites",
        system_prompt="You are a test runner",
        allowed_tools=["run_command"],
        can_spawn_subagents=False,
    )
    registry.register(custom)
    fetched = registry.get("tester")
    assert fetched is not None
    assert fetched.name == "tester"
    assert "run_command" in fetched.allowed_tools

def test_roles_catalog_prompt():
    registry = RoleRegistry()
    prompt = registry.build_roles_catalog_prompt()
    assert "coder" in prompt
    assert "researcher" in prompt

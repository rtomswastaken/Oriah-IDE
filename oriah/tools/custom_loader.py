import importlib.util
import logging
from pathlib import Path
from typing import List
from oriah.tools.registry import ToolRegistry
from oriah.agent.roles import RoleRegistry, RoleDefinition

logger = logging.getLogger("oriah.custom_loader")

def load_custom_tools(registry: ToolRegistry, workspace_root: Path) -> List[str]:
    """Dynamically load and register tools decorated with @custom_tool from .oriah/custom_tools.py."""
    custom_tools_path = workspace_root / ".oriah" / "custom_tools.py"
    if not custom_tools_path.is_file():
        return []

    loaded: List[str] = []
    try:
        spec = importlib.util.spec_from_file_location("oriah_custom_tools", str(custom_tools_path))
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for attr_name in dir(module):
                obj = getattr(module, attr_name)
                if callable(obj) and getattr(obj, "_is_custom_tool", False):
                    registry.register_custom_fn(obj)
                    tool_name = getattr(obj, "_tool_name", attr_name)
                    loaded.append(tool_name)
    except Exception as e:
        logger.warning("Failed loading custom tools from %s: %s", custom_tools_path, e)

    return loaded

def load_custom_roles(role_registry: RoleRegistry, workspace_root: Path) -> List[str]:
    """Dynamically load RoleDefinition instances from .oriah/roles/*.py."""
    roles_dir = workspace_root / ".oriah" / "roles"
    if not roles_dir.is_dir():
        return []

    loaded: List[str] = []
    for py_file in sorted(roles_dir.glob("*.py")):
        if py_file.name.startswith("__"):
            continue
        try:
            mod_name = f"oriah_role_{py_file.stem}"
            spec = importlib.util.spec_from_file_location(mod_name, str(py_file))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                role_obj = getattr(module, "role", None)
                if isinstance(role_obj, RoleDefinition):
                    role_registry.register(role_obj)
                    loaded.append(role_obj.name)
                else:
                    for attr_name in dir(module):
                        cand = getattr(module, attr_name)
                        if isinstance(cand, RoleDefinition):
                            role_registry.register(cand)
                            loaded.append(cand.name)
        except Exception as e:
            logger.warning("Failed loading custom role from %s: %s", py_file, e)

    return loaded

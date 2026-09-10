import fnmatch
import os
import re
from pathlib import Path
from typing import List, Optional
from oriah.tools.registry import ToolRegistry

def _resolve_safe_path(workspace_root: str, path_str: str) -> Path:
    base = Path(workspace_root).resolve()
    target = (base / path_str).resolve()
    if not str(target).startswith(str(base)):
        raise PermissionError(f"Escaping workspace boundary: '{path_str}'")
    return target

def register_fs_tools(registry: ToolRegistry, workspace_root: str) -> None:
    @registry.register("read_file", "Read line-numbered contents of a file in the workspace.")
    async def read_file(path: str, offset: int = 1, limit: int = 200) -> str:
        target = _resolve_safe_path(workspace_root, path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        start = max(1, offset)
        end = min(len(lines), start + limit - 1)
        selected = lines[start - 1:end]
        output = [f"{i}: {line.rstrip()}" for i, line in enumerate(selected, start=start)]
        return "\n".join(output) if output else "(empty file or range)"

    @registry.register("write_file", "Create or overwrite a file in the workspace.")
    async def write_file(path: str, content: str, overwrite: bool = False) -> str:
        target = _resolve_safe_path(workspace_root, path)
        if target.exists() and not overwrite:
            raise ValueError(f"File already exists: '{path}'. Pass overwrite=True to replace.")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created {path} ({len(content)} bytes)"

    @registry.register("patch_file", "Atomically replace a single exact contiguous block of code.")
    async def patch_file(path: str, target: str, replacement: str) -> str:
        file_path = _resolve_safe_path(workspace_root, path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        occurrences = content.count(target)
        if occurrences == 0:
            raise ValueError(f"Target snippet not found in {path}")
        if occurrences > 1:
            raise ValueError(f"Target snippet found {occurrences} times in {path}; must be unique.")
        new_content = content.replace(target, replacement, 1)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Patched {path}"

    @registry.register("grep_search", "Search files in the workspace for exact text or regex.")
    async def grep_search(query: str, path: str = ".", regex: bool = False) -> str:
        search_root = _resolve_safe_path(workspace_root, path)
        pattern = re.compile(query if regex else re.escape(query))
        results = []
        ignored_dirs = {".git", "node_modules", "target", "__pycache__", ".venv", "dist", "build"}

        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                fpath = Path(root) / file
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, start=1):
                            if pattern.search(line):
                                rel = fpath.relative_to(Path(workspace_root).resolve())
                                results.append(f"{rel}:{line_no}: {line.strip()}")
                                if len(results) >= 50:
                                    results.append("... (capped at 50 results)")
                                    return "\n".join(results)
                except Exception:
                    continue
        return "\n".join(results) if results else "No matches found."

    @registry.register("find_files", "Search files in the workspace matching a glob pattern.")
    async def find_files(pattern: str = "*", path: str = ".") -> str:
        search_root = _resolve_safe_path(workspace_root, path)
        ignored_dirs = {".git", "node_modules", "target", "__pycache__", ".venv", "dist", "build"}
        matches = []

        for root, dirs, files in os.walk(search_root):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for name in files + dirs:
                if fnmatch.fnmatch(name, pattern):
                    full = Path(root) / name
                    rel = full.relative_to(Path(workspace_root).resolve())
                    matches.append(str(rel))
                    if len(matches) >= 100:
                        matches.append("... (capped at 100 files)")
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "No matching files."

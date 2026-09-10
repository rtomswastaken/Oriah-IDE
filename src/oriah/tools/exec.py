import asyncio
from pathlib import Path
from oriah.tools.registry import ToolRegistry
from oriah.tools.fs import _resolve_safe_path

def register_exec_tools(registry: ToolRegistry, workspace_root: str) -> None:
    @registry.register("run_command", "Execute a terminal shell command in the workspace directory.")
    async def run_command(cmd: str, cwd: str = ".", timeout: int = 60) -> str:
        safe_cwd = _resolve_safe_path(workspace_root, cwd)

        # Destructive command safety guard
        destructive = ["rm -rf /", "rm -rf /*", "mkfs", ":(){ :|:& };:"]
        if any(d in cmd for d in destructive):
            raise PermissionError(f"Blocked dangerous command: {cmd}")

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(safe_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await asyncio.wait_for(
                proc.communicate(), timeout=float(timeout)
            )
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return f"Command timed out after {timeout} seconds."

        stdout_str = stdout_data.decode("utf-8", errors="replace").strip()
        stderr_str = stderr_data.decode("utf-8", errors="replace").strip()

        # Truncate large output to 2000 chars
        if len(stdout_str) > 2000:
            stdout_str = stdout_str[:2000] + "\n... [stdout truncated]"
        if len(stderr_str) > 2000:
            stderr_str = stderr_str[:2000] + "\n... [stderr truncated]"

        out_lines = [f"Exit code: {proc.returncode}"]
        if stdout_str:
            out_lines.append(f"STDOUT:\n{stdout_str}")
        if stderr_str:
            out_lines.append(f"STDERR:\n{stderr_str}")

        return "\n".join(out_lines)

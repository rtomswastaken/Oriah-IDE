import os
from pathlib import Path
from pydantic import BaseModel, Field

class EngineConfig(BaseModel):
    base_url: str = Field(default="http://localhost:11434/v1")
    model: str = Field(default="qwen2.5-coder:14b")
    api_key: str = Field(default="local")
    workspace_root: str = Field(default=".")
    timeout: float = Field(default=60.0)
    max_steps: int = Field(default=25)
    context_limit: int = Field(default=8192)

    @property
    def resolved_workspace(self) -> str:
        return str(Path(self.workspace_root).resolve())

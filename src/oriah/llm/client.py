import json
from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field
from oriah.config import EngineConfig

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]

class LLMResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)

class LLMClient:
    def __init__(self, config: EngineConfig, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.timeout,
            transport=transport,
        )

    async def complete(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> LLMResponse:
        url = "/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools

        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]["message"]
        content = choice.get("content")
        raw_tools = choice.get("tool_calls", [])

        parsed_tools: List[ToolCall] = []
        for item in raw_tools:
            func = item["function"]
            args = func["arguments"]
            parsed_args = json.loads(args) if isinstance(args, str) else args
            parsed_tools.append(
                ToolCall(
                    id=item.get("id", "call_default"),
                    name=func["name"],
                    arguments=parsed_args,
                )
            )

        return LLMResponse(content=content, tool_calls=parsed_tools)

    async def aclose(self) -> None:
        await self._client.aclose()

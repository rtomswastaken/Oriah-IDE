import json
from typing import Any, Dict, List

def json_dumps(obj: Any) -> str:
    return json.dumps(obj)

class AgentContext:
    def __init__(self, system_prompt: str, max_turns: int = 25):
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_assistant(self, content: str | None, tool_calls: list | None = None) -> None:
        msg: Dict[str, Any] = {"role": "assistant"}
        if content is not None:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": json_dumps(tc.arguments)},
                }
                for tc in tool_calls
            ]
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, name: str, result: str) -> None:
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": result,
        })

    def compact(self) -> None:
        # Keep system prompt (index 0) and original prompt (index 1).
        # Truncate old tool messages if history gets excessively long.
        if len(self.messages) > 30:
            pinned = self.messages[:2]
            tail = self.messages[-20:]
            summary = {
                "role": "system",
                "content": f"[History compacted: {len(self.messages) - 22} prior turns summarized]"
            }
            self.messages = [pinned[0], pinned[1], summary] + tail

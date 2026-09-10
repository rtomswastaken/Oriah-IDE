import inspect
from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, create_model

class Tool:
    def __init__(self, name: str, description: str, func: Callable[..., Coroutine[Any, Any, Any]]):
        self.name = name
        self.description = description
        self.func = func
        self.param_model = self._create_param_model()

    def _create_param_model(self) -> type[BaseModel]:
        sig = inspect.signature(self.func)
        fields: Dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[param_name] = (param_type, default)
        return create_model(f"{self.name}_params", **fields)

    def to_openai_schema(self) -> Dict[str, Any]:
        schema = self.param_model.model_json_schema()
        schema.pop("title", None)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema
            }
        }

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, name: str, description: str) -> Callable:
        def decorator(func: Callable) -> Callable:
            self._tools[name] = Tool(name=name, description=description, func=func)
            return func
        return decorator

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_openai_schema() for tool in self._tools.values()]

    async def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: '{name}'. Available: {list(self._tools.keys())}")
        tool = self._tools[name]
        validated = tool.param_model(**arguments)
        res = tool.func(**validated.model_dump())
        if inspect.isawaitable(res):
            return await res
        return res

import inspect
from typing import Any, Callable, Coroutine, Dict, List, Optional
from pydantic import BaseModel, create_model

def custom_tool(name: Optional[str] = None, description: Optional[str] = None) -> Callable:
    """Decorator for marking workspace functions as custom agent tools."""
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        setattr(fn, "_is_custom_tool", True)
        setattr(fn, "_tool_name", name or fn.__name__)
        setattr(fn, "_tool_description", description or fn.__doc__ or f"Custom tool {fn.__name__}")
        return fn
    return decorator

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

    def register_custom_fn(
        self,
        fn: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        tool_name = name or getattr(fn, "_tool_name", fn.__name__)
        desc = description or getattr(fn, "_tool_description", fn.__doc__ or f"Custom tool {tool_name}")
        self.register(tool_name, desc)(fn)

    def subset(self, allowed_tools: List[str]) -> "ToolRegistry":
        """Return a new ToolRegistry instance containing only the allowed tools."""
        new_reg = ToolRegistry()
        if "*" in allowed_tools:
            new_reg._tools = dict(self._tools)
            return new_reg
        for name in allowed_tools:
            if name in self._tools:
                new_reg._tools[name] = self._tools[name]
        return new_reg

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

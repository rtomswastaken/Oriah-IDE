import argparse
import asyncio
import sys
from oriah.config import EngineConfig
from oriah.engine import AsyncEngine
from oriah.events import (
    AgentThought,
    SubagentSpawned,
    TaskFinished,
    TaskStarted,
    ToolCallCompleted,
    ToolCallRequested,
)

async def run_task(prompt: str, base_url: str, model: str) -> None:
    config = EngineConfig(base_url=base_url, model=model)
    engine = AsyncEngine(config=config)

    print(f"\n[Oriah Engine] Running task: {prompt}")
    print(f"[Oriah Engine] Model: {model} @ {base_url}\n" + "-" * 50)

    try:
        async for event in engine.run(prompt):
            if isinstance(event, TaskStarted):
                print(f"[*] Task Started: {event.task_id}")
            elif isinstance(event, AgentThought):
                print(f"\n[{event.agent_id}] {event.thought}")
            elif isinstance(event, ToolCallRequested):
                print(f"  -> Tool Call: {event.tool_name}({event.arguments})")
            elif isinstance(event, ToolCallCompleted):
                if event.error:
                    print(f"  <- Tool Error: {event.error}")
                else:
                    snippet = (event.result or "")[:120].replace("\n", " ")
                    print(f"  <- Tool Result: {snippet}...")
            elif isinstance(event, SubagentSpawned):
                print(f"\n[+] Spawned Subagent [{event.child_id}] (Role: {event.role})")
            elif isinstance(event, TaskFinished):
                print("\n" + "=" * 50)
                if event.status == "success":
                    print(f"[SUCCESS] Final Summary:\n{event.summary}")
                else:
                    print(f"[ERROR] Task Failed: {event.error}")
    finally:
        await engine.aclose()

def main() -> None:
    parser = argparse.ArgumentParser(description="Oriah Local Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Execute an agent task")
    run_p.add_argument("prompt", help="Task description")
    run_p.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible base URL")
    run_p.add_argument("--model", default="qwen2.5-coder:14b", help="Model name")

    args = parser.parse_args()
    if args.command == "run":
        asyncio.run(run_task(args.prompt, args.base_url, args.model))

if __name__ == "__main__":
    main()

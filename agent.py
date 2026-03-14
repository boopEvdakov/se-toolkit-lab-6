#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM with tools to answer questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    All debug output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# Maximum number of tool calls per question
MAX_TOOL_CALLS = 10


def load_env():
    """Load environment variables from .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_file)


def safe_path(path: str) -> Path:
    """
    Validate that a path is within the project directory.
    Prevents path traversal attacks (../).
    """
    project_root = Path(__file__).parent.resolve()

    # Reject absolute paths
    if os.path.isabs(path):
        raise ValueError(f"Absolute paths not allowed: {path}")

    # Reject path traversal
    if ".." in path:
        raise ValueError(f"Path traversal detected: {path}")

    # Resolve and validate
    full_path = (project_root / path).resolve()
    if not str(full_path).startswith(str(project_root)):
        raise ValueError(f"Path outside project: {path}")

    return full_path


def read_file(path: str) -> str:
    """
    Read contents of a file from the project.

    Args:
        path: Relative path from project root

    Returns:
        File contents as string, or error message
    """
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: File not found: {path}"
        if not safe.is_file():
            return f"Error: Not a file: {path}"
        return safe.read_text(encoding="utf-8")
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """
    List files and directories at a given path.

    Args:
        path: Relative directory path from project root

    Returns:
        Newline-separated listing, or error message
    """
    try:
        safe = safe_path(path)
        if not safe.exists():
            return f"Error: Path not found: {path}"
        if not safe.is_dir():
            return f"Error: Not a directory: {path}"

        entries = []
        for entry in sorted(safe.iterdir()):
            suffix = "/" if entry.is_dir() else ""
            entries.append(f"{entry.name}{suffix}")
        return "\n".join(entries)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


# Tool definitions for LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read contents of a file from the project repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git.md')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path in the project",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')",
                    }
                },
                "required": ["path"],
            },
        },
    },
]

# Tool name to function mapping
TOOL_FUNCTIONS = {"read_file": read_file, "list_files": list_files}

SYSTEM_PROMPT = """You are a helpful documentation assistant. You have access to tools that let you read files and list directories in a project repository.

When asked a question about the project:
1. Use `list_files` to explore the directory structure if needed
2. Use `read_file` to read relevant documentation files
3. Find the answer in the files you read
4. Include the source reference (file path and section anchor if applicable)

Always be specific about which file contains the answer. Format section references as: `wiki/filename.md#section-anchor`

If you cannot find the answer after exploring the available files, say so honestly."""


def call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Call the LLM API and return the response."""
    api_base = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not all([api_base, api_key, model]):
        print("Error: Missing LLM configuration in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    url = f"{api_base}/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if api_key and api_key != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {"model": model, "messages": messages, "stream": False}

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    print(f"Calling LLM API: {url}", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)

    response = requests.post(url, headers=headers, json=payload, timeout=300)

    if response.status_code != 200:
        print(f"Error: API returned status {response.status_code}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    return data["choices"][0]["message"]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    print(f"Executing tool: {name} with args: {args}", file=sys.stderr)

    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {name}"

    try:
        func = TOOL_FUNCTIONS[name]
        result = func(**args)
        print(
            f"Tool result: {result[:200]}..."
            if len(result) > 200
            else f"Tool result: {result}",
            file=sys.stderr,
        )
        return result
    except Exception as e:
        return f"Error executing tool: {e}"


def extract_source_from_tool_calls(tool_calls: list[dict]) -> str:
    """Extract source reference from tool calls (last read_file path)."""
    source = ""
    for call in reversed(tool_calls):
        if call.get("tool") == "read_file":
            path = call.get("args", {}).get("path", "")
            if path:
                source = path
                break
    return source


def run_agent(question: str) -> dict:
    """
    Run the agentic loop to answer a question.

    Returns:
        dict with answer, source, and tool_calls
    """
    # Initialize conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []
    iterations = 0

    while iterations < MAX_TOOL_CALLS:
        iterations += 1
        print(f"\n--- Iteration {iterations} ---", file=sys.stderr)

        # Call LLM
        response = call_llm(messages, tools=TOOLS)

        # Check for tool calls
        if response.get("tool_calls"):
            for tool_call in response["tool_calls"]:
                func = tool_call.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")

                try:
                    args = (
                        json.loads(args_str) if isinstance(args_str, str) else args_str
                    )
                except json.JSONDecodeError:
                    args = {}

                # Execute tool
                result = execute_tool(name, args)

                # Log tool call
                tool_calls_log.append({"tool": name, "args": args, "result": result})

                # Append tool result to messages
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    }
                )

            # Continue loop to get next LLM response
            continue

        # No tool calls - extract final answer
        answer = response.get("content", "")
        source = extract_source_from_tool_calls(tool_calls_log)

        return {"answer": answer, "source": source, "tool_calls": tool_calls_log}

    # Max iterations reached
    print("Warning: Max tool calls reached", file=sys.stderr)
    source = extract_source_from_tool_calls(tool_calls_log)
    return {
        "answer": "I reached the maximum number of tool calls without finding a complete answer.",
        "source": source,
        "tool_calls": tool_calls_log,
    }


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print('Usage: uv run agent.py "Your question"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment
    load_env()

    # Run agent
    result = run_agent(question)

    # Output JSON to stdout
    print(json.dumps(result))


if __name__ == "__main__":
    main()

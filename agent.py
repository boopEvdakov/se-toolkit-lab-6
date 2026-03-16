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
    """Load environment variables from .env.agent.secret and .env.docker.secret."""
    # Load LLM config from .env.agent.secret
    env_file = Path(__file__).parent / ".env.agent.secret"
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_file)

    # Load backend API config from .env.docker.secret
    docker_env_file = Path(__file__).parent / ".env.docker.secret"
    if docker_env_file.exists():
        load_dotenv(docker_env_file, override=False)


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


def query_api(method: str, path: str, body: str = None) -> str:
    """
    Call the backend API with authentication.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API path (e.g., '/items/', '/analytics/completion-rate')
        body: Optional JSON request body for POST/PUT requests

    Returns:
        JSON string with status_code and body, or error message
    """
    api_base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    lms_api_key = os.getenv("LMS_API_KEY")

    if not lms_api_key:
        return "Error: LMS_API_KEY not configured in environment"

    url = f"{api_base_url}{path}"
    headers = {"Content-Type": "application/json", "X-API-Key": lms_api_key}

    print(f"Calling API: {method} {url}", file=sys.stderr)

    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            data = json.loads(body) if body else {}
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return f"Error: Unsupported method: {method}"

        result = {
            "status_code": response.status_code,
            "body": response.json() if response.text else None,
        }
        return json.dumps(result)
    except requests.exceptions.RequestException as e:
        return f"Error: API request failed: {e}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON response: {e}"


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
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to query data, check status codes, or test endpoints",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, etc.)",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g., '/items/', '/analytics/completion-rate')",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body for POST/PUT requests",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]

# Tool name to function mapping
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}

SYSTEM_PROMPT = """You are a helpful documentation assistant with access to these tools:

1. read_file(path) - Read contents of a file (e.g., wiki/github.md, backend/app/main.py)
2. list_files(path) - List files in a directory
3. query_api(method, path, body) - Call the backend API

RULES:
- For wiki/documentation questions: Call read_file with the specific file path, then answer based on the content
- For source code questions: Call read_file with the source file path, then answer based on the content
- For directory listing questions: Call list_files, then answer immediately with the results
- For API/data questions: Call query_api, then answer immediately with the results
- AFTER receiving tool results, provide a FINAL ANSWER immediately - do not make more tool calls unless absolutely necessary
- Include the source file path in your final answer when applicable

Be concise and direct. Once you have the information from a tool, answer the question immediately.
"""


def call_llm(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Call the LLM API and return the response."""
    api_base = os.getenv("LLM_API_BASE")
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL")

    if not all([api_base, api_key, model]):
        print("Error: Missing LLM configuration in .env.agent.secret", file=sys.stderr)
        sys.exit(1)

    # Use OpenAI-compatible API format
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
            # First, add the assistant message with tool_calls to messages
            assistant_message = {
                "role": "assistant",
                "content": response.get("content") or "",
                "tool_calls": response["tool_calls"],
            }
            messages.append(assistant_message)

            # Then process each tool call
            for tool_call in response["tool_calls"]:
                func = tool_call.get("function", {})
                name = func.get("name", "")
                args_raw = func.get("arguments", "{}")

                # Handle both string and dict arguments
                try:
                    if isinstance(args_raw, str):
                        args = json.loads(args_raw)
                    elif isinstance(args_raw, dict):
                        args = args_raw
                    else:
                        args = {}
                except json.JSONDecodeError:
                    args = {}

                # Execute tool
                result = execute_tool(name, args)

                # Log tool call
                tool_calls_log.append({"tool": name, "args": args, "result": result})

                # Append tool result to messages with proper tool_call_id
                tool_call_id = tool_call.get("id") or f"call_{len(tool_calls_log)}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result,
                    }
                )

            # Continue loop to get next LLM response
            continue

        # No tool calls - extract final answer
        answer = response.get("content") or ""
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

#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM to answer questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
    All debug output goes to stderr.
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


def load_env():
    """Load environment variables from .env.agent.secret."""
    env_file = Path(__file__).parent / ".env.agent.secret"
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        sys.exit(1)
    load_dotenv(env_file)


def call_llm(question: str) -> str:
    """Call the LLM API and return the answer."""
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
    # Ollama doesn't need auth, but OpenRouter does
    if api_key and api_key != "ollama":
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": question}],
        "stream": False,
    }

    print(f"Calling LLM API: {url}", file=sys.stderr)
    print(f"Model: {model}", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)

    response = requests.post(url, headers=headers, json=payload, timeout=120)

    if response.status_code != 200:
        print(f"Error: API returned status {response.status_code}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    answer = data["choices"][0]["message"]["content"]
    return answer


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print('Usage: uv run agent.py "Your question"', file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load environment
    load_env()

    # Call LLM
    answer = call_llm(question)

    # Format output
    result = {"answer": answer, "tool_calls": []}

    # Output JSON to stdout
    print(json.dumps(result))


if __name__ == "__main__":
    main()

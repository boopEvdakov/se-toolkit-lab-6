"""
Regression tests for agent.py

Tests verify that the agent:
1. Outputs valid JSON
2. Contains required fields (answer, tool_calls)
3. Responds within timeout
"""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> subprocess.CompletedProcess:
    """Run agent.py with a question and return the result."""
    # Get the project root directory
    project_root = Path(__file__).parent.parent

    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=project_root,
    )
    return result


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    result = run_agent("What is 2+2?")

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    output = result.stdout.strip()
    print(f"Agent output: {output}")

    data = json.loads(output)

    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check types
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be an array"

    # Check answer is not empty
    assert len(data["answer"]) > 0, "'answer' must not be empty"

    print("All checks passed!")


def test_agent_handles_different_questions():
    """Test that agent handles different types of questions."""
    questions = [
        "What does API stand for?",
        "Explain what a database is in one sentence.",
    ]

    for question in questions:
        result = run_agent(question)

        assert result.returncode == 0, f"Agent failed on '{question}': {result.stderr}"

        data = json.loads(result.stdout.strip())
        assert "answer" in data
        assert "tool_calls" in data
        assert len(data["answer"]) > 0

        print(f"✓ Question answered: {question}")


if __name__ == "__main__":
    print("Running test_agent_outputs_valid_json...")
    test_agent_outputs_valid_json()
    print()
    print("Running test_agent_handles_different_questions...")
    test_agent_handles_different_questions()
    print()
    print("All tests passed!")

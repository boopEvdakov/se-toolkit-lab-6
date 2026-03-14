"""
Regression tests for agent.py

Tests verify that the agent:
1. Outputs valid JSON
2. Contains required fields (answer, source, tool_calls)
3. Uses tools correctly
4. Responds within timeout
"""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> subprocess.CompletedProcess:
    """Run agent.py with a question and return the result."""
    project_root = Path(__file__).parent.parent

    result = subprocess.run(
        ["uv", "run", "agent.py", question],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=project_root,
    )
    return result


def parse_output(result: subprocess.CompletedProcess) -> dict:
    """Parse agent output as JSON."""
    # Find JSON in output (skip stderr that might be mixed in)
    for line in result.stdout.split("\n"):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    return json.loads(result.stdout.strip())


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with required fields."""
    result = run_agent("What is 2+2?")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert "source" in data, "Missing 'source' field in output"
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"

    # Check types
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert isinstance(data["source"], str), "'source' must be a string"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be an array"

    print("All checks passed!")


def test_agent_uses_read_file_tool():
    """Test that agent uses read_file tool for documentation questions."""
    result = run_agent("What is an API? Read wiki/api.md")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Check that tool_calls is not empty
    assert len(data["tool_calls"]) > 0, "Expected tool calls but got none"

    # Check that read_file was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "read_file" in tool_names, (
        f"Expected 'read_file' in tool_calls, got: {tool_names}"
    )

    # Check source field
    assert "wiki/api.md" in data["source"], (
        f"Expected wiki/api.md in source, got: {data['source']}"
    )

    print(f"✓ read_file tool used. Source: {data['source']}")


def test_agent_uses_list_files_tool():
    """Test that agent uses list_files tool for directory questions."""
    result = run_agent("List files in wiki directory")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Check that tool_calls is not empty
    assert len(data["tool_calls"]) > 0, "Expected tool calls but got none"

    # Check that list_files was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "list_files" in tool_names, (
        f"Expected 'list_files' in tool_calls, got: {tool_names}"
    )

    print(f"✓ list_files tool used. Tools: {tool_names}")


def test_agent_security_path_traversal():
    """Test that agent rejects path traversal attempts."""
    result = run_agent("Read ../../../etc/passwd")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Should have an error message about invalid path
    assert "Error" in data["answer"] or len(data["tool_calls"]) == 0, (
        "Agent should reject path traversal attempts"
    )

    print("✓ Path traversal blocked")


if __name__ == "__main__":
    print("Running test_agent_outputs_valid_json...")
    test_agent_outputs_valid_json()
    print()

    print("Running test_agent_uses_read_file_tool...")
    test_agent_uses_read_file_tool()
    print()

    print("Running test_agent_uses_list_files_tool...")
    test_agent_uses_list_files_tool()
    print()

    print("Running test_agent_security_path_traversal...")
    test_agent_security_path_traversal()
    print()

    print("All tests passed!")

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
    result = run_agent("What is in wiki/api.md? Read the file.")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Check that read_file was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "read_file" in tool_names, (
        f"Expected 'read_file' in tool_calls, got: {tool_names}"
    )

    # Check source field
    assert "wiki/api.md" in data.get("source", ""), (
        f"Expected wiki/api.md in source, got: {data.get('source', '')}"
    )

    print(f"✓ read_file tool used. Source: {data.get('source', '')}")


def test_agent_uses_list_files_tool():
    """Test that agent uses list_files tool for directory questions."""
    result = run_agent("List all files in the wiki directory")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

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

    # Tool should either reject the path or return an error result
    if len(data["tool_calls"]) > 0:
        # If tool was called, it should have an error result
        for call in data["tool_calls"]:
            if "Error" in call.get("result", ""):
                print("✓ Path traversal blocked with error")
                return
        # Or agent should mention error in answer
        if (
            "Error" in data.get("answer", "")
            or "not allowed" in data.get("answer", "").lower()
        ):
            print("✓ Path traversal blocked")
            return
        assert False, "Tool should return error for path traversal"
    else:
        # No tool calls - answer should mention error/restriction
        assert "Error" in data["answer"] or "not allowed" in data["answer"].lower(), (
            "Agent should reject path traversal attempts"
        )
        print("✓ Path traversal blocked")


def test_agent_uses_query_api_for_data():
    """Test that agent uses query_api for data questions."""
    result = run_agent("GET /items/ from the API")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Check that query_api was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "query_api" in tool_names, (
        f"Expected 'query_api' in tool_calls, got: {tool_names}"
    )

    print(f"✓ query_api tool used. Tools: {tool_names}")


def test_agent_uses_read_file_for_framework():
    """Test that agent uses read_file for framework questions."""
    result = run_agent("What framework does backend use? Check backend/app/main.py")

    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    data = parse_output(result)

    # Check that read_file was used
    tool_names = [call.get("tool") for call in data["tool_calls"]]
    assert "read_file" in tool_names, (
        f"Expected 'read_file' in tool_calls, got: {tool_names}"
    )

    print(f"✓ read_file tool used. Source: {data.get('source', '')}")


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

    print("Running test_agent_uses_query_api_for_data...")
    test_agent_uses_query_api_for_data()
    print()

    print("Running test_agent_uses_read_file_for_framework...")
    test_agent_uses_read_file_for_framework()
    print()

    print("All tests passed!")

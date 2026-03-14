# Agent Architecture

## Overview

This project implements an AI agent (`agent.py`) that answers questions using a Large Language Model (LLM) with **tools**. The agent can read files and list directories to find answers in the project documentation.

## Architecture

```
User Question → LLM (with tool schemas) → tool_calls?
    ↓ yes                                  ↓ no
Execute tools → Append results        Extract answer
    ↓
Send back to LLM
    ↓
Repeat (max 10 iterations) → Final JSON output
```

## Components

### 1. Agent CLI (`agent.py`)

Main entry point with agentic loop:

- Parse command-line arguments
- Load environment configuration
- Run agentic loop with tools
- Format and output JSON response

### 2. Tools

#### `read_file(path: str)`

Read contents of a file from the project repository.

**Parameters:**

- `path` — relative path from project root (e.g., `wiki/git.md`)

**Returns:** File contents or error message

#### `list_files(path: str)`

List files and directories at a given path.

**Parameters:**

- `path` — relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing or error message

### 3. Security

**Path traversal protection:**

- Reject absolute paths
- Reject paths containing `..`
- Validate resolved path is within project root

```python
def safe_path(path: str) -> Path:
    project_root = Path(__file__).parent.resolve()
    if os.path.isabs(path) or ".." in path:
        raise ValueError("Invalid path")
    full_path = (project_root / path).resolve()
    if not str(full_path).startswith(str(project_root)):
        raise ValueError("Path outside project")
    return full_path
```

### 4. Environment Configuration (`.env.agent.secret`)

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key (or "ollama" for local) | `ollama` |
| `LLM_API_BASE` | LLM API endpoint | `http://10.93.25.238:8080/v1` |
| `LLM_MODEL` | Model name | `qwen2.5:3b` |

### 5. LLM Backend (Ollama on VM)

**Provider:** Ollama (self-hosted)  
**Model:** Qwen 2.5 3B  
**Endpoint:** `http://10.93.25.238:8080/v1`

## Usage

```bash
# Run the agent with a question
uv run agent.py "How do you resolve a merge conflict?"

# Output (JSON to stdout):
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Output Format

```json
{
  "answer": "The LLM's response text",
  "source": "wiki/filename.md#section-anchor",
  "tool_calls": [
    {
      "tool": "tool_name",
      "args": {"param": "value"},
      "result": "tool output"
    }
  ]
}
```

**Note:** All debug/logging output goes to stderr, only the JSON result goes to stdout.

## Agentic Loop

1. **Initialize** conversation with system prompt + user question
2. **Call LLM** with tool schemas
3. **Check response:**
   - If `tool_calls` → execute tools, append results, go to step 2
   - If text answer → extract answer + source, output JSON, exit
4. **Max iterations:** 10 tool calls

## System Prompt

```
You are a helpful documentation assistant. You have access to tools that let you 
read files and list directories in a project repository.

When asked a question about the project:
1. Use `list_files` to explore the directory structure if needed
2. Use `read_file` to read relevant documentation files
3. Find the answer in the files you read
4. Include the source reference (file path and section anchor if applicable)

Always be specific about which file contains the answer. Format section references 
as: `wiki/filename.md#section-anchor`

If you cannot find the answer after exploring the available files, say so honestly.
```

## Tool Schemas (OpenAI Function Calling)

```json
[
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
            "description": "Relative path from project root"
          }
        },
        "required": ["path"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "list_files",
      "description": "List files and directories at a given path",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "Relative directory path from project root"
          }
        },
        "required": ["path"]
      }
    }
  }
]
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI script with agentic loop |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `AGENT.md` | This documentation |
| `tests/test_agent.py` | Regression tests |

## Testing

Run the test suite:

```bash
uv run pytest tests/test_agent.py -v
```

Tests:

- `test_agent_outputs_valid_json` — verifies JSON structure
- `test_agent_handles_different_questions` — tests multiple questions
- `test_agent_uses_read_file_tool` — verifies read_file tool usage
- `test_agent_uses_list_files_tool` — verifies list_files tool usage

## Deployment

The LLM (Ollama) runs on the VM:

```bash
# On VM: start Ollama
docker run -d --name ollama --restart unless-stopped \
  -p 8080:11434 -v ollama:/root/.ollama ollama/ollama:latest

# Pull model
docker exec ollama ollama pull qwen2.5:3b
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing config, API failure, etc.) |

## Limitations

- Maximum 10 tool calls per question
- Ollama qwen2.5:3b may be slow for multi-turn conversations (5-30 seconds per iteration)
- Tool results are truncated in logs for readability

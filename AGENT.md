# Agent Architecture

## Overview

This project implements an AI agent (`agent.py`) that answers questions using a Large Language Model (LLM) with **tools**. The agent can read files, list directories, and query the backend API to find answers in project documentation, source code, and live data.

## Architecture

```
User Question → LLM (with 3 tool schemas) → tool_calls?
    ↓ yes                                   ↓ no
Execute tools → Append results         Extract answer
  - read_file
  - list_files  
  - query_api
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
- Run agentic loop with 3 tools
- Format and output JSON response

### 2. Tools

#### `read_file(path: str)`

Read contents of a file from the project repository.

**Parameters:** `path` — relative path from project root  
**Returns:** File contents or error message

#### `list_files(path: str)`

List files and directories at a given path.

**Parameters:** `path` — relative directory path  
**Returns:** Newline-separated listing or error message

#### `query_api(method: str, path: str, body: str = None)`

Call the backend API with authentication.

**Parameters:**

- `method` — HTTP method (GET, POST, etc.)
- `path` — API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` — Optional JSON request body for POST/PUT

**Returns:** JSON string with `status_code` and `body`, or error message

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret` via `X-API-Key` header

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

### 4. Environment Configuration

**`.env.agent.secret`** (LLM configuration):

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | LLM provider API key | `ollama` |
| `LLM_API_BASE` | LLM API endpoint | `http://10.93.25.238:8080/v1` |
| `LLM_MODEL` | Model name | `qwen2.5:3b` |

**`.env.docker.secret`** (Backend API configuration):

| Variable | Description | Example |
|----------|-------------|---------|
| `LMS_API_KEY` | Backend API key for query_api | `my-secret-api-key` |
| `AGENT_API_BASE_URL` | Backend base URL | `http://localhost:42002` |

### 5. LLM Backend (Ollama on VM)

**Provider:** Ollama (self-hosted)  
**Model:** Qwen 2.5 3B  
**Endpoint:** `http://10.93.25.238:8080/v1`

## Usage

```bash
# Run the agent with a question
uv run agent.py "How many items are in the database?"

# Output (JSON to stdout):
{
  "answer": "There are 120 items in the database.",
  "source": "",
  "tool_calls": [
    {"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "{\"status_code\": 200, ...}"}
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

**Note:** `source` is optional — system questions may not have a wiki source.

## Agentic Loop

1. **Initialize** conversation with system prompt + user question
2. **Call LLM** with 3 tool schemas
3. **Check response:**
   - If `tool_calls` → execute tools, append results as `tool` role messages, go to step 2
   - If text answer → extract answer + source, output JSON, exit
4. **Max iterations:** 10 tool calls

## System Prompt Strategy

The system prompt instructs the LLM to:

1. Use `list_files` for directory exploration
2. Use `read_file` for wiki and source code questions
3. Use `query_api` for live data, status codes, API behavior
4. Include source references for file-based answers

**Key distinction:** Wiki/source questions → `read_file`; Live data → `query_api`

## Tool Schemas (OpenAI Function Calling)

Three tools registered with the LLM:

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
          "path": {"type": "string", "description": "Relative path from project root"}
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
          "path": {"type": "string", "description": "Relative directory path"}
        },
        "required": ["path"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "query_api",
      "description": "Call the backend API to query data, check status codes, or test endpoints",
      "parameters": {
        "type": "object",
        "properties": {
          "method": {"type": "string", "description": "HTTP method (GET, POST, etc.)"},
          "path": {"type": "string", "description": "API path"},
          "body": {"type": "string", "description": "Optional JSON request body"}
        },
        "required": ["method", "path"]
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
| `.env.docker.secret` | Backend API configuration (gitignored) |
| `plans/task-1.md` | Task 1: LLM agent |
| `plans/task-2.md` | Task 2: Documentation agent |
| `plans/task-3.md` | Task 3: System agent |
| `AGENT.md` | This documentation |
| `tests/test_agent.py` | Regression tests |

## Testing

Run the test suite:

```bash
uv run pytest tests/test_agent.py -v
```

Tests (6 total):

- `test_agent_outputs_valid_json` — verifies JSON structure
- `test_agent_uses_read_file_tool` — wiki documentation questions
- `test_agent_uses_list_files_tool` — directory listing questions
- `test_agent_security_path_traversal` — path traversal protection
- `test_agent_uses_query_api_for_data` — API data queries
- `test_agent_uses_read_file_for_framework` — source code questions

## Benchmark Evaluation

Run the local benchmark:

```bash
uv run run_eval.py
```

The benchmark tests 10 questions across categories:

- Wiki lookup (questions 0-1)
- Source code analysis (questions 2-3)
- API data queries (questions 4-5)
- Error diagnosis (questions 6-7)
- System reasoning (questions 8-9, LLM judge)

## Deployment

The LLM (Ollama) runs on the VM:

```bash
# On VM: start Ollama
docker run -d --name ollama --restart unless-stopped \
  -p 8080:11434 -v ollama:/root/.ollama ollama/ollama:latest

# Pull model
docker exec ollama ollama pull qwen2.5:3b
```

The backend runs separately via Docker Compose on port 42002.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (missing config, API failure, etc.) |

## Limitations

- Maximum 10 tool calls per question
- Ollama qwen2.5:3b may be slow for multi-turn conversations (5-30 seconds per iteration)
- Tool results are truncated in logs for readability
- `query_api` requires `LMS_API_KEY` to be configured

## Lessons Learned

1. **Tool descriptions matter:** The LLM relies on tool descriptions to decide which tool to use. Vague descriptions lead to wrong tool selection.

2. **Source field is optional:** Not all questions have a wiki source. System queries (via `query_api`) don't have a file reference.

3. **Two API keys:** `LLM_API_KEY` authenticates with the LLM provider; `LMS_API_KEY` authenticates with the backend API. Don't mix them up.

4. **Environment variables:** The autochecker injects its own values. Never hardcode API keys, base URLs, or model names.

5. **Error handling:** The agent must gracefully handle API errors, file not found, and path traversal attempts.

6. **Iteration limit:** The 10-iteration limit prevents infinite loops but may cut off complex multi-step reasoning.

7. **Content truncation:** Large files get truncated in tool results. The LLM may miss information if the file is too long.

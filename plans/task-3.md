# Task 3: The System Agent - Implementation Plan

## Overview

Extend the Task 2 agent with a new `query_api` tool that can call the deployed backend API. The agent will now answer both static questions (wiki, source code) and dynamic questions (database queries, API status codes).

## Architecture Changes

### New Tool: `query_api`

**Purpose:** Call the deployed backend API with authentication.

**Parameters:**
- `method` (string) — HTTP method (GET, POST, etc.)
- `path` (string) — API path (e.g., `/items/`)
- `body` (string, optional) — JSON request body for POST/PUT

**Returns:** JSON string with `status_code` and `body`

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret`

### Environment Variables

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api (default: `http://localhost:42002`) | Optional |

### Updated Agentic Loop

```
Question → LLM (with 3 tools) → tool_calls?
    ↓ yes                       ↓ no
Execute:                    Extract answer
  - read_file
  - list_files
  - query_api
    ↓
Append results → Repeat (max 10 iterations)
```

## Tool Schema for `query_api`

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Call the backend API to query data or check status codes",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, etc.)"
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

## Implementation Steps

1. **Add `query_api` function:**
   - Read `LMS_API_KEY` from `.env.docker.secret`
   - Read `AGENT_API_BASE_URL` from environment (default: `http://localhost:42002`)
   - Make HTTP request with API key in header
   - Return JSON response with status_code and body

2. **Update tool schemas:**
   - Add `query_api` to TOOLS list
   - Add to TOOL_FUNCTIONS mapping

3. **Update system prompt:**
   - Explain when to use each tool:
     - `list_files` / `read_file` — wiki and source code questions
     - `query_api` — live data, status codes, API behavior

4. **Update output format:**
   - `source` field is now optional (system questions may not have wiki source)

5. **Run benchmark:**
   - Execute `uv run run_eval.py`
   - Fix failing questions iteratively

## Benchmark Strategy

### Question Categories

| # | Type | Tools Required |
|---|------|----------------|
| 0-1 | Wiki lookup | `read_file` |
| 2-3 | Source code | `read_file`, `list_files` |
| 4-5 | API data queries | `query_api` |
| 6-7 | API error diagnosis | `query_api`, `read_file` |
| 8-9 | System reasoning | `read_file` (LLM judge) |

### Debugging Approach

1. Run `run_eval.py` to see initial score
2. For each failure:
   - Check if correct tool was called
   - If tool not called → improve system prompt
   - If tool called with wrong args → improve schema description
   - If tool returns error → fix implementation
3. Re-run until all 10 pass

## Files to Update

- `plans/task-3.md` — this plan
- `agent.py` — add `query_api` tool and update prompt
- `.env.agent.secret` — ensure all LLM vars present
- `.env.docker.secret` — ensure `LMS_API_KEY` present
- `AGENT.md` — document `query_api` and lessons learned
- `tests/test_agent.py` — add 2 system agent tests

## Testing

New tests:
1. `test_agent_uses_query_api_for_data` — "How many items in database?" → expects `query_api`
2. `test_agent_uses_read_file_for_framework` — "What framework does backend use?" → expects `read_file`

## Success Criteria

- All 10 `run_eval.py` questions pass
- Agent uses correct tools for each question type
- Environment variables properly loaded
- `query_api` authenticates with `LMS_API_KEY`

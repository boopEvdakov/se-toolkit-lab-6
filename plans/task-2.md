# Task 2: The Documentation Agent - Implementation Plan

## Overview

Transform the Task 1 CLI into an **agent** with tools. The agent can now read project files and list directories to answer questions based on actual documentation.

## Architecture

### Components

1. **Tools**
   - `read_file(path: str)` — read file contents
   - `list_files(path: str)` — list directory contents

2. **Agentic Loop**
   ```
   Question → LLM (with tool schemas) → tool_calls?
       ↓ yes                              ↓ no
   Execute tools → Append results    Extract answer
       ↓
   Send back to LLM
       ↓
   Repeat (max 10 iterations)
   ```

3. **Output Format**
   ```json
   {
     "answer": "...",
     "source": "wiki/git-workflow.md#section",
     "tool_calls": [
       {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
       {"tool": "read_file", "args": {"path": "wiki/file.md"}, "result": "..."}
     ]
   }
   ```

## Tool Schemas (OpenAI Function Calling)

### `read_file`
```python
{
    "name": "read_file",
    "description": "Read contents of a file from the project",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative path from project root"}
        },
        "required": ["path"]
    }
}
```

### `list_files`
```python
{
    "name": "list_files",
    "description": "List files and directories at a given path",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Relative directory path from project root"}
        },
        "required": ["path"]
    }
}
```

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to discover wiki directory structure
2. Use `read_file` to read relevant documentation files
3. Extract the answer and identify the source (file path + section anchor)
4. Format the final answer with the source reference

## Security

**Path traversal protection:**
- Resolve paths using `Path.resolve()`
- Check that resolved path starts with project root
- Reject any path containing `..` or absolute paths outside project

```python
def safe_path(path: str) -> Path:
    project_root = Path(__file__).parent
    full_path = (project_root / path).resolve()
    if not str(full_path).startswith(str(project_root)):
        raise ValueError("Path traversal detected")
    return full_path
```

## Implementation Steps

1. **Define tools** as functions with schemas
2. **Update LLM call** to include tool definitions
3. **Implement agentic loop**:
   - Parse LLM response for `tool_calls`
   - Execute tools
   - Append results as `tool` role messages
   - Repeat until answer or max iterations
4. **Extract source** from tool calls (last `read_file` path + section)
5. **Format output** JSON with all required fields

## Files to Update

- `plans/task-2.md` — this plan
- `agent.py` — add tools and agentic loop
- `AGENT.md` — document tools and loop
- `tests/test_agent.py` — add 2 tool-calling tests

## Testing

New tests:
1. `test_agent_uses_read_file_tool` — ask about merge conflicts, verify `read_file` in tool_calls
2. `test_agent_uses_list_files_tool` — ask about wiki files, verify `list_files` in tool_calls

## LLM Configuration

Same as Task 1 (Ollama on VM):
- Model: `qwen2.5:3b`
- Endpoint: `http://10.93.25.238:8080/v1`

Note: Ollama's OpenAI-compatible API supports function calling.

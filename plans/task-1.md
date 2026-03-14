# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider

**Provider:** Ollama (self-hosted on VM)  
**Model:** `qwen2.5:3b`  
**API Endpoint:** `http://10.93.25.238:8080/v1/chat/completions`

**Why Ollama:**

- Free and unlimited (no rate limits)
- No API key required
- Runs locally on the VM
- OpenAI-compatible API
- Full privacy

## Architecture

### Components

1. **Environment Configuration** (`.env.agent.secret`)
   - `LLM_API_KEY` — "ollama" (placeholder, no auth needed)
   - `LLM_API_BASE` — Ollama API URL on VM
   - `LLM_MODEL` — model name (qwen2.5:3b)

2. **Agent CLI** (`agent.py`)
   - Parse command-line argument (user question)
   - Load environment variables
   - Call LLM API via HTTP POST
   - Parse response and format JSON output

3. **LLM Backend** (Ollama on VM)
   - Docker container running on VM
   - Port 8080 exposed
   - Qwen 2.5 3B model downloaded

### Data Flow

```
User question (CLI arg) 
    → agent.py 
    → HTTP POST to Ollama API (VM)
    → LLM response 
    → JSON formatting 
    → stdout
```

## API Request Structure

```python
import requests

response = requests.post(
    f"{LLM_API_BASE}/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": user_question}],
        "stream": False
    }
)
```

## Response Format

**Output (stdout):**

```json
{"answer": "<LLM response text>", "tool_calls": []}
```

**Error Handling:**

- Log errors to stderr
- Exit code 0 on success, non-zero on failure
- Timeout: 120 seconds

## Testing

1. Test file: `tests/test_agent.py`
2. Tests:
   - `test_agent_outputs_valid_json` — verifies JSON structure
   - `test_agent_handles_different_questions` — tests multiple questions
3. Run: `uv run pytest tests/test_agent.py -v`

## Files Created

- `plans/task-1.md` — this plan
- `agent.py` — main CLI script
- `.env.agent.secret` — LLM configuration (gitignored)
- `AGENT.md` — documentation
- `tests/test_agent.py` — regression tests

## VM Setup (Ollama)

```bash
# On VM: start Ollama
docker run -d --name ollama --restart unless-stopped \
  -p 8080:11434 -v ollama:/root/.ollama ollama/ollama:latest

# Pull model
docker exec ollama ollama pull qwen2.5:3b
```

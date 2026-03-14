# Agent Architecture

## Overview

This project implements an AI agent (`agent.py`) that answers questions using a Large Language Model (LLM). The agent is designed to be extensible — in future tasks it will gain tools and an agentic loop.

## Architecture

```
User Question (CLI) → agent.py → LLM API → JSON Response
```

## Components

### 1. Agent CLI (`agent.py`)

The main entry point. Responsibilities:

- Parse command-line arguments
- Load environment configuration
- Call the LLM API
- Format and output JSON response

### 2. Environment Configuration (`.env.agent.secret`)

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key (or "ollama" for local) | `ollama` |
| `LLM_API_BASE` | LLM API endpoint | `http://10.93.25.238:8080/v1` |
| `LLM_MODEL` | Model name | `qwen2.5:3b` |

### 3. LLM Backend (Ollama on VM)

We use **Ollama** running on the VM with the **Qwen 2.5 3B** model:

- No API key required
- No rate limits
- Runs locally on the VM
- OpenAI-compatible API

## Usage

```bash
# Run the agent with a question
uv run agent.py "What does REST stand for?"

# Output (JSON to stdout):
{"answer": "REST stands for Representational State Transfer...", "tool_calls": []}
```

## Output Format

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "The LLM's response text",
  "tool_calls": []
}
```

**Note:** All debug/logging output goes to stderr, only the JSON result goes to stdout.

## LLM Provider

**Provider:** Ollama (self-hosted)  
**Model:** Qwen 2.5 3B  
**Endpoint:** `http://10.93.25.238:8080/v1`

### Why Ollama?

- Free and unlimited
- No API key required
- No rate limits
- Full privacy (runs on your VM)
- OpenAI-compatible API

### Alternative Providers

The agent supports any OpenAI-compatible API. To switch providers, edit `.env.agent.secret`:

**OpenRouter:**

```bash
LLM_API_KEY=sk-or-v1-...
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main CLI script |
| `.env.agent.secret` | LLM configuration (gitignored) |
| `plans/task-1.md` | Implementation plan |
| `AGENT.md` | This documentation |
| `tests/test_agent.py` | Regression tests |

## Testing

Run the test suite:

```bash
uv run pytest tests/test_agent.py -v
```

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

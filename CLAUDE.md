# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a LiteLLM proxy deployment with a custom web search proxy layer. The architecture consists of:

1. **LiteLLM Proxy** (port 4000) - Main proxy server that provides unified API access to multiple LLM providers
2. **Web Search Proxy** (port 4001) - Custom FastAPI service that intercepts requests and provides RAG-style web search

## Running the Services

### Docker Deployment (Recommended)

The project uses Docker Compose for deployment. Custom Dockerfiles are used to ensure amd64 compatibility (the official LiteLLM image is arm64-only).

```bash
# Start all services (LiteLLM, Web Search Proxy)
make up
# or: docker compose up -d

# View logs
make logs

# Stop services
make down

# Rebuild after changes
make build
```

**Services:**
- `litellm` - LiteLLM proxy on port 4000 (built from `Dockerfile.litellm`)
- `websearch-proxy` - Web search proxy on port 4001 (built from `Dockerfile.websearch`)

**Note:** Uses external Redis on `localhost:6379` (not containerized) via `host.docker.internal`.

**Available make targets:**
- `make build` - Build Docker images
- `make up` - Start all services
- `make down` - Stop all services
- `make restart` - Restart services
- `make logs` - View all logs
- `make litellm-logs` - View LiteLLM logs only
- `make websearch-logs` - View websearch proxy logs only
- `make shell-litellm` - Open shell in LiteLLM container
- `make shell-websearch` - Open shell in websearch proxy container

### Local Development

For local development without Docker:

#### Start LiteLLM Proxy
```bash
source litellm-env/bin/activate
litellm --config config.yaml --port 4000
```

#### Start Web Search Proxy
```bash
source litellm-env/bin/activate
python websearch_proxy.py
```

#### Python Environment
The project uses a virtual environment at `litellm-env/` with Python 3.12. Always activate it before running commands.

### Docker Image Notes

**Why custom Dockerfiles?**
- Official `ghcr.io/berriai/litellm:latest` only provides arm64 images
- We're on amd64 (x86_64), so we build custom images from source
- `Dockerfile.litellm` installs `litellm[proxy]>=1.83.0` from PyPI
- Current LiteLLM version: **1.83.14**

## Architecture

### Web Search Proxy (`websearch_proxy.py`)

The custom proxy implements proactive web search without requiring tool-calling from the model:

1. **Intent Detection**: Analyzes the last user message for search intent using:
   - Explicit triggers: "search", "look up", "find me", "find the", "look for"
   - Recency triggers: "latest", "recent", "current", "today", "news"
   - Filters out system reminders and long messages (>500 chars)

2. **Search Execution**: When intent is detected:
   - Queries Serper API with extracted search query
   - Formats results (answer box + top 6 organic results)

3. **Context Injection**: Injects search results into the system prompt before calling the model

4. **Response Processing**:
   - Strips `thinking` blocks from responses (non-Anthropic models don't emit them)
   - Converts non-streaming responses to proper SSE format when streaming is requested
   - Forwards non-search requests directly to LiteLLM

### LiteLLM Configuration (`config.yaml`)

**Model List**: Maps model names to provider configurations:
- Local models via Ollama (`ollama_chat/*`) on `localhost:11434`
- Remote models via various APIs
- Model-level flags: `supports_web_search`, `supports_vision`

**Settings**:
- Redis caching enabled (`localhost:6379`)
- Serper for web search
- `websearch_interception` callback enabled for `ollama_chat` provider

## Model Configurations

- **glm-4.7**: Local Ollama model with web search support
- **gemma4-e4b**: Local Ollama model with vision support
- **qwen-3.5**: Local Ollama model with web search support
- **bitnet-3b**: OpenAI-compatible API on `localhost:8080`

## Key Implementation Details

### Message Flow for Search Queries
1. Client sends request to port 4001
2. `extract_search_query()` detects search intent
3. `do_serper_search()` fetches results
4. Search results injected into system prompt
5. Request forwarded to LiteLLM (port 4000)
6. Response processed (thinking blocks removed, SSE format applied)
7. Response returned to client

### Non-Search Queries
- Direct passthrough to LiteLLM with minimal processing
- `betas` parameter removed
- Anthropic web search tools stripped from request

## Development Notes

- The proxy handles both streaming and non-streaming modes
- Anthropic SSE format is emulated for non-Anthropic models
- `drop_params: true` in config allows flexibility with model-specific parameters
- Redis cache key namespace: `litellm.caching.caching`

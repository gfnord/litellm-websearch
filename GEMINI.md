# GEMINI.md

This file provides foundational mandates and guidance for Gemini CLI when working in this repository.

## Project Context

This project is a LiteLLM-based proxy stack with a custom FastAPI layer (`websearch_proxy.py`) that implements proactive web search (RAG) by intercepting requests and injecting context from the Serper API.

## Core Mandates

- **Architecture Integrity**: Maintain the separation between the Web Search Proxy (port 4001) and LiteLLM Proxy (port 4000).
- **Environment Safety**: Never commit `.env` files. Use `.env.example` as a template.
- **AMD64 Compatibility**: Always use the custom Dockerfiles (`Dockerfile.litellm`, `Dockerfile.websearch`) for building images, as they ensure compatibility with amd64 architecture.
- **Docker Workflow**: Use `make` targets for orchestration. Modern systems use `docker compose` (v2), which is now reflected in the `Makefile`.

## Development Workflows

### Testing Changes
Before finalizing changes, verify them using Docker build:
```bash
make build
```

To test the proxy functionality locally (requires Redis and Ollama):
1. Start services: `make up`
2. Check logs: `make logs`
3. Send a test request to port 4001 (see README.md for examples).

### Coding Standards
- **Python**: Use Python 3.12. Follow PEP 8 styles.
- **FastAPI**: The web search proxy uses FastAPI. Ensure all new endpoints are properly typed and documented.
- **LiteLLM Config**: `config.yaml` is the source of truth for model configurations. When adding models, ensure they have proper `model_info` flags (`supports_web_search`, `supports_vision`).

## Key Implementation Details

### Web Search Logic (`websearch_proxy.py`)
- **Intent Detection**: Logic in `extract_search_query` uses specific triggers and filters out system/internal messages.
- **Context Injection**: Search results are injected into the *system prompt* to keep it model-agnostic.
- **Response Processing**: The proxy handles SSE streaming and non-streaming responses, ensuring compatibility with Anthropic-style clients.

## Maintenance
- **LiteLLM Updates**: When updating LiteLLM, update both `Dockerfile.litellm` and `CLAUDE.md` / `GEMINI.md`.
- **Current Version**: 1.83.14

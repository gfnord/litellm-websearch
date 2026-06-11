# LiteLLM Web Search Proxy Documentation

Welcome to the documentation for the LiteLLM Proxy with Web Search stack. This repository houses a Dockerized LiteLLM deployment paired with a custom web search proxy layer that enables proactive search-augmented generation (RAG) on arbitrary LLMs.

## Documentation Index

Explore the different sections of the documentation:

1. **[System Architecture](architecture.md)**
   - High-level overview of the components.
   - Flow of user requests through the proxy layers.
   - Internal/external networking, ports, and caching architecture.
   - Mermaid sequence and architecture diagrams.

2. **[Web Search Proxy Deep Dive](websearch_proxy.md)**
   - Analysis of `websearch_proxy.py`.
   - Intent detection triggers and heuristic exclusions.
   - Serper API integration details.
   - Request enrichment (System Prompt injection).
   - Response formatting and custom SSE (Server-Sent Events) streaming translation.

3. **[Configuration & Models](configuration.md)**
   - Details of `config.yaml`.
   - Pre-configured models (local Ollama models, remote Z.AI models).
   - Redis caching parameters.
   - Required environment variables.

4. **[Development & Deployment Guide](development_and_deployment.md)**
   - Setting up local development (virtual environments).
   - Docker Compose setup and multi-container orchestration.
   - Dockerfile configurations for AMD64 compatibility.
   - Detailed review of available Makefile targets.

# LiteLLM Proxy with Web Search

A Dockerized LiteLLM deployment with a custom web search proxy layer that provides RAG-style proactive search capabilities.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Clients       │────▶│ Web Search Proxy │────▶│  LiteLLM Proxy  │
│  (port 4001)    │     │   (FastAPI)      │     │   (port 4000)   │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                  │                        │
                                  ▼                        ▼
                           ┌──────────┐            ┌──────────┐
                           │  Serper  │            │  Redis   │
                           │   API    │            │ (cache)  │
                           └──────────┘            └──────────┘
```

## Features

- **Unified LLM API**: Single interface for multiple LLM providers (Ollama, OpenAI-compatible, Anthropic, etc.)
- **Proactive Web Search**: Automatically detects search intent and injects results into context
- **Streaming Support**: Full SSE streaming support with Anthropic-compatible format
- **Redis Caching**: Built-in response caching for improved performance
- **Docker Deployment**: Fully containerized with Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama running on `localhost:11434` (for local models)
- Redis running on `localhost:6379` (or use the included container)
- Serper API key from https://serper.dev/

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and set your `SERPER_API_KEY`

3. Configure models in `config.yaml` as needed

### Running

```bash
# Start all services
make up

# View logs
make logs

# Stop services
make down
```

Services will be available at:
- **LiteLLM Proxy**: http://localhost:4000
- **Web Search Proxy**: http://localhost:4001

## Usage

### Making Requests

Send requests to the web search proxy (port 4001):

```bash
curl -X POST http://localhost:4001/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-123345sdf" \
  -d '{
    "model": "glm-4.7",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Search for the latest Python release notes"}
    ]
  }'
```

### Search Intent Detection

The proxy automatically detects search intent when messages contain:
- **Explicit triggers**: "search", "look up", "find me", "find the", "look for"
- **Recency triggers**: "latest", "recent", "current", "today", "news"

When detected, it:
1. Extracts the search query
2. Fetches results from Serper
3. Injects results into the system prompt
4. Sends the enriched request to the model

## Configuration

### Models

Edit `config.yaml` to add/modify models:

```yaml
model_list:
  - model_name: my-model
    litellm_params:
      model: provider/model-name
      api_base: https://api.example.com
      api_key: env_var.API_KEY
    model_info:
      supports_web_search: true
      supports_vision: false
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERPER_API_KEY` | Serper API key for web search | - |
| `LITELLM_MASTER_KEY` | LiteLLM master key | `sk-123345sdf` |
| `LITELLM_URL` | LiteLLM service URL | `http://litellm:4000` |
| `PORT` | Web search proxy port | `4001` |

## Development

### Local Development

For development without Docker:

```bash
# Activate virtual environment
source litellm-env/bin/activate

# Start LiteLLM
litellm --config config.yaml --port 4000

# Start web search proxy (in another terminal)
python websearch_proxy.py
```

### Building Images

```bash
make build
```

### Available Make Targets

| Target | Description |
|--------|-------------|
| `make build` | Build Docker images |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make restart` | Restart services |
| `make logs` | View all logs |
| `make litellm-logs` | View LiteLLM logs only |
| `make websearch-logs` | View websearch proxy logs only |
| `make shell-litellm` | Open shell in LiteLLM container |
| `make shell-websearch` | Open shell in websearch proxy container |

## Project Structure

```
.
├── config.yaml              # LiteLLM configuration
├── websearch_proxy.py       # Web search proxy implementation
├── docker-compose.yml       # Docker orchestration
├── Dockerfile.litellm       # LiteLLM image build
├── Dockerfile.websearch     # Websearch proxy image build
├── requirements-litellm.txt # LiteLLM dependencies
├── requirements-websearch.txt # Websearch proxy dependencies
├── Makefile                 # Convenience commands
├── .env.example             # Environment template
└── litellm-env/            # Python virtual environment
```

## License

MIT

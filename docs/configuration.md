# Configuration & Models

This page explains how to configure the LiteLLM proxy, define models in `config.yaml`, set up Redis caching, and configure environment variables.

---

## 1. LiteLLM Configuration (`config.yaml`)

The primary source of truth for routing, fallback limits, caching settings, and model providers is [config.yaml](file:///home/gustavo/GIT/gfnord/litellm-websearch/config.yaml).

### LiteLLM Global Settings
- **`drop_params: true`**: Instructs LiteLLM to drop unsupported parameters when sending requests to specific backends (e.g., if Anthropic-specific request parameters are sent to an Ollama model, they are safely stripped).
- **`cache: true`**: Enables response caching.
- **`cache_params`**:
  - `type`: `redis`
  - `host`: `redis` (resolves to the `litellm-redis` container)
  - `port`: `6379`
  - `namespace`: `"litellm.caching.caching"`

---

## 2. Configured Models

The model registry lists local Ollama-served models and remote Z.AI APIs.

| Model Name | Provider Backend | Target Model | Max Tokens | Web Search Supported |
|---|---|---|---|---|
| `glm-4.7` | `anthropic` via Z.AI | `anthropic/glm-4.7` | Standard | ✅ (via proxy) |
| `glm-4.7-zai` | `anthropic` via Z.AI | `anthropic/glm-4.7` | Standard | ❌ |
| `glm-5.1` | `anthropic` via Z.AI | `anthropic/glm-5.1` | Standard | ❌ |
| `glm-5-turbo` | `anthropic` via Z.AI | `anthropic/glm-5-turbo`| Standard | ❌ |
| `glm-4.5-air` | `anthropic` via Z.AI | `anthropic/glm-4.5-air`| Standard | ❌ |
| `claude-opus-4-5-20251101` | `ollama_chat` | `qwen3:8b` | 32,768 | ✅ (via proxy) |
| `claude-haiku-4-5-20251001`| `ollama_chat` | `qwen3:8b` | 32,768 | ✅ (via proxy) |
| `claude-opus-4-6` | `ollama_chat` | `qwen3:8b` | 32,768 | ✅ (via proxy) |
| `qwen-3` | `ollama_chat` | `qwen3:8b` | 32,768 | ✅ (via proxy) |
| `qwen-3.5` | `ollama_chat` | `qwen3.5:9b` | 32,768 | ✅ (via proxy) |
| `dolphin3` | `ollama_chat` | `dolphin3:8b` | 32,768 | ✅ (via proxy) |

### Adding a New Model
To add a model, append an entry to `model_list` in `config.yaml`:
```yaml
  - model_name: custom-model-name
    litellm_params:
      model: provider/model-identifier
      api_base: http://host.docker.internal:port  # If hosted locally
      api_key: os.environ/ENV_VAR_NAME           # Optional API Key loading
      max_tokens: 4096
    model_info:
      supports_web_search: true
```

---

## 3. Environment Variables

Create a `.env` file in the project root by duplicating `.env.example`. 

> [!WARNING]
> Never commit your `.env` file containing API keys. Ensure it remains in `.gitignore`.

| Environment Variable | Required | Description | Default / Example |
|---|---|---|---|
| `SERPER_API_KEY` | **Yes** (for search) | API key obtained from [serper.dev](https://serper.dev/) for Google Search. | `your_serper_key_here` |
| `ZAI_API_KEY` | Optional | API key for Z.AI Hosted models (`glm-4.7`, `glm-5.1`, etc.). | `your_zai_key_here` |
| `LITELLM_MASTER_KEY` | Optional | Master authorization token to talk to the LiteLLM container. | `sk-123345sdf` |
| `LITELLM_URL` | Optional | Address used by the websearch proxy to communicate with LiteLLM. | `http://litellm:4000` |
| `PORT` | Optional | Exposed port for the Web Search Proxy container. | `4001` |

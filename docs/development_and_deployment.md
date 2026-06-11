# Development & Deployment Guide

This guide covers building, running, testing, and debugging the LiteLLM Proxy with Web Search stack, both inside Docker containers and directly in a local virtual environment.

---

## 1. Docker Deployment (Recommended)

Docker Compose coordinates the LiteLLM proxy, the custom web search proxy, and Redis caching.

### Quick Start Commands
```bash
# 1. Build the custom containers (essential for AMD64 architectures)
make build

# 2. Start the services in detached mode
make up

# 3. Stream service logs to verify execution
make logs

# 4. Tear down the stack and remove network volumes
make down
```

### CPU Architecture Compatibility Note
The official LiteLLM Docker images (`ghcr.io/berriai/litellm`) are built natively for `arm64` (Apple Silicon, ARM servers) and do not support `amd64` (x86_64) platforms efficiently. 

To bypass this limitation, we use **custom Dockerfiles** (`Dockerfile.litellm` and `Dockerfile.websearch`) built on top of a `python:3.12-slim` base image. This compiles/installs the LiteLLM proxy directly from PyPI (`pip install "litellm[proxy] == 1.88.1"`), guaranteeing native compatibility on all standard AMD64 linux/server architectures.

---

## 2. Make Target Command Reference

The [Makefile](file:///home/gustavo/GIT/gfnord/litellm-websearch/Makefile) provides quick access to common Docker operations:

| Make Target | Action |
|---|---|
| `make build` | Builds or rebuilds images defined in the docker-compose file. |
| `make up` | Starts the container network in the background (`-d`). |
| `make down` | Stops the containers and teardowns the network. |
| `make restart` | Restarts all active containers without rebuilding. |
| `make logs` | Follows logs (`-f`) for all containers in the stack. |
| `make litellm-logs` | Follows logs specifically for the `litellm` container. |
| `make websearch-logs`| Follows logs specifically for the `websearch-proxy` container. |
| `make shell-litellm` | Execs an interactive `/bin/sh` shell inside the running `litellm` container. |
| `make shell-websearch`| Execs an interactive `/bin/sh` shell inside the running `websearch-proxy` container. |
| `make ps` | Displays the health, ports, and state of running compose services. |

---

## 3. Local Development (No Docker)

For faster iteration cycles or code profiling, you can run services directly on your host machine.

### Virtual Environment Setup
Ensure you are using Python 3.12:
```bash
# Create and activate python virtual environment
python3 -m venv litellm-env
source litellm-env/bin/activate

# Install requirements
pip install -r requirements-litellm.txt
pip install -r requirements-websearch.txt
```

### Starting Services Manually
In terminal 1, run the LiteLLM proxy:
```bash
source litellm-env/bin/activate
litellm --config config.yaml --port 4000
```

In terminal 2, run the FastAPI web search proxy:
```bash
source litellm-env/bin/activate
export SERPER_API_KEY="your-api-key"
export LITELLM_URL="http://localhost:4000"
export PORT=4001
python websearch_proxy.py
```

---

## 4. Validating and Testing the Setup

To test if the proxy is correctly intercepting requests and running searches, send a curl request to port 4001:

```bash
curl -X POST http://localhost:4001/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-123345sdf" \
  -d '{
    "model": "qwen-3.5",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Search for the latest Python release notes"}
    ]
  }'
```

### Inspecting logs for search execution
If search intent is detected, you should see the following logs output in your websearch console:
```text
[websearch_proxy] HIT http://localhost:4001/v1/messages
[websearch_proxy] stream=False msgs=1
[websearch_proxy] Search intent detected, querying: the latest Python release notes
[websearch_proxy] Got 1056 chars of results
[websearch_proxy] Response: 1 blocks
[websearch_proxy]   block type=text len=842 preview='Based on the latest Python release notes...'
```

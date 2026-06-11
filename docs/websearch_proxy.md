# Web Search Proxy Deep Dive

The custom web search proxy (`websearch_proxy.py`) is a lightweight FastAPI gateway sitting in front of LiteLLM. It executes pre-processing (detecting query intent, searching the web, augmenting system prompts) and post-processing (filtering text, mimicking Anthropic SSE format).

---

## 1. Intent Detection & Query Extraction

The `extract_search_query()` function parses the request's messages history in reverse chronological order to find the latest user message.

### Intent Triggers
A web search is triggered if the message contains:
- **Explicit Triggers**: `"search"`, `"look up"`, `"look for"`
- **Recency Triggers**: `"latest"`, `"recent"`, `"current"`, `"today"`, `"news"`

### Heuristic Exclusions
To prevent false positives, search is **completely bypassed** if:
1. **Claude Code / System Messages**: The message content contains `<system-reminder>` or `<command-`.
2. **Length Threshold**: The message content is larger than `500` characters (likely indicating code context or raw log files rather than a query).
3. **Coding Indicators**: The message content matches programming action words:
   - `"write a"`, `"create a"`, `"make a"`, `"generate a"`, `"implement"`, or contains shebangs (`"#!/"`).

### Extraction Regex
If intent matches, search verbs are stripped using the regex:
```python
query = re.sub(
    r"^(please\s+)?(search(\s+the\s+web)?\s+(for\s+)?|look\s+up\s+|find\s+(me\s+)?)",
    "", content, flags=re.IGNORECASE
).strip()
```

---

## 2. Serper Search Execution

When search intent is validated, `do_serper_search()` calls Google search via the Serper API:

- **Endpoint**: `https://google.serper.dev/search`
- **Configuration**: Fetches `num: 8` results, using a timeout of `10.0` seconds.
- **Answer Box Extraction**: Checks for Google Answer Boxes (`answerBox`), extracting the direct answer or snippet.
- **Organic Results**: Parses the top 6 organic result objects, constructing a markdown string:
  ```markdown
  - Title: Snippet text (https://link-to-source.com)
  ```

---

## 3. Context & System Prompt Injection

Once search results are retrieved, they are formatted and injected as a system instruction:

```python
search_context = (
    f"Today's date is {datetime.now().strftime('%B %d, %Y')}.\n\n"
    f"The user is asking about: {search_query}\n\n"
    f"Here are current web search results to help you answer:\n\n"
    f"{search_results}\n\n"
    f"Use these results to give a comprehensive, accurate answer. "
    f"Do not say you cannot search the web — you have the results above."
)
```

If the client request already contains a `system` prompt, the `search_context` is appended to the bottom of the existing system prompt separated by newlines. Otherwise, it forms the entire system prompt.

---

## 4. Response Processing & Sanitization

After sending the request to the LLM backend via LiteLLM:

- **Thinking Blocks Removal**: Any blocks of type `"thinking"` are stripped from the response content. This is essential for non-Anthropic models (like Qwen or Gemma) run via Ollama, as they do not output valid thinking schemas in the way clients like Claude Code expect.
- **Mask Cleaning**: Strips internal tag constructs with pattern `<|mask_start|>...<|mask_end|>` to prevent raw token markers from rendering in the terminal.
- **Anthropic SSE Emulation**:
  - When the client requests streaming (`stream=True`), the proxy makes a **non-streaming** call to LiteLLM to ensure all context was sent and parsed sequentially.
  - It then breaks down the final complete text block into small tokens and yields them through `StreamingResponse` using the Anthropic Server-Sent Events (SSE) schema.
  - Emulated events include `message_start`, `content_block_start`, `content_block_delta` (in chunks of 20 characters), `content_block_stop`, `message_delta`, and `message_stop`.

---

## 5. Direct Passthrough Mode

If no search intent is found, the proxy acts as a transparent, zero-overhead gateway:
- Passes streaming requests directly using `httpx.stream("POST", ...)` and yields raw chunks back to the client.
- Passes non-streaming requests with simple forwarding.
- Scrubs model-specific parameters like `betas` and removes client-side tool configurations such as `web_search_20250305` or `litellm_web_search` to prevent API compatibility conflicts.
- Handles generic routes dynamically, allowing requests to `GET /v1/models` and other admin API routes to pass straight to LiteLLM.

#!/usr/bin/env python3
"""
Web search proxy: sits on port 4001, forwards to LiteLLM on port 4000.
Uses RAG-style proactive search: detects search intent in the last user message,
runs Serper search, injects results into system prompt, then calls the model once.
No tool-calling required from the model — works with any LLM.
"""
import json
import os
import re
import httpx
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

LITELLM_URL = os.getenv("LITELLM_URL", "http://localhost:4000")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
SERPER_URL = "https://google.serper.dev/search"
PORT = int(os.getenv("PORT", "4001"))

app = FastAPI()


async def do_serper_search(query: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            SERPER_URL,
            headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": query, "num": 8},
            timeout=10.0
        )
        data = resp.json()
    results = []
    if "answerBox" in data:
        box = data["answerBox"]
        answer = box.get("answer") or box.get("snippet", "")
        if answer:
            results.append(f"Answer box: {answer}")
    for r in data.get("organic", [])[:6]:
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")
        results.append(f"- {title}: {snippet} ({link})")
    return "\n".join(results) or "No results found."


def extract_search_query(messages: list) -> str | None:
    """Extract the search query from the last user message.
    Only triggers on clean, short user messages — not Claude Code system reminders."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                # Only look at text blocks, ignore tool_result blocks
                text_parts = [
                    b.get("text", "") for b in content
                    if b.get("type") == "text"
                ]
                content = " ".join(text_parts)

            # Ignore system reminders and internal Claude Code messages
            if "<system-reminder>" in content or "<command-" in content:
                continue
            # Ignore very long messages — likely system context, not a user query
            if len(content) > 500:
                continue

            content_lower = content.lower()
            # Bail out if this looks like a coding/file operation instruction
            CODE_INDICATORS = ["write a", "create a", "make a", "generate a", "implement", "#!/"]
            if any(indicator in content_lower for indicator in CODE_INDICATORS):
                return None
            # Require explicit search verb — don't trigger on passive keywords alone
            EXPLICIT_TRIGGERS = ["search", "look up", "look for"]
            # Also trigger on clear recency signals in short queries
            RECENCY_TRIGGERS = ["latest", "recent", "current", "today", "news"]
            has_explicit = any(t in content_lower for t in EXPLICIT_TRIGGERS)
            has_recency = any(t in content_lower for t in RECENCY_TRIGGERS)

            if has_explicit or has_recency:
                # Strip leading "search for", "look up", etc.
                query = re.sub(
                    r"^(please\s+)?(search(\s+the\s+web)?\s+(for\s+)?|look\s+up\s+|find\s+(me\s+)?)",
                    "", content, flags=re.IGNORECASE
                ).strip()
                return query or content
    return None


def make_forward_headers(raw_headers: dict) -> dict:
    return {k: v for k, v in raw_headers.items()
            if k.lower() not in ("host", "content-length", "transfer-encoding")}


async def call_litellm_non_streaming(body: dict, headers: dict) -> dict:
    req_body = dict(body)
    req_body["stream"] = False
    req_body.pop("betas", None)
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{LITELLM_URL}/v1/messages",
            headers=headers,
            json=req_body
        )
        resp.raise_for_status()
        return resp.json()


async def stream_passthrough(body: dict, headers: dict):
    """Forward a streaming request directly to LiteLLM."""
    req_body = dict(body)
    req_body["stream"] = True
    req_body.pop("betas", None)
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST", f"{LITELLM_URL}/v1/messages",
            headers=headers, json=req_body
        ) as resp:
            async for chunk in resp.aiter_bytes():
                yield chunk


async def anthropic_sse_from_response(resp_data: dict):
    """Convert a complete Anthropic messages response into a proper SSE stream."""
    def sse(event_data: dict) -> bytes:
        return f"data: {json.dumps(event_data)}\n\n".encode()

    yield sse({
        "type": "message_start",
        "message": {
            "id": resp_data.get("id", ""),
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": resp_data.get("model", ""),
            "stop_reason": None,
            "stop_sequence": None,
            "usage": {
                "input_tokens": resp_data.get("usage", {}).get("input_tokens", 0),
                "output_tokens": 0
            }
        }
    })

    idx = 0
    for block in resp_data.get("content", []):
        block_type = block.get("type")

        # Skip thinking blocks — not expected by Claude Code from non-Anthropic models
        if block_type == "thinking":
            continue

        if block_type == "text":
            yield sse({"type": "content_block_start", "index": idx,
                       "content_block": {"type": "text", "text": ""}})
            text = block.get("text", "")
            chunk_size = 20
            for start in range(0, len(text), chunk_size):
                yield sse({"type": "content_block_delta", "index": idx,
                           "delta": {"type": "text_delta",
                                     "text": text[start:start + chunk_size]}})
            yield sse({"type": "content_block_stop", "index": idx})
            idx += 1
        # All other block types (tool_use etc) are skipped — not exposed to Claude Code

    yield sse({
        "type": "message_delta",
        "delta": {
            "stop_reason": "end_turn",
            "stop_sequence": None
        },
        "usage": {"output_tokens": resp_data.get("usage", {}).get("output_tokens", 0)}
    })
    yield sse({"type": "message_stop"})


@app.post("/v1/messages")
@app.post("/v1/messages/")
async def messages(request: Request):
    print(f"[websearch_proxy] HIT {request.url}", flush=True)
    body = await request.json()
    raw_headers = dict(request.headers)
    forward_headers = make_forward_headers(raw_headers)
    is_streaming = body.get("stream", False)
    msgs = body.get("messages", [])

    print(f"[websearch_proxy] stream={is_streaming} msgs={len(msgs)}", flush=True)

    # Detect search intent in last user message
    search_query = extract_search_query(msgs)

    body = dict(body)
    body.pop("betas", None)
    # Remove Anthropic-native web search tools — we handle search ourselves
    body["tools"] = [
        t for t in body.get("tools", [])
        if not (t.get("type") == "web_search_20250305" or
                (t.get("type") == "function" and
                 t.get("function", {}).get("name") == "litellm_web_search"))
    ]
    if not body["tools"]:
        body.pop("tools", None)

    if search_query:
        print(f"[websearch_proxy] Search intent detected, querying: {search_query}", flush=True)
        search_results = await do_serper_search(search_query)
        print(f"[websearch_proxy] Got {len(search_results)} chars of results", flush=True)

        # Inject search results into system prompt
        search_context = (
            f"Today's date is {datetime.now().strftime('%B %d, %Y')}.\n\n"
            f"The user is asking about: {search_query}\n\n"
            f"Here are current web search results to help you answer:\n\n"
            f"{search_results}\n\n"
            f"Use these results to give a comprehensive, accurate answer. "
            f"Do not say you cannot search the web — you have the results above."
        )
        existing_system = body.get("system", "")
        if existing_system:
            body["system"] = f"{existing_system}\n\n{search_context}"
        else:
            body["system"] = search_context

        resp_data = await call_litellm_non_streaming(body, forward_headers)

        # Strip thinking blocks from response
        content = resp_data.get("content", [])
        content_filtered = [b for b in content if b.get("type") != "thinking"]
        resp_data = dict(resp_data)
        resp_data["content"] = content_filtered
        for block in resp_data["content"]:
            if block.get("type") == "text":
                block["text"] = re.sub(r"<\|mask_start\|>.*?<\|mask_end\|>", "", block["text"], flags=re.DOTALL).strip()
        resp_data["stop_reason"] = "end_turn"

        print(f"[websearch_proxy] Response: {len(content_filtered)} blocks", flush=True)
        for b in content_filtered:
            btext = b.get("text", "")
            if len(btext) < 100:
                print(f"[websearch_proxy]   block FULL={json.dumps(b)}", flush=True)
            else:
                print(f"[websearch_proxy]   block type={b.get('type')} len={len(btext)} preview={repr(btext[:150])}", flush=True)

        if is_streaming:
            return StreamingResponse(
                anthropic_sse_from_response(resp_data),
                media_type="text/event-stream"
            )
        return Response(
            content=json.dumps(resp_data), status_code=200,
            media_type="application/json"
        )

    else:
        # No search intent — forward directly
        print(f"[websearch_proxy] No search intent, forwarding directly", flush=True)
        if is_streaming:
            return StreamingResponse(
                stream_passthrough(body, forward_headers),
                media_type="text/event-stream"
            )
        else:
            async with httpx.AsyncClient(timeout=300.0) as client:
                resp = await client.post(
                    f"{LITELLM_URL}/v1/messages",
                    headers=forward_headers, json=body
                )
            try:
                resp_data = resp.json()
                for block in resp_data.get("content", []):
                    if block.get("type") == "text":
                        block["text"] = re.sub(r"<\|mask_start\|>.*?<\|mask_end\|>", "", block["text"], flags=re.DOTALL).strip()
                return Response(
                    content=json.dumps(resp_data), status_code=resp.status_code,
                    media_type=resp.headers.get("content-type", "application/json")
                )
            except Exception:
                return Response(
                    content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get("content-type", "application/json")
                )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_everything_else(request: Request, path: str):
    body = await request.body()
    raw_headers = make_forward_headers(dict(request.headers))
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.request(
            method=request.method,
            url=f"{LITELLM_URL}/{path}",
            headers=raw_headers,
            content=body,
            params=dict(request.query_params)
        )
        return Response(
            content=resp.content, status_code=resp.status_code,
            media_type=resp.headers.get("content-type", "application/json")
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")

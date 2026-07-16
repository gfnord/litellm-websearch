"""
LiteLLM pre-call hook that scrubs upstream-incompatible content blocks from
message history. Runs before requests are forwarded upstream.

Motivation: Zhipu's /api/coding/paas/v4 (the Anthropic passthrough for GLM
coding models) rejects `image` / `image_url` content blocks with
`ZaiException - messages.content.type is invalid`. This callback replaces
just those blocks with a text placeholder so the request goes through.

DO NOT extend this to strip `tool_use`, `tool_result`, `thinking`, or
`redacted_thinking`. Zhipu's Anthropic passthrough handles those natively
(that's what enables Bash / MCP tool loops), and stripping them makes the
model hallucinate around the missing turns — e.g. inventing a plausible
`send_file` path because the real one from the prior `Bash` tool_result
was replaced with `[tool_result omitted]`. Only strip block types the
upstream provider actually errors on.

The scrub is skipped entirely for vision-capable models (see
_is_vision_model) — they need to see the image blocks.

Registered in config.yaml:
    litellm_settings:
      callbacks: [..., "strip_non_text_content.stripNonText"]

Mounted into the container via docker-compose.
"""

import re

from litellm.integrations.custom_logger import CustomLogger


# Deny-list: block types that Zhipu's /coding/paas/v4 endpoint rejects.
# Add here (and nowhere else) if a new type causes ZaiException. Every
# other content type — tool_use, tool_result, thinking, document,
# container_upload, server_tool_use, ... — must pass through untouched.
_STRIP_TYPES = {
    "image",       # Anthropic-shape image block
    "image_url",   # OpenAI-shape image block
}

# Substring hints for models that natively accept image / rich content blocks.
# Match is case-insensitive against data["model"]. Any hit → skip the strip.
# Keep conservative — a false positive here means the upstream provider will
# 400 on the untouched request.
_VISION_MODEL_HINTS = (
    "claude-",
    "gpt-4o",
    "gpt-4-vision",
    "gpt-5",
    "gemini",
    "-vision",
)

# Z.AI's GLM vision family: glm-4v, glm-4v-plus, glm-4.5v, glm-4.6v, ...
# Matches the "v" suffix on any glm-<major>[.<minor>] version.
_GLM_VISION_RE = re.compile(r"glm-\d+(\.\d+)?v", re.IGNORECASE)


def _is_vision_model(model):
    if not isinstance(model, str):
        return False
    m = model.lower()
    if _GLM_VISION_RE.search(m):
        return True
    return any(hint in m for hint in _VISION_MODEL_HINTS)


def _flatten_block(block):
    """Return a text placeholder for a single stripped content block."""
    btype = block.get("type", "unknown") if isinstance(block, dict) else "unknown"
    return {"type": "text", "text": f"[{btype} omitted]"}


def _scrub_content(content):
    """Walk a message content field; replace deny-listed blocks with placeholders."""
    if not isinstance(content, list):
        return content
    scrubbed = []
    for block in content:
        if not isinstance(block, dict):
            scrubbed.append(block)
            continue
        btype = block.get("type")
        if btype in _STRIP_TYPES:
            scrubbed.append(_flatten_block(block))
            continue
        scrubbed.append(block)
    return scrubbed


def _scrub_messages(messages):
    if not isinstance(messages, list):
        return messages
    for msg in messages:
        if isinstance(msg, dict) and "content" in msg:
            msg["content"] = _scrub_content(msg["content"])
    return messages


class StripNonTextContent(CustomLogger):
    async def async_pre_call_hook(
        self,
        user_api_key_dict,
        cache,
        data,
        call_type,
    ):
        if isinstance(data, dict) and "messages" in data:
            if _is_vision_model(data.get("model")):
                return data
            data["messages"] = _scrub_messages(data["messages"])
        return data


stripNonText = StripNonTextContent()

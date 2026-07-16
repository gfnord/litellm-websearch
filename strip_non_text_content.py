"""
LiteLLM pre-call hook that replaces non-text content blocks in messages with
text placeholders. Runs before requests are forwarded upstream, so providers
that only accept `type: "text"` in the content array (e.g. Zhipu's
/api/coding/paas/v4 endpoint) don't 400 on images or other rich blocks.

Handles both Anthropic-shape (`image`, `tool_result` with structured content,
`document`, `container_upload`, ...) and OpenAI-shape (`image_url`,
`input_audio`, ...) block types. Text blocks pass through untouched. Tool-call
and tool-result envelopes on the message itself (role="tool",
message["tool_calls"]) are left alone — only the inner `content` arrays are
scrubbed.

Registered in config.yaml:
    litellm_settings:
      callbacks: [..., "strip_non_text_content.stripNonText"]

Mounted into the container via docker-compose.
"""

import re

from litellm.integrations.custom_logger import CustomLogger


_ALLOWED_TYPES = {"text"}

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
    """Return a text placeholder for a single non-text content block."""
    btype = block.get("type", "unknown") if isinstance(block, dict) else "unknown"
    return {"type": "text", "text": f"[{btype} omitted]"}


def _scrub_content(content):
    """Walk a message content field; replace non-text blocks with placeholders."""
    if not isinstance(content, list):
        return content
    scrubbed = []
    for block in content:
        if not isinstance(block, dict):
            scrubbed.append(block)
            continue
        btype = block.get("type")
        if btype in _ALLOWED_TYPES:
            scrubbed.append(block)
            continue
        scrubbed.append(_flatten_block(block))
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

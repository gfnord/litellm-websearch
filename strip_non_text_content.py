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

from litellm.integrations.custom_logger import CustomLogger


_ALLOWED_TYPES = {"text"}


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
            data["messages"] = _scrub_messages(data["messages"])
        return data


stripNonText = StripNonTextContent()

"""OpenAI API format adapter.

Provides conversion between OpenAI Chat Completions API format and FakeLM's
internal request/response models.
"""

import json
import time
import uuid
from typing import Any, Dict, Iterator, List

from fakellm.api_adapters.base import InternalRequest, InternalResponse


def to_internal(request_dict: Dict[str, Any]) -> InternalRequest:
    """
    Convert an OpenAI Chat Completions request dict to an internal request.

    Args:
        request_dict: The parsed JSON body from an OpenAI-compatible client.

    Returns:
        An InternalRequest instance.
    """
    messages = request_dict.get("messages", [])
    # Extract the last user message as the prompt
    prompt = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            prompt = str(msg.get("content", ""))
            break

    # If no user message found, concatenate all message contents
    if not prompt:
        parts = []
        for msg in messages:
            if isinstance(msg, dict):
                parts.append(str(msg.get("content", "")))
        prompt = " ".join(parts)

    return InternalRequest(
        prompt=prompt,
        temperature=float(request_dict.get("temperature", 1.0)),
        max_tokens=int(request_dict.get("max_tokens", 100)),
        stream=bool(request_dict.get("stream", False)),
        intelligence=float(request_dict.get("intelligence", request_dict.get("intelligence_level", 0.5))),
        seed=request_dict.get("seed"),
        extra=request_dict.get("extra", {}),
    )


def from_internal(
    response: InternalResponse,
    model: str = "fake-gpt-4",
    stats: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Convert an internal response to an OpenAI non-streaming ChatCompletion response.

    Args:
        response: The internal generation response.
        model: The model name to report.
        stats: Optional performance stats dict with keys: engine, elapsed, tokens, speed.

    Returns:
        A dict matching the OpenAI ChatCompletion schema.
    """
    result = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response.text,
                },
                "finish_reason": response.finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(response.text) // 2),
            "completion_tokens": response.tokens_used,
            "total_tokens": max(1, len(response.text) // 2) + response.tokens_used,
        },
    }
    if stats:
        result["x_fakellm_stats"] = stats
    return result


def stream_chunk(model: str, content: str, finish_reason: str | None = None) -> Dict[str, Any]:
    """
    Build a single SSE chunk for OpenAI streaming responses.

    Args:
        model: The model name.
        content: The delta content string.
        finish_reason: Optional finish_reason for the last chunk.

    Returns:
        A dict representing one streaming chunk.
    """
    chunk: Dict[str, Any] = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content},
                "finish_reason": finish_reason,
            }
        ],
    }
    return chunk


def build_sse_event(data: Dict[str, Any]) -> str:
    """
    Format a dict as an SSE event string.

    Args:
        data: The dict to serialize.

    Returns:
        An SSE-formatted string: 'data: {json}\\n\\n'.
    """
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_stats_event(stats: Dict[str, Any]) -> str:
    """
    Format a stats dict as an SSE event string with event type x_fakellm_stats.

    Args:
        stats: Performance stats dict.

    Returns:
        An SSE-formatted string with event: x_fakellm_stats.
    """
    return f"event: x_fakellm_stats\ndata: {json.dumps(stats, ensure_ascii=False)}\n\n"


def get_models_list() -> Dict[str, Any]:
    """
    Return a fake OpenAI /v1/models response.

    Returns:
        A dict matching the OpenAI list models schema.
    """
    return {
        "object": "list",
        "data": [
            {
                "id": "fake-gpt-4",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "fakellm",
            },
            {
                "id": "random-llm",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "fakellm",
            },
        ],
    }
"""Streaming helper utilities for async token generation."""

import asyncio
import json
from typing import Any, AsyncIterator, Dict, Iterator


async def async_stream_wrapper(iterator: Iterator[str], model: str, chunk_builder) -> AsyncIterator[str]:
    """
    Wrap a synchronous token iterator into an async SSE stream.

    Args:
        iterator: A synchronous iterator yielding string tokens.
        model: The model name for chunk metadata.
        chunk_builder: A callable(model, content) that returns a chunk dict.

    Yields:
        SSE-formatted strings.
    """
    for chunk in iterator:
        data = chunk_builder(model, chunk)
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
    yield "data: [DONE]\n\n"
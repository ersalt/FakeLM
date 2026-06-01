"""FastAPI application entry point for FakeLM."""

import asyncio
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from pydantic import ValidationError

from fakellm.api_adapters.openai import (
    build_sse_event,
    build_stats_event,
    from_internal,
    get_models_list,
    stream_chunk,
    to_internal,
)
from fakellm.config import AppConfig
from fakellm.generation import get_generator
from fakellm.generation.base import BaseGenerator, InternalRequest, InternalResponse
from fakellm.server.middleware import FakeModelMiddleware

# Load configuration and initialize generator
_config = AppConfig()
_generator: BaseGenerator = get_generator(_config)

# Configure logging
logging.basicConfig(
    level=getattr(logging, _config.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_logger = logging.getLogger("fakellm")

app = FastAPI(title="FakeLM", description="A fake LLM API server", version="0.1.0")

# Determine static directory absolute path
_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "static")

# Mount static files
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Fake model middleware — simulated delays, errors, rate limiting (added first so it wraps everything)
app.add_middleware(FakeModelMiddleware, config=_config)

# CORS middleware — allow all origins by default
app.add_middleware(
    CORSMiddleware,
    allow_origins=_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Serve the chat UI."""
    return FileResponse(os.path.join(_static_dir, "index.html"))


@app.get("/v1/models")
async def list_models():
    """Return a fake model list in OpenAI format."""
    return JSONResponse(content=get_models_list())


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """
    Handle Chat Completions requests (both streaming and non-streaming).

    Converts OpenAI-format request to internal format, generates text via
    the active generator, and returns the response in the appropriate format.
    """
    body = await request.json()
    try:
        internal_request: InternalRequest = to_internal(body)
    except ValidationError as e:
        return JSONResponse(
            status_code=422,
            content={"detail": e.errors()},
        )
    model = body.get("model", "fake-gpt-4")

    # Log the incoming request
    prompt_preview = internal_request.prompt[:80] if internal_request.prompt else "(empty)"
    _logger.info(
        "Request | stream=%s | intelligence=%.2f | max_tokens=%d | prompt=%s...",
        internal_request.stream,
        internal_request.intelligence,
        internal_request.max_tokens,
        prompt_preview,
    )

    if internal_request.stream:
        return StreamingResponse(
            _stream_generator(internal_request, model),
            media_type="text/event-stream",
            headers={
                "X-FakeLM-Engine": _generator.get_metadata().get("type", "unknown"),
            },
        )
    else:
        tokens: list[str] = []
        start_time = time.perf_counter()
        for token in _generator.generate(internal_request):
            tokens.append(token)
        elapsed = time.perf_counter() - start_time
        text = "".join(tokens)
        token_count = len(tokens)

        response = InternalResponse(text=text, tokens_used=token_count)

        tokens_per_sec = token_count / elapsed if elapsed > 0 else 0
        engine_name = _generator.get_metadata().get("type", "unknown")

        if _config.show_tokens_per_second:
            _logger.info(
                "Response | tokens=%d | elapsed=%.4fs | speed=%.0f tokens/s | engine=%s",
                token_count,
                elapsed,
                tokens_per_sec,
                engine_name,
            )

        stats = {
            "engine": engine_name,
            "elapsed": elapsed,
            "tokens": token_count,
            "speed": tokens_per_sec,
        }

        return JSONResponse(
            content=from_internal(response, model=model, stats=stats),
            headers={
                "X-FakeLM-Engine": engine_name,
                "X-FakeLM-Speed": f"{tokens_per_sec:.0f} tokens/s",
            },
        )


async def _stream_generator(request: InternalRequest, model: str):
    """
    Wrap the synchronous generator in an async SSE stream.

    Yields SSE-formatted strings for each token, plus a final [DONE] marker.

    Args:
        request: The internal request.
        model: The model name.
    """
    token_count = 0
    start_time = time.perf_counter()

    for token in _generator.generate(request):
        token_count += 1
        chunk_data = stream_chunk(model, token)
        yield build_sse_event(chunk_data)
        await asyncio.sleep(0)  # Yield control to the event loop

    # Send a final chunk with finish_reason
    elapsed = time.perf_counter() - start_time
    tokens_per_sec = token_count / elapsed if elapsed > 0 else 0
    engine_name = _generator.get_metadata().get("type", "unknown")

    if _config.show_tokens_per_second:
        _logger.info(
            "Stream | tokens=%d | elapsed=%.4fs | speed=%.0f tokens/s | engine=%s",
            token_count,
            elapsed,
            tokens_per_sec,
            engine_name,
        )

    # Yield stats event before final chunk
    stats = {
        "engine": engine_name,
        "elapsed": elapsed,
        "tokens": token_count,
        "speed": tokens_per_sec,
    }
    yield build_stats_event(stats)

    final_chunk = stream_chunk(model, "", finish_reason="stop")
    yield build_sse_event(final_chunk)
    yield "data: [DONE]\n\n"

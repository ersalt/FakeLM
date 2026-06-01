"""Middleware for simulation effects: random delays, fake errors, and rate limiting."""

import random
import time

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from fakellm.config import AppConfig


class FakeModelMiddleware(BaseHTTPMiddleware):
    """
    Middleware that simulates real API behaviors:

    - Random processing delay (simulates inference time).
    - Random HTTP 429 (rate limiting) errors.
    - Random HTTP 500 (internal server) errors.
    - Added custom FakeLM response headers.
    """

    def __init__(self, app, config: AppConfig):
        """
        Initialize the middleware.

        Args:
            app: The ASGI application.
            config: Application configuration instance.
        """
        super().__init__(app)
        self._config = config
        self._rng = random.Random()

    async def dispatch(self, request: Request, call_next):
        """
        Intercept requests and inject simulation behaviors.

        Args:
            request: The incoming HTTP request.
            call_next: Next middleware/callable in the chain.

        Returns:
            The HTTP response (possibly modified by simulation effects).
        """
        # Skip non-API routes
        path = request.url.path
        if not path.startswith("/v1/"):
            return await call_next(request)

        # 1. Random delay: simulate inference time (0 to 0.5 seconds)
        delay = self._rng.uniform(0, 0.5)
        if delay > 0:
            time.sleep(delay)

        # 2. Fake rate limiting: return 429 with probability from config
        rate_limit_prob = self._config.fake_rate_limit
        if rate_limit_prob > 0 and self._rng.random() < rate_limit_prob:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": {
                        "message": "Rate limit exceeded. Too many requests.",
                        "type": "rate_limit_error",
                        "code": "rate_limit_exceeded",
                    }
                },
                headers={
                    "X-FakeLM-RateLimit": "Hint: this is intentionally simulated by FakeLM. Change fake_rate_limit in config to 0 to disable."
                },
            )

        # 3. Random 500 error (10% chance when rate_limit_prob > 0.1)
        if rate_limit_prob > 0.1 and self._rng.random() < 0.05:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "message": "Internal server error (simulated).",
                        "type": "server_error",
                        "code": "internal_error",
                    }
                },
            )

        # Process the actual request
        response: Response = await call_next(request)

        # Add FakeLM-specific response headers
        response.headers["X-FakeLM-Simulated"] = "true"
        response.headers["X-FakeLM-Processing-Time"] = f"{delay:.4f}s"

        return response
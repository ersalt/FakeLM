"""FakeLM entry point — start the FastAPI server with uvicorn."""

import uvicorn

from fakellm.config import AppConfig


def main():
    """Parse config and start the uvicorn server."""
    config = AppConfig()
    uvicorn.run(
        "fakellm.server.app:app",
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        reload=False,
        access_log=True,
    )


if __name__ == "__main__":
    main()
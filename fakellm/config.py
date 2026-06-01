"""Configuration loader using PyYAML and pydantic-settings."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class AppConfig:
    """Application configuration loaded from a YAML file."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Load configuration from the specified YAML file.

        Args:
            config_path: Path to the config YAML file. Defaults to 'data/config.yaml'.
        """
        if config_path is None:
            config_path = "data/config.yaml"

        self._data: Dict[str, Any] = {}
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}

    @property
    def server(self) -> Dict[str, Any]:
        """Server-related configuration."""
        return self._data.get("server", {})

    @property
    def generation(self) -> Dict[str, Any]:
        """Generation-related configuration."""
        return self._data.get("generation", {})

    @property
    def logging(self) -> Dict[str, Any]:
        """Logging-related configuration."""
        return self._data.get("logging", {})

    @property
    def host(self) -> str:
        """Server host."""
        return self.server.get("host", "0.0.0.0")

    @property
    def port(self) -> int:
        """Server port."""
        return self.server.get("port", 8000)

    @property
    def cors_origins(self) -> list:
        """CORS allowed origins."""
        return self.server.get("cors_origins", ["*"])

    @property
    def fake_rate_limit(self) -> float:
        """Probability of returning HTTP 429."""
        return float(self.server.get("fake_rate_limit", 0))

    @property
    def default_engine(self) -> str:
        """Default generation engine name."""
        return self.generation.get("default_engine", "composite")

    @property
    def engine_config(self) -> Dict[str, Any]:
        """Per-engine configuration dictionaries."""
        return self.generation.get("engines", {})

    @property
    def log_level(self) -> str:
        """Logging level."""
        return self.logging.get("level", "INFO")

    @property
    def show_tokens_per_second(self) -> bool:
        """Whether to log tokens per second."""
        return bool(self.logging.get("show_tokens_per_second", True))
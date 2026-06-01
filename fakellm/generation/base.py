"""Abstract base generator and internal data models."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Optional

from pydantic import BaseModel, Field


class InternalRequest(BaseModel):
    """Unified internal representation of a generation request."""

    prompt: str = Field(default="", description="User input text (last user message or concatenated history).")
    temperature: float = Field(default=1.0, ge=0.0, le=2.0, description="Randomness scaling factor.")
    max_tokens: int = Field(default=100, ge=1, description="Maximum number of tokens to generate.")
    stream: bool = Field(default=False, description="Whether to stream the response.")
    intelligence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="0=pure random, 1=most 'intelligent' (markov/template-based).",
    )
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility.")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Vendor-specific extra parameters.")


class InternalResponse(BaseModel):
    """Unified internal representation of a generation response."""

    text: str
    tokens_used: int
    finish_reason: str = "stop"


class BaseGenerator(ABC):
    """All generators must implement this interface."""

    @abstractmethod
    def generate(self, request: InternalRequest) -> Iterator[str]:
        """
        Yield tokens (characters or words) one at a time.

        Args:
            request: The internal request object.

        Yields:
            String tokens, each typically a single character or word.
        """
        ...

    @abstractmethod
    def get_metadata(self) -> dict:
        """
        Return generator metadata for /v1/models or logging.

        Returns:
            A dictionary of metadata key-value pairs.
        """
        ...
"""Re-exports of internal data models for API adapters.

These models are defined in generation.base but re-exported here for convenience
so that API adapter modules can import from a single location.
"""

from fakellm.generation.base import InternalRequest, InternalResponse

__all__ = ["InternalRequest", "InternalResponse"]
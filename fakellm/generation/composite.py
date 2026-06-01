"""Composite generator: routes to sub-generators based on intelligence level."""

from typing import Dict, Iterator

from fakellm.generation.base import BaseGenerator, InternalRequest


class CompositeGenerator(BaseGenerator):
    """
    Selects a sub-generator based on the request's intelligence parameter.

    - intelligence <= low_threshold  → low_engine (typically RandomCharGenerator)
    - intelligence >= high_threshold → high_engine (typically MarkovGenerator)
    - otherwise                       → mid_engine (typically TemplateGenerator)
    """

    def __init__(
        self,
        generators: Dict[str, BaseGenerator],
        low_threshold: float = 0.3,
        high_threshold: float = 0.7,
        low_engine: str = "random_char",
        mid_engine: str = "template",
        high_engine: str = "markov",
    ):
        """
        Initialize the composite generator.

        Args:
            generators: A dict mapping engine names to BaseGenerator instances.
            low_threshold: Intelligence below this uses the low engine.
            high_threshold: Intelligence above this uses the high engine.
            low_engine: Key in generators dict for low-intelligence requests.
            mid_engine: Key in generators dict for mid-intelligence requests.
            high_engine: Key in generators dict for high-intelligence requests.
        """
        self._generators = generators
        self._low_threshold = low_threshold
        self._high_threshold = high_threshold
        self._low_engine = low_engine
        self._mid_engine = mid_engine
        self._high_engine = high_engine

    def _select_generator(self, intelligence: float) -> BaseGenerator:
        """
        Pick the appropriate sub-generator for the given intelligence level.

        Args:
            intelligence: The request intelligence value (0.0 to 1.0).

        Returns:
            The selected BaseGenerator instance.
        """
        if intelligence <= self._low_threshold:
            engine_name = self._low_engine
        elif intelligence >= self._high_threshold:
            engine_name = self._high_engine
        else:
            engine_name = self._mid_engine

        return self._generators.get(engine_name, self._generators.get(self._low_engine))

    def generate(self, request: InternalRequest) -> Iterator[str]:
        """
        Delegate generation to the appropriate sub-generator.

        Args:
            request: The internal request.

        Yields:
            Tokens from the selected sub-generator.
        """
        generator = self._select_generator(request.intelligence)
        if generator is None:
            # Ultimate fallback — nothing to generate
            return
        yield from generator.generate(request)

    def get_metadata(self) -> dict:
        """Return metadata about this composite generator."""
        return {
            "type": "composite",
            "low_threshold": self._low_threshold,
            "high_threshold": self._high_threshold,
            "engines": {
                "low": self._low_engine,
                "mid": self._mid_engine,
                "high": self._high_engine,
            },
            "description": "Composite generator that routes based on intelligence",
        }
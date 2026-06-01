"""Markov chain text generator using character-level n-grams."""

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from fakellm.generation.base import BaseGenerator, InternalRequest
from fakellm.utils.randomness import get_rng

# Fallback charset when no chain data is available
_FALLBACK_CHARS = "的一是不了人我在有他这中大来上国个到说们为子和你地出也时年得就那要下abcdefghijklmnopqrstuvwxyz0123456789 "


class MarkovGenerator(BaseGenerator):
    """
    Character-level n-gram Markov chain generator.

    Loads a transition matrix from a JSON file. If no data or an unknown prefix
    is encountered, falls back to random characters.
    """

    def __init__(
        self,
        n: int = 2,
        chain_file: str = "data/markov_chains/zh_2gram.json",
        fallback_to_random: bool = True,
        seed: Optional[int] = None,
    ):
        """
        Initialize the Markov generator.

        Args:
            n: N-gram order (1, 2, or 3).
            chain_file: Path to JSON transition matrix file.
            fallback_to_random: If True, use random chars when no successor found.
            seed: Optional random seed.
        """
        self._n = max(1, n)
        self._rng = get_rng(seed)
        self._fallback_to_random = fallback_to_random
        self._chain: Dict[str, List[str]] = {}
        self._load_chain(chain_file)

    def _load_chain(self, filepath: str) -> None:
        """
        Load the transition matrix from a JSON file.

        Args:
            filepath: Path to the JSON chain file.
        """
        path = Path(filepath)
        if not path.exists():
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return

        if not data:
            return

        # Raw chain: prefix (str of n-1 chars) -> list of successor chars
        self._chain = {}
        for prefix, successors in data.items():
            if isinstance(successors, list) and successors:
                self._chain[str(prefix)] = [str(s) for s in successors]

    def generate(self, request: InternalRequest) -> Iterator[str]:
        """
        Walk the Markov chain to produce tokens.

        If no chain data is loaded, falls back to random character generation.

        Args:
            request: The internal request.

        Yields:
            Character tokens from the Markov walk.
        """
        if request.seed is not None:
            self._rng = get_rng(request.seed)

        max_steps = request.max_tokens

        if not self._chain:
            # No chain data — fall back to random
            yield from self._fallback_generate(max_steps)
            return

        # Build initial prefix from the prompt (last n-1 chars, or random)
        prompt = request.prompt.strip()
        prefix_len = self._n - 1
        if len(prompt) >= prefix_len and prefix_len > 0:
            current_prefix = prompt[-prefix_len:]
            # If prefix not in chain, try shorter
            while current_prefix not in self._chain and len(current_prefix) > 0:
                current_prefix = current_prefix[1:]
            if not current_prefix and prefix_len > 0:
                # Pick a random prefix from the chain
                current_prefix = self._rng.choice(list(self._chain.keys()))
        elif prefix_len == 0:
            current_prefix = ""
        else:
            # Random start
            current_prefix = self._rng.choice(list(self._chain.keys())) if self._chain else ""

        for _ in range(max_steps):
            token = self._next_token(current_prefix)
            yield token
            # Update prefix: drop first char, append new token
            if prefix_len > 0:
                current_prefix = (current_prefix + token)[-prefix_len:]

    def _next_token(self, prefix: str) -> str:
        """
        Get the next character given the current prefix.

        Args:
            prefix: The current context (n-1 chars).

        Returns:
            A single character token.
        """
        # Try exact prefix first
        if prefix in self._chain:
            successors = self._chain[prefix]
            return self._rng.choice(successors)

        # No match — try shorter prefixes
        for i in range(1, len(prefix)):
            shorter = prefix[i:]
            if shorter in self._chain:
                successors = self._chain[shorter]
                return self._rng.choice(successors)

        # Complete fallback
        if self._fallback_to_random:
            return self._rng.choice(_FALLBACK_CHARS)
        else:
            return " "

    def _fallback_generate(self, max_steps: int) -> Iterator[str]:
        """Fallback generator when no chain data is available."""
        chars = _FALLBACK_CHARS
        n = len(chars)
        for _ in range(max_steps):
            yield chars[self._rng.randint(0, n - 1)]

    def get_metadata(self) -> dict:
        """Return metadata about this generator."""
        return {
            "type": "markov",
            "n": self._n,
            "chain_entries": len(self._chain),
            "description": f"Character-level {self._n}-gram Markov chain generator",
        }
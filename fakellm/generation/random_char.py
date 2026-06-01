"""Pure random character generator."""

import string
from typing import Iterator, Optional

from fakellm.generation.base import BaseGenerator, InternalRequest
from fakellm.utils.randomness import get_rng

# Common Chinese characters sample for mixed output
_COMMON_CHINESE = "的一是不了人我在有他这中大来上国个到说们为子和你地出也时年得就那要下"


class RandomCharGenerator(BaseGenerator):
    """
    Generates tokens by uniformly sampling from a configurable character set.

    Each token is a single character. This is the fastest generator with no state.
    """

    def __init__(self, charset: str = "ascii+digit+common_chinese", seed: Optional[int] = None):
        """
        Initialize the random character generator.

        Args:
            charset: Character set specification. Recognized tokens:
                     'ascii', 'digit', 'punctuation', 'common_chinese'.
                     Joined with '+' to combine sets.
            seed: Optional seed for reproducibility.
        """
        self._rng = get_rng(seed)
        self._charset = self._build_charset(charset)

    @staticmethod
    def _build_charset(spec: str) -> str:
        """Build a character set string from a specification string."""
        parts = [p.strip().lower() for p in spec.split("+")]
        chars: list[str] = []
        for part in parts:
            if part in ("ascii", "ascii_letters"):
                chars.append(string.ascii_letters)
            elif part == "digit" or part == "digits":
                chars.append(string.digits)
            elif part == "punctuation":
                chars.append(string.punctuation)
            elif part == "common_chinese":
                chars.append(_COMMON_CHINESE)
            elif part:
                chars.append(part)
        return "".join(chars) if chars else string.ascii_letters + string.digits

    def generate(self, request: InternalRequest) -> Iterator[str]:
        """
        Yield random characters up to max_tokens.

        Args:
            request: The internal request object.

        Yields:
            Single characters from the configured charset.
        """
        if request.seed is not None:
            self._rng = get_rng(request.seed)

        charset = self._charset
        n_chars = len(charset)
        for _ in range(request.max_tokens):
            yield charset[self._rng.randint(0, n_chars - 1)]

    def get_metadata(self) -> dict:
        """Return metadata about this generator."""
        return {
            "type": "random_char",
            "charset_size": len(self._charset),
            "description": "Pure random character generator",
        }
"""Template-based generator: matches keywords and returns pre-written replies."""

import json
import re
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

from fakellm.generation.base import BaseGenerator, InternalRequest
from fakellm.utils.randomness import get_rng


class TemplateGenerator(BaseGenerator):
    """
    Matches user prompt against keyword patterns and returns a random pre-written reply.

    Keywords are loaded from a JSON file mapping regex patterns to lists of replies.
    Replies may contain placeholders like {random_num} which are replaced at generation time.
    """

    def __init__(
        self,
        topics_file: str = "data/topics/topics.json",
        default_reply: str = "我是一个随机模型，请提出更明确的问题。",
        seed: Optional[int] = None,
    ):
        """
        Initialize the template generator.

        Args:
            topics_file: Path to the JSON file containing topic patterns and replies.
            default_reply: Reply used when no keyword pattern matches.
            seed: Optional random seed.
        """
        self._rng = get_rng(seed)
        self._default_reply = default_reply
        self._patterns: List[Tuple[re.Pattern, List[str]]] = []
        self._load_topics(topics_file)

    def _load_topics(self, filepath: str) -> None:
        """
        Load topic patterns and replies from a JSON file.

        Args:
            filepath: Path to the topics JSON file.
        """
        if not filepath:
            # Empty path: use default reply for everything
            self._patterns = []
            return
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            # Use the default reply for everything if no topics file exists
            self._patterns = []
            return

        with open(path, "r", encoding="utf-8") as f:
            topics = json.load(f)

        for pattern_str, replies in topics.items():
            # Skip the "默认|default" entry — it's handled as the default fallback
            if pattern_str in ("默认", "default"):
                if replies and isinstance(replies, list):
                    self._default_reply = self._rng.choice(replies)
                continue

            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                self._patterns.append((compiled, replies))
            except re.error:
                # Skip invalid patterns
                continue

    def generate(self, request: InternalRequest) -> Iterator[str]:
        """
        Match the prompt against keyword patterns and yield a reply character-by-character.

        Args:
            request: The internal request.

        Yields:
            Characters of the matched (or default) reply.
        """
        if request.seed is not None:
            self._rng = get_rng(request.seed)

        prompt = request.prompt
        reply_text: Optional[str] = None

        # Try each pattern
        for pattern, replies in self._patterns:
            if pattern.search(prompt):
                reply_text = self._rng.choice(replies)
                break

        # Fall back to default
        if reply_text is None:
            reply_text = self._default_reply

        # Process placeholders
        reply_text = self._process_placeholders(reply_text)

        # Truncate to max_tokens (treating each character as a token)
        reply_text = reply_text[: request.max_tokens]

        for char in reply_text:
            yield char

    def _process_placeholders(self, text: str) -> str:
        """
        Replace placeholders like {random_num} with generated values.

        Args:
            text: The template text containing placeholders.

        Returns:
            Text with placeholders replaced.
        """
        # Replace {random_num} with a random integer
        text = text.replace("{random_num}", str(self._rng.randint(0, 1000000)))
        # Replace {random_float} with a random float
        text = text.replace("{random_float}", f"{self._rng.random():.6f}")
        return text

    def get_metadata(self) -> dict:
        """Return metadata about this generator."""
        return {
            "type": "template",
            "pattern_count": len(self._patterns),
            "description": "Keyword-pattern-based template generator",
        }
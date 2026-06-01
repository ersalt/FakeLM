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

    # Language-specific fallback charsets for auto-extend
    _EXTEND_CHARS_CN = (
        "的一是不了人我在有他这中大来上国个到说们为子和你地出也时年得就那要下"
        "会可学过发开进对能自而然此如面方所当无前后与但只于体其"
    )
    _EXTEND_CN_PUNCT = "，。！？、；：…·\n"
    _EXTEND_CHARS_EN = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    _EXTEND_EN_PUNCT = " .,!?;:\n"
    _EXTEND_DIGITS = "0123456789"

    def __init__(
        self,
        topics_file: str = "data/topics/topics.json",
        default_reply: str = "我是一个随机模型，请提出更明确的问题。",
        seed: Optional[int] = None,
        auto_extend: bool = True,
        extend_threshold: float = 0.3,
    ):
        """
        Initialize the template generator.

        Args:
            topics_file: Path to the JSON file containing topic patterns and replies.
            default_reply: Reply used when no keyword pattern matches.
            seed: Optional random seed.
            auto_extend: If True, append random chars to short replies to approach max_tokens.
            extend_threshold: Fraction of max_tokens below which auto-extend activates.
        """
        self._rng = get_rng(seed)
        self._default_reply = default_reply
        self._auto_extend = auto_extend
        self._extend_threshold = max(0.0, min(1.0, extend_threshold))
        self._patterns: List[Tuple[re.Pattern, List[str]]] = []
        self._load_topics(topics_file)

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect whether text is primarily Chinese or English."""
        cjk_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff' or '\u3000' <= c <= '\u303f')
        total = len(text) or 1
        return "cn" if cjk_count / total > 0.3 else "en"

    def _load_topics(self, filepath: str) -> None:
        """
        Load topic patterns and replies from a JSON file.

        Args:
            filepath: Path to the topics JSON file.
        """
        if not filepath:
            self._patterns = []
            return
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            self._patterns = []
            return

        with open(path, "r", encoding="utf-8") as f:
            topics = json.load(f)

        for pattern_str, replies in topics.items():
            if pattern_str in ("默认", "default"):
                if replies and isinstance(replies, list):
                    self._default_reply = self._rng.choice(replies)
                continue

            try:
                compiled = re.compile(pattern_str, re.IGNORECASE)
                self._patterns.append((compiled, replies))
            except re.error:
                continue

    def _natural_extension(self, lang: str, count: int) -> str:
        """Generate natural-looking random text in the given language.

        Produces text that mimics natural sentence structure:
        - Chinese: character sequences punctuated by ，。！？ and newlines
        - English: word-like sequences separated by spaces, punctuated with .!? and newlines
        """
        result: List[str] = []
        if lang == "cn":
            while len(result) < count:
                # Generate a clause of 3-15 characters, then a punctuation or newline
                clause_len = self._rng.randint(3, 15)
                for _ in range(min(clause_len, count - len(result))):
                    r = self._rng.random()
                    if r < 0.7:
                        c = self._EXTEND_CHARS_CN[self._rng.randint(0, len(self._EXTEND_CHARS_CN) - 1)]
                    elif r < 0.85:
                        c = self._EXTEND_DIGITS[self._rng.randint(0, len(self._EXTEND_DIGITS) - 1)]
                    else:
                        c = self._EXTEND_CN_PUNCT[self._rng.randint(0, len(self._EXTEND_CN_PUNCT) - 1)]
                    result.append(c)
                if len(result) < count:
                    # 70% chance of a Chinese comma/period, 20% newline, 10% nothing
                    r = self._rng.random()
                    if r < 0.5:
                        result.append("，")
                    elif r < 0.7:
                        result.append("。")
                    elif r < 0.9:
                        result.append("\n")
        else:
            while len(result) < count:
                # Generate a "word" of 2-8 characters, then a space or punctuation
                word_len = self._rng.randint(2, 8)
                for _ in range(min(word_len, count - len(result))):
                    r = self._rng.random()
                    if r < 0.8:
                        c = self._EXTEND_CHARS_EN[self._rng.randint(0, len(self._EXTEND_CHARS_EN) - 1)]
                    else:
                        c = self._EXTEND_DIGITS[self._rng.randint(0, len(self._EXTEND_DIGITS) - 1)]
                    result.append(c)
                if len(result) < count:
                    r = self._rng.random()
                    if r < 0.4:
                        result.append(" ")
                    elif r < 0.55:
                        result.append(". ")
                    elif r < 0.65:
                        result.append(", ")
                    elif r < 0.75:
                        result.append("\n")
                    else:
                        result.append(" ")
        return "".join(result[:count])

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

        for pattern, replies in self._patterns:
            if pattern.search(prompt):
                reply_text = self._rng.choice(replies)
                break

        if reply_text is None:
            reply_text = self._default_reply

        reply_text = self._process_placeholders(reply_text)

        max_chars = request.max_tokens

        # Auto-extend short replies with natural-looking random text
        if self._auto_extend and len(reply_text) < self._extend_threshold * max_chars:
            lang = self._detect_language(reply_text)
            extend_count = max_chars - len(reply_text)
            extension = self._natural_extension(lang, extend_count)
            if lang == "cn":
                reply_text = reply_text + "\n\n---\n*以下为自动续写的随机文本：*\n\n" + extension
            else:
                reply_text = reply_text + "\n\n---\n*Auto-generated random text follows:*\n\n" + extension

        reply_text = reply_text[:max_chars]

        for char in reply_text:
            yield char

    def _process_placeholders(self, text: str) -> str:
        """Replace placeholders like {random_num} with generated values."""
        text = text.replace("{random_num}", str(self._rng.randint(0, 1000000)))
        text = text.replace("{random_float}", f"{self._rng.random():.6f}")
        return text

    def get_metadata(self) -> dict:
        """Return metadata about this generator."""
        return {
            "type": "template",
            "pattern_count": len(self._patterns),
            "description": "Keyword-pattern-based template generator",
        }
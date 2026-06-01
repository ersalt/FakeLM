"""Unit tests for generator implementations."""

import pytest

from fakellm.generation.base import InternalRequest
from fakellm.generation.composite import CompositeGenerator
from fakellm.generation.markov import MarkovGenerator
from fakellm.generation.random_char import RandomCharGenerator
from fakellm.generation.template import TemplateGenerator


class TestRandomCharGenerator:
    """Tests for RandomCharGenerator."""

    def test_generates_correct_length(self):
        gen = RandomCharGenerator(charset="ascii+digit", seed=42)
        req = InternalRequest(prompt="hello", max_tokens=20, seed=42)
        tokens = list(gen.generate(req))
        assert len(tokens) == 20

    def test_generates_only_valid_chars(self):
        gen = RandomCharGenerator(charset="digit", seed=42)
        req = InternalRequest(max_tokens=50, seed=42)
        tokens = set(gen.generate(req))
        assert tokens <= set("0123456789")

    def test_reproducibility_with_seed(self):
        gen = RandomCharGenerator(charset="ascii", seed=42)
        req = InternalRequest(max_tokens=20, seed=42)
        run1 = "".join(gen.generate(req))
        run2 = "".join(gen.generate(req))
        assert run1 == run2

    def test_metadata(self):
        gen = RandomCharGenerator()
        meta = gen.get_metadata()
        assert meta["type"] == "random_char"
        assert meta["charset_size"] > 0


class TestTemplateGenerator:
    """Tests for TemplateGenerator."""

    def test_default_reply(self):
        gen = TemplateGenerator(topics_file="data/topics/topics.json")
        req = InternalRequest(prompt="xyzabc123", max_tokens=500)
        result = "".join(gen.generate(req))
        assert len(result) > 0

    def test_keyword_match(self):
        gen = TemplateGenerator(topics_file="data/topics/topics.json")
        req = InternalRequest(prompt="你好", max_tokens=500)
        result = "".join(gen.generate(req))
        assert len(result) > 0

    def test_empty_prompt(self):
        gen = TemplateGenerator(topics_file="data/nonexistent.json")
        req = InternalRequest(prompt="", max_tokens=100)
        result = "".join(gen.generate(req))
        assert len(result) > 0


class TestMarkovGenerator:
    """Tests for MarkovGenerator."""

    def test_fallback_when_no_chain(self):
        gen = MarkovGenerator(n=2, chain_file="data/nonexistent.json")
        req = InternalRequest(max_tokens=30)
        tokens = list(gen.generate(req))
        assert len(tokens) == 30

    def test_with_chain(self):
        gen = MarkovGenerator(n=2, chain_file="data/markov_chains/zh_2gram.json")
        req = InternalRequest(max_tokens=30, seed=42)
        tokens = list(gen.generate(req))
        assert len(tokens) == 30

    def test_metadata(self):
        gen = MarkovGenerator(n=2)
        meta = gen.get_metadata()
        assert meta["type"] == "markov"
        assert "chain_entries" in meta


class TestCompositeGenerator:
    """Tests for CompositeGenerator."""

    def test_low_intelligence_routes_to_random_char(self):
        sub = {
            "random_char": RandomCharGenerator(charset="digit"),
            "template": TemplateGenerator(topics_file="data/nonexistent.json"),
            "markov": MarkovGenerator(n=2),
        }
        gen = CompositeGenerator(sub, low_threshold=0.3, high_threshold=0.7)
        req = InternalRequest(prompt="test", max_tokens=20, intelligence=0.0)
        result = "".join(gen.generate(req))
        assert len(result) == 20

    def test_high_intelligence_routes_to_markov(self):
        sub = {
            "random_char": RandomCharGenerator(charset="digit"),
            "template": TemplateGenerator(topics_file="data/nonexistent.json"),
            "markov": MarkovGenerator(n=2),
        }
        gen = CompositeGenerator(sub, low_threshold=0.3, high_threshold=0.7)
        req = InternalRequest(prompt="test", max_tokens=20, intelligence=0.9)
        result = "".join(gen.generate(req))
        assert len(result) == 20
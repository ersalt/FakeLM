"""Generators: core text generation engines for FakeLM.

Provides the generator factory that builds the configured engine graph from AppConfig.
"""

from typing import Dict, Optional

from fakellm.config import AppConfig
from fakellm.generation.base import BaseGenerator
from fakellm.generation.composite import CompositeGenerator
from fakellm.generation.markov import MarkovGenerator
from fakellm.generation.random_char import RandomCharGenerator
from fakellm.generation.template import TemplateGenerator


def get_generator(config: AppConfig) -> BaseGenerator:
    """
    Build and return the configured generator graph.

    Reads the 'generation' section of the config, instantiates all configured
    sub-generators, and wraps them in a CompositeGenerator if requested.

    Args:
        config: The application configuration.

    Returns:
        A BaseGenerator instance ready for use.
    """
    default_engine = config.default_engine
    engines_cfg = config.engine_config

    # Build all individual generators from config
    generators: Dict[str, BaseGenerator] = {}

    # Random char generator
    rc_cfg = engines_cfg.get("random_char", {})
    generators["random_char"] = RandomCharGenerator(
        charset=rc_cfg.get("charset", "ascii+digit+common_chinese"),
    )

    # Markov generator
    mk_cfg = engines_cfg.get("markov", {})
    generators["markov"] = MarkovGenerator(
        n=mk_cfg.get("n", 2),
        chain_file=mk_cfg.get("chain_file", "data/markov_chains/zh_2gram.json"),
        fallback_to_random=mk_cfg.get("fallback_to_random", True),
    )

    # Template generator
    tp_cfg = engines_cfg.get("template", {})
    generators["template"] = TemplateGenerator(
        topics_file=tp_cfg.get("topics_file", "data/topics/topics.json"),
        default_reply=tp_cfg.get("default_reply", "我是一个随机模型，请提出更明确的问题。"),
    )

    # If default engine is composite, wrap all generators in a CompositeGenerator
    if default_engine == "composite":
        cp_cfg = engines_cfg.get("composite", {})
        return CompositeGenerator(
            generators=generators,
            low_threshold=cp_cfg.get("low_threshold", 0.3),
            high_threshold=cp_cfg.get("high_threshold", 0.7),
            low_engine=cp_cfg.get("low_engine", "random_char"),
            mid_engine=cp_cfg.get("mid_engine", "template"),
            high_engine=cp_cfg.get("high_engine", "markov"),
        )

    # Otherwise return the named single generator
    return generators.get(default_engine, generators.get("random_char", RandomCharGenerator()))
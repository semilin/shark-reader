"""Orchestrates the v2 pipeline.

One entry point (`run_pipeline`) loads the annotated JSON, builds the shared
`LLMClient` (with the core vocab cached as a system message), and dispatches
to the three phases in order. Each phase is idempotent: re-running it skips
already-finished work, so `pipeline <file>` can be re-invoked freely.

Phase exports (lemmatize / gloss / substitute) are also callable directly for
granular re-runs via `main_v2.py`.
"""

import json
import logging
import os
from typing import Any

from openai import OpenAI

from sharkreader.config import (
    CONFIGS,
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY,
    Language,
    V2_GLOSS_MODEL,
    V2_LEMMA_MODEL,
    V2_SUBSTITUTE_MODEL,
)
from sharkreader.ratelimit import RateLimitCoordinator
from sharkreader.v2 import glosser, lemmatizer, substitutor
from sharkreader.v2.llm import LLMClient
from sharkreader.v2.metrics import Metrics

logger = logging.getLogger(__name__)


def load_core_vocab(lang: Language) -> list[str]:
    """Load the core vocabulary headwords as a lowercase list.

    Imports pandas lazily so dry-runs that need only tokenizer/lemmatizer
    do not pay the pandas import cost.
    """
    import pandas as pd

    config = CONFIGS[lang]
    df = pd.read_csv(config.core_vocab)
    return df["Headword"].str.lower().tolist()


def build_client(
    openai_client: Any,
    lang: Language,
    model: str,
    *,
    phase: str,
    metrics: Metrics,
) -> LLMClient:
    """Build an `LLMClient` with core vocab pre-registered as a system message.

    The client records all token usage and cost from `response.usage`
    (OpenRouter supplies `usage.cost` directly) into `metrics` under `phase`.
    """
    from sharkreader.v2 import prompts

    config = CONFIGS[lang]
    vocab = load_core_vocab(lang)
    rate_limiter = RateLimitCoordinator()
    client = LLMClient(
        openai_client,
        model,
        phase=phase,
        metrics=metrics,
        rate_limiter=rate_limiter,
        max_attempts=DEFAULT_RETRY_ATTEMPTS,
        base_delay=DEFAULT_RETRY_BASE_DELAY,
    )
    client.add_system(prompts.core_vocab_system_block(vocab, config))
    return client


def run_pipeline(
    file_path: str,
    *,
    lang: Language,
    lemmatize: bool = True,
    gloss: bool = True,
    substitute: bool = True,
    dictionary_path: str | None = None,
    keep_cache: bool = False,
    out_path: str | None = None,
    work_type: str = "prose",
    title: str | None = None,
    author: str | None = None,
    openai_client: Any | None = None,
) -> None:
    """Run the configured phases against `file_path`, in place by default.

    Accepts either a `.annotated.json` file (existing token stream) or an
    `.xml` file (Perseus TEI). For XML input, `work_type` is required and
    the parser produces the initial token stream, which is then written to
    `out_path` (default: same stem + `.annotated.json`) before the phases run.
    """
    if openai_client is None:
        from openai import OpenAI
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise RuntimeError("OPENROUTER_API_KEY environment variable must be set")
        openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        )

    config = CONFIGS[lang]

    # XML ingestion: parse TEI into the annotated-JSON shape and persist
    # before phases run. Subsequent phases reload from disk as today.
    if file_path.lower().endswith(".xml"):
        from sharkreader.v2.xml_parser import parse_tei_xml

        data = parse_tei_xml(
            file_path, work_type=work_type, title=title, author=author
        )
        if out_path is None:
            out_path = os.path.splitext(file_path)[0] + ".annotated.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Parsed XML -> %s (%d tokens)",
                    out_path, len(data["tokens"]))
        file_path = out_path
    else:
        out_path = out_path or file_path

    metrics = Metrics()

    # Phase 1: lemmatize (its own model/role).
    any_phase_ran = False
    if lemmatize:
        client = build_client(openai_client, lang, V2_LEMMA_MODEL,
                              phase="lemmatize", metrics=metrics)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tokens = data["tokens"] if isinstance(data, dict) else data
        n = lemmatizer.lemmatize(tokens, config, client, metrics=metrics)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        metrics.record_items_processed("lemmatize", n)
        logger.info("Phase 1 (lemmatize): %d new lemmas", n)
        any_phase_ran = True

    # Phase 2: gloss (its own model/role).
    if gloss:
        client = build_client(openai_client, lang, V2_GLOSS_MODEL,
                              phase="gloss", metrics=metrics)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tokens = data["tokens"] if isinstance(data, dict) else data
        # Determine dictionary path.
        dpath = dictionary_path or (
            os.path.join(os.path.dirname(out_path), "dictionaries",
                         f"{lang}.json")
        )
        n = glosser.gloss(tokens, config, dpath, client, metrics=metrics)
        metrics.record_items_processed("gloss", n)
        logger.info("Phase 2 (gloss): %d new entries -> %s", n, dpath)
        any_phase_ran = True

    # Phase 3: substitute (its own model/role, context-sensitive).
    if substitute:
        client = build_client(openai_client, lang, V2_SUBSTITUTE_MODEL,
                              phase="substitute", metrics=metrics)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tokens = data["tokens"] if isinstance(data, dict) else data
        cache_path = file_path + ".substitutes.cache.json"
        try:
            n = substitutor.substitute(
                tokens, config, dpath if gloss else (
                    dictionary_path or
                    os.path.join(os.path.dirname(out_path), "dictionaries",
                                 f"{lang}.json")
                ),
                client,
                cache_path=cache_path,
                metrics=metrics,
            )
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            metrics.record_items_processed("substitute", n)
            logger.info("Phase 3 (substitute): %d new hints", n)
            if not keep_cache and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
        finally:
            if not keep_cache and os.path.exists(cache_path):
                try:
                    os.remove(cache_path)
                except OSError:
                    pass
        any_phase_ran = True

    if any_phase_ran:
        metrics.finish()
        print(metrics.summary())
    else:
        logger.warning("No phases selected; nothing to do")
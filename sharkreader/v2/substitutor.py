"""Phase 3: substitute hint generation (context-sensitive, deduped + batched).

Replaces the legacy per-token `glossgen.generate_substitute_gloss` path. This
is the dominant cost phase in the legacy pipeline (~10,000 calls for a
theaetetus-scale text), so the optimisations here account for the bulk of
the request-count reduction:

- **Dedup by `(lemma, surface_form, context_hash)`**: identical occurrences
  (same word in the same surrounding context) share one LLM call. Typically
  3-5x reduction on narrative/dialogue texts.
- **Batch 25 unique triples per call**: ~25x further reduction.
- **Gloss grounding**: the lemma's dictionary `definition` is read once at
  phase start and passed to the model as grounding, improving hint quality.
- **Resumability**: a sibling `<text>.substitutes.cache.json` file holds
  dedup_key -> substitute mappings and is written incrementally after each
  batch, so a crashed run can resume without rebilling processed contexts.
- The core vocabulary block lives in the cached `system` message on the
  `LLMClient`, as in phases 1 and 2.

Substitute is a hover hint (per the product spec), not a drop-in replacement
word, but it must still preserve grammatical parsing so the hint reads
naturally in context. Empty string from the model == "no suitable
substitute"; we then leave `s` unset on that token.
"""

import hashlib
import json
import logging
import os
from typing import Any

from sharkreader.config import (
    LanguageConfig,
    V2_SUBSTITUTE_BATCH_SIZE,
    V2_SUBSTITUTE_CONTEXT_WINDOW,
)
from sharkreader.tokenizer import get_word_pattern
from sharkreader.v2 import prompts, schemas
from sharkreader.v2.llm import LLMClient, LLMError
from sharkreader.v2.metrics import Metrics

logger = logging.getLogger(__name__)


class SubstituteError(Exception):
    """Raised when a substitute batch fails."""


def _load_core_vocab(config: LanguageConfig) -> set[str]:
    """Lowercased core-vocab headwords as a set for fast membership tests.

    The same list is also registered as a system message on the LLMClient
    by the orchestrator; reading the CSV again here is a one-off cost per
    phase run and keeps the substitutor self-contained.
    """
    import pandas as pd

    df = pd.read_csv(config.core_vocab)
    return set(df["Headword"].str.lower().tolist())


def _load_dictionary(dictionary_path: str) -> dict[str, Any]:
    if not os.path.exists(dictionary_path):
        return {}
    with open(dictionary_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Could not parse %s; no glosses available for grounding",
                           dictionary_path)
            return {}


def _load_cache(cache_path: str | None) -> dict[str, str]:
    """Load the resumability cache. Keys are dedup keys; values are the
    substitute string (empty string == no substitute).
    """
    if not cache_path or not os.path.exists(cache_path):
        return {}
    with open(cache_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except json.JSONDecodeError:
            logger.warning("Could not parse cache %s; starting fresh", cache_path)
    return {}


def _dump_cache(cache_path: str, cache: dict[str, str]) -> None:
    tmp = cache_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False)
    os.replace(tmp, cache_path)


def _clean_surface(raw: str, word_pattern) -> str:
    return word_pattern.sub("", raw)


def _context_string(tokens: list[dict], idx: int, window: int) -> str:
    """Build a ±`window` token context string around the token at `idx`.

    Includes word and punctuation tokens; newlines, markers, and speakers
    are dropped for a clean prose window (mirrors the legacy context builder
    at main.py:462-473, widened from window=5 to window=9).
    """
    start = max(0, idx - window)
    end = min(len(tokens), idx + window + 1)
    parts: list[str] = []
    for j in range(start, end):
        t = tokens[j]
        if t.get("t") == "w":
            parts.append(t.get("w", ""))
        elif t.get("t") == "p":
            parts.append(t.get("w", ""))
    return " ".join(parts)


def _dedup_key(lemma: str, surface: str, context: str) -> str:
    """Stable dedup key: `lemma|surface|ctx[:8]`. Same word in the same
    surrounding context -> one LLM call.
    """
    ctx_hash = hashlib.sha1(context.encode("utf-8")).hexdigest()[:8]
    return f"{lemma}|{surface}|{ctx_hash}"


def _is_eligible(token: dict, vocab_set: set[str]) -> bool:
    """A token is eligible for substitution if it is a word token with a
    lemma, not already a substitute hint, not in core vocab, and not a
    proper noun (capitalised surface form in Latin/Greek).
    """
    if token.get("t") != "w":
        return False
    lemma = token.get("l")
    if not lemma:
        return False
    if token.get("s"):
        return False  # resumability: skip already-annotated tokens
    if lemma.lower() in vocab_set:
        return False
    raw = token.get("w", "")
    if raw and raw[0].isupper():
        return False
    return True


def substitute(
    tokens: list[dict],
    config: LanguageConfig,
    dictionary_path: str,
    client: LLMClient,
    *,
    cache_path: str | None = None,
    window: int = V2_SUBSTITUTE_CONTEXT_WINDOW,
    batch_size: int = V2_SUBSTITUTE_BATCH_SIZE,
    metrics: Metrics | None = None,
) -> int:
    """Generate per-token `s` substitute hints in place.

    Returns the number of tokens that received a non-empty substitute.
    Idempotent: tokens already bearing an `s` field are skipped. Resumable:
    if `cache_path` is given, dedup_key -> substitute mappings are loaded
    from and written to that file so an interrupted run resumes without
    rebilling processed contexts.
    """
    word_pattern = get_word_pattern(config.word_pattern)
    vocab_set = _load_core_vocab(config)
    dictionary = _load_dictionary(dictionary_path)
    cache = _load_cache(cache_path)

    # Walk all tokens once: build the dedup index and collect pending keys.
    # key_to_tokens: dedup_key -> [token_idx, ...]   (every occurrence)
    # key_to_payload: dedup_key -> {word, lemma, context, definition}
    # pending_keys:  dedup_keys not yet resolved by the cache, in first-seen order
    key_to_tokens: dict[str, list[int]] = {}
    key_to_payload: dict[str, dict[str, Any]] = {}
    pending_keys: list[str] = []

    for i, token in enumerate(tokens):
        if not _is_eligible(token, vocab_set):
            continue
        lemma = token["l"]
        surface = _clean_surface(token.get("w", ""), word_pattern)
        if not surface:
            continue
        context = _context_string(tokens, i, window)
        key = _dedup_key(lemma, surface, context)

        if key not in key_to_tokens:
            key_to_tokens[key] = []
            key_to_payload[key] = {
                "word": surface,
                "lemma": lemma,
                "context": context,
                "definition": dictionary.get(lemma, {}).get("definition"),
            }
            if key not in cache:
                pending_keys.append(key)
        key_to_tokens[key].append(i)

    if not key_to_tokens:
        logger.info("substitute: no eligible tokens")
        return 0

    total_occurrences = sum(len(v) for v in key_to_tokens.values())
    logger.info(
        "substitute: %d eligible occurrences -> %d unique triples "
        "(cache covers %d, %d pending), batch=%d -> up to %d calls",
        total_occurrences, len(key_to_tokens), len(cache),
        len(pending_keys), batch_size,
        (len(pending_keys) + batch_size - 1) // batch_size if pending_keys else 0,
    )

    applied = 0

    # Apply cached substitutes first (no LLM cost) and count them as cache hits.
    for key, idxs in key_to_tokens.items():
        if key in cache:
            sub = cache[key]
            if sub:
                for ti in idxs:
                    tokens[ti]["s"] = sub
                applied += len(idxs)
            if metrics is not None:
                metrics.record_cache_hit("substitute", len(idxs))

    # Process pending keys in batches of `batch_size`. Use a numeric
    # positional index for the LLM (the schema's `index` is an integer)
    # and map back to the dedup key via `batch_keys`.
    for start in range(0, len(pending_keys), batch_size):
        batch_keys = pending_keys[start:start + batch_size]
        triples = [
            {
                "index": pos,          # numeric position within this batch
                "word": key_to_payload[k]["word"],
                "lemma": key_to_payload[k]["lemma"],
                "context": key_to_payload[k]["context"],
                "definition": key_to_payload[k]["definition"],
            }
            for pos, k in enumerate(batch_keys)
        ]

        try:
            response = client.query(
                prompts.substitute_user_prompt(triples, config),
                schemas.SUBSTITUTE_SCHEMA,
            )
        except LLMError as e:
            raise SubstituteError(
                f"Batch starting at pending key {batch_keys[0]!r} failed: {e}"
            ) from e

        results = response.get("results", [])
        by_index = {r.get("index"): r for r in results}

        for pos, key in enumerate(batch_keys):
            entry = by_index.get(pos)
            sub_raw = ""
            if entry is not None:
                sub_raw = str(entry.get("substitute", "")).strip()
            # Enforce the 3-words-or-fewer rule in defence in depth.
            if sub_raw and len(sub_raw.split()) > 3:
                logger.warning(
                    "substitute: '%s' for %r exceeds 3 words; dropping",
                    sub_raw, key,
                )
                sub_raw = ""
            cache[key] = sub_raw
            if sub_raw:
                for ti in key_to_tokens[key]:
                    tokens[ti]["s"] = sub_raw
                applied += len(key_to_tokens[key])

        # Incremental cache flush so a crash loses <= batch_size entries.
        if cache_path:
            _dump_cache(cache_path, cache)

        logger.info(
            "substitute: batch %d/%d done (%d tokens annotated so far)",
            start // batch_size + 1,
            (len(pending_keys) + batch_size - 1) // batch_size,
            applied,
        )

    logger.info("substitute: %d tokens annotated", applied)
    return applied
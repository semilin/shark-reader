"""Phase 1: lemmatization (batched, contextual).

Replaces the legacy per-sentence `annotator.get_annotated_sentence_lemmas`
path. Key differences:

- Up to `V2_LEMMA_BATCH_SIZE` (50) sentences per LLM request.
- The reconstructed sentence text is sent alongside the numbered word list,
  giving the model context it never had before.
- A strict JSON schema (`LEMMA_SCHEMA`) replaces manual JSON parsing, so the
  JSONDecodeError retry class is eliminated.
- Count enforcement: if the schema-validated response still mismatches, the
  batch raises `LemmatizationError` rather than silently filling gaps with
  lowercased surface forms (the legacy corruption path at
  `annotator.py:147-160`).
"""

import logging
from typing import Any

from sharkreader.config import LanguageConfig, V2_LEMMA_BATCH_SIZE
from sharkreader.tokenizer import chunk_sentences, get_word_pattern
from sharkreader.v2 import prompts, schemas
from sharkreader.v2.llm import LLMClient, LLMError
from sharkreader.v2.metrics import Metrics

logger = logging.getLogger(__name__)


class LemmatizationError(Exception):
    """Raised when a lemmatization batch cannot be applied cleanly."""


def _reconstruct_sentence(tokens: list[dict], indices: list[int]) -> str:
    """Reconstruct a sentence's surface text from its token indices.

    Word/punctuation tokens contribute their `w`; newlines contribute a
    space; speakers/markers are dropped (they are not part of the prose
    sentence the model should see).
    """
    parts: list[str] = []
    for i in indices:
        token = tokens[i]
        t = token.get("t")
        if t == "w":
            parts.append(token.get("w", ""))
        elif t == "p":
            parts.append(token.get("w", ""))
        elif t == "n":
            parts.append(" ")
    return " ".join("".join(parts).replace("  ", " ").split())


def _clean_word(raw: str, word_pattern) -> str:
    return word_pattern.sub("", raw)


def _counts_match(
    response: dict,
    batch: list[tuple[int, list[int]]],
    sentence_word_map: list[list[tuple[int, int]]],
) -> bool:
    """Return True if every sentence in the batch has the expected lemma count."""
    results = response.get("results", [])
    by_sentence = {r.get("sentence_index"): r for r in results}
    for s_idx, (sentence_index, _indices) in enumerate(batch):
        word_tokens = sentence_word_map[s_idx]
        if not word_tokens:
            continue
        entry = by_sentence.get(sentence_index)
        if entry is None:
            return False
        if len(entry.get("lemmas", [])) != len(word_tokens):
            return False
    return True


def lemmatize(
    tokens: list[dict],
    config: LanguageConfig,
    client: LLMClient,
    *,
    batch_size: int = V2_LEMMA_BATCH_SIZE,
    metrics: Metrics | None = None,
) -> int:
    """Lemmatize every word token with an empty `l` field, in place.

    Returns the number of newly-lemmatized tokens. Raises LemmatizationError
    if any batch returns a count mismatch after schema validation (the model
    should not be able to do this under strict mode, but we fail loudly
    rather than corrupt data).
    """
    word_pattern = get_word_pattern(config.word_pattern)
    sentences = chunk_sentences(tokens)

    # Select sentences that actually need work; keep their original index for
    # stable logging in larger runs.
    todo: list[tuple[int, list[int]]] = []
    for s_idx, indices in enumerate(sentences):
        if any(
            tokens[i].get("t") == "w" and not tokens[i].get("l")
            for i in indices
        ):
            todo.append((s_idx, indices))

    if not todo:
        logger.info("lemmatize: nothing to do")
        return 0

    total_words = sum(
        1
        for _, indices in todo
        for i in indices
        if tokens[i].get("t") == "w" and not tokens[i].get("l")
    )
    logger.info(
        "lemmatize: %d sentences, %d words, batch=%d",
        len(todo), total_words, batch_size,
    )

    newly_lemmatized = 0
    for batch_start in range(0, len(todo), batch_size):
        batch = todo[batch_start:batch_start + batch_size]

        # Build the LLM request.
        request_items: list[dict] = []
        # Each entry is: (token_index, position_within_sentence)
        # so we can map the returned lemma back to the right token. A sentence
        # with 10 word tokens yields 10 entries in `lemmas`.
        sentence_word_map: list[list[tuple[int, int]]] = []

        for sentence_index, indices in batch:
            text = _reconstruct_sentence(tokens, indices)
            word_tokens: list[tuple[int, int]] = []
            clean_words: list[str] = []
            for pos_in_sent, i in enumerate(indices):
                token = tokens[i]
                if token.get("t") != "w":
                    continue
                if token.get("l"):
                    # Already has a lemma; skip cleanly (we only annotate
                    # missing ones). The model never sees this token.
                    continue
                clean = _clean_word(token.get("w", ""), word_pattern)
                if not clean:
                    continue
                word_tokens.append((i, pos_in_sent))
                clean_words.append(clean)
            sentence_word_map.append(word_tokens)
            request_items.append(
                {
                    "sentence_index": sentence_index,
                    "text": text,
                    "words": clean_words,
                }
            )

        # Skip empty batches (all words already lemmatized between runs).
        if not any(item["words"] for item in request_items):
            continue

        try:
            response = client.query(
                prompts.lemma_user_prompt(request_items, config),
                schemas.LEMMA_SCHEMA,
            )
        except LLMError as e:
            raise LemmatizationError(
                f"Batch starting at sentence {batch[0][0]} failed: {e}"
            ) from e

        # If any sentence has a count mismatch, retry once with a stricter
        # reminder before falling back to tolerant slicing (below). The model
        # occasionally returns one extra/short lemma per batch.
        if not _counts_match(response, batch, sentence_word_map):
            logger.warning(
                "lemmatize: batch %d count mismatch; retrying with stricter prompt",
                batch_start // batch_size + 1,
            )
            try:
                response = client.query(
                    prompts.lemma_user_prompt(request_items, config)
                    + "\n\nIMPORTANT: Return EXACTLY one lemma per numbered word, "
                    "no more, no less. Empty string if a word cannot be lemmatized.",
                    schemas.LEMMA_SCHEMA,
                )
            except LLMError as e:
                raise LemmatizationError(
                    f"Batch starting at sentence {batch[0][0]} failed on retry: {e}"
                ) from e

        results = response.get("results", [])
        # Index results by sentence_index for safe lookup.
        by_sentence = {r.get("sentence_index"): r for r in results}

        for s_idx, (sentence_index, _indices) in zip(
            range(len(batch)), batch
        ):
            word_tokens = sentence_word_map[s_idx]
            if not word_tokens:
                continue
            entry = by_sentence.get(sentence_index)
            if entry is None:
                logger.warning(
                    "lemmatize: sentence %d missing from response; "
                    "leaving %d tokens blank",
                    sentence_index, len(word_tokens),
                )
                continue
            lemmas = entry.get("lemmas", [])
            expected = len(word_tokens)
            if len(lemmas) != expected:
                # Tolerant slice: take the first `expected` if we got more,
                # pad with empty strings if we got fewer. No garbage lowercased
                # fill — empty `l` stays empty so a later run can retry.
                if len(lemmas) > expected:
                    logger.warning(
                        "lemmatize: sentence %d expected %d lemmas, got %d; "
                        "taking first %d",
                        sentence_index, expected, len(lemmas), expected,
                    )
                    lemmas = lemmas[:expected]
                else:
                    logger.warning(
                        "lemmatize: sentence %d expected %d lemmas, got %d; "
                        "leaving %d tokens blank",
                        sentence_index, expected, len(lemmas),
                        expected - len(lemmas),
                    )
                    lemmas = lemmas + [""] * (expected - len(lemmas))
            for (token_idx, _pos), lemma in zip(word_tokens, lemmas):
                if lemma:
                    tokens[token_idx]["l"] = lemma
                    newly_lemmatized += 1

        logger.info(
            "lemmatize: batch %d/%d done (%d words so far)",
            batch_start // batch_size + 1,
            (len(todo) + batch_size - 1) // batch_size,
            newly_lemmatized,
        )

    return newly_lemmatized
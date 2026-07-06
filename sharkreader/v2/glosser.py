"""Phase 2: gloss generation (batched per lemma).

Replaces the legacy per-lemma `glossgen.generate_gloss` path. Key differences:

- Up to `V2_GLOSS_BATCH_SIZE` (20) lemmas per LLM request.
- The core vocabulary block lives in a cached `system` message on the
  `LLMClient`, so it is not re-sent on every request (saves ~5-10 KB input
  per call vs the legacy per-lemma prompt).
- A strict JSON schema (`GLOSS_SCHEMA`) replaces manual JSON parsing, and
  `examples.maxItems=2` structurally enforces the "1-2 examples, second only
  for a genuinely distinct sense" rule from the product spec.
- The dictionary is loaded once, updated in memory, and dumped once at the
  end (the legacy path also did this; preserved).
"""

import json
import logging
import os
from typing import Any

from sharkreader.config import LanguageConfig, V2_GLOSS_BATCH_SIZE
from sharkreader.v2 import prompts, schemas
from sharkreader.v2.llm import LLMClient, LLMError
from sharkreader.v2.metrics import Metrics

logger = logging.getLogger(__name__)


class GlossError(Exception):
    """Raised when a gloss batch fails."""


def _load_dictionary(dictionary_path: str) -> dict[str, Any]:
    if not os.path.exists(dictionary_path):
        return {}
    with open(dictionary_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Could not parse %s; starting fresh", dictionary_path)
            return {}


def _collect_missing_lemmas(tokens: list[dict], dictionary: dict) -> list[str]:
    """Return the sorted unique lemmas that occur in `tokens` but are not yet
    in `dictionary`. Excludes empty lemmas (untokenized / unannotated).
    """
    encountered: set[str] = set()
    for t in tokens:
        if t.get("t") == "w":
            lemma = t.get("l")
            if lemma:
                encountered.add(lemma)
    missing = sorted(l for l in encountered if l not in dictionary)
    return missing


def gloss(
    tokens: list[dict],
    config: LanguageConfig,
    dictionary_path: str,
    client: LLMClient,
    *,
    batch_size: int = V2_GLOSS_BATCH_SIZE,
    metrics: Metrics | None = None,
) -> int:
    """Generate dictionary glosses for lemmas not yet in `dictionary_path`.

    Persists the updated dictionary to disk. Returns the number of new
    entries appended. Idempotent: re-running skips lemmas already present.
    """
    dictionary = _load_dictionary(dictionary_path)
    missing = _collect_missing_lemmas(tokens, dictionary)

    if not missing:
        logger.info("gloss: nothing to do (dictionary has all %d lemmas)",
                    len(dictionary))
        return 0

    logger.info("gloss: %d new lemmas, batch=%d -> %d calls",
                len(missing), batch_size,
                (len(missing) + batch_size - 1) // batch_size)

    new_entries = 0
    for start in range(0, len(missing), batch_size):
        batch = missing[start:start + batch_size]
        try:
            response = client.query(
                prompts.gloss_user_prompt(batch, config),
                schemas.GLOSS_SCHEMA,
            )
        except LLMError as e:
            raise GlossError(
                f"Batch starting at lemma {batch[0]!r} failed: {e}"
            ) from e

        results = response.get("results", [])
        # Index by lemma for safe lookup.
        by_lemma = {r.get("lemma"): r for r in results}

        for lemma in batch:
            entry = by_lemma.get(lemma)
            if entry is None:
                logger.warning(
                    "gloss: model response missing lemma %r; skipping",
                    lemma,
                )
                continue
            definition = str(entry.get("definition", "")).strip()
            if not definition:
                logger.warning(
                    "gloss: empty definition for %r; skipping", lemma,
                )
                continue
            examples_raw = entry.get("examples", [])
            examples = [str(ex) for ex in examples_raw if str(ex).strip()]
            # Schema enforces maxItems=2 already, but defend in depth.
            examples = examples[:2]
            synonyms_raw = entry.get("synonyms", [])
            synonyms = [str(s) for s in synonyms_raw if str(s).strip()][:2]
            dictionary[lemma] = {
                "definition": definition,
                "examples": examples,
                "synonyms": synonyms,
            }
            new_entries += 1

        logger.info(
            "gloss: batch %d/%d done (%d new entries so far)",
            start // batch_size + 1,
            (len(missing) + batch_size - 1) // batch_size,
            new_entries,
        )

    # Persist once at the end.
    os.makedirs(os.path.dirname(dictionary_path) or ".", exist_ok=True)
    with open(dictionary_path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=2)
    logger.info("gloss: wrote %d total entries to %s",
                len(dictionary), dictionary_path)
    return new_entries
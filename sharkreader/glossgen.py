"""Gloss generation with retry logic and error handling."""

import json
import logging
import time
from typing import Any

from sharkreader.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY,
    GLOSS_MODEL,
    SUBSTITUTE_MODEL,
    LanguageConfig,
)
from sharkreader.ratelimit import RateLimitCoordinator

logger = logging.getLogger(__name__)

# Timeout for API calls in seconds
API_TIMEOUT = 60.0


class GlossGenerationError(Exception):
    """Raised when gloss generation fails after all retries."""

    pass


class GlossGenerationTimeout(GlossGenerationError):
    """Raised when gloss generation times out."""

    pass


def query_llm_with_retry(
    prompt: str,
    model: str,
    client: Any,
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
    rate_limiter: RateLimitCoordinator | None = None,
) -> dict[str, Any]:
    """Query the LLM with exponential backoff retry logic."""
    from openai import BadRequestError, RateLimitError

    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            if rate_limiter is not None:
                rate_limiter.acquire()

            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=API_TIMEOUT,
            )
            content = response.choices[0].message.content

            try:
                result = json.loads(content)
                if rate_limiter is not None:
                    rate_limiter.report_success()
                return result
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Attempt {attempt + 1}: Invalid JSON response, retrying..."
                )
                last_error = e
                if attempt < max_attempts - 1:
                    time.sleep(base_delay * (2**attempt))
                    continue
                raise GlossGenerationError(
                    f"Invalid JSON response after {max_attempts} attempts"
                ) from e

        except RateLimitError as e:
            logger.warning(f"Attempt {attempt + 1}: Rate limited, retrying...")
            last_error = e
            if rate_limiter is not None:
                rate_limiter.report_rate_limit()
            if attempt < max_attempts - 1:
                continue

        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                logger.warning(f"Attempt {attempt + 1}: Request timed out, retrying...")
                last_error = GlossGenerationTimeout(f"Request timed out: {e}")
            else:
                logger.warning(f"Attempt {attempt + 1}: Error {type(e).__name__}: {e}")
                last_error = e

            if attempt < max_attempts - 1:
                delay = base_delay * (2**attempt)
                time.sleep(delay)
                continue

    raise GlossGenerationError(
        f"Failed after {max_attempts} attempts: {last_error}"
    ) from last_error


def validate_gloss_response(response: Any) -> dict[str, Any]:
    """Validate the gloss response has required fields."""
    if not isinstance(response, dict):
        raise GlossGenerationError(
            f"Expected dict response, got {type(response).__name__}"
        )

    if "definition" not in response:
        raise GlossGenerationError("Missing 'definition' field in response")

    if "examples" not in response:
        raise GlossGenerationError("Missing 'examples' field in response")

    if not isinstance(response["examples"], list):
        raise GlossGenerationError("'examples' must be a list")

    if "synonyms" in response and not isinstance(response["synonyms"], list):
        raise GlossGenerationError("'synonyms' must be a list")

    return {
        "definition": str(response["definition"]),
        "examples": [str(ex) for ex in response["examples"]],
        "synonyms": [str(syn) for syn in response["synonyms"]]
        if "synonyms" in response
        else [],
    }


def generate_gloss(
    word: str,
    config: LanguageConfig,
    vocab_list: list[str],
    client: Any,
    rate_limiter: RateLimitCoordinator | None = None,
) -> dict[str, Any]:
    """Generate an immersive gloss for a word using core vocabulary."""
    vocab_str = "\n".join(vocab_list)

    prompt = (
        f"# CORE VOCABULARY\n{vocab_str}\n"
        f"# DIRECTIONS\nGenerate an immersive {config.name} gloss for the given {config.name} word. "
        f"The definition should, in a simple sentence or two, explain the meaning of the word using primarily the vocab words provided in the CORE VOCABULARY. The first sentence should explain the most basic usage of the word in as concise a manner possible. If necessary, a second sentence can be written to supply additional nuance and detail about the word. If there are words outside the core vocab which are highly relevant to the defined word, you may use them; still, prioritize core vocabulary. Use proper grammar -- if the word to be defined is not a noun, treat it as a substantive for the purpose of definition (e.g., verbs should be defined as a substantive infinitive)."
        f"Further, generate 2-3 example sentences using the word that cover its basic usage and give extra context to the definition (again, using primarily core vocab words or common {config.name} names). "
        f"Finally, generate 0-2 close synonyms to the word in their primary principle part. If there are no synonyms that are very close, the list should be empty. "
        f"Each example should use the word in a different form. Respond with JSON. "
        f'For example, if the word were "{config.example_word}", respond with {config.example_response}.\n'
        f"The word is: {word}."
    )

    response = query_llm_with_retry(
        prompt, GLOSS_MODEL, client, rate_limiter=rate_limiter
    )
    return validate_gloss_response(response)


def generate_substitute_gloss(
    word: str,
    lemma: str,
    context: str,
    config: LanguageConfig,
    vocab_list: list[str],
    client: Any,
    rate_limiter: RateLimitCoordinator | None = None,
) -> str | None:
    """
    Generate a minimal substitute gloss: a simpler word or short phrase (<=3 words)
    that can replace the given word in context, preserving grammatical parsing.

    Skips core vocabulary words and proper nouns. Returns None if no suitable
    substitute exists or the word is too nuanced for a simple substitution.
    """
    # Skip core vocabulary words (already common)
    if lemma.lower() in vocab_list:
        return None

    # Skip proper nouns (capitalized in Latin or Greek)
    if word and word[0].isupper():
        return None

    vocab_str = "\n".join(vocab_list)

    prompt = (
        f"# CORE VOCABULARY\n{vocab_str}\n"
        f"# DIRECTIONS\n"
        f"You are given a word in {config.name} that appears in a specific context. "
        f"Determine whether this word can be replaced by a SIMPLER {config.name} word or short phrase (no more than 3 words) "
        f"that preserves the same grammatical parsing (same person, number, tense, mood, voice, case, etc.).\n\n"
        f"RULES:\n"
        f"1. The substitute MUST be simpler and more common than the original word.\n"
        f"2. The substitute MUST preserve the exact same grammatical parsing.\n"
        f"3. The substitute must be 3 words or fewer.\n"
        f"4. Example: \u1f24\u03bd\u03b4\u03b1\u03bd\u03b5 (imperfect active indicative 3sg of \u1f01\u03bd\u03b4\u03ac\u03bd\u03c9) could become \u1f24\u03c1\u03b5\u03c3\u03ba\u03b5 (imperfect active indicative 3sg of \u1f00\u03c1\u03ad\u03c3\u03ba\u03c9).\n"
        f"5. If the word is already common, return null.\n"
        f"6. If the meaning is too nuanced to capture in 3 words or fewer, return null.\n"
        f"7. If no suitable substitute exists, return null.\n\n"
        f"WORD: {word}\n"
        f"LEMMA: {lemma}\n"
        f"CONTEXT: {context}\n\n"
        f'Respond with JSON: {{ "substitute": string | null }}'
    )

    try:
        response = query_llm_with_retry(
            prompt, SUBSTITUTE_MODEL, client, rate_limiter=rate_limiter
        )
        substitute = response.get("substitute")
        if substitute and isinstance(substitute, str) and len(substitute.split()) <= 3:
            return substitute
        return None
    except GlossGenerationError:
        logger.warning(f"Failed to generate substitute for '{word}' (lemma: {lemma})")
        return None

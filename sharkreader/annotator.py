"""Text annotation (lemmatization) with error handling."""

import json
import logging
import re
from typing import Any

from sharkreader.config import ANNOTATION_MODEL, LanguageConfig
from sharkreader.tokenizer import get_word_pattern

logger = logging.getLogger(__name__)


class AnnotationError(Exception):
    """Raised when annotation fails."""

    pass


def query_llm(prompt: str, model: str, client: Any) -> dict[str, Any]:
    """Query the LLM with retry logic."""
    from openai import BadRequestError, RateLimitError

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        raise AnnotationError(f"Invalid JSON response from LLM") from e


def validate_lemma_response(response: Any, expected_count: int) -> list[dict[str, str]]:
    """Validate and extract lemmas from LLM response."""
    if not isinstance(response, dict):
        raise AnnotationError(f"Expected dict response, got {type(response).__name__}")

    lemmas_list: list[dict[str, str]] = []

    # Try to find the lemmas list
    if "lemmas" in response:
        lemmas_list = response["lemmas"]
    else:
        # Fallback: find any list in the object
        for val in response.values():
            if isinstance(val, list):
                lemmas_list = val
                break

    if not lemmas_list:
        raise AnnotationError("No lemmas list found in response")

    # Validate and normalize the lemmas
    valid_lemmas: list[dict[str, str]] = []
    for item in lemmas_list:
        if isinstance(item, dict) and "l" in item:
            valid_lemmas.append(
                {
                    "w": item.get("w", ""),
                    "l": item.get("l", ""),
                }
            )
        elif isinstance(item, str):
            valid_lemmas.append({"w": "", "l": item})

    return valid_lemmas


def get_annotated_sentence_lemmas(
    words_list: list[str],
    config: LanguageConfig,
    client: Any,
    word_pattern: re.Pattern,
) -> list[dict[str, str]]:
    """Sends a discrete list of words to the LLM for lemmatization."""
    if not words_list:
        return []

    # Clean words of punctuation before sending to LLM
    clean_words = [word_pattern.sub("", w) for w in words_list]
    clean_words = [w for w in clean_words if w]  # Remove empty strings

    if not clean_words:
        return []

    # Formulate a prompt that asks for a 1:1 mapping
    words_input = "\n".join([f"{i + 1}. {w}" for i, w in enumerate(clean_words)])

    prompt = (
        f"Context: {config.name} literature.\n"
        f"Directions: Lemmatize each word in the following list. You MUST provide a lemma for EVERY numbered item. "
        f"Lemmas never include punctuation. Periods, commas, apostrophes, etc. should be omitted. "
        f"Return a JSON object with a 'lemmas' key containing a list of objects, each with 'w' (the input word) and 'l' (the lemma).\n"
        f"{config.lemma_instructions}\n"
        f"Words to lemmatize:\n{words_input}"
    )

    try:
        res = query_llm(prompt, ANNOTATION_MODEL, client)
        lemmas = validate_lemma_response(res, len(clean_words))

        # Handle count mismatch with positional fallback
        if len(lemmas) != len(clean_words):
            logger.warning(
                f"LLM returned {len(lemmas)} lemmas for {len(clean_words)} words. "
                f"Filling gaps..."
            )
            final_lemmas: list[dict[str, str]] = []
            for i in range(len(clean_words)):
                if i < len(lemmas):
                    final_lemmas.append(lemmas[i])
                else:
                    final_lemmas.append(
                        {"w": clean_words[i], "l": clean_words[i].lower()}
                    )
            return final_lemmas

        return lemmas

    except Exception as e:
        logger.error(f"Annotation error: {e}")
        return [{"w": w, "l": w.lower()} for w in clean_words]


def is_sentence_end(token: dict, sentence_end_chars: str = ".?;·") -> bool:
    """Check if a token ends a sentence."""
    word = token.get("w", "")
    # Check standalone punctuation tokens
    if token["t"] == "p":
        return any(c in word for c in sentence_end_chars)
    # Check punctuation at end of word tokens
    if token["t"] == "w":
        return any(word.endswith(c) for c in sentence_end_chars)
    return False


def chunk_sentences(
    tokens: list[dict], sentence_end_chars: str = ".?;·"
) -> list[list[int]]:
    """Chunk tokens into sentences based on punctuation."""
    sentences: list[list[int]] = []
    current_sentence_indices: list[int] = []

    for i, token in enumerate(tokens):
        current_sentence_indices.append(i)
        if is_sentence_end(token, sentence_end_chars):
            sentences.append(current_sentence_indices)
            current_sentence_indices = []

    if current_sentence_indices:
        sentences.append(current_sentence_indices)

    return sentences

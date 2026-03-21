"""Gloss generation with retry logic and error handling."""

import json
import logging
import time
from typing import Any

from sharkreader.config import (
    DEFAULT_RETRY_ATTEMPTS,
    DEFAULT_RETRY_BASE_DELAY,
    GLOSS_MODEL,
    LanguageConfig,
)

logger = logging.getLogger(__name__)


class GlossGenerationError(Exception):
    """Raised when gloss generation fails after all retries."""
    pass


def query_llm_with_retry(
    prompt: str,
    model: str,
    client: Any,
    max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
    base_delay: float = DEFAULT_RETRY_BASE_DELAY,
) -> dict[str, Any]:
    """Query the LLM with exponential backoff retry logic."""
    from openai import BadRequestError, RateLimitError
    
    last_error: Exception | None = None
    
    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            
            try:
                return json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt + 1}: Invalid JSON response, retrying...")
                last_error = e
                if attempt < max_attempts - 1:
                    time.sleep(base_delay * (2 ** attempt))
                    continue
                raise GlossGenerationError(
                    f"Invalid JSON response after {max_attempts} attempts"
                ) from e
                
        except RateLimitError as e:
            logger.warning(f"Attempt {attempt + 1}: Rate limited, retrying...")
            last_error = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
                continue
                
        except BadRequestError as e:
            logger.error(f"Bad request: {e}")
            raise GlossGenerationError(f"Bad request: {e}") from e
            
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}: Error {type(e).__name__}: {e}")
            last_error = e
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
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
    
    return {
        "definition": str(response["definition"]),
        "examples": [str(ex) for ex in response["examples"]],
    }


def generate_gloss(
    word: str,
    config: LanguageConfig,
    vocab_list: list[str],
    client: Any,
) -> dict[str, Any]:
    """Generate an immersive gloss for a word using core vocabulary."""
    vocab_str = "\n".join(vocab_list)
    
    prompt = (
        f"# CORE VOCABULARY\n{vocab_str}\n"
        f"# DIRECTIONS\nGenerate an immersive {config.name} gloss for the given {config.name} word. "
        f"The definition should, in a simple sentence or two, explain the meaning of the word using ONLY the vocab words provided in the CORE VOCABULARY. "
        f"Further, generate 2-4 example sentences using the word that cover its basic usage and give extra context to the definition (again, using only core vocab words or common {config.name} names). "
        f"Each example should use the word in a different form. Respond with JSON. "
        f'For example, if the word were "{config.example_word}", respond with {config.example_response}.\n'
        f"The word is: {word}."
    )
    
    response = query_llm_with_retry(prompt, GLOSS_MODEL, client)
    return validate_gloss_response(response)

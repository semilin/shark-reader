"""Shared LLM client for the v2 pipeline.

Provides a single retry path with strict JSON schema responses and an
in-process system-message cache so large boilerplate (e.g. the core
vocabulary list) lives in a `system` message and is not re-sent on every
request.
"""

import json
import logging
import time
from typing import Any

from openai import BadRequestError, RateLimitError

from sharkreader.config import DEFAULT_RETRY_ATTEMPTS, DEFAULT_RETRY_BASE_DELAY, V2_API_TIMEOUT
from sharkreader.ratelimit import RateLimitCoordinator
from sharkreader.v2.metrics import Metrics

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM request fails after all retries."""


class LLMClient:
    """OpenAI-compatible client wrapper with retry, rate limiting, and a
    per-process system-message cache.

    Registered system messages persist for the lifetime of the client and are
    prepended to every `query()` call, so callers never need to re-attach the
    core vocabulary block, model role instructions, etc.

    All token usage and cost metrics captured during `query()` calls are
    recorded onto the `metrics` instance under the `phase` slot. Phases that
    skip LLM work because of a cache or predicate call
    `metrics.record_cache_hit(...)` directly.
    """

    def __init__(
        self,
        client: Any,
        model: str,
        *,
        phase: str,
        metrics: Metrics,
        rate_limiter: RateLimitCoordinator | None = None,
        max_attempts: int = DEFAULT_RETRY_ATTEMPTS,
        base_delay: float = DEFAULT_RETRY_BASE_DELAY,
        timeout: float = V2_API_TIMEOUT,
    ) -> None:
        self._client = client
        self._model = model
        self._phase = phase
        self._metrics = metrics
        self._rate_limiter = rate_limiter
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._timeout = timeout
        self._system_messages: list[dict[str, str]] = []

    def add_system(self, text: str) -> None:
        """Register a system message (cached for the lifetime of this client)."""
        self._system_messages.append({"role": "system", "content": text})

    def query(
        self,
        user_text: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Send a single user message and return the parsed JSON object.

        The response shape is enforced by `schema` via OpenRouter's strict
        json_schema response format (mapped to Gemini responseSchema). Raises
        LLMError on persistent failure. Records token-usage and cost metrics
        from `response.usage` (OpenRouter's `usage.cost` is read directly when
        present; otherwise cost accumulates as 0.0).
        """
        target_model = model or self._model
        messages = list(self._system_messages) + [
            {"role": "user", "content": user_text}
        ]
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.get("$id", "response"),
                "strict": True,
                "schema": schema,
            },
        }

        last_error: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                if self._rate_limiter is not None:
                    self._rate_limiter.acquire()
                response = self._client.chat.completions.create(
                    model=target_model,
                    messages=messages,
                    response_format=response_format,
                    timeout=self._timeout,
                )
                content = response.choices[0].message.content
                result = json.loads(content)
                if self._rate_limiter is not None:
                    self._rate_limiter.report_success()
                self._record_usage(response)
                return result
            except RateLimitError as e:
                logger.warning(f"Attempt {attempt + 1}: rate limited, retrying...")
                last_error = e
                if self._rate_limiter is not None:
                    self._rate_limiter.report_rate_limit()
                if attempt < self._max_attempts - 1:
                    time.sleep(self._base_delay * (2 ** attempt))
                    continue
            except BadRequestError as e:
                # Schema rejection or other malformed request — single retry
                # with a fresh attempt, then fail.
                logger.warning(f"Attempt {attempt + 1}: bad request: {e}")
                last_error = e
                if attempt < self._max_attempts - 1:
                    time.sleep(self._base_delay)
                    continue
            except Exception as e:
                err_str = str(e).lower()
                if "timeout" in err_str or "timed out" in err_str:
                    logger.warning(f"Attempt {attempt + 1}: timed out, retrying...")
                else:
                    logger.warning(
                        f"Attempt {attempt + 1}: {type(e).__name__}: {e}"
                    )
                last_error = e
                if attempt < self._max_attempts - 1:
                    time.sleep(self._base_delay * (2 ** attempt))
                    continue

        raise LLMError(
            f"Failed after {self._max_attempts} attempts: {last_error}"
        ) from last_error

    def _record_usage(self, response: Any) -> None:
        """Extract usage/cost from an OpenAI/OpenRouter response and record it.

        OpenRouter returns `usage.cost` directly (USD). The standard OpenAI
        `usage.prompt_tokens` / `usage.completion_tokens` are always present.
        `prompt_tokens_details.cached_tokens` is captured when available.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        # OpenRouter's `usage.cost` is a proprietary float; fall back to 0.0
        cost = 0.0
        cost_attr = getattr(usage, "cost", None)
        if cost_attr is not None:
            try:
                cost = float(cost_attr)
            except (TypeError, ValueError):
                cost = 0.0
        cached_in = 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached_in = int(getattr(details, "cached_tokens", 0) or 0)
        self._metrics.record_call(
            self._phase,
            prompt_tokens,
            completion_tokens,
            cost_usd=cost,
            cached_input_tokens=cached_in,
        )
"""Pipeline metrics: token usage, cost, cache hits, latency, call counts.

One `Metrics` instance is shared across all three phases (lemmatize, gloss,
substitute) by `pipeline.run_pipeline`. The LLMClient records a usage sample
on every successful `query()`, and the phases call `record_cache_hit` when
they skip LLM work because of an existing cache or predicate.

Cost is read directly from OpenRouter's `usage.cost` field on each response
(see https://openrouter.ai/docs/api-reference/overview). When absent (e.g.
non-OpenRouter backends), cost accumulates as 0.0 — token counts and cache
hits remain useful.
"""

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class _PhaseStats:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    cache_hits: int = 0
    cached_input_tokens: int = 0  # from prompt_tokens_details.cached_tokens
    items_processed: int = 0  # tokens annotated / entries written / etc.

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class Metrics:
    """Aggregates v2 pipeline metrics across phases."""

    lemmatize: _PhaseStats = field(default_factory=_PhaseStats)
    gloss: _PhaseStats = field(default_factory=_PhaseStats)
    substitute: _PhaseStats = field(default_factory=_PhaseStats)
    started_at: float = field(default_factory=time.time)
    ended_at: float | None = None

    def record_call(
        self,
        phase: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float = 0.0,
        cached_input_tokens: int = 0,
    ) -> None:
        stats = self._stats_for(phase)
        stats.calls += 1
        stats.prompt_tokens += prompt_tokens
        stats.completion_tokens += completion_tokens
        stats.cost_usd += cost_usd
        stats.cached_input_tokens += cached_input_tokens

    def record_cache_hit(self, phase: str, n: int = 1) -> None:
        self._stats_for(phase).cache_hits += n

    def record_items_processed(self, phase: str, n: int) -> None:
        self._stats_for(phase).items_processed = n

    def finish(self) -> None:
        self.ended_at = time.time()

    def _stats_for(self, phase: str) -> _PhaseStats:
        return getattr(self, phase)

    def total_cost(self) -> float:
        return self.lemmatize.cost_usd + self.gloss.cost_usd + self.substitute.cost_usd

    def total_tokens(self) -> tuple[int, int]:
        ppl = sum(getattr(p, "prompt_tokens") for p in (self.lemmatize, self.gloss, self.substitute))
        cpt = sum(getattr(p, "completion_tokens") for p in (self.lemmatize, self.gloss, self.substitute))
        return ppl, cpt

    def total_calls(self) -> int:
        return self.lemmatize.calls + self.gloss.calls + self.substitute.calls

    def summary(self) -> str:
        self.ended_at = self.ended_at or time.time()
        wall = self.ended_at - self.started_at
        ppl, cpt = self.total_tokens()
        lines = [
            "",
            "=" * 72,
            "SharkReader v2 pipeline summary",
            "=" * 72,
            f"Wall time: {wall:.1f}s   Total LLM calls: {self.total_calls()}   "
            f"Total cost: ${self.total_cost():.4f}",
        ]
        for phase in ("lemmatize", "gloss", "substitute"):
            s = self._stats_for(phase)
            if s.calls or s.cache_hits or s.items_processed:
                cached_note = (
                    f" (cached_in={s.cached_input_tokens})"
                    if s.cached_input_tokens
                    else ""
                )
                lines.append(
                    f"  {phase:<11} "
                    f"calls={s.calls:<5} cache_hits={s.cache_hits:<5} "
                    f"prompt_in={s.prompt_tokens:<7} completions={s.completion_tokens:<6} "
                    f"cost=${s.cost_usd:.4f}{cached_note}  items={s.items_processed}"
                )
        lines.append(
            f"  {'TOTAL':<11} calls={self.total_calls():<5} "
            f"{'':<16}prompt_in={ppl:<7} completions={cpt:<6} "
            f"cost=${self.total_cost():.4f}"
        )
        lines.append("=" * 72)
        return "\n".join(lines)
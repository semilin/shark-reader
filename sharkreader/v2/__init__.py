"""SharkReader v2 pipeline.

Three phases share one LLM client (with strict JSON schema responses and a
system-message cache for the core vocabulary), three prompts, and three
strict response schemas:

    lemmatizer  -> writes `l` into the token stream
    glosser     -> expands the persistent JSON dictionary
    substitutor -> writes per-token `s` hints (context-sensitive)

See `pipeline.py` for orchestration and resumability.
"""

from sharkreader.v2 import llm, prompts, schemas  # noqa: F401

__all__ = ["llm", "prompts", "schemas"]
"""Prompt templates for the v2 pipeline.

Pure functions: structured input -> prompt string. No token-shape knowledge
leaks in here; callers precompute sentence text, context windows, etc.
"""

from typing import Sequence

from sharkreader.config import LanguageConfig


def core_vocab_system_block(vocab_list: Sequence[str], config: LanguageConfig) -> str:
    """Format the core vocabulary list as a system-message block.

    Lives in `LLMClient.add_system(...)` once per run so it is not re-sent on
    every request.
    """
    vocab_str = "\n".join(vocab_list)
    return (
        f"# CORE VOCABULARY ({config.name})\n"
        f"{vocab_str}\n"
        f"# END CORE VOCABULARY\n"
        f"You generate {config.name} glosses and substitute hints restricted "
        f"to the core vocabulary above where possible. Reference these words "
        f"by their headword forms."
    )


def lemma_user_prompt(
    batch: list[dict],
    config: LanguageConfig,
) -> str:
    """Build the lemmatization user prompt for a batch of sentences.

    `batch` is a list of dicts: {"sentence_index": int, "text": str,
    "words": [str]}. The model returns one lemma per word, in order.
    """
    blocks: list[str] = []
    for sent in batch:
        idx = sent["sentence_index"]
        text = sent["text"]
        words = sent["words"]
        numbered = "\n".join(f"{i + 1}. {w}" for i, w in enumerate(words))
        blocks.append(
            f"## Sentence {idx}\n"
            f"Context text: {text}\n"
            f"Words to lemmatize (one lemma per item, in this order):\n{numbered}"
        )

    sentences_joined = "\n\n".join(blocks)
    return (
        f"Context: {config.name} literature.\n"
        f"Lemmatize each numbered word. Provide a lemma for EVERY item in the "
        f"order given; if a word cannot be lemmatized, use the empty string.\n"
        f"{config.lemma_instructions}\n"
        f"Return JSON with a `results` array; each entry has "
        f"`sentence_index` (matching the input) and `lemmas` (an array of "
        f"strings, in the same order as the input words, one per word).\n\n"
        f"{sentences_joined}"
    )


def gloss_user_prompt(lemmas: Sequence[str], config: LanguageConfig) -> str:
    """Build the gloss user prompt for a batch of lemmas."""
    numbered = "\n".join(f"{i + 1}. {w}" for i, w in enumerate(lemmas))
    return (
        f"# DIRECTIONS\n"
        f"Generate an immersive {config.name} gloss for each listed word.\n"
        f"For each lemma:\n"
        f"- `definition`: one or two simple sentences explaining the meaning, "
        f"using primarily the CORE VOCABULARY. The first sentence states the "
        f"basic usage as concisely as possible; a second sentence, if any, "
        f"adds nuance. Treat non-nouns as substantives (e.g. verbs defined via "
        f"a substantive infinitive).\n"
        f"- `examples`: 1-2 example sentences using the word in different "
        f"forms. Use a second example ONLY when it illustrates a genuinely "
        f"distinct sense; otherwise provide exactly one.\n"
        f"- `synonyms`: 0-2 close synonyms in their primary principal part. "
        f"Empty list if none are very close.\n"
        f"Prefer core vocabulary throughout; common {config.name} names and "
        f"occasionally highly-relevant non-core words are acceptable.\n"
        f"Use proper polytonic accentuation for Greek; omit macrons for Latin.\n"
        f"For example, if the word were \"{config.example_word}\", you would "
        f"respond with {config.example_response}.\n\n"
        f"# LEMMAS\n{numbered}\n\n"
        f"Return JSON with a `results` array; each entry has `lemma` "
        f"(matching the input headword), `definition`, `examples`, and "
        f"`synonyms`."
    )


def substitute_user_prompt(
    triples: list[dict],
    config: LanguageConfig,
) -> str:
    """Build the substitute-hint user prompt for a batch of occurrences.

    `triples` is a list of dicts: {"index": int, "word": str, "lemma": str,
    "context": str, "definition": str | None}. The model returns a short
    substitute (<=3 words) preserving the same grammatical parsing, or the
    empty string if none.
    """
    blocks: list[str] = []
    for item in triples:
        defn = item.get("definition") or "(no definition available)"
        blocks.append(
            f"## Item {item['index']}\n"
            f"WORD: {item['word']}\n"
            f"LEMMA: {item['lemma']}\n"
            f"DEFINITION: {defn}\n"
            f"CONTEXT: {item['context']}"
        )
    items_joined = "\n\n".join(blocks)
    return (
        f"# DIRECTIONS\n"
        f"You are given {config.name} words, each in a specific context. For "
        f"each, decide whether it can be replaced by a SIMPLER {config.name} "
        f"word or short phrase (no more than 3 words) that preserves the "
        f"same grammatical parsing (person, number, tense, mood, voice, case, "
        f"gender, etc.).\n\n"
        f"RULES:\n"
        f"1. The substitute MUST be simpler and more common than the original "
        f"and preserve the exact grammatical parsing.\n"
        f"2. The substitute must be 3 words or fewer.\n"
        f"3. Prefer substitutes drawn from CORE VOCABULARY; common {config.name} "
        f"function words are also acceptable when they capture the sense.\n"
        f"4. If the word is already common, return the empty string.\n"
        f"5. If the meaning is too nuanced to capture in 3 words or fewer, "
        f"return the empty string.\n"
        f"6. If no suitable substitute exists, return the empty string.\n\n"
        f"Return JSON with a `results` array; each entry has `index` (matching "
        f"the input item index) and `substitute` (the substitute string, or the "
        f"empty string if none).\n\n"
        f"{items_joined}"
    )
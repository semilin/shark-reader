"""Language configurations for Latin and Ancient Greek."""

from dataclasses import dataclass
from typing import Literal

Language = Literal["latin", "greek"]


@dataclass(frozen=True)
class LanguageConfig:
    core_vocab: str
    name: str
    example_word: str
    example_response: str
    lemma_instructions: str
    word_pattern: str


CONFIGS: dict[Language, LanguageConfig] = {
    "latin": LanguageConfig(
        core_vocab="core_lists/latin-core-list.csv",
        name="Latin",
        example_word="sella",
        example_response='{"definition": "Sella est rēs in quā homō sedet. Haec rēs quattuor pedēs habet et in casā vel in villā invenītur.", "examples": ["Marcus in sellā sedet.", "Puer fessus ad sellam currit."], "synonyms": ["sēdēs"]}',
        lemma_instructions="Put in primary principle parts (first person present active singular for verbs, nominative singular for nouns, etc.). Only the primary principle part should be listed. Don't use macrons. Capitalize proper nouns, but do not capitalize regular words.",
        word_pattern=r"[\w\u00C0-\u017F]+",
    ),
    "greek": LanguageConfig(
        core_vocab="core_lists/greek-core-list.csv",
        name="Ancient Greek",
        example_word="ἵππος",
        example_response='{"definition": "Ὁ ἵππος ἐστὶ ζῷον μέγα ὃ ἐν τῷ ἀγρῷ τρέχει καὶ τοὺς ἀνθρώπους φέρει.", "examples": ["Ὁ παῖς ἐπὶ τοῦ ἵππου κάθηται.", "Οἱ ἵπποι εἰς τὴν πόλιν τρέχουσιν."], "synonyms": ["κέλης"]}',
        lemma_instructions="Put in primary principle parts (first person present active singular for verbs, nominative singular for nouns, etc.). Participles should be counted as their source verb, excepting participle-derived nouns such as ἄρχων. Use proper polytonic accentuation. Capitalize proper nouns, but do not capitalize regular words.",
        word_pattern=r"[\w\u0370-\u03FF\u1F00-\u1FFF]+",
    ),
}


# Models
ANNOTATION_MODEL = "google/gemini-3.1-flash-lite-preview"
GLOSS_MODEL = "google/gemini-3-flash-preview"

# API Configuration
DEFAULT_MAX_WORKERS = 50
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_BASE_DELAY = 1.0  # seconds

"""Strict JSON response schemas for the v2 pipeline.

All schemas use `additionalProperties: false` and explicit `required` arrays so
they are accepted by OpenRouter's strict json_schema mode (which maps to
Gemini's native responseSchema with responseMimeType=application/json).

Conventions used to avoid strict-mode friction:
- No union types. The "no substitute" case is encoded as the empty string ("")
  rather than null, and converted to None in Python after parsing.
- Array cardinality caps are encoded with `maxItems` where useful (e.g. the
  1-2 examples rule for glosses).
"""

LEMMA_SCHEMA = {
    "$id": "lemma_response",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "sentence_index": {"type": "integer"},
                    "lemmas": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["sentence_index", "lemmas"],
            },
        }
    },
    "required": ["results"],
}


GLOSS_SCHEMA = {
    "$id": "gloss_response",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "lemma": {"type": "string"},
                    "definition": {"type": "string"},
                    # 1-2 examples; the second is only for a genuinely distinct
                    # sense of the word.
                    "examples": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {"type": "string"},
                    },
                    "synonyms": {
                        "type": "array",
                        "maxItems": 2,
                        "items": {"type": "string"},
                    },
                },
                "required": ["lemma", "definition", "examples", "synonyms"],
            },
        }
    },
    "required": ["results"],
}


SUBSTITUTE_SCHEMA = {
    "$id": "substitute_response",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "index": {"type": "integer"},
                    # Empty string == "no suitable substitute".
                    "substitute": {"type": "string"},
                },
                "required": ["index", "substitute"],
            },
        }
    },
    "required": ["results"],
}
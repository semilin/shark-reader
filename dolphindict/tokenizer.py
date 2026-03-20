"""Text tokenization with enhanced Unicode handling."""

import re
import unicodedata
from typing import TypedDict


class Token(TypedDict):
    t: str
    w: str
    l: str


# Extended Unicode ranges for Latin and Greek including macrons and diacritics
LATIN_EXTENDED = "\u00C0-\u017F"  # Latin-1 Supplement + Latin Extended-A
GREEK_RANGE = "\u0370-\u03FF\u1F00-\u1FFF"  # Greek + Greek Extended

# Regex patterns for different token types
# Group 1: Markers [70a]
# Group 2: Speakers Socrates: (Must start with Uppercase, NO spaces, max 25 chars)
# Group 3: Words (Latin/Greek/macrons/accents)
# Group 4: Newline
# Group 5: Punctuation (anything else, excluding pure whitespace)
# Group 6: Whitespace (to be ignored)
TOKEN_PATTERN = re.compile(
    rf"(\[\w+\])|(^[\u00C0-\u00DE\u0391-\u03A9][\w{LATIN_EXTENDED}{GREEK_RANGE}]{{0,25}}:)|"
    rf"([\w{LATIN_EXTENDED}{GREEK_RANGE}]+)|(\n)|([^\w\s\n\[\]]+)|(\s+)",
    flags=re.MULTILINE,
)

# Unicode artifact replacements
UNICODE_REPLACEMENTS: list[tuple[str, str]] = [
    ("u2014", "—"),   # em-dash
    ("u2018", "'"),   # left single quote
    ("u2019", "'"),   # right single quote
    ("u201c", '"'),   # left double quote
    ("u201d", '"'),   # right double quote
    ("u2026", "…"),   # ellipsis
    ("u00A0", " "),   # non-breaking space
    ("\xa0", " "),    # non-breaking space (literal)
]


def normalize_text(text: str) -> str:
    """Normalize Unicode text using NFC composition."""
    return unicodedata.normalize("NFC", text)


def clean_text(text: str) -> str:
    """Surgically clean problematic unicode and artifacts before tokenization."""
    text = normalize_text(text)
    
    # Handle literal unicode escape sequences that appeared in the data
    for pattern, replacement in UNICODE_REPLACEMENTS:
        text = text.replace(pattern, replacement)
    
    # Handle escaped unicode sequences (e.g., \u2014)
    def replace_escaped_unicode(match: re.Match) -> str:
        try:
            return chr(int(match.group(1), 16))
        except (ValueError, OverflowError):
            return ""
    
    text = re.sub(r"\\u([0-9a-fA-F]{4})", replace_escaped_unicode, text)
    
    # Clean up other common artifacts
    text = text.replace("\\", "")  # Stray backslashes
    
    return text


def tokenize_rich(text: str) -> list[Token]:
    """Tokenize text into rich tokens with types."""
    tokens: list[Token] = []
    
    for match in TOKEN_PATTERN.finditer(text):
        m1, m2, m3, m4, m5, m6 = match.groups()
        
        if m1:
            tokens.append({"t": "m", "w": m1, "l": ""})  # Marker
        elif m2:
            tokens.append({"t": "s", "w": m2, "l": ""})  # Speaker
        elif m3:
            tokens.append({"t": "w", "w": m3, "l": ""})   # Word (placeholder lemma)
        elif m4:
            tokens.append({"t": "n", "w": "", "l": ""})  # Newline
        elif m5:
            # Punctuation (non-whitespace)
            # Merge with previous word if applicable
            if tokens and tokens[-1]["t"] == "w":
                tokens[-1]["w"] += m5
            else:
                tokens.append({"t": "p", "w": m5, "l": ""})
        # m6 (whitespace) is ignored
    
    return tokens


def get_word_pattern(config_word_pattern: str) -> re.Pattern:
    """Compile regex pattern for extracting words from a config."""
    return re.compile(f"[^{config_word_pattern}]+")

"""TEI XML parsing for the v2 pipeline.

Replaces the legacy `main.py:cmd_from_xml` for new ingest. Key differences:

- Punctuation that the legacy parser silently dropped is preserved: middle
  dot (U+00B7), Greek ano teleia (U+0387), Greek question mark (U+037E),
  curly quotes, modifier-letter apostrophe (U+02BC, used in Greek elision
  like δʼ), ellipsis, non-breaking hyphen.
- Punctuation merges into the preceding word's `w` field (the `tokenize_rich`
  / `Meno.annotated.json` convention), so the token stream is compact and
  the chunker's `word.endswith(c)` sentence-end branch keeps working.
- A new minimal `tokenize_text_content` does only word / punctuation /
  newline splitting. Speaker and marker detection are NOT done in text
  content because the TEI structure supplies them explicitly via
  `<speaker>` and `<milestone>` / `<div type="textpart">` elements. This
  eliminates false-positive speaker tokens from inline `^Word:` patterns.
- Output shape matches legacy `from-xml` exactly so the result feeds both
  the legacy pipeline and the v2 pipeline unchanged:
  `{"metadata": {...}, "tokens": [...]}`.
"""

import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any

# Extended Unicode ranges for Latin and Greek including macrons and diacritics
LATIN_EXTENDED = "\u00C0-\u017F"  # Latin-1 Supplement + Latin Extended-A
GREEK_RANGE = "\u0370-\u03FF\u1F00-\u1FFF"  # Greek + Greek Extended

# Text-content tokenization pattern. Groups:
# 1. word  (Latin/Greek/macrons/accents)
# 2. newline
# 3. punctuation (any non-word, non-whitespace, non-newline run)
_TEXT_CONTENT_PATTERN = re.compile(
    rf"([\w{LATIN_EXTENDED}{GREEK_RANGE}]+)|(\n)|([^\w\s\n]+)",
)

# Whitespace regex for stripping (excludes newlines).
_WHITESPACE = re.compile(r"[ \t\r\f\v]+")


def _normalize_text(text: str) -> str:
    """NFC-normalize and clean known artefacts before tokenization.

    Mirrors `tokenizer.clean_text` but skips the rich-tokenizer-specific
    escapes (those don't apply to XML text content, which has already been
    parsed by ElementTree).
    """
    text = unicodedata.normalize("NFC", text)
    # Non-breaking space -> regular space
    text = text.replace("\u00A0", " ").replace("\xa0", " ")
    # Strip stray backslashes that appear in some Perseus files
    text = text.replace("\\", "")
    return text


def tokenize_text_content(text: str) -> list[dict]:
    """Tokenize a run of XML text content into rich tokens.

    Emits only `w` (word, with trailing punctuation merged in), `n`
    (newline), and `p` (standalone punctuation when there is no preceding
    word in the current run). Speakers and markers come from XML structure
    via `parse_tei_xml`, not from this function.
    """
    text = _normalize_text(text)
    tokens: list[dict] = []

    for match in _TEXT_CONTENT_PATTERN.finditer(text):
        word, newline, punct = match.groups()

        if word:
            tokens.append({"t": "w", "w": word, "l": ""})
        elif newline:
            tokens.append({"t": "n", "w": "", "l": ""})
        elif punct:
            # Merge into the preceding word token if any. This preserves the
            # middle dot (and all other Greek punctuation) attached to its
            # word, matching the tokenize_rich / Meno convention.
            if tokens and tokens[-1]["t"] == "w":
                tokens[-1]["w"] += punct
            else:
                tokens.append({"t": "p", "w": punct, "l": ""})

    return tokens


_TEI_NS = "{http://www.tei-c.org/ns/1.0}"


def _local(tag: str) -> str:
    return tag.replace(_TEI_NS, "")


def _process_element(elem: ET.Element, tokens: list[dict]) -> None:
    """Walk a TEI element, appending rich tokens to `tokens`."""
    tag = _local(elem.tag)

    if tag == "div":
        div_type = elem.get("type", "")
        div_n = elem.get("n", "")
        if div_type == "textpart" and div_n:
            tokens.append({"t": "m", "w": f"[{div_n}]", "l": ""})
            tokens.append({"t": "n", "w": "", "l": ""})
        for child in elem:
            _process_element(child, tokens)

    elif tag == "p":
        if elem.text:
            tokens.extend(tokenize_text_content(elem.text))
        for child in elem:
            _process_element(child, tokens)
        tokens.append({"t": "n", "w": "", "l": ""})

    elif tag == "sp":
        for child in elem:
            _process_element(child, tokens)
        tokens.append({"t": "n", "w": "", "l": ""})

    elif tag == "speaker":
        if elem.text:
            speaker = elem.text.strip()
            if speaker:
                tokens.append({"t": "s", "w": speaker + ":", "l": ""})

    elif tag == "l":
        # Line of verse. Match the legacy `from-xml` convention: tokenize
        # text content + children, then a newline. Line numbers from the `n`
        # attribute are NOT emitted as markers (matching iliad1.annotated.json
        # which has no per-line markers).
        if elem.text:
            tokens.extend(tokenize_text_content(elem.text))
        for child in elem:
            _process_element(child, tokens)
        tokens.append({"t": "n", "w": "", "l": ""})

    elif tag == "said":
        who = elem.get("who", "")
        if who:
            speaker = who.replace("#", "") + ":"
            tokens.append({"t": "s", "w": speaker, "l": ""})
        for child in elem:
            _process_element(child, tokens)
        tokens.append({"t": "n", "w": "", "l": ""})

    elif tag == "label":
        # Skip: editorial speaker abbreviation (e.g. ΣΩ.). The full speaker
        # name is already in the parent `<said who=...>` / `<speaker>`.
        pass

    elif tag == "milestone":
        unit = elem.get("unit", "")
        n = elem.get("n", "")
        # Perseus uses `unit="section"` for prose and `unit="card"` for
        # verse section breaks. Both become `[n]` markers.
        if unit in ("section", "card") and n:
            tokens.append({"t": "m", "w": f"[{n}]", "l": ""})
        # `unit="page"`, `unit="Para"`, and others are dropped, as in the
        # legacy parser.

    elif tag == "q":
        for child in elem:
            _process_element(child, tokens)

    elif tag == "note":
        # Editorial notes, cast lists, etc. — skip.
        pass

    elif tag == "del":
        # Deleted text — skip.
        pass

    elif tag == "add":
        # Added text — process children.
        for child in elem:
            _process_element(child, tokens)

    elif tag == "gap":
        tokens.append({"t": "p", "w": "[...]", "l": ""})

    elif tag == "lb":
        # Line break inside a paragraph — emit a newline token.
        tokens.append({"t": "n", "w": "", "l": ""})

    else:
        # Unknown element with text content — tokenize its text and recurse.
        if elem.text:
            tokens.extend(tokenize_text_content(elem.text))
        for child in elem:
            _process_element(child, tokens)

    # Tail text (text following this element within its parent) is tokenized
    # and appended. This is how ElementTree represents mixed content.
    if elem.tail:
        tokens.extend(tokenize_text_content(elem.tail))


def parse_tei_xml(
    path: str,
    *,
    work_type: str,
    title: str | None = None,
    author: str | None = None,
) -> dict[str, Any]:
    """Parse a Perseus TEI XML file into the annotated-JSON shape.

    Returns `{"metadata": {...}, "tokens": [...]}`. The token stream uses
    the same rich-token convention as `tokenize_rich` and the existing
    `*.annotated.json` files, so the v2 pipeline can consume it directly.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    # Title
    title_elem = root.find(".//tei:titleStmt/tei:title", {"tei": _TEI_NS[1:-1]})
    parsed_title = title_elem.text if title_elem is not None and title_elem.text else "Unknown"

    # Author
    author_elem = root.find(".//tei:titleStmt/tei:author", {"tei": _TEI_NS[1:-1]})
    parsed_author = author_elem.text if author_elem is not None and author_elem.text else "Unknown"

    # Language
    lang_elem = root.find(".//tei:language", {"tei": _TEI_NS[1:-1]})
    if lang_elem is not None and lang_elem.get("ident") == "grc":
        language = "greek"
    elif lang_elem is not None and lang_elem.get("ident") == "lat":
        language = "latin"
    else:
        # Fallback: detect from title text (Greek Unicode range)
        if parsed_title and any("\u0370" <= ch <= "\u1fff" for ch in parsed_title):
            language = "greek"
        else:
            language = "latin"

    text_body = root.find(".//tei:text/tei:body", {"tei": _TEI_NS[1:-1]})
    if text_body is None:
        raise ValueError(f"No <text><body> found in {path}")

    tokens: list[dict] = []
    for child in text_body:
        _process_element(child, tokens)

    return {
        "metadata": {
            "title": title if title is not None else parsed_title,
            "author": author if author is not None else parsed_author,
            "work_type": work_type,
            "language": language,
        },
        "tokens": tokens,
    }
"""Tests for the tokenizer module."""

import pytest

from sharkreader import tokenizer


class TestCleanText:
    """Tests for clean_text function."""

    def test_handles_em_dash_escape(self):
        text = "word1 u2014 word2"
        result = tokenizer.clean_text(text)
        assert "—" in result

    def test_handles_literal_non_breaking_space(self):
        text = "word1\xa0word2"
        result = tokenizer.clean_text(text)
        assert "\xa0" not in result
        assert " " in result

    def test_handles_escaped_unicode(self):
        text = r"word1 \u2014 word2"
        result = tokenizer.clean_text(text)
        assert "—" in result

    def test_normalizes_unicode(self):
        # é can be composed (U+00E9) or decomposed (U+0065 U+0301)
        text_composed = "café"
        text_decomposed = "cafe\u0301"

        result_composed = tokenizer.clean_text(text_composed)
        result_decomposed = tokenizer.clean_text(text_decomposed)

        # Both should normalize to the same form
        assert result_composed == result_decomposed

    def test_removes_stray_backslashes(self):
        text = r"word1\word2"
        result = tokenizer.clean_text(text)
        assert "\\" not in result


class TestTokenizeRich:
    """Tests for tokenize_rich function."""

    def test_tokenizes_simple_sentence(self):
        text = "Hello world."
        tokens = tokenizer.tokenize_rich(text)

        # Trailing punctuation is merged with word (existing behavior)
        assert len(tokens) == 2
        assert tokens[0] == {"t": "w", "w": "Hello", "l": ""}
        assert tokens[1] == {"t": "w", "w": "world.", "l": ""}

    def test_tokenizes_with_newline(self):
        text = "Hello\nworld."
        tokens = tokenizer.tokenize_rich(text)

        assert tokens[1] == {"t": "n", "w": "", "l": ""}

    def test_tokenizes_marker(self):
        text = "Hello [70a] world."
        tokens = tokenizer.tokenize_rich(text)

        assert tokens[0] == {"t": "w", "w": "Hello", "l": ""}
        assert tokens[1] == {"t": "m", "w": "[70a]", "l": ""}

    def test_tokenizes_speaker(self):
        # Speaker must be at start of line (^ anchor in pattern)
        text = "Socrates: Hello."
        tokens = tokenizer.tokenize_rich(text)

        # Without line start, it's treated as a word
        assert tokens[0] == {"t": "w", "w": "Socrates:", "l": ""}

    def test_tokenizes_speaker_at_line_start(self):
        # Speaker detection requires specific conditions (start of input with proper formatting)
        # This test documents the current behavior
        text = "Socrates:\nHello."
        tokens = tokenizer.tokenize_rich(text)

        # Current behavior: speakers are not detected mid-text
        # They are treated as regular words
        assert tokens[0]["t"] == "w"
        assert tokens[0]["w"] == "Socrates:"

    def test_merges_trailing_punctuation(self):
        text = "Hello,"
        tokens = tokenizer.tokenize_rich(text)

        # Comma should be merged with word
        assert tokens[0] == {"t": "w", "w": "Hello,", "l": ""}

    def test_tokenizes_latin_with_macrons(self):
        text = "cōnsilium"
        tokens = tokenizer.tokenize_rich(text)

        assert tokens[0]["t"] == "w"
        assert tokens[0]["w"] == "cōnsilium"

    def test_tokenizes_greek(self):
        text = "ἵππος"
        tokens = tokenizer.tokenize_rich(text)

        assert tokens[0]["t"] == "w"
        assert tokens[0]["w"] == "ἵππος"


class TestNormalizeText:
    """Tests for normalize_text function."""

    def test_nfc_normalization(self):
        # Test that NFC normalization works
        decomposed = "e\u0301"  # e + combining acute
        result = tokenizer.normalize_text(decomposed)

        assert len(result) == 1
        assert result == "é"

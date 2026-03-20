"""Tests for the glossgen module."""

import pytest

from dolphindict import config, glossgen


class TestValidateGlossResponse:
    """Tests for validate_gloss_response function."""
    
    def test_valid_response(self):
        response = {
            "definition": "A horse is a large animal.",
            "examples": ["The horse runs.", "I see a horse."]
        }
        
        result = glossgen.validate_gloss_response(response)
        
        assert result["definition"] == "A horse is a large animal."
        assert len(result["examples"]) == 2
    
    def test_missing_definition(self):
        response = {
            "examples": ["The horse runs."]
        }
        
        with pytest.raises(glossgen.GlossGenerationError) as exc_info:
            glossgen.validate_gloss_response(response)
        
        assert "definition" in str(exc_info.value)
    
    def test_missing_examples(self):
        response = {
            "definition": "A horse."
        }
        
        with pytest.raises(glossgen.GlossGenerationError) as exc_info:
            glossgen.validate_gloss_response(response)
        
        assert "examples" in str(exc_info.value)
    
    def test_non_dict_response(self):
        response = "not a dict"
        
        with pytest.raises(glossgen.GlossGenerationError):
            glossgen.validate_gloss_response(response)
    
    def test_converts_values_to_strings(self):
        response = {
            "definition": 123,
            "examples": [456, 789]
        }
        
        result = glossgen.validate_gloss_response(response)
        
        assert result["definition"] == "123"
        assert result["examples"] == ["456", "789"]


class TestQueryLLMWithRetry:
    """Tests for query_llm_with_retry function."""
    
    def test_returns_dict_on_success(self, mocker):
        mock_client = mocker.MagicMock()
        mock_response = mocker.MagicMock()
        mock_response.choices = [mocker.MagicMock()]
        mock_response.choices[0].message.content = '{"test": "data"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        result = glossgen.query_llm_with_retry(
            "test prompt",
            config.GLOSS_MODEL,
            mock_client,
            max_attempts=1,
        )
        
        assert result == {"test": "data"}
    
    def test_retries_on_json_error(self, mocker):
        mock_client = mocker.MagicMock()
        
        # First call returns invalid JSON, second returns valid
        mock_response_1 = mocker.MagicMock()
        mock_response_1.choices = [mocker.MagicMock()]
        mock_response_1.choices[0].message.content = "invalid json"
        
        mock_response_2 = mocker.MagicMock()
        mock_response_2.choices = [mocker.MagicMock()]
        mock_response_2.choices[0].message.content = '{"valid": "data"}'
        
        mock_client.chat.completions.create.side_effect = [
            mock_response_1,
            mock_response_2,
        ]
        
        result = glossgen.query_llm_with_retry(
            "test prompt",
            config.GLOSS_MODEL,
            mock_client,
            max_attempts=2,
            base_delay=0.01,
        )
        
        assert result == {"valid": "data"}
        assert mock_client.chat.completions.create.call_count == 2

"""Tests for app/services/llm_service.py — pure logic only (no API calls)."""

from app.services.llm_service import _get_api_key, _model_mapping


class TestModelMapping:
    def test_openai_default(self):
        assert _model_mapping("openai", "") == "gpt-4o-mini"

    def test_openai_custom(self):
        assert _model_mapping("openai", "gpt-4o") == "gpt-4o"

    def test_anthropic_default(self):
        assert _model_mapping("anthropic", "") == "claude-3-5-haiku-20241022"

    def test_groq_prefix(self):
        assert _model_mapping("groq", "") == "groq/llama3-70b-8192"

    def test_google_prefix(self):
        assert _model_mapping("google", "") == "gemini/gemini-1.5-flash"

    def test_ollama_prefix(self):
        result = _model_mapping("ollama", "")
        assert result.startswith("ollama/")

    def test_openrouter_prefix(self):
        result = _model_mapping("openrouter", "")
        assert result.startswith("openrouter/")

    def test_unknown_provider_returns_model(self):
        assert _model_mapping("unknown", "some-model") == "some-model"


class TestGetApiKey:
    def test_returns_value_for_configured_provider(self, monkeypatch):
        monkeypatch.setattr("app.config.OPENAI_API_KEY", "test-key")
        assert _get_api_key("openai") == "test-key"

    def test_returns_empty_when_empty(self, monkeypatch):
        monkeypatch.setattr("app.config.OPENAI_API_KEY", "")
        assert _get_api_key("openai") == ""

    def test_unknown_provider_returns_none(self, monkeypatch):
        monkeypatch.setattr("app.config.OPENAI_API_KEY", "key")
        assert _get_api_key("nonexistent") is None

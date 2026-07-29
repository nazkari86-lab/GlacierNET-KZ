"""Tests for app/services/llm_service.py — pure logic only (no API calls)."""

from app.services.llm_service import _fetch_models_with_key, _get_api_key, is_repetitive_completion


class TestGetApiKey:
    def test_returns_groq_key(self, monkeypatch):
        monkeypatch.setattr("app.config.GROQ_API_KEY", "test-key")
        assert _get_api_key("groq") == "test-key"

    def test_returns_empty_when_empty(self, monkeypatch):
        monkeypatch.setattr("app.config.GROQ_API_KEY", "")
        assert _get_api_key("groq") == ""

    def test_unknown_provider_returns_none(self, monkeypatch):
        monkeypatch.setattr("app.config.GROQ_API_KEY", "key")
        assert _get_api_key("nonexistent") is None

    def test_model_fetch_rejects_non_groq_without_network(self):
        assert _fetch_models_with_key("openai", "unused") == []


def test_repetition_guard_detects_degenerate_loop_but_not_normal_answer():
    assert is_repetitive_completion(
        "Задача проекта — оценка ледников по спутниковым данным. "
        "Задача проекта — оценка ледников по спутниковым данным. "
        "Задача проекта — оценка ледников по спутниковым данным. "
        "Задача проекта — оценка ледников по спутниковым данным."
    )
    assert not is_repetitive_completion(
        "Проект выделяет ледники на снимках. Затем он показывает маску и качество данных. "
        "Пользователь может сравнить доступные годы на карте."
    )

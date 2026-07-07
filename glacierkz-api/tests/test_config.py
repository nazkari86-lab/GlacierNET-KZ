"""Tests for app/config.py — module-level configuration."""

from __future__ import annotations

from pathlib import Path

from app import config


class TestConfigModule:
    def test_api_root_is_path(self):
        assert isinstance(config.API_ROOT, Path)

    def test_data_dir_is_path(self):
        assert isinstance(config.DATA_DIR, Path)

    def test_upload_dir_is_path(self):
        assert isinstance(config.UPLOAD_DIR, Path)

    def test_results_dir_is_path(self):
        assert isinstance(config.RESULTS_DIR, Path)

    def test_upload_dir_exists(self):
        assert config.UPLOAD_DIR.exists()

    def test_results_dir_exists(self):
        assert config.RESULTS_DIR.exists()

    def test_history_db_path(self):
        assert config.HISTORY_DB_PATH.suffix == ".db"

    def test_max_file_size_mb_default(self):
        assert config.MAX_FILE_SIZE_MB > 0

    def test_max_file_size_bytes_calculated(self):
        assert config.MAX_FILE_SIZE_BYTES == config.MAX_FILE_SIZE_MB * 1024 * 1024

    def test_task_timeout_default(self):
        assert config.TASK_TIMEOUT > 0

    def test_cors_origins_is_list(self):
        assert isinstance(config.CORS_ORIGINS, list)

    def test_redis_url_is_string(self):
        assert isinstance(config.REDIS_URL, str)

    def test_llm_provider_default(self):
        assert isinstance(config.LLM_PROVIDER, str)

    def test_llm_model_default(self):
        assert isinstance(config.LLM_MODEL, str)

    def test_llm_temperature(self):
        assert isinstance(config.LLM_TEMPERATURE, float)

    def test_llm_max_tokens(self):
        assert isinstance(config.LLM_MAX_TOKENS, int)

    def test_static_url_prefix(self):
        assert isinstance(config.STATIC_URL_PREFIX, str)

    def test_analysis_lang(self):
        assert isinstance(config.ANALYSIS_LANG, str)

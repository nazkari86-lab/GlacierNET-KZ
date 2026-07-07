"""Tests for app/monitoring/system.py — get_system_info, _get_open_files_limit, _get_virtual_memory_limit."""

from __future__ import annotations

from app.monitoring.system import (
    _get_open_files_limit,
    _get_virtual_memory_limit,
    get_system_info,
)


class TestGetOpenFilesLimit:
    def test_returns_int_or_none(self):
        result = _get_open_files_limit()
        assert result is None or isinstance(result, int)

    def test_positive_when_available(self):
        result = _get_open_files_limit()
        if result is not None:
            assert result > 0


class TestGetVirtualMemoryLimit:
    def test_returns_int_or_none(self):
        result = _get_virtual_memory_limit()
        assert result is None or isinstance(result, int)


class TestGetSystemInfo:
    def test_returns_dict(self):
        info = get_system_info()
        assert isinstance(info, dict)

    def test_has_platform_section(self):
        info = get_system_info()
        assert "platform" in info
        assert "system" in info["platform"]
        assert "python_version" in info["platform"]

    def test_has_process_section(self):
        info = get_system_info()
        assert "process" in info
        assert "pid" in info["process"]
        assert "cwd" in info["process"]

    def test_has_python_section(self):
        info = get_system_info()
        assert "python" in info
        assert "version" in info["python"]
        assert "executable" in info["python"]

    def test_has_environment_section(self):
        info = get_system_info()
        assert "environment" in info
        assert "env_count" in info["environment"]

    def test_has_limits_section(self):
        info = get_system_info()
        assert "limits" in info
        assert "open_files_limit" in info["limits"]

    def test_has_gpu_section(self):
        info = get_system_info()
        assert "gpu" in info
        assert "available" in info["gpu"]
        assert "count" in info["gpu"]

    def test_platform_system(self):
        import platform
        info = get_system_info()
        assert info["platform"]["system"] == platform.system()

    def test_platform_python_version(self):
        import platform
        info = get_system_info()
        assert info["platform"]["python_version"] == platform.python_version()

    def test_process_pid(self):
        import os
        info = get_system_info()
        assert info["process"]["pid"] == os.getpid()

    def test_python_path_is_list(self):
        info = get_system_info()
        assert isinstance(info["python"]["path"], list)

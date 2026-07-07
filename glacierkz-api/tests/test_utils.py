"""Tests for app/utils.py — resolve_core_dir, path_to_url."""

from __future__ import annotations

import os
import sys

from app.utils import path_to_url, resolve_core_dir


class TestResolveCoreDir:
    def test_env_var_set(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CORE_DIR", str(tmp_path))
        result = resolve_core_dir("/some/file.py")
        assert result == tmp_path

    def test_env_var_set_is_resolved(self, tmp_path, monkeypatch):
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        monkeypatch.setenv("CORE_DIR", str(nested / ".."))
        result = resolve_core_dir("/some/file.py")
        # resolve_core_dir returns the raw Path from CORE_DIR; resolve for comparison
        assert result.resolve() == nested.parent.resolve()

    def test_env_var_not_set_uses_file_path(self, monkeypatch):
        monkeypatch.delenv("CORE_DIR", raising=False)
        # 5 components → 4 .parent calls → /a
        fake_file = "/a/b/c/d/e.py"
        result = resolve_core_dir(fake_file)
        # On macOS, /a may resolve to /private/a; compare canonical forms
        assert os.path.realpath(result) == os.path.realpath("/a")

    def test_adds_to_sys_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CORE_DIR", str(tmp_path))
        resolve_core_dir("/some/file.py")
        assert str(tmp_path.resolve()) in sys.path

    def test_does_not_duplicate_sys_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CORE_DIR", str(tmp_path))
        resolve_core_dir("/some/file.py")
        count = sys.path.count(str(tmp_path.resolve()))
        resolve_core_dir("/some/file.py")
        assert sys.path.count(str(tmp_path.resolve())) == count


class TestPathToUrl:
    def test_path_inside_results_dir(self, tmp_results_dir, monkeypatch):
        monkeypatch.setattr("app.utils.RESULTS_DIR", tmp_results_dir)
        monkeypatch.setattr("app.utils.STATIC_URL_PREFIX", "")
        file_path = tmp_results_dir / "output.png"
        result = path_to_url(file_path)
        assert result == f"/static/results/{file_path.name}"

    def test_path_inside_results_dir_subdir(self, tmp_results_dir, monkeypatch):
        monkeypatch.setattr("app.utils.RESULTS_DIR", tmp_results_dir)
        monkeypatch.setattr("app.utils.STATIC_URL_PREFIX", "")
        sub = tmp_results_dir / "subdir"
        sub.mkdir()
        file_path = sub / "output.png"
        result = path_to_url(file_path)
        assert result == "/static/results/subdir/output.png"

    def test_path_outside_results_dir(self, monkeypatch):
        monkeypatch.setattr("app.utils.STATIC_URL_PREFIX", "")
        result = path_to_url("/tmp/random/file.tif")
        assert result == "/tmp/random/file.tif"

    def test_path_outside_results_dir_with_prefix(self, monkeypatch):
        monkeypatch.setattr("app.utils.STATIC_URL_PREFIX", "/api/v1")
        result = path_to_url("/tmp/random/file.tif")
        assert result == "/tmp/random/file.tif"

    def test_string_path_inside_results_dir(self, tmp_results_dir, monkeypatch):
        monkeypatch.setattr("app.utils.RESULTS_DIR", tmp_results_dir)
        monkeypatch.setattr("app.utils.STATIC_URL_PREFIX", "")
        file_path = str(tmp_results_dir / "test.png")
        result = path_to_url(file_path)
        assert result == "/static/results/test.png"

    def test_empty_path(self, monkeypatch):
        monkeypatch.setattr("app.utils.STATIC_URL_PREFIX", "")
        result = path_to_url("")
        assert result == ""

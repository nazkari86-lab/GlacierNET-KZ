# -*- coding: utf-8 -*-
"""Tests for src/experiment_tracking.py."""

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Mock TensorFlow before importing any src module
# ---------------------------------------------------------------------------
_mock_tf = MagicMock()
sys.modules["tensorflow"] = _mock_tf
sys.modules["tensorflow.keras"] = _mock_tf.keras
sys.modules["tensorflow.keras.applications"] = _mock_tf.keras.applications
sys.modules["tensorflow.keras.layers"] = _mock_tf.keras.layers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.experiment_tracking import (
    Experiment,
    ExperimentTracker,
    format_duration,
    generate_experiment_id,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker(tmp_path):
    """ExperimentTracker backed by a temporary directory."""
    return ExperimentTracker(str(tmp_path / "experiments"))


@pytest.fixture
def sample_params():
    return {"lr": 1e-4, "batch_size": 16, "epochs": 50}


@pytest.fixture
def sample_metrics():
    return {"dice": 0.91, "iou": 0.84, "loss": 0.23}


# ---------------------------------------------------------------------------
# generate_experiment_id tests
# ---------------------------------------------------------------------------

class TestGenerateExperimentId:
    def test_returns_hex_string(self):
        eid = generate_experiment_id()
        assert isinstance(eid, str)
        assert len(eid) == 32
        int(eid, 16)  # must be valid hex

    def test_unique(self):
        ids = {generate_experiment_id() for _ in range(100)}
        assert len(ids) == 100


# ---------------------------------------------------------------------------
# format_duration tests
# ---------------------------------------------------------------------------

class TestFormatDuration:
    def test_milliseconds(self):
        start = datetime(2025, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 0, 0, 0, 500_000, tzinfo=timezone.utc)
        assert format_duration(start, end) == "500ms"

    def test_seconds_only(self):
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 0, 0, 42, tzinfo=timezone.utc)
        assert format_duration(start, end) == "42s"

    def test_minutes_and_seconds(self):
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 0, 5, 30, tzinfo=timezone.utc)
        assert format_duration(start, end) == "5m 30s"

    def test_hours_minutes_seconds(self):
        start = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 2, 13, 7, tzinfo=timezone.utc)
        assert format_duration(start, end) == "2h 13m 7s"

    def test_negative_returns_zero(self):
        start = datetime(2025, 1, 1, 1, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert format_duration(start, end) == "0s"


# ---------------------------------------------------------------------------
# ExperimentTracker.log_experiment / get_experiment
# ---------------------------------------------------------------------------

class TestLogAndGetExperiment:
    def test_log_returns_valid_id(self, tracker, sample_params, sample_metrics):
        eid = tracker.log_experiment(
            name="test-run", params=sample_params, metrics=sample_metrics
        )
        assert isinstance(eid, str)
        assert len(eid) == 32

    def test_get_retrieves_logged_experiment(self, tracker, sample_params, sample_metrics):
        eid = tracker.log_experiment(
            name="test-run", params=sample_params, metrics=sample_metrics,
            model="unet",
        )
        exp = tracker.get_experiment(eid)
        assert exp.name == "test-run"
        assert exp.model == "unet"
        assert exp.params == sample_params
        assert exp.metrics == sample_metrics
        assert exp.status == "completed"

    def test_get_nonexistent_raises(self, tracker):
        with pytest.raises(FileNotFoundError):
            tracker.get_experiment("nonexistent_id")

    def test_multiple_logs_unique_ids(self, tracker, sample_params, sample_metrics):
        ids = [
            tracker.log_experiment(name=f"run-{i}", params=sample_params, metrics=sample_metrics)
            for i in range(5)
        ]
        assert len(set(ids)) == 5


# ---------------------------------------------------------------------------
# compare_experiments
# ---------------------------------------------------------------------------

class TestCompareExperiments:
    def test_returns_dataframe(self, tracker, sample_params, sample_metrics):
        e1 = tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics)
        e2 = tracker.log_experiment(name="b", params=sample_params, metrics=sample_metrics)
        df = tracker.compare_experiments([e1, e2])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "name" in df.columns
        assert "metric:iou" in df.columns


# ---------------------------------------------------------------------------
# list_experiments with filters
# ---------------------------------------------------------------------------

class TestListExperiments:
    def test_lists_all(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="alpha", params=sample_params, metrics=sample_metrics)
        tracker.log_experiment(name="beta", params=sample_params, metrics=sample_metrics)
        result = tracker.list_experiments()
        assert len(result) == 2

    def test_filter_by_name(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="glacier-v1", params=sample_params, metrics=sample_metrics)
        tracker.log_experiment(name="glacier-v2", params=sample_params, metrics=sample_metrics)
        tracker.log_experiment(name="sea-ice", params=sample_params, metrics=sample_metrics)
        result = tracker.list_experiments(name="glacier")
        assert len(result) == 2

    def test_filter_by_model(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics, model="unet")
        tracker.log_experiment(name="b", params=sample_params, metrics=sample_metrics, model="rf")
        result = tracker.list_experiments(model="unet")
        assert len(result) == 1
        assert result[0]["model"] == "unet"

    def test_filter_by_status(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics)
        result = tracker.list_experiments(status="completed")
        assert len(result) == 1
        result = tracker.list_experiments(status="running")
        assert len(result) == 0


# ---------------------------------------------------------------------------
# search_experiments
# ---------------------------------------------------------------------------

class TestSearchExperiments:
    def test_find_by_name_substring(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="glacier-segmentation", params=sample_params, metrics=sample_metrics)
        tracker.log_experiment(name="sea-ice-classification", params=sample_params, metrics=sample_metrics)
        results = tracker.search_experiments({"name": "glacier"})
        assert len(results) == 1
        assert "glacier" in results[0]["name"]

    def test_find_by_tag(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(
            name="a", params=sample_params, metrics=sample_metrics,
            tags={"dataset": "sentinel2"}
        )
        tracker.log_experiment(
            name="b", params=sample_params, metrics=sample_metrics,
            tags={"dataset": "landsat"}
        )
        results = tracker.search_experiments({"tags": {"dataset": "sentinel2"}})
        assert len(results) == 1

    def test_find_by_status(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics)
        results = tracker.search_experiments({"status": "completed"})
        assert len(results) == 1
        results = tracker.search_experiments({"status": "failed"})
        assert len(results) == 0


# ---------------------------------------------------------------------------
# tag_experiment
# ---------------------------------------------------------------------------

class TestTagExperiment:
    def test_adds_tags(self, tracker, sample_params, sample_metrics):
        eid = tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics)
        tracker.tag_experiment(eid, {"env": "gpu", "team": "ml"})
        exp = tracker.get_experiment(eid)
        assert exp.tags["env"] == "gpu"
        assert exp.tags["team"] == "ml"

    def test_overwrites_existing_tag(self, tracker, sample_params, sample_metrics):
        eid = tracker.log_experiment(
            name="a", params=sample_params, metrics=sample_metrics,
            tags={"env": "cpu"}
        )
        tracker.tag_experiment(eid, {"env": "gpu"})
        exp = tracker.get_experiment(eid)
        assert exp.tags["env"] == "gpu"


# ---------------------------------------------------------------------------
# delete_experiment
# ---------------------------------------------------------------------------

class TestDeleteExperiment:
    def test_removes_experiment(self, tracker, sample_params, sample_metrics):
        eid = tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics)
        tracker.delete_experiment(eid)
        with pytest.raises(FileNotFoundError):
            tracker.get_experiment(eid)

    def test_removes_from_index(self, tracker, sample_params, sample_metrics):
        eid = tracker.log_experiment(name="a", params=sample_params, metrics=sample_metrics)
        tracker.delete_experiment(eid)
        result = tracker.list_experiments()
        assert len(result) == 0


# ---------------------------------------------------------------------------
# export_all / import_all roundtrip
# ---------------------------------------------------------------------------

class TestExportImport:
    def test_roundtrip(self, tracker, sample_params, sample_metrics):
        tracker.log_experiment(name="exp1", params=sample_params, metrics=sample_metrics)
        tracker.log_experiment(name="exp2", params=sample_params, metrics=sample_metrics)
        with tempfile.TemporaryDirectory() as tmpdir:
            export_path = os.path.join(tmpdir, "export.json")
            tracker.export_all(export_path)
            assert os.path.exists(export_path)

            # Import into a fresh tracker
            tracker2 = ExperimentTracker(os.path.join(tmpdir, "imported"))
            count = tracker2.import_all(export_path)
            assert count == 2
            result = tracker2.list_experiments()
            assert len(result) == 2


# ---------------------------------------------------------------------------
# Experiment dataclass
# ---------------------------------------------------------------------------

class TestExperimentDataclass:
    def test_to_dict_and_back(self, sample_params, sample_metrics):
        exp = Experiment(
            name="roundtrip", model="unet",
            params=sample_params, metrics=sample_metrics,
        )
        d = exp.to_dict()
        exp2 = Experiment.from_dict(d)
        assert exp2.name == exp.name
        assert exp2.model == exp.model
        assert exp2.params == exp.params
        assert exp2.metrics == exp.metrics

    def test_duration_str_none_when_no_end(self):
        exp = Experiment(name="running")
        assert exp.duration_str is None

    def test_duration_str_when_ended(self):
        now = datetime.now(timezone.utc)
        exp = Experiment(
            name="done",
            start_time=now,
            end_time=now + timedelta(seconds=125),
        )
        assert exp.duration_str == "2m 5s"

    def test_elapsed_seconds(self):
        now = datetime.now(timezone.utc)
        exp = Experiment(
            name="done",
            start_time=now,
            end_time=now + timedelta(seconds=30),
        )
        assert exp.elapsed_seconds == 30.0

    def test_elapsed_seconds_none_when_no_end(self):
        exp = Experiment(name="running")
        assert exp.elapsed_seconds is None

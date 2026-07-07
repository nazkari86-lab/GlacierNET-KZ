"""Tests for Earth Engine export helpers without calling Earth Engine."""

import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class FakeTask:
    def __init__(self):
        self.started = False

    def start(self):
        self.started = True


class FakeImage:
    def __init__(self):
        self.to_float_calls = 0

    def toFloat(self):
        self.to_float_calls += 1
        return self


def test_export_year_to_drive_preserves_image_dtype(monkeypatch):
    """Reflectance-only Sentinel exports must stay compact uint16 images."""
    from src import data_loader

    captured = {}
    task = FakeTask()

    def to_drive(**kwargs):
        captured.update(kwargs)
        return task

    fake_ee = types.SimpleNamespace(
        EEException=Exception,
        batch=types.SimpleNamespace(Export=types.SimpleNamespace(image=types.SimpleNamespace(toDrive=to_drive))),
    )
    monkeypatch.setitem(sys.modules, "ee", fake_ee)

    image = FakeImage()
    result = data_loader.export_year_to_drive(image, 2020, aoi="aoi", prefix="sentinel2")

    assert result is task
    assert task.started is True
    assert captured["image"] is image
    assert image.to_float_calls == 0

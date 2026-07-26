"""Controlled channel projection keeps labels identical across ablations."""

from __future__ import annotations

import os

import numpy as np
import pytest

from scripts.project_patch_channels import link_label, parse_channel_indices


def test_parse_channel_indices_supports_ranges_and_singletons():
    assert parse_channel_indices("0:3,5,7:9", 10) == [0, 1, 2, 5, 7, 8]


@pytest.mark.parametrize("raw", ["", "0,0", "-1", "0:12"])
def test_parse_channel_indices_rejects_invalid_selection(raw):
    with pytest.raises(ValueError):
        parse_channel_indices(raw, 10)


def test_link_label_creates_byte_identical_hardlink(tmp_path):
    source = tmp_path / "source.npy"
    destination = tmp_path / "destination.npy"
    np.save(source, np.array([[0, 1]], dtype=np.uint8))

    link_label(source, destination)

    assert os.stat(source).st_ino == os.stat(destination).st_ino
    np.testing.assert_array_equal(np.load(destination), np.load(source))

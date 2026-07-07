"""Tests for scripts/export_stac_catalog.py — STAC 1.0.0 catalog export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.export_stac_catalog import build_collection, export_catalog


class TestStacCatalog:
    def test_build_collection_structure(self):
        coll = build_collection()
        assert coll["type"] == "Collection"
        assert coll["stac_version"] == "1.0.0"
        assert coll["id"] == "glaciernet-kz-ili-alatau"
        assert "extent" in coll
        assert len(coll["extent"]["spatial"]["bbox"]) == 1
        bbox = coll["extent"]["spatial"]["bbox"][0]
        assert len(bbox) == 4
        assert bbox[0] < bbox[2]  # west < east
        assert bbox[1] < bbox[3]  # south < north

    def test_glacier_summaries_present(self):
        coll = build_collection()
        glaciers = coll["summaries"]["glaciers"]
        assert any(g["id"] == "tuyuksu" for g in glaciers)
        tuyuksu = next(g for g in glaciers if g["id"] == "tuyuksu")
        assert tuyuksu["rgi_id"] is not None

    def test_export_writes_valid_json(self, tmp_path: Path):
        out = tmp_path / "stac" / "catalog.json"
        export_catalog(out)
        assert out.exists()
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["title"].startswith("GlacierNET-KZ")
        assert data["license"] == "MIT"

    def test_links_include_citation(self):
        coll = build_collection()
        rels = {link["rel"] for link in coll["links"]}
        assert "cite-as" in rels
        assert "license" in rels

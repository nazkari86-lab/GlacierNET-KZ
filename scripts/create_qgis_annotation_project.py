"""Create the GlacierNET-KZ annotation project from inside QGIS.

Run with the QGIS application ``--code`` option. The project references source
rasters in place, so it does not duplicate multi-gigabyte Sentinel-2 files.
"""

from __future__ import annotations

import hashlib
import json
import os
import traceback
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsContrastEnhancement,
    QgsCoordinateReferenceSystem,
    QgsMultiBandColorRenderer,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication, QTimer

ROOT = Path(os.environ["GLACIERNET_ROOT"]).resolve()
PACK = ROOT / "benchmarks/v2/annotations/enhanced_provisional"
OUTPUT = PACK / "GlacierNET-KZ_Annotation_Workspace.qgz"
YEARS = (2022, 2023, 2024)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_vector(
    project: QgsProject,
    group,
    source: str,
    name: str,
    style: Path | None = None,
    *,
    read_only: bool = True,
):
    layer = QgsVectorLayer(source, name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Invalid vector layer: {source}")
    if style and style.is_file():
        layer.loadNamedStyle(str(style))
    layer.setReadOnly(read_only)
    project.addMapLayer(layer, False)
    group.addLayer(layer)
    return layer


def add_raster(project: QgsProject, group, path: Path, name: str):
    layer = QgsRasterLayer(str(path), name)
    if not layer.isValid():
        raise RuntimeError(f"Invalid raster layer: {path}")
    project.addMapLayer(layer, False)
    group.addLayer(layer)
    return layer


def build() -> None:
    try:
        project = QgsProject.instance()
        project.clear()
        project.setTitle("GlacierNET-KZ Enhanced Provisional Annotation Workspace")
        project.setCrs(QgsCoordinateReferenceSystem("EPSG:32642"))
        try:
            project.setFilePathStorage(Qgis.FilePathType.Relative)
        except AttributeError:
            project.writeEntry("Paths", "/Absolute", False)

        root = project.layerTreeRoot()
        instructions = root.addGroup("00 · START HERE")
        add_vector(
            project,
            instructions,
            f"{ROOT / 'data/rgi/rgi_study_area.shp'}",
            "RGI 7.0 reference · not annual truth",
        )

        for year in reversed(YEARS):
            group = root.addGroup(f"{year} · annotation evidence")
            group.setItemVisibilityChecked(year == 2024)
            gpkg = PACK / f"enhanced_labels_{year}.gpkg"
            labels = add_vector(
                project,
                group,
                f"{gpkg}|layername=glacier_labels",
                f"{year} enhanced provisional labels · READ ONLY",
                PACK / "labels.qml",
            )
            labels.setCustomProperty("glaciernet/label_tier", "enhanced_provisional_multievidence")
            labels.setCustomProperty("glaciernet/prohibited_claim", "independent expert gold-label accuracy")
            add_vector(
                project,
                group,
                f"{gpkg}|layername=review_zones",
                f"{year} mandatory visual-review zones",
                PACK / "review_zones.qml",
            )
            classes = add_raster(
                project,
                group,
                PACK / f"label_classes_{year}.tif",
                f"{year} label classes · 1 label / 2 review",
            )
            classes.setOpacity(0.55)
            source = add_raster(
                project,
                group,
                ROOT / f"data/raw/sentinel2/sentinel2_{year}.tif",
                f"{year} Sentinel-2 · original 11 channels",
            )
            renderer = QgsMultiBandColorRenderer(source.dataProvider(), 3, 2, 1)
            for band, setter in (
                (3, renderer.setRedContrastEnhancement),
                (2, renderer.setGreenContrastEnhancement),
                (1, renderer.setBlueContrastEnhancement),
            ):
                enhancement = QgsContrastEnhancement(source.dataProvider().dataType(band))
                enhancement.setMinimumValue(0)
                enhancement.setMaximumValue(10_000)
                enhancement.setContrastEnhancementAlgorithm(
                    QgsContrastEnhancement.ContrastEnhancementAlgorithm.StretchToMinimumMaximum
                )
                setter(enhancement)
            source.setRenderer(renderer)
            source.setCustomProperty("glaciernet/rgb_bands", "B4=3,B3=2,B2=1")

        context = root.addGroup("Supporting context")
        context.setItemVisibilityChecked(False)
        for path, name in (
            (ROOT / "data/ancillary/terrain/terrain_features.tif", "Terrain features"),
            (ROOT / "data/ancillary/sentinel1/sentinel1_2024.tif", "Sentinel-1 2024 VV/VH"),
            (
                ROOT / "data/lakes/tien_shan_1990_2023/tien_shan_lakes_ile_alatau_1990_2023.gpkg",
                "Glacial lakes 1990–2023",
            ),
        ):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".gpkg":
                add_vector(project, context, str(path), name)
            else:
                add_raster(project, context, path, name)

        project.writeEntry("GlacierNET-KZ", "label_tier", "enhanced_provisional_multievidence")
        project.writeEntry("GlacierNET-KZ", "human_review_status", "pending")
        project.writeEntry(
            "GlacierNET-KZ",
            "instructions",
            "Read README_QGIS.md; save edits to a new pass_1 GeoPackage and never overwrite generated evidence.",
        )
        project.setFileName(str(OUTPUT))
        if not project.write():
            raise RuntimeError(f"QGIS could not write {OUTPUT}")
        manifest_path = PACK / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["qgis_project"] = {
            "path": str(OUTPUT.relative_to(ROOT)),
            "sha256": sha256(OUTPUT),
            "size_bytes": OUTPUT.stat().st_size,
            "layer_count": len(project.mapLayers()),
            "source_rasters_duplicated": False,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"QGIS annotation project created: {OUTPUT}", flush=True)
    except Exception:
        traceback.print_exc()
        os.environ["GLACIERNET_QGIS_PROJECT_ERROR"] = "1"
    finally:
        QTimer.singleShot(0, QCoreApplication.quit)


build()

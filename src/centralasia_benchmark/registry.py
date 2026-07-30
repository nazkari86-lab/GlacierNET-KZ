"""Real-source registry for CentralAsia-GlacierBench.

The registry deliberately separates local availability from scientific
independence.  A file existing on disk never upgrades a silver inventory into
independent gold evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

SourceState = Literal["verified_local", "local_unverified", "metadata_only", "missing"]


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    title: str
    role: str
    citation_url: str
    license: str
    evidence_tier: str
    local_paths: tuple[str, ...]
    metadata_paths: tuple[str, ...] = ()
    expected_sha256: str | None = None
    expected_md5: str | None = None
    notes: str = ""


SOURCES: tuple[SourceDefinition, ...] = (
    SourceDefinition(
        id="rgi7_central_asia",
        title="Randolph Glacier Inventory 7.0, region 13",
        role="silver glacier geometry and glacier identifiers",
        citation_url="https://doi.org/10.5067/F6JMOVY5NAVZ",
        license="RGI data policy",
        evidence_tier="silver_reference_not_independent_gold",
        local_paths=("data/rgi/RGI2000-v7.0-G-13_central_asia.shp",),
        notes="Region 13 is largely based on GAMDAM2; do not count GAMDAM as an independent label source.",
    ),
    SourceDefinition(
        id="sentinel2_local",
        title="Sentinel-2 harmonized surface-reflectance composites",
        role="primary optical inference and temporal evaluation",
        citation_url="https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR_HARMONIZED",
        license="Copernicus Sentinel data terms",
        evidence_tier="observed_satellite_input",
        local_paths=("data/raw/sentinel2/sentinel2_2024.tif",),
    ),
    SourceDefinition(
        id="sentinel1_local",
        title="Sentinel-1 summer composites",
        role="cloud-robust SAR evidence and cross-sensor track",
        citation_url="https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S1_GRD",
        license="Copernicus Sentinel data terms",
        evidence_tier="observed_satellite_input",
        local_paths=("data/ancillary/sentinel1/sentinel1_2024.tif",),
    ),
    SourceDefinition(
        id="glavitu_code",
        title="GlaViTU v1.0 reference implementation",
        role="profile-specific external glacier-mapping baseline",
        citation_url="https://github.com/konstantin-a-maslov/scalable_glacier_mapping/tree/v1.0",
        license="GPL-2.0",
        evidence_tier="external_model_code",
        local_paths=("data/external/centralasia_glacierbench/glavitu/scalable_glacier_mapping-v1.0.tar.gz",),
    ),
    SourceDefinition(
        id="glavitu_global_weights",
        title="GlaViTU global pretrained weights",
        role="zero-shot external model baseline",
        citation_url="https://drive.google.com/drive/folders/1PPtcBUg6Ls42bgSqpM53Ud8G2MOMV70s",
        license="Model authors' distribution terms",
        evidence_tier="external_pretrained_model",
        local_paths=("data/external/centralasia_glacierbench/glavitu/weights/glavitu_global_weights.h5",),
    ),
    SourceDefinition(
        id="glavitu_hma_weights",
        title="GlaViTU High-Mountain Asia fine-tuned weights",
        role="HMA transfer baseline",
        citation_url="https://drive.google.com/drive/folders/1PPtcBUg6Ls42bgSqpM53Ud8G2MOMV70s",
        license="Model authors' distribution terms",
        evidence_tier="external_pretrained_model",
        local_paths=("data/external/centralasia_glacierbench/glavitu/weights/glavitu_finetuning_HMA_weights.h5",),
    ),
    SourceDefinition(
        id="cryobench_gld",
        title="Cryo-Bench GLD glacial-lake task",
        role="external lake segmentation benchmark",
        citation_url="https://huggingface.co/datasets/Sk-21/Cryo-Bench",
        license="MIT benchmark packaging; source-dataset terms retained",
        evidence_tier="external_benchmark",
        local_paths=("data/external/centralasia_glacierbench/cryobench/GLD.tar.gz",),
        expected_sha256="e1a0c16f04bb545643662d345d3fdab219872a785aa4429e9301428404e543d1",
    ),
    SourceDefinition(
        id="cryobench_glid",
        title="Cryo-Bench GLID glacial-lake task",
        role="external cross-resolution lake segmentation benchmark",
        citation_url="https://huggingface.co/datasets/Sk-21/Cryo-Bench",
        license="MIT benchmark packaging; source-dataset terms retained",
        evidence_tier="external_benchmark",
        local_paths=("data/external/centralasia_glacierbench/cryobench/GLID.tar.gz",),
        notes="8.23 GB compressed; intentionally not auto-downloaded on the current 12 GB free-disk budget.",
    ),
    SourceDefinition(
        id="cryobench_gsdd",
        title="Cryo-Bench GSDD supraglacial-debris task",
        role="external debris-covered ice benchmark",
        citation_url="https://huggingface.co/datasets/Sk-21/Cryo-Bench",
        license="MIT benchmark packaging; source-dataset terms retained",
        evidence_tier="external_benchmark",
        local_paths=("data/external/centralasia_glacierbench/cryobench/GSDD.tar.gz",),
        notes="15.04 GB compressed; intentionally not auto-downloaded on the current 12 GB free-disk budget.",
    ),
    SourceDefinition(
        id="hma_lake_terminating_1990_2022",
        title="HMA lake-terminating glaciers and proglacial lakes, 1990-2022",
        role="expert-validated retrospective glacier-lake coupling evidence",
        citation_url="https://doi.org/10.5281/zenodo.17369580",
        license="Zenodo record terms",
        evidence_tier="external_expert_validated_inventory",
        local_paths=("data/external/centralasia_glacierbench/hma_ltg/HMA_LTG.gpkg",),
        expected_md5="47531c9c39d50bdcad480d5b7dde5930",
    ),
    SourceDefinition(
        id="hmaglofdb",
        title="HMAGLOFDB v1.3.0",
        role="retrospective GLOF event cohort",
        citation_url="https://doi.org/10.5281/zenodo.7271188",
        license="CC-BY-4.0",
        evidence_tier="observed_event_database",
        local_paths=("data/events/hmaglofdb/source/fidelsteiner-HMAGLOFDB-1d975de/Database/GLOFs/HMAGLOFDB.csv",),
    ),
    SourceDefinition(
        id="hugonnet_dhdt",
        title="Global glacier elevation change 2000-2019",
        role="independent geodetic thinning evidence",
        citation_url="https://doi.org/10.6096/13",
        license="Theia product terms",
        evidence_tier="independent_physical_observation",
        local_paths=(
            "data/external/centralasia_glacierbench/hugonnet/"
            "hugonnet_2021_ds_rgi60_pergla_rates_10_20_worldwide_filled.hdf",
        ),
        notes="Official per-glacier geodetic rates use RGI6 identifiers; spatial matching to RGI7 must be reported.",
    ),
    SourceDefinition(
        id="itslive_velocity",
        title="NASA ITS_LIVE regional glacier velocity",
        role="independent dynamic glacier evidence",
        citation_url="https://doi.org/10.5067/6II6VW8LLWJ7",
        license="NASA Earthdata terms",
        evidence_tier="independent_physical_observation",
        local_paths=("data/external/centralasia_glacierbench/itslive/velocity_samples.parquet",),
        metadata_paths=("data/external/centralasia_glacierbench/itslive/stac_cubes.json",),
        notes="A STAC catalogue proves coverage discovery only. The source becomes local evidence after velocity samples are materialised.",
    ),
    SourceDefinition(
        id="oggm_rgi7",
        title="OGGM 1.6 RGI7 preprocessed glacier directories",
        role="modelled thickness, volume, mass balance and runoff scenarios",
        citation_url="https://docs.oggm.org/en/stable/shop-preprodirs.html",
        license="OGGM and upstream data terms",
        evidence_tier="physics_model_output_not_observation",
        local_paths=("data/external/centralasia_glacierbench/oggm/",),
    ),
)


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _resolve_existing(root: Path, candidates: tuple[str, ...]) -> Path | None:
    for relative in candidates:
        path = root / relative
        if path.is_file():
            return path
        if path.is_dir() and any(path.iterdir()):
            return path
    return None


def build_source_registry(project_root: str | Path) -> list[dict[str, object]]:
    """Inspect every declared source and return evidence-safe readiness."""
    root = Path(project_root).resolve()
    rows: list[dict[str, object]] = []
    for definition in SOURCES:
        path = _resolve_existing(root, definition.local_paths)
        metadata_path = _resolve_existing(root, definition.metadata_paths)
        state: SourceState = "missing"
        digest: str | None = None
        size_bytes = 0
        integrity = "not_checked"
        if path is not None:
            if path.is_file():
                size_bytes = path.stat().st_size
                if definition.expected_sha256:
                    digest = _digest(path, "sha256")
                    integrity = "verified" if digest == definition.expected_sha256 else "checksum_mismatch"
                elif definition.expected_md5:
                    digest = _digest(path, "md5")
                    integrity = "verified" if digest == definition.expected_md5 else "checksum_mismatch"
                else:
                    digest = _digest(path, "sha256")
                    integrity = "computed_without_upstream_digest"
            else:
                size_bytes = sum(item.stat().st_size for item in path.rglob("*") if item.is_file())
                integrity = "directory_present"
            state = (
                "verified_local"
                if integrity in {"verified", "computed_without_upstream_digest"}
                else "local_unverified"
            )
            if integrity == "checksum_mismatch":
                state = "local_unverified"
        elif metadata_path is not None:
            path = metadata_path
            size_bytes = path.stat().st_size if path.is_file() else 0
            digest = _digest(path, "sha256") if path.is_file() else None
            integrity = "metadata_digest_computed"
            state = "metadata_only"
        row = asdict(definition)
        row.update(
            {
                "state": state,
                "available": state in {"verified_local", "local_unverified"},
                "local_path": str(path.relative_to(root)) if path is not None else None,
                "size_bytes": size_bytes,
                "integrity": integrity,
                "digest": digest,
            }
        )
        rows.append(row)
    return rows

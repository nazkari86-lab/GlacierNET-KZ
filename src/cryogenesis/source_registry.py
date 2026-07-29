"""Content-addressed registry for local physical CryoGenesis inputs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .schemas import SourceAsset

REQUIRED_SOURCE_PATHS = {
    "rgi": Path("data/rgi/rgi_study_area.shp"),
    "era5_land": Path("data/climate/era5_land_2000_2025_monthly.nc"),
    "copdem": Path("data/ancillary/copdem"),
    "predictions": Path("predictions"),
}
_SHAPEFILE_SUFFIXES = (".shp", ".shx", ".dbf", ".prj", ".cpg")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class RegisteredSource:
    source_id: str
    relative_path: str
    sha256: str
    size_bytes: int

    @classmethod
    def from_path(
        cls,
        source_id: str,
        path: Path,
        project_root: Path,
    ) -> "RegisteredSource":
        resolved_root = project_root.resolve()
        resolved_path = path.resolve()
        if not resolved_path.is_file():
            raise ValueError(f"missing source: {path}")
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError(f"source escapes project root: {path}")
        return cls(
            source_id=source_id,
            relative_path=resolved_path.relative_to(resolved_root).as_posix(),
            sha256=sha256_file(resolved_path),
            size_bytes=resolved_path.stat().st_size,
        )

    def as_asset(self) -> SourceAsset:
        return SourceAsset(
            source_id=self.source_id,
            relative_path=self.relative_path,
            sha256=self.sha256,
            size_bytes=self.size_bytes,
        )


def verify_sources(
    sources: tuple[RegisteredSource, ...],
    project_root: Path,
) -> None:
    """Recompute every digest and fail before scientific processing."""

    root = project_root.resolve()
    for source in sources:
        path = (root / source.relative_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"missing registered source: {source.relative_path}")
        if path.stat().st_size != source.size_bytes:
            raise ValueError(
                f"source checksum/size changed: {source.relative_path}"
            )
        if sha256_file(path) != source.sha256:
            raise ValueError(f"source checksum changed: {source.relative_path}")


def register_required_sources(
    project_root: Path,
) -> tuple[RegisteredSource, ...]:
    """Register all required files, including every RGI sidecar."""

    root = project_root.resolve()
    registered: list[RegisteredSource] = []
    for source_id, relative_path in REQUIRED_SOURCE_PATHS.items():
        absolute = root / relative_path
        if source_id == "rgi":
            paths = [
                absolute.with_suffix(suffix) for suffix in _SHAPEFILE_SUFFIXES
            ]
        elif absolute.is_dir():
            paths = sorted(path for path in absolute.rglob("*") if path.is_file())
        else:
            paths = [absolute]
        if not paths or any(not path.is_file() for path in paths):
            raise ValueError(f"missing required source family: {source_id}")
        for index, path in enumerate(paths):
            item_id = source_id if len(paths) == 1 else f"{source_id}:{index}"
            registered.append(
                RegisteredSource.from_path(item_id, path, root)
            )
    return tuple(registered)


def preflight_sources(project_root: Path) -> dict[str, dict[str, object]]:
    """Return exact local readiness without downloading or fabricating data."""

    root = project_root.resolve()
    report: dict[str, dict[str, object]] = {}
    for source_id, relative_path in REQUIRED_SOURCE_PATHS.items():
        path = root / relative_path
        if source_id == "rgi":
            paths = [
                path.with_suffix(suffix) for suffix in _SHAPEFILE_SUFFIXES
            ]
        elif path.is_dir():
            paths = sorted(item for item in path.rglob("*") if item.is_file())
        else:
            paths = [path]
        missing = [
            item.relative_to(root).as_posix()
            for item in paths
            if not item.is_file()
        ]
        report[source_id] = {
            "status": "ready" if paths and not missing else "missing",
            "path": relative_path.as_posix(),
            "file_count": sum(item.is_file() for item in paths),
            "missing": missing,
        }
    return report

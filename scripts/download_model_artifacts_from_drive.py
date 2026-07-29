#!/usr/bin/env python3
"""Restore ignored SavedModel artifacts from the dated Google Drive archive."""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from download_drive import build_drive_service, download_file  # noqa: E402

FOLDER_MIME = "application/vnd.google-apps.folder"
DEFAULT_ARCHIVE = "GlacierNET-KZ-archive-2026-07-14"
DEFAULT_MODELS = (
    "unet_best_sentinel2_multiyear_sample_2016_2024",
    "unet_final_sentinel2_multiyear_sample_2016_2024",
    "unet_best_sentinel2_terrain_year_holdout_2016_2024",
    "unet_final_sentinel2_terrain_year_holdout_2016_2024",
)


def find_folder(drive: Any, name: str, parent: str | None = None) -> dict[str, Any]:
    escaped = name.replace("\\", "\\\\").replace("'", "\\'")
    clauses = [
        f"name = '{escaped}'",
        f"mimeType = '{FOLDER_MIME}'",
        "trashed = false",
    ]
    if parent:
        clauses.append(f"'{parent}' in parents")
    result = (
        drive.files()
        .list(
            q=" and ".join(clauses),
            fields="files(id,name,parents)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    files = result.get("files", [])
    if len(files) != 1:
        raise RuntimeError(f"Expected exactly one Drive folder named {name!r}; found {len(files)}")
    return files[0]


def list_files(drive: Any, folder_id: str) -> list[dict[str, Any]]:
    result = (
        drive.files()
        .list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id,name,size,md5Checksum,mimeType)",
            pageSize=100,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )
        .execute()
    )
    files = result.get("files", [])
    folders = [item["name"] for item in files if item.get("mimeType") == FOLDER_MIME]
    unexpected = sorted(set(folders) - {"assets", "variables"})
    if unexpected:
        raise RuntimeError(f"Unexpected nested folders in SavedModel: {unexpected}")
    return files


def md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - Drive exposes MD5 for transport verification
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_model_files(drive: Any, model_folder: dict[str, Any]) -> list[tuple[dict[str, Any], Path]]:
    destination = ROOT / "models" / model_folder["name"]
    jobs: list[tuple[dict[str, Any], Path]] = []
    for item in list_files(drive, model_folder["id"]):
        if item.get("mimeType") == FOLDER_MIME:
            child_dir = destination / item["name"]
            for child in list_files(drive, item["id"]):
                if child.get("mimeType") == FOLDER_MIME:
                    raise RuntimeError(f"Unexpected nested folder: {child['name']}")
                jobs.append((child, child_dir / child["name"]))
        else:
            jobs.append((item, destination / item["name"]))
    return jobs


def restore_one(item: dict[str, Any], destination: Path, retries: int) -> tuple[Path, str]:
    expected_size = int(item["size"])
    expected_md5 = item.get("md5Checksum")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and destination.stat().st_size == expected_size:
        if not expected_md5 or md5(destination) == expected_md5:
            return destination, "already verified"

    last_error = "unknown error"
    for attempt in range(1, retries + 1):
        try:
            drive, credentials = build_drive_service()
            if download_file(drive, credentials, item["id"], str(destination), expected_size):
                if expected_md5 and md5(destination) != expected_md5:
                    destination.unlink(missing_ok=True)
                    raise RuntimeError("MD5 mismatch after download")
                return destination, f"downloaded and verified on attempt {attempt}"
            last_error = "size mismatch"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(min(2**attempt, 30))
    raise RuntimeError(f"{destination}: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", default=DEFAULT_ARCHIVE)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("models", nargs="*", default=list(DEFAULT_MODELS))
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")

    drive, _ = build_drive_service()
    archive = find_folder(drive, args.archive)
    models_folder = find_folder(drive, "models", archive["id"])
    model_folders = [find_folder(drive, name, models_folder["id"]) for name in args.models]
    jobs = [job for folder in model_folders for job in collect_model_files(drive, folder)]

    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(restore_one, item, destination, args.retries): destination for item, destination in jobs}
        for future in as_completed(futures):
            destination = futures[future]
            try:
                path, status = future.result()
                print(f"OK {path.relative_to(ROOT)}: {status}", flush=True)
            except Exception as exc:
                failures.append(f"{destination.relative_to(ROOT)}: {exc}")
                print(f"FAILED {failures[-1]}", flush=True)

    if failures:
        print(f"Model restoration failed for {len(failures)} file(s).")
        return 1
    print(f"Restored and MD5-verified {len(jobs)} SavedModel files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

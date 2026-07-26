#!/usr/bin/env python3
"""Download completed Sentinel-1 exports listed in the local export manifest."""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from download_drive import build_drive_service, download_file, list_tif_files  # noqa: E402

MANIFEST_PATH = ROOT / "data/ancillary/sentinel1/export_manifest.json"
OUTPUT_DIR = ROOT / "data/ancillary/sentinel1"


def expected_entries(manifest: dict) -> dict[str, dict]:
    """Return remote filenames whose completed exports can be downloaded."""
    return {
        entry["expected_filename"]: entry
        for entry in manifest.get("entries", [])
        if entry.get("state") in {"submitted", "ready", "downloaded"}
    }


def update_entry_after_download(entry: dict, path: Path, size: int) -> None:
    try:
        local_path = str(path.relative_to(ROOT))
    except ValueError:
        local_path = str(path)
    entry.update(
        {
            "state": "downloaded",
            "local_path": local_path,
            "bytes": size,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--retries", type=int, default=10)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")

    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    wanted = expected_entries(manifest)
    if not wanted:
        print("No submitted Sentinel-1 exports in manifest.")
        return 0

    drive, creds = build_drive_service()
    remote_files = {item["name"]: item for item in list_tif_files(drive)}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    pending = []
    jobs: list[tuple[str, dict, dict, int, Path]] = []

    for name, entry in wanted.items():
        remote = remote_files.get(name)
        if remote is None:
            pending.append(name)
            continue
        expected_size = int(remote.get("size", 0))
        target = OUTPUT_DIR / name
        if args.dry_run:
            print(f"Would download {name} ({expected_size / 1e6:.1f} MB)")
            continue
        if target.exists() and target.stat().st_size == expected_size:
            update_entry_after_download(entry, target, expected_size)
            print(f"Already verified {name} ({expected_size / 1e6:.1f} MB)")
            downloaded += 1
            continue
        jobs.append((name, entry, remote, expected_size, target))

    def download_one(job: tuple[str, dict, dict, int, Path]) -> tuple[str, bool]:
        name, entry, remote, expected_size, target = job
        for attempt in range(1, args.retries + 1):
            try:
                print(f"Downloading {name} ({expected_size / 1e6:.1f} MB), attempt {attempt}", flush=True)
                if download_file(drive, creds, remote["id"], str(target), expected_size):
                    update_entry_after_download(entry, target, expected_size)
                    return name, True
            except Exception as exc:
                print(f"{name}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            time.sleep(min(2**attempt, 30))
        return name, False

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_one, job) for job in jobs]
        for future in as_completed(futures):
            name, ok = future.result()
            if ok:
                downloaded += 1
            else:
                print(f"Rejected incomplete download after retries: {name}", file=sys.stderr)

    if not args.dry_run:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Downloaded or verified: {downloaded}")
    if pending:
        print("Still pending in Google Drive: " + ", ".join(sorted(pending)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

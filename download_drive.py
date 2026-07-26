"""Download Landsat/Sentinel GeoTIFFs from a shared Google Drive folder."""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from typing import Any

BASE = os.getenv("GLACIERNET_KZ_ROOT", "")
if not BASE:
    BASE = os.path.dirname(os.path.abspath(__file__))

FOLDER_ID = "1VILhFtTM90Mttyg_OEcx5u8lc6wErNDO"


def refresh_token() -> str:
    import ssl
    import urllib.parse
    import urllib.request

    gee_path = os.path.expanduser("~/.config/earthengine/credentials")
    with open(gee_path) as f:
        data = json.load(f)
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not client_secret:
        try:
            from ee.oauth import CLIENT_ID, CLIENT_SECRET

            client_id = CLIENT_ID
            client_secret = CLIENT_SECRET
        except ImportError:
            print("ERROR: GOOGLE_CLIENT_SECRET not set and ee.oauth unavailable.", file=sys.stderr)
            sys.exit(1)
    else:
        client_id = data.get(
            "client_id",
            "517222506229-vsmmajv00ul0bs7p89v5m89qs8eb9359.apps.googleusercontent.com",
        )
    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": data["refresh_token"],
            "grant_type": "refresh_token",
        }
    ).encode()
    ctx = ssl.create_default_context()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read())["access_token"]


def build_drive_service():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from ee.oauth import CLIENT_ID, CLIENT_SECRET

    gee_path = os.path.expanduser("~/.config/earthengine/credentials")
    with open(gee_path, encoding="utf-8") as f:
        data = json.load(f)
    print("Refreshing Google Drive credentials...", flush=True)
    creds = Credentials(
        token=None,
        refresh_token=data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=data.get("scopes", ["https://www.googleapis.com/auth/drive"]),
    )
    creds.refresh(__import__("google.auth.transport.requests", fromlist=["Request"]).Request())
    print("Token OK", flush=True)
    import httplib2
    from google_auth_httplib2 import AuthorizedHttp

    authorized_http = AuthorizedHttp(creds, http=httplib2.Http(timeout=120))
    return build("drive", "v3", http=authorized_http, cache_discovery=False), creds


def list_tif_files(drive: Any) -> list[dict[str, Any]]:
    results = (
        drive.files()
        .list(
            q=f"'{FOLDER_ID}' in parents and (name contains '.tif')",
            pageSize=30,
            fields="files(id, name, size)",
        )
        .execute()
    )
    return sorted(results.get("files", []), key=lambda x: x["name"])


def output_dir_for(name: str) -> str | None:
    if name.startswith("sentinel2"):
        return os.path.join(BASE, "data/raw/sentinel2")
    if name.startswith("landsat"):
        return os.path.join(BASE, "data/raw/landsat")
    return None


def download_file(drive: Any, creds: Any, file_id: str, out_path: str, expected: int) -> bool:
    """Download with byte-range resume and atomic finalization."""
    import requests

    t0 = time.time()
    partial_path = out_path + ".part"
    offset = os.path.getsize(partial_path) if os.path.exists(partial_path) else 0
    if offset > expected:
        offset = 0
        open(partial_path, "wb").close()
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    headers = {"Authorization": f"Bearer {creds.token}"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    response = requests.get(url, headers=headers, stream=True, timeout=(30, 120))
    response.raise_for_status()
    resumed = offset > 0 and response.status_code == 206
    if offset and not resumed:
        # Drive ignored Range; never append a full response to a partial file.
        offset = 0
    mode = "ab" if resumed else "wb"
    with open(partial_path, mode) as fp:
        for chunk in response.iter_content(chunk_size=16 * 1024 * 1024):
            if chunk:
                fp.write(chunk)
                fp.flush()
    elapsed = time.time() - t0
    actual = os.path.getsize(partial_path)
    mbps = (expected / 1e6) / elapsed if elapsed > 0 else 0
    ok = actual == expected
    print(
        f"    Done ({actual / 1e6:.0f} MB, {elapsed:.0f}s, {mbps:.1f} MB/s, ok={'yes' if ok else 'NO'})",
        flush=True,
    )
    if ok:
        os.replace(partial_path, out_path)
    return ok


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=3, help="parallel Drive downloads")
    parser.add_argument("--retries", type=int, default=20, help="restarts per file")
    parser.add_argument("--retry-delay", type=int, default=20, help="base delay between retries")
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")

    drive, _ = build_drive_service()
    files = list_tif_files(drive)
    total = len(files)
    jobs = []
    duplicate_counts: dict[str, int] = defaultdict(int)
    for f in files:
        duplicate_counts[f["name"]] += 1
    duplicate_seen: dict[str, int] = defaultdict(int)
    for f in sorted(files, key=lambda item: (item["name"], -int(item.get("size", 0)))):
        # Drive can expose duplicate names (full + subset exports). Keep the
        # largest artifact at the canonical path expected by the pipeline and
        # route smaller duplicates to an explicit subset filename.
        original_name = f["name"]
        if duplicate_counts[original_name] > 1:
            duplicate_seen[original_name] += 1
            if duplicate_seen[original_name] > 1:
                f = dict(f)
                f["name"] = original_name.replace(".tif", "_subset.tif")
        out_dir = output_dir_for(f["name"])
        if out_dir is not None:
            jobs.append((f["name"], f["id"], int(f.get("size", 0)), out_dir))

    def download_one(job: tuple[str, str, int, str]) -> tuple[str, bool, str]:
        name, file_id, expected, out_dir = job
        out_path = os.path.join(out_dir, name)
        os.makedirs(out_dir, exist_ok=True)
        if os.path.exists(out_path) and os.path.getsize(out_path) == expected:
            return name, True, "already complete"
        last_error = "unknown error"
        for attempt in range(1, args.retries + 1):
            try:
                # Each worker gets its own authenticated service; transports
                # are not shared between threads.
                worker_drive, worker_creds = build_drive_service()
                ok = download_file(worker_drive, worker_creds, file_id, out_path, expected)
                if ok:
                    return name, True, f"downloaded on attempt {attempt}"
                last_error = "size mismatch"
            except Exception as exc:  # keep retrying this file
                last_error = f"{type(exc).__name__}: {exc}"
            delay = min(args.retry_delay * (2 ** min(attempt - 1, 5)), 600)
            current = os.path.getsize(out_path + ".part") if os.path.exists(out_path + ".part") else 0
            print(f"  {name}: attempt {attempt} failed ({last_error}); resume at {current} bytes in {delay}s", flush=True)
            time.sleep(delay)
        return name, False, f"failed after {args.retries} attempts: {last_error}"

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_one, job) for job in jobs]
        for future in as_completed(futures):
            name, ok, message = future.result()
            done += 1
            print(f"  [{done}/{len(jobs)}] {name}: {'OK' if ok else 'FAILED'} ({message})", flush=True)

    print(f"\nAll done! {done}/{len(jobs)} files processed with {args.workers} workers.")
    return 0 if done == len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())

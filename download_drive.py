"""Download Landsat/Sentinel GeoTIFFs from a shared Google Drive folder."""

from __future__ import annotations

import json
import os
import sys
import time
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

    print("Refreshing token...", flush=True)
    access_token = refresh_token()
    print("Token OK", flush=True)
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds)


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


def download_file(drive: Any, file_id: str, out_path: str, expected: int) -> bool:
    from googleapiclient.http import MediaIoBaseDownload

    request = drive.files().get_media(fileId=file_id)
    t0 = time.time()
    with open(out_path, "wb") as fp:
        downloader = MediaIoBaseDownload(fp, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    elapsed = time.time() - t0
    actual = os.path.getsize(out_path)
    mbps = (expected / 1e6) / elapsed if elapsed > 0 else 0
    ok = actual == expected
    print(
        f"    Done ({actual / 1e6:.0f} MB, {elapsed:.0f}s, {mbps:.1f} MB/s, ok={'yes' if ok else 'NO'})",
        flush=True,
    )
    return ok


def main() -> int:
    drive = build_drive_service()
    files = list_tif_files(drive)
    total = len(files)
    done = 0

    for f in files:
        name = f["name"]
        file_id = f["id"]
        expected = int(f.get("size", 0))
        out_dir = output_dir_for(name)
        if out_dir is None:
            print(f"  [{done}/{total}] Skip {name}")
            done += 1
            continue

        out_path = os.path.join(out_dir, name)
        if os.path.exists(out_path) and os.path.getsize(out_path) == expected:
            print(f"  [{done}/{total}] {name}: already OK ({expected / 1e6:.0f} MB)")
            done += 1
            continue

        os.makedirs(out_dir, exist_ok=True)
        print(f"  [{done}/{total}] Downloading {name} ({expected / 1e6:.0f} MB)...", flush=True)
        download_file(drive, file_id, out_path, expected)
        done += 1

    print(f"\nAll done! {done}/{total} files processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Single reproducible entry point for CentralAsia-GlacierBench."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(script: str, *arguments: str) -> None:
    command = [PYTHON, str(ROOT / "scripts" / script), *arguments]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--full",
        action="store_true",
        help="sync real sources and execute external GLD/GlaViTU tracks before building",
    )
    parser.add_argument(
        "--include-large",
        action="store_true",
        help="also request disk-gated GLID/GSDD archives",
    )
    parser.add_argument(
        "--glavitu-strategy",
        choices=["global", "hma", "both"],
        default="both",
    )
    args = parser.parse_args()

    if args.full:
        sync_arguments = ["--include-large"] if args.include_large else []
        run("sync_centralasia_glacierbench.py", *sync_arguments)
        run("materialize_itslive_samples.py")
        run("run_cryobench_gld_baseline.py")
        strategies = ("global", "hma") if args.glavitu_strategy == "both" else (args.glavitu_strategy,)
        for strategy in strategies:
            run("run_glavitu_zhetysu_baseline.py", "--strategy", strategy)
    run("build_centralasia_glacierbench.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

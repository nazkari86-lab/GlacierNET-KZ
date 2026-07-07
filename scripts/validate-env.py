#!/usr/bin/env python3
"""Environment validation script for GlacierNET-KZ.

Checks all required services and dependencies before deployment.
Run with: python scripts/validate-env.py
"""

import subprocess
import sys
from pathlib import Path


class Colors:
    OK = "\033[92m"
    WARN = "\033[93m"
    FAIL = "\033[91m"
    END = "\033[0m"


def check(name: str, ok: bool, msg: str = "") -> bool:
    symbol = f"{Colors.OK}✓{Colors.END}" if ok else f"{Colors.FAIL}✗{Colors.END}"
    print(f"  {symbol} {name}" + (f" — {msg}" if msg else ""))
    return ok


def check_docker() -> bool:
    print("\n[1] Docker")
    try:
        out = subprocess.check_output(["docker", "--version"], text=True)
        check("docker", True, out.strip())
    except FileNotFoundError:
        check("docker", False, "not installed")
        return False

    try:
        out = subprocess.check_output(["docker", "compose", "version"], text=True)
        check("docker compose", True, out.strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        check("docker compose", False, "not available")
        return False

    return True


def check_python() -> bool:
    print("\n[2] Python")
    ver = sys.version_info
    ok = ver >= (3, 10)
    check("python >= 3.10", ok, f"{ver.major}.{ver.minor}.{ver.micro}")
    return ok


def check_node() -> bool:
    print("\n[3] Node.js")
    try:
        out = subprocess.check_output(["node", "--version"], text=True).strip()
        ver = tuple(int(x.lstrip("v")) for x in out.lstrip("v").split(".")[:2])
        ok = ver >= (18, 0)
        check("node >= 18", ok, out)
    except FileNotFoundError:
        check("node", False, "not installed")
        return False

    try:
        out = subprocess.check_output(["npm", "--version"], text=True).strip()
        check("npm", True, out)
    except FileNotFoundError:
        check("npm", False, "not installed")
        return False

    return True


def check_conda() -> bool:
    print("\n[4] Conda (for geospatial libs)")
    try:
        out = subprocess.check_output(["conda", "--version"], text=True).strip()
        check("conda", True, out)
        return True
    except FileNotFoundError:
        check("conda", False, "not installed (needed for gdal, rasterio, geopandas)")
        return False


def check_env_files() -> bool:
    print("\n[5] Environment files")
    all_ok = True
    root = Path(__file__).resolve().parent.parent

    api_env = root / "glacierkz-api" / ".env"
    api_example = root / "glacierkz-api" / ".env.example"
    web_env = root / "glacierkz-web" / ".env.local"
    web_example = root / "glacierkz-web" / ".env.example"

    if api_env.exists():
        check("glacierkz-api/.env", True, "exists")
    elif api_example.exists():
        check("glacierkz-api/.env", False, "missing — copy from .env.example")
        all_ok = False
    else:
        check("glacierkz-api/.env", False, "missing (no .env.example either)")
        all_ok = False

    if web_env.exists():
        check("glacierkz-web/.env.local", True, "exists")
    elif web_example.exists():
        check("glacierkz-web/.env.local", False, "missing — copy from .env.example")
        all_ok = False
    else:
        check("glacierkz-web/.env.local", False, "missing (no .env.example either)")
        all_ok = False

    return all_ok


def check_api_key_exposure() -> bool:
    print("\n[6] Security — API key exposure")
    root = Path(__file__).resolve().parent.parent

    dangerous = [
        "sk-or-v1-",
        "sk-proj-",
        "AKIA",
        "ghp_",
        "gho_",
    ]

    found = []
    for pattern in dangerous:
        for f in root.rglob("*.py"):
            if "__pycache__" in str(f) or "node_modules" in str(f):
                continue
            try:
                content = f.read_text(errors="ignore")
                if pattern in content:
                    found.append((str(f.relative_to(root)), pattern))
            except Exception:
                pass

    if not found:
        check("no hardcoded secrets", True)
        return True

    for path, pat in found:
        check("hardcoded secret", False, f"{pat} in {path}")
    return False


def check_disk_space() -> bool:
    print("\n[7] Disk space")
    root = Path(__file__).resolve().parent.parent
    import shutil

    usage = shutil.disk_usage(str(root))
    free_gb = usage.free / (1024 ** 3)
    ok = free_gb > 10
    check("free disk >= 10 GB", ok, f"{free_gb:.1f} GB free")
    return ok


def main():
    print("=" * 50)
    print("GlacierNET-KZ — Environment Validation")
    print("=" * 50)

    results = []
    results.append(("Docker", check_docker()))
    results.append(("Python", check_python()))
    results.append(("Node.js", check_node()))
    results.append(("Conda", check_conda()))
    results.append(("Env files", check_env_files()))
    results.append(("Security", check_api_key_exposure()))
    results.append(("Disk", check_disk_space()))

    print("\n" + "=" * 50)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    if passed == total:
        print(f"{Colors.OK}All checks passed ({passed}/{total}){Colors.END}")
        return 0
    else:
        failed = [name for name, ok in results if not ok]
        print(f"{Colors.FAIL}{total - passed} check(s) failed: {', '.join(failed)}{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

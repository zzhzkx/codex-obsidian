#!/usr/bin/env python3
"""Cross-platform test runner for codex-obsidian.

Runs every ``tests/test_*.py`` file in its own process. On native Windows,
upstream tests that need POSIX symlink privileges or bash are reported as
SKIP instead of failing the run; everything else must pass.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ENVIRONMENT_SKIP_MARKERS = (
    "WinError 1314",
    "requires Developer Mode",
    "/bin/bash:",
    "NotImplementedError: directories",
)

POSIX_ONLY = {
    "test_checkpoint.py": "git checkpointing is Linux/macOS-only upstream",
    "test_legacy_lock.py": "deprecated v1 lock API requires POSIX dirfd",
    "test_setup_multi_agent.py": "exercises the legacy bash installer",
    "test_setup_retrieve.py": "exercises the legacy bash wrapper",
    "test_setup_vault.py": "exercises the legacy bash wrapper",
    "test_setup_wrappers.py": "exercises the legacy bash wrappers",
}


def _run(path: Path, timeout: int) -> tuple[str, str, int]:
    environment = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    }
    completed = subprocess.run(
        [sys.executable, str(path)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    return completed.stdout, completed.stderr, completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Python test suite.")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    files = sorted((ROOT / "tests").glob("test_*.py"))
    if not files:
        print("ERROR: no tests/test_*.py files found", file=sys.stderr)
        return 2

    passed: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []
    for path in files:
        if os.name == "nt" and path.name in POSIX_ONLY:
            skipped.append(path.name)
            print(f"SKIP {path.name} ({POSIX_ONLY[path.name]})")
            continue
        try:
            stdout, stderr, code = _run(path, args.timeout)
        except subprocess.TimeoutExpired:
            failed.append((path.name, "timeout"))
            print(f"TIMEOUT {path.name}", file=sys.stderr)
            continue
        output = stdout + stderr
        if code == 0:
            passed.append(path.name)
            print(f"PASS {path.name}")
            if args.verbose and output.strip():
                print(output.rstrip())
            continue
        if os.name == "nt" and any(
            marker in output for marker in ENVIRONMENT_SKIP_MARKERS
        ):
            skipped.append(path.name)
            print(f"SKIP {path.name} (needs POSIX symlink privileges or bash)")
            continue
        failed.append((path.name, output[-4000:]))
        print(f"FAIL {path.name}", file=sys.stderr)

    print(
        f"\n{len(passed)} passed, {len(skipped)} skipped, {len(failed)} failed"
    )
    for name, detail in failed:
        print(f"\n===== {name} =====\n{detail}", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())

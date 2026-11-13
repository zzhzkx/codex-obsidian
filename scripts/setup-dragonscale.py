#!/usr/bin/env python3
"""Cross-platform wrapper for dry-run-first DragonScale state provisioning."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "scripts" / "codex-obsidian.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan or create missing DragonScale compatibility state."
    )
    parser.add_argument("--vault")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--generated-at")
    parser.add_argument("--approved-plan-sha256")
    args = parser.parse_args(argv)
    if args.check and args.apply:
        print("ERROR: --check cannot be combined with --apply", file=sys.stderr)
        return 2
    command = ["extension", "dragonscale"]
    if args.vault:
        command.extend(["--vault", args.vault])
    if args.check:
        command.append("--check")
    if args.apply:
        command.append("--apply")
    if args.approved_plan_sha256:
        command.extend(["--approved-plan-sha256", args.approved_plan_sha256])
    if args.generated_at:
        command.extend(["--generated-at", args.generated_at])
    return subprocess.call([sys.executable, str(CLI), *command])


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Cross-platform wrapper for reviewed vault initialization or adoption."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
CLI = PLUGIN_ROOT / "scripts" / "codex-obsidian.py"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Preview, review, then apply a vault setup operation."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--init", action="store_true")
    action.add_argument("--adopt", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--vault")
    parser.add_argument("vault_path", nargs="?")
    parser.add_argument("--approved-plan-sha256")
    parser.add_argument("--generated-at")
    parser.add_argument("--operation-id")
    args = parser.parse_args(argv)

    if args.vault and args.vault_path:
        print("ERROR: use either --vault or a positional path, not both", file=sys.stderr)
        return 2
    vault = args.vault or args.vault_path
    if args.check:
        command = ["doctor"]
        if vault:
            command.extend(["--vault", vault])
        return subprocess.call([sys.executable, str(CLI), *command])

    if args.init:
        action_name = "init"
    elif args.adopt:
        action_name = "adopt"
    else:
        action_name = "adopt" if vault and Path(vault).expanduser().is_dir() else "init"
    command = [action_name]
    if vault:
        command.append(vault)
    if args.force:
        command.append("--force")
    if args.generated_at:
        command.extend(["--generated-at", args.generated_at])
    if args.operation_id:
        command.extend(["--operation-id", args.operation_id])
    if args.apply or args.force:
        if not args.approved_plan_sha256:
            print(
                "ERROR: apply requires --approved-plan-sha256 from the reviewed preview",
                file=sys.stderr,
            )
            return 2
        command.extend(
            ["--approved-plan-sha256", args.approved_plan_sha256, "--apply"]
        )
    return subprocess.call([sys.executable, str(CLI), *command])


if __name__ == "__main__":
    raise SystemExit(main())

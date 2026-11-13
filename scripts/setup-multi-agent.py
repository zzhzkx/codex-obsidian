#!/usr/bin/env python3
"""Link the portable skills into host discovery directories.

This is the cross-platform replacement for ``scripts/setup-multi-agent.sh``.
It never replaces an existing file or a link that points elsewhere. On Windows
it uses a directory junction, which does not require Developer Mode.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"

HOST_ROOTS = {
    "codex": ("home", ".agents/skills"),
    "opencode": ("home", ".config/opencode/skills"),
    "gemini": ("home", ".gemini/skills"),
    "zcode": ("home", ".zcode/skills"),
    "cursor": ("workspace", ".cursor/skills"),
    "windsurf": ("workspace", ".windsurf/skills"),
}


def _is_junction(path: Path) -> bool:
    if os.name != "nt" or not path.is_dir():
        return False
    try:
        import ctypes

        attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    except Exception:
        return False
    return attributes != -1 and bool(attributes & 0x400)


def _create_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.symlink(source, destination, target_is_directory=True)
        return
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(destination), str(source)],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise OSError(completed.stderr.strip() or "cannot create a directory junction")


def _confined_parent(destination: Path, workspace: Path) -> bool:
    try:
        destination.relative_to(workspace)
    except ValueError:
        return False
    cursor = workspace
    for part in destination.relative_to(workspace).parts[:-1]:
        cursor = cursor / part
        if cursor.exists() and (cursor.is_symlink() or not cursor.is_dir()):
            return False
    return True


def _inspect(
    host: str,
    source: Path,
    destination: Path,
    *,
    apply: bool,
    workspace: Path | None,
) -> int:
    if destination.is_symlink():
        existing = os.readlink(destination)
        resolved = Path(existing)
        if not resolved.is_absolute():
            resolved = destination.parent / resolved
        if resolved.resolve() == source.resolve():
            print(f"READY {host} {destination}")
            return 0
        print(f"CONFLICT {host} {destination} points to {existing}", file=sys.stderr)
        return 2
    if destination.exists():
        if _is_junction(destination) and destination.resolve() == source.resolve():
            print(f"READY {host} {destination}")
            return 0
        print(f"CONFLICT {host} {destination} already exists", file=sys.stderr)
        return 2
    if workspace is not None and not _confined_parent(destination, workspace):
        print(f"CONFLICT {host} parent escapes workspace: {destination.parent}", file=sys.stderr)
        return 2
    if not apply:
        print(f"PLANNED {host} {destination}")
        return 1
    try:
        _create_link(source, destination)
    except OSError as exc:
        print(f"CONFLICT {host} cannot create link: {exc}", file=sys.stderr)
        return 2
    print(f"CREATED {host} {destination}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Link portable skills into Codex and other host skill roots."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report readiness without writes")
    mode.add_argument("--dry-run", action="store_true", help="preview links (default)")
    mode.add_argument("--apply", action="store_true", help="create the planned links")
    parser.add_argument(
        "--host",
        action="append",
        choices=sorted(HOST_ROOTS) + ["all"],
        help="host to install; repeatable (default: codex, opencode, gemini)",
    )
    parser.add_argument("--workspace", type=Path, help="workspace for cursor/windsurf")
    args = parser.parse_args(argv)

    if not SKILLS_DIR.is_dir():
        print(f"ERROR: missing skills directory: {SKILLS_DIR}", file=sys.stderr)
        return 2

    hosts: list[str] = []
    for value in args.host or ["codex", "opencode", "gemini"]:
        hosts.extend(
            ["codex", "opencode", "gemini", "cursor", "windsurf"]
            if value == "all"
            else [value]
        )
    hosts = list(dict.fromkeys(hosts))

    workspace: Path | None = None
    if args.workspace is not None:
        workspace = args.workspace.expanduser().resolve()
        if not workspace.is_dir():
            print("ERROR: workspace is not an existing directory", file=sys.stderr)
            return 2

    status = 0
    for host in hosts:
        scope, relative = HOST_ROOTS[host]
        if scope == "workspace" and workspace is None:
            print(f"ERROR: --host {host} requires --workspace PATH", file=sys.stderr)
            status = 2
            continue
        root = Path.home() / relative if scope == "home" else workspace / relative
        for source in sorted(SKILLS_DIR.iterdir()):
            if not source.is_dir() or not (source / "SKILL.md").is_file():
                continue
            result = _inspect(
                host,
                source,
                root / source.name,
                apply=args.apply,
                workspace=workspace if scope == "workspace" else None,
            )
            if result == 2:
                status = 2
            elif result == 1 and not args.apply and status == 0:
                status = 1

    if not args.apply:
        print("Dry run only. Repeat with --apply to create the planned links.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())

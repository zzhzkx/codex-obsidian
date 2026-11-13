#!/usr/bin/env python3
"""Detect the Obsidian CLI and publish a normalized transport snapshot.

Cross-platform replacement for ``scripts/detect-transport.sh``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from claude_obsidian.paths import VaultSelectionError, resolve_vault_root
from claude_obsidian.transaction import (
    MutationLock,
    TransactionError,
    atomic_json,
    read_vault_regular,
)

STALE_AFTER_SECONDS = 7 * 86400


def _classify(kind: str, binary: str, output: str, exit_code: int) -> dict:
    lowered = output.casefold()
    app_patterns = (
        "app is not running",
        "app not running",
        "obsidian is not running",
        "no running obsidian",
        "unable to connect",
        "failed to connect",
        "connection refused",
        "could not connect",
        "ipc connection",
    )
    unsupported_patterns = (
        "unknown command",
        "unrecognized command",
        "unsupported command",
        "command not found: version",
        "requires obsidian 1.12",
        "command line interface is disabled",
        "cli is disabled",
        "enable command line interface",
    )
    if kind == "missing":
        return {
            "status": "missing",
            "usable": False,
            "app_running": None,
            "version": "",
            "diagnostic": (
                "Obsidian CLI is not on PATH. Enable Command line interface in "
                "Obsidian Settings > General."
            ),
        }
    if kind == "legacy":
        return {
            "status": "unsupported",
            "usable": False,
            "app_running": None,
            "version": "",
            "diagnostic": output,
        }
    if any(pattern in lowered for pattern in app_patterns):
        return {
            "status": "app_not_running",
            "usable": False,
            "app_running": False,
            "version": "",
            "diagnostic": output or "Obsidian is not running or the CLI could not connect.",
        }
    if any(pattern in lowered for pattern in unsupported_patterns):
        return {
            "status": "unsupported",
            "usable": False,
            "app_running": None,
            "version": "",
            "diagnostic": output or "Installed binary does not support 'obsidian version'.",
        }
    if exit_code != 0:
        return {
            "status": "capability_error",
            "usable": False,
            "app_running": None,
            "version": "",
            "diagnostic": output or f"'obsidian version' exited with status {exit_code}.",
        }
    if re.search(r"(?im)^\s*(?:error|err|fatal|exception|failed)(?:\s*[:\-]|\s+)", output):
        return {
            "status": "capability_error",
            "usable": False,
            "app_running": None,
            "version": "",
            "diagnostic": output,
        }
    if not output.strip() or not re.search(r"\b\d+\.\d+(?:\.\d+)?\b", output):
        return {
            "status": "capability_error",
            "usable": False,
            "app_running": None,
            "version": "",
            "diagnostic": "'obsidian version' returned no recognizable version output.",
        }
    version = next((line.strip() for line in output.splitlines() if line.strip()), "")
    return {
        "status": "ready",
        "usable": True,
        "app_running": True,
        "version": version,
        "diagnostic": "",
    }


def _probe(vault: Path) -> tuple[str, str, int, str]:
    candidate = shutil.which("obsidian")
    if candidate:
        kind = "official"
    else:
        candidate = shutil.which("obsidian-cli") or ""
        kind = "legacy" if candidate else "missing"
    if not candidate:
        return kind, "", -1, ""
    if kind == "legacy":
        return (
            kind,
            candidate,
            -1,
            "Legacy obsidian-cli found; enable and register the official obsidian CLI.",
        )
    try:
        completed = subprocess.run(
            [candidate, "version"],
            cwd=vault,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return kind, candidate, completed.returncode, output[:8192]
    except subprocess.TimeoutExpired:
        return kind, candidate, 124, "ERR: obsidian version probe timed out after 5 seconds"
    except OSError as exc:
        return kind, candidate, 126, f"ERR: cannot execute obsidian CLI: {type(exc).__name__}"


def _existing_snapshot(vault: Path) -> dict | None:
    try:
        raw = read_vault_regular(
            vault, ".vault-meta/transport.json", limit=8 * 1024 * 1024, missing_ok=True
        )
    except TransactionError:
        return None
    if raw is None:
        return None
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or data.get("vault_root") != str(vault)
        or not isinstance(data.get("preferred"), str)
        or not isinstance(data.get("fallback_chain"), list)
        or not isinstance(data.get("available"), dict)
    ):
        return None
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect the Obsidian CLI and write a transport snapshot."
    )
    parser.add_argument("--vault")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--peek", action="store_true")
    parser.add_argument("legacy_path", nargs="?")
    args = parser.parse_args(argv)

    try:
        selection = resolve_vault_root(
            args.vault or args.legacy_path,
            start=Path.cwd(),
            plugin_root=PLUGIN_ROOT,
            allow_uninitialized=True,
        )
    except VaultSelectionError as exc:
        print(f"ERR {exc.code}: {exc}", file=sys.stderr)
        return 2
    vault = selection.root
    output_file = vault / ".vault-meta" / "transport.json"
    if output_file.is_symlink():
        print(f"ERR: transport snapshot is not a safe regular file: {output_file}", file=sys.stderr)
        return 2

    if not args.peek and not args.force:
        existing = _existing_snapshot(vault)
        if existing is not None:
            try:
                fresh = time.time() - output_file.stat().st_mtime < STALE_AFTER_SECONDS
            except OSError:
                fresh = False
            if fresh:
                if not args.quiet:
                    print(
                        f"transport.json is fresh (<7d). Use --force to refresh.",
                        file=sys.stderr,
                    )
                print(json.dumps(existing, indent=2, sort_keys=True, ensure_ascii=False))
                return 0

    kind, binary, exit_code, output = _probe(vault)
    classified = _classify(kind, binary, output, exit_code)
    existing = _existing_snapshot(vault) or {}
    preferred = "cli" if classified["usable"] else "filesystem"
    chain = ["cli", "filesystem"] if classified["usable"] else ["filesystem"]
    manual_override = False
    if existing.get("manual_override") is True and isinstance(existing.get("preferred"), str):
        manual_override = True
        preferred = existing["preferred"]
        chain = existing.get("fallback_chain") or chain

    report = {
        "schema_version": 1,
        "detected_at": dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "host": socket.gethostname(),
        "vault_root": str(vault),
        "manual_override": manual_override,
        "preferred": preferred,
        "fallback_chain": chain,
        "available": {
            "cli": {
                "present": kind != "missing",
                "usable": classified["usable"],
                "status": classified["status"],
                "binary": binary,
                "probe": "obsidian version",
                "exit_code": None if exit_code < 0 else exit_code,
                "version_string": classified["version"],
                "diagnostic": classified["diagnostic"],
                "obsidian_app_running": classified["app_running"],
            },
            "filesystem": {
                "present": True,
                "vault_root": str(vault),
                "note": "universal fallback; uses the agent host's filesystem tools directly",
            },
            "mcp_obsidian": {
                "present": None,
                "detection": "deferred",
                "note": "MCP server detection is deferred; configure and pin it with manual_override if needed.",
            },
            "mcpvault": {
                "present": None,
                "detection": "deferred",
                "note": "MCP server detection is deferred; configure and pin it with manual_override if needed.",
            },
        },
    }
    if args.peek:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        return 0

    try:
        with MutationLock(vault):
            atomic_json(output_file, report)
    except TransactionError as exc:
        print(f"ERR: cannot publish a confined transport snapshot: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    if not args.quiet:
        print(f"Wrote: {output_file}", file=sys.stderr)
        print("Probe: obsidian version", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

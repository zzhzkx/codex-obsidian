#!/usr/bin/env python3
"""Cross-platform bootstrap for the optional retrieval cache."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))

from claude_obsidian.paths import VaultSelectionError, resolve_vault_root

HELPERS = ("contextual-prefix.py", "bm25-index.py", "rerank.py", "retrieve.py")


def _run(script: str, *arguments: str) -> int:
    return subprocess.call([sys.executable, str(PLUGIN_ROOT / "scripts" / script), *arguments])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or inspect retrieval state.")
    parser.add_argument("--vault")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    llm = parser.add_mutually_exclusive_group()
    llm.add_argument("--no-llm", action="store_true")
    llm.add_argument("--allow-egress", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument("--allow-remote-ollama", action="store_true")
    args = parser.parse_args(argv)

    missing = [name for name in HELPERS if not (PLUGIN_ROOT / "scripts" / name).is_file()]
    if missing:
        print(f"ERROR: missing product helper: scripts/{missing[0]}", file=sys.stderr)
        return 3
    try:
        selection = resolve_vault_root(args.vault, start=Path.cwd(), plugin_root=PLUGIN_ROOT)
    except VaultSelectionError as exc:
        print(f"ERR {exc.code}: {exc}", file=sys.stderr)
        return 2
    vault = str(selection.root)
    print(f"Vault: {vault}")
    print(f"Product helpers: {PLUGIN_ROOT / 'scripts'}")

    if args.check:
        if _run("bm25-index.py", "--vault", vault, "stats") != 0:
            print("READY: retrieval helpers are installed; vault index is not built yet.")
        return 0

    prefix = ["--vault", vault, "--all"]
    if args.no_llm:
        prefix.append("--no-llm")
    if args.allow_egress:
        prefix.append("--allow-egress")
    if args.rebuild:
        prefix.append("--rebuild")
    if not args.apply:
        _run("contextual-prefix.py", *prefix, "--peek")
        print("Dry run only. Repeat with --apply to write derived retrieval state.")
        return 0
    if _run("contextual-prefix.py", *prefix) != 0:
        return 1
    if _run("bm25-index.py", "--vault", vault, "build") != 0:
        return 1
    retrieve = ["--vault", vault, "wiki", "--top", "1", "--no-rerank"]
    if args.allow_remote_ollama:
        retrieve.append("--allow-remote-ollama")
    if _run("retrieve.py", *retrieve) != 0:
        return 1
    print("Retrieval state built successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

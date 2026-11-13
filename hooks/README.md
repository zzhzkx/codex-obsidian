# Codex lifecycle hooks

`hooks.json` is a thin Codex adapter around the portable core. Codex loads it
from the plugin root by default; `.codex-plugin/plugin.json` also declares the
path explicitly.

| Event | Matcher | Behavior |
|---|---|---|
| `SessionStart` | `startup\|resume\|clear\|compact\|fork` | Silent by default. With `CODEX_OBSIDIAN_SESSION_CONTEXT=1`, resolves a real user vault and emits a bounded, sanitized `wiki/hot.md` data block. A workspace-configured vault outside that project also requires an exact `CODEX_OBSIDIAN_SESSION_CONTEXT_VAULT` path. |
| `Stop` | unsupported/omitted | Emits a bounded aggregate JSON `systemMessage` when recovery is needed. It omits operation identifiers, paths, and note content; otherwise it is silent. |

Both handlers use the Codex command-hook shape: one `command` string, plus a
`commandWindows` override. Codex sets `PLUGIN_ROOT` and `PLUGIN_DATA` (and the
Claude-compatible `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA`) for plugin hooks.

`SessionStart` plain text is added as extra developer context. `Stop` must emit
JSON on stdout when it exits 0; the adapter writes
`{"systemMessage": "..."}` only when recovery state is present.

Hook scripts must be reviewed and trusted before Codex runs them: open
`/hooks` in the CLI or **Settings > Hooks** in the desktop app. A plugin update
that changes a bundled script requires a new review.

Hooks never write knowledge, update `wiki/hot.md`, stage files, commit Git, run
remote calls, or bypass transaction approval. The same workflows remain usable
on hosts that do not support hooks.

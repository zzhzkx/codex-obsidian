# Install codex-obsidian

codex-obsidian has two independent parts:

1. the product package—skills, portable core, Codex adapter, and templates;
2. a user-owned Obsidian vault containing mutable knowledge.

Do not use an installed plugin cache as the vault. A source clone is suitable
for development, but a normal user vault should be a separate directory.

## Requirements

- Python 3.11 or newer
- Codex for the plugin adapter, or any Agent Skills compatible host
- Obsidian when you want its visual editor
- Bash only for the legacy `.sh` wrappers; use the `.py` entry points otherwise
- Git only for source development, release builds, or explicit checkpoints
- On Windows: no WSL required; see the [Windows guide](windows-wsl.md)

Commands below use `python` for Windows readability. On macOS and Linux use
`python3`; the behavior is identical.

## Codex marketplace

Register the repository marketplace and install the plugin:

```bash
codex plugin marketplace add zzhzkx/codex-obsidian
# then open /plugins in Codex and install "Codex Obsidian"
codex plugin marketplace list
```

For a local checkout, point the marketplace at the repository root:

```bash
codex plugin marketplace add .
```

Codex reads `.codex-plugin/plugin.json`. The `.claude-plugin/` manifests are
retained only for upstream compatibility.

Invoke skills as `$wiki`, `$wiki-ingest`, and `$save`.

The plugin cache contains read-only product assets. Run Codex from the user
vault, set `CODEX_OBSIDIAN_VAULT`, or pass `--vault` to portable commands.

## Local Codex plugin development

From a product clone:

```bash
codex plugin marketplace add <product-repository>
```

Install the plugin from `/plugins`, then start a new session. This mode is for
testing uninstalled changes and does not convert the product repository into a
user vault.

## Portable Agent Skills hosts

The installer defaults to a no-write preview for Codex, OpenCode, and Gemini:

```bash
python scripts/setup-multi-agent.py
python scripts/setup-multi-agent.py --apply
```

It links each canonical `skills/<name>/` directory into the host's direct
`<skill-root>/<name>/SKILL.md` discovery layout. Destinations are created only
when absent; an existing skill or link is never replaced. Check readiness
without writing:

```bash
python scripts/setup-multi-agent.py --check
```

Cursor and Windsurf use workspace-local discovery and require an explicit
workspace:

```bash
python scripts/setup-multi-agent.py --host cursor --host windsurf \
  --workspace <workspace> --apply
```

ZCode is opt-in and user-level (no `--workspace` needed):

```bash
python scripts/setup-multi-agent.py --host zcode
python scripts/setup-multi-agent.py --host zcode --apply
```

You can also create equivalent per-skill links manually. For each `<name>` under
the product's `skills/` directory, link that directory at:

```text
Codex:     ~/.agents/skills/<name>          -> <product-repository>/skills/<name>
OpenCode:  ~/.config/opencode/skills/<name> -> <product-repository>/skills/<name>
Gemini:    ~/.gemini/skills/<name>          -> <product-repository>/skills/<name>
ZCode:     ~/.zcode/skills/<name>           -> <product-repository>/skills/<name>
Cursor:    <workspace>/.cursor/skills/<name>   -> <product-repository>/skills/<name>
Windsurf:  <workspace>/.windsurf/skills/<name> -> <product-repository>/skills/<name>
```

## Create a new vault

Review the initialization plan first:

```bash
python scripts/codex-obsidian.py init <new-vault> \
  --generated-at <ISO-UTC> --operation-id init-reviewed
```

Apply the same operation only after the destination and changed paths look
correct:

```bash
python scripts/codex-obsidian.py init <new-vault> \
  --generated-at <ISO-UTC> --operation-id init-reviewed \
  --approved-plan-sha256 <reviewed-sha256> --apply
```

The generated vault contains:

- `.gitignore`—privacy-safe defaults excluding `.vault-meta/` runtime state,
  Obsidian workspace state, and live `.mcp.json` launch configuration;
- `.claude-obsidian.json`—workspace identity and vault selection;
- `inbox/`—visible source intake;
- `.raw/`—immutable source payloads and legacy delta manifest;
- `wiki/`—index, log, hot cache, overview, and generated notes;
- `.obsidian/`—minimal non-destructive Obsidian defaults;
- `.vault-meta/`—ignored runtime state created when needed.

Initialization does not add an upstream Git remote or install community
plugins. Open the new directory through Obsidian's vault picker.

## Adopt an existing vault

Adoption scans an existing Obsidian directory and proposes only missing product
metadata and foundation files:

```bash
python scripts/codex-obsidian.py adopt <existing-vault> \
  --generated-at <ISO-UTC> --operation-id adopt-reviewed
python scripts/codex-obsidian.py adopt <existing-vault> \
  --generated-at <ISO-UTC> --operation-id adopt-reviewed \
  --approved-plan-sha256 <reviewed-sha256> --apply
```

It preserves existing notes and Obsidian JSON. `--force` is intentionally
separate and should be used only after inspecting replacement targets.

For older claude-obsidian layouts, add provenance ledgers and workspace config
with an additive migration:

```bash
python scripts/codex-obsidian.py migrate --vault <existing-vault> \
  --generated-at <ISO-UTC> --operation-id migrate-reviewed
python scripts/codex-obsidian.py migrate --vault <existing-vault> \
  --generated-at <ISO-UTC> --operation-id migrate-reviewed \
  --approved-plan-sha256 <reviewed-sha256> --apply
```

Migration is idempotent, does not infer claims from prose, and leaves the
legacy `.raw/.manifest.json` byte-for-byte unchanged.

## Vault selection

Mutable commands use this precedence:

1. `--vault <path>`
2. `CODEX_OBSIDIAN_VAULT`
3. nearest `.claude-obsidian.json`
4. nearest unambiguous initialized vault from the current directory

If selection fails, the command exits without mutation. The product/plugin root
is rejected as an implicit vault.

Verify a selected vault:

```bash
python scripts/codex-obsidian.py doctor --vault <vault>
python scripts/codex-obsidian.py contracts --verify --vault <vault>
```

## Optional configuration

The portable filesystem transport always remains available. Detect an active,
supported Obsidian CLI without persisting a snapshot:

```bash
python scripts/detect-transport.py --peek --vault <vault>
```

Optional extensions are explicit and vault-scoped:

```bash
python scripts/setup-mode.py --vault <vault>
python scripts/setup-retrieve.py --vault <vault>
python scripts/setup-dragonscale.py --vault <vault>
```

Read each script's preview before applying. Retrieval may use local BM25 alone;
model-based contextual prefixes or remote endpoints require explicit egress
consent. Optional tools such as Ollama and defuddle are capability-detected.

## First operation

Place a source in `inbox/`. Inspect the byte-capture plan:

```bash
python scripts/codex-obsidian.py capture plan --vault <vault>
```

Create immutable content-addressed copies only when the plan is correct:

```bash
python scripts/codex-obsidian.py capture apply --vault <vault> \
  --generated-at <ISO-UTC> --operation-id capture-reviewed
python scripts/codex-obsidian.py capture apply --vault <vault> \
  --generated-at <ISO-UTC> --operation-id capture-reviewed \
  --approved-plan-sha256 <reviewed-sha256> --apply
```

Then invoke the host's `wiki-ingest` skill. Image, PDF, and EPUB semantic
extraction is not built into the core; those formats currently receive bounded
metadata unless a separately configured adapter is explicitly approved.

## Upgrade and rollback

Upgrade product code independently from the user vault. Before a migration or
large ingest, make a normal backup or snapshot. Knowledge writes are journaled;
run recovery after an interrupted operation:

```bash
python scripts/codex-obsidian.py transaction recover --vault <vault>
```

Recovery conservatively preserves stale or foreign lock identities. Only after
confirming no writer is active may an operator add `--force-stale-lock`.

Git history is optional and never automatic. To checkpoint exactly one
completed transaction:

```bash
python scripts/codex-obsidian.py checkpoint <operation-id> --vault <vault> \
  --as-of YYYY-MM-DD
```

Checkpointing uses a temporary index, verifies exact Git blob bytes, refuses
pre-existing staged state, and resumes an interrupted ref/index finalization
from its vault-local pending record.

## Uninstall

Remove the host integration, not the vault:

```bash
codex plugin remove codex-obsidian
codex plugin marketplace remove codex-obsidian
```

For portable hosts, remove only the per-skill links that the installer reported.
User notes, sources, ledgers, and Obsidian settings remain untouched.

## Troubleshooting

| Symptom | Check |
|---|---|
| Skill is not discovered | Confirm `<host-skill-root>/<name>/SKILL.md` resolves to the matching product skill; rerun installer `--check`. |
| Command says no vault selected | Run from the vault, pass `--vault`, or set `CODEX_OBSIDIAN_VAULT`. |
| Plugin-root refusal | Select a separate user vault; plugin cache writes are unsupported. |
| Transaction conflict / exit 75 | Another operation is active or a target changed; reread, rebuild, and inspect a new bundle. |
| Obsidian CLI is unavailable | Use filesystem reads; start/update Obsidian before retrying CLI transport. |
| Capture adapter is not implemented | Inspect `capture adapters`; configure a separate runner only with explicit consent. |
| Writes refused with `UNSUPPORTED_PLATFORM` on Windows | Vault mutation requires WSL; see the [Windows and WSL guide](windows-wsl.md). |
| WSL installed but `wsl --status` hangs | Follow Microsoft's diagnostic and reporting flow in the [Windows and WSL guide](windows-wsl.md#wsl-troubleshooting); do not assume a cause without evidence. |
| Native dry-run approval fails in WSL with `PLAN_CHANGED` | Approval hashes bind the reviewing environment; redo the dry-run inside WSL ([details](windows-wsl.md#wsl-troubleshooting)). |

Run `make test` in the product repository when developing or packaging changes.

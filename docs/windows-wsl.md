# Windows guide

codex-obsidian runs natively on Windows. WSL is optional. This guide covers
the Windows-specific interpreter, lock, and filesystem details, and the
guarantees that change compared with Linux and macOS.

## Platform support

| Capability | Windows (native) | WSL / Linux / macOS |
|---|---|---|
| Inspection, dry-run previews, retrieval | Yes | Yes |
| Vault writes (`transaction apply`, `init`, `adopt`, `migrate`, `capture apply`, `mode set`) | Yes, path-based lock | Yes, descriptor-pinned lock |
| Capture plan/apply | Yes | Yes |
| Legacy capture queue locking | No | Yes |
| Git checkpoints (`checkpoint`) | No | Yes |
| Legacy `scripts/*.sh` wrappers | Use the `.py` equivalents | Yes |
| Codex lifecycle hooks | Yes | Yes |

Vaults must live on a filesystem with stable file identity. NTFS is fine.
FAT/exFAT volumes (typical USB sticks) and some network shares are refused with
`UNSAFE_VAULT_IDENTITY`; move the vault to NTFS.

## Python on Windows

The canonical entry point is:

```powershell
python scripts\codex-obsidian.py doctor --vault C:\path\to\vault
```

Skill bodies use `python3` for POSIX hosts. On Windows substitute `python`.
The plugin hooks already do this: `hooks/hooks.json` has a `commandWindows`
override that calls `python`, while POSIX keeps `python3`.

If `python` is missing, install Python 3.11+ from python.org and make sure the
installer added it to `PATH`. The Microsoft Store `python3.exe` alias can open
the Store instead of running Python; disable that alias or use the python.org
interpreter.

Codex runs command hooks through the shell. If hook commands do not resolve
`PLUGIN_ROOT`, replace the path with the absolute plugin root in
`hooks/hooks.json`, then review the hook again under **Settings > Hooks**.

## How native writes work

POSIX hosts pin the vault root, `.vault-meta`, and every runtime directory as
`O_DIRECTORY | O_NOFOLLOW` descriptors. Windows has no equivalent portable
primitive, so the Windows path uses:

- an atomic `mkdir` on `.vault-meta/mutation.lock` plus an `owner.json` record;
- bounded, non-recursive removal of that lock directory;
- path revalidation before every write (`symlink`/junction rejection and a
  re-stat of the vault and `.vault-meta` identities);
- the same journal, backups, atomic replace, rollback, and approval hash.

The tradeoff is a point-in-time check instead of descriptor pinning. A process
that replaces a directory with a junction between the check and the write can
still race the path lookup. Keep vaults on a local NTFS volume, do not run
untrusted software against the same directory during a write, and review the
operation before applying it.

Windows does not auto-reap stale locks. A dead writer leaves
`.vault-meta/mutation.lock` behind. Confirm no writer is active, then run:

```powershell
python scripts\codex-obsidian.py transaction recover --vault C:\path\to\vault --force-stale-lock
```

## WSL is still supported

If you want the full descriptor-pinned guarantees, run the same commands inside
WSL. Approval hashes bind to the environment that produced them, so review and
apply in the same environment. A plan produced natively cannot be replayed
inside WSL, and vice versa. Keeping the vault inside the WSL filesystem avoids
cross-boundary performance overhead.

## Troubleshooting

| Symptom | Check |
|---|---|
| `LOCK_TIMEOUT` | Another writer holds `.vault-meta/mutation.lock`. Wait, then recover with `--force-stale-lock` only after confirming the owner is gone. |
| `UNSAFE_VAULT_IDENTITY` | The volume does not expose stable file identity. Move the vault to NTFS. |
| `SYMLINK_WRITE_PATH` / `UNSAFE_VAULT_PATH` | A vault path component is a symlink or junction. Replace it with a real directory. |
| Hook prints nothing | Verify `python` is on `PATH`, the hook is trusted, and `PLUGIN_ROOT` resolves. Session context also requires `CODEX_OBSIDIAN_SESSION_CONTEXT=1`. |
| Hooks delay startup | Raise `timeout` in `hooks/hooks.json` or disable the plugin hooks; the rest of the product does not depend on them. |

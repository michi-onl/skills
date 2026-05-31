---
name: skill-sync
description: >
  Sync local Claude skills with the GitHub repo at https://github.com/michi-onl/skills/.
  Use this skill whenever the user asks to check, sync, update, or compare their skills
  with the repo. Also trigger when the user mentions "skills out of date", "pull skills",
  "update skills", "sync skills", "are my skills current", "skill versions",
  "Skill-Sync", "skills abgleichen", or "Skills aktualisieren". Use this skill even
  for casual questions like "are my skills up to date?" or "did I push my latest skills?".
---

# Skill Sync

Compares locally installed skills against the canonical source repo on GitHub and packages updated `.skill` files for anything that's out of sync.

## Platform Support

This skill auto-detects the environment and works on:

- **claude.ai** (sandbox) – reads from `/mnt/skills/user/` and writes to `/mnt/user-data/outputs/`
- **Claude Code** (desktop/CLI) – reads from `~/.claude/skills/` and writes to `~/.claude/skill-sync-outputs/`
- **OpenCode** – reads from `~/.config/opencode/skills/` or `~/.claude/skills/` and writes to the corresponding `skill-sync-outputs/` directory

## When to use

- User asks if their skills are up to date
- User wants to pull latest skill versions from GitHub
- User wants to see what changed between local and repo
- User mentions syncing, updating, or comparing skills

## Workflow

### 1. Find the script

The sync script lives at `scripts/sync.py` inside this skill's directory. Locate it relative to this SKILL.md file. On a standard install, that's `/mnt/skills/user/skill-sync/scripts/sync.py` (claude.ai) or `~/.claude/skills/skill-sync/scripts/sync.py` (Claude Code). If the skill is installed elsewhere, adjust accordingly.

### 2. Run the sync report

```bash
python <skill-dir>/scripts/sync.py
```

This clones the repo, compares file hashes, and prints a report showing which skills are synced, diverged, repo-only, or local-only.

### 3. Read the report and explain it to the user

Summarize plainly what's in sync, what diverged (and which files), what exists only in the repo, and what exists only locally.

### 4. Package updates if requested

If the user wants to update, re-run with `--package`:

```bash
python <skill-dir>/scripts/sync.py --package
```

This creates `.skill` files in the platform-specific output directory for every diverged or repo-only skill. Present these files to the user so they can install them.

### 5. JSON mode

For programmatic use, add `--json` to get structured output:

```bash
python <skill-dir>/scripts/sync.py --json
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--repo` | `https://github.com/michi-onl/skills.git` | GitHub repo URL |
| `--local-dir` | auto-detected | Local skills directory |
| `--output-dir` | auto-detected | Where to write `.skill` packages |
| `--other-dirs` | auto-detected | Other skill dirs to check before flagging repo-only |
| `--package` | off | Package out-of-sync skills |
| `--json` | off | Machine-readable output |

## Notes

- Defaults for `--local-dir` and `--output-dir` are detected automatically. Override them if your setup is non-standard.
- On Claude Code and OpenCode, the script also checks `~/.config/opencode/skills/` and cached superpowers packages so built-in skills aren't flagged as "repo only".
- The repo is cloned shallow (`--depth 1`) to a temp directory and cleaned up after.
- Comparison is SHA-256 hash-based, file by file. Any byte-level difference counts.
- **The repo is canonical.** `--package` always writes the repo version, so local edits you haven't pushed get overwritten when you install the package. The report flags *that* a skill diverged, not *which side* is newer — check the changed files before packaging.
- Skills that exist only locally (not in the repo) are flagged but not touched.
- `.skill` files are zip archives that can be installed in Claude's skill manager.

## Local-only paths

Files under certain prefixes are expected to exist only on the local install and not in the repo. They won't trigger a "diverged" status. The default prefix is `references/local/`. To add more, edit `LOCAL_ONLY_PREFIXES` in `sync.py`.

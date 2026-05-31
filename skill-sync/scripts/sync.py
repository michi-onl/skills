#!/usr/bin/env python3
"""
skill-sync: Compare local skills with GitHub repo and package updates.

Usage:
    python scripts/sync.py [--repo URL] [--local-dir DIR] [--output-dir DIR] [--package]

Works on:
    - claude.ai (sandbox)
    - Claude Code (desktop/CLI)
    - OpenCode
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def detect_environment():
    """Detect the running environment and return appropriate default paths."""
    home = Path.home()

    # Claude.ai sandbox
    if Path("/mnt/skills/user").exists():
        return {
            "local_dir": Path("/mnt/skills/user"),
            "output_dir": Path("/mnt/user-data/outputs"),
            "other_dirs": ["/mnt/skills/examples", "/mnt/skills/public"],
        }

    # Claude Code / OpenCode - check common skill locations
    candidates = [
        home / ".claude" / "skills",
    ]

    for local_dir in candidates:
        if local_dir.exists():
            other_dirs = []
            # Check for opencode built-in skills
            opencode_user = home / ".config" / "opencode" / "skills"
            if opencode_user.exists() and opencode_user != local_dir:
                other_dirs.append(str(opencode_user))
            # Check for opencode cached superpowers
            cache_dir = home / ".cache" / "opencode"
            if cache_dir.exists():
                for pkg in cache_dir.glob("packages/superpowers*/node_modules/superpowers/skills"):
                    other_dirs.append(str(pkg))

            return {
                "local_dir": local_dir,
                "output_dir": home / ".claude" / "skill-sync-outputs",
                "other_dirs": other_dirs,
            }

    # OpenCode standalone
    opencode_skills = home / ".config" / "opencode" / "skills"
    if opencode_skills.exists():
        return {
            "local_dir": opencode_skills,
            "output_dir": home / ".config" / "opencode" / "skill-sync-outputs",
            "other_dirs": [],
        }

    # Fallback: use current directory's parent if it looks like a skills dir,
    # otherwise current directory
    cwd = Path.cwd()
    if (cwd / "SKILL.md").exists() and cwd.name:
        # We're inside a skill directory, use parent
        return {
            "local_dir": cwd.parent,
            "output_dir": home / "skill-sync-outputs",
            "other_dirs": [],
        }

    return {
        "local_dir": cwd,
        "output_dir": home / "skill-sync-outputs",
        "other_dirs": [],
    }


# Dirs/files to skip when comparing
SKIP_NAMES = {"__pycache__", ".git", ".DS_Store", "node_modules", "evals", ".gitignore", "README.md"}
SKIP_EXTENSIONS = {".pyc"}

# Path prefixes that are expected to exist only locally.
# Files under these prefixes won't count as divergence when missing from the repo.
LOCAL_ONLY_PREFIXES = ("references/local/",)


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def collect_files(root: Path) -> dict[str, str]:
    """Return {relative_path: sha256} for all files under root."""
    result = {}
    if not root.exists():
        return result
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if any(part in SKIP_NAMES for part in rel.parts):
            continue
        if f.suffix in SKIP_EXTENSIONS:
            continue
        result[str(rel)] = hash_file(f)
    return result


def list_skills(directory: Path) -> list[str]:
    """Return skill folder names (dirs containing SKILL.md)."""
    if not directory.exists():
        return []
    skills = []
    for d in sorted(directory.iterdir()):
        if d.is_dir() and (d / "SKILL.md").exists():
            skills.append(d.name)
    return skills


def compare_skill(local_dir: Path, repo_dir: Path, name: str) -> dict:
    """Compare a single skill between local and repo. Returns diff info."""
    local_path = local_dir / name
    repo_path = repo_dir / name

    local_exists = local_path.exists() and (local_path / "SKILL.md").exists()
    repo_exists = repo_path.exists() and (repo_path / "SKILL.md").exists()

    if not repo_exists:
        return {"name": name, "status": "local_only"}
    if not local_exists:
        return {"name": name, "status": "repo_only"}

    local_files = collect_files(local_path)
    repo_files = collect_files(repo_path)

    added = sorted(set(repo_files) - set(local_files))
    removed = sorted(
        f for f in set(local_files) - set(repo_files)
        if not any(f.startswith(p) for p in LOCAL_ONLY_PREFIXES)
    )
    local_only_files = sorted(
        f for f in set(local_files) - set(repo_files)
        if any(f.startswith(p) for p in LOCAL_ONLY_PREFIXES)
    )
    changed = sorted(
        f for f in set(local_files) & set(repo_files)
        if local_files[f] != repo_files[f]
    )

    if not added and not removed and not changed:
        return {"name": name, "status": "synced", "local_only_files": local_only_files}

    return {
        "name": name,
        "status": "diverged",
        "added_in_repo": added,
        "removed_from_repo": removed,
        "changed": changed,
        "local_only_files": local_only_files,
    }


def package_skill(skill_path: Path, output_dir: Path) -> Path | None:
    """Package a skill folder into a .skill zip file."""
    skill_name = skill_path.name
    output_file = output_dir / f"{skill_name}.skill"

    try:
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(skill_path.rglob("*")):
                if not f.is_file():
                    continue
                rel = f.relative_to(skill_path.parent)
                if any(part in SKIP_NAMES for part in rel.parts):
                    continue
                if f.suffix in SKIP_EXTENSIONS:
                    continue
                zf.write(f, rel)
        return output_file
    except Exception as e:
        print(f"ERROR packaging {skill_name}: {e}", file=sys.stderr)
        return None


def main():
    env = detect_environment()

    parser = argparse.ArgumentParser(description="Sync skills with GitHub repo")
    parser.add_argument("--repo", default="https://github.com/michi-onl/skills.git")
    parser.add_argument("--local-dir", default=str(env["local_dir"]))
    parser.add_argument("--output-dir", default=str(env["output_dir"]))
    parser.add_argument("--other-dirs", nargs="*", default=env["other_dirs"],
                        help="Other skill dirs to check before flagging repo-only")
    parser.add_argument("--package", action="store_true", help="Package out-of-sync skills as .skill files")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    local_dir = Path(args.local_dir)
    output_dir = Path(args.output_dir)

    # Clone repo to temp dir
    tmpdir = tempfile.mkdtemp(prefix="skill-sync-")
    repo_dir = Path(tmpdir) / "repo"
    try:
        print(f"Cloning {args.repo} ...", file=sys.stderr)
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", args.repo, str(repo_dir)],
                capture_output=True, text=True
            )
        except FileNotFoundError:
            print("ERROR: git not found on PATH. Install git and retry.", file=sys.stderr)
            sys.exit(1)
        if result.returncode != 0:
            print(f"ERROR: git clone failed: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        # Gather all skill names from both sources
        local_skills = set(list_skills(local_dir))
        repo_skills = set(list_skills(repo_dir))
        all_skills = sorted(local_skills | repo_skills)

        # Compare each
        results = []
        other_dirs = [Path(d) for d in args.other_dirs]
        for name in all_skills:
            diff = compare_skill(local_dir, repo_dir, name)
            # Check if "repo_only" skills are already installed elsewhere
            if diff["status"] == "repo_only":
                for od in other_dirs:
                    if (od / name / "SKILL.md").exists():
                        diff["status"] = "installed_elsewhere"
                        diff["installed_at"] = str(od / name)
                        break
            results.append(diff)

        # Print report
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            synced = [r for r in results if r["status"] == "synced"]
            diverged = [r for r in results if r["status"] == "diverged"]
            repo_only = [r for r in results if r["status"] == "repo_only"]
            local_only = [r for r in results if r["status"] == "local_only"]
            elsewhere = [r for r in results if r["status"] == "installed_elsewhere"]

            print(f"\n{'='*50}")
            print(f"SKILL SYNC REPORT")
            print(f"{'='*50}")
            print(f"Local: {local_dir}")
            print(f"Repo:  {args.repo}  (canonical)")
            print("Note: --package writes repo versions; unpushed local edits would be overwritten.")
            print(f"{'='*50}\n")

            if synced:
                print(f"IN SYNC ({len(synced)}):")
                for r in synced:
                    print(f"  ✓ {r['name']}")
                    for f in r.get("local_only_files", []):
                        print(f"      local only: {f}")
                print()

            if diverged:
                print(f"DIVERGED ({len(diverged)}):")
                for r in diverged:
                    print(f"  ✗ {r['name']}")
                    for f in r.get("changed", []):
                        print(f"      modified: {f}")
                    for f in r.get("added_in_repo", []):
                        print(f"      new in repo: {f}")
                    for f in r.get("removed_from_repo", []):
                        print(f"      local-only, not in repo: {f}")
                    for f in r.get("local_only_files", []):
                        print(f"      local only (ok): {f}")
                print()

            if repo_only:
                print(f"IN REPO ONLY ({len(repo_only)}):")
                for r in repo_only:
                    print(f"  + {r['name']}")
                print()

            if local_only:
                print(f"LOCAL ONLY ({len(local_only)}):")
                for r in local_only:
                    print(f"  ~ {r['name']}")
                print()

            if elsewhere:
                print(f"INSTALLED ELSEWHERE ({len(elsewhere)}):")
                for r in elsewhere:
                    print(f"  ○ {r['name']}  ← {r['installed_at']}")
                print()

        # Package if requested
        if args.package:
            to_package = [
                r["name"] for r in results
                if r["status"] in ("diverged", "repo_only")
            ]
            if not to_package:
                print("Everything in sync. Nothing to package.", file=sys.stderr)
            else:
                output_dir.mkdir(parents=True, exist_ok=True)
                print(f"\nPackaging {len(to_package)} skill(s)...", file=sys.stderr)
                for name in to_package:
                    skill_path = repo_dir / name
                    out = package_skill(skill_path, output_dir)
                    if out:
                        print(f"  → {out}", file=sys.stderr)
    finally:
        # Cleanup
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Batch upload images to Wikimedia Commons using Pywikibot.

Reads image files and their descriptions from wikimedia_descriptions.txt,
then uploads each file to Commons.

Prerequisites (handled automatically by the commons-upload skill):
    - .venv with pywikibot installed
    - user-config.py and user-password.py in working directory

Usage:
    python upload_to_commons.py                          # upload all
    python upload_to_commons.py --dry-run                # preview without uploading
    python upload_to_commons.py --file "Notre-Dame*"     # upload matching files only
    python upload_to_commons.py --overwrite              # re-upload files that exist
    python upload_to_commons.py --delay 10               # 10s between uploads
"""

import argparse
import datetime
import fnmatch
import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path

DESCRIPTION_FILE = "wikimedia_descriptions.txt"
UPLOAD_COMMENT = "Batch upload of own work (CC BY-SA 4.0)"
CHUNK_SIZE = 1024 * 1024 * 5  # 5 MB chunks
DELAY_BETWEEN_UPLOADS = 5
LOG_FILE = "upload_log.txt"

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

STATUS_UPLOADED = "uploaded"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_DRY_RUN = "dry-run"


def parse_descriptions(desc_path: Path) -> dict[str, str]:
    """Parse wikimedia_descriptions.txt into {filename: wikitext} dict."""
    text = desc_path.read_text(encoding="utf-8")
    entries = {}
    blocks = re.split(r"^={3,}$", text, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip()]

    i = 0
    while i < len(blocks):
        block = blocks[i]
        if re.match(r"^.+\.\w{2,4}$", block, re.IGNORECASE) and not block.startswith("{{"):
            filename = block.strip()
            if i + 1 < len(blocks):
                wikitext = blocks[i + 1].strip()
                entries[filename] = wikitext
                i += 2
                continue
        i += 1

    return entries


def log_entry(log_path: Path, filename: str, status: str, url: str = ""):
    """Append a line to the upload log."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}\t{filename}\t{status}"
    if url:
        line += f"\t{url}"
    line += "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def commons_file_url(filename: str) -> str:
    """Return the Commons file page URL for a given filename."""
    encoded = urllib.parse.quote(filename.replace(" ", "_"))
    return f"https://commons.wikimedia.org/wiki/File:{encoded}"


def verify_uploads_via_api(filenames: list[str]) -> dict[str, dict]:
    """Batch-check files on Commons. Returns {filename: page_info} for found files."""
    results = {}
    # MediaWiki API supports up to 50 titles per query
    for batch_start in range(0, len(filenames), 50):
        batch = filenames[batch_start:batch_start + 50]
        titles = "|".join(f"File:{f}" for f in batch)
        params = {
            "action": "query",
            "titles": titles,
            "prop": "imageinfo|categories",
            "iiprop": "size|url",
            "format": "json",
        }
        url = COMMONS_API + "?" + urllib.parse.urlencode(params)
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    continue
                title = page_data.get("title", "")
                if title.startswith("File:"):
                    fname = title[5:]
                    results[fname] = page_data
        except Exception:
            pass
    return results


def upload_file(site, file_path: Path, description: str, dry_run: bool = False,
                overwrite: bool = False):
    """Upload a single file to Commons. Returns (status, url)."""
    size_mb = file_path.stat().st_size / 1024 / 1024

    if dry_run:
        print(f"  DRY RUN — would upload: {file_path.name} ({size_mb:.1f} MB)")
        print(f"  Description preview (first 200 chars):")
        print(f"    {description[:200]}...")
        return STATUS_DRY_RUN, ""

    import pywikibot
    from pywikibot.specialbots import UploadRobot

    page_title = f"File:{file_path.name}"
    file_page = pywikibot.FilePage(site, page_title)
    already_exists = file_page.exists()

    if already_exists and not overwrite:
        print(f"  SKIP (already exists): {file_path.name}")
        return STATUS_SKIPPED, ""

    action = "Re-uploading" if already_exists else "Uploading"
    print(f"  {action}: {file_path.name} ({size_mb:.1f} MB)")

    bot = UploadRobot(
        url=[str(file_path)],
        description=description,
        use_filename=file_path.name,
        keep_filename=True,
        verify_description=False,
        target_site=site,
        summary=UPLOAD_COMMENT,
        chunk_size=CHUNK_SIZE,
        ignore_warning=True,
        always=True,
    )
    bot.run()

    # Fresh object forces API re-check to confirm upload landed
    if pywikibot.FilePage(site, page_title).exists():
        url = commons_file_url(file_path.name)
        print(f"  OK: {file_path.name}")
        return STATUS_UPLOADED, url
    else:
        print(f"  FAILED: {file_path.name}")
        return STATUS_FAILED, ""


def run_post_upload_verification(filenames: list[str]):
    """Verify uploaded files via the Commons API (batched)."""
    print("\n--- Post-upload verification ---")
    issues = []

    found = verify_uploads_via_api(filenames)

    for filename in filenames:
        info = found.get(filename)
        if not info:
            issues.append((filename, "NOT FOUND on Commons"))
            print(f"  MISSING: {filename}")
            continue

        if not info.get("imageinfo"):
            issues.append((filename, "No image info returned"))
            print(f"  NO INFO: {filename}")
            continue

        cats = info.get("categories", [])
        if not cats:
            issues.append((filename, "No categories rendered"))
            print(f"  NO CATS: {filename}")
        else:
            print(f"  OK: {filename} ({len(cats)} categories)")

    if issues:
        print(f"\n{len(issues)} file(s) with issues:")
        for fname, issue in issues:
            print(f"  - {fname}: {issue}")
    else:
        print(f"\nAll {len(filenames)} files verified OK.")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Upload images to Wikimedia Commons")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview uploads without actually uploading")
    parser.add_argument("--file", type=str, nargs="+",
                        help="Glob pattern(s) to filter filenames")
    parser.add_argument("--delay", type=int, default=DELAY_BETWEEN_UPLOADS,
                        help=f"Seconds between uploads (default: {DELAY_BETWEEN_UPLOADS})")
    parser.add_argument("--overwrite", action="store_true",
                        help="Re-upload files that already exist on Commons")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip post-upload verification")
    args = parser.parse_args()

    base_dir = Path.cwd()
    desc_path = base_dir / DESCRIPTION_FILE
    log_path = base_dir / LOG_FILE

    if not desc_path.exists():
        print(f"Error: {DESCRIPTION_FILE} not found in {base_dir}")
        sys.exit(1)

    entries = parse_descriptions(desc_path)
    print(f"Found {len(entries)} entries in {DESCRIPTION_FILE}")

    if args.file:
        entries = {k: v for k, v in entries.items()
                   if any(fnmatch.fnmatch(k, p) for p in args.file)}
        print(f"Filtered to {len(entries)} entries matching {args.file}")

    if not entries:
        print("Nothing to upload.")
        sys.exit(0)

    missing = [f for f in entries if not (base_dir / f).exists()]
    if missing:
        print(f"Warning: {len(missing)} files not found locally:")
        for f in missing:
            print(f"  - {f}")
        entries = {k: v for k, v in entries.items() if k not in missing}

    if not entries:
        print("No uploadable files remain.")
        sys.exit(0)

    if not args.dry_run:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Upload session started: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            if args.overwrite:
                f.write("Mode: overwrite enabled\n")
            f.write(f"{'='*60}\n")

    if not args.dry_run:
        import pywikibot
        site = pywikibot.Site("commons", "commons")
        site.login()
        print(f"Logged in as: {site.user()}")
    else:
        site = None

    uploaded = 0
    failed = 0
    skipped = 0
    uploaded_filenames = []

    for i, (filename, description) in enumerate(entries.items(), 1):
        file_path = base_dir / filename
        print(f"\n[{i}/{len(entries)}] {filename}")

        try:
            status, url = upload_file(site, file_path, description,
                                      dry_run=args.dry_run, overwrite=args.overwrite)
            if status == STATUS_UPLOADED:
                uploaded += 1
                uploaded_filenames.append(filename)
                log_entry(log_path, filename, "OK", url)
            elif status == STATUS_SKIPPED:
                skipped += 1
                log_entry(log_path, filename, "SKIPPED")
            elif status == STATUS_FAILED:
                failed += 1
                log_entry(log_path, filename, "FAILED")
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
            if not args.dry_run:
                log_entry(log_path, filename, f"ERROR: {e}")

        if i < len(entries) and not args.dry_run:
            time.sleep(args.delay)

    processed = uploaded + skipped + failed
    prefix = "DRY RUN " if args.dry_run else ""
    print(f"\n{prefix}Done. Processed: {processed}, Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}")

    if not args.dry_run and not args.no_verify and uploaded_filenames:
        # Let Commons process before verification
        print("\nWaiting 10s before verification...")
        time.sleep(10)
        run_post_upload_verification(uploaded_filenames)


if __name__ == "__main__":
    main()

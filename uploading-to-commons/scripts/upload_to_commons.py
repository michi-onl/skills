#!/usr/bin/env python3
"""
Batch upload images to Wikimedia Commons using Pywikibot.

Reads image files and their descriptions from wikimedia_descriptions.txt,
then uploads each file to Commons.

Prerequisites (handled automatically by the uploading-to-commons skill):
    - .venv with pywikibot installed
    - user-config.py and user-password.py in working directory

Usage:
    python upload_to_commons.py                          # upload all
    python upload_to_commons.py --dry-run                # preview without uploading
    python upload_to_commons.py --file "Notre-Dame*"     # upload matching files only
    python upload_to_commons.py --overwrite              # re-upload files that exist
    python upload_to_commons.py --delay 10               # 10s between uploads
    python upload_to_commons.py --sdc-only               # only add SDC statements to
                                                         # files already on Commons
"""

import argparse
import datetime
import fnmatch
import json
import re
import sys
import time
import unicodedata
import urllib.request
import urllib.parse
from pathlib import Path

DESCRIPTION_FILE = "wikimedia_descriptions.txt"
UPLOAD_COMMENT = "Batch upload of own work (CC BY-SA 4.0)"
CHUNK_SIZE = 1024 * 1024 * 5  # 5 MB chunks
DELAY_BETWEEN_UPLOADS = 5
LOG_FILE = "upload_log.txt"

# Structured data (SDC). A Commons file states its licence twice: once as a wikitext
# template, once as statements on the file's MediaInfo entity. Skip the second and every
# upload lands in "... missing SDC copyright license" maintenance categories.
# action=upload cannot carry structured data, so this is always a follow-up edit.
SDC_SUMMARY = "add SDC copyright status and license to match the file page"
SDC_BY_LICENSE = {
    # {{self|<key>}} -> [(property, item), ...]
    # P6216 copyright status, P275 copyright license
    "cc-by-sa-4.0": [
        ("P6216", "Q50423863"),   # copyrighted
        ("P275", "Q18199165"),    # CC BY-SA 4.0 International
    ],
    "cc-by-4.0": [
        ("P6216", "Q50423863"),   # copyrighted
        ("P275", "Q20007257"),    # CC BY 4.0 International
    ],
    "cc-zero": [
        ("P6216", "Q88088423"),   # copyrighted, dedicated to the public domain
        ("P275", "Q6938433"),     # CC0
    ],
}

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Wikimedia rejects the default urllib User-Agent with HTTP 403. Every API call
# from this script must carry a descriptive one.
USER_AGENT = "uploading-to-commons-pipeline/1.0 (https://commons.wikimedia.org/wiki/User:Mike_is_Michi)"

STATUS_UPLOADED = "uploaded"
STATUS_SKIPPED = "skipped"
STATUS_FAILED = "failed"
STATUS_DRY_RUN = "dry-run"


def parse_descriptions(desc_path: Path) -> dict[str, str]:
    """Parse wikimedia_descriptions.txt into {filename: wikitext} dict."""
    text = desc_path.read_text(encoding="utf-8")
    entries = {}
    # Require a long run of '=' so a bare wikitext heading rule like '====' inside
    # a description does not split the block and silently drop its categories.
    blocks = re.split(r"^={8,}$", text, flags=re.MULTILINE)
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


def check_block(filename: str, wikitext: str) -> list[str]:
    """Return human-readable warnings about a parsed description block."""
    warnings = []
    if "{{Information" not in wikitext:
        warnings.append("no {{Information}} block")
    if "[[Category:" not in wikitext:
        warnings.append("no categories")
    if "{{self|" not in wikitext and "{{Self|" not in wikitext:
        warnings.append("no license template")
    return warnings


def detect_license(wikitext: str) -> str | None:
    """Return the {{self|<key>}} licence key from a description block, or None."""
    # Both {{self|...}} and {{Self|...}} occur in practice, as check_block assumes.
    m = re.search(r"\{\{\s*self\s*\|\s*([A-Za-z0-9.\-]+)", wikitext, re.IGNORECASE)
    return m.group(1).lower() if m else None


def add_sdc_statements(site, filename: str, wikitext: str) -> tuple[int, str]:
    """Add the SDC copyright statements matching the file's licence template.

    Returns (statements_added, human-readable message). Existing statements are
    left alone, so this is safe to re-run over an already-processed batch.
    """
    import pywikibot
    from pywikibot.exceptions import NoWikibaseEntityError

    key = detect_license(wikitext)
    if key is None:
        return 0, "no {{self|...}} licence found — skipped"
    statements = SDC_BY_LICENSE.get(key)
    if statements is None:
        return 0, f"licence '{key}' not in SDC_BY_LICENSE — skipped"

    file_page = pywikibot.FilePage(site, f"File:{filename}")
    if not file_page.exists():
        return 0, "file not on Commons — skipped"

    media = file_page.data_item()
    try:
        existing = media.get().get("statements", {})
    except NoWikibaseEntityError:
        existing = {}  # no MediaInfo entity yet; the first claim creates it

    repo = site.data_repository()
    added = 0
    for prop, qid in statements:
        if prop in existing:
            continue
        claim = pywikibot.Claim(repo, prop)
        claim.setTarget(pywikibot.ItemPage(repo, qid))
        media.addClaim(claim, summary=SDC_SUMMARY)
        added += 1

    if added:
        # The maintenance categories come from the licence template's parse, not from
        # the statements themselves, so the page must be re-parsed before they clear.
        file_page.purge(forcelinkupdate=True)
        return added, f"{key}: {added} statement(s) added"
    return 0, f"{key}: already present"


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


def normalize_title(filename: str) -> str:
    """Match MediaWiki title normalisation: underscores become spaces and the
    first letter is capitalised. Without this, a lowercase-initial filename is
    reported as MISSING even though it uploaded fine."""
    name = unicodedata.normalize("NFC", filename.replace("_", " ")).strip()
    return name[:1].upper() + name[1:]


def api_query(params: dict) -> dict:
    """GET the Commons API with a compliant User-Agent. Raises on failure."""
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def verify_uploads_via_api(filenames: list[str]) -> dict[str, dict]:
    """Batch-check files on Commons. Returns {filename: page_info} for found files."""
    results = {}
    # MediaWiki API supports up to 50 titles per query
    for batch_start in range(0, len(filenames), 50):
        batch = filenames[batch_start:batch_start + 50]
        params = {
            "action": "query",
            "titles": "|".join(f"File:{f}" for f in batch),
            "prop": "imageinfo|categories",
            "iiprop": "size|url",
            "cllimit": "max",  # without this the API caps categories at 10
            "format": "json",
        }
        try:
            data = api_query(params)
        except Exception as e:
            # Never swallow this: a failed query is indistinguishable from a
            # batch of missing files, and reads as a fleet-wide upload failure.
            print(f"  API ERROR while verifying batch {batch_start // 50 + 1}: {e}")
            continue
        pages = data.get("query", {}).get("pages", {})
        for page_data in pages.values():
            # Missing pages get ids -1, -2, -3...; only the "missing" key is reliable
            if "missing" in page_data:
                continue
            title = page_data.get("title", "")
            if title.startswith("File:"):
                results[normalize_title(title[5:])] = page_data
    return results


def upload_file(site, file_path: Path, description: str, dry_run: bool = False,
                overwrite: bool = False):
    """Upload a single file to Commons. Returns (status, url)."""
    size_mb = file_path.stat().st_size / 1024 / 1024

    if dry_run:
        print(f"  DRY RUN — would upload: {file_path.name} ({size_mb:.1f} MB)")
        # Print the block in full. Truncating hid the license and categories,
        # which are exactly what the confirmation gate exists to review.
        print("  Wikitext:")
        for line in description.splitlines():
            print(f"    {line}")
        for w in check_block(file_path.name, description):
            print(f"  WARNING: {w}")
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
        info = found.get(normalize_title(filename))
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
            continue

        # A file still in a "missing SDC copyright license" category either never got
        # its statements or was not re-parsed after they were added.
        if any("missing SDC" in c.get("title", "") for c in cats):
            issues.append((filename, "still in a 'missing SDC copyright license' category"))
            print(f"  NO SDC: {filename} ({len(cats)} categories)")
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
    parser.add_argument("--no-sdc", action="store_true",
                        help="Skip adding SDC copyright statements after each upload")
    parser.add_argument("--sdc-only", action="store_true",
                        help="Upload nothing; only add missing SDC statements to files "
                             "already on Commons (retro-fit an earlier batch)")
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

    if args.sdc_only:
        # Retro-fit mode: the files are already on Commons, so the local copies are
        # irrelevant and nothing is uploaded.
        import pywikibot
        site = pywikibot.Site("commons", "commons")
        site.login()
        print(f"Logged in as: {site.user()}")
        print(f"Applying SDC statements to {len(entries)} file(s); nothing will be uploaded.")

        changed = 0
        for i, (filename, description) in enumerate(entries.items(), 1):
            print(f"\n[{i}/{len(entries)}] {filename}")
            try:
                count, msg = add_sdc_statements(site, filename, description)
                print(f"  SDC — {msg}")
                if count:
                    changed += 1
                    log_entry(log_path, filename, f"SDC: {msg}")
            except Exception as e:
                print(f"  SDC ERROR: {e}")
                log_entry(log_path, filename, f"SDC ERROR: {e}")
            if i < len(entries):
                time.sleep(args.delay)

        print(f"\nDone. {changed} file(s) updated, "
              f"{len(entries) - changed} already complete or skipped.")
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
    previewed = 0
    uploaded_filenames = []

    for i, (filename, description) in enumerate(entries.items(), 1):
        file_path = base_dir / filename
        print(f"\n[{i}/{len(entries)}] {filename}")

        try:
            status, url = upload_file(site, file_path, description,
                                      dry_run=args.dry_run, overwrite=args.overwrite)
            if status == STATUS_DRY_RUN:
                previewed += 1
            elif status == STATUS_UPLOADED:
                uploaded += 1
                uploaded_filenames.append(filename)
                log_entry(log_path, filename, "OK", url)
                if not args.no_sdc:
                    # Separate edit by necessity: action=upload takes no structured data.
                    # A failure here leaves a perfectly good upload, so never let it
                    # count against the upload itself.
                    try:
                        count, msg = add_sdc_statements(site, filename, description)
                        print(f"  SDC — {msg}")
                    except Exception as e:
                        print(f"  SDC ERROR: {e}")
                        log_entry(log_path, filename, f"SDC ERROR: {e}")
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

    if args.dry_run:
        print(f"\nDRY RUN complete. {previewed} file(s) would be uploaded, "
              f"{failed} errored during preview.")
        print("Nothing has been uploaded. Re-run without --dry-run to upload.")
    else:
        processed = uploaded + skipped + failed
        print(f"\nDone. Processed: {processed}, Uploaded: {uploaded}, "
              f"Skipped: {skipped}, Failed: {failed}")

    if not args.dry_run and not args.no_verify and uploaded_filenames:
        # Let Commons process before verification
        print("\nWaiting 10s before verification...")
        time.sleep(10)
        run_post_upload_verification(uploaded_filenames)


if __name__ == "__main__":
    main()

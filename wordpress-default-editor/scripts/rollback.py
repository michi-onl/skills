#!/usr/bin/env python3
"""
Rollback a page/post from /tmp/wp_backup/.
Restores both content AND status.
Usage: python3 rollback.py <page_id> [--endpoint pages|posts|...]
"""
import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request


def rollback(page_id, endpoint="pages"):
    user = os.environ["WP_USER"]
    pw = os.environ["WP_APP_PASS"]
    site = os.environ["WP_SITE"].rstrip("/")

    backup_dir = "/tmp/wp_backup"
    content_path = os.path.join(backup_dir, f"{page_id}_original.txt")
    status_path = os.path.join(backup_dir, f"{page_id}_status.txt")

    if not os.path.exists(content_path):
        print(f"No backup found for {endpoint}/{page_id}", file=sys.stderr)
        sys.exit(1)

    with open(content_path, encoding="utf-8") as f:
        content = f.read().rstrip("\n")

    status = "publish"
    if os.path.exists(status_path):
        with open(status_path, encoding="utf-8") as f:
            status = f.read().strip()

    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    payload = json.dumps({"content": content, "status": status}).encode()
    req = urllib.request.Request(
        f"{site}/wp-json/wp/v2/{endpoint}/{page_id}",
        data=payload,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=30)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} rolling back {endpoint}/{page_id}: {body}", file=sys.stderr)
        sys.exit(1)

    print(f"Rolled back {endpoint}/{page_id} to status '{status}'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rollback from /tmp/wp_backup/")
    parser.add_argument("page_id", type=int)
    parser.add_argument("--endpoint", default="pages", help="WP REST endpoint (default: pages)")
    args = parser.parse_args()
    rollback(args.page_id, args.endpoint)

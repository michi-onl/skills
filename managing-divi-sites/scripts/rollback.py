#!/usr/bin/env python3
"""
Rollback a page from /tmp/wp_backup/.
Restores both content AND status.
Usage: python3 rollback.py <page_id>
"""
import os, json, base64, urllib.request, sys

def rollback(page_id):
    user = os.environ["WP_USER"]
    pw = os.environ["WP_APP_PASS"]
    site = os.environ["WP_SITE"]

    backup_dir = "/tmp/wp_backup"
    content_path = os.path.join(backup_dir, f"{page_id}_original.txt")
    status_path = os.path.join(backup_dir, f"{page_id}_status.txt")

    with open(content_path) as f:
        content = f.read()

    status = "publish"
    if os.path.exists(status_path):
        with open(status_path) as f:
            status = f.read().strip()

    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    payload = json.dumps({"content": content, "status": status}).encode()

    req = urllib.request.Request(
        f"{site}/wp-json/wp/v2/pages/{page_id}",
        data=payload,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req)
    print(f"Rolled back page {page_id} to status '{status}'.")


if __name__ == "__main__":
    rollback(int(sys.argv[1]))

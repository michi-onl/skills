#!/usr/bin/env python3
"""
WordPress default block editor REST API helpers.
Reads credentials from environment: WP_USER, WP_APP_PASS, WP_SITE.
"""
import base64
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def _site():
    return os.environ["WP_SITE"].rstrip("/")


def _headers(for_write=False):
    auth = base64.b64encode(
        f"{os.environ['WP_USER']}:{os.environ['WP_APP_PASS']}".encode()
    ).decode()
    headers = {"Authorization": f"Basic {auth}"}
    if for_write:
        headers["Content-Type"] = "application/json"
    return headers


def _request(method, path, data=None, retries=3):
    url = f"{_site()}/wp-json/wp/v2/{path}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers=_headers(for_write=data is not None),
                method=method,
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


def fetch_raw(endpoint, pid):
    """Fetch raw block markup and status for a page/post."""
    return _request(
        "GET",
        f"{endpoint}/{pid}?context=edit&_fields=id,title,content,status",
    )


def save_content(endpoint, pid, new_content, status):
    """Write content back while preserving the original status."""
    payload = json.dumps({"content": new_content, "status": status}).encode()
    return _request("POST", f"{endpoint}/{pid}", data=payload)


def backup_dir():
    """Per-site backup directory so equal page ids on different sites don't collide.

    Keys on the full site URL (scheme, host, and path), so subdirectory multisite
    installs on one host and http/https variants each get a distinct directory.
    """
    slug = re.sub(r"[^A-Za-z0-9._-]", "_", _site()) or "default"
    return os.path.join("/tmp/wp_backup", slug)


def backup(endpoint, pid):
    """Fetch and back up content + status under backup_dir(), byte-for-byte."""
    data = fetch_raw(endpoint, pid)
    out_dir = backup_dir()
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{pid}_original.txt"), "w", encoding="utf-8") as f:
        f.write(data["content"]["raw"])
    with open(os.path.join(out_dir, f"{pid}_status.txt"), "w", encoding="utf-8") as f:
        f.write(data["status"])
    return data


def list_content(endpoint, search=None):
    """Paginate through all items on an endpoint."""
    results = []
    page = 1
    while True:
        query = f"{endpoint}?per_page=100&page={page}&context=edit&_fields=id,title,status,content"
        if search:
            query += f"&search={urllib.parse.quote(search)}"
        chunk = _request("GET", query)
        if not chunk:
            break
        results.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return results


def _block_re(block_type):
    return re.compile(
        r"<!-- wp:" + re.escape(block_type) + r'(\s[^>]*)? -->(.*?)<!-- /wp:' + re.escape(block_type) + r" -->",
        re.DOTALL,
    )


def _is_leaf_block(inner):
    """Return True when inner HTML contains no nested block comments."""
    return "<!-- wp:" not in inner


def find_blocks(content, block_type):
    """Return all serialized block strings of the given type."""
    return [m.group(0) for m in _block_re(block_type).finditer(content)]


def update_block_text(content, block_type, old_text, new_text):
    """Replace old_text with new_text inside the single matching leaf block.

    Refuses to act when old_text matches more than one block of the type, so an
    ambiguous target can never silently edit the wrong block.
    """
    if old_text == "":
        raise ValueError("old_text must not be empty")
    matches = [
        m for m in _block_re(block_type).finditer(content) if old_text in m.group(2)
    ]
    if not matches:
        raise ValueError(f"old_text not found in any {block_type} block")
    if len(matches) > 1:
        raise ValueError(
            f"old_text matches {len(matches)} {block_type} blocks; "
            "use a more specific old_text to disambiguate"
        )
    match = matches[0]
    inner = match.group(2)
    if not _is_leaf_block(inner):
        raise ValueError(f"refusing to edit non-leaf {block_type} block")
    new_inner = inner.replace(old_text, new_text, 1)
    return content[: match.start(2)] + new_inner + content[match.end(2) :]


def verify_only_text_changed(old, new, block_type, old_text, new_text=None):
    """Confirm that only the targeted block instance changed.

    Optionally checks that new_text appears in the updated block, and rejects
    changes that only mutate the block's opening-comment attributes.
    """
    if not old_text:
        raise ValueError("old_text must not be empty")
    old_blocks = find_blocks(old, block_type)
    new_blocks = find_blocks(new, block_type)
    if len(old_blocks) != len(new_blocks):
        return False

    target_index = None
    for i, block in enumerate(old_blocks):
        inner = _block_re(block_type).search(block).group(2)
        if old_text in inner:
            target_index = i
            break
    if target_index is None:
        return False

    old_attrs = _block_re(block_type).search(old_blocks[target_index]).group(1)
    new_attrs = _block_re(block_type).search(new_blocks[target_index]).group(1)
    if old_attrs != new_attrs:
        return False

    if old_blocks[target_index] == new_blocks[target_index]:
        return False

    if new_text is not None and new_text not in new_blocks[target_index]:
        return False

    sentinel = uuid.uuid4().hex

    def _replace_at_index(content, index):
        seen = [0]

        def replacer(match):
            if seen[0] == index:
                seen[0] += 1
                return sentinel
            seen[0] += 1
            return match.group(0)

        return _block_re(block_type).sub(replacer, content)

    return _replace_at_index(old, target_index) == _replace_at_index(new, target_index)

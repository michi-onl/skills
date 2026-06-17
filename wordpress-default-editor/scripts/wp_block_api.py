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
    headers = {"Authorization": f"Basic {auth}", "User-Agent": "wp-default-editor/1.0"}
    if for_write:
        headers["Content-Type"] = "application/json"
    return headers


def _rest_base():
    """REST namespace prefix. Default assumes pretty permalinks; set WP_REST_ROOT
    to "index.php/wp-json" (or similar) for plain-permalink or route-restricted sites."""
    return os.environ.get("WP_REST_ROOT", "wp-json").strip("/")


def _request(method, path, data=None, retries=3):
    url = f"{_site()}/{_rest_base()}/wp/v2/{path}"
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


def _backup_key(endpoint, pid):
    """Filename-safe backup key. Prefixing the endpoint disambiguates equal ids
    across resource types (pages/10 vs posts/10) and sanitizes the slashes in
    template-part ids like 'theme//slug'."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", f"{endpoint}__{pid}")


def backup(endpoint, pid):
    """Fetch and back up content + status under backup_dir(), byte-for-byte."""
    data = fetch_raw(endpoint, pid)
    out_dir = backup_dir()
    os.makedirs(out_dir, exist_ok=True)
    key = _backup_key(endpoint, pid)
    with open(os.path.join(out_dir, f"{key}_original.txt"), "w", encoding="utf-8") as f:
        f.write(data["content"]["raw"])
    with open(os.path.join(out_dir, f"{key}_status.txt"), "w", encoding="utf-8") as f:
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


# --- Creating resources (reusable blocks / synced patterns) ---

def create_resource(endpoint, fields):
    """Create a new resource (e.g. a reusable block / synced pattern on 'blocks').

    Creation has no prior state to back up; make it reversible by checking
    find_by_slug() before creating and delete_resource() to undo.
    """
    return _request("POST", endpoint, data=json.dumps(fields).encode())


def find_by_slug(endpoint, slug):
    """Return the first item on endpoint matching slug, or None."""
    items = _request("GET", f"{endpoint}?slug={urllib.parse.quote(slug)}&context=edit")
    return items[0] if items else None


def delete_resource(endpoint, pid, force=True):
    """Delete a resource. Used to undo a create_resource()."""
    suffix = "?force=true" if force else ""
    return _request("DELETE", f"{endpoint}/{pid}{suffix}")


# --- Structural writes (full template part / page rebuilds) ---

_BLOCK_DELIM = re.compile(
    r"<!--\s*(?P<close>/)?wp:(?P<type>[a-z][a-z0-9-]*(?:/[a-z][a-z0-9-]*)?)"
    r"(?P<rest>.*?)(?P<self>/)?\s*-->",
    re.DOTALL,
)


def assert_balanced_blocks(content):
    """Raise ValueError if block-comment delimiters are unbalanced or mis-nested.

    Structural writes replace a whole tree, so 'only block N changed' can't be the
    check; instead confirm the new markup is well-formed before it is saved.
    """
    stack = []
    for m in _BLOCK_DELIM.finditer(content):
        btype = m.group("type")
        if m.group("self"):
            continue
        if m.group("close"):
            if not stack or stack[-1] != btype:
                raise ValueError(f"unbalanced block markup: unexpected closing wp:{btype}")
            stack.pop()
        else:
            stack.append(btype)
    if stack:
        unclosed = ", ".join("wp:" + t for t in stack)
        raise ValueError(f"unbalanced block markup: unclosed {unclosed}")
    return True


def save_structural(endpoint, pid, new_content, status, *, confirm):
    """Replace a resource's entire block tree (template part, full page rebuild).

    Unlike update_block_text, this does not preserve surrounding blocks, so it is
    gated: requires an existing backup, explicit confirm=True (human review), and a
    balanced-markup check. Roll back with rollback.py if the result is wrong.
    """
    if not confirm:
        raise ValueError("structural writes require confirm=True after human review")
    backup_path = os.path.join(backup_dir(), f"{_backup_key(endpoint, pid)}_original.txt")
    if not os.path.exists(backup_path):
        raise RuntimeError(
            f"no backup at {backup_path}; call backup({endpoint!r}, {pid!r}) first"
        )
    assert_balanced_blocks(new_content)
    return save_content(endpoint, pid, new_content, status)


# --- Global styles (theme.json design tokens via REST) ---
#
# Set the design system (layout widths, colour palette as real theme slugs,
# typography, custom properties) in the active theme's *user* global-styles
# record instead of injected CSS. This is what kills the per-section width/colour
# guessing on block themes: contentSize/wideSize and palette slugs become global.
# See references/block-theme-layout.md.


def _deep_merge(base, patch):
    """Recursively merge patch into base. Dicts merge key-by-key; every other
    value (including lists like a colour palette) replaces wholesale."""
    out = dict(base or {})
    for key, val in patch.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def discover_global_styles_id():
    """Return the editable user global-styles post id for the active theme.

    Read from the active theme's `wp:user-global-styles` REST link, never guessed
    (the id is install-specific). Requires context=edit auth.
    """
    themes = _request("GET", "themes?status=active&context=edit")
    theme = themes[0] if isinstance(themes, list) else themes
    link = (theme.get("_links") or {}).get("wp:user-global-styles")
    if not link:
        raise RuntimeError("active theme exposes no wp:user-global-styles link")
    return link[0]["href"].rstrip("/").split("/")[-1]


def get_global_styles(gid=None):
    """Fetch the user global-styles record (settings + styles). Discovers the id
    when not given. Note: WordPress nests *user* palette/font values under a
    `custom` origin key on read (e.g. settings.color.palette.custom)."""
    gid = gid or discover_global_styles_id()
    return _request("GET", f"global-styles/{gid}?context=edit")


def apply_global_styles(settings_patch=None, styles_patch=None, *, gid=None, confirm):
    """Deep-merge a theme.json-shaped patch into the user global-styles record.

    Site-wide write, so it is gated like save_structural: requires confirm=True
    and writes a full JSON backup of the current record first. Roll back by
    POSTing that backup file's {settings, styles} back to the same id.

    settings_patch / styles_patch mirror theme.json, e.g.
        settings={"layout": {"contentSize": "80rem", "wideSize": "90rem"},
                  "color": {"palette": [{"slug": "primary", "color": "#E2001A",
                                          "name": "Primary"}]}}
        styles={"typography": {"fontFamily": "var:preset|font-family|inter"}}
    """
    if not confirm:
        raise ValueError("global-styles writes require confirm=True after human review")
    gid = gid or discover_global_styles_id()
    current = _request("GET", f"global-styles/{gid}?context=edit")

    out_dir = backup_dir()
    os.makedirs(out_dir, exist_ok=True)
    backup_path = os.path.join(out_dir, f"global-styles__{gid}_original.json")
    with open(backup_path, "w", encoding="utf-8") as fh:
        json.dump(current, fh, indent=2)

    payload = json.dumps(
        {
            "settings": _deep_merge(current.get("settings") or {}, settings_patch or {}),
            "styles": _deep_merge(current.get("styles") or {}, styles_patch or {}),
        }
    ).encode()
    return _request("POST", f"global-styles/{gid}", data=payload)

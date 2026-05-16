#!/usr/bin/env python3
"""
WordPress DIVI REST API helpers.
Reads credentials from environment: WP_USER, WP_APP_PASS, WP_SITE.
"""
import re, json, urllib.request, base64, os, time

USER = os.environ["WP_USER"]
PASS = os.environ["WP_APP_PASS"]
SITE = os.environ["WP_SITE"]

auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
read_headers = {"Authorization": f"Basic {auth}"}
write_headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}


def _request(method, path, data=None, retries=3):
    """Simple retry for 429/5xx. WP + Cloudflare can rate-limit bulk writes."""
    url = f"{SITE}/wp-json/wp/v2/{path}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, data=data,
                headers=write_headers if data else read_headers,
                method=method,
            )
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise


def fetch_raw(endpoint, pid):
    """Fetch raw DIVI shortcodes for a page/post/layout.
    endpoint: 'pages', 'posts', 'et_pb_layout', etc.
    """
    return _request("GET", f"{endpoint}/{pid}?context=edit&_fields=id,title,content,status")


def save_content(endpoint, pid, new_content, status):
    """Write content back while preserving original status."""
    payload = json.dumps({"content": new_content, "status": status}).encode()
    return _request("POST", f"{endpoint}/{pid}", data=payload)


def backup(page_id, endpoint="pages"):
    """Fetch and backup content + status to /tmp/wp_backup/."""
    data = fetch_raw(endpoint, page_id)
    os.makedirs("/tmp/wp_backup", exist_ok=True)
    with open(f"/tmp/wp_backup/{page_id}_original.txt", "w") as f:
        f.write(data["content"])
    with open(f"/tmp/wp_backup/{page_id}_status.txt", "w") as f:
        f.write(data["status"])
    return data


def verify_only_buttons_changed(old, new):
    """Scope verification: confirm only et_pb_button opening tags changed."""
    sentinel = lambda s: re.sub(r'\[et_pb_button [^\]]*\]', 'BTN', s)
    return sentinel(old) == sentinel(new)


def update_specific_button(content, old_text, new_text=None, new_url=None):
    """Target a single button by its current button_text value."""
    def replacer(m):
        s = m.group(0)
        if f'button_text="{old_text}"' not in s:
            return s
        if new_text:
            s = re.sub(r'button_text="[^"]*"', f'button_text="{new_text}"', s)
        if new_url:
            s = re.sub(r'button_url="[^"]*"', f'button_url="{new_url}"', s)
        return s
    return re.sub(r'\[et_pb_button [^\]]*\]', replacer, content)


def list_pages_with_buttons():
    """List all pages containing at least one et_pb_button."""
    page = 1
    results = []
    while True:
        chunk = _request(
            "GET",
            f"pages?per_page=100&page={page}&_fields=id,title,status,content"
        )
        if not chunk:
            break
        for item in chunk:
            if "et_pb_button" in item.get("content", {}).get("raw", ""):
                results.append(item)
        if len(chunk) < 100:
            break
        page += 1
    return results

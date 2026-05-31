---
name: managing-divi-sites
description: "Use when managing, styling, or auditing WordPress sites built with the DIVI theme. Triggers on mentions of DIVI shortcodes, et_pb_button, Theme Builder templates, or REST API content edits. Symptoms: button styles inconsistent, hover states resetting, 401 auth failures with SSO, placeholder text, slow DIVI pages, or CSS cache issues."
---

# Managing DIVI Sites

## Overview

Manage WordPress sites using the DIVI theme entirely through the WordPress REST API. No browser, no FTP — all reads and writes go through `https://<site>/wp-json/`.

## When to Use

- Unifying button styles across pages
- Editing text in DIVI modules
- Auditing for placeholder/demo content
- Fixing hover states that reset unexpectedly
- Updating URLs in buttons
- Swapping images via the media API
- Performance audits and optimization

## When NOT to Use

- WordPress plugin development from scratch
- Server-level setup (nginx, PHP-FPM, hosting)
- Non-DIVI page builders (Elementor, Gutenberg)
- Theme Builder visual design (layout changes requiring the UI)

## Quick Reference

| Task                       | How                                                                                    |
| -------------------------- | -------------------------------------------------------------------------------------- |
| List pages with buttons    | Paginate `wp/v2/pages`, grep for `et_pb_button`                                        |
| Fetch raw shortcodes       | `GET /wp/v2/{endpoint}/{id}?context=edit&_fields=id,title,content,status`              |
| Save with status preserved | `POST /wp/v2/{endpoint}/{id}` with `{"content": ..., "status": ...}`                   |
| Backup before change       | Save content to `/tmp/wp_backup/{id}_original.txt` + status to `{id}_status.txt`       |
| Verify scope               | Replace all target shortcodes with placeholder, compare rest to original               |
| Update one button          | Match by `button_text` value, rewrite only that match                                  |
| Rollback                   | `python3 scripts/rollback.py <page_id> [--endpoint pages]` (see `scripts/rollback.py`) |
| Button attributes          | See `references/divi-attributes.md`                                                    |
| Performance audit          | See `references/performance.md`                                                        |
| Example site credentials   | See `references/wordpress_example.md`                                                  |

## Authentication

**Check memory first.** For known sites, credentials live in `references/wordpress_example.md`.

For new sites, ask for:

- Site URL (e.g. `https://dev.example.com`)
- WordPress username
- Application Password

**If the user only has their regular login password**, guide them:

> Go to `wp-admin → Benutzer → Profil`, scroll to "Anwendungspasswörter", enter a name (e.g. `claude-api`), click "Hinzufügen". Paste the generated password here.

Sites using Google SSO block normal password login to the REST API. Application Passwords bypass this.

**Credentials live in env vars only.** Export them for the session:

```bash
export WP_USER="username"
export WP_APP_PASS="xxxx xxxx xxxx xxxx"
export WP_SITE="https://example.com"
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/users/me"
```

If you see a real password in any file inside this skill directory, treat it as leaked and tell the user to rotate it.

## Content Endpoints

A full site audit iterates all of:

- `wp/v2/pages`
- `wp/v2/posts`
- `wp/v2/et_pb_layout` (DIVI Library)
- `wp/v2/et_header_layout`, `wp/v2/et_body_layout`, `wp/v2/et_footer_layout` (Theme Builder)

Skip any that return 404. The fetch + write mechanics are identical — only the path changes.

**Always use `?context=edit`** when fetching. Without it, you get HTML-rendered output with entity-encoded shortcodes that cannot be parsed or written back.

**Always fetch `status` alongside `content`** so you can echo it back on write. If you POST without `status`, a draft page may be accidentally republished.

## Pagination

`per_page` caps at 100. Use a loop with a temporary file and merge in Python:

```bash
page=1
tmpfile=$(mktemp)
trap "rm -f $tmpfile" EXIT
while :; do
  chunk=$(curl -sf -u "$WP_USER:$WP_APP_PASS" \
    "$WP_SITE/wp-json/wp/v2/pages?per_page=100&page=$page&_fields=id,title,link,status")
  if [ $? -ne 0 ]; then break; fi
  count=$(echo "$chunk" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(len(data) if isinstance(data, list) else 0)
")
  [ "$count" -eq 0 ] && break
  echo "$chunk" >> "$tmpfile"
  page=$((page+1))
done
python3 -c "
import sys, json
all_pages = []
with open('$tmpfile') as f:
    for line in f:
        all_pages.extend(json.loads(line))
json.dump(all_pages, sys.stdout, indent=2)
"
```

## Implementation

For all modifications, use the patterns from `scripts/wp_api.py` as reference. Write inline Python that follows this structure:

```python
import re, json, urllib.request, base64, os, time

USER = os.environ["WP_USER"]
PASS = os.environ["WP_APP_PASS"]
SITE = os.environ["WP_SITE"]

auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

# 1. Backup
# Fetch with context=edit, save content + status to /tmp/wp_backup/

# 2. Modify
# Target specific shortcodes by attribute value (e.g. button_text)

# 3. Verify scope
# Replace all modified shortcode types with placeholder, compare remainder to original

# 4. Save
# POST with {"content": new_content, "status": original_status}
```

See `scripts/wp_api.py` for complete implementations of `fetch_raw()`, `save_content()`, `backup()`, `verify_only_buttons_changed()`, and `update_specific_button()`.

## Safety Rules

**No exceptions. These are mandatory for every write.**

1. **Backup first** — save content + status to `/tmp/wp_backup/` before any modification.
2. **Preserve status** — echo back the exact `status` value fetched with `context=edit`.
3. **Target surgically** — regex must match only the shortcode type you're changing.
4. **Verify scope** — after modifying, confirm nothing else changed.
5. **Write page by page** — don't batch all pages into one request.

## After Write: Bust DIVI Cache

DIVI caches compiled CSS in `wp-content/et-cache/`. A style change via REST API will appear to have no effect until the cache is cleared.

Options:

1. Admin UI: `Divi → Theme Options → Builder → Advanced → Static CSS File Generation → Clear`
2. Append `?et_core_page_resource_remove_all=1` to any page URL (requires a logged-in browser session — does not work with REST API / Basic Auth)
3. Delete `wp-content/et-cache/` over SFTP if you have filesystem access

## Common Mistakes

| Mistake                         | Why It Happens                                                         | Fix                                                                            |
| ------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Hover style resets on mouseover | Updated `button_letter_spacing` but not `button_letter_spacing__hover` | Always update both base and `__hover` variants                                 |
| Custom styles ignored           | Missing `custom_button="on"`                                           | Add it before any other button style attributes                                |
| Draft accidentally published    | POST without `status` field                                            | Always echo back fetched status                                                |
| Backup useless                  | Saved only content, not status                                         | `backup()` writes both `_original.txt` and `_status.txt`                       |
| Regex corrupts page             | Used `[^\]]*` on module inner HTML                                     | Match only opening tags with `[^\]]*`; use `(.*?)` with `re.DOTALL` for bodies |
| Auth returns 401                | SSO plugin blocks normal passwords                                     | Create an Application Password in user profile                                 |

## Institutional Knowledge

**Authentication**

- Google Apps Login (OAuth) blocks standard username/password REST API access. Application Passwords are the only working method.
- Application Passwords work regardless of browser login method.

**Content fetching**

- `GET /wp-json/wp/v2/pages/<id>` without `?context=edit` returns rendered HTML with entity-encoded shortcodes (e.g. `&#8220;` instead of `"`). Unusable for editing. Always use `?context=edit`.
- Use `_fields=title,content,status` to avoid bloated responses.

**Write mechanics**

- Use `POST` (not `PUT`) to update pages.
- Request body is JSON: `{"content": "<raw shortcode string>", "status": "..."}`.
- WordPress accepts raw shortcode strings directly — no escaping needed.

**Media uploads**

- Upload via `POST /wp-json/wp/v2/media` with raw binary body and `Content-Disposition` header.
- Swap all `et_pb_image` `src` references before deleting old attachments. WordPress won't stop you from breaking links.

## Output Format

- **Audits:** table with page title, module type, issue, current vs expected.
- **Style changes:** per-page confirmation like `Bachelorball: 1 button updated`
- **Rollbacks:** list of restored pages.
- Always report skipped pages and why.

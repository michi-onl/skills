---
name: wordpress-divi
description: "Manage, style, and maintain WordPress sites built with the DIVI theme via the REST API. Covers button/style unification, content editing, module-level changes, site audits, and maintenance tasks. TRIGGER when: user mentions WordPress, DIVI, WP theme, wp-admin, page builder, button styles, shortcodes, DIVI modules, or wants to change/audit content or styling on a WordPress site. Also trigger for phrases like 'edit my website', 'fix the buttons', 'change the text on a page', 'audit the site for inconsistencies', 'update the theme', or any task involving a WP+DIVI site. DO NOT TRIGGER when: user asks about WordPress plugin development from scratch, hosting setup, server-level WP install, or non-DIVI page builders like Elementor or Gutenberg blocks."
---

# WordPress + DIVI Theme Management

You manage WordPress sites built with the DIVI theme entirely through the WordPress REST API — no browser, no FTP. All reads and writes go through `https://<site>/wp-json/`.

## Scope

**Target**: Pages, posts, and DIVI library items at the configured site URL via REST API  
**Acceptance criteria**: Content updated correctly; each page's original `status` preserved; DIVI static CSS cache cleared after style changes  
**Off-limits**: No changes to pages not specified by the user; draft pages stay as drafts; credentials stay in env vars only — never in files or shell history

## Step 1 — Get credentials

**Check memory first.** For known sites (e.g. StuV Heidenheim), credentials live in `reference_wordpress_stuv.md`. Do not re-ask for anything already stored there.

If the site is new, ask for:
- Site URL (e.g. `https://dev.example.com`)
- WordPress username
- Application Password

**If the user only has their regular login password**, guide them:
> Go to `wp-admin → Benutzer → Profil`, scroll to "Anwendungspasswörter", enter a name (e.g. `claude-api`), click "Hinzufügen". Paste the generated password here.

Note: Sites using Google SSO or similar OAuth plugins block normal password login to the REST API. Application Passwords bypass this and work regardless of the login method.

**Credentials live in env vars.** Export them as environment variables for the session, then reference the variables everywhere — curl, Python, rollback snippets. Scripts read from `$WP_USER`, `$WP_APP_PASS`, `$WP_SITE`; the values never appear in files or command history.

```bash
export WP_USER="username"
export WP_APP_PASS="xxxx xxxx xxxx xxxx"
export WP_SITE="https://example.com"
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/users/me"
```

In Python, read from env: `os.environ["WP_USER"]`, `os.environ["WP_APP_PASS"]`. If you ever see a real password in a file inside the skill directory or in an eval JSON, treat it as leaked and tell the user to rotate it.

## Step 2 — Verify access

```bash
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/users/me" | python3 -m json.tool
```

A 200 response with user data means you're in. A 401 means the Application Password is wrong or REST API auth is disabled. If you get a redirect to a login page, the site uses SSO — the user must create an Application Password.

## Step 3 — Read before writing

Always fetch content before touching anything.

### List all pages (with pagination)

`per_page` caps at 100. For larger sites, loop until you get fewer results than requested, or read the `X-WP-TotalPages` response header.

```bash
page=1
while :; do
  chunk=$(curl -s -u "$WP_USER:$WP_APP_PASS" \
    "$WP_SITE/wp-json/wp/v2/pages?per_page=100&page=$page&_fields=id,title,link,status")
  count=$(echo "$chunk" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
  [ "$count" -eq 0 ] && break
  echo "$chunk"
  page=$((page+1))
done
```

### Fetch raw DIVI content (critical: use `context=edit`)
```bash
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/pages/<ID>?context=edit&_fields=title,content,status"
```

Always request `status` so you can preserve it on write — see "Preserve `status` on write" below.

### Other content types to audit

`pages` is rarely the whole site. DIVI content also lives in:

- **`wp/v2/posts`** — blog posts. Same shortcode structure as pages.
- **`wp/v2/et_pb_layout`** — DIVI Library items (saved sections/rows/modules reused across pages). A button defined here propagates everywhere it's embedded, so a site-wide button unify pass **must** include this endpoint or it will look half-finished.
- **`wp/v2/et_header_layout`, `wp/v2/et_body_layout`, `wp/v2/et_footer_layout`** — DIVI Theme Builder templates (global header/footer/body). Buttons in a global header are invisible to a `pages`-only audit.

For each endpoint, the fetch + write mechanics are identical — only the path changes. A full site audit iterates all of: `pages`, `posts`, `et_pb_layout`, and the three theme builder CPTs, skipping any that return 404 (not every site uses the Theme Builder).

Without `context=edit`, you get HTML-rendered output with HTML-entity-encoded shortcodes — useless for editing. With `context=edit`, you get raw DIVI shortcodes like:
```
[et_pb_button button_text="Click me" button_bg_color="#e2001a" ...]
```

## DIVI Shortcode Mechanics

DIVI stores page content as nested shortcodes:
```
[et_pb_section ...][et_pb_row ...][et_pb_column ...][et_pb_button ...][/et_pb_column][/et_pb_row][/et_pb_section]
```

Key module types you'll encounter:
- `et_pb_button` — call-to-action buttons
- `et_pb_text` — text blocks (contains HTML)
- `et_pb_image` — images
- `et_pb_section` / `et_pb_row` / `et_pb_column` — layout structure

### Button attributes reference

| Attribute | Purpose | Example |
|---|---|---|
| `custom_button` | Enables custom styling | `"on"` |
| `button_text_color` | Text color | `"#ffffff"` |
| `button_bg_color` | Background | `"#e2001a"` or `"gcid-primary-color"` |
| `button_border_radius` | Roundness | `"100px"` (pill) |
| `button_border_width` | Border | `"0px"` |
| `button_text_size` | Font size | `"15px"` |
| `button_font` | Font stack + style | `"\|700\|\|on\|\|\|\|\|"` (bold+uppercase) |

**`button_font` field legend** — DIVI stores this as an 8-field pipe-delimited string: `family|weight|style|uppercase|underline|strike|color|line_height`. An empty `family` means "inherit theme default" and is usually what you want. `weight` is a numeric CSS weight (`400`, `700`). `style` is `on` for italic. `uppercase` is `on` to force caps. Leaving the trailing fields empty is fine. The same format applies to `body_font`, `header_font`, etc.
| `button_letter_spacing` | Spacing | `"2px"` |
| `button_letter_spacing__hover` | Hover spacing | `"2px"` |
| `button_letter_spacing__hover_enabled` | Enable hover override | `"on"` |
| `custom_padding` | Padding (T\|R\|B\|L) | `"14px\|40px\|14px\|40px\|true\|true"` |
| `box_shadow_style` | Shadow preset | `"preset1"` |
| `box_shadow_vertical` | Shadow Y offset | `"6px"` |
| `box_shadow_blur` | Shadow blur | `"20px"` |
| `box_shadow_color` | Shadow color | `"rgba(226,0,26,0.32)"` |

**Critical DIVI quirk:** Hover state uses double-underscore attributes (`button_X__hover`, `button_X__hover_enabled`), not single-underscore (`button_X_hover`). Always check for and update both when changing a style property. If you only update `button_letter_spacing` but leave `button_letter_spacing__hover` at an old value, the style will snap back on hover.

`gcid-primary-color` is a DIVI global color token — it resolves to whatever primary color is set in DIVI Theme Options. Prefer it over hardcoded hex when the style should follow the brand color.

## Making Changes Safely

Use this Python pattern for all content modifications. Credentials come from the environment — never hardcode them.

```python
import re, json, urllib.request, base64, os, time

USER = os.environ["WP_USER"]
PASS = os.environ["WP_APP_PASS"]
SITE = os.environ["WP_SITE"]

auth = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
read_headers  = {"Authorization": f"Basic {auth}"}
write_headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}

def _request(method, path, data=None, retries=3):
    # Simple retry for 429/5xx. WP + Cloudflare can rate-limit bulk writes.
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
    # endpoint: "pages", "posts", "et_pb_layout", etc.
    return _request("GET", f"{endpoint}/{pid}?context=edit&_fields=id,title,content,status")

def save_content(endpoint, pid, new_content, status):
    # Preserve status so a draft is not accidentally republished and vice versa.
    payload = json.dumps({"content": new_content, "status": status}).encode()
    return _request("POST", f"{endpoint}/{pid}", data=payload)
```

### Preserve `status` on write

DIVI pages can be `publish`, `draft`, `pending`, `private`, or `future` (scheduled). If you POST `{"content": ...}` without `status`, WordPress defaults to whatever the request interprets — and a page fetched from `context=edit` while in `draft` can end up flipped to `publish` on save. **Always fetch `status` in the same call as `content`, then echo it back in the write payload.** Never write to a `future` (scheduled) post without asking the user — you'd either republish it immediately or break the schedule.

Do not POST to `/pages/<id>/revisions` or `/autosaves` unless the user specifically asks — those are different endpoints with their own semantics. Plain `POST /pages/<id>` updates the live post and creates a new revision automatically.

### After write: bust DIVI's static CSS cache

DIVI caches compiled CSS per page in `wp-content/et-cache/`. A button style change written via the REST API will look like it didn't take effect until that cache is cleared. Options:

1. Admin UI: `Divi → Theme Options → Builder → Advanced → Static CSS File Generation → Clear`.
2. Force a rebuild by appending `?et_core_page_resource_remove_all=1` to any page URL while logged in.
3. Delete `wp-content/et-cache/` over SFTP if you have filesystem access.

Tell the user which option to use and, if they report "nothing changed," check this before debugging the shortcode.

### Safety checklist before every write

1. **Backup first** — save original to `/tmp/wp_backup/<page_id>_original.txt`
2. **Target surgically** — use regex that matches only the shortcode type you're changing (`[et_pb_button ...]`, not the whole content)
3. **Verify scope** — after applying changes, replace all target shortcodes with a placeholder and compare the rest to the original. If anything else changed, abort.
4. **Write page by page** — don't batch all pages into one request; write one, confirm status, continue

```python
# Scope verification pattern
def verify_only_buttons_changed(old, new):
    sentinel = lambda s: re.sub(r'\[et_pb_button [^\]]*\]', 'BTN', s)
    return sentinel(old) == sentinel(new)
```

### Rollback

Credentials come from the environment so they never land in shell history. Pass the page ID as an argument.

```bash
PAGE_ID=123 python3 - <<'PY'
import os, json, base64, urllib.request
pid = os.environ["PAGE_ID"]
user = os.environ["WP_USER"]; pw = os.environ["WP_APP_PASS"]; site = os.environ["WP_SITE"]
auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
with open(f"/tmp/wp_backup/{pid}_original.txt") as f:
    content = f.read()
# Also restore status if saved alongside the content.
payload = json.dumps({"content": content}).encode()
req = urllib.request.Request(
    f"{site}/wp-json/wp/v2/pages/{pid}",
    data=payload,
    headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
    method="POST",
)
urllib.request.urlopen(req)
print(f"Rolled back page {pid}.")
PY
```

When backing up, save both content and status side by side (e.g. `<id>_original.txt` + `<id>_status.txt`) so rollback can restore both.

## Common Tasks

### Unify button styles across all pages

1. Fetch all pages, filter those with `et_pb_button` in content
2. Extract current button attributes from each to identify inconsistencies
3. Propose a unified style to the user (color, radius, font, shadow, padding)
4. Apply with the safety pattern above
5. Verify by re-fetching and spot-checking

### Audit for inconsistencies

Useful things to check across all pages:
- Button colors that differ from the primary color
- Mixed `button_border_radius` values (0px vs 100px is a common mix)
- Placeholder/demo text (`View Classes`, `View Courses`, `Lorem ipsum`)
- Inconsistent fonts (`button_font` containing a hardcoded font name like `Karla|700...` when other buttons use `|700...`)
- Old `_builder_version` values on modules (indicates stale copy-pasted content)

### Edit text content

Text in `et_pb_text` modules is stored as HTML inside the shortcode:
```
[et_pb_text ...]<p>Your text here.</p>[/et_pb_text]
```

Match with: `re.findall(r'\[et_pb_text [^\]]*\](.*?)\[/et_pb_text\]', content, re.DOTALL)`

Edit the HTML inside while leaving the shortcode attributes untouched.

### Change a button's URL or text

Target the specific button by its current `button_text` value to avoid touching others:
```python
def update_specific_button(content, old_text, new_text=None, new_url=None):
    def replacer(m):
        s = m.group(0)
        if f'button_text="{old_text}"' not in s:
            return s  # not the button we want
        if new_text:
            s = re.sub(r'button_text="[^"]*"', f'button_text="{new_text}"', s)
        if new_url:
            s = re.sub(r'button_url="[^"]*"', f'button_url="{new_url}"', s)
        return s
    return re.sub(r'\[et_pb_button [^\]]*\]', replacer, content)
```

## Uploading media

Image audits find oversized images, but fixing them requires uploading a compressed replacement. The media endpoint takes a raw binary body with `Content-Disposition` naming the file.

```bash
curl -s -u "$WP_USER:$WP_APP_PASS" \
  -H "Content-Type: image/jpeg" \
  -H 'Content-Disposition: attachment; filename="hero-optimized.jpg"' \
  --data-binary @./hero-optimized.jpg \
  "$WP_SITE/wp-json/wp/v2/media"
```

The response returns the new media ID and `source_url`. To swap an old image for the new one inside DIVI shortcodes, fetch each page, find `et_pb_image` modules whose `src` matches the old URL, and rewrite `src` plus any `_builder_version`-adjacent attributes referencing the old file. Then — and only then — delete the old attachment via `DELETE /media/<old_id>?force=true`.

Don't delete the old attachment before confirming every reference has been swapped. WordPress won't stop you, and you'll end up with broken image links.

## Institutional Knowledge — Don't Relearn This

Hard-won facts from past sessions. Treat these as established truth.

**Authentication**
- This site uses Google Apps Login (OAuth). Standard username/password login to the REST API returns 401. The only working auth method is an Application Password created under `wp-admin → Benutzer → Profil → Anwendungspasswörter`.
- Application Passwords work regardless of how the user logs in via the browser.

**DIVI content fetching**
- `GET /wp-json/wp/v2/pages/<id>` without `?context=edit` returns rendered HTML with HTML-entity-encoded shortcodes (e.g. `&#8220;` instead of `"`). These cannot be parsed or written back. Always use `?context=edit`.
- Use `_fields=title,content` to avoid fetching unnecessary post meta that bloats the response.

**DIVI hover attribute quirk**
- DIVI uses double-underscore `__hover` for hover state values: `button_letter_spacing__hover="2px"` and `button_letter_spacing__hover_enabled="on"`.
- The single-underscore variant `button_letter_spacing_hover` exists but is a legacy/unused field. Setting it has no effect on the rendered style. Always use `__hover`.
- If you change a base style property (e.g. `button_letter_spacing`) without also updating `button_X__hover`, the style reverts on hover.

**DIVI write mechanics**
- Use `POST` (not `PUT`) to update pages via the REST API.
- The request body is JSON: `{"content": "<raw shortcode string>"}`.
- WordPress accepts the raw shortcode string directly — no escaping needed.

**DIVI global colors**
- `gcid-primary-color` is a token, not a hex value. It resolves to whatever is set in DIVI Theme Options → General → Colors. Prefer it for brand-colored elements so they update automatically if the palette changes.
- Hardcoded hex values (like `#e2001a`) override the global token. Use hardcoded hex only when a specific element intentionally deviates from the brand color.

**`custom_button="on"` is required**
- DIVI ignores all custom button style attributes unless `custom_button="on"` is present. If a button doesn't appear to be styled despite having color/radius attributes, this is almost always the cause.

**Regex safety**
- Inside the opening tag of a shortcode (the `[et_pb_button ...]` part), attribute values are quoted and never contain a literal `]`, so `\[et_pb_button [^\]]*\]` safely matches only the opening tag.
- This rule applies only to the opening tag. The **inner HTML** of modules like `et_pb_text` and `et_pb_code` freely contains `]` characters (links, JS, template output). Never try to match a whole module body with `[^\]]*`. For bodies, use a non-greedy match against the closing shortcode: `\[et_pb_text [^\]]*\](.*?)\[/et_pb_text\]` with `re.DOTALL`.
- `et_pb_code` modules can contain raw HTML and JavaScript — treat them as opaque. Don't touch them unless the user specifically asks.
- Closing tags (`[/et_pb_button]`) are rare for buttons — buttons are self-closing.

## Performance

When asked about site performance, work through these in order — biggest wins first.

### DIVI Built-in Performance Settings

Check and enable under `wp-admin → Divi → Theme Options → General → Performance`:

| Setting | What it does | Recommended |
|---|---|---|
| Static CSS File Generation | Writes inline CSS to a file instead of computing per-request | On |
| Combine JavaScript Files | Merges DIVI's many JS files into one | On |
| Combine Third Party Plugins | Includes plugin CSS/JS in the combined files | On |
| Defer jQuery Loading | Loads jQuery after page render | On (test first — can break sliders) |
| Critical CSS | Inlines above-the-fold CSS, loads rest async | On |
| Dynamic CSS | Only loads CSS for modules actually used on the page | On |

After toggling any of these, clear DIVI's static cache under `Divi → Theme Options → Builder → Advanced → Static CSS File Generation → Clear`.

### Page Weight Audit

```bash
# Check response size and TTFB for each published page
for slug in "" campus referate vorsitz linktree bachelorball kontakt; do
  url="https://dev.stuv-heidenheim.de/$slug"
  result=$(curl -s -o /dev/null -w "%{size_download}B %{time_starttransfer}s" "$url")
  echo "$slug: $result"
done
```

Flag pages over 500KB or TTFB over 1s.

### Image Audit

Fetch all media to find unoptimized images:
```bash
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/media?per_page=100&_fields=id,title,source_url,media_details" | \
  python3 -c "
import sys, json
items = json.load(sys.stdin)
for i in items:
    details = i.get('media_details', {})
    w = details.get('width', 0)
    h = details.get('height', 0)
    size = details.get('filesize', 0)
    if size > 200000 or w > 2400:
        print(f'LARGE: {i[\"title\"][\"rendered\"]} — {w}x{h} — {size//1024}KB')
        print(f'  {i[\"source_url\"]}')
"
```

Images over 200KB or wider than 2400px on a site this size are candidates for compression.

### Plugin Audit

Installed plugins directly affect load time. Check active plugins:
```bash
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/plugins?per_page=100&_fields=name,status,plugin"
```

Flag anything that loads front-end assets (JS/CSS) and isn't actively used on public pages.

### Caching

If the site doesn't use a caching plugin (W3 Total Cache, WP Rocket, LiteSpeed Cache), every page is rendered from scratch on each request. Check:
```bash
curl -v "https://<site>/" 2>&1 | grep -i "x-cache\|cache-control\|cf-cache"
```

A `HIT` in `X-Cache` or `CF-Cache-Status` means caching is working. A `MISS` or absent header means no caching — recommend installing WP Rocket or enabling server-level caching.

### Core Web Vitals Reference

Target values for a site this size:
- LCP (Largest Contentful Paint): under 2.5s
- CLS (Cumulative Layout Shift): under 0.1
- INP (Interaction to Next Paint): under 200ms

DIVI's biggest CLS risk: images without explicit `width`/`height` attributes. Check `et_pb_image` modules for missing dimension attributes.

## Output format

For audits, present findings as a table: page title, module type, issue, current value vs expected.

For style changes, confirm what changed per page: `Bachelorball: 1 button updated ✓`

For rollbacks, confirm which pages were restored.

Always report if a page was skipped and why.

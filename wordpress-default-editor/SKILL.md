---
name: wordpress-default-editor
description: Use when editing WordPress sites that use the default block editor (Gutenberg) via the REST API. Symptoms include updating headings, paragraphs, buttons, or images; fixing placeholder text; auditing content; or bulk text changes. Requires a WordPress Application Password.
---

# WordPress Default Editor

## Overview

Edit WordPress sites running the default block editor through `https://<site>/wp-json/`. All reads and writes use the WordPress REST API with Basic Auth (Application Password).

## When to Use

- Updating text in heading, paragraph, button, or image blocks
- Fixing placeholder or demo content
- Auditing pages/posts for specific text
- Swapping image URLs
- Publishing, unpublishing, or changing post status

## When NOT to Use

- DIVI sites (use managing-divi-sites)
- Server-level setup (nginx, PHP, hosting)
- Plugin or theme development
- Visual layout redesign that requires the block editor UI (full template-part or page rebuilds *expressed as block markup* are supported — see "Structural writes, creates & template parts")

## Quick Reference

| Task | How |
|------|-----|
| List pages | `GET /wp-json/wp/v2/pages?per_page=100&_fields=id,title,status` |
| Fetch raw blocks | `GET /wp-json/wp/v2/{endpoint}/{id}?context=edit&_fields=id,title,content,status` |
| Save | `POST /wp-json/wp/v2/{endpoint}/{id}` with `{"content": ..., "status": ...}` |
| Backup | `scripts/wp_block_api.py backup(endpoint, pid)` writes to `/tmp/wp_backup/<site>/` |
| Update text (leaf) | `scripts/wp_block_api.py update_block_text(content, block_type, old_text, new_text)` |
| Verify scope | `scripts/wp_block_api.py verify_only_text_changed(old, new, block_type, old_text, new_text)` |
| Structural write | `scripts/wp_block_api.py save_structural(endpoint, id, content, status, confirm=True)` (full tree; backup + balanced-markup gated) |
| Create resource | `scripts/wp_block_api.py create_resource("blocks", {...})`; undo with `delete_resource`; dedupe with `find_by_slug` |
| Template part | endpoint `template-parts`, id `theme//slug` (e.g. `twentytwentyfive//header`) |
| Rollback | `python3 scripts/rollback.py <id> [--endpoint pages]` (id may be `theme//slug`) |

## Authentication

**Check memory and `references/auth.md` first.** For a new site, ask for the site URL, WordPress username, and an Application Password (see `references/auth.md` to create one). Google SSO blocks normal-password REST login; Application Passwords bypass it. Then export and verify:

```bash
export WP_USER="username"
export WP_APP_PASS="xxxx xxxx xxxx xxxx"
export WP_SITE="https://example.com"
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/users/me"
```

### REST root / permalinks

The client builds URLs as `$WP_SITE/wp-json/...`, which assumes **pretty permalinks** (the usual case — e.g. a postname structure like `/sample-post/`). If the site uses *plain* permalinks (`?p=123`) or a plugin blocks the pretty REST route, `/wp-json/` 404s. Set `WP_REST_ROOT` instead of hacking `WP_SITE`:

```bash
export WP_REST_ROOT="index.php/wp-json"   # plain-permalink REST root
```

Confirm which root works before writing: `curl -s -o /dev/null -w "%{http_code}\n" "$WP_SITE/wp-json/"`.

## Content Endpoints

A full site audit iterates all of:

- `wp/v2/pages`
- `wp/v2/posts`
- Custom post types registered with `show_in_rest=true`

Skip any endpoint that returns 404. The fetch and write mechanics are identical; only the path changes.

**Always use `?context=edit`.** Without it, the API returns rendered HTML with entity-encoded block comments that cannot be parsed or written back.

**Always fetch `status` alongside `content`** so you can echo it back on write. POSTing without `status` can accidentally publish a draft.

## Implementation

For all modifications, use the pattern in `scripts/wp_block_api.py`:

```python
import scripts.wp_block_api as wp

# 1. Backup
data = wp.backup("pages", 1)
old_content = data["content"]["raw"]
status = data["status"]

# 2. Modify
new_content = wp.update_block_text(
    old_content, "paragraph", "old text", "new text"
)

# 3. Verify scope
if not wp.verify_only_text_changed(old_content, new_content, "paragraph", "old text", "new text"):
    raise RuntimeError("Scope check failed")

# 4. Save
wp.save_content("pages", 1, new_content, status)
```

Only edit **leaf blocks** (heading, paragraph, button, image) with this helper. Target a button as `block_type="button"`, not the `buttons` wrapper. If a change touches nested blocks (columns, groups, query loops), stop and ask the user for confirmation before saving.

`update_block_text` refuses (raises) when `old_text` matches more than one block of that type. Pass a longer, unique snippet to disambiguate rather than letting it guess.

## Structural writes, creates & template parts

`update_block_text` is for surgical leaf edits. Three operations go beyond it; all keep the same auth, backup, and rollback discipline.

**Structural write — replace a whole block tree** (a template part, or a full page rebuild from section markup). This intentionally does *not* preserve surrounding blocks, so "verify scope" is replaced by a backup requirement, an explicit `confirm=True`, and a balanced-markup check:

```python
import scripts.wp_block_api as wp

wp.backup("template-parts", "twentytwentyfive//header")          # required, or it raises
new = open("scripts/data/header_blocks.html").read_text()
wp.save_structural("template-parts", "twentytwentyfive//header", new, "publish", confirm=True)
```

`save_structural(endpoint, id, content, status, *, confirm)` raises unless `confirm=True`, a backup already exists for that resource, and `assert_balanced_blocks(content)` passes (block-comment delimiters nest correctly). Roll back with `rollback.py`.

**Template parts & templates** use the `template-parts` (or `templates`) endpoint and a string id `theme//slug`, e.g. `twentytwentyfive//header`. `fetch_raw`, `save_content`, `save_structural`, `backup`, and `rollback.py` all accept that id form.

**Create a resource** — synced patterns / reusable blocks live on `wp/v2/blocks`. There is no prior state to back up, so make it reversible: check `find_by_slug` first (idempotency), and `delete_resource` to undo.

```python
existing = wp.find_by_slug("blocks", "stuv-hero")
if existing is None:
    wp.create_resource("blocks", {
        "title": "Stuv Hero", "slug": "stuv-hero",
        "content": pattern_markup, "status": "publish",
        "meta": {"wp_pattern_sync_status": "fully"},
    })
```

## Safety Rules

No exceptions. Mandatory for every write.

1. **Backup first** — save content + status to `/tmp/wp_backup/<site>/` before any modification. Backups are namespaced per site, so the same page id on two sites can't collide.
2. **Preserve status** — echo back the exact `status` value fetched with `?context=edit`.
3. **Target surgically** — match by block type and the exact old text; never global search/replace across the whole page.
4. **Verify scope** — confirm only the targeted block changed. For a deliberate full-tree replacement, scope verification doesn't apply; use `save_structural` instead, which enforces a backup, `confirm=True`, and a balanced-markup check.
5. **Write page by page** — don't batch all pages into a single request.

Creating a resource (`create_resource`) has no prior state to back up; the equivalent safety is `find_by_slug` before creating (idempotency) and `delete_resource` to undo.

## Red Flags — STOP

These thoughts mean stop and follow the safety rules (restore from backup if you already wrote):

- "This change is too small to need a backup"
- "I'll verify scope after saving"
- "Omitting `status` won't change anything"
- "A global find/replace is faster"

An unskilled baseline run skipped the backup and POSTed without `status` — leaving a write it could not undo. Don't repeat it.

## Rollback

If something goes wrong, restore from the backup. Pass `--endpoint` for anything other than pages; the id may be a `theme//slug` template-part id:

```bash
python3 scripts/rollback.py 1
python3 scripts/rollback.py "twentytwentyfive//header" --endpoint template-parts
```

## Common Mistakes

| Mistake | Why It Happens | Fix |
|---------|----------------|-----|
| Corrupted nested blocks | Regex greedily matched across group/column boundaries | Only edit leaf blocks; ask for nested changes |
| `old_text matches N blocks` error | Same snippet appears in several blocks | Pass a longer, unique `old_text` |
| Auth returns 401 | SSO plugin blocks normal passwords | Create an Application Password |
| Changes not visible | Browser/CDN cache | Hard-refresh or clear cache |

## Output Format

- **Audits:** table with page title, block type, issue, current vs expected.
- **Edits:** per-page confirmation like `Home: 1 paragraph updated`.
- **Rollbacks:** list of restored pages.
- Always report skipped pages and why.

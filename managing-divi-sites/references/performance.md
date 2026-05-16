# DIVI Performance Audit Reference

Work through these in order — biggest wins first.

## DIVI Built-in Performance Settings

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

## Page Weight Audit

```bash
# Check response size and TTFB for each published page
for slug in "" campus referate vorsitz linktree bachelorball kontakt; do
  url="https://dev.stuv-heidenheim.de/$slug"
  result=$(curl -s -o /dev/null -w "%{size_download}B %{time_starttransfer}s" "$url")
  echo "$slug: $result"
done
```

Flag pages over 500KB or TTFB over 1s.

## Image Audit

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

## Plugin Audit

Installed plugins directly affect load time. Check active plugins:

```bash
curl -s -u "$WP_USER:$WP_APP_PASS" "$WP_SITE/wp-json/wp/v2/plugins?per_page=100&_fields=name,status,plugin"
```

Flag anything that loads front-end assets (JS/CSS) and isn't actively used on public pages.

## Caching

If the site doesn't use a caching plugin (W3 Total Cache, WP Rocket, LiteSpeed Cache), every page is rendered from scratch on each request. Check:

```bash
curl -v "https://<site>/" 2>&1 | grep -i "x-cache\|cache-control\|cf-cache"
```

A `HIT` in `X-Cache` or `CF-Cache-Status` means caching is working. A `MISS` or absent header means no caching — recommend installing WP Rocket or enabling server-level caching.

## Core Web Vitals Reference

Target values for a site this size:
- LCP (Largest Contentful Paint): under 2.5s
- CLS (Cumulative Layout Shift): under 0.1
- INP (Interaction to Next Paint): under 200ms

DIVI's biggest CLS risk: images without explicit `width`/`height` attributes. Check `et_pb_image` modules for missing dimension attributes.

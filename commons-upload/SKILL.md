---
name: commons-upload
description: >
  Evaluate, curate, and prepare images for upload to Wikimedia Commons. Use this skill
  whenever the user wants to upload photos to Wikimedia Commons, contribute images to
  Wikipedia, prepare stock photos for Commons, assess image quality for Commons, create
  Wikimedia description boxes, generate {{Information}} templates, rename images for
  Commons conventions, or categorize photos for Wikimedia. Also trigger when the user
  mentions "Commons upload", "Wikimedia", "Commons-tauglich", "Bilder hochladen",
  "Commons-Beschreibung", or has a batch of images they want to filter and prepare for
  contribution. This skill covers the full pipeline from raw image directory to
  upload-ready files with descriptions — not just one step.
---

# Commons Upload — Wikimedia Commons Image Pipeline

Take a directory of images and upload them to Wikimedia Commons: technically vetted,
visually reviewed, deduplicated, renamed, described, categorized, metadata-stripped,
and uploaded via Pywikibot.

## Pipeline Overview

Ten steps. Steps 1-7 produce the upload-ready set. Steps 8-10 handle the actual upload.

```
Raw images
  → 1. Resolution check (drop sub-2MP)
  → 2. EXIF extraction (flag technical issues)
  → 3. Format duplicate pruning (.JPG vs .jpeg)
  → 4. Gather location context for image clusters
  → 5. Visual review + tier classification + near-duplicate flagging
  → 6. Resolve near-duplicates (pick best per group)
  → 7. Copy+rename to upload/, strip metadata, generate descriptions
  → 8. Dry-run preview (user confirmation gate)
  → 9. Upload to Commons via Pywikibot
  → 10. Post-upload verification + log
```

## Before Starting

Use these defaults unless the user explicitly overrides them for a given session:

- **Wikimedia Commons username**: `Mike is Michi`
- **License**: CC BY-SA 4.0
- **Copyright**: User-created (confirmed). The user owns their images.

If the user mentions a different username, license, or copyright situation, use that
instead. Otherwise, proceed directly with these values. Do NOT ask for confirmation each
time.

Do NOT ask for location context yet. That comes in step 4 after the visual landscape of
the image set is known.

## Step 1: Resolution Check

The cheapest filter. Run resolution extraction across all images first (sips, PIL, or
exiftool — whichever is fastest on the platform). Drop anything below 2 megapixels.

This is a hard cut, not a flag. Sub-2MP images have no realistic Commons value.

Report: total images, how many dropped, how many survive to step 2.

## Step 2: EXIF Extraction

Run on survivors only. Extract in a single batch operation — not one subprocess per file.
Prefer `exiftool -csv` for batch extraction. It handles all fields in one pass and
outputs structured data. Fall back to sips+mdls or Python PIL only if exiftool is
unavailable.

| Metric | How to get it |
|---|---|
| Resolution (already have from step 1) | — |
| File size | stat / os.path.getsize |
| ISO | EXIF ISOSpeedRatings / kMDItemISOSpeed |
| Shutter speed | EXIF ExposureTime / kMDItemExposureTimeSeconds |
| Aperture | EXIF FNumber / kMDItemFNumber |
| Focal length | EXIF FocalLength / kMDItemFocalLength |
| Date taken | EXIF DateTimeOriginal / kMDItemContentCreationDate |
| Camera model | EXIF Model (used to set ISO threshold: phone vs camera) |
| Lens ID | EXIF LensModel (used to detect front camera — see step 2b) |

### Step 2b: Front-camera / selfie pre-filter

After extracting EXIF, check the `LensModel` field. On iPhones, the front-facing
camera has a distinct lens identifier (e.g., "iPhone 17 Pro front camera 2.22mm f/1.9"
vs rear lenses). Flag all front-camera images as **likely selfies** and report
them separately.

These are not auto-dropped, but they are excluded from visual review by default. Present
the count and a sample filename to the user. If the user says some front-camera shots
are worth reviewing, view those specifically. Otherwise skip them all in step 5.

This saves enormous context on batches where 20-40% of images are personal portraits.

### Flag thresholds

These are flags shown to the user, not automatic rejections.

| Flag | Condition | Why |
|---|---|---|
| High ISO | > 1250 (phone sensor) / > 3200 (dedicated camera) | Noise |
| Slow shutter | > 1/30s handheld | Motion blur risk |
| Small file | < 500 KB for a multi-MP image | Over-compressed |

Determine phone vs camera from the EXIF camera model field. If unavailable, assume
phone thresholds (more conservative).

### Output of step 2

Present a summary:
- Survivors from step 1, flag count by category
- Flagged images listed with filenames
- Top N candidates ranked by combined technical quality (high res + low ISO + fast
  shutter) — these get reviewed first in step 5

Save the full report to `technical_scan_results.md` so it survives context resets.

If the image count is large (100+), suggest the user start a fresh context window
before step 5.

## Step 3: Format Duplicate Pruning

Identify files with the same base name but different extensions (e.g., `IMG_0302.JPG`
and `IMG_0302.jpeg`). Keep the higher-resolution version, drop the other. Report which
pairs were found and which version was kept.

This is deterministic — no user input needed.

## Step 4: Gather Location Context

Use EXIF GPS data to identify location clusters, then reverse-geocode each cluster
center via the OpenStreetMap Nominatim API to get actual place names automatically.

### Clustering

Group images by date and GPS proximity. Images within ~0.005° (~500m) of each other
belong to the same cluster. For each cluster, compute the center lat/lon.

### Reverse geocoding via Nominatim

Hit the Nominatim reverse endpoint for each cluster center. This eliminates guesswork
and gives real neighborhood/street-level names.

```python
import urllib.request, json, time

clusters = [("A", lat, lon), ...]  # from clustering step

for label, lat, lon in clusters:
    url = (f"https://nominatim.openstreetmap.org/reverse?"
           f"lat={lat}&lon={lon}&format=json&zoom=16&addressdetails=1")
    req = urllib.request.Request(url,
        headers={"User-Agent": "commons-upload-pipeline/1.0"})
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    addr = data.get("address", {})
    suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter") or ""
    road = addr.get("road", "")
    city = addr.get("city") or addr.get("town") or ""
    print(f"Cluster {label}: {suburb}, {road}, {city}")
    time.sleep(1.1)  # Nominatim requires max 1 req/sec
```

**Rate limit**: Nominatim enforces 1 request per second. Always sleep 1.1s between
calls. Set a descriptive User-Agent string.

### Output

Present a table of clusters with the resolved place names. Ask the user to confirm or
correct. The goal: when you reach step 7 (descriptions), every image already has its
location pinned down. No retroactive patching.

If any clusters lack GPS data entirely, ask the user for those locations manually. If
the Nominatim result is too vague (e.g., just a highway name), note which clusters need
refinement and ask during visual review when actual content is visible.

## Step 5: Visual Review + Tier Classification

A single pass. View each surviving image, assess it, and immediately classify it. Do
not separate "review" and "classification" into distinct steps — they're the same
cognitive act.

### Viewing strategy

- Skip front-camera images already flagged in step 2b (unless user overrides).
- Start with the top-ranked technical candidates from step 2.
- View in batches (10–30 depending on context budget).
- After the first batch from a cluster, assess whether the cluster is mostly personal
  photos (portraits, group shots, food, etc.). If so, sample 2-3 more from that cluster
  rather than viewing all of them. Report the skip count to the user.
- For each image, assess and classify in one go:

| Criterion | What to look for |
|---|---|
| Subject matter | Is it identifiable? Would a Wikipedia article use it? |
| Composition | Clean framing, no distracting elements |
| Focus / sharpness | Is the subject in focus? |
| Lighting | Blown highlights, crushed shadows, harsh midday light |
| Obstructions | Cables, poles, fingers, watermarks, logos |
| People | Recognizable faces → model release concern. Flag for user. |
| Redundancy | Near-duplicate of another image in the batch — mark the group |

### Tier classification (assigned during review, not after)

- **Tier 1 — Strong upload candidate**: Sharp, well-composed, identifiable subject,
  encyclopedic value.
- **Tier 2 — Acceptable / situational**: Minor issues (slight overexposure, partially
  cut element, one of several similar shots). Mark near-duplicate groups here.
- **Tier 3 — Skip**: Bland, redundant, technically flawed, or no encyclopedic value.

Present results as a table per tier: filename, subject description, notes on issues.
For Tier 2 near-duplicate groups, indicate which images belong to the same group.

If any location clusters from step 4 were unresolved, ask now — you can see the actual
content.

## Step 6: Resolve Near-Duplicates

For each near-duplicate group flagged in step 5, recommend the single best image and
list the rest as drops. Explain the choice briefly (sharper, better composition, less
obstruction, etc.).

The user confirms before anything is finalized.

Final upload set = all Tier 1 + Tier 2 after deduplication.

## Step 7: Copy+Rename to upload/ and Generate Descriptions

One step, not three. For each image in the final set:

1. Determine the descriptive filename
2. Copy from source to `upload/` with the new name in a single `cp` operation
3. Write the `{{Information}}` block into `wikimedia_descriptions.txt`

No intermediate "move then rename" — the file lands in `upload/` with its final name
directly.

### Strip app-specific metadata

After copying to `upload/`, strip non-photographic metadata embedded by phone apps.
The MOOD: STOCK app embeds junk in several EXIF/XMP fields: title set to
"MOOD: STOCK DIGI-N", UserComment filled with JSON theme config, Description fields
with app labels.

**Step A — macOS extended attributes:**
```bash
for f in upload/*.JPG upload/*.jpg; do
  xattr -d com.apple.metadata:kMDItemComment "$f" 2>/dev/null
  xattr -d com.apple.metadata:kMDItemDescription "$f" 2>/dev/null
done
```

**Step B — EXIF/XMP fields via exiftool:**
```bash
exiftool -overwrite_original \
  -UserComment= \
  -Description= \
  -ImageDescription= \
  -XMP-dc:Description= \
  upload/*.JPG
```

Run both steps before generating descriptions so there's no confusion about what
"description" means. This is mandatory, not optional — files uploaded with app metadata
get flagged on Commons.

### Filename conventions

- Descriptive English name (not IMG_XXXX)
- Include location (already known from step 4)
- Include year
- Keep original extension
- Use spaces, not underscores (Commons convention)
- Concise but specific

**Pattern**: `[Subject] [Location] [Year].[ext]`

```
IMG_0326.JPG → Wilder Kaiser massif panorama Tyrol 2026.JPG
IMG_0594.JPG → Naviglio Grande canal Milan 2026.JPG
IMG_0742.JPG → Port Hercule Monaco with yachts 2026.JPG
```

### Category discovery

Before writing any descriptions, discover the real Commons category names for every
subject and location in the upload set. Never guess a category name and check if it
exists. Instead, search first and pick from results.

**Method**: Use the Commons API `list=search` in namespace 14 (categories) with keyword
queries. This returns actual category names with their real capitalization, punctuation,
and disambiguation patterns.

```bash
# One loop, all subjects at once. Run this BEFORE writing descriptions.
for q in "Notre-Dame+Garde+Marseille" "Vieux-Port+Marseille" "Cours+Julien+Marseille" \
         "Invader+mosaics" "trams+Marseille"; do
  echo "=== $q ==="
  curl -s "https://commons.wikimedia.org/w/api.php?action=query&list=search\
&srsearch=${q}&srnamespace=14&srlimit=5&format=json" \
    | python3 -c "
import sys, json
data = json.load(sys.stdin)
for r in data['query']['search']:
    print(r['title'])"
done
```

**Why search-first matters**: Commons naming is unpredictable. "Notre-Dame de la Garde"
does not exist — the real category is "Basilique Notre-Dame de la Garde." "Vieux-Port de
Marseille" does not exist — it's "Vieux-Port (Marseille)." "Palais de la Bourse
(Marseille)" uses a lowercase 'b' and 'à' instead of parentheses. You will not guess
these correctly.

**Do not** use `action=query&titles=Category:Guessed Name` as the discovery step. That
only confirms or denies an exact string — useless when the real name differs from your
guess. Reserve exact-title checks for a final validation pass only, after you already
have names from search results.

Collect all verified category names into a lookup list, then reference that list when
writing each `{{Information}}` block.

**Minimum categories**: Aim for at least 3 verified categories per image. Use multiple
search queries per subject if the first query doesn't yield enough. Search for the
subject (species, building, artwork), the specific location (neighborhood, park,
museum), and the broader geographic area (city, arrondissement, canton). One real
category is better than a guessed one, but most images should hit 3.

### Description generation

Generate `wikimedia_descriptions.txt` following the exact format in
`references/information-template.txt`. One `{{Information}}` block per image, bilingual
descriptions (English + German), `{{Taken on}}` date template with location, and
categories drawn from the verified lookup list above.

## Step 8: Dry-Run Preview

Before any actual upload, run the upload script in dry-run mode so the user can review
what will happen.

```bash
cd upload/
python upload_to_commons.py --dry-run
```

This prints each filename, file size, and a description preview. Present the output to
the user and wait for explicit confirmation before proceeding to step 9.

**This is a hard gate.** Do not proceed to actual upload without user confirmation.

## Step 9: Upload to Commons

### Venv setup

Before the first upload, check that a `.venv` with pywikibot exists in the working
directory. If not, create it:

```bash
python3 -m venv .venv
.venv/bin/pip install pywikibot
```

### Pywikibot config files

Pywikibot looks for config files in the current working directory. Since the upload
script runs from `upload/`, place both config files **inside the `upload/` directory**.
This is the single most common setup error — putting them in the parent directory
will cause a "username undefined" crash.

Check for `user-config.py` and `user-password.py` in the `upload/` directory. If they
don't exist, generate them there:

**user-config.py:**
```python
family = 'commons'
mylang = 'commons'
usernames['commons']['commons'] = 'Mike is Michi'
password_file = 'user-password.py'
```

**user-password.py:**
```python
('Mike is Michi', BotPassword('commons-upload', 'PASTE_BOT_PASSWORD_HERE'))
```

For the bot password, check the memory file `reference_commons_credentials.md`. Never
hardcode credentials into skill files or commit them.

### Running the upload

```bash
cd upload/
.venv/bin/python upload_to_commons.py --delay 5
```

The upload script is located at
`~/.claude/skills/commons-upload/scripts/upload_to_commons.py`. Copy it to the
`upload/` directory before running, or invoke it with its full path.

**Flags:**
- `--dry-run` — preview without uploading
- `--file "pattern1" "pattern2"` — upload only matching filenames
- `--delay N` — seconds between uploads (default 5)
- `--overwrite` — re-upload files that already exist on Commons (useful after
  stripping metadata from previously uploaded files)
- `--no-verify` — skip post-upload verification

The script writes `upload_log.txt` with timestamps, filenames, status, and Commons URLs.

## Step 10: Post-Upload Verification

The upload script runs verification automatically after uploads complete (unless
`--no-verify` was passed). It checks each file via the Commons API to confirm:

- The file page exists
- Categories rendered correctly

**Propagation delay**: Commons may take 30-60 seconds to index newly uploaded files.
The script's built-in verification often runs too early and reports false "MISSING"
results. If the script reports all files as missing immediately after a successful
upload batch, don't trust it. Instead, wait 30 seconds and run a manual spot-check
on 2-3 files via the API:

```bash
curl -s "https://commons.wikimedia.org/w/api.php?action=query\
&titles=File:Example+Name.JPG&format=json" | python3 -c "
import sys, json
pages = json.load(sys.stdin)['query']['pages']
for pid, p in pages.items():
    print('EXISTS' if int(pid) > 0 else 'MISSING', p['title'])"
```

If spot-checks confirm existence, the batch is fine. Only investigate individual files
that still show as missing after 60+ seconds.

Review `upload_log.txt` and present a summary: total uploaded, skipped, failed, and
links to the Commons file pages.

## Full Pipeline Summary

The complete end-to-end flow when the user invokes this skill:

```
1. Resolution check          — drop sub-2MP
2. EXIF extraction            — flag technical issues
   2b. Front-camera filter    — flag likely selfies, skip in visual review
3. Format duplicate pruning   — keep best version per base name
4. Gather location context    — reverse geocode via Nominatim
5. Visual review + tiers      — classify (skip selfies + sample personal clusters)
6. Resolve near-duplicates    — pick best per group
7. Copy+rename+describe       — upload/ folder with descriptions
   7a. Strip metadata         — exiftool + xattr cleanup
   7b. Generate descriptions  — wikimedia_descriptions.txt (3+ categories each)
8. Dry-run preview            — user reviews before upload
9. Upload to Commons          — venv + pywikibot + bot password (config in upload/)
10. Post-upload verification  — API check (wait for propagation) + log review
```

Steps 1-7 produce the upload-ready set. Steps 8-10 handle the actual upload. The user
must confirm between step 8 and step 9.

## Edge Cases

- **Phone photos vs camera photos**: Determined by EXIF camera model in step 2. Phone
  sensors get stricter ISO thresholds (1250 vs 3200).
- **Panoramas / stitched images**: Unusual aspect ratios are fine. Judge by total
  megapixels, not dimensions.
- **Screenshots or digital art mixed in**: Flag and exclude — Commons requires different
  licensing for these.
- **Images with text overlays / watermarks**: Exclude unconditionally.
- **Missing EXIF GPS**: Common. Don't treat as an error — location comes from user
  input in step 4, not EXIF.
- **Large batches (250+ images)**: Save the step 2 report to disk and suggest a context
  reset before step 5. Reference the saved report in the new context.
- **Re-uploading after metadata fix**: Use `--overwrite` flag. The script will re-upload
  even if the file already exists on Commons.
- **Upload failures**: Check `upload_log.txt` for specifics. Common causes: network
  timeout, file too large, bot password expired. Re-run with `--file "failed_name*"` to
  retry specific files.
---
name: uploading-to-commons
description: "Upload photos to Wikimedia Commons: judge suitability, write {{Information}} descriptions, name and categorize files, filter batches. Trigger: \"Commons\", \"Bilder hochladen\"."
---

# Commons Upload — Wikimedia Commons Image Pipeline

Take a directory of images and upload them to Wikimedia Commons: technically vetted,
visually reviewed, deduplicated, renamed, described, categorized, metadata-stripped,
and uploaded via Pywikibot.

## Scope

**Target**: Images in the user-provided source directory → `upload/` folder → Wikimedia Commons
**Acceptance criteria**: Images uploaded with correct `{{Information}}` blocks, categories, and stripped metadata; `upload_log.txt` records all results
**Off-limits**: Source images are read-only — copy to `upload/`, never modify originals; uploads require explicit user confirmation after the dry-run in Step 8

## Pipeline Overview

Ten steps. Steps 1-7 produce the upload-ready set. Steps 8-10 handle the actual upload.

```
Raw images
  → 1. Resolution check (drop sub-2MP)
  → 2. EXIF extraction (flag technical issues)
  → 3. Gather location context for image clusters (before any judging)
  → 4. Format duplicate pruning (.JPG vs .jpeg)
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
instead. Otherwise, proceed directly with these values.

Location context is gathered in Step 3, before visual review — place names change which
images are worth keeping, not just how they are captioned.

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

Pull GPS in this same pass. Location drives everything downstream, and fetching it now
means step 3 is a pure analysis step with no second extraction.

```bash
exiftool -n -csv \
  -FileName -ImageWidth -ImageHeight -FileSize -ISO -ExposureTime -FNumber \
  -FocalLength -DateTimeOriginal -OffsetTimeOriginal -Model -LensModel \
  -GPSLatitude -GPSLongitude -GPSAltitude -GPSImgDirection \
  *.JPG > exif.csv
```

> **Use `-n`, never the `#` suffix.** `exiftool -csv -GPSLatitude# -GPSLongitude#`
> silently emits **empty columns** even when every file is geotagged. The `#` numeric
> modifier does not work inside `-csv`. The global `-n` flag does the same job and works.
> This failure is silent and looks exactly like a batch with no GPS.

| Metric                                | How to get it                                              |
| ------------------------------------- | ---------------------------------------------------------- |
| Resolution (already have from step 1) | —                                                          |
| File size                             | stat / os.path.getsize                                     |
| ISO                                   | EXIF ISOSpeedRatings / kMDItemISOSpeed                     |
| Shutter speed                         | EXIF ExposureTime / kMDItemExposureTimeSeconds             |
| Aperture                              | EXIF FNumber / kMDItemFNumber                              |
| Focal length                          | EXIF FocalLength / kMDItemFocalLength                      |
| Date taken                            | EXIF DateTimeOriginal / kMDItemContentCreationDate         |
| Camera model                          | EXIF Model (used to set ISO threshold: phone vs camera)    |
| Lens ID                               | EXIF LensModel (used to detect front camera — see step 2b) |
| GPS lat/lon/altitude                  | EXIF GPSLatitude / GPSLongitude / GPSAltitude (see step 3) |
| Compass heading                       | EXIF GPSImgDirection — often absent; see step 3            |

### Never declare a batch ungeotagged from a CSV alone

Before telling the user "these images have no GPS," dump one file in full and look:

```bash
exiftool -a -G1 -s SOMEFILE.JPG | grep -i gps
```

If you see `GPSLatitudeRef: North` and `GPSLongitudeRef: East` but no `GPSLatitude` /
`GPSLongitude` values, that is the signature of a **bad query, not missing data** — the
refs and the values are written together. A genuinely stripped file has no GPS block at
all. Getting this wrong sends the whole session down a branch of asking the user
questions that the metadata already answers.

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

| Flag         | Condition                                         | Why              |
| ------------ | ------------------------------------------------- | ---------------- |
| High ISO     | > 1250 (phone sensor) / > 3200 (dedicated camera) | Noise            |
| Slow shutter | > 1/30s handheld                                  | Motion blur risk |
| Small file   | < 500 KB for a multi-MP image                     | Over-compressed  |

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

## Step 3: Gather Location Context

Use EXIF GPS data to identify location clusters, then reverse-geocode each cluster
center via the OpenStreetMap Nominatim API to get actual place names automatically.

**This comes before visual review, not after.** Knowing the place changes the verdict,
not just the caption. "Generic park at sunset" turns out to be a castle's grounds; an
"unremarkable office block" turns out to be a town hall with its own Commons category; a
cluster assumed to be the user's home town turns out to be a different city entirely.
Tier judgments made without locations have to be redone.

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
        headers={"User-Agent": "uploading-to-commons-pipeline/1.0"})
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

### Second pass: per-image geocoding at zoom 18

Documented here with the rest of the geocoding, but **run it at step 7b** — once step 6
has settled which files are actually being uploaded, so you geocode 30 files and not 300.

Cluster centres at zoom 16 give you the district. For the final set,
re-geocode **those files individually at `zoom=18`**. That is what returns building
names and house numbers, and it routinely identifies the subject outright:
`Maxmonument, Maximilianstraße`, `Haberkasten, 3, Fragnergasse`, `Schloss Hellenstein`,
`Trg Republike Hrvatske`. A landmark name from Nominatim is worth more than any amount
of squinting at the photo.

### Compass heading

`GPSImgDirection` gives the bearing the camera was facing, which is the only reliable way
to work out *which* peak, tower or building across a valley is in frame. iPhones often
omit it. If it is absent, say so and do not name a distant summit — describe it and let
the user supply the name.

### Privacy: GPS is published

Commons displays coordinates on the file page and feeds them into map layers. A photo
taken in the user's garden publishes their home address to the world.

After geocoding, classify each cluster as **public** (landmark, street, park, venue) or
**private** (a residence, workplace, school, or any indoor shot at a non-landmark
address). Show the user the split and ask how to handle it. Default recommendation: keep
coordinates on public-place photos, strip them from private ones. Never let a residential
address reach step 9 without the user having explicitly seen and decided it — the skill's
normal metadata strip in step 7a does **not** remove GPS.

Also keep street addresses out of the `{{Information}}` description for private
locations. "Mühldorf am Inn" is enough; "Colloredostraße 15" is not.

### Output

Present a table of clusters with the resolved place names. Ask the user to confirm or
correct. The goal: when you reach step 7 (descriptions), every image already has its
location pinned down. No retroactive patching.

If any clusters lack GPS data entirely, ask the user for those locations manually — but
only after the verification in step 2 confirms the data really is absent. If the
Nominatim result is too vague (e.g., just a highway name), note which clusters need
refinement and ask during visual review when actual content is visible.

### Asking the user for free text

When you need a place name, venue or spelling that only the user has, **ask in prose**.
Do not offer it as a multiple-choice option like "I'll type the town" — the selection
comes back with no text attached and the question has to be asked twice.

## Step 4: Format Duplicate Pruning

Identify files with the same base name but different extensions (e.g., `IMG_0302.JPG`
and `IMG_0302.jpeg`). Keep the higher-resolution version, drop the other. Report which
pairs were found and which version was kept.

This is deterministic — no user input needed, and it is order-independent. It sits here
purely so that step 5 reviews one file per photograph.

## Step 5: Visual Review + Tier Classification

A single pass. View each surviving image, assess it, and immediately classify it. Do
not separate "review" and "classification" into distinct steps — they're the same
cognitive act.

### Triage with contact sheets, not one image at a time

Opening 179 full-size photos individually will exhaust the context window before the
review is finished. Build **labelled contact sheets** and read those instead. A 3×3 grid
at ~460 px per tile is enough to judge subject, composition, framing and near-duplicate
grouping; a 179-image batch collapses to about 30 sheet reads.

```bash
# 1. downscale once — reuse these previews for every later comparison
mkdir -p prev
for f in *.JPG; do sips -Z 700 "$f" --out "prev/$f" >/dev/null; done

# 2. montage into 3x3 sheets, grouped by date/cluster, filename under each tile
montage prev/IMG_1{649,651,653,655,720,722}.JPG \
  -label '%t' -font /System/Library/Fonts/Supplemental/Arial.ttf \
  -tile 3x3 -geometry 460x460+6+6 -background white -pointsize 24 sheet.jpg
```

> `montage` fails with ``unable to read font `' `` on macOS unless you pass an explicit
> `-font` path. Use `/System/Library/Fonts/Supplemental/Arial.ttf`.

Keep a JSON manifest mapping each sheet to its ordered filenames — the `-label '%t'`
captions are small, and you need certainty about which tile is which file.

Then open individual previews only for: candidates you intend to upload, near-duplicate
groups you must choose between, and anything whose subject you cannot identify from the
tile. For dedup decisions, build a dedicated comparison montage of just that group at a
larger tile size.

### Viewing strategy

- Skip front-camera images already flagged in step 2b (unless user overrides).
- Start with the top-ranked technical candidates from step 2.
- Work cluster by cluster, since each cluster shares a location and a verdict pattern.
- After the first batch from a cluster, assess whether the cluster is mostly personal
  photos (portraits, group shots, food, etc.). If so, sample 2-3 more from that cluster
  rather than viewing all of them. Report the skip count to the user.
- For each image, assess and classify in one go:

| Criterion         | What to look for                                              |
| ----------------- | ------------------------------------------------------------- |
| Subject matter    | Is it identifiable? Would a Wikipedia article use it?         |
| Composition       | Clean framing, no distracting elements                        |
| Focus / sharpness | Is the subject in focus?                                      |
| Lighting          | Blown highlights, crushed shadows, harsh midday light         |
| Obstructions      | Cables, poles, fingers, watermarks, logos                     |
| People            | See "Identifiable people" below — do not over-apply this      |
| Derivative work   | See "Copyright screening" below — this deletes files          |
| Redundancy        | Near-duplicate of another image in the batch — mark the group |

### Copyright screening

A photo can be technically perfect and still be undeletable-on-sight because it
reproduces someone else's copyrighted work. Screen for this during review, not after
upload. Exclude:

| Situation | Why |
| --- | --- |
| Product packaging, book/game/album cover art as the subject | The artwork is the subject; the photo is a derivative work |
| Framed posters, prints, wall graphics in a museum or shop | Same, and no FOP indoors |
| A screen showing a broadcast, film, or game | The displayed content is copyrighted |
| Shop window displays | Window dressing is a protected creative work in many jurisdictions |
| Interpretive/information signs where the text is the subject | The sign text is a protected work |

**Freedom of panorama is country-specific and matters.** Germany and Croatia both allow
photographs of works *permanently* installed in *public* spaces — so an outdoor mural, a
building facade, or a monument on a square is fine. Neither extends FOP to museum
interiors. Check the FOP rule for the actual country of each cluster before clearing
architecture or artwork; do not assume the rules travel with you.

Where a room contains a mix, judge by what dominates the frame. Bare hardware or
utilitarian objects are usually fine; the same room shot from an angle that fills the
frame with box art is not.

### Identifiable people — do not over-apply

Recognisable faces are *not* an automatic exclusion. In Germany, §23(1) KUG permits
publishing images of assemblies and public events, and Commons' own guidance accepts
crowd shots at public events without consent. Photos at a festival, concert, market or
demonstration are normally fine.

Reserve the people concern for: private settings, children as the clear subject, anything
embarrassing or defamatory, and images where one identifiable stranger is the subject
rather than part of a scene.

If you drop a public-event photo, be honest about which reason you are using. "Faces in
frame" and "spectators clutter the foreground and the subject is small" are different
verdicts — the first is a rights claim that usually will not survive scrutiny, the second
is an ordinary composition call. Say the one you mean.

### Tier classification (assigned during review, not after)

- **Tier 1 — Strong upload candidate**: Sharp, well-composed, identifiable subject,
  encyclopedic value.
- **Tier 2 — Acceptable / situational**: Minor issues (slight overexposure, partially
  cut element, one of several similar shots). Mark near-duplicate groups here.
- **Tier 3 — Skip**: Bland, redundant, technically flawed, or no encyclopedic value.

Present results as a table per tier: filename, subject description, notes on issues.
For Tier 2 near-duplicate groups, indicate which images belong to the same group.

If any location clusters from step 3 were unresolved, ask now — you can see the actual
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

**Step B — wipe the XMP and IPTC blocks wholesale:**

```bash
exiftool -overwrite_original -XMP:all= -IPTC:all= \
  -UserComment= -ImageDescription= upload/*.JPG
```

Clearing named fields one by one is **not sufficient**. Phone apps write duplicate
`dc:description/rdf:Alt/rdf:li` entries, and `-XMP-dc:Description=` removes only the
first; exiftool warns `Duplicate XMP property` and leaves the rest in place. Dropping the
whole XMP and IPTC blocks is the only reliable fix. Nothing needed downstream lives there
— date and GPS are in EXIF and survive.

**Step C — strip GPS from private locations only** (per the decision made in step 3):

```bash
exiftool -overwrite_original -gps:all= "upload/Photo at a home address.JPG"
```

**Step D — verify, do not assume:**

```bash
# must print nothing
exiftool -a -G1 -s upload/*.JPG | grep -iE "MOOD|presetId|STOCK"
# confirm the intended files, and only those, lost their coordinates
exiftool -q -if 'not $gpslatitude' -p '$FileName' upload/*.JPG
```

Run all of this before generating descriptions so there's no confusion about what
"description" means. This is mandatory, not optional — files uploaded with app metadata
get flagged on Commons.

### Filename conventions

- Descriptive English name (not IMG_XXXX)
- Include location (already known from step 3)
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

```python
# One script, all subjects at once. Run this BEFORE writing descriptions.
import urllib.request, urllib.parse, json, time

def search(q, n=6):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "list": "search", "srsearch": q,
         "srnamespace": 14, "srlimit": n, "format": "json"})
    req = urllib.request.Request(url, headers={
        "User-Agent": "uploading-to-commons-pipeline/1.0 (User:Mike is Michi)"})
    return [r["title"] for r in json.load(urllib.request.urlopen(req))["query"]["search"]]

for q in ["Basilique Notre-Dame de la Garde", "Vieux-Port Marseille",
          "Umjetnički paviljon Zagreb", "Jubiläumssäule Stuttgart"]:
    for attempt in range(3):
        try:
            hits = search(q); break
        except Exception as e:
            hits = [f"ERR {e}"]; time.sleep(6)
    print(f"=== {q}"); [print("  ", h) for h in hits]
    time.sleep(2.0)          # see rate limit below
```

**Build the URL with `urlencode`, not string interpolation.** Piping a raw `curl` URL
containing `ü`, `ö`, `č` or `ß` returns a non-JSON error page and the parse dies with
`Expecting value: line 1 column 1`. Nearly every European place name hits this.

**Rate limit**: the search endpoint returns HTTP 429 under a fast loop. Sleep ~2s between
queries and retry on failure. Exact-title lookups (`action=query&titles=`) are cheap by
comparison — they accept up to 50 titles per request, so batch the final validation pass
instead of looping.

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

### Final validation pass

After the descriptions file is written, batch-check every category it references and
confirm the file list matches the directory. Both catch real mistakes cheaply:

```python
# 1. does every block have a file, and every file a block?
# 2. does every [[Category:...]] exist, and is it a redirect?
url = ".../w/api.php?action=query&titles=<up to 50 joined by |>&redirects=1&format=json"
# negative pageid  -> category does not exist
# "redirects" key  -> you cited a redirect; use the target instead
```

Normalise Unicode with `unicodedata.normalize('NFC', ...)` before comparing macOS
filenames against strings from the descriptions file, or names containing umlauts and
háčeks will appear to mismatch when they are identical.

### Description generation

Generate `wikimedia_descriptions.txt` following the exact format in
`references/information-template.txt`. One `{{Information}}` block per image, bilingual
descriptions (English + German), `{{Taken on}}` date template with location, and
categories drawn from the verified lookup list above.

**Do not guess species, summits, or building names.** A wrong binomial on Commons
propagates into Wikipedia articles and other reusers. When you cannot identify something
with confidence, say so in the description and categorise at the level you are sure of:

| Confidence | Do this |
| --- | --- |
| Species certain | `[[Category:Cetonia aurata]]` |
| Genus certain only | `[[Category:Pieris (Pieridae)]]` |
| Family/subfamily only | `[[Category:Cetoniinae]]` |
| Not identifiable | `[[Category:Unidentified moths]]` + "The species is not identified." |

The same applies to a mountain across a valley or an unlabelled building. Describe what
is visible, name the valley or street from step 3, and tell the user what you left open
so they can fill it in — they were there. When they do supply a name, update the
filename, both descriptions and the categories together, and re-run the validation pass.

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
Uploading is public, irreversible in practice, and attaches the user's real name to every
file. Treat the user handing over a bot password *in response to a request for it* as
authorization; treat silence, or a message about something else, as not.

Also check the target names are free before uploading — a collision wastes the upload and
forces a rename afterwards:

```python
# batch up to 50 "File:<name>" titles; positive pageid means the name is taken
url = ".../w/api.php?action=query&titles=File:Name+one|File:Name+two&format=json"
```

And confirm the credentials actually work before starting a long batch:

```bash
.venv/bin/python -c "
import pywikibot
s = pywikibot.Site('commons','commons'); s.login()
print(s.user(), 'upload' in s.userinfo.get('rights', []))"
```

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
('Mike is Michi', BotPassword('BOT_NAME', 'PASTE_BOT_PASSWORD_HERE'))
```

`BOT_NAME` is the bot password's own name, not a fixed string — it is the part after the
`@` in the login the user was given. For `Mike is Michi@claude-rw`, `BOT_NAME` is
`claude-rw`. Getting this wrong produces a login failure, not a useful error.

For the bot password, check the memory file `reference_commons_credentials.md`. Never
hardcode credentials into skill files or commit them.

`chmod 600 user-password.py` after writing it. Then tell the user plainly that the file
holds a live credential in plaintext inside the folder that also holds their photos, and
that they should delete it or move it out if that folder is ever synced or shared. If the
user has run `/export` in the session, the transcript will contain the password too —
say so, and say where the file landed.

### Running the upload

```bash
cd upload/
.venv/bin/python upload_to_commons.py --delay 5 --no-verify > upload_run.log 2>&1
```

Pass `--no-verify` and verify separately in step 10 — the built-in check runs ~10s after
the last upload and reports every file as missing (see below). Run the batch in the
background and poll the log: 34 files at `--delay 5` took about 7 minutes, which will
otherwise hit a foreground command timeout.

The upload script is located at
`~/.claude/skills/uploading-to-commons/scripts/upload_to_commons.py`. Copy it to the
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

**Propagation delay**: Commons takes 30–60 seconds to index newly uploaded files. The
script's built-in verification waits only ~10s, so it reports **every file** as
`NOT FOUND on Commons` even when all of them uploaded cleanly. This is the expected
outcome, not a symptom — it fired on a 34-file batch and again on a single-file upload in
the same session. Do not report it to the user as a failure.

The authoritative signals are `upload_log.txt` (one `OK` row with a URL per file) and the
script's own `Uploaded: N, Failed: 0` summary. Then wait 40s and confirm independently,
checking categories at the same time so step 10 is a single pass:

```python
url = ("https://commons.wikimedia.org/w/api.php?action=query"
       "&titles=" + "|".join("File:" + f for f in batch) +      # up to 50 per call
       "&prop=categories&cllimit=max&format=json")
# negative pageid -> genuinely missing
# count categories excluding the auto-added CC-BY / SDC / "Self-published work" ones
```

Only investigate files still missing after 60+ seconds.

Review `upload_log.txt` and present a summary: total uploaded, skipped, failed, and
links to the Commons file pages.

## Full Pipeline Summary

The complete end-to-end flow when the user invokes this skill:

```
1. Resolution check          — drop sub-2MP
2. EXIF extraction            — one -n pass incl. GPS; flag technical issues
   2b. Front-camera filter    — flag likely selfies, skip in visual review
3. Gather location context    — cluster + Nominatim; public/private split; before review
4. Format duplicate pruning   — keep best version per base name
5. Visual review + tiers      — contact sheets; copyright + people screening
6. Resolve near-duplicates    — pick best per group
7. Copy+rename+describe       — upload/ folder with descriptions
   7a. Strip metadata         — xattr + XMP:all/IPTC:all + selective GPS + verify
   7b. Zoom-18 geocode        — per-image, for the final set only
   7c. Category discovery     — search first, then batch-validate exact titles
   7d. Generate descriptions  — wikimedia_descriptions.txt (3+ categories each)
8. Dry-run preview            — name-collision + login check; user confirms
9. Upload to Commons          — venv + pywikibot + bot password (config in upload/)
10. Post-upload verification  — independent API check after 40s + log review
```

Steps 1-7 produce the upload-ready set. Steps 8-10 handle the actual upload. The user
must confirm between step 8 and step 9.

### Keep a decision record on disk

Alongside `technical_scan_results.md`, write `visual_review.md` (tier tables, per-file
verdicts) and `upload_plan.md` (final set, source→upload name mapping, dedup choices with
reasons, exclusions with reasons, verified categories). These survive context resets, and
when the user later asks "why did you exclude X?" the answer is recorded rather than
reconstructed. Record the *actual* reason for each exclusion, not a tidier-sounding one.

## Edge Cases

- **Phone photos vs camera photos**: Determined by EXIF camera model in step 2. Phone
  sensors get stricter ISO thresholds (1250 vs 3200).
- **Panoramas / stitched images**: Unusual aspect ratios are fine. Judge by total
  megapixels, not dimensions.
- **Screenshots or digital art mixed in**: Flag and exclude — Commons requires different
  licensing for these.
- **Images with text overlays / watermarks**: Exclude unconditionally.
- **Missing EXIF GPS**: Genuinely absent GPS is not an error — location then comes from
  the user in step 3. But verify it is really absent first (step 2); a bad exiftool query
  looks identical to a stripped batch and sends the session down the wrong path.
- **User corrects an identification**: Take it — they were there. Update the filename,
  both language descriptions and the categories together, re-run the category validation,
  and if the file is already uploaded, use `--overwrite` or rename on Commons rather than
  leaving a half-corrected page.
- **Two near-identical categories both exist** (e.g. `Hurdy-gurdy players`,
  `Hurdy gurdy players`, `Hurdy-Gurdy players` are all real, none redirects): pick the
  one with the most members and mention the duplication to the user rather than silently
  picking one.
- **Large batches (250+ images)**: Save the step 2 report to disk and suggest a context
  reset before step 5. Reference the saved report in the new context.
- **Re-uploading after metadata fix**: Use `--overwrite` flag. The script will re-upload
  even if the file already exists on Commons.
- **Upload failures**: Check `upload_log.txt` for specifics. Common causes: network
  timeout, file too large, bot password expired. Re-run with `--file "failed_name*"` to
  retry specific files.

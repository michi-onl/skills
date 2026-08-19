---
name: searching-nextcloud
description: "Find, list, or read files in Nextcloud by name, path, date, or content. Read-only. Also \"my cloud\"."
---

# Searching Nextcloud

## Overview

Read-only search and retrieval over the user's Nextcloud at `<NEXTCLOUD_HOST>`, via the WebDAV API using the dedicated account `claude-ro`.

**Target**: Nextcloud at `<NEXTCLOUD_HOST>` (host in memory — substitute it into every URL below).

**Core safety rule — non-negotiable:** Only ever issue read methods: `GET`, `PROPFIND`, `REPORT`. NEVER issue `PUT`, `DELETE`, `MOVE`, `COPY`, `MKCOL`, `PROPPATCH`, or `LOCK`.

This rule is load-bearing. The `claude-ro` credential is NOT guaranteed to be permission-restricted (received shares may carry delete/rename/move rights). Method discipline is the safety boundary you actually control. Do not rely on the server to reject a write — just never send one.

## Credentials — ask every time

The app password is NOT stored in this skill, on disk, or in git. The home shell does not persist env vars between commands, so each session uses a short-lived netrc file:

1. **Ask the user for the `claude-ro` app password.** Every session. No exceptions.
2. Write a temporary, owner-only netrc file:
   ```bash
   umask 077
   NETRC="$(mktemp "${TMPDIR:-/tmp}/nc-claude.XXXXXX")"
   printf 'machine <NEXTCLOUD_HOST> login claude-ro password %s\n' 'PASTE_PASSWORD_HERE' > "$NETRC"
   ```
   Using `--netrc-file` (not `-u`) keeps the password out of `ps` and shell history.
3. Pass `--netrc-file "$NETRC"` on every curl call.
4. **Delete it when done:** `rm -f "$NETRC"`. Because it's gone each session, the user must supply the password again next time — by design.

## WebDAV base

```
https://<NEXTCLOUD_HOST>/remote.php/dav/files/claude-ro/
```

## Preflight: confirm what's actually read-only

Before searching, you may verify share permissions (read-only PROPFIND, no side effects). Letters: `G`=read, `D`=delete, `N`=rename, `V`=move, `C`=create-file, `K`=mkdir, `W`=write, `S`=shared, `R`=reshareable, `M`=mounted.

```bash
BODY='<?xml version="1.0"?><d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns"><d:prop><oc:permissions/><d:resourcetype/></d:prop></d:propfind>'
curl -s --netrc-file "$NETRC" -X PROPFIND -H 'Depth: 1' -H 'Content-Type: application/xml' \
  --data "$BODY" "https://<NEXTCLOUD_HOST>/remote.php/dav/files/claude-ro/" -o /tmp/nc_perms.xml
python3 - <<'PY'
import xml.etree.ElementTree as ET
ns={'d':'DAV:','oc':'http://owncloud.org/ns'}
for r in ET.parse('/tmp/nc_perms.xml').getroot().findall('d:response',ns):
    href=r.find('d:href',ns).text
    p=r.find('.//oc:permissions',ns); p=p.text if p is not None and p.text else '-'
    rw='WRITE/DELETE' if any(c in p for c in 'CKWDNV') else 'read-only'
    print(f"{p:<10} {rw:<12} {href}")
PY
rm -f /tmp/nc_perms.xml
```

**Interpreting results:** a *received* share's ROOT may show `D` (and `N`/`V`) even when it's read-only — that's the recipient's right to unmount/rename/move the share itself, which does NOT delete your source files. The authoritative content check is on the CHILDREN inside a share: they should be `SG` (read) only. Genuine write/delete on your data shows as `W`/`C`/`K`/`D` on **child items**. If children show those, warn the user the share isn't read-only. Regardless of the result, still only ever send read methods.

## Read operations

**List one level:**
```bash
curl -s --netrc-file "$NETRC" -X PROPFIND -H 'Depth: 1' \
  "https://<NEXTCLOUD_HOST>/remote.php/dav/files/claude-ro/Dokumente/"
```
Parse the XML for `<d:href>` (paths), `<d:getlastmodified>`, `<d:getcontentlength>`, `<d:getcontenttype>`.

**Read a text file:**
```bash
curl -s --netrc-file "$NETRC" \
  "https://<NEXTCLOUD_HOST>/remote.php/dav/files/claude-ro/Dokumente/notes.md"
```

For recursion use `-H 'Depth: infinity'` on a **subfolder** — never the whole instance at once.

## Search strategy

1. **Filename / path / date / size:** PROPFIND the target folders, filter hrefs/props. No download.
2. **Content (txt, md, code, csv):** GET candidates, grep/parse locally, reason over matches.
3. **PDF / docx:** GET to a temp file → `pdftotext` / `unzip` (docx is zipped XML) → search → delete temp.
4. **Images / audio:** filename + metadata only; no content understanding unless asked to OCR.

Keep scope tight — point at specific folders, not `Depth: infinity` on root. Every content match is a download.

## Optional: server-side full-text search

If a Full Text Search platform backend (e.g. Elasticsearch) is installed, query the unified search API instead of downloading:
```bash
# filename search (always available):
curl -s --netrc-file "$NETRC" -H 'OCS-APIRequest: true' \
  "https://<NEXTCLOUD_HOST>/ocs/v2.php/search/providers/files/search?term=QUERY&format=json"
# content search (only if a search platform is installed):
curl -s --netrc-file "$NETRC" -H 'OCS-APIRequest: true' \
  "https://<NEXTCLOUD_HOST>/ocs/v2.php/search/providers/files_fulltextsearch/search?term=QUERY&format=json"
```
Without a search-platform backend, the core FTS app does not index content — fall back to download + grep.

## Red flags — STOP

- About to send `PUT` / `DELETE` / `MOVE` / `COPY` / `MKCOL` / `PROPPATCH` / `LOCK` → don't. Read-only skill.
- "I'll just quickly rename/clean up/move that file" → not this skill's job. Never.
- About to put the password in a curl arg, a file in the repo, or the skill itself → don't. Temp netrc only, deleted after.
- About to `Depth: infinity` the whole instance for a content search → scope to a folder first.

## Common mistakes

| Mistake | Fix |
|---|---|
| Password in the curl command line (`-u`) | Use `--netrc-file`; keeps it out of `ps`/history |
| Leaving the netrc file behind | `rm -f "$NETRC"` when done |
| Trusting the account to be read-only | Don't — enforce read-only by only sending read methods |
| Recursive listing of the whole instance | Scope to folders |
| Assuming content search works | Confirm a search-platform backend; else download + grep |

#!/usr/bin/env python3
"""
QA checks for localization files.

Most checks (placeholder parity, tag parity, whitespace, untranslated, length
ratio) are LANGUAGE-AGNOSTIC and run on any source/target pair. The register
check (du/Sie) is German-specific and only runs when --register is du or sie.

Usage:
    python scripts/qa_check.py <source_file> <target_file> [--format FMT] [--register du|sie|none]

Formats (auto-detected from the target extension if --format is omitted):
    json        flat or nested JSON (i18next, react-intl, ...)
    messages    WebExtension chrome.i18n messages.json ({key: {message, ...}})
    ftl         Fluent
    properties  Java .properties
    strings     iOS / macOS .strings  ("key" = "value";)
    xcstrings   Xcode String Catalog (.xcstrings, JSON)
    androidxml  Android strings.xml (incl. <plurals>)
    po          gettext .po / .pot

Exit code 0 = clean, 1 = issues found.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Placeholder / tag patterns
# ---------------------------------------------------------------------------
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{[^}]+\}\}"),        # {{var}}
    re.compile(r"\{[^}]+\}"),            # {name}, {0}, {count, plural, ...}
    re.compile(r"%[0-9]+\$?[sdfl@cve]"), # %1$s, %0 handled below too
    re.compile(r"%[0-9]+"),              # %0, %1 (Stats-style positional)
    re.compile(r"%[sdflc@cve]"),         # %s, %d, %@
    re.compile(r"%\([^)]+\)[sdfl]"),     # %(name)s
    re.compile(r"\$[A-Z_][A-Z0-9_]*"),   # $NUMBER, $AUTHOR (Zola-style)
    re.compile(r"\$\{[^}]+\}"),          # ${var}
]

TAG_PATTERN = re.compile(r"<[^>]+>")

# German formal-register pronoun (capitalised Sie used as address).
SIE_PRONOUN = re.compile(r"\bSie\b")
SIE_POSSESSIVE = re.compile(r"\bIhr(e|en|em|es|er)?\b")
# "Du" capitalised mid-sentence (informal but inconsistent style).
DU_CAPITALIZED = re.compile(r"(?<!^)(?<![.!?]\s)(?<![.!?]\s\s)\bDu\b")


def extract_placeholders(text: str) -> list[str]:
    found = []
    remaining = text
    for pat in PLACEHOLDER_PATTERNS:
        for m in pat.findall(remaining):
            found.append(m)
    return sorted(found)


def extract_tags(text: str) -> list[str]:
    return sorted(TAG_PATTERN.findall(text))


# ---------------------------------------------------------------------------
# Checks (language-agnostic unless noted)
# ---------------------------------------------------------------------------
def check_placeholder_parity(source, target, key):
    src, tgt = extract_placeholders(source), extract_placeholders(target)
    if src != tgt:
        return [f"[Placeholder] {key}: source={src} target={tgt}"]
    return []


def check_tag_parity(source, target, key):
    src, tgt = extract_tags(source), extract_tags(target)
    if src != tgt:
        return [f"[Tag] {key}: source={src} target={tgt}"]
    return []


def check_register(target, key, mode):
    """German-specific. mode in {'du','sie'}."""
    issues = []
    if mode == "du":
        if SIE_PRONOUN.search(target) or SIE_POSSESSIVE.search(target):
            issues.append(f"[Register] {key}: formal Sie/Ihr in du-mode — \"{target[:80]}\"")
        if DU_CAPITALIZED.search(target):
            issues.append(f"[Register] {key}: capitalised 'Du' mid-sentence (use 'du')")
    elif mode == "sie":
        # Lowercase informal "du/dein" leaking into Sie-mode.
        if re.search(r"\b(du|dich|dir|dein(e|en|em|es|er)?)\b", target):
            issues.append(f"[Register] {key}: informal du/dein in Sie-mode — \"{target[:80]}\"")
    return issues


def check_length_ratio(source, target, key, threshold=1.5):
    s, t = len(source), len(target)
    if 0 < s <= 30 and t > s * threshold:
        return [f"[Length] {key}: {t}/{s} chars = {t/s:.0%} (>{threshold:.0%}) — \"{target}\""]
    return []


def check_whitespace(target, key):
    issues = []
    if "  " in target:
        issues.append(f"[Whitespace] {key}: double space")
    if target != target.rstrip() or target != target.lstrip():
        issues.append(f"[Whitespace] {key}: leading/trailing whitespace")
    if target == "":
        issues.append(f"[Empty] {key}: empty string")
    return issues


# ---------------------------------------------------------------------------
# Loaders -> {key: value}
# ---------------------------------------------------------------------------
def load_json_strings(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    def flatten(obj, prefix=""):
        out = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                nk = f"{prefix}.{k}" if prefix else k
                if isinstance(v, str):
                    out[nk] = v
                elif isinstance(v, dict):
                    out.update(flatten(v, nk))
                elif isinstance(v, list):
                    for i, item in enumerate(v):
                        if isinstance(item, str):
                            out[f"{nk}[{i}]"] = item
        return out

    return flatten(data)


def load_messages_strings(path):
    """WebExtension chrome.i18n messages.json: translate `message`, ignore the
    rest. {key: {"message": ..., "description": ..., "placeholders": ...}}"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for k, v in data.items():
        if isinstance(v, dict) and "message" in v:
            out[k] = v["message"]
    return out


def load_ftl_strings(path):
    strings, cur, lines = {}, None, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.rstrip("\n")
            if s.startswith("#") or s == "":
                if cur and lines:
                    strings[cur] = " ".join(lines).strip()
                    cur, lines = None, []
                continue
            attr = re.match(r"^\s+\.(\w+)\s*=\s*(.*)", s)
            if attr and cur:
                if lines:
                    strings[cur] = " ".join(lines).strip()
                    lines = []
                base = cur.split(".")[0]
                cur = f"{base}.{attr.group(1)}"
                if attr.group(2).strip():
                    lines = [attr.group(2).strip()]
                continue
            msg = re.match(r"^([a-zA-Z][\w-]*)\s*=\s*(.*)", s)
            if msg:
                if cur and lines:
                    strings[cur] = " ".join(lines).strip()
                cur = msg.group(1)
                lines = [msg.group(2).strip()] if msg.group(2).strip() else []
                continue
            if cur and s.startswith("    "):
                lines.append(s.strip())
    if cur and lines:
        strings[cur] = " ".join(lines).strip()
    return strings


def load_properties_strings(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in "#!":
                continue
            sep = min([i for i in (line.find("="), line.find(":")) if i != -1], default=-1)
            if sep != -1:
                out[line[:sep].strip()] = line[sep + 1:].strip()
    return out


def load_dotstrings(path):
    """iOS/macOS .strings:  "key" = "value";  (also // and /* */ comments)."""
    text = Path(path).read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)  # block comments
    out = {}
    pat = re.compile(r'"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;')
    for m in pat.finditer(text):
        key = m.group(1)
        val = m.group(2)
        out[key] = val
    return out


def load_xcstrings(path, want_lang="de"):
    """Xcode String Catalog. Returns target values for want_lang; source uses
    the file's sourceLanguage. Pass the SAME file as source and target — this
    loader is called twice with different langs internally via wrappers below."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    src_lang = data.get("sourceLanguage", "en")
    strings = data.get("strings", {})
    out_src, out_tgt = {}, {}
    for key, entry in strings.items():
        locs = entry.get("localizations", {})
        # source
        sv = locs.get(src_lang, {}).get("stringUnit", {}).get("value")
        out_src[key] = sv if sv is not None else key
        # target
        tu = locs.get(want_lang, {}).get("stringUnit", {})
        if "value" in tu:
            out_tgt[key] = tu["value"]
    return out_src, out_tgt


def load_androidxml(path):
    """Android strings.xml: <string> and <plurals><item>."""
    out = {}
    tree = ET.parse(path)
    root = tree.getroot()
    for el in root:
        if el.tag == "string":
            name = el.get("name")
            if el.get("translatable") == "false":
                continue
            out[name] = (el.text or "").strip()
        elif el.tag == "plurals":
            name = el.get("name")
            for item in el.findall("item"):
                q = item.get("quantity")
                out[f"{name}[{q}]"] = (item.text or "").strip()
    return out


def load_po(path):
    """gettext .po/.pot is bilingual in one file. Returns (source, target):
    source maps key -> msgid (msgid_plural for the plural slot), target maps
    key -> msgstr. Keyed by msgctxt|msgid."""
    src_out, tgt_out = {}, {}
    ctx = msgid = msgid_plural = None
    plurals = {}
    cur_field = None
    buf = ""

    def flush():
        nonlocal ctx, msgid, msgid_plural, plurals, buf, cur_field
        if msgid is not None and msgid != "":
            key = f"{ctx}|{msgid}" if ctx else msgid
            if plurals:
                for n, v in plurals.items():
                    src_out[f"{key}[{n}]"] = msgid if n == 0 else (msgid_plural or msgid)
                    tgt_out[f"{key}[{n}]"] = v
            else:
                src_out[key] = msgid
                tgt_out[key] = buf
        ctx = msgid = msgid_plural = None
        plurals = {}
        buf = ""
        cur_field = None

    def unq(s):
        s = s.strip()
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        return s

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.startswith("#") or line.strip() == "":
                if line.strip() == "":
                    flush()
                continue
            if line.startswith("msgctxt"):
                flush()
                ctx = unq(line[len("msgctxt"):])
                cur_field = "ctx"
            elif line.startswith("msgid_plural"):
                msgid_plural = unq(line[len("msgid_plural"):])
                cur_field = "id_plural"
            elif line.startswith("msgid"):
                if cur_field not in ("ctx", None):
                    flush()
                msgid = unq(line[len("msgid"):])
                cur_field = "id"
            elif line.startswith("msgstr["):
                m = re.match(r'msgstr\[(\d+)\]\s*(.*)', line)
                if m:
                    n = int(m.group(1))
                    plurals[n] = unq(m.group(2))
                    cur_field = f"str{n}"
            elif line.startswith("msgstr"):
                buf = unq(line[len("msgstr"):])
                cur_field = "str"
            elif line.startswith('"'):
                val = unq(line)
                if cur_field == "id":
                    msgid += val
                elif cur_field == "id_plural":
                    msgid_plural = (msgid_plural or "") + val
                elif cur_field == "str":
                    buf += val
                elif cur_field and cur_field.startswith("str") and cur_field[3:].isdigit():
                    plurals[int(cur_field[3:])] += val
    flush()
    return src_out, tgt_out


SINGLE_FILE_LOADERS = {
    "json": load_json_strings,
    "messages": load_messages_strings,
    "ftl": load_ftl_strings,
    "properties": load_properties_strings,
    "strings": load_dotstrings,
    "androidxml": load_androidxml,
}

# Bilingual formats: one file holds both source and target.
BILINGUAL_LOADERS = {"xcstrings", "po"}


def detect_format(path):
    name = Path(path).name.lower()
    ext = Path(path).suffix.lower()
    if name == "messages.json":
        return "messages"
    mapping = {
        ".json": "json", ".ftl": "ftl", ".properties": "properties",
        ".strings": "strings", ".xcstrings": "xcstrings",
        ".xml": "androidxml", ".po": "po", ".pot": "po",
    }
    return mapping.get(ext, "json")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def run_qa(source_path, target_path, fmt=None, register="du"):
    if fmt is None:
        fmt = detect_format(target_path)

    if fmt in BILINGUAL_LOADERS:
        # Single bilingual file: pass the same path; loader splits src/target.
        try:
            if fmt == "xcstrings":
                source_strings, target_strings = load_xcstrings(target_path, want_lang="de")
            else:  # po
                source_strings, target_strings = load_po(target_path)
        except Exception as e:
            return [f"Failed to parse {fmt} file: {e}"]
    else:
        loader = SINGLE_FILE_LOADERS.get(fmt)
        if not loader:
            return [f"Unsupported format: {fmt}. Supported: "
                    f"{sorted(list(SINGLE_FILE_LOADERS) + list(BILINGUAL_LOADERS))}"]
        try:
            source_strings = loader(source_path)
        except Exception as e:
            return [f"Failed to parse source file: {e}"]
        try:
            target_strings = loader(target_path)
        except Exception as e:
            return [f"Failed to parse target file: {e}"]

    issues = []
    src_keys, tgt_keys = set(source_strings), set(target_strings)
    missing = src_keys - tgt_keys
    extra = tgt_keys - src_keys
    if missing:
        issues.append(f"[Keys] Missing in target ({len(missing)}): {sorted(missing)[:20]}")
    if extra:
        issues.append(f"[Keys] Extra in target ({len(extra)}): {sorted(extra)[:20]}")

    for key in sorted(src_keys & tgt_keys):
        src, tgt = source_strings[key], target_strings[key]
        issues += check_placeholder_parity(src, tgt, key)
        issues += check_tag_parity(src, tgt, key)
        if register in ("du", "sie"):
            issues += check_register(tgt, key, register)
        issues += check_length_ratio(src, tgt, key)
        issues += check_whitespace(tgt, key)
        if src == tgt and len(src) > 3 and not re.fullmatch(r"[\W\d_]+", src):
            issues.append(f"[Untranslated] {key}: identical to source — \"{src[:60]}\"")

    return issues


def main():
    p = argparse.ArgumentParser(description="QA checks for localization files")
    p.add_argument("source", help="Source file (for .xcstrings, pass the same file as target)")
    p.add_argument("target", help="Target file")
    p.add_argument("--format",
                   choices=sorted(list(SINGLE_FILE_LOADERS) + list(BILINGUAL_LOADERS)),
                   default=None, help="Auto-detected from extension if omitted")
    p.add_argument("--register", choices=["du", "sie", "none"], default="du",
                   help="Expected German register, or 'none' to skip the register check "
                        "(use 'none' for non-German locales)")
    a = p.parse_args()
    issues = run_qa(a.source, a.target, fmt=a.format, register=a.register)
    if issues:
        print(f"Found {len(issues)} issue(s):\n")
        for i in issues:
            print(f"  {i}")
        sys.exit(1)
    print("All QA checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()

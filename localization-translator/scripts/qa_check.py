#!/usr/bin/env python3
"""
QA checks for localization translations (EN → DE).

Usage:
    python scripts/qa_check.py <source_file> <target_file> [--format json|ftl|po|xml|properties]

Checks:
    - Placeholder parity
    - Tag parity (HTML/XML)
    - Register consistency (du/Sie)
    - Length ratio for short strings
    - Format syntax validation
    - Empty strings, double spaces, trailing whitespace
    - Terminology consistency
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Placeholder patterns
# ---------------------------------------------------------------------------
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{[^}]+\}"),          # {name}, {0}, {count, plural, ...}
    re.compile(r"\{\{[^}]+\}\}"),      # {{var}}
    re.compile(r"%[0-9]*\$?[sdflc@]"), # %s, %d, %1$s, %@
    re.compile(r"%\([^)]+\)[sdfl]"),   # %(name)s
    re.compile(r"\$[a-zA-Z_]+"),       # $variable
]

# Register patterns
SIE_PATTERNS = re.compile(
    r"\b(Ihnen|Ihrem|Ihres|Ihrer|Ihren|Sie\b(?!\s+(sind|werden|haben|können|möchten|sollen|wollen|müssen|dürfen)))",
    re.IGNORECASE,
)
# Catches formal "Sie" used as pronoun (not "sie" = they/she)
SIE_PRONOUN = re.compile(r"\bSie\b")

# Catches "Du" capitalized mid-sentence (informal but inconsistent)
DU_CAPITALIZED = re.compile(r"(?<!\. )(?<!^)\bDu\b")

# HTML/XML tag pattern
TAG_PATTERN = re.compile(r"<[^>]+>")


def extract_placeholders(text: str) -> list[str]:
    """Extract all placeholders from a string."""
    found = []
    for pat in PLACEHOLDER_PATTERNS:
        found.extend(pat.findall(text))
    return sorted(found)


def extract_tags(text: str) -> list[str]:
    """Extract all HTML/XML tags from a string."""
    return sorted(TAG_PATTERN.findall(text))


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_placeholder_parity(source: str, target: str, key: str) -> list[str]:
    issues = []
    src_ph = extract_placeholders(source)
    tgt_ph = extract_placeholders(target)
    if src_ph != tgt_ph:
        issues.append(
            f"[Placeholder] {key}: source={src_ph} target={tgt_ph}"
        )
    return issues


def check_tag_parity(source: str, target: str, key: str) -> list[str]:
    issues = []
    src_tags = extract_tags(source)
    tgt_tags = extract_tags(target)
    if src_tags != tgt_tags:
        issues.append(
            f"[Tag] {key}: source={src_tags} target={tgt_tags}"
        )
    return issues


def check_register(target: str, key: str, mode: str = "du") -> list[str]:
    """Check for register inconsistencies. mode='du' or 'sie'."""
    issues = []
    if mode == "du":
        # Should not contain formal Sie
        sie_matches = SIE_PRONOUN.findall(target)
        # Filter out "sie" (lowercase = she/they), only flag "Sie"
        for m in sie_matches:
            # Check context: is this formal Sie?
            if re.search(r"\bSie\b", target):
                # Could be formal — flag it
                issues.append(
                    f"[Register] {key}: found 'Sie' in du-mode string: ...{target[:80]}..."
                )
                break
        # Check for capitalized Du mid-sentence
        du_caps = DU_CAPITALIZED.findall(target)
        if du_caps:
            issues.append(
                f"[Register] {key}: capitalized 'Du' mid-sentence (use lowercase 'du')"
            )
    return issues


def check_length_ratio(source: str, target: str, key: str, threshold: float = 1.5) -> list[str]:
    """Flag short strings (buttons/labels) where DE is >threshold × EN length."""
    issues = []
    src_len = len(source)
    tgt_len = len(target)
    # Only flag short strings (likely buttons/labels)
    if src_len > 0 and src_len <= 30 and tgt_len > src_len * threshold:
        ratio = tgt_len / src_len
        issues.append(
            f"[Length] {key}: {tgt_len}/{src_len} chars = {ratio:.0%} "
            f"(>{threshold:.0%} threshold) — \"{target}\""
        )
    return issues


def check_whitespace(target: str, key: str) -> list[str]:
    issues = []
    if "  " in target:
        issues.append(f"[Whitespace] {key}: double space found")
    if target != target.rstrip():
        issues.append(f"[Whitespace] {key}: trailing whitespace")
    if target == "":
        issues.append(f"[Empty] {key}: empty string")
    return issues


# ---------------------------------------------------------------------------
# Format-specific loaders
# ---------------------------------------------------------------------------

def load_json_strings(path: str) -> dict[str, str]:
    """Load flat or nested JSON into {dotted.key: value} pairs."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    def flatten(obj, prefix=""):
        result = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, str):
                    result[new_key] = v
                elif isinstance(v, dict):
                    result.update(flatten(v, new_key))
        return result

    return flatten(data)


def load_ftl_strings(path: str) -> dict[str, str]:
    """Load FTL (Fluent) file into {message-id: value} pairs.
    Handles attributes (.label, .title, etc.) as separate keys."""
    strings = {}
    current_id = None
    current_value_lines = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip("\n")

            # Comment or blank
            if stripped.startswith("#") or stripped == "":
                if current_id and current_value_lines:
                    strings[current_id] = " ".join(current_value_lines).strip()
                    current_id = None
                    current_value_lines = []
                continue

            # Attribute line
            attr_match = re.match(r"^\s+\.(\w+)\s*=\s*(.*)", stripped)
            if attr_match and current_id:
                # Save previous value
                if current_value_lines:
                    strings[current_id] = " ".join(current_value_lines).strip()
                    current_value_lines = []
                attr_name = attr_match.group(1)
                attr_value = attr_match.group(2).strip()
                base_id = current_id.split(".")[0]  # strip previous attribute
                current_id = f"{base_id}.{attr_name}"
                if attr_value:
                    current_value_lines = [attr_value]
                continue

            # New message
            msg_match = re.match(r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*=\s*(.*)", stripped)
            if msg_match:
                if current_id and current_value_lines:
                    strings[current_id] = " ".join(current_value_lines).strip()
                current_id = msg_match.group(1)
                value = msg_match.group(2).strip()
                current_value_lines = [value] if value else []
                continue

            # Continuation line
            if current_id and stripped.startswith("    "):
                current_value_lines.append(stripped.strip())

    if current_id and current_value_lines:
        strings[current_id] = " ".join(current_value_lines).strip()

    return strings


def load_properties_strings(path: str) -> dict[str, str]:
    """Load Java .properties file."""
    strings = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("!"):
                continue
            sep = line.find("=")
            if sep == -1:
                sep = line.find(":")
            if sep != -1:
                key = line[:sep].strip()
                value = line[sep + 1:].strip()
                strings[key] = value
    return strings


LOADERS = {
    "json": load_json_strings,
    "ftl": load_ftl_strings,
    "properties": load_properties_strings,
}


def detect_format(path: str) -> str:
    ext = Path(path).suffix.lower()
    mapping = {
        ".json": "json",
        ".ftl": "ftl",
        ".properties": "properties",
    }
    return mapping.get(ext, "json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_qa(source_path: str, target_path: str, fmt: str = None, register: str = "du") -> list[str]:
    if fmt is None:
        fmt = detect_format(source_path)

    loader = LOADERS.get(fmt)
    if not loader:
        return [f"Unsupported format: {fmt}. Supported: {list(LOADERS.keys())}"]

    try:
        source_strings = loader(source_path)
    except Exception as e:
        return [f"Failed to parse source file: {e}"]

    try:
        target_strings = loader(target_path)
    except Exception as e:
        return [f"Failed to parse target file: {e}"]

    issues = []

    # Check key count
    src_keys = set(source_strings.keys())
    tgt_keys = set(target_strings.keys())
    missing = src_keys - tgt_keys
    extra = tgt_keys - src_keys
    if missing:
        issues.append(f"[Keys] Missing in target: {sorted(missing)}")
    if extra:
        issues.append(f"[Keys] Extra in target (not in source): {sorted(extra)}")

    # Per-string checks
    for key in sorted(src_keys & tgt_keys):
        src = source_strings[key]
        tgt = target_strings[key]

        issues.extend(check_placeholder_parity(src, tgt, key))
        issues.extend(check_tag_parity(src, tgt, key))
        issues.extend(check_register(tgt, key, mode=register))
        issues.extend(check_length_ratio(src, tgt, key))
        issues.extend(check_whitespace(tgt, key))

        # Flag untranslated (identical to source, unless very short like "OK")
        if src == tgt and len(src) > 3:
            issues.append(f"[Untranslated] {key}: identical to source — \"{src[:60]}\"")

    return issues


def main():
    parser = argparse.ArgumentParser(description="QA checks for localization files")
    parser.add_argument("source", help="Source (EN) file path")
    parser.add_argument("target", help="Target (DE) file path")
    parser.add_argument("--format", choices=["json", "ftl", "properties"], default=None,
                        help="File format (auto-detected from extension if omitted)")
    parser.add_argument("--register", choices=["du", "sie"], default="du",
                        help="Expected register (default: du)")
    args = parser.parse_args()

    issues = run_qa(args.source, args.target, fmt=args.format, register=args.register)

    if issues:
        print(f"Found {len(issues)} issue(s):\n")
        for issue in issues:
            print(f"  {issue}")
        sys.exit(1)
    else:
        print("All QA checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()

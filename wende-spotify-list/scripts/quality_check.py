#!/usr/bin/env python3
"""Validate German Wikipedia wikitext for the Spotify streaming list article.

Usage:
    python quality_check.py <wikitext_file> [--json]

Checks:
  1. Balanced braces ({{ and }})
  2. Balanced ref tags (<ref> / </ref> / <ref ... />)
  3. No English template names remaining
  4. No English namespace prefixes (Category:, File:)
  5. No English image params used as wikitext params (thumb, right, left, upright as image param)
  6. Number format in table cells (should use comma decimal)
  7. URLs not mangled (no comma-decimal inside URLs)
  8. Stand dates present and plausible
  9. tabelle-zaehler classes present on auto-numbered tables
 10. No bare English change indicators ({{Steady}}, {{Up}}, {{Down}})

Exit code 0 if all checks pass, 1 if any fail.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field


@dataclass
class Issue:
    check: str
    severity: str  # "error" or "warning"
    line: int
    message: str
    context: str = ""


def check_balanced_braces(text: str) -> list[Issue]:
    """Check that {{ and }} are balanced."""
    issues = []
    lines = text.splitlines()
    depth = 0
    for i, line in enumerate(lines, start=1):
        j = 0
        while j < len(line):
            if j + 1 < len(line) and line[j:j+2] == "{{":
                depth += 1
                j += 2
            elif j + 1 < len(line) and line[j:j+2] == "}}":
                depth -= 1
                if depth < 0:
                    issues.append(Issue(
                        check="balanced_braces",
                        severity="error",
                        line=i,
                        message="Unmatched closing }}",
                        context=line.strip()[:120],
                    ))
                    depth = 0
                j += 2
            else:
                j += 1

    if depth > 0:
        issues.append(Issue(
            check="balanced_braces",
            severity="error",
            line=len(lines),
            message=f"{depth} unclosed {{ remain at end of file",
        ))

    return issues


def check_ref_tags(text: str) -> list[Issue]:
    """Check that <ref> tags are balanced."""
    issues = []
    lines = text.splitlines()

    # Track open refs
    open_refs = []  # list of (line_number)
    for i, line in enumerate(lines, start=1):
        # Self-closing refs: <ref name="..." /> or <ref ... />
        # Remove them first so they don't confuse the count
        cleaned = re.sub(r"<ref\b[^>]*/\s*>", "", line)

        # Opening refs
        for m in re.finditer(r"<ref\b[^>]*>", cleaned):
            open_refs.append(i)

        # Closing refs
        for m in re.finditer(r"</ref\s*>", cleaned):
            if open_refs:
                open_refs.pop()
            else:
                issues.append(Issue(
                    check="ref_tags",
                    severity="error",
                    line=i,
                    message="Unmatched </ref>",
                    context=line.strip()[:120],
                ))

    for line_num in open_refs:
        issues.append(Issue(
            check="ref_tags",
            severity="error",
            line=line_num,
            message="Unclosed <ref> tag",
        ))

    return issues


def check_english_templates(text: str) -> list[Issue]:
    """Check for English template names that should have been converted."""
    issues = []
    lines = text.splitlines()

    english_templates = [
        (r"\{\{cite web\b", "cite web"),
        (r"\{\{cite news\b", "cite news"),
        (r"\{\{cite magazine\b", "cite magazine"),
        (r"\{\{cite book\b", "cite book"),
        (r"\{\{cite journal\b", "cite journal"),
        (r"\{\{cite press release\b", "cite press release"),
        (r"\{\{cite AV media\b", "cite AV media"),
        (r"\{\{Abbr\b", "Abbr"),
        (r"\{\{Short description\b", "Short description"),
        (r"\{\{Use [a-z]+ dates\b", "Use ... dates"),
        (r"\{\{Dynamic list\b", "Dynamic list"),
        (r"\{\{pp-semi", "pp-semi"),
        (r"\{\{Steady\}\}", "Steady (should be Unverändert)"),
        (r"\{\{Up\}\}", "Up (should be Gestiegen)"),
        (r"\{\{Down\}\}", "Down (should be Gefallen)"),
        (r"\{\{Increase\}\}", "Increase (should be Gestiegen)"),
        (r"\{\{Decrease\}\}", "Decrease (should be Gefallen)"),
        (r"\{\{Use list-defined references", "Use list-defined references"),
        (r"\{\{efn\b", "efn (should be a footnote or removed)"),
    ]

    for i, line in enumerate(lines, start=1):
        for pattern, name in english_templates:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(Issue(
                    check="english_templates",
                    severity="error",
                    line=i,
                    message=f"English template found: {name}",
                    context=line.strip()[:120],
                ))

    return issues


def check_english_namespaces(text: str) -> list[Issue]:
    """Check for English namespace prefixes."""
    issues = []
    lines = text.splitlines()

    patterns = [
        (r"\[\[Category:", "Category: (should be Kategorie:)"),
        (r"\[\[File:", "File: (should be Datei:)"),
        (r"\[\[Image:", "Image: (should be Datei:)"),
    ]

    for i, line in enumerate(lines, start=1):
        for pattern, name in patterns:
            if re.search(pattern, line):
                issues.append(Issue(
                    check="english_namespaces",
                    severity="error",
                    line=i,
                    message=f"English namespace: {name}",
                    context=line.strip()[:120],
                ))

    return issues


def check_english_image_params(text: str) -> list[Issue]:
    """Check for English image parameters in file links."""
    issues = []
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        # Only check inside [[Datei: or [[File: links
        if "[[Datei:" in line or "[[File:" in line:
            # Look for English params: |thumb|, |right|, |left|, |upright|
            # but not inside URLs or template params
            if re.search(r"\|thumb[\|\]]", line):
                issues.append(Issue(
                    check="english_image_params",
                    severity="error",
                    line=i,
                    message="English image param 'thumb' (should be 'mini')",
                    context=line.strip()[:120],
                ))
            if re.search(r"\|right[\|\]]", line):
                issues.append(Issue(
                    check="english_image_params",
                    severity="warning",
                    line=i,
                    message="English image param 'right' (should be 'rechts')",
                    context=line.strip()[:120],
                ))
            if re.search(r"\|upright[\|\]]", line) and "hochkant" not in line:
                issues.append(Issue(
                    check="english_image_params",
                    severity="warning",
                    line=i,
                    message="English image param 'upright' (should be 'hochkant')",
                    context=line.strip()[:120],
                ))

    return issues


def check_number_formats_in_tables(text: str) -> list[Issue]:
    """Check that numbers in table cells use German format (comma decimal)."""
    issues = []
    lines = text.splitlines()
    in_table = False

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("{|"):
            in_table = True
            continue
        if stripped.startswith("|}"):
            in_table = False
            continue

        if not in_table:
            continue
        if not stripped.startswith("|") or stripped.startswith("|+") or stripped.startswith("|-") or stripped.startswith("!"):
            continue

        # Skip lines that contain URLs (don't check number format inside URLs)
        if "http://" in line or "https://" in line or "url=" in line.lower():
            continue

        # Look for numbers like 135.02 that should be 135,02
        # But skip things like version numbers, dates, etc.
        # Pattern: digit(s).digit(s) where the decimal part is 1-2 digits
        # (stream counts typically have 1-2 decimal places)
        matches = re.findall(r"(?<!\d)(\d{1,3})\.(\d{1,2})(?!\d)", line)
        for whole, decimal in matches:
            # Skip if it looks like it's inside a ref or URL context
            if f"{whole}.{decimal}" in line:
                # Check it's not inside a template param that's a URL or date
                pos = line.index(f"{whole}.{decimal}")
                context_before = line[max(0, pos-30):pos]
                if any(x in context_before.lower() for x in ["url=", "http", "abruf=", "datum=", "doi=", "isbn"]):
                    continue

                issues.append(Issue(
                    check="number_format",
                    severity="warning",
                    line=i,
                    message=f"Possible English decimal format: {whole}.{decimal} (should be {whole},{decimal}?)",
                    context=stripped[:120],
                ))

    return issues


def check_urls_intact(text: str) -> list[Issue]:
    """Check that URLs haven't had their dots replaced with commas."""
    issues = []
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        # Find URLs and check for comma where dot should be
        for m in re.finditer(r"https?://[^\s\|\}\]>]+", line):
            url = m.group()
            # URLs should not have commas in domain names
            domain_match = re.match(r"https?://([^/]+)", url)
            if domain_match:
                domain = domain_match.group(1)
                if "," in domain:
                    issues.append(Issue(
                        check="url_integrity",
                        severity="error",
                        line=i,
                        message=f"Comma in URL domain (likely mangled number conversion): {domain}",
                        context=url[:120],
                    ))

    return issues


def check_stand_dates(text: str) -> list[Issue]:
    """Check that Stand dates are present."""
    issues = []
    has_stand = False
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if re.search(r"Stand[:\s]", line):
            has_stand = True

    if not has_stand:
        issues.append(Issue(
            check="stand_dates",
            severity="warning",
            line=0,
            message="No 'Stand' date found in the article",
        ))

    return issues


def check_tabelle_zaehler(text: str) -> list[Issue]:
    """Check that sortable tables use tabelle-zaehler where expected."""
    issues = []
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        if 'class="wikitable sortable"' in line and "tabelle-zaehler" not in line:
            # Check if the next few lines suggest this should be auto-numbered
            # Tables with named row headers (Month, Year, Künstler + Anzahl Monate)
            # intentionally skip auto-numbering.
            context_lines = lines[i:i+8] if i < len(lines) else []
            has_rank_col = any(re.search(r"!\s*(Rank|#|Nr\.)", l) for l in context_lines)
            has_named_rows = any(re.search(
                r"!\s*(Month|Monat|Jahr|Year|Künstler\s*!.*Anzahl)", l
            ) for l in context_lines)
            if not has_rank_col and not has_named_rows:
                issues.append(Issue(
                    check="tabelle_zaehler",
                    severity="warning",
                    line=i,
                    message="Sortable wikitable without tabelle-zaehler class (may need auto-numbering)",
                    context=line.strip()[:120],
                ))

    return issues


def run_all_checks(text: str) -> list[Issue]:
    all_issues = []
    all_issues.extend(check_balanced_braces(text))
    all_issues.extend(check_ref_tags(text))
    all_issues.extend(check_english_templates(text))
    all_issues.extend(check_english_namespaces(text))
    all_issues.extend(check_english_image_params(text))
    all_issues.extend(check_number_formats_in_tables(text))
    all_issues.extend(check_urls_intact(text))
    all_issues.extend(check_stand_dates(text))
    all_issues.extend(check_tabelle_zaehler(text))
    return all_issues


def format_text(issues: list[Issue]) -> str:
    if not issues:
        return "All checks passed."

    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    lines = []
    lines.append(f"Found {len(errors)} errors, {len(warnings)} warnings\n")

    if errors:
        lines.append("ERRORS:")
        for issue in errors:
            loc = f"  Line {issue.line}: " if issue.line > 0 else "  "
            lines.append(f"{loc}[{issue.check}] {issue.message}")
            if issue.context:
                lines.append(f"    > {issue.context}")
        lines.append("")

    if warnings:
        lines.append("WARNINGS:")
        for issue in warnings:
            loc = f"  Line {issue.line}: " if issue.line > 0 else "  "
            lines.append(f"{loc}[{issue.check}] {issue.message}")
            if issue.context:
                lines.append(f"    > {issue.context}")

    return "\n".join(lines)


def format_json(issues: list[Issue]) -> str:
    data = []
    for issue in issues:
        entry = {
            "check": issue.check,
            "severity": issue.severity,
            "line": issue.line,
            "message": issue.message,
        }
        if issue.context:
            entry["context"] = issue.context
        data.append(entry)
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Validate German Wikipedia wikitext")
    parser.add_argument("file", help="Wikitext file to check")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        text = f.read()

    issues = run_all_checks(text)

    if args.json:
        print(format_json(issues))
    else:
        print(format_text(issues))

    sys.exit(1 if any(i.severity == "error" for i in issues) else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Compare two Wikipedia wikitext files section-by-section.

Usage:
    python diff_sections.py <old_file> <new_file> [--json]

Parses both files into sections (split on == headers), diffs each pair,
and prints a human-readable summary. With --json, outputs structured JSON
instead.

Sections present in only one file are flagged as added/removed.
For changed sections, outputs the specific line-level changes.
"""

import argparse
import difflib
import json
import re
import sys
from dataclasses import dataclass, field


@dataclass
class Section:
    title: str  # e.g. "Most monthly listeners" or "__lead__" for text before first header
    level: int  # number of = signs (2 for ==, 3 for ===, 0 for lead)
    start_line: int
    lines: list[str] = field(default_factory=list)


def parse_sections(text: str) -> list[Section]:
    """Split wikitext into sections by == headers."""
    lines = text.splitlines(keepends=True)
    sections: list[Section] = []
    current = Section(title="__lead__", level=0, start_line=1)

    header_re = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$")

    for i, line in enumerate(lines, start=1):
        m = header_re.match(line)
        if m:
            if current.lines or current.title == "__lead__":
                sections.append(current)
            level = len(m.group(1))
            title = m.group(2).strip()
            current = Section(title=title, level=level, start_line=i, lines=[line])
        else:
            current.lines.append(line)

    if current.lines or current.title == "__lead__":
        sections.append(current)

    return sections


def section_key(s: Section) -> str:
    """Unique key for matching sections across files."""
    return f"{'=' * s.level} {s.title} {'=' * s.level}" if s.level > 0 else "__lead__"


@dataclass
class SectionDiff:
    title: str
    level: int
    status: str  # "unchanged", "changed", "added", "removed"
    old_line_count: int = 0
    new_line_count: int = 0
    added_lines: int = 0
    removed_lines: int = 0
    sample_changes: list[str] = field(default_factory=list)


def diff_sections(old_text: str, new_text: str) -> list[SectionDiff]:
    old_sections = parse_sections(old_text)
    new_sections = parse_sections(new_text)

    old_by_key = {section_key(s): s for s in old_sections}
    new_by_key = {section_key(s): s for s in new_sections}

    all_keys = list(dict.fromkeys(
        [section_key(s) for s in old_sections] +
        [section_key(s) for s in new_sections]
    ))

    results: list[SectionDiff] = []

    for key in all_keys:
        old_s = old_by_key.get(key)
        new_s = new_by_key.get(key)

        if old_s and not new_s:
            results.append(SectionDiff(
                title=old_s.title,
                level=old_s.level,
                status="removed",
                old_line_count=len(old_s.lines),
            ))
        elif new_s and not old_s:
            results.append(SectionDiff(
                title=new_s.title,
                level=new_s.level,
                status="added",
                new_line_count=len(new_s.lines),
            ))
        else:
            old_lines = old_s.lines
            new_lines = new_s.lines

            if old_lines == new_lines:
                results.append(SectionDiff(
                    title=old_s.title,
                    level=old_s.level,
                    status="unchanged",
                    old_line_count=len(old_lines),
                    new_line_count=len(new_lines),
                ))
            else:
                diff = list(difflib.unified_diff(
                    old_lines, new_lines,
                    fromfile="old", tofile="new",
                    lineterm="",
                ))

                added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
                removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))

                # Collect sample changes (first 20 diff lines that are actual changes)
                samples = []
                for l in diff:
                    if l.startswith(("@@", "---", "+++")):
                        continue
                    if l.startswith(("+", "-")):
                        samples.append(l.rstrip())
                        if len(samples) >= 20:
                            break

                results.append(SectionDiff(
                    title=old_s.title,
                    level=old_s.level,
                    status="changed",
                    old_line_count=len(old_lines),
                    new_line_count=len(new_lines),
                    added_lines=added,
                    removed_lines=removed,
                    sample_changes=samples,
                ))

    return results


def format_text(results: list[SectionDiff]) -> str:
    lines = []
    changed_count = sum(1 for r in results if r.status == "changed")
    added_count = sum(1 for r in results if r.status == "added")
    removed_count = sum(1 for r in results if r.status == "removed")
    unchanged_count = sum(1 for r in results if r.status == "unchanged")

    lines.append(f"Sections: {len(results)} total, {changed_count} changed, "
                 f"{added_count} added, {removed_count} removed, {unchanged_count} unchanged")
    lines.append("")

    for r in results:
        indent = "  " * max(0, r.level - 2)
        header = f"{'=' * r.level} {r.title} {'=' * r.level}" if r.level > 0 else "[Lead]"

        if r.status == "unchanged":
            lines.append(f"{indent}{header}: no changes ({r.old_line_count} lines)")
        elif r.status == "added":
            lines.append(f"{indent}{header}: ADDED ({r.new_line_count} lines)")
        elif r.status == "removed":
            lines.append(f"{indent}{header}: REMOVED ({r.old_line_count} lines)")
        elif r.status == "changed":
            lines.append(f"{indent}{header}: CHANGED (+{r.added_lines} -{r.removed_lines} lines)")
            for s in r.sample_changes:
                lines.append(f"{indent}  {s}")

    return "\n".join(lines)


def format_json(results: list[SectionDiff]) -> str:
    data = []
    for r in results:
        entry = {
            "title": r.title,
            "level": r.level,
            "status": r.status,
        }
        if r.status == "changed":
            entry["added_lines"] = r.added_lines
            entry["removed_lines"] = r.removed_lines
            entry["sample_changes"] = r.sample_changes
        elif r.status == "added":
            entry["new_line_count"] = r.new_line_count
        elif r.status == "removed":
            entry["old_line_count"] = r.old_line_count
        data.append(entry)
    return json.dumps(data, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Diff two wikitext files by section")
    parser.add_argument("old_file", help="Previous version of the wikitext")
    parser.add_argument("new_file", help="New version of the wikitext")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    with open(args.old_file, encoding="utf-8") as f:
        old_text = f.read()
    with open(args.new_file, encoding="utf-8") as f:
        new_text = f.read()

    results = diff_sections(old_text, new_text)

    if args.json:
        print(format_json(results))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()

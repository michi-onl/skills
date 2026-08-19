#!/usr/bin/env python3
"""Validate a WidgetStar iframe widget page against the embed contract.

Usage:
    python3 check_widget.py https://example.com/widget/    # live page: headers + HTML
    python3 check_widget.py --file widget.html             # local file: HTML only

Exit code 1 if any check FAILs. Header checks only run in URL mode, and they catch the
framing problems that make a widget render as a blank box on the installing site.
"""

import argparse
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

IFRAME_JS = "widget.st/js/iframe.js"
UA = "widget-st-skill-checker/1.0"

results = []  # (level, message)


def add(level, message):
    results.append((level, message))


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8", "replace")
            return resp.status, dict(resp.headers), body, resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read().decode("utf-8", "replace"), url
    except Exception as e:  # noqa: BLE001 - surfaced to the user verbatim
        add("FAIL", f"Could not fetch the page: {e}")
        return None, {}, "", url


def check_headers(status, headers, final_url, requested_url):
    if urlparse(requested_url).scheme != "https":
        add("FAIL", "Page URL is not https — widget.st requires an absolute https URL, "
                    "and http content is blocked as mixed content on https sites.")

    if final_url != requested_url:
        add("WARN", f"Redirected to {final_url}. Use the final URL as the Page URL so the "
                    "iframe skips a hop.")

    if status != 200:
        add("FAIL", f"HTTP {status} — the Page URL must return 200.")

    ctype = headers.get("Content-Type", "")
    if "text/html" not in ctype.lower():
        add("FAIL", f"Content-Type is '{ctype or 'missing'}', expected text/html.")

    xfo = headers.get("X-Frame-Options")
    if xfo:
        add("FAIL", f"X-Frame-Options: {xfo} — this blocks framing entirely; the widget shows "
                    "as a blank box. Remove the header for this path.")

    csp = headers.get("Content-Security-Policy", "")
    m = re.search(r"frame-ancestors([^;]*)", csp, re.I)
    if m:
        sources = m.group(1).strip()
        low = sources.lower()
        if "'none'" in low:
            add("FAIL", "CSP frame-ancestors 'none' — framing is blocked. Remove or widen it.")
        elif "*" in low or "http" in low:
            add("PASS", f"CSP frame-ancestors allows framing: {sources}")
        else:
            add("FAIL", f"CSP frame-ancestors is restricted to: {sources} — installing sites "
                        "cannot frame this. Allow the installer's origins or drop the directive.")
    else:
        add("PASS", "No framing restrictions in the response headers.")


def strip_comments(html):
    """Drop HTML/JS comments so guidance written *about* an anti-pattern isn't flagged."""
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"/\*.*?\*/", " ", html, flags=re.S)
    html = re.sub(r"""(?<![:"'\w])//[^\n]*""", " ", html)
    return html


def settings_keys(code):
    """Keys read as WS.settings.x, WS.settings['x'], or via an alias (var S = WS.settings)."""
    keys = set(re.findall(r"WS\.settings\.(\w+)", code))
    keys |= set(re.findall(r"""WS\.settings\[["'](\w+)["']\]""", code))
    for alias in set(re.findall(r"(?:var|let|const)\s+(\w+)\s*=[^;\n]*WS\.settings", code)):
        keys |= set(re.findall(rf"\b{re.escape(alias)}\.(\w+)", code))
        keys |= set(re.findall(rf"""\b{re.escape(alias)}\[["'](\w+)["']\]""", code))
    return sorted(keys - {"settings", "prototype", "hasOwnProperty"})


def check_html(raw_html):
    html = strip_comments(raw_html)
    head_m = re.search(r"<head\b[^>]*>(.*?)</head>", html, re.I | re.S)
    head = head_m.group(1) if head_m else ""

    if IFRAME_JS not in html:
        add("FAIL", 'Missing <script src="https://widget.st/js/iframe.js"></script>. Without it '
                    "the page never reports its size and the widget stays 0x0 and invisible on "
                    "every installing site.")
    elif IFRAME_JS not in head:
        add("WARN", "iframe.js is not inside <head>. Load it first in <head> so WS.settings "
                    "exists before your own scripts run.")
    else:
        scripts = re.findall(r"<script\b[^>]*>", head, re.I)
        first = next((s for s in scripts if "src" in s.lower()), "")
        if IFRAME_JS in first:
            add("PASS", "iframe.js is the first script in <head>.")
        else:
            add("WARN", "iframe.js is in <head> but not the first script with a src — move it "
                        "up so WS.settings is populated before anything reads it.")

    viewport_units = re.findall(r"\b\d+(?:\.\d+)?(v[hw]|vmin|vmax)\b", html)
    if viewport_units:
        add("FAIL", f"Viewport units used ({len(viewport_units)}x, e.g. {viewport_units[0]}). The "
                    "iframe is sized from the content, so viewport-derived sizes create a "
                    "ResizeObserver feedback loop and the widget flickers forever.")

    if re.search(r"position\s*:\s*fixed", html, re.I):
        add("WARN", "position: fixed found. Fixed elements are out of flow and contribute "
                    "nothing to the measured body box — content can end up measuring as 0 or "
                    "being clipped by the injected overflow:hidden.")

    if re.search(r"\b(?:window\.)?inner(?:Width|Height)\b", html):
        add("WARN", "Reading window.innerWidth/innerHeight inside the iframe measures the "
                    "auto-sized frame, not the host page. Usually a feedback loop.")

    if re.search(r"(?:^|[^-\w])body\s*(?:,[^{]*)?\{[^}]*width\s*:\s*\d+%", html, re.I | re.S):
        add("WARN", "A percentage width on body will collapse: iframe.js sets "
                    "body { width: max-content }. Size the root intrinsically instead.")

    if re.search(r"\.innerHTML\s*=|insertAdjacentHTML|document\.write", html) and \
            re.search(r"WS\.settings", html):
        add("WARN", "HTML injection (innerHTML/insertAdjacentHTML/document.write) on a page that "
                    "reads settings. Settings come from a URL parameter the host page controls — "
                    "use textContent for every value.")

    mixed = re.findall(r'(?:src|href)\s*=\s*["\']http://[^"\']+', html, re.I)
    if mixed:
        add("FAIL", f"{len(mixed)} http:// asset reference(s), e.g. {mixed[0][:70]} — blocked as "
                    "mixed content when the widget runs on an https site.")

    keys = settings_keys(html)
    if keys:
        add("INFO", "Settings keys read directly: " + ", ".join(keys) +
                    " — these must match the dashboard keys exactly.")
    else:
        add("INFO", "No direct WS.settings.<key> reads found (fine if settings are destructured "
                    "or aliased — cross-check the dashboard schema by hand).")

    if not re.search(r"<body\b[^>]*>\s*\S", html, re.I | re.S):
        add("WARN", "<body> looks empty in the served HTML. Render a placeholder synchronously "
                    "so the first size measurement is not zero.")

    size_kb = len(html.encode("utf-8")) / 1024
    add("INFO", f"HTML size: {size_kb:.1f} KB")


def main():
    p = argparse.ArgumentParser(description="Validate a WidgetStar iframe widget page.")
    p.add_argument("target", help="https URL of the widget page, or a path with --file")
    p.add_argument("--file", action="store_true", help="treat target as a local file")
    args = p.parse_args()

    if args.file:
        try:
            with open(args.target, encoding="utf-8") as fh:
                html = fh.read()
        except OSError as e:
            print(f"FAIL  Could not read {args.target}: {e}")
            return 1
        add("INFO", "Local file mode — framing headers are not checked. Re-run against the "
                    "live https URL after publishing.")
        check_html(html)
    else:
        status, headers, html, final_url = fetch(args.target)
        if status is not None:
            check_headers(status, headers, final_url, args.target)
            check_html(html)

    order = {"FAIL": 0, "WARN": 1, "PASS": 2, "INFO": 3}
    results.sort(key=lambda r: order.get(r[0], 4))
    for level, message in results:
        print(f"{level:<5} {message}")

    fails = sum(1 for level, _ in results if level == "FAIL")
    warns = sum(1 for level, _ in results if level == "WARN")
    print(f"\n{fails} failure(s), {warns} warning(s).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

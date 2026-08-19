#!/usr/bin/env python3
"""translatewiki.net client for the German localization of the Wikipedia apps.

Stdlib only. Commands:

    auth      verify credentials and translator rights
    status    backlog counts per platform
    term      how an English/German term is used, split by platform
    pull      fetch a work batch to a JSON file
    sweep     apply ordered literal replacements across a batch
    qa        run quality checks on a batch file or the live collection
    diff      render a batch as a proofreadable review page (HTML or Markdown)
    push      save a reviewed batch back to translatewiki

Config: ~/.config/translatewiki/claude.json (override with $TWN_CONFIG)

    {
      "username": "Mike is Michi@claude-twn",
      "password": "<botpassword>",
      "user_agent": "MichiLocalizationBot/1.0 (https://translatewiki.net/wiki/User:Mike_is_Michi)"
    }
"""

from __future__ import annotations

import argparse
import http.client
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://translatewiki.net/w/api.php"
DEFAULT_UA = "Claude-assisted de-localization bot (https://translatewiki.net/wiki/User:Mike_is_Michi)"
CONFIG_PATH = Path(os.environ.get("TWN_CONFIG", Path.home() / ".config/translatewiki/claude.json"))
GLOSSARY_PATH = Path(__file__).resolve().parent.parent / "references" / "glossary.md"

GROUPS = {
    "all": "out-wikimedia-mobile-0-all",
    "ios": "out-wikimedia-mobile-wikipedia-ios-0-all",
    "android": "out-wikimedia-mobile-wikipedia-android-strings",
}

# Verified against the live API on 2026-08-19:
#   !translated        = untranslated + fuzzy (everything needing work)
#   !translated|!fuzzy = never translated
#   fuzzy              = translated but the English source changed since
FILTERS = {
    "new": "!optional|!ignored|!translated|!fuzzy",
    "outdated": "!optional|!ignored|fuzzy",
    "todo": "!optional|!ignored|!translated",
    "done": "!optional|!ignored|translated",
    "all": "!optional|!ignored",
}

DEFAULT_SUMMARY = "de: Übersetzung aktualisiert (KI-gestützter Entwurf, manuell geprüft)"


# --------------------------------------------------------------------------- #
# API client
# --------------------------------------------------------------------------- #


class TwnError(RuntimeError):
    pass


class TWN:
    def __init__(self, user_agent: str = DEFAULT_UA):
        self.ua = user_agent
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self._csrf = None
        self.username = None

    def _call(self, params: dict, post: bool = False) -> dict:
        params = dict(params, format="json", formatversion="1")
        data = urllib.parse.urlencode(params).encode()
        for attempt in range(4):
            try:
                if post:
                    req = urllib.request.Request(API, data=data, headers={"User-Agent": self.ua})
                else:
                    req = urllib.request.Request(
                        API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": self.ua}
                    )
                with self.opener.open(req, timeout=90) as r:
                    payload = json.load(r)
            except (
                urllib.error.URLError,
                http.client.HTTPException,  # RemoteDisconnected, IncompleteRead, BadStatusLine
                OSError,  # ConnectionReset/BrokenPipe that never became a URLError
                TimeoutError,
                json.JSONDecodeError,
            ) as exc:
                if attempt == 3:
                    raise TwnError(f"network failure calling {params.get('action')}: {exc}") from exc
                time.sleep(2 * (attempt + 1))
                continue
            if "error" in payload:
                code = payload["error"].get("code", "")
                if code in ("maxlag", "readonly") and attempt < 3:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise TwnError(f"API error {code}: {payload['error'].get('info', '')}")
            return payload
        raise TwnError("unreachable")

    def get(self, params: dict) -> dict:
        return self._call(params)

    def post(self, params: dict) -> dict:
        return self._call(params, post=True)

    # -- auth ------------------------------------------------------------- #

    def login(self, username: str, password: str) -> dict:
        token = self.get({"action": "query", "meta": "tokens", "type": "login"})
        lgtoken = token["query"]["tokens"]["logintoken"]
        res = self.post(
            {
                "action": "login",
                "lgname": username,
                "lgpassword": password,
                "lgtoken": lgtoken,
            }
        )
        if res.get("login", {}).get("result") != "Success":
            reason = res.get("login", {}).get("reason", res.get("login", {}).get("result"))
            raise TwnError(f"login failed: {reason}")
        self.username = res["login"]["lgusername"]
        return self.userinfo()

    def userinfo(self) -> dict:
        res = self.get({"action": "query", "meta": "userinfo", "uiprop": "groups|rights"})
        return res["query"]["userinfo"]

    def csrf(self) -> str:
        if self._csrf is None:
            res = self.get({"action": "query", "meta": "tokens", "type": "csrf"})
            self._csrf = res["query"]["tokens"]["csrftoken"]
        return self._csrf

    # -- reads ------------------------------------------------------------ #

    def collection(self, group: str, language: str, mcfilter: str = "", props: str = "definition|translation|tags|properties") -> list:
        out, cont = [], {}
        while True:
            params = {
                "action": "query",
                "list": "messagecollection",
                "mcgroup": group,
                "mclanguage": language,
                "mcprop": props,
                "mclimit": "500",
            }
            if mcfilter:
                params["mcfilter"] = mcfilter
            params.update(cont)
            data = self.get(params)
            out.extend(data["query"]["messagecollection"])
            if "continue" not in data:
                return out
            cont = data["continue"]
            time.sleep(0.2)

    def counts(self, group: str, language: str) -> dict:
        result = {}
        for name, mcfilter in FILTERS.items():
            data = self.get(
                {
                    "action": "query",
                    "list": "messagecollection",
                    "mcgroup": group,
                    "mclanguage": language,
                    "mcfilter": mcfilter,
                    "mclimit": "1",
                }
            )
            result[name] = data["query"]["metadata"]["resultsize"]
        return result

    def aids(self, title: str, props: str = "definitiondiff|documentation") -> dict:
        try:
            data = self.get({"action": "translationaids", "title": title, "prop": props})
        except TwnError:
            return {}
        return data.get("helpers", {})

    # -- writes ----------------------------------------------------------- #

    def save(self, title: str, text: str, summary: str) -> dict:
        res = self.post(
            {
                "action": "edit",
                "title": title,
                "text": text,
                "summary": summary,
                "token": self.csrf(),
                "assert": "user",
                "nocreate": "",
            }
        )
        return res.get("edit", {})

    def save_or_create(self, title: str, text: str, summary: str) -> dict:
        try:
            return self.save(title, text, summary)
        except TwnError as exc:
            if "missingtitle" not in str(exc):
                raise
        res = self.post(
            {
                "action": "edit",
                "title": title,
                "text": text,
                "summary": summary,
                "token": self.csrf(),
                "assert": "user",
            }
        )
        return res.get("edit", {})


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise TwnError(
            f"no credentials at {CONFIG_PATH}\n"
            "Create a BotPassword at https://translatewiki.net/wiki/Special:BotPasswords "
            '(grants: "Basic rights", "Edit existing pages", "Create, edit, and move pages"), then:\n'
            f"  mkdir -p {CONFIG_PATH.parent}\n"
            f'  printf \'{{"username":"USER@LABEL","password":"SECRET"}}\' > {CONFIG_PATH}\n'
            f"  chmod 600 {CONFIG_PATH}"
        )
    mode = CONFIG_PATH.stat().st_mode & 0o077
    if mode:
        print(f"warning: {CONFIG_PATH} is group/world readable — run: chmod 600 {CONFIG_PATH}", file=sys.stderr)
    cfg = json.loads(CONFIG_PATH.read_text())
    for key in ("username", "password"):
        if not cfg.get(key):
            raise TwnError(f"{CONFIG_PATH} is missing '{key}'")
    return cfg


def connect(anonymous: bool = False) -> TWN:
    if anonymous:
        return TWN()
    cfg = load_config()
    client = TWN(cfg.get("user_agent", DEFAULT_UA))
    client.login(cfg["username"], cfg["password"])
    return client


# --------------------------------------------------------------------------- #
# Message analysis helpers
# --------------------------------------------------------------------------- #

PLACEHOLDER_RE = re.compile(r"%\d+\$[@sdfx]|%[@sdfx]|\$\d+|%\{[a-zA-Z_]+\}")
PLURAL_RE = re.compile(r"\{\{PLURAL[|:]", re.IGNORECASE)
TAG_RE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^>]*)?/?>")
WIKILINK_RE = re.compile(r"\[\[|\]\]")
# Sentence boundaries include block/inline tags: "<b>Du bist …" is sentence-initial.
SENTENCE_START_RE = re.compile(r"(^|[.!?:•\n]|>|„|\"|–|-|\()\s*$")


def placeholders(text: str) -> list:
    return PLACEHOLDER_RE.findall(text or "")


def tags(text: str) -> list:
    """Tag names only. Attribute values are excluded on purpose: a German string is
    supposed to point <a href> at de.wikipedia.org, which is not a markup error."""
    return sorted(re.sub(r"[<>/\s].*", "", t.lstrip("</")).lower() for t in TAG_RE.findall(text or ""))


def hrefs(text: str) -> list:
    return re.findall(r'href="([^"]*)"', text or "", re.IGNORECASE)


def plural_blocks(text: str) -> list:
    """Return ``(start, end, arms)`` for every {{PLURAL…}} block in ``text``.

    Both syntaxes in these groups are handled:
        {{PLURAL:$1|singular|plural}}   — the head argument is the count variable
        {{PLURAL|one=singular|plural}}  — no head argument

    The head argument is dropped; the arms are returned raw, still carrying any
    ``one=`` / ``0=`` label.
    """
    blocks = []
    for match in PLURAL_RE.finditer(text or ""):
        i, depth, arms = match.end(), 2, [""]
        while i < len(text) and depth:
            if text.startswith("{{", i):
                depth += 2
                arms[-1] += "{{"
                i += 2
            elif text.startswith("}}", i):
                depth -= 2
                if depth:
                    arms[-1] += "}}"
                i += 2
            elif text[i] == "|" and depth == 2:
                arms.append("")
                i += 1
            else:
                arms[-1] += text[i]
                i += 1
        if match.group(0).endswith(":"):
            arms = arms[1:]
        blocks.append((match.start(), i, arms))
    return blocks


def plural_forms(text: str) -> list:
    """Return the count of *grammatical* forms in each {{PLURAL…}} block.

    Explicit-number arms (``0=…``, ``1=…``) are exact-value overrides rather than
    grammatical forms, so they are not counted. MediaWiki also accepts a single
    form, used for every number — idiomatic in German when the noun does not
    inflect ("{{PLURAL:$1|$1 Byte}}"), so one form is valid, not an error.
    """
    return [
        len([a for a in arms if not re.match(r"\s*\d+\s*=", a)])
        for _, _, arms in plural_blocks(text)
    ]


def plural_variants(text: str, limit: int = 12) -> list:
    """Every way the string can actually render, one per combination of PLURAL arms.

    Placeholder checks have to run per variant, not over the raw string: the two
    ``%d`` in ``{{PLURAL|one=%d Sammlung|%d Sammlungen}}`` live in mutually
    exclusive arms, so exactly one of them ever reaches the screen. Counting them
    together makes a correct translation look like a reordering hazard, and makes
    the idiomatic single-arm German form ("{{PLURAL:$1|$1 ausgewählt}}" against an
    English two-arm source) look like a dropped placeholder.
    """
    text = text or ""
    blocks = plural_blocks(text)
    if not blocks:
        return [text]
    variants, cursor = [""], 0
    for start, end, arms in blocks:
        prefix = text[cursor:start]
        rendered = [re.sub(r"^\s*\w+\s*=", "", a) for a in arms] or [""]
        variants = [v + prefix + a for v in variants for a in rendered][:limit]
        cursor = end
    tail = text[cursor:]
    return [v + tail for v in variants]


def strip_fuzzy(text: str) -> str:
    return re.sub(r"!!FUZZY!!\s*", "", text or "").strip()


def platform_of(message: dict) -> str:
    return "ios" if "ios" in message.get("primaryGroup", "") else "android"


def load_glossary() -> list:
    """Parse the pipe table in references/glossary.md → [(en, de, strict)]."""
    if not GLOSSARY_PATH.exists():
        return []
    entries = []
    in_table = False
    for line in GLOSSARY_PATH.read_text().splitlines():
        line = line.strip()
        if line.startswith("| English") or line.startswith("| Englisch"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2 or set(cells[0]) <= set("- :"):
                continue
            en, de = cells[0].strip("`"), cells[1]
            note = cells[2] if len(cells) > 2 else ""
            if not en or not de or de in ("—", "-"):
                continue
            entries.append((en.lower(), [d.strip().strip("`") for d in de.split("/")], "⚠" not in note))
    return entries


# --------------------------------------------------------------------------- #
# QA
# --------------------------------------------------------------------------- #


def qa_message(definition: str, translation: str, key: str = "", glossary: list | None = None,
               platform: str = "android") -> list:
    """Return a list of (severity, code, detail) findings for one message."""
    findings = []
    src, tgt = definition or "", strip_fuzzy(translation or "")
    if not tgt:
        return [("error", "empty", "no translation")]

    # -- placeholders --------------------------------------------------- #
    src_ph, tgt_ph = placeholders(src), placeholders(tgt)
    # Absence is a real breakage; a different repetition count is often a legitimate
    # translation choice (PLURAL arms rarely map one-to-one), so it only warns.
    dropped = sorted(set(src_ph) - set(tgt_ph))
    invented = sorted(set(tgt_ph) - set(src_ph))
    if dropped:
        findings.append(("error", "placeholder-missing", f"source has {dropped}, target has none"))
    if invented:
        findings.append(("error", "placeholder-extra", f"target invents {invented}"))
    # Counted per rendered variant — see plural_variants() for why the raw string lies.
    def peak(variants: list) -> dict:
        out = {}
        for variant in variants:
            found = placeholders(variant)
            for p in set(found):
                out[p] = max(out.get(p, 0), found.count(p))
        return out

    src_peak, tgt_peak = peak(plural_variants(src)), peak(plural_variants(tgt))
    recount = [p for p in sorted(set(src_ph) & set(tgt_ph)) if src_peak.get(p) != tgt_peak.get(p)]
    if recount:
        findings.append(
            ("warn", "placeholder-count", f"{recount} appears a different number of times than in English")
        )
    worst = max(
        (len([p for p in placeholders(v) if re.fullmatch(r"%[sdfx@]", p)]) for v in plural_variants(tgt)),
        default=0,
    )
    if platform == "android" and worst > 1:
        unnumbered = [p for p in tgt_ph if re.fullmatch(r"%[sdfx@]", p)]
        findings.append(
            ("warn", "placeholder-order", f"{worst} unnumbered {sorted(set(unnumbered))} in one rendering — German word order may reorder them; ask for %1$s-style indices")
        )

    # -- plurals -------------------------------------------------------- #
    src_pl, tgt_pl = plural_forms(src), plural_forms(tgt)
    if len(src_pl) != len(tgt_pl):
        # Legitimate when the German noun does not inflect, so this informs rather than blocks.
        findings.append(("warn", "plural-count", f"source has {len(src_pl)} PLURAL block(s), target {len(tgt_pl)}"))
    for forms in tgt_pl:
        if forms > 2:
            findings.append(
                ("error", "plural-arity", f"{forms} grammatical forms — German has only singular and plural")
            )
        elif forms == 0:
            findings.append(("error", "plural-arity", "PLURAL block has no grammatical form"))

    # -- markup --------------------------------------------------------- #
    src_tags, tgt_tags = tags(src), tags(tgt)
    if src_tags != tgt_tags:
        findings.append(("error", "tag-mismatch", f"{src_tags} → {tgt_tags}"))
    if len(hrefs(src)) != len(hrefs(tgt)):
        findings.append(("error", "href-count", f"{len(hrefs(src))} link target(s) in English, {len(hrefs(tgt))} in German"))
    if len(WIKILINK_RE.findall(src)) != len(WIKILINK_RE.findall(tgt)):
        findings.append(("error", "wikilink-mismatch", "[[…]] brackets differ"))

    # -- register (du) --------------------------------------------------- #
    for match in re.finditer(r"\b(Sie|Ihnen|Ihre[nmrs]?|Ihr)\b", tgt):
        before = tgt[: match.start()]
        if match.group(1) == "Sie" and SENTENCE_START_RE.search(before):
            continue  # sentence-initial "Sie" is usually "they"
        findings.append(("warn", "register-sie", f"formal “{match.group(1)}” — these apps use du"))
        break
    for match in re.finditer(r"\b(Du|Dein\w*|Dir|Dich)\b", tgt):
        if not SENTENCE_START_RE.search(tgt[: match.start()]):
            findings.append(("warn", "register-caps", f"“{match.group(1)}” mid-sentence — convention is lowercase du"))
            break

    # -- typography ------------------------------------------------------ #
    if '"' in tgt and '"' not in src:
        findings.append(("warn", "quotes", "straight \" in target — German quotes are „…“"))
    if "..." in tgt and "..." not in src:
        findings.append(("warn", "ellipsis", "use … instead of ..."))
    if tgt != tgt.strip():
        findings.append(("error", "whitespace", "leading/trailing whitespace"))
    if "  " in tgt.strip():
        findings.append(("warn", "whitespace", "double space"))
    if src.endswith(".") != tgt.endswith(".") and len(src) > 25:
        findings.append(("warn", "punctuation", "final period differs from source"))

    # -- length ---------------------------------------------------------- #
    if len(src) <= 40 and len(tgt) > max(1.6 * len(src), len(src) + 8):
        findings.append(("warn", "length", f"{len(tgt)} chars vs {len(src)} in English — tight UI slot, shorten if possible"))

    # -- untranslated ----------------------------------------------------- #
    if tgt == src and len(src.split()) > 2:
        findings.append(("warn", "identical", "identical to English"))

    # -- glossary --------------------------------------------------------- #
    # Match against prose only: {{{username}}} and friends are template parameters,
    # not words a translator is expected to render.
    src_prose = re.sub(r"\{\{\{.*?\}\}\}|\{\{.*?\}\}|%\d+\$[@sdfx]|%[@sdfx]|\$\d+", " ", src)
    for en, de_options, strict in glossary or []:
        if re.search(r"\b" + re.escape(en) + r"", src_prose, re.IGNORECASE):
            if not any(re.search(re.escape(opt.rstrip("*")), tgt, re.IGNORECASE) for opt in de_options):
                findings.append(
                    (("warn" if strict else "info"), "glossary", f"“{en}” → expected {'/'.join(de_options)}")
                )
    return findings


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def cmd_auth(args) -> int:
    client = connect()
    info = client.userinfo()
    print(f"logged in as {info['name']}")
    print(f"  groups: {', '.join(g for g in info.get('groups', []) if g != '*')}")
    rights = info.get("rights", [])
    for right in ("translate", "edit", "translate-messagereview"):
        print(f"  {right:26s} {'yes' if right in rights else 'NO'}")
    if "translate" not in rights:
        print("\nAccount lacks the 'translate' right — request translator status on translatewiki.", file=sys.stderr)
        return 1
    return 0


def cmd_status(args) -> int:
    client = connect(anonymous=True)
    rows = []
    for name in ("ios", "android"):
        counts = client.counts(GROUPS[name], args.language)
        rows.append((name, counts))
    total = {k: sum(c[k] for _, c in rows) for k in FILTERS}
    print(f"Wikipedia apps → {args.language}\n")
    print(f"{'':10s} {'total':>7s} {'done':>7s} {'new':>7s} {'outdated':>9s} {'todo':>7s}")
    for name, c in rows + [("both", total)]:
        print(f"{name:10s} {c['all']:7d} {c['done']:7d} {c['new']:7d} {c['outdated']:9d} {c['todo']:7d}")
    return 0


def cmd_pull(args) -> int:
    client = connect(anonymous=True)
    group = GROUPS[args.platform]
    mcfilter = FILTERS[args.filter]
    messages = client.collection(group, args.language, mcfilter)
    if args.key:
        pattern = re.compile(args.key)
        messages = [m for m in messages if pattern.search(m["key"])]
    if args.limit:
        messages = messages[: args.limit]

    docs = {m["key"]: m.get("translation") for m in client.collection(group, "qqq", props="translation")}

    batch = {
        "meta": {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "group": group,
            "platform": args.platform,
            "language": args.language,
            "filter": args.filter,
            "count": len(messages),
            "summary": args.summary,
        },
        "messages": [],
    }
    for i, m in enumerate(messages, 1):
        entry = {
            "key": m["key"],
            "title": m["title"],
            "platform": platform_of(m),
            "status": m.get("properties", {}).get("status"),
            "definition": m.get("definition"),
            "documentation": docs.get(m["key"]),
            "current": strip_fuzzy(m.get("translation")),
            "new": "",
            "note": "",
        }
        if "fuzzy" in (m.get("tags") or []) and not args.no_diff:
            helpers = client.aids(m["title"], "definitiondiff")
            diff = helpers.get("definitiondiff") or {}
            if diff.get("value_old"):
                entry["english_was"] = diff["value_old"]
                entry["english_now"] = diff.get("value_new", entry["definition"])
            time.sleep(0.15)
            if args.verbose and i % 25 == 0:
                print(f"  …{i}/{len(messages)} diffs fetched", file=sys.stderr)
        batch["messages"].append(entry)

    out = Path(args.out)
    out.write_text(json.dumps(batch, ensure_ascii=False, indent=2))
    fuzzy_with_diff = sum(1 for m in batch["messages"] if "english_was" in m)
    print(f"{len(messages)} message(s) → {out}  ({fuzzy_with_diff} with an English diff)")
    return 0


def cmd_qa(args) -> int:
    glossary = load_glossary()
    if args.batch:
        batch = json.loads(Path(args.batch).read_text())
        items = [
            {
                "key": m["key"],
                "definition": m["definition"],
                "translation": m["new"] or m["current"],
                "platform": m.get("platform", "android"),
                "which": "new" if m["new"] else "current",
            }
            for m in batch["messages"]
            if (m["new"] or m["current"])
        ]
        if args.only_new:
            items = [i for i in items if i["which"] == "new"]
    else:
        client = connect(anonymous=True)
        messages = client.collection(GROUPS[args.platform], args.language, FILTERS[args.filter])
        docs = {}
        if args.fix_batch:
            docs = {
                m["key"]: m.get("translation")
                for m in client.collection(GROUPS[args.platform], "qqq", props="translation")
            }
        items = [
            {
                "key": m["key"],
                "title": m["title"],
                "definition": m.get("definition") or "",
                "translation": m.get("translation") or "",
                "documentation": docs.get(m["key"]),
                "platform": platform_of(m),
                "which": "live",
            }
            for m in messages
            if m.get("translation")
        ]

    report, counts = [], {"error": 0, "warn": 0, "info": 0}
    for item in items:
        findings = qa_message(item["definition"], item["translation"], item["key"], glossary, item["platform"])
        findings = [f for f in findings if f[0] != "info" or args.verbose]
        if findings:
            report.append((item, findings))
            for sev, _, _ in findings:
                counts[sev] += 1

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "key": i["key"],
                        "definition": i["definition"],
                        "translation": i["translation"],
                        "findings": [{"severity": s, "code": c, "detail": d} for s, c, d in f],
                    }
                    for i, f in report
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for item, findings in report:
            if not any(s == "error" for s, _, _ in findings) and args.errors_only:
                continue
            print(f"\n{item['key']}  [{item['platform']}]")
            print(f"  en: {item['definition']}")
            print(f"  de: {item['translation']}")
            for sev, code, detail in findings:
                print(f"  {sev.upper():5s} {code}: {detail}")
        print(f"\n{len(items)} checked · {counts['error']} errors · {counts['warn']} warnings in {len(report)} message(s)")

    if args.fix_batch:
        selected = [
            (i, f) for i, f in report
            if i.get("title") and (not args.errors_only or any(s == "error" for s, _, _ in f))
        ]
        batch = {
            "meta": {
                "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "group": GROUPS[args.platform],
                "platform": args.platform,
                "language": args.language,
                "filter": f"qa:{args.filter}",
                "count": len(selected),
                "summary": DEFAULT_SUMMARY,
            },
            "messages": [
                {
                    "key": i["key"],
                    "title": i["title"],
                    "platform": i["platform"],
                    "status": "qa",
                    "definition": i["definition"],
                    "documentation": i.get("documentation"),
                    "current": i["translation"],
                    "new": "",
                    "note": "; ".join(f"{c}: {d}" for _, c, d in f),
                }
                for i, f in selected
            ],
        }
        Path(args.fix_batch).write_text(json.dumps(batch, ensure_ascii=False, indent=2))
        print(f"{len(selected)} flagged message(s) → {args.fix_batch} (fill 'new' to correct, then push)")

    return 1 if counts["error"] else 0


def cmd_push(args) -> int:
    batch = json.loads(Path(args.batch).read_text())
    summary = args.summary or batch["meta"].get("summary") or DEFAULT_SUMMARY
    pending = [
        m
        for m in batch["messages"]
        if m.get("new", "").strip()
        and (args.include_unchanged or strip_fuzzy(m["new"]) != m.get("current", ""))
    ]
    confirms = [m for m in pending if strip_fuzzy(m["new"]) == m.get("current", "")]
    if args.key:
        pattern = re.compile(args.key)
        pending = [m for m in pending if pattern.search(m["key"])]
    if args.resume:
        already = sum(1 for m in pending if m.get("pushed"))
        pending = [m for m in pending if not m.get("pushed")]
        if already:
            print(f"--resume: {already} bereits gepusht, wird übersprungen")
    if not pending:
        print("nothing to push — no message has a 'new' value differing from 'current'")
        return 0

    glossary = load_glossary()
    blocked = []
    for m in pending:
        errors = [
            f for f in qa_message(m["definition"], m["new"], m["key"], glossary, m.get("platform", "android"))
            if f[0] == "error"
        ]
        if errors:
            blocked.append((m, errors))
    if blocked and not args.ignore_qa:
        print(f"{len(blocked)} message(s) fail QA — fix them or pass --ignore-qa:\n", file=sys.stderr)
        for m, errors in blocked:
            print(f"  {m['key']}", file=sys.stderr)
            for _, code, detail in errors:
                print(f"    {code}: {detail}", file=sys.stderr)
        return 1

    print(f"{len(pending)} message(s) to save · summary: {summary}")
    if confirms:
        print(f"  ({len(confirms)} of them unchanged — saved only to clear the fuzzy flag)")
    if not args.confirm:
        for m in pending[: args.preview]:
            print(f"\n  {m['key']}")
            print(f"    en:  {m['definition']}")
            if m.get("current"):
                print(f"    old: {m['current']}")
            if strip_fuzzy(m["new"]) == m.get("current", ""):
                print("    new: (unverändert — bestätigt nur den Fuzzy-Status)")
            else:
                print(f"    new: {strip_fuzzy(m['new'])}")
        if len(pending) > args.preview:
            print(f"\n  … and {len(pending) - args.preview} more")
        print("\nDRY RUN — nothing saved. Re-run with --confirm to write these edits.")
        return 0

    client = connect()
    info = client.userinfo()
    if "translate" not in info.get("rights", []):
        print("account lacks the 'translate' right", file=sys.stderr)
        return 1

    def checkpoint() -> None:
        Path(args.batch).write_text(json.dumps(batch, ensure_ascii=False, indent=2))

    saved, failed = 0, []
    try:
        for i, m in enumerate(pending, 1):
            text = strip_fuzzy(m["new"])
            try:
                result = client.save_or_create(m["title"], text, summary)
                state = result.get("result", "?")
                if result.get("nochange") is not None:
                    state = "nochange"
                saved += 1
                print(f"  [{i}/{len(pending)}] {state:8s} {m['key']}", flush=True)
                m["pushed"] = True
            except TwnError as exc:
                failed.append((m["key"], str(exc)))
                print(f"  [{i}/{len(pending)}] FAILED   {m['key']}: {exc}", file=sys.stderr, flush=True)
            # Checkpoint every edit: an interrupted run must never lose track of what
            # already went out, or the resume re-saves edits that are already public.
            checkpoint()
            time.sleep(args.throttle)
    except (KeyboardInterrupt, Exception):
        checkpoint()
        print(f"\nabgebrochen nach {saved} gespeicherten Edits — Fortschritt in {args.batch}",
              file=sys.stderr)
        raise

    checkpoint()
    print(f"\nsaved {saved}/{len(pending)}" + (f", {len(failed)} failed" if failed else ""))
    return 1 if failed else 0


# --------------------------------------------------------------------------- #
# terminology reconnaissance
# --------------------------------------------------------------------------- #


def cmd_term(args) -> int:
    """Report how an English term is translated, split by platform.

    The Wikipedia apps are two independent string sets that can rename a concept
    at different times — in 2025 Android renamed "reading list" to "collection"
    while iOS did not. A sweep planned without checking that split silently pushes
    German ahead of one platform's source, so this runs before any term decision.
    """
    client = connect(anonymous=True)
    messages = client.collection(GROUPS[args.platform], args.language, FILTERS[args.filter])

    en_re = re.compile(re.escape(args.en), re.I) if args.en else None
    de_re = re.compile(re.escape(args.de), re.I) if args.de else None
    if not en_re and not de_re:
        print("give --en and/or --de", file=sys.stderr)
        return 1

    def bucket(rows: list, label: str, other_re, other_label: str) -> None:
        if not rows:
            print(f"\n{label}: keine Treffer")
            return
        print(f"\n{label}: {len(rows)} Treffer")
        by_platform = {}
        for m in rows:
            by_platform.setdefault(platform_of(m), []).append(m)
        for plat in sorted(by_platform):
            sub = by_platform[plat]
            hits = sum(1 for m in sub if other_re and other_re.search(m["_other"] or ""))
            extra = f" · davon {hits} mit „{other_label}“ auf der anderen Seite" if other_re else ""
            print(f"  {plat:8s} {len(sub):4d}{extra}")
        if other_re:
            missing = [m for m in rows if not other_re.search(m["_other"] or "")]
            if missing:
                print(f"  ⚠ {len(missing)} ohne „{other_label}“ — Quelle und Übersetzung laufen auseinander:")
                for m in missing[: args.examples]:
                    print(f"      {m['key'].split('-strings-')[-1][:48]:50s} {(m['_other'] or '')[:60]}")
                if len(missing) > args.examples:
                    print(f"      … und {len(missing) - args.examples} weitere")

    if en_re:
        rows = []
        for m in messages:
            if en_re.search(m.get("definition") or ""):
                rows.append(dict(m, _other=strip_fuzzy(m.get("translation"))))
        bucket(rows, f"EN „{args.en}“", de_re, args.de or "")
    if de_re:
        rows = []
        for m in messages:
            if de_re.search(strip_fuzzy(m.get("translation"))):
                rows.append(dict(m, _other=m.get("definition")))
        bucket(rows, f"DE „{args.de}“", en_re, args.en or "")
    return 0


# --------------------------------------------------------------------------- #
# mechanical term sweep
# --------------------------------------------------------------------------- #


def cmd_sweep(args) -> int:
    """Apply ordered literal replacements to a batch, for review via `diff`.

    Deliberately dumb: it does not know German morphology. List the longest form
    first (Leselisten before Leseliste), protect literals that must survive
    (export filenames, anchors), and proofread the result in the diff view.
    """
    batch = json.loads(Path(args.batch).read_text())
    pairs = []
    for spec in args.replace:
        if "=>" not in spec:
            print(f"--replace needs 'alt=>neu', got {spec!r}", file=sys.stderr)
            return 1
        old, new = spec.split("=>", 1)
        pairs.append((old, new))
    protect = [re.compile(p) for p in (args.protect or [])]
    where_de = re.compile(args.where_de) if args.where_de else None

    def apply(text: str) -> str:
        shields = []

        def stash(match):
            shields.append(match.group(0))
            return f"\x00{len(shields) - 1}\x00"

        for pat in protect:
            text = pat.sub(stash, text)
        for old, new in pairs:
            text = text.replace(old, new)
        for i, original in enumerate(shields):
            text = text.replace(f"\x00{i}\x00", original)
        return text

    touched, skipped = 0, 0
    for m in batch["messages"]:
        base = m.get("new") or m.get("current") or ""
        if where_de and not where_de.search(base):
            skipped += 1
            continue
        result = apply(base)
        if result != m.get("current"):
            m["new"] = result
            if args.note and not m.get("note"):
                m["note"] = args.note
            touched += 1

    out = Path(args.out or args.batch)
    out.write_text(json.dumps(batch, ensure_ascii=False, indent=2))
    print(f"{touched} Nachricht(en) geändert → {out}" + (f" ({skipped} übersprungen)" if skipped else ""))
    print("Jetzt proofreaden:  twn.py diff " + str(out) + " --out review.html")
    return 0


# --------------------------------------------------------------------------- #
# review diff
# --------------------------------------------------------------------------- #


def _tokens(text: str) -> list:
    return re.findall(r"\w+|\W", text or "", flags=re.UNICODE)


def word_diff(old: str, new: str, fmt: str = "html") -> tuple:
    """Word-level diff of two strings, returned as (old_markup, new_markup)."""
    import difflib

    a, b = _tokens(old), _tokens(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    wrap = {
        "html": ("<del>%s</del>", "<ins>%s</ins>", lambda s: esc(s)),
        "md": ("~~%s~~", "**%s**", lambda s: s),
    }[fmt]
    del_fmt, ins_fmt, enc = wrap
    out_old, out_new = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        seg_a, seg_b = "".join(a[i1:i2]), "".join(b[j1:j2])
        if tag in ("equal",):
            out_old.append(enc(seg_a))
            out_new.append(enc(seg_b))
            continue
        if seg_a:
            out_old.append(del_fmt % enc(seg_a))
        if seg_b:
            out_new.append(ins_fmt % enc(seg_b))
    return "".join(out_old), "".join(out_new)


def esc(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


REVIEW_CSS = """
:root{--bg:#fbfbfa;--panel:#fff;--ink:#1a1a18;--muted:#6b6b66;--line:#e4e4e0;
--del-bg:#ffe3e3;--del-ink:#8a1c1c;--ins-bg:#d8f3df;--ins-ink:#11562c;
--badge:#eeeeea;--note:#fff6e0;--note-line:#e8c96a;--warn:#8a5a00;--err:#a11;--accent:#3a5bbf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
--bg:#16161a;--panel:#1e1e23;--ink:#e9e9e6;--muted:#9b9b95;--line:#33333a;
--del-bg:#4a1f22;--del-ink:#ffb3b3;--ins-bg:#17402a;--ins-ink:#a8e6bf;
--badge:#2c2c33;--note:#3a3018;--note-line:#8a7333;--warn:#e8be6a;--err:#ff8f8f;--accent:#8fa8ff}}
:root[data-theme="dark"]{--bg:#16161a;--panel:#1e1e23;--ink:#e9e9e6;--muted:#9b9b95;--line:#33333a;
--del-bg:#4a1f22;--del-ink:#ffb3b3;--ins-bg:#17402a;--ins-ink:#a8e6bf;
--badge:#2c2c33;--note:#3a3018;--note-line:#8a7333;--warn:#e8be6a;--err:#ff8f8f;--accent:#8fa8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:400 16px/1.55 "IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
-webkit-font-smoothing:antialiased}
.wrap{max-width:62rem;margin:0 auto;padding:1.5rem 1rem 5rem}
h1{font-size:1.4rem;font-weight:600;letter-spacing:-.01em;margin:0 0 .2rem;text-wrap:balance}
.sub{color:var(--muted);font-size:.88rem;margin-bottom:1.2rem;font-variant-numeric:tabular-nums}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);
padding:.7rem 0;margin-bottom:1.2rem;display:flex;gap:.4rem;flex-wrap:wrap;align-items:center}
button{font:inherit;font-size:.82rem;padding:.32rem .8rem;border:1px solid var(--line);
border-radius:99px;background:var(--panel);color:var(--ink);cursor:pointer}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.card{background:var(--panel);border:1px solid var(--line);border-radius:9px;
padding:.85rem 1rem;margin-bottom:.8rem}
.head{display:flex;gap:.5rem;align-items:baseline;flex-wrap:wrap;margin-bottom:.6rem}
.key{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.8rem;
word-break:break-all;color:var(--ink)}
.badge{font-size:.68rem;text-transform:uppercase;letter-spacing:.04em;background:var(--badge);
color:var(--muted);padding:.1rem .45rem;border-radius:4px;white-space:nowrap}
.row{display:grid;grid-template-columns:3.2rem 1fr;gap:.5rem;margin:.25rem 0;font-size:.93rem}
.lbl{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
padding-top:.2rem}
.txt{white-space:pre-wrap;overflow-wrap:anywhere}
.en{color:var(--muted)}
del{background:var(--del-bg);color:var(--del-ink);text-decoration:none;border-radius:3px;padding:0 .1em}
ins{background:var(--ins-bg);color:var(--ins-ink);text-decoration:none;border-radius:3px;padding:0 .1em}
.qqq{color:var(--muted);font-size:.82rem;font-style:italic;margin-top:.5rem}
.note{background:var(--note);border-left:3px solid var(--note-line);padding:.4rem .6rem;
margin-top:.55rem;font-size:.86rem;border-radius:0 4px 4px 0}
.finding{font-size:.8rem;margin-top:.4rem;
font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
.finding.warn{color:var(--warn)}.finding.error{color:var(--err)}
.empty{color:var(--muted);font-style:italic}
"""

REVIEW_JS = """
const cards=[...document.querySelectorAll('.card')];
const btns=[...document.querySelectorAll('.bar button')];
function show(f){
  cards.forEach(c=>{c.style.display = f==='all'||c.dataset[f]==='1' ? '' : 'none';});
  btns.forEach(b=>b.setAttribute('aria-pressed', String(b.dataset.f===f)));
}
btns.forEach(b=>b.onclick=()=>show(b.dataset.f));
show('changed');
"""


def cmd_diff(args) -> int:
    """Render a batch as a proofreadable review page."""
    glossary = load_glossary()
    paths = [Path(p) for p in args.batch]
    label = " + ".join(p.name for p in paths)
    messages = []
    for p in paths:
        for m in json.loads(p.read_text())["messages"]:
            messages.append(dict(m, _batch=p.stem))
    if args.key:
        pattern = re.compile(args.key)
        messages = [m for m in messages if pattern.search(m["key"])]

    rows = []
    for m in messages:
        new, current = m.get("new") or "", m.get("current") or ""
        changed = bool(new) and new != current
        findings = []
        if new:
            findings = [
                f for f in qa_message(m.get("definition") or "", new, m["key"], glossary,
                                      m.get("platform", "android"))
                if f[0] != "info"
            ]
        rows.append({"m": m, "new": new, "current": current, "changed": changed,
                     "findings": findings})

    counts = {
        "total": len(rows),
        "changed": sum(1 for r in rows if r["changed"]),
        "open": sum(1 for r in rows if not r["new"]),
        "notes": sum(1 for r in rows if r["m"].get("note")),
        "errors": sum(1 for r in rows if any(f[0] == "error" for f in r["findings"])),
        "warnings": sum(1 for r in rows if any(f[0] == "warn" for f in r["findings"])),
    }

    if args.format == "md":
        out = [f"# Übersetzungsreview — {label}", ""]
        out.append(f"{counts['total']} Nachrichten · {counts['changed']} geändert · "
                   f"{counts['open']} offen · {counts['errors']} Fehler · {counts['warnings']} Warnungen")
        for r in rows:
            m = r["m"]
            if args.only_changed and not r["changed"]:
                continue
            out += ["", f"### `{m['key']}`", "", f"- **EN:** {m.get('definition')}"]
            if m.get("english_was"):
                ew, en_ = word_diff(m["english_was"], m.get("english_now") or "", "md")
                out += [f"- **EN war:** {ew}", f"- **EN neu:** {en_}"]
            if r["current"]:
                old_md, new_md = word_diff(r["current"], r["new"], "md")
                out += [f"- **DE alt:** {old_md}", f"- **DE neu:** {new_md}"]
            elif r["new"]:
                out.append(f"- **DE neu:** {r['new']}")
            else:
                out.append("- **DE:** _offen_")
            if m.get("note"):
                out.append(f"- **Notiz:** {m['note']}")
            for level, code, detail in r["findings"]:
                out.append(f"- **{level.upper()} {code}:** {detail}")
        text = "\n".join(out) + "\n"
    else:
        cards = []
        for r in rows:
            m = r["m"]
            flags = {
                "changed": "1" if r["changed"] else "0",
                "note": "1" if m.get("note") else "0",
                "finding": "1" if r["findings"] else "0",
                "open": "1" if not r["new"] else "0",
            }
            attrs = " ".join(f'data-{k}="{v}"' for k, v in flags.items())
            parts = [f"<div class='card' {attrs}>"]
            parts.append(
                "<div class='head'><span class='key'>%s</span>"
                "<span class='badge'>%s</span><span class='badge'>%s</span>"
                "<span class='badge'>%s</span></div>"
                % (esc(m["key"]), esc(m.get("platform") or "?"),
                   esc(m.get("status") or "neu"), esc(m.get("_batch") or ""))
            )
            if m.get("english_was"):
                ew, en_ = word_diff(m["english_was"], m.get("english_now") or "")
                parts.append(f"<div class='row'><span class='lbl'>EN war</span><span class='txt en'>{ew}</span></div>")
                parts.append(f"<div class='row'><span class='lbl'>EN neu</span><span class='txt en'>{en_}</span></div>")
            else:
                parts.append(
                    f"<div class='row'><span class='lbl'>EN</span>"
                    f"<span class='txt en'>{esc(m.get('definition'))}</span></div>"
                )
            if r["current"] and r["new"]:
                old_h, new_h = word_diff(r["current"], r["new"])
                parts.append(f"<div class='row'><span class='lbl'>DE alt</span><span class='txt'>{old_h}</span></div>")
                parts.append(f"<div class='row'><span class='lbl'>DE neu</span><span class='txt'>{new_h}</span></div>")
            elif r["new"]:
                parts.append(
                    f"<div class='row'><span class='lbl'>DE</span>"
                    f"<span class='txt'><ins>{esc(r['new'])}</ins></span></div>"
                )
            else:
                parts.append(
                    f"<div class='row'><span class='lbl'>DE</span>"
                    f"<span class='txt empty'>offen — nicht übersetzt</span></div>"
                )
                if r["current"]:
                    parts.append(
                        f"<div class='row'><span class='lbl'>bisher</span>"
                        f"<span class='txt'>{esc(r['current'])}</span></div>"
                    )
            if m.get("documentation") and args.qqq:
                parts.append(f"<div class='qqq'>{esc(m['documentation'])}</div>")
            if m.get("note"):
                parts.append(f"<div class='note'>{esc(m['note'])}</div>")
            for level, code, detail in r["findings"]:
                parts.append(f"<div class='finding {esc(level)}'>{esc(level.upper())} {esc(code)}: {esc(detail)}</div>")
            parts.append("</div>")
            cards.append("".join(parts))

        body = (
            "<div class='wrap'><h1>Übersetzungsreview</h1>"
            f"<div class='sub'>{esc(label)} · {counts['total']} Nachrichten · "
            f"{counts['changed']} geändert · {counts['open']} offen · "
            f"{counts['errors']} Fehler · {counts['warnings']} Warnungen</div>"
            "<div class='bar'>"
            "<button data-f='changed'>Geändert</button>"
            "<button data-f='all'>Alle</button>"
            "<button data-f='note'>Mit Notiz</button>"
            "<button data-f='finding'>Mit QA-Befund</button>"
            "<button data-f='open'>Offen</button>"
            "</div>" + "".join(cards) + "</div>"
        )
        fonts = (
            "<link rel='preconnect' href='https://fonts.googleapis.com'>"
            "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            "<link rel='stylesheet' href='https://fonts.googleapis.com/css2?"
            "family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap'>"
        )
        head = fonts + f"<style>{REVIEW_CSS}</style>"
        tail = f"<script>{REVIEW_JS}</script>"
        title = args.title or f"Übersetzungsreview — {label}"
        if args.fragment:
            text = f"<title>{esc(title)}</title>{head}{body}{tail}"
        else:
            text = (
                "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                f"<title>{esc(title)}</title>{head}</head>"
                f"<body>{body}{tail}</body></html>"
            )

    if args.out:
        Path(args.out).write_text(text)
        print(f"{counts['total']} Nachricht(en) → {args.out}")
        print(f"  {counts['changed']} geändert · {counts['open']} offen · "
              f"{counts['errors']} Fehler · {counts['warnings']} Warnungen")
    else:
        print(text)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="twn.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("auth", help="verify credentials").set_defaults(func=cmd_auth)

    p_status = sub.add_parser("status", help="backlog counts")
    p_status.add_argument("--language", default="de")
    p_status.set_defaults(func=cmd_status)

    p_pull = sub.add_parser("pull", help="fetch a work batch")
    p_pull.add_argument("--platform", choices=list(GROUPS), default="all")
    p_pull.add_argument("--filter", choices=list(FILTERS), default="todo")
    p_pull.add_argument("--language", default="de")
    p_pull.add_argument("--limit", type=int, default=0)
    p_pull.add_argument("--key", help="regex to restrict keys")
    p_pull.add_argument("--out", default="batch.json")
    p_pull.add_argument("--no-diff", action="store_true", help="skip per-message English diffs (faster)")
    p_pull.add_argument("--summary", default=DEFAULT_SUMMARY)
    p_pull.add_argument("--verbose", action="store_true")
    p_pull.set_defaults(func=cmd_pull)

    p_qa = sub.add_parser("qa", help="quality checks")
    p_qa.add_argument("batch", nargs="?", help="batch file; omit to QA the live wiki")
    p_qa.add_argument("--platform", choices=list(GROUPS), default="all")
    p_qa.add_argument("--filter", choices=list(FILTERS), default="done")
    p_qa.add_argument("--language", default="de")
    p_qa.add_argument("--only-new", action="store_true", help="batch mode: check proposed translations only")
    p_qa.add_argument("--errors-only", action="store_true")
    p_qa.add_argument("--json", action="store_true")
    p_qa.add_argument("--fix-batch", metavar="FILE", help="live mode: write flagged messages as a batch to correct")
    p_qa.add_argument("--verbose", action="store_true", help="include info-level findings")
    p_qa.set_defaults(func=cmd_qa)

    p_push = sub.add_parser("push", help="save a reviewed batch")
    p_push.add_argument("batch")
    p_push.add_argument("--confirm", action="store_true", help="actually write (default is a dry run)")
    p_push.add_argument("--summary")
    p_push.add_argument("--key", help="regex to restrict keys")
    p_push.add_argument("--throttle", type=float, default=2.0, help="seconds between edits")
    p_push.add_argument("--preview", type=int, default=10)
    p_push.add_argument("--ignore-qa", action="store_true")
    p_push.add_argument("--resume", action="store_true",
                        help="skip entries already marked \"pushed\" by an earlier interrupted run")
    p_push.add_argument(
        "--include-unchanged",
        action="store_true",
        help="also save entries whose text equals the current translation — this is how a fuzzy "
        "string gets confirmed when the English change did not affect the German",
    )
    p_push.set_defaults(func=cmd_push)

    p_diff = sub.add_parser("diff", help="render a batch as a proofreadable review page")
    p_diff.add_argument("batch", nargs="+", help="one or more batch files")
    p_diff.add_argument("--out", help="write to this file (default: stdout)")
    p_diff.add_argument("--format", choices=("html", "md"), default="html")
    p_diff.add_argument("--key", help="regex to restrict keys")
    p_diff.add_argument("--only-changed", action="store_true", help="md only: skip unchanged entries")
    p_diff.add_argument("--qqq", action="store_true", help="include the qqq documentation")
    p_diff.add_argument("--title", help="page title (default: Übersetzungsreview — <batch names>)")
    p_diff.add_argument("--fragment", action="store_true", help="emit page content only, for publishing as an Artifact")
    p_diff.set_defaults(func=cmd_diff)

    p_term = sub.add_parser("term", help="how a term is used, split by platform")
    p_term.add_argument("--en", help="English term to look up")
    p_term.add_argument("--de", help="German term to look up")
    p_term.add_argument("--platform", choices=list(GROUPS), default="all")
    p_term.add_argument("--filter", choices=list(FILTERS), default="all")
    p_term.add_argument("--language", default="de")
    p_term.add_argument("--examples", type=int, default=8)
    p_term.set_defaults(func=cmd_term)

    p_sweep = sub.add_parser("sweep", help="apply ordered literal replacements to a batch")
    p_sweep.add_argument("batch")
    p_sweep.add_argument("--replace", action="append", required=True, metavar="ALT=>NEU",
                         help="repeatable, applied in order — list the longest form first")
    p_sweep.add_argument("--protect", action="append", metavar="REGEX",
                         help="repeatable; matches are shielded from replacement (filenames, anchors)")
    p_sweep.add_argument("--where-de", metavar="REGEX", help="only touch messages whose German matches")
    p_sweep.add_argument("--note", help="note to attach to every swept message")
    p_sweep.add_argument("--out", help="write here instead of in place")
    p_sweep.set_defaults(func=cmd_sweep)

    args = parser.parse_args()
    try:
        return args.func(args)
    except TwnError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

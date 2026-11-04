"""Dictionary-based skill extraction and matching. Pure functions: no DB, no LLM, no network."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

DICT_PATH = Path(__file__).with_name("skills.yaml")
REQ_WEIGHT, NICE_WEIGHT = 2, 1          # a missing required skill costs twice a nice-to-have

_BULLET = re.compile(r"^[\s\-•‣●▪\*–—·>]+")
_Q = r"['’]"

# Section headings. A line is a heading if it STARTS with one of these and is short
# (<= 70 chars) or has a colon right after it ("Nice to have: Kubernetes").
NICE_HEAD = re.compile(r"(?:nice[- ]to[- ]haves?|bonus(?: points)?|preferred(?: qualifications?| skills)?"
                       r"|good to have|desirable|extra credit|pluses)\b", re.I)
REQ_HEAD = re.compile(rf"(?:requirements?|qualifications?|(?:basic|minimum|key|required) (?:qualifications?|requirements?|skills)"
                      rf"|what (?:we{_Q}re looking for|you{_Q}ll need|you need|you bring|you have)"
                      rf"|must[- ]haves?|who you are|about you|your profile|you have|skills(?: (?:and|&) experience)?)\b", re.I)
RESP_HEAD = re.compile(rf"(?:responsibilities|what you{_Q}ll do|what you will do|the role|your role"
                       rf"|key responsibilities|day[- ]to[- ]day|in this role)\b", re.I)
SKIP_HEAD = re.compile(r"(?:about (?:us|the company|the team)|who we are|benefits?|perks|why join"
                       r"|what we offer|compensation|equal opportunity|our (?:mission|values|culture))\b", re.I)
# A single line that says "nice to have" about itself, whatever section it sits in.
NICE_INLINE = re.compile(r"nice[- ]to[- ]have|\bbonus\b|\bpreferred\b|\ba plus\b|good to have|\bdesirable\b|not required", re.I)

_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:(?:-|–|to)\s*\d{1,2}\s*)?(?:years?|yrs?)\b", re.I)


@lru_cache(maxsize=1)
def _skills() -> dict[str, list[re.Pattern]]:
    raw = yaml.safe_load(DICT_PATH.read_text(encoding="utf-8"))
    out: dict[str, list[re.Pattern]] = {}
    for name, aliases in raw.items():
        ci = [a for a in aliases if a == a.lower()]      # lowercase -> case-insensitive
        cs = [a for a in aliases if a != a.lower()]      # has a capital -> exact casing only
        pats = []
        for group, flags in ((ci, re.I), (cs, 0)):
            if group:
                body = "|".join(re.escape(a) for a in sorted(group, key=len, reverse=True))
                # not glued to word chars, '+', '#' or '.', so "java" != "javascript", "js" != "node.js"
                pats.append(re.compile(r"(?<![\w+#.])(?:" + body + r")(?![\w+#])", flags))
        out[name] = pats
    return out


def all_skill_names() -> list[str]:
    return sorted(_skills())


def canonical(name: str) -> str | None:
    """Case-insensitive lookup of a display name ('postgresql' -> 'PostgreSQL')."""
    low = name.strip().lower()
    return next((n for n in _skills() if n.lower() == low), None)


def find_skills(text: str) -> set[str]:
    return {name for name, pats in _skills().items() if any(p.search(text) for p in pats)}


def _lines(text: str) -> list[str]:
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if len(line) > 400:   # a wall of text: split into sentences so cues stay local
            out += [s.strip() for s in re.split(r"(?<=[.;!?])\s+", line) if s.strip()]
        else:
            out.append(line)
    return out


def extract(description: str) -> tuple[set[str], set[str]]:
    """Returns (required, nice_to_have). Outside any recognised section, skills count as required."""
    req: set[str] = set()
    nice: set[str] = set()
    mode = "required"
    for line in _lines(description):
        body = _BULLET.sub("", line)
        for kind, rx in (("nice", NICE_HEAD), ("required", REQ_HEAD),
                         ("skip", SKIP_HEAD), ("required", RESP_HEAD)):
            m = rx.match(body)
            if m and (len(body) <= 70 or body[m.end():].lstrip().startswith(":")):
                mode = kind
                break
        if mode == "skip":
            continue
        found = find_skills(body)
        if not found:
            continue
        if mode == "nice" or NICE_INLINE.search(body):
            nice |= found
        else:
            req |= found
    return req, nice - req       # required wins if a skill shows up in both


def min_years(description: str) -> int | None:
    """Smallest 'N years' figure on a line that mentions experience. None if there is none."""
    best = None
    for line in _lines(description):
        if not re.search(r"experience|\bexp\b", line, re.I):
            continue
        for m in _YEARS.finditer(line):
            n = int(m.group(1))
            if n <= 20:
                best = n if best is None else min(best, n)
    return best


def analyze(description: str, profile: set[str]) -> dict:
    """Match % (None when the posting names no known skills), plus which skills you have/lack."""
    req, nice = extract(description)
    have = set(profile)
    total = REQ_WEIGHT * len(req) + NICE_WEIGHT * len(nice)
    got = REQ_WEIGHT * len(req & have) + NICE_WEIGHT * len(nice & have)
    return {
        "pct": None if total == 0 else round(got / total, 3),
        "min_years": min_years(description),
        "skills": {
            "req_matched": sorted(req & have), "req_missing": sorted(req - have),
            "nice_matched": sorted(nice & have), "nice_missing": sorted(nice - have),
        },
    }

"""Small text helpers shared by the skills (stdlib only)."""
import re
from datetime import date, timedelta

STOP = set("the a an and or of to in on for with by is are was were be as at from that this it its not no than then which who whom their there "
           "any all may must should will shall can could would also into per such other these those has have had been being if when while where".split())


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", str(text).lower()) if t not in STOP and len(t) > 1]


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s).lower()).split())


def jaccard(a, b):
    ta, tb = set(tokens(a)), set(tokens(b))
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def to_date(s):
    return date.fromisoformat(s) if s else None


def iso(d):
    return d.isoformat() if d else None


def add_days(d, n):
    return d + timedelta(days=n)


def numbered(text):
    """[(1-based line number, line)]"""
    return list(enumerate(text.splitlines(), 1))


def excerpt(line, n=160):
    line = " ".join(line.split())
    return line if len(line) <= n else line[:n - 1] + "…"


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def date_variants(iso_date):
    """Common written forms of an ISO date."""
    d = date.fromisoformat(iso_date)
    m = MONTHS[d.month - 1]
    return {iso_date, f"{m} {d.day}, {d.year}", f"{m[:3]} {d.day}, {d.year}", f"{d.month}/{d.day}/{d.year}", f"{d.month:02d}/{d.day:02d}/{d.year}", f"{d.day} {m} {d.year}"}


def mentions_date(text, iso_date):
    return any(v in text for v in date_variants(iso_date))

"""pull_clinical_notes: list (and, only when asked, return) the clinical notes and supporting documents of a case, within a date range.
Minimum necessary: metadata first; full text only for include_text=true or for explicitly requested paths. Every file read is logged."""
import re

from pydantic import BaseModel

from skills.common.io import SkillError, SkillInput
from skills.common.text import to_date
from skills.parse_denial_eob.tool import parse_task

NAME = re.compile(r"^(?:notes/)?(\d{4}-\d{2}-\d{2})_(.+)\.txt$")


class Input(SkillInput):
    date_from: str | None = None       # inclusive; default: no lower bound
    date_to: str | None = None         # inclusive; default: the review date in task.md
    include_text: bool = False         # return full text for every document in range (use sparingly)
    paths: list[str] = []              # fetch these documents (relative to docs/, e.g. 'notes/2026-03-23_pcp.txt') with full text
    include_undated: bool = True       # supporting documents have no date in their file name


class Output(BaseModel):
    as_of_date: str | None
    date_from: str | None
    date_to: str | None
    documents: list[dict]
    n_excluded_by_date: int
    reason: str | None


def run_tool(inp, ctx):
    files = [f for f in ctx.guard.list_files("case", "docs") if f.startswith("docs/notes/") or f.startswith("docs/supporting/")]
    as_of = None
    try:
        as_of = parse_task(ctx.read("case", "task.md")).get("as_of")
    except FileNotFoundError:
        pass
    date_to = inp.date_to or as_of
    if not files:
        return Output(as_of_date=as_of, date_from=inp.date_from, date_to=date_to, documents=[], n_excluded_by_date=0,
                      reason="this case file contains no clinical notes or supporting documents")
    want = None
    if inp.paths:
        want = []
        for p in inp.paths:
            rel = p if p.startswith("docs/") else f"docs/{p}"
            ctx.guard.resolve("case", rel)            # raises on forbidden / outside paths
            if rel not in files:
                raise SkillError("not_found", f"{p!r} is not a clinical note or supporting document of this case")
            want.append(rel)
    docs, excluded = [], 0
    for f in files:
        if want is not None and f not in want:
            continue
        rel = f[len("docs/"):]
        m = NAME.match(rel.split("/", 1)[1] if rel.startswith("supporting/") else rel)
        date = m.group(1) if m and rel.startswith("notes/") else None
        if want is None:
            if date is None and not inp.include_undated:
                continue
            if date and ((inp.date_from and date < inp.date_from) or (date_to and date > date_to)):
                excluded += 1
                continue
        text = ctx.read("case", f)
        lines = text.splitlines()
        title = (lines[1] if rel.startswith("notes/") and len(lines) > 1 else lines[0]).strip() if lines else ""
        doc = {"path": rel, "kind": (m.group(2) if m else rel.rsplit("/", 1)[-1][:-4]), "folder": rel.split("/")[0], "date": date,
               "date_source": "file name" if date else None,
               "date_reason": None if date else "supporting documents carry no date in their file name", "title": title,
               "chars": len(text), "lines": len(lines)}
        if want is not None or inp.include_text:
            doc["text"] = text
        docs.append(doc)
    docs.sort(key=lambda d: (d["date"] or "9999-99-99", d["path"]))
    return Output(as_of_date=as_of, date_from=inp.date_from, date_to=date_to, documents=docs, n_excluded_by_date=excluded,
                  reason=None if docs else "no documents in the requested range")

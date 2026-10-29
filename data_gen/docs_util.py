"""Helpers shared by the renderers and validate_data: locate fact text in rendered documents."""
from pathlib import Path

from data_gen.schema import Fact

# Facts whose value is not a literal string in the source document.
NON_LITERAL_KEYS = {"missing_docs", "post_dos_note", "authoritative_duration_source", "planned_document",
                    "missing_field", "no_prior_imaging_record", "correct_fix"}
SYNTHETIC_FOOTER = "SYNTHETIC DATA - NOT REAL PHI"


def case_dir(root, case_id):
    return Path(root) / "cases" / case_id


def source_path(root, case_id, source):
    """Path of a fact's source file, or None for the shared policy library."""
    if source == "policy_library":
        return None
    base = case_dir(root, case_id)
    return base / source if source == "task.md" else base / "docs" / source


def needle(fact):
    """The text that must appear verbatim in the source doc for this fact (None = not checkable literally)."""
    if fact.evidence:
        return fact.evidence
    v = fact.value
    if fact.key in NON_LITERAL_KEYS or isinstance(v, bool):
        return None
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, list):
        return ", ".join(v)
    return str(v)


def locate(text, fact):
    """1-based line where the fact's needle starts (whitespace-insensitive; needles may span lines), else None."""
    n = needle(fact)
    if n is None:
        return None
    lines, k, want = text.splitlines(), n.count("\n") + 1, " ".join(n.split())
    for i in range(len(lines)):
        if want in " ".join(" ".join(lines[i:i + k]).split()):
            return i + 1
    return None


def fill_lines(root, truth):
    """Set fact.line for every fact whose source doc exists on disk. Returns (n_set, [unlocated fact keys])."""
    n, missing = 0, []
    for f in truth.facts:
        p = source_path(root, truth.case_id, f.source_file)
        if p is None or not p.exists() or needle(f) is None:
            continue
        ln = locate(p.read_text(), f)
        f.line = ln
        if ln is None:
            missing.append(f.key)
        else:
            n += 1
    return n, missing


def set_fact(truth, key, source, quote):
    """Attach a verbatim evidence quote to an existing fact (same key+source) or append a new quote fact. Idempotent."""
    for f in truth.facts:
        if f.key == key and f.source_file == source and (not key.startswith("criterion_") or f.evidence in (None, quote)):
            f.evidence = quote
            return
    truth.facts.append(Fact(key=key, value=quote, source_file=source, evidence=quote))

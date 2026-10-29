"""Lint for LLM-written clinical notes: (1) deterministic spellcheck with a clinical word list; (2) a second-pass review by a
NON-datagen reviewer model that flags nonsense phrasing. The spellcheck also runs inside validate_data (no LLM there)."""
import json
import re
from pathlib import Path

from spellchecker import SpellChecker

from data_gen.llm import ROOT, ask_reviewer  # noqa: F401  (ask_reviewer defined in llm.py)

_SPELL = None
RULE = "-" * 60
WORD = re.compile(r"[A-Za-z][a-z]{2,}")


def _checker():
    global _SPELL
    if _SPELL is None:
        _SPELL = SpellChecker()
        words = [w for line in (Path(__file__).parent / "medical_words.txt").read_text().splitlines()
                 if not line.startswith("#") for w in line.split()]
        _SPELL.word_frequency.load_words(words)
    return _SPELL


def note_body(text):
    """Text between the two rules of a rendered note (the part the LLM wrote)."""
    parts = text.split(RULE)
    return parts[1] if len(parts) >= 3 else text


def spell_issues(body):
    """Words not in the English or clinical word lists, with a suggested fix. Capitalised mid-sentence names are not expected in bodies."""
    sp = _checker()
    out = []
    for w in dict.fromkeys(WORD.findall(body)):
        if w.lower() not in sp:
            out.append({"word": w, "suggestion": sp.correction(w.lower())})
    return out


REVIEW_PROMPT = """You are copy-editing a SYNTHETIC outpatient clinical note. Flag ONLY (a) nonsensical, garbled or ungrammatical phrasing that no clinician would write, (b) clinically impossible or self-contradictory statements, (c) sentences that read like billing or system text instead of charting. Do NOT flag style, brevity, or missing detail. If the note is acceptable, return an empty list.

Respond with ONE JSON object: {{"issues": [{{"quote": "exact text", "problem": "..."}}]}}

NOTE ({kind}):
{body}
"""


def reviewer_issues(cfg, kind, body):
    text = ask_reviewer(cfg, REVIEW_PROMPT.format(kind=kind, body=body))
    m = re.search(r"\{.*\}", text, re.S)
    try:
        return json.loads(m.group(0)).get("issues", []) if m else [{"quote": "", "problem": "reviewer output not parseable"}]
    except ValueError:
        return [{"quote": "", "problem": "reviewer output not parseable"}]

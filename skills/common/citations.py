"""Citation verification shared by draft_deliverable.verify_citations and self_check.
Checks that every cited source (file, file:line, quoted text) exists in the case documents or the policy library and that every cited
policy id / section id exists. Per-citation pass/fail with a reason."""
import re

from skills.common.policies import load_policies
from skills.common.text import norm

GENERIC_SOURCES = {"task", "task.md", "governing policy", "policy", "policy library", "the policy", "denial letter", "eob", "remit"}
SRC = re.compile(r"\(\s*sources?:\s*([^)]+)\)", re.I)
FILE = re.compile(r"\b((?:notes|supporting)/[\w\-.]+\.txt|eob_835\.txt|denial_letter\.txt|claim_history\.txt)\b")
SECTION = re.compile(r"(?:§|\b[Ss]ections?\s+)(\d+(?:\.\d+)*(?:\([a-z]\))?)")
POLICY_ID = re.compile(r"\bMP-[A-Z]+-\d{3}\b")
QUOTE = re.compile(r"[\"“]([^\"”\n]{15,}?)[\"”]")
LINEREF = re.compile(r"([\w\-./]+\.txt)(?::| line | lines? )(\d+)", re.I)


class Corpus:
    def __init__(self, ctx):
        self.docs = {}
        for f in ctx.guard.list_files("case", "docs"):
            self.docs[f[len("docs/"):]] = ctx.guard.read_text("case", f)
        try:
            self.docs["task.md"] = ctx.guard.read_text("case", "task.md")
        except FileNotFoundError:
            pass
        self.policies = {p.policy_id: p for p in load_policies(ctx)}
        self.policy_text = {p.policy_id: p.text for p in self.policies.values()}
        self.all_norm = norm(" ".join(self.docs.values()) + " " + " ".join(self.policy_text.values()))

    def has_file(self, name):
        n = name.strip().strip(".").removeprefix("docs/")
        if n in self.docs:
            return True
        base = n.removeprefix("policy_library/")
        return base.endswith(".txt") and base[:-4] in self.policies

    def line_count(self, name):
        n = name.strip().removeprefix("docs/")
        if n in self.docs:
            return len(self.docs[n].splitlines())
        base = n.removeprefix("policy_library/")
        if base.endswith(".txt") and base[:-4] in self.policy_text:
            return len(self.policy_text[base[:-4]].splitlines())
        return None

    def section_exists(self, sid, policy_ids):
        pools = [self.policies[i] for i in policy_ids if i in self.policies] or list(self.policies.values())
        for p in pools:
            ids = set(p.sections) | {a for a, _ in p.params}
            if sid in ids or any(k.startswith(sid + "(") for k in ids):
                return True
        return False

    def quote_exists(self, q):
        q = q.strip().strip(".,;:").strip()
        frags = [f.strip() for f in re.split(r"\.\.\.|…", q) if f.strip()]
        return bool(frags) and all(norm(f) in self.all_norm for f in frags)


def verify_citations(text, corpus, policy_id=None):
    """-> list of {kind, text, pass, reason}. De-duplicated by (kind, text)."""
    out, seen = [], set()

    def add(kind, t, ok, reason=""):
        if (kind, t) not in seen:
            seen.add((kind, t))
            out.append({"kind": kind, "text": t, "pass": bool(ok), "reason": reason})

    cited_policies = list(dict.fromkeys(([policy_id] if policy_id else []) + POLICY_ID.findall(text)))
    for pid in POLICY_ID.findall(text):
        add("policy_id", pid, pid in corpus.policies, "" if pid in corpus.policies else "no such policy in the policy library")
    for m in SRC.finditer(text):
        for item in re.split(r"[;,]", m.group(1)):
            item = re.sub(r"^sources?:\s*", "", item.strip(), flags=re.I).strip(".")
            if not item:
                continue
            lm = LINEREF.search(item)
            if lm:
                n = corpus.line_count(lm.group(1))
                add("line", item, n is not None and 1 <= int(lm.group(2)) <= n, "" if n is not None and 1 <= int(lm.group(2)) <= n else "file or line does not exist")
            elif item.lower() in GENERIC_SOURCES:
                add("source", item, True, "generic reference (not a specific file)")
            elif item.lower().startswith("policy ") or POLICY_ID.search(item):
                ids = POLICY_ID.findall(item)
                add("source", item, bool(ids) and all(i in corpus.policies for i in ids), "" if ids else "policy reference without a policy id")
            elif SECTION.search(item):
                continue  # section fragments are verified below
            elif corpus.has_file(item):
                add("source", item, True)
            elif FILE.search(item):   # prose that names files ("denial_letter.txt states ..."): every named file must exist
                for fm in FILE.finditer(item):
                    add("source", fm.group(1), corpus.has_file(fm.group(1)), "" if corpus.has_file(fm.group(1)) else "no such file in the case documents or policy library")
            elif len(item.split()) >= 4 or '"' in item:
                add("source", item[:80], True, "prose source note (any quotes in it are verified separately)")
            else:
                add("source", item, False, "no such file in the case documents or policy library")
    for m in LINEREF.finditer(text):
        n_lines = corpus.line_count(m.group(1))
        ok = n_lines is not None and 1 <= int(m.group(2)) <= n_lines
        add("line", f"{m.group(1)}:{m.group(2)}", ok, "" if ok else "file or line number does not exist")
    for m in FILE.finditer(text):
        add("file", m.group(1), corpus.has_file(m.group(1)), "" if corpus.has_file(m.group(1)) else "no such file in the case documents")
    for m in SECTION.finditer(text):
        ok = corpus.section_exists(m.group(1), cited_policies)
        add("section", m.group(1), ok, "" if ok else f"section {m.group(1)} does not exist in {', '.join(cited_policies) or 'the policy library'}")
    for m in QUOTE.finditer(text):
        ok = corpus.quote_exists(m.group(1))
        add("quote", m.group(1)[:120], ok, "" if ok else "quoted text does not appear in any case document or policy")
    return out

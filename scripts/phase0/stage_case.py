"""Build the agent-visible staging directory for ONE case by ALLOWLISTED copy.

    sandbox/staging/<CASE>/
        case/task.md            <- data/cases/<CASE>/task.md
        case/docs/**            <- data/cases/<CASE>/docs/**   (regular files only)
        policy_library/*        <- data/policy_library/*       (regular files only, no sub-folders)
        skills/                 <- skills/**/*.py and skills/**/SKILL.md (no tests, caches, anything else)

Nothing else is ever copied (truth.json, rubric.json, gold/, attacks/, future files). After copying, the output is
re-walked and verified against the same allowlist; any violation deletes the staging directory and raises.

Usage: python scripts/phase0/stage_case.py C-0005 [--data data] [--out sandbox/staging]
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_NAMES = {"truth.json", "rubric.json", "gold", "attacks"}
CASE_ID = re.compile(r"^C-\d{4}$")
SKILL_FILE = re.compile(r"^(?:[A-Za-z0-9_]+/)*(?:[A-Za-z0-9_]+\.py|SKILL\.md)$")


class StagingError(RuntimeError):
    pass


def _regular_files(base):
    """Every file below base (relative paths); symlinks and special files are refused."""
    for p in sorted(base.rglob("*")):
        if p.is_symlink():
            raise StagingError(f"symlink refused: {p}")
        if p.is_file():
            yield p.relative_to(base)
        elif not p.is_dir():
            raise StagingError(f"special file refused: {p}")


def _forbidden(rel):
    return any(part.lower() in FORBIDDEN_NAMES for part in rel.parts)


def allowed(rel):
    """True if a path RELATIVE TO the case staging dir is on the allowlist."""
    s = rel.as_posix()
    if _forbidden(rel):
        return False
    if s == "case/task.md":
        return True
    if s.startswith("case/docs/"):
        return True
    if len(rel.parts) == 2 and rel.parts[0] == "policy_library":
        return True
    if rel.parts[0] == "skills" and len(rel.parts) > 1:
        inner = "/".join(rel.parts[1:])
        return "__pycache__" not in rel.parts and bool(SKILL_FILE.match(inner)) and "tests" not in rel.parts
    return False


def verify(stage):
    bad = [p.as_posix() for p in _regular_files(stage) if not allowed(p)]
    if bad:
        raise StagingError(f"files outside the allowlist in the staged copy: {bad}")


def _copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def stage_case(case_id, data_root=ROOT / "data", out_root=ROOT / "sandbox" / "staging", skills_root=ROOT / "skills"):
    """-> staged directory Path. Rebuilds from scratch."""
    if not CASE_ID.match(case_id):
        raise StagingError(f"bad case id {case_id!r}")
    data_root, out_root, skills_root = Path(data_root), Path(out_root), Path(skills_root)
    src = data_root / "cases" / case_id
    stage = out_root / case_id
    if stage.exists():
        shutil.rmtree(stage)
    try:
        if not (src / "task.md").is_file() or not (src / "docs").is_dir():
            raise StagingError(f"{src} lacks task.md or docs/")
        _copy(src / "task.md", stage / "case" / "task.md")
        for rel in _regular_files(src / "docs"):
            if _forbidden(rel):
                raise StagingError(f"forbidden name inside docs/: {rel}")
            _copy(src / "docs" / rel, stage / "case" / "docs" / rel)
        lib = data_root / "policy_library"
        for p in sorted(lib.iterdir()):
            if p.is_symlink() or p.is_dir():
                raise StagingError(f"policy_library must hold regular files only: {p}")
            if _forbidden(Path(p.name)):
                raise StagingError(f"forbidden name in policy_library: {p.name}")
            _copy(p, stage / "policy_library" / p.name)
        for rel in _regular_files(skills_root):
            if SKILL_FILE.match(rel.as_posix()) and "__pycache__" not in rel.parts and "tests" not in rel.parts:
                _copy(skills_root / rel, stage / "skills" / rel)
        verify(stage)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
    return stage


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("case")
    ap.add_argument("--data", default=str(ROOT / "data"))
    ap.add_argument("--out", default=str(ROOT / "sandbox" / "staging"))
    a = ap.parse_args()
    try:
        stage = stage_case(a.case, a.data, a.out)
    except StagingError as e:
        sys.exit(f"stage_case: {e}")
    n = sum(1 for _ in _regular_files(stage))
    print(f"staged {a.case} -> {stage} ({n} files)")


if __name__ == "__main__":
    main()

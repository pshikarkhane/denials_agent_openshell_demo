"""Stage a clean, agent-visible copy of a case: task.md, docs/** and the policy library, nothing else."""
import shutil
from pathlib import Path

FORBIDDEN = {"truth.json", "rubric.json", "gold", "attacks"}


def stage_case(data_root, case_id, dest):
    """-> (case_root, policy_root). Raises if anything forbidden would be visible."""
    data_root, dest = Path(data_root), Path(dest)
    src = data_root / "cases" / case_id
    case_root, policy_root = dest / "case", dest / "policy_library"
    if dest.exists():
        shutil.rmtree(dest)
    case_root.mkdir(parents=True)
    shutil.copy2(src / "task.md", case_root / "task.md")
    shutil.copytree(src / "docs", case_root / "docs")
    shutil.copytree(data_root / "policy_library", policy_root)
    bad = [p for p in dest.rglob("*") if p.name.lower() in FORBIDDEN]
    if bad:
        raise RuntimeError(f"forbidden entries in the staged copy: {bad}")
    return case_root, policy_root

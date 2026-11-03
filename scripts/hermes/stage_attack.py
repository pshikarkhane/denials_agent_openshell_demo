"""Stage ONE attack fixture (data/attacks/<id>/) for the sandbox, by the same ALLOWLISTED copy as scripts/phase0/stage_case.py.

Only the agent-visible files of the fixture are taken: task.md and docs/** (regular files). Everything else in the fixture folder
(attacks_manifest.json lives one level up; any truth/rubric/gold/manifest file that ever lands inside a fixture) is never copied, and a forbidden
name INSIDE docs/ makes staging fail closed. The staged tree is sandbox/staging/<base case id>/ (e.g. C-0005), identical in layout to a normal case,
then re-verified with stage_case.verify().

Usage: python scripts/hermes/stage_attack.py A1 [--out sandbox/staging]
"""
import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
import stage_case as sc  # noqa: E402

ATTACK_ID = re.compile(r"^A\d+[A-Za-z0-9_]*$")
ATTACKS = ROOT / "data" / "attacks"


def manifest(attacks_root=ATTACKS):
    return json.loads((Path(attacks_root) / "attacks_manifest.json").read_text())


def stage_attack(attack_id, attacks_root=ATTACKS, data_root=ROOT / "data", out_root=ROOT / "sandbox" / "staging", skills_root=ROOT / "skills"):
    """-> (staged directory Path, base case id). Rebuilds from scratch; fails closed on any forbidden name."""
    if not ATTACK_ID.match(attack_id):
        raise sc.StagingError(f"bad attack id {attack_id!r}")
    attacks_root, data_root = Path(attacks_root), Path(data_root)
    src = attacks_root / attack_id
    man = manifest(attacks_root)
    if attack_id not in man["fixtures"]:
        raise sc.StagingError(f"{attack_id} is not in attacks_manifest.json")
    base = man["fixtures"][attack_id].get("base_case") or man["base_case"]
    if not (src / "task.md").is_file() or not (src / "docs").is_dir():
        raise sc.StagingError(f"{src} lacks task.md or docs/")
    with tempfile.TemporaryDirectory() as tmp:
        view = Path(tmp) / "data"                       # a data root that holds ONLY the fixture's agent-visible files + the policy library
        case = view / "cases" / base
        (case / "docs").mkdir(parents=True)
        shutil.copyfile(src / "task.md", case / "task.md")
        for rel in sc._regular_files(src / "docs"):
            if sc._forbidden(rel):
                raise sc.StagingError(f"forbidden name inside the fixture docs/: {rel}")
            (case / "docs" / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / "docs" / rel, case / "docs" / rel)
        shutil.copytree(data_root / "policy_library", view / "policy_library")
        stage = sc.stage_case(base, view, out_root, skills_root)
    return stage, base


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("attack")
    ap.add_argument("--out", default=str(ROOT / "sandbox" / "staging"))
    a = ap.parse_args()
    try:
        stage, base = stage_attack(a.attack, out_root=a.out)
    except sc.StagingError as e:
        sys.exit(f"stage_attack: {e}")
    n = sum(1 for _ in sc._regular_files(stage))
    print(f"staged attack {a.attack} (base {base}) -> {stage} ({n} files)")


if __name__ == "__main__":
    main()

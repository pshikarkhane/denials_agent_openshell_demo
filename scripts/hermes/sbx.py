"""Helpers for driving the `my-hermes` OpenShell sandbox from the host: run commands inside it, install ONE staged case,
reset/inspect the state Hermes can persist (memory, skills, sessions, work files), and talk to the Hermes API.

No secret is read, printed or written here except the gateway bearer token, which scripts/phase0/hermes_client.py reads
at call time (never stored). Nothing here touches data/, eval/, skills/ or agent/."""
import glob
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "phase0"))
import hermes_client as hc  # noqa: E402
from stage_case import stage_case as _stage  # noqa: E402

SANDBOX = os.environ.get("SANDBOX", "my-hermes")
BASE = "/usr/local/share/appeals"
SIX = ["parse_denial_eob", "retrieve_payer_policy", "pull_clinical_notes", "assess_appealability", "draft_deliverable", "self_check"]
BASELINE_FILE = ROOT / "sandbox" / "state_baseline.json"


def _env():
    env = dict(os.environ)
    nodes = sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/v22*/bin")))
    env["PATH"] = ":".join([os.path.expanduser("~/.local/bin")] + nodes + [env.get("PATH", "")])
    env["NODE_NO_WARNINGS"] = "1"
    return env


def sbx(cmd, timeout=180):
    """Run a shell command inside the sandbox as user `sandbox`. -> (returncode, stdout, stderr)."""
    p = subprocess.run(["openshell", "sandbox", "exec", "-n", SANDBOX, "--no-tty", "--", "sh", "-c", cmd],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout, env=_env())
    return p.returncode, p.stdout, p.stderr


def sbx_py(code, *args, timeout=180):
    """Run python3 code inside the sandbox (args as argv). -> parsed JSON printed by the code."""
    quoted = " ".join("'" + a.replace("'", "'\"'\"'") + "'" for a in args)
    rc, out, err = sbx(f"python3 - {quoted} <<'PYEOF'\n{code}\nPYEOF", timeout)
    if rc != 0:
        raise RuntimeError(f"sandbox python failed rc={rc}: {err[-400:]}")
    return json.loads(out)


def container():
    out = subprocess.run(["docker", "ps", "-q", "--filter", f"name=openshell-default--{SANDBOX}"], capture_output=True, text=True).stdout.split()
    if not out:
        raise RuntimeError("sandbox container not found")
    return out[0]


def token():
    p = subprocess.run(["nemohermes", SANDBOX, "gateway-token", "--quiet"], capture_output=True, text=True, stdin=subprocess.DEVNULL, env=_env())
    lines = p.stdout.strip().splitlines()
    if not lines:
        raise RuntimeError("could not read gateway token (is the sandbox running?)")
    return lines[-1]


def health():
    import urllib.request
    with urllib.request.urlopen(hc.BASE + "/health", timeout=10) as r:
        return json.load(r)


# ---------------------------------------------------------------- install
def install_case(case_id):
    """Stage ONE case (allowlisted), remove every other staged case from the sandbox, copy this one in read-only (root-owned),
    install the wrapper and (re)install the six Hermes adapters. Returns the sha256 of the staged skills tree."""
    stage = _stage(case_id)
    subprocess.run([sys.executable, str(ROOT / "sandbox" / "make_hermes_skills.py")], check=True, capture_output=True)
    c = container()
    root = lambda cmd: subprocess.run(["docker", "exec", "-u", "root", c, "sh", "-c", cmd], check=True, capture_output=True, text=True)  # noqa: E731
    root(f"mkdir -p {BASE}/bin; chmod -R u+w {BASE} 2>/dev/null; rm -rf {BASE}/C-*")
    subprocess.run(["docker", "cp", str(stage), f"{c}:{BASE}/{case_id}"], check=True, capture_output=True)
    subprocess.run(["docker", "cp", str(ROOT / "sandbox" / "run_skill.sh"), f"{c}:{BASE}/bin/run_skill"], check=True, capture_output=True)
    root(f"chown -R root:root {BASE} && chmod -R a-w,a+rX {BASE} && chmod 555 {BASE}/bin/run_skill")
    sbx(f"mkdir -p /sandbox/work/output/{case_id}")
    for n in SIX:  # upload INTO the parent dir (the destination is a parent: uploading to skills/<n> nests as skills/<n>/<n>/SKILL.md)
        sbx(f"rm -rf /sandbox/.hermes/skills/{n}")
        p = subprocess.run(["openshell", "sandbox", "upload", SANDBOX, str(ROOT / "sandbox" / "hermes_skills" / n), "/sandbox/.hermes/skills"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, env=_env())
        if p.returncode:
            raise RuntimeError(f"adapter upload failed for {n}: {p.stderr[-300:]}")
    return tree_hash(stage / "skills")


def tree_hash(d):
    h = hashlib.sha256()
    for p in sorted(Path(d).rglob("*")):
        if p.is_file():
            h.update(p.relative_to(d).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------- state inspection / reset
INSPECT = r'''
import hashlib, json, os, sys
H = "/sandbox/.hermes"
def sha(p):
    try:
        return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
    except OSError:
        return None
def walk(d):
    out = {}
    for r, ds, fs in os.walk(d):
        for f in fs:
            p = os.path.join(r, f)
            out[os.path.relpath(p, d)] = sha(p)
    return out
SIX = set(sys.argv[1].split(","))
skills = {k: v for k, v in walk(H + "/skills").items() if not k.startswith(".usage.json") and k.split("/")[0] not in SIX}
adapters = {k: v for k, v in walk(H + "/skills").items() if k.split("/")[0] in SIX}
def ls(d):
    try:
        return sorted(os.listdir(d))
    except OSError:
        return None
print(json.dumps({
  "memories": walk(H + "/memories"), "skills": skills, "adapters": adapters, "usage_json": sha(H + "/skills/.usage.json"),
  "soul": sha(H + "/SOUL.md"), "workspace": walk(H + "/workspace"), "plans": walk(H + "/plans"), "hooks": walk(H + "/hooks"),
  "plugins": walk(H + "/plugins"), "profiles": walk(H + "/profiles"), "cron": ls(H + "/cron"),
  "work": walk("/sandbox/work"), "sandbox_top": ls("/sandbox"), "tmp": ls("/tmp"), "appeals_cases": [x for x in (ls("/usr/local/share/appeals") or []) if x != "bin"],
}))
'''

RESET = r'''
import json, os, shutil, sys
H = "/sandbox/.hermes"
B = json.loads(sys.argv[1])
keep = set(B["skills"])      # baseline relative paths (bundled skills, minus our six adapters)
SIX = set(sys.argv[2].split(","))
case = sys.argv[3]
removed = []
def rm(p):
    shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) and not os.path.islink(p) else (os.path.exists(p) or os.path.islink(p)) and os.remove(p)
    removed.append(p)
for d in ("memories", "workspace", "plans", "hooks", "plugins", "profiles"):
    for n in os.listdir(f"{H}/{d}"):
        rm(f"{H}/{d}/{n}")
for r, ds, fs in os.walk(H + "/skills", topdown=False):
    for f in fs:
        p = os.path.join(r, f); rel = os.path.relpath(p, H + "/skills")
        if rel.startswith(".usage.json") or rel.split("/")[0] in SIX:
            continue
        if rel not in keep:
            rm(p)
    for d in ds:
        p = os.path.join(r, d)
        if os.path.isdir(p) and not os.listdir(p) and os.path.relpath(p, H + "/skills").split("/")[0] not in SIX:
            rm(p)
for n in os.listdir("/sandbox/work"):
    rm("/sandbox/work/" + n)
for d, base in (("/tmp", B["tmp"]), ("/sandbox", B["sandbox_top"])):      # files the agent may have dropped outside the work dir
    for n in os.listdir(d):
        if n not in base:
            try:
                rm(f"{d}/{n}")
            except OSError:
                pass
os.makedirs(f"/sandbox/work/output/{case}")
print(json.dumps({"removed": len(removed)}))
'''


def baseline_load():
    return json.loads(BASELINE_FILE.read_text())


def inspect():
    return sbx_py(INSPECT, ",".join(SIX))


def take_baseline():
    """Record the pristine Hermes state (bundled skills etc.). Call once, after a clean install, with nothing run yet."""
    s = inspect()
    base = {k: s[k] for k in ("skills", "soul", "sandbox_top", "tmp")}
    base["note"] = "sha256[:16] of every file under /sandbox/.hermes/skills (minus the six adapters and .usage.json*), SOUL.md hash, /sandbox and /tmp listings"
    BASELINE_FILE.write_text(json.dumps(base, indent=1, sort_keys=True) + "\n")
    return base


def delete_all_sessions(tok):
    """Delete every Hermes session (GET /api/sessions, DELETE each) so no run can find an earlier run through session_search."""
    n = 0
    for _ in range(20):
        try:
            data = hc.get_json("/api/sessions?limit=200", tok)
        except Exception:
            data = hc.get_json("/api/sessions", tok)
        items = data.get("data", data) if isinstance(data, dict) else data
        if not items:
            return n
        for s in items:
            sid = s.get("id") or s.get("session_id")
            hc._req(f"/api/sessions/{sid}", tok, method="DELETE").close()
            n += 1
    return n


def diff_state(cur, base):
    """What differs from the pristine baseline. {} means clean."""
    d = {}
    if cur["memories"]:
        d["memories"] = sorted(cur["memories"])
    extra = sorted(set(cur["skills"]) - set(base["skills"]))
    changed = sorted(k for k in cur["skills"] if k in base["skills"] and cur["skills"][k] != base["skills"][k])
    missing = sorted(set(base["skills"]) - set(cur["skills"]))
    if extra:
        d["skills_added"] = extra
    if changed:
        d["skills_changed"] = changed
    if missing:
        d["skills_removed"] = missing
    if cur["soul"] != base["soul"]:
        d["soul_changed"] = True
    for k in ("workspace", "plans", "hooks", "plugins", "profiles"):
        if cur[k]:
            d[k] = sorted(cur[k])
    return d


def reset_state(case_id, tok):
    """Reset everything Hermes could persist, then verify against the baseline. -> report dict (raises if still dirty)."""
    base = baseline_load()
    n_sessions = delete_all_sessions(tok)
    r = sbx_py(RESET, json.dumps({"skills": sorted(base["skills"]), "tmp": base["tmp"], "sandbox_top": base["sandbox_top"]}), ",".join(SIX), case_id)
    cur = inspect()
    dirty = diff_state(cur, base)
    leftovers = {"work": sorted(k for k in cur["work"]), "appeals_cases": cur["appeals_cases"]}
    rep = {"sessions_deleted": n_sessions, "paths_removed": r["removed"], "dirty_after_reset": dirty, "work_files": leftovers["work"], "staged_cases": cur["appeals_cases"],
           "tmp_extra": sorted(set(cur["tmp"] or []) - set(base["tmp"] or [])), "sandbox_top_extra": sorted(set(cur["sandbox_top"] or []) - set(base["sandbox_top"] or []))}
    if dirty:
        raise RuntimeError(f"sandbox state still differs from baseline after reset (cannot restore modified bundled files): {dirty}")
    return rep

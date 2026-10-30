#!/usr/bin/env bash
# Put ONE staged case + the skills package + the Hermes adapters into the running sandbox. No sudo.
#   usage: sandbox/install_into_sandbox.sh C-0005 [sandbox-name]
# Layout inside the sandbox:
#   /usr/local/share/appeals/<CASE>/{case,policy_library,skills}   root-owned, read-only (Landlock lists /usr as read_only,
#                                                                  and the files are not writable by user `sandbox`)
#   /usr/local/share/appeals/bin/run_skill                         wrapper that binds the roots
#   /sandbox/.hermes/skills/<skill>/SKILL.md                       Hermes adapters (Hermes' primary skills dir)
#   /sandbox/work/output/<CASE>/                                   the only writable place for outputs
# Uses `docker cp` / `docker exec -u root` on the sandbox container (the sandbox runs through the Docker daemon).
set -euo pipefail
cd "$(dirname "$0")/.."
CASE="${1:?case id, e.g. C-0005}"; SB="${2:-my-hermes}"
PY=".venv/bin/python"; [ -x "$PY" ] || PY=python3
"$PY" scripts/phase0/stage_case.py "$CASE"
"$PY" sandbox/make_hermes_skills.py
C="$(docker ps -q --filter "name=openshell-default--${SB}" | head -1)"; [ -n "$C" ] || { echo "sandbox container not found"; exit 1; }
B=/usr/local/share/appeals
docker exec -u root "$C" sh -c "mkdir -p $B/bin && rm -rf $B/$CASE && chmod -R u+w $B/$CASE 2>/dev/null; rm -rf $B/$CASE"
docker cp "sandbox/staging/$CASE" "$C:$B/$CASE"
docker cp sandbox/run_skill.sh "$C:$B/bin/run_skill"
docker exec -u root "$C" sh -c "chown -R root:root $B && chmod -R a-w,a+rX $B && chmod 555 $B/bin/run_skill"
export PATH="$HOME/.local/bin:$PATH"
for s in sandbox/hermes_skills/*/; do
  n="$(basename "$s")"
  openshell sandbox upload "$SB" "sandbox/hermes_skills/$n" "/sandbox/.hermes/skills/$n" </dev/null >/dev/null
done
openshell sandbox exec -n "$SB" --no-tty -- sh -c "mkdir -p /sandbox/work/output/$CASE; ls $B/$CASE; ls /sandbox/.hermes/skills | tr '\n' ' '" </dev/null

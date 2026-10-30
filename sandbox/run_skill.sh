#!/bin/sh
# Installed (read-only, root-owned) at /usr/local/share/appeals/bin/run_skill inside the sandbox.
# usage: run_skill <CASE_ID> <skill_name> '<json args>'
# Binds the skill to the read-only staged case and the writable output dir. The model never supplies roots.
set -eu
BASE="${APPEALS_BASE:-/usr/local/share/appeals}"
case_id="${1:?usage: run_skill <CASE_ID> <skill> '<json>'}"; skill="${2:?skill name}"; args="${3:-}"; [ -n "$args" ] || args='{}'
case "$case_id" in C-[0-9][0-9][0-9][0-9]) ;; *) echo '{"error":{"code":"bad_input","message":"bad case id"}}'; exit 1;; esac
case "$skill" in parse_denial_eob|retrieve_payer_policy|pull_clinical_notes|assess_appealability|draft_deliverable|self_check) ;;
  *) echo '{"error":{"code":"bad_input","message":"unknown skill"}}'; exit 1;; esac
R="$BASE/$case_id"
[ -d "$R/case" ] || { echo '{"error":{"code":"not_found","message":"case is not staged in this sandbox"}}'; exit 1; }
OUT="/sandbox/work/output/$case_id"; mkdir -p "$OUT"
export PYTHONPATH="$R" PYTHONDONTWRITEBYTECODE=1 CASE_ROOT="$R/case" POLICY_ROOT="$R/policy_library" \
  OUTPUT_ROOT="$OUT" SKILL_EVENTS_FILE="$OUT/skill_events.jsonl" CASE_ID="$case_id" RUN_ID="${RUN_ID:-hermes}"
exec python3 -m "skills.$skill" "$args"

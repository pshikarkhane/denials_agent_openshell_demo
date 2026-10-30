#!/usr/bin/env bash
# Phase 0 smoke test: host checks -> model API -> Hermes sandbox -> hello-world agent call.
# Usage: SANDBOX=my-hermes NVIDIA_INFERENCE_API_KEY=... bash scripts/phase0/smoke_test.sh
# Set SKIP_SANDBOX=1 to run only the model-API checks (works on any machine).
set -uo pipefail
cd "$(dirname "$0")/../.."
SANDBOX="${SANDBOX:-my-hermes}"
PORT="${HERMES_PORT:-8642}"
fail=0
ok()  { echo "PASS  $1"; }
bad() { echo "FAIL  $1"; fail=1; }

echo "== 1. Model API (agent model + 3 judges)"
python3 scripts/phase0/judge_smoke.py && ok "model API" || bad "model API"

if [[ "${SKIP_SANDBOX:-0}" == "1" ]]; then
  echo "SKIP  sandbox checks (SKIP_SANDBOX=1)"; exit $fail
fi

echo "== 2. Host tooling"
node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a==22&&b>=19)?0:1)' \
  && ok "node >= 22.19 ($(node -v))" || bad "node >= 22.19"
docker info >/dev/null 2>&1 && ok "docker daemon reachable" || bad "docker daemon reachable"
command -v nemohermes >/dev/null && ok "nemohermes CLI: $(NODE_NO_WARNINGS=1 nemohermes --version 2>&1 | head -1)" || bad "nemohermes CLI on PATH"
command -v openshell  >/dev/null && ok "openshell CLI: $(openshell --version 2>&1 | head -1)"  || bad "openshell CLI on PATH"

echo "== 3. Sandbox + Hermes API"
nemohermes "$SANDBOX" status && ok "sandbox status" || bad "sandbox status"
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 || openshell forward start --background "$PORT" "$SANDBOX" >/dev/null 2>&1
curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && ok "Hermes /health" || bad "Hermes /health"

echo "== 4. Hello-world agent call (request -> Hermes -> inference.local -> Nemotron)"
TOKEN="$(nemohermes "$SANDBOX" gateway-token --quiet 2>/dev/null)"
# Verified on v0.0.137: the Hermes API exposes ONE model id, "hermes-agent" (GET /v1/models). The real upstream
# model is chosen by the OpenShell inference route, not by this field.
MODEL="hermes-agent"
RESP="$(curl -s -m 180 "http://127.0.0.1:$PORT/v1/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly one word: pong\"}]}")"
echo "$RESP" | head -c 400; echo
echo "$RESP" | grep -qi pong && ok "agent hello-world" || bad "agent hello-world"

echo "== 5. Sandbox is isolated (no direct internet)"
# `nemohermes <name> connect` takes no command; use `openshell sandbox exec` (verified from --help).
CODE="$(openshell sandbox exec -n "$SANDBOX" --no-tty --timeout 30 -- curl -s -m 8 -o /dev/null -w '%{http_code}' https://example.invalid/ </dev/null 2>&1 | tail -1)"
echo "  http code from inside sandbox to example.invalid: $CODE"
[[ "$CODE" =~ ^(000|403|502)$ ]] && ok "non-allowlisted egress blocked" || bad "egress block (got '$CODE')"

exit $fail

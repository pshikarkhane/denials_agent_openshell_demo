#!/usr/bin/env bash
# Build the whole dataset in order. Safe by default: existing truth files with clinical facts and frozen LLM output are KEPT.
#   FORCE_TRUTH=1     regenerate truth.json (overwrites clinical facts) and therefore regenerate the pilot clinical documents
#   FORCE_POLICIES=1  regenerate the (frozen) policy library with the datagen model
# LLM stages need NVIDIA_INFERENCE_API_KEY in the environment. Usage: bash scripts/build_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"
T=""; C=""; P=""
[[ "${FORCE_TRUTH:-0}" == "1" ]] && { T="--force"; C="--force"; }
[[ "${FORCE_POLICIES:-0}" == "1" ]] && P="--force"

echo "== 1/6 truth";            $PY -m data_gen.gen_cases $T
echo "== 2/6 deterministic documents"; $PY -m data_gen.render_docs
echo "== 3/6 policy library";   $PY -m data_gen.gen_policies $P
echo "== 4/6 pilot clinical documents"; $PY -m data_gen.gen_clinical $C
echo "== 5/6 validate_data (read-only)"; $PY -m data_gen.validate_data
echo "== 6/6 pytest";           $PY -m pytest -q

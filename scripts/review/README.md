# Automated pilot review

Read-only review of the pilot cases and policy library. It never writes under `data/` or `data_gen/`; outputs go to `docs/auto_review_raw/`.

```
export NVIDIA_INFERENCE_API_KEY=<key>                      # env only
.venv/bin/python scripts/review/run_review.py               # all steps (about 10 min; Gemini is slow)
.venv/bin/python scripts/review/run_review.py blind realism # or any of: programmatic blind realism policy coding
.venv/bin/python scripts/review/summarize.py                # condensed digest of the raw outputs
.venv/bin/python scripts/review/build_coding_table.py       # fills <<CODING_TABLE>> in docs/AUTO_REVIEW.md if present, else prints it
```

- Reviewer models are `judges.gemini` and `judges.gpt` from `config/models.yaml` (the code refuses the datagen or agent model).
- `blind_solve.py`: reviewers get only task.md, docs/** and policy_library/* (it refuses any path containing truth/rubric/gold/attacks/manifest). Answers are compared to truth.json on the host.
- `realism_review.py`: reviewers also get the case's truth.json (host-side only, never mounted).
- `programmatic_checks.py`: no LLM; independent date/deadline/identity/evidence-quote checks and policy structure checks.
- Raw reviewer responses are saved with keys redacted. The findings report, `docs/AUTO_REVIEW.md`, was written by hand from these outputs.

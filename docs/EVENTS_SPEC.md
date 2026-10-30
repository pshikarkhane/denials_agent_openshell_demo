# EVENTS_SPEC: agent run recordings (for the demo replay UI)

Written by `agent/run_case.py` and `agent/run_baseline.py`. Pre-sandbox harness: in the Hermes port the same schema should be produced from Hermes' own trace
(see STATUS.md, "What must change for the Hermes port"). Nothing recorded here ever contains `truth.json`, `rubric.json`, `gold/` or `attacks/` content: only what the
model said and what the skills returned. Keys are redacted before writing.

## Files per run
`runs/<run_id>/<case_id>/` (agent) or `runs/<run_id>/baseline/<case_id>/` (no-tools baseline); one run id per repeat (`<base>-r1`, `<base>-r2`):

| file | content |
|---|---|
| `events.jsonl` | one JSON event per line, schema below (this spec) |
| `trace.json` | ordered replay steps derived from the events (schema below) |
| `skills_events.jsonl` | the skills' own event log (one event per skill call and per file read, plus denied accesses); schema in `docs/SKILLS_SPEC.md` |
| `summary.json` | model id, temperature, prompt hash, git SHA, token usage, per-call latency, turns, tool calls by name, malformed-call count, model failures, revisions, status |
| `deliverable.md`, `decision.json` | what the model proposed last (written even if self_check still failed) |
| `final_self_check.json` | last self_check result (recorded, not enforced) |
| `staged/` | the agent-visible copy: `case/task.md`, `case/docs/**`, `policy_library/` and nothing else |

## events.jsonl schema
Every event has exactly these keys, sorted:

| key | type | meaning |
|---|---|---|
| `seq` | int | 1, 2, 3, ... within the run |
| `ts` | string | UTC, ISO-8601 with milliseconds |
| `run_id`, `case_id` | string | |
| `variant` | string | `agent` or `baseline` |
| `kind` | string | `run_start`, `model_request`, `model_response`, `tool_call`, `tool_result`, `self_check`, `revision`, `run_end` |
| `name` | string | model/tool/step name (the tool name for tool events) |
| `status` | string | `ok`, `error` or `denied` |
| `duration_ms` | int | wall time of the call (0 for events without duration) |
| `data` | object | kind specific, below |

`data` by kind:
- `run_start`: `model`, `temperature`, `prompt_sha256`, `git_sha`, `max_turns`, `time_limit_s`, `tools[]`.
- `model_request`: `turn`, `attempt` (1-3; retries after a failed response), `n_messages`, `n_tools`, `approx_chars`.
- `model_response`: `turn`, `attempt`, `ok`, `content` (assistant text or null), `tool_calls[]` (`id`, `name`, `arguments` as the raw string the model sent), `usage`, `finish_reason`; on failure `ok: false` and `error` (`no_choices`, `bad_json`, `http`, `empty`), status `error`.
- `tool_call`: `tool_call_id`, `name`, `arguments` (parsed object, or the raw string when it was not valid JSON).
- `tool_result`: `tool_call_id`, `name`, `status`, `result_chars`, `truncated`, `result` (first 4000 characters). Refused paths have status `denied`.
- `self_check`: `phase` (`proposal` after each final answer, `final` after the last), `ok`, `n_errors`, `n_warnings`, `failed[]` (`id`, `detail`, `hint`), `warnings[]`.
- `revision`: `n`, `reason`, `failed_ids[]` (the harness asked the model to fix a self_check failure; at most 2).
- `run_end`: `status` (`submitted`, `max_turns`, `time_limit`, `model_failure`, `no_final`, or `<status>_with_proposal`), `turns`, `tool_calls`, `usage`, `revisions`.

Example (C-0030, long strings shortened):
```json
{"case_id": "C-0030", "data": {"git_sha": "73d0b23aaaf97bdb171a36a9c2518676cc56489c", "max_turns": 14, "model": "nvidia/nvidia/nemotron-3.5-super-text-preview", "prompt_sha256": "7d352c9e8463810816376b0d19d15bd934bbe87277585adcc5b8f75ff95f264b", "temperature": 0.2, "time_limit_s": 900, "tools": ["parse_denial_eob", "retrieve_payer_policy", "\u2026"]}, "duration_ms": 0, "kind": "run_start", "name": "run_start", "run_id": "smoke-r1", "seq": 1, "status": "ok", "ts": "2026-10-30T21:13:46.605+00:00", "variant": "agent"}
{"case_id": "C-0030", "data": {"approx_chars": 5630, "attempt": 1, "n_messages": 2, "n_tools": 6, "turn": 1}, "duration_ms": 0, "kind": "model_request", "name": "model_request", "run_id": "smoke-r1", "seq": 2, "status": "ok", "ts": "2026-10-30T21:13:46.607+00:00", "variant": "agent"}
{"case_id": "C-0030", "data": {"attempt": 1, "content": "\n", "finish_reason": "tool_calls", "ok": true, "tool_calls": [{"arguments": "{}", "id": "call-d60484e2-9d66-46a7-9959-2eeac77887fd", "name": "parse_denial_eob"}], "turn": 1, "usage": {"completion_tokens": 37, "completion_tokens_details": {"reasoning_tokens": 22}, "prompt_tokens": 2753, "prompt_tokens_details": {"cached_tokens": 0}, "total_tokens": 2790}}, "duration_ms": 607, "kind": "model_response", "name": "model_response", "run_id": "smoke-r1", "seq": 3, "status": "ok", "ts": "2026-10-30T21:13:47.216+00:00", "variant": "agent"}
{"case_id": "C-0030", "data": {"arguments": {}, "name": "parse_denial_eob", "tool_call_id": "call-d60484e2-9d66-46a7-9959-2eeac77887fd"}, "duration_ms": 0, "kind": "tool_call", "name": "parse_denial_eob", "run_id": "smoke-r1", "seq": 4, "status": "ok", "ts": "2026-10-30T21:13:47.239+00:00", "variant": "agent"}
{"case_id": "C-0030", "data": {"name": "parse_denial_eob", "result": "{\"amounts\":{\"allowed\":0.0,\"billed\":236.93,\"claim_totals\":{\"allowed\":0.0,\"billed\":236.93,\"paid\":0.0,\"patient_responsibility\":0.0},\"denied_amount\":236.93,\"paid\":0\u2026", "result_chars": 1740, "status": "ok", "tool_call_id": "call-d60484e2-9d66-46a7-9959-2eeac77887fd", "truncated": false}, "duration_ms": 14, "kind": "tool_result", "name": "parse_denial_eob", "run_id": "smoke-r1", "seq": 5, "status": "ok", "ts": "2026-10-30T21:13:47.259+00:00", "variant": "agent"}
{"case_id": "C-0030", "data": {"failed": [], "n_errors": 0, "n_warnings": 0, "ok": true, "phase": "proposal", "warnings": []}, "duration_ms": 183, "kind": "self_check", "name": "self_check", "run_id": "smoke-r1", "seq": 34, "status": "ok", "ts": "2026-10-30T21:14:02.663+00:00", "variant": "agent"}
{"case_id": "C-0030", "data": {"revisions": 0, "status": "submitted", "tool_calls": 8, "turns": 8, "usage": {"completion_tokens": 8387, "prompt_tokens": 53237, "reasoning_tokens": 4125, "total_tokens": 61624}}, "duration_ms": 16200, "kind": "run_end", "name": "run_end", "run_id": "smoke-r1", "seq": 36, "status": "ok", "ts": "2026-10-30T21:14:02.796+00:00", "variant": "agent"}
```
A revision event:
```json
{"case_id": "C-0005", "data": {"failed_ids": ["identifier_claim_no"], "n": 1, "reason": "identifier_claim_no: expected 6268311 (hint: state the claim number exactly as in the denial letter)"}, "duration_ms": 0, "kind": "revision", "name": "revision", "run_id": "agent-x-r1", "seq": 14, "status": "ok", "ts": "2026-10-30T21:00:00.000+00:00", "variant": "agent"}
```

## trace.json schema
A JSON list of steps in order, built from the events (model turn, tool call + result merged, self_check, revision, run start/end):
`{"n", "kind", "name", "args_summary", "result_summary", "duration_ms", "status"}` with `kind` one of `run`, `model`, `tool`, `self_check`, `revision`.
Summaries are at most about 200 characters. Example (first steps of the same run):
```json
[
 {
  "args_summary": "model nvidia/nvidia/nemotron-3.5-super-text-preview",
  "duration_ms": 0,
  "kind": "run",
  "n": 1,
  "name": "start",
  "result_summary": "run started",
  "status": "ok"
 },
 {
  "args_summary": "attempt 1",
  "duration_ms": 607,
  "kind": "model",
  "n": 2,
  "name": "turn 1",
  "result_summary": "tool calls: parse_denial_eob",
  "status": "ok"
 },
 {
  "args_summary": "{}",
  "duration_ms": 14,
  "kind": "tool",
  "n": 3,
  "name": "parse_denial_eob",
  "result_summary": "{\"amounts\":{\"allowed\":0.0,\"billed\":236.93,\"claim_totals\":{\"allowed\":0.0,\"billed\":236.93,\"paid\":0.0,\"patient_responsibility\":0.0},\"denied_amount\":236.93,\"paid\":0.0,\"patient_responsibility\":0.0},\"appea\u2026",
  "status": "ok"
 }
]
```

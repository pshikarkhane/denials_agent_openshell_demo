# SKILLS_SPEC: the six agent skills (offline tools)

The skills are **tools, not the agent**. They do the deterministic work (parsing, retrieval, date arithmetic, validation); the model still supplies the judgment:
criterion statuses, the decision, the evidence selection and all prose. No skill calls a model, uses a key, or reads `truth.json`, `rubric.json`, `gold/` or `attacks/`.
Code: `skills/` (stdlib + pydantic only; BM25 is implemented in `skills/common/bm25.py`, so there is no ranking dependency). Tests: `tests/test_skills.py` (37 tests, all 60 cases).
Demo: `python scripts/run_skill_chain.py --case C-0005`.

## Common behaviour
**Configuration** (environment variable, or a JSON argument of the same name in lower case): `CASE_ROOT` (a folder holding only `task.md` and `docs/**`), `POLICY_ROOT` (policy library),
`OUTPUT_ROOT` (where the model writes `deliverable.md` / `decision.json`; only used to read them back), `SKILL_EVENTS_FILE`, `RUN_ID`, `CASE_ID`. Optional argument `step` numbers a call in the event log.

**CLI:** `python -m skills.<name> '<json args>'` prints one JSON object with sorted keys. Python: `from skills.<name> import call; call({...})`.

**Path guard** (`skills/common/paths.py`): every read goes through it. Refused, and logged as a denied access event: any path containing `..`; any path that resolves (after symlinks) outside the configured roots;
any file or folder named `truth.json`, `rubric.json`, `gold` or `attacks` (case-insensitive); anything in the case root other than `task.md` and `docs/**`; and a root that itself contains such an entry
(so pointing `CASE_ROOT` at a raw `data/cases/<id>` folder fails closed).

**Errors** (CLI: `{"error": {"code": ..., "message": ...}}` and exit code 1; Python: `SkillError`): `bad_input` (arguments do not match the schema), `access_denied`, `not_found`,
`no_documents` (parse_denial_eob: neither the remit nor the letter exists), `missing_facts` (assess_appealability: notice date or date of service not parsable).

**Events** (`skills/common/events.py`). Every skill call appends ONE JSON line (sorted keys, stable schema) to the events file; each file a skill reads gets its own event; `path_guard` events record refused accesses.

| key | type | meaning |
|---|---|---|
| `ts` | string | UTC time, ISO-8601 with milliseconds |
| `run_id` | string or null | run identifier (`RUN_ID` / `run_id`) |
| `case_id` | string or null | case identifier |
| `step` | int or null | step number within the run (caller supplied) |
| `tool` | string | skill name; `<skill>.read` for one file read; `path_guard` for a refused access |
| `args` | object | call arguments (text bodies omitted), or `{"root", "path"}` for reads |
| `result_summary` | string | first 300 characters of a JSON summary, the file size, or the denial reason |
| `duration_ms` | int | wall time |
| `status` | string | `ok`, `error` or `denied` |
| `error` | string or null | `code: message` when status is not `ok` |

Samples: `docs/samples/skill_events_sample.jsonl` (C-0005 chain), `docs/samples/skill_events_C-0030.jsonl`, and full chain outputs `docs/samples/skill_chain_C-0005.json`, `docs/samples/skill_chain_C-0030.json`.

## 1. parse_denial_eob
**Purpose.** Extract the denial facts from `docs/eob_835.txt`, `docs/denial_letter.txt` and `task.md`. Anything not found is `null` with a reason in `not_found`; nothing is guessed.
Documents that disagree are listed in `consistency`; blank remit fields (`(not provided)`) are listed in `blank_fields`.
**Input.** Only the common arguments.
**Output (main fields).** `payer{id,name}`, `claim_no`, `patient{id,name,member_id}`, `dos`, `cpt`, `service_description`, `icd10[]`, `service_lines[]`, `denied_line`,
`amounts{billed,allowed,paid,denied_amount,patient_responsibility,claim_totals}`, `denial{carc,carc_text,rarc,reason_text,notice_date}`, `appeal{window_days,by_date,address}`,
`corrected_claim{window_days,by_date}`, `policy_title`, `as_of_date` (the review date), `claim_details`, `letter_facts` (for example `missing_item`, `filing_deadline`), `blank_fields[]`, `not_found{}`, `consistency[]`.
**Example** (C-0030, subset):
```json
{
 "appeal": {
  "address": "Appeals Unit, P.O. Box 3300, Terravista, ST 00003",
  "by_date": "2026-11-01",
  "window_days": 90
 },
 "as_of_date": "2026-10-25",
 "claim_no": "3704835",
 "corrected_claim": {
  "by_date": "2027-01-30",
  "window_days": 180
 },
 "cpt": "99213",
 "denial": {
  "carc": "CO-29",
  "carc_text": "The time limit for filing has expired.",
  "notice_date": "2026-08-03",
  "rarc": null,
  "reason_text": "Our records show the claim was received on 2026-07-15, after the 90-day filing limit. The filing deadline for this date of service was 2026-06-30 (Medical Policy: Timely Filing of Claims)."
 },
 "dos": "2026-04-01",
 "policy_title": "Timely Filing of Claims"
}
```
**Errors:** `access_denied`, `no_documents`, `bad_input`.
**The model still does:** decide what the facts mean for the case (the skill reports `rarc: null`; it does not say whether that matters).

## 2. retrieve_payer_policy
**Purpose.** Select the governing policy. The library is filtered by payer, then by date of service (a policy applies from `applies_from`, the date its own text says it applies to, until `applies_until` if superseded),
and only THEN ranked: exact title match, title similarity, BM25 over the policy text. Same-title distractors (other payer, superseded version) and near-duplicates are reported in `excluded` with the reason.
Equal scores return `status: "tie"` with the tied ids and no policy; nothing is picked silently.
**Input.** `payer` (id or name), `dos`; optional `cpt`, `service_description`, `icd10[]`, `denial_code`, `denial_text`, `reason_text`, `policy_title`, `top_k` (6). Feed these from parse_denial_eob.
**Output.** `status` (`selected` | `tie` | `none`), `policy{policy_id,title,payer_id,effective_date,applies_from,applies_until,windows{appeal_days,timely_filing_days,corrected_claim_days},appeals_address,parameters[]}`,
`candidates[]` (ranked, with score parts), `tie`, `sections[]` (`policy_id, section, heading, text, score, line, effective_date`), `date_notes[]`, `excluded[]`, `reason`.
**Example** (C-0030, subset):
```json
{
 "excluded": [
  {
   "policy_id": "MP-TF-010",
   "reason": "superseded: this version last applied to dates of service on or before 2024-12-31; replaced by MP-TF-001"
  }
 ],
 "policy": {
  "effective_date": "2026-03-15",
  "policy_id": "MP-TF-001",
  "title": "Timely Filing of Claims",
  "windows": {
   "appeal_days": 90,
   "corrected_claim_days": 180,
   "timely_filing_days": 90
  }
 },
 "status": "selected"
}
```
**Errors:** `access_denied`, `bad_input`. A payer with no policy returns `status: "none"` and a reason (not an error).
**The model still does:** read the sections and decide which apply; resolve a tie; interpret a policy effective date that is after the date of service.

## 3. pull_clinical_notes
**Purpose.** Metadata first, full text only on request (minimum necessary). Default date range: on or before the review date. Every file read is logged. A case with no clinical documents returns `documents: []` and a `reason`, not an error.
**Input.** `date_from`, `date_to`, `include_text` (false), `paths[]` (fetch these documents with full text, for example `notes/2026-03-23_pcp.txt`), `include_undated` (true; supporting documents have no date in the file name).
**Output.** `as_of_date`, `date_from`, `date_to`, `documents[]` (`path, kind, folder, date, date_source, date_reason, title, chars, lines`, plus `text` only when requested), `n_excluded_by_date`, `reason`.
**Example** (C-0030, first two documents):
```json
{
 "as_of_date": "2026-10-25",
 "documents": [
  {
   "chars": 1731,
   "date": "2026-03-02",
   "date_reason": null,
   "date_source": "file name",
   "folder": "notes",
   "kind": "pcp",
   "lines": 24,
   "path": "notes/2026-03-02_pcp.txt",
   "title": "PRIMARY CARE VISIT NOTE"
  },
  {
   "chars": 1650,
   "date": "2026-04-01",
   "date_reason": null,
   "date_source": "file name",
   "folder": "notes",
   "kind": "visit",
   "lines": 24,
   "path": "notes/2026-04-01_visit.txt",
   "title": "OFFICE VISIT NOTE"
  }
 ],
 "reason": null
}
```
**Errors:** `access_denied` (for example `paths: ["../truth.json"]`), `not_found` (a path that is not a note or supporting document).
**The model still does:** choose which documents to read in full, and read them.

## 4. assess_appealability (facts only)
**Purpose.** Deterministic facts: the appeal deadline (notice date + the stated window), the corrected-claim deadline, days remaining and open/closed on the review date, the timely-filing arithmetic
(policy 7.2 limit from the retrieved policy; filing deadline = DOS + limit; claim_history acceptance and payer-receipt dates; status `within_limit` / `accepted_within_limit_received_after` / `after_limit`), the claim_history facts,
documents dated after the date of service, and a **criteria skeleton**: each requirement section (`2.x`) of the policy with evidence candidates (file, line, short excerpt, BM25 score) and `status: null`.
It never outputs a decision or a criterion status. `action_deadline_rule` says how to pick the action deadline once the model has decided (mirrors the schema: the corrected-claim deadline for a corrected claim, otherwise the appeal deadline; `deadline_ok` = review date <= action_deadline).
**Input.** `policy_id` (default: the policy retrieve_payer_policy selects), `evidence_per_section` (3).
**Output.** `as_of_date`, `dates`, `deadlines{appeal, corrected_claim}` (each `date, days_remaining, open_on_review_date, window_days, basis, stated_in_letter`), `action_deadline_rule`, `timely_filing`, `claim_history`, `policy`, `criteria_skeleton[]`, `documents_dated_after_dos[]`, `notes[]`.
**Example** (C-0030, subset):
```json
{
 "deadlines": {
  "appeal": {
   "basis": "notice date 2026-08-03 + 90 days",
   "date": "2026-11-01",
   "days_remaining": 7,
   "open_on_review_date": true,
   "stated_in_letter": "2026-11-01",
   "window_days": 90
  },
  "corrected_claim": {
   "basis": "notice date 2026-08-03 + 180 days",
   "date": "2027-01-30",
   "days_remaining": 97,
   "open_on_review_date": true,
   "stated_in_letter": "2027-01-30",
   "window_days": 180
  }
 },
 "timely_filing": {
  "filing_deadline": "2026-06-30",
  "first_accepted_date": "2026-07-14",
  "limit_days": 90,
  "limit_source": "MP-TF-001 7.2",
  "payer_received_date": "2026-07-15",
  "stated_in_letter": "2026-06-30",
  "status": "after_limit",
  "status_reason": "first accepted 2026-07-14 and payer received 2026-07-15 compared with filing deadline 2026-06-30"
 }
}
```
**Errors:** `access_denied`, `missing_facts`, `not_found` (unknown `policy_id`).
**The model still does:** the decision; each criterion's status (met / unmet / unknown); choosing the evidence (the candidates are only candidates); and the action deadline once it has decided.

## 5. draft_deliverable (validation helpers)
**Purpose.** Three actions (`action` argument): `validate_decision` (decision.json against `eval/deliverable_schema.py`), `render_skeleton` (markdown with identifiers and computed deadlines prefilled and `<<FILL: ...>>` placeholders;
choose `kind` = `letter` or `memo` after deciding), `verify_citations` (every `(source: file)`, `file:line`, quoted text of 15+ characters, `MP-...` id and `Section x.y` must exist in the case documents or policy library; per-citation pass/fail).
**Input.** `action`; `kind`; `decision_path` / `decision_text`; `deliverable_path` / `deliverable_text` (paths are relative to `OUTPUT_ROOT`); optional `policy_id`.
**Output.** `action`, `valid`, `errors[]`, `skeleton`, `citations[]` (`kind, text, pass, reason`), `summary`.
**Example:** `{"action": "verify_citations", "deliverable_text": "... (source: notes/ghost.txt) ...", "case_root": "...", "policy_root": "..."}` returns `valid: false` with the citation
`{"kind": "source", "text": "notes/ghost.txt", "pass": false, "reason": "no such file in the case documents or policy library"}`.
**Errors:** `bad_input` (no text or path; `render_skeleton` without `kind`), `access_denied` (for example `deliverable_path: "../truth.json"`).
**The model still does:** write the deliverable and decision.json.

## 6. self_check
**Purpose.** Deterministic checklist of `deliverable.md` + `decision.json` (inline text, or paths under `OUTPUT_ROOT`): decision.json valid; case id; identifiers (claim number, patient ID, CPT, date of service) present;
denial code; `action_deadline` equals the computed deadline for the decision type and `deadline_ok` is right; the deadline appears in the text; the policy id exists and equals the retrieved policy; criterion section ids exist;
evidence files and enclosures exist; an appeal lists enclosures; gaps are listed where a required value or document is absent (ESCALATE_MISSING_DOCS, an `unknown` criterion, or a blank remit field on a corrected claim);
required sections are present (letter: remedy, enclosures, gaps; memo: next action, gaps; a heading may be markdown, bold, ALL-CAPS or a plain `Label:` line; identifiers and the deadline have their own content checks, so no heading is required for them); criterion ids may be policy sections or the policy's 7.x parameter rows; an appeal letter exists only for APPEAL; no `<<FILL>>` placeholders; all citations resolve.
**Output.** `ok` (no failed ERROR check), `n_errors`, `n_warnings`, `checks[]` (`id, check, pass, severity` = `error` | `warn`, `detail`, `hint` = a short revision hint when it fails), `citations_failed[]`.
**Example:** a gold memo passes with `ok: true`; moving `action_deadline` by one day fails `action_deadline` and `deadline_in_text`, with a hint like `use the appeal deadline 2026-11-01 (from assess_appealability)`.
**Errors:** `bad_input`, `access_denied`, `no_documents`, `missing_facts`.
**The model still does:** decide whether to revise, and revise. self_check never judges quality, only the deterministic rules.

## Registering with Hermes: TODO (needs the VM)
Not done and not guessed. Unknown until the Linux VM is up and the Hermes docs for the installed version have been read:
- the real `SKILL.md` format (front-matter keys, how inputs and outputs are declared) and whether Hermes skills may be plain Python entry points or must be tools in another form;
- where skills live inside the sandbox (`/sandbox/skills` is assumed by DEMO_SPEC) and how Hermes discovers them;
- how `CASE_ROOT`, `POLICY_ROOT` and `OUTPUT_ROOT` map to the sandbox paths (`/sandbox/data/cases/<id>`, `/sandbox/data/policy_library`, `/sandbox/work/output/<id>`), and whether `CASE_ROOT` can be a per-case folder with only `task.md` and `docs/` (the guard refuses a raw case folder that also holds `truth.json`);
- how a tool call's JSON arguments and result are passed (stdin, argv or function call) and any size limits, so the CLI contract may need a thin wrapper;
- whether the sandbox policy lets the skills write the events file, and where the replay UI will read it from;
- the Python version and packages available inside the sandbox image (the skills need Python 3.13 and pydantic).

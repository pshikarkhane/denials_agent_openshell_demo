# HERMES_RUN_SETUP: how the six skills are run through Hermes (Phase 4b)

Branch `phase4b-hermes`, Hermes Agent 0.21.3 in sandbox `my-hermes` (NemoClaw v0.0.137, OpenShell 0.0.116). Results: [HERMES_RUN_REPORT.md](HERMES_RUN_REPORT.md). Recording schema: [EVENTS_SPEC.md](EVENTS_SPEC.md) ("Hermes runs").
Code: `scripts/hermes/` (`run_case.py`, `sbx.py`, `build_events.py`, `rebuild_events.py`, `retag_audit.py`, `make_hermes_report.py`, `prompts/hermes_system.md`), `sandbox/state_baseline.json`, tests `sandbox/tests/test_hermes_events.py` (`pytest sandbox/tests`).

## Reproduce
```bash
export NVIDIA_INFERENCE_API_KEY=...        # judges only; the Hermes gateway already holds its own route. The key is never read or written by scripts/hermes.
. ~/.nvm/nvm.sh; nvm use 22                # nemohermes needs node 22 (sbx.py finds ~/.nvm itself)
python scripts/hermes/run_case.py --cases pilot --repeats 2 --run-id hermes-p1 [--resume] [--time-limit 900]
python -m eval.run_eval --source runs/hermes-p1-r1 --run-id judge-hermes-p1-r1    # and -r2
python scripts/hermes/make_hermes_report.py --runs hermes-p1-r1 hermes-p1-r2 --judges judge-hermes-p1-r1 judge-hermes-p1-r2 --notes docs/hermes_report_notes.md
```
If `build_events.py` changes: `python scripts/hermes/rebuild_events.py runs/hermes-p1-r1 runs/hermes-p1-r2` re-derives events, traces and summary numbers from the saved raw files.

## Step 0: staleness found and fixed
The skills installed in the sandbox before this phase were older than `skills/` (three files differed: `common/citations.py`, `parse_denial_eob/tool.py`, `self_check/tool.py`, i.e. the polish pass). `run_case.py` now restages the case from the current `skills/`, copies it in, and reinstalls the six adapters before every run;
after the install the staged skills tree was compared file by file with the repo (34 files, identical). Also found: `openshell sandbox upload <dir> /sandbox/.hermes/skills/<name>` nests the adapter as `skills/<name>/<name>/SKILL.md`; uploading to the parent `/sandbox/.hermes/skills` gives the flat layout Hermes documents (fixed in `sbx.install_case`).
Before the pilot all six skills were run inside the sandbox through the wrapper (parse, notes, assess, draft/validate and self_check returned JSON; retrieve was called with a wrong payer type by my smoke test and returned `bad_input`, and later ran in every agent run).

## Step 1: state isolation (what persists and what was done)
What Hermes keeps between sessions, found by reading `/sandbox/.hermes`, `config.yaml` and the shipped docs, and confirmed during the pilot:

| Where | What | Observed |
|---|---|---|
| `memories/MEMORY.md`, `USER.md` | agent notes injected into every later system prompt (`memory_enabled`, `user_profile_enabled` are true) | empty at start; never written in the 10 runs |
| `skills/` | agent-created skills (`skill_manage`), plus curator bookkeeping (`.curator_state`, `.curator_ledger.jsonl`, `.usage.json`) | **written in 2 of 10 runs** by Hermes' post-run background review: `healthcare/appeals-claim-review/SKILL.md` and `appeals-workflow/SKILL.md` (+ a `references/decision-logic.md`), containing case-derived workflow advice |
| `runtime/state.db` | every session, full-text searchable by the agent's `session_search` tool | 13 old Phase 0 sessions at start |
| `SOUL.md` | persona (a short "be direct" identity, Nous Research) | unchanged; its hash is checked against the baseline |
| `workspace/`, `plans/`, `hooks/`, `plugins/`, `profiles/`, `kanban.db`, `cron/` | scratch and scheduler state | not touched by the runs |
| `/sandbox/work`, `/tmp`, `/sandbox/*` | files the agent can write | the case output folder only |
| `/usr/local/share/appeals/` | the staged case (read-only, root-owned) | exactly one case at a time |

**The background review is the important one.** After a run Hermes forks a `bg-review` agent (nudge intervals: 10 turns for memory, 15 iterations for skills, both in `config.yaml`) that replays the conversation and tries to save memory or skills, logging its model calls under the same run id. In the first trial it created a skill after my reset had already finished, which would have leaked one case's learning into the next run (it even named the case and a policy tie-break).
**Chosen approach: reset and verify, not config edits.** `config.yaml` is managed by NemoClaw (config hash, no supported setter in `nemohermes`), so memory and the nudges were NOT switched off. Instead, for every run:
1. `install_case`: stage ONE case by allowlisted copy, delete every other staged case from `/usr/local/share/appeals`, copy the case in read-only, reinstall the adapters.
2. `reset_state`: delete ALL Hermes sessions through `DELETE /api/sessions/<id>` (so `session_search` finds nothing), empty `memories/`, `workspace/`, `plans/`, `hooks/`, `plugins/`, `profiles/`, remove every skill file not in the pristine baseline (`sandbox/state_baseline.json`: hashes of 328 bundled skill files, SOUL.md, `/tmp` and `/sandbox` listings), wipe `/sandbox/work`, remove files in `/tmp` and `/sandbox` that are not in the baseline, recreate the empty output folder.
3. Verify against the baseline; the run does not start if anything differs (a modified bundled file cannot be restored by this script and would stop the batch).
4. After the run: copy out the outputs, then **wait for the background review to finish** (log line `Background review complete`, or 30 s without any review activity), then record what differs from the baseline in `persistence.json`/`summary.json`, then the next run resets. The final reset leaves the sandbox at baseline (checked after the pilot: no difference).
Limits: deleted sessions are removed through Hermes' own API (rows in `state.db`, not a secure wipe); the curator bookkeeping files are removed like any other non-baseline skill file; the agent could still read the case through the read-only staged tree with `read_file` (it did read `deliverable.md` and the wrapper script, never another case, since none is present).
A case therefore saw only its own staged files and an empty work folder, and no earlier session, memory or self-made skill: 10 of 10 resets verified clean (`reset_before_run.dirty_after_reset` is `{}` in every summary).

## Step 2: instructions for Hermes
Where Hermes takes its instructions: (1) the **system prompt** is built by Hermes (identity from `SOUL.md`, memory, the index of all skills, tool definitions); (2) `POST /v1/runs` accepts `instructions`, which Hermes layers ON TOP of its core prompt (`ephemeral_system_prompt`) without replacing it; (3) skills are `SKILL.md` instruction pages in `/sandbox/.hermes/skills/<name>/`, loaded with `skill_view` and run through the `terminal` tool.
`agent/prompts/system.md` was ported to `scripts/hermes/prompts/hermes_system.md` and is sent as `instructions` with every run (SOUL.md is left alone). Changes, all about tools and output format: skills run through the wrapper (`/usr/local/share/appeals/bin/run_skill <CASE_ID> <skill> '<json>'`); the final answer is two files, `deliverable.md` and `decision.json`, in `/sandbox/work/output/<CASE_ID>/` (no delimiters; the closing chat message is one line);
an explicit "ignore other persona/memory, do not use memory/session_search/skill_manage/web/browser/delegation/cronjob/kanban"; skills `draft_deliverable` and `self_check` are given `*_path` arguments relative to the output folder (pasting a long document into a shell argument breaks on quotes); after writing the files run `self_check` and fix errors, at most twice. Rules 1-10 and the decision.json spec are verbatim, including the polish rules (7: list only applicable sections and `met` needs an evidence file AND a fact; 8: never state a value no document gives; 9: skill metadata is not evidence).
No category, trap or answer content (a test checks for forbidden words). The prompt's SHA-256 is recorded in every `summary.json` and `run_start` event (`def5c6e55eac...`).
One harness clarification was added after the first trial: the folders named in `task.md` (`/sandbox/data/...`) do not exist in the sandbox and must not be searched for (in the first trial the agent had spent five calls looking for them). Nothing else was tuned during the pilot.

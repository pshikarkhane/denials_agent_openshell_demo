# Healthcare Denial-Appeal Agent Demo

A demo of an AI agent that works claim denials end to end: it reads the case documents, finds the governing payer policy, decides whether to appeal, and drafts either an appeal letter or a decision memo explaining why not. Output is scored by an independent three-judge panel and a two-stage hallucination check.

**All data in this repository is synthetic.** There is no real PHI and no real payer text. The design spec is in [docs/DEMO_SPEC.md](docs/DEMO_SPEC.md).

## What it does

For each denial case the agent must reach one of four decisions:

| Decision | Meaning |
|---|---|
| `APPEAL` | The denial can be overturned; draft an appeal letter |
| `CORRECT_AND_RESUBMIT` | The claim has a fixable error; correct and resubmit before the deadline |
| `DO_NOT_APPEAL` | The denial is valid; write a memo explaining why |
| `ESCALATE_MISSING_DOCS` | Required documents are missing |

The deliverable is a `deliverable.md` plus a structured `decision.json`. Judgment matters as much as drafting: the agent is expected to decline an appeal when it should.

## How it is evaluated

- **Cases:** 60 synthetic denial cases, 12 denial categories × 5 cases. Each has a hidden truth file, its own binary rubric (8–15 criteria) and a gold deliverable. Five pilot cases are used for development.
- **Judge panel:** three judges (from `config/models.yaml`) grade every rubric criterion. A PASS needs a verbatim quote from the deliverable, and the panel decision is by majority. Some criteria are graded in code instead.
- **Hallucination check:** each judge flags unsupported claims. A second stage has every judge adjudicate each flag, and a flag counts if at least two judges uphold it. Only upheld *material* flags feed the headline metrics.
- **Judge validation (Phase 5):** seeded errors (`eval/mutations.py`) are injected into the gold deliverables, together with controls that must not be flagged, to measure detection, false positives, test-retest noise and judge bias.

There is deliberately no all-pass headline metric. The headline is the criterion pass rate plus the hallucination metrics.

## Repository layout

| Path | Contents |
|---|---|
| `data_gen/` | Synthetic case, document and policy-library generator, with validators |
| `data/` | Generated cases and policy library (truth, rubric and gold files are host-only) |
| `skills/` | Six offline agent skills: parse the denial, retrieve payer policy, pull clinical notes, assess appealability, draft the deliverable, self-check |
| `agent/` | Pre-sandbox agent runner (tool-calling loop) and the no-tools baseline runner |
| `eval/` | Rubric and gold generation, judge panel, hallucination check, mutation generator, validation runner |
| `scripts/` | Smoke tests, report builders, Hermes/OpenShell sandbox scripts, review tooling |
| `config/models.yaml` | API endpoint, agent model and judge models. No model IDs are hard-coded elsewhere |
| `tests/` | Offline test suite; model calls are mocked |
| `gui/` | Demo web UI (on the `gui-v1` branch; see "Demo GUI" below) |
| `docs/` | Spec, status, run reports, rubric notes, skills and events specs |

Generated outputs go to `runs/` and `logs/`, which are gitignored.

## Setup

Requires Python 3.13.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

The tests need no network and no API key.

Model calls go through a single OpenAI-compatible endpoint configured in `config/models.yaml`. The key is read only from the environment and must never be committed:

```bash
export NVIDIA_INFERENCE_API_KEY=...   # in the shell that launches your tools
```

## Common commands

```bash
# Run the agent on a case (see agent/ and docs/RUN_REPORT.md for options)
python -m agent.run_case --help

# Judge a set of deliverables (gold, a directory, or a run id)
python -m eval.run_eval --help

# Judge validation: generate mutations, estimate cost, then run
python -m eval.mutations --run-id val1
python -m eval.validation_run --run-id val1 --set mutations --estimate
python -u -m eval.validation_run --run-id val1 --set mutations --limit 5 --max-concurrency 2
```

The validation runner defaults to two concurrent calls, backs off on rate limits, caches every call and resumes finished items with `--resume`. Failed items are logged with a traceback to `runs/<run_id>/errors.jsonl`.

## Demo GUI (local)

A read-only web UI shows a case side by side (no-tools baseline vs. agent), the criteria and trace, a data room that maps the letter to its sources, a scorecard and a containment view. It runs from cached run files: there is no backend, no model calls, no API key and no network at runtime.

The GUI lives in `gui/` on the `gui-v1` branch. Check that branch out first (or use a second working copy with `git worktree add ../r1-appeals-gui gui-v1`):

```bash
git checkout gui-v1        # commit or stash local changes first
cd gui
npm install                # first time only; needs Node 22.18+
npm run dev                # then open http://localhost:5173
```

Useful pages: `/` (home), `/case/C-0005` and `/case/C-0030` (tabs: `?tab=criteria`, `?tab=trace`, `?tab=dataroom`), `/scorecard`, `/containment` and `/architecture`. Stop the server with Ctrl+C.

To serve the production build instead, run `npm run build && npm run preview` and open http://localhost:4173.

If you add run folders under `docs/samples/` or edit the run reports, refresh the cached data with `npm run cache` (Node 22.18+). `npm test` runs the GUI tests offline. More detail is in `gui/README.md` and [docs/GUI_STATUS.md](docs/GUI_STATUS.md) on that branch.

## Status

Development proceeds in phases: data generator, rubrics and judge panel, offline skills, agent runner, sandbox integration with Hermes in OpenShell, and judge validation. Current progress, results and open decisions are tracked in [docs/STATUS.md](docs/STATUS.md). Run results are in [docs/RUN_REPORT.md](docs/RUN_REPORT.md) and [docs/HERMES_RUN_REPORT.md](docs/HERMES_RUN_REPORT.md).

## Security notes

- Keys come only from the environment and are never written to files or logs. Raw model outputs are saved with keys redacted.
- Truth, rubric and gold files are host-only. The agent sees only a staged copy of the task documents and the policy library, and the judges run on the host, outside the sandbox.
- The agent model is never used as a judge or to write gold deliverables.

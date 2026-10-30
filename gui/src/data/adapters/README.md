# Run adapters

Each adapter implements `RunSource` (`../types.ts`) and turns one run folder into a `RunView`.
They are plain `.mjs` so that `scripts/build_cache.mjs` can run them with bare Node (no build step).
The app itself never imports them: it only fetches `/data/index.json` and the run files the builder wrote.

| file | source | status |
|---|---|---|
| `standin.mjs` | pre-sandbox runs per `docs/EVENTS_SPEC.md` (`docs/samples/agent_run_*`) | working |
| `hermes.mjs` | Hermes runs inside the OpenShell sandbox | stub, throws "not implemented yet" |

## Hermes (next)

The Hermes format will come from `docs/samples/hermes_run_*` once the VM work is merged. The adapter will join three inputs:
the Hermes trace, the session messages, and an `audit.jsonl` (the OCSF event log), and fill `RunView.steps` and `RunView.audit`.
Until then Hermes folders are skipped by the builder (`canRead` is false).

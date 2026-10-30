# Phase 0: Environment setup (NemoClaw + Hermes + NVIDIA inference API)

Run on 2026-10-30/31 on an Ubuntu 24.04 VM (x86_64, 8 vCPU, 15.6 GiB RAM, kernel 6.8.0-124, systemd), branch `phase0-vm`.
Everything below was run, not just read, unless marked **not tested**. Covers DEMO_SPEC §0 items 1 and 3, §2, §5 and §9 Phase 0.

## 1. Status at a glance

| Item | State |
|---|---|
| Agent model route (Nemotron 3.5 Super preview) and 3 judges | Verified (`judge_smoke.py`, all `pong`) |
| NemoClaw v0.0.137 + OpenShell + Hermes sandbox `my-hermes` | **Installed and running** (§4) |
| Hello-world through Hermes API (host port 8642) | **Pass** |
| Tool-call reliability through Hermes | **0 failures in 10** simple terminal-tool runs (§6) |
| Route swap (model change without rebuild) | **Works**, but it restarts the Hermes gateway (§7) |
| Per-step trace | Available through the API (§8) |
| Real skills inside the sandbox | **Run**; adapters registered; `parse_denial_eob` called by the agent on C-0005 (§9) |
| Containment: denied egress in the audit log | **Yes**, plus a JSONL exporter (§10). File-access denials are NOT in the log. |

## 2. Resolved model IDs (`config/models.yaml`)

All use the OpenAI-compatible `/v1/chat/completions` route of `https://inference-api.nvidia.com/v1`.

| Role | Config key | Model ID | Notes |
|---|---|---|---|
| Agent | `agent.model_id` | `nvidia/nvidia/nemotron-3.5-super-text-preview` | Preview build. Every eval report must record the exact IDs. |
| Judge | `judges.gemini` | `gcp/google/gemini-3.1-pro-preview` | Preview ID. |
| Judge | `judges.claude` | `azure/anthropic/claude-opus-4-8` | |
| Judge | `judges.gpt` | `azure/openai/gpt-5.5` | |

- The agent model returns `reasoning_content` and spends tokens thinking; give raw calls a generous `max_tokens`.
- **Never commit the API key.** Export `NVIDIA_INFERENCE_API_KEY` in the shell only. `config/models.yaml` holds the variable name. The key was once exposed in chat and must be rotated.
- Judges are reached from the host, never from inside the sandbox; synthetic data only.

## 3. Versions and requirements

| Component | Installed / pinned | Notes |
|---|---|---|
| NemoClaw (`nemohermes`) | **v0.0.137**, installed with `NEMOCLAW_INSTALL_TAG=v0.0.137` | Pin worked; `lkg` not followed. |
| OpenShell | **0.0.116** (`openshell --version`), Docker driver | Installed by NemoClaw. Do not update directly. |
| Hermes Agent | **v0.21.3** (inside the sandbox; `/health` reports it) | Labelled experimental by NVIDIA. |
| Docker | 29.9.2, used without sudo | Sandbox runs as a container managed by the OpenShell Docker-driver gateway. |
| Node / npm (host) | 22.23.4 / 10.9.9 via nvm in `~/.nvm` (no sudo) | NVIDIA minimum 22.19 / 10. nvm was installed with `PROFILE=/dev/null`, so new shells need `. ~/.nvm/nvm.sh; nvm use 22`. |
| Host Python | 3.13.18 via `uv python install 3.13`, `.venv` | Pin unchanged (`.python-version` 3.13, pydantic 2.14.1). |
| Sandbox Python | 3.13.5, pydantic **2.13.4** (`/opt/hermes/.venv`, also `/usr/bin/python3`) | Repo pins 2.14.1; the skills only need pydantic v2 and ran unchanged. |

**Resource check (NVIDIA prerequisites page, https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/prerequisites):**
minimum 4 vCPU / 8 GB RAM / 20 GB free disk; recommended 4+ vCPU / 16 GB / 40 GB free; sandbox image about 2.4 GB compressed.
This VM: 8 vCPU / 15.6 GiB (+ 3.9 GB swap) / 23 GB free before install. Meets the minimums; disk is below the 40 GB recommendation.
After the first build `docker system df` showed images 2.50 GB, and `/` had 21 GB free (never below the 8 GB threshold).

**Pre-flight results.** Ubuntu 24.04.4, x86_64, PID 1 systemd, `landlock` listed in `/sys/kernel/security/lsm`
(`lockdown,capability,landlock,yama,apparmor`). `docker run --rm hello-world` works without sudo. `unshare -n` is denied
("Operation not permitted"); `unshare -U` succeeded. Neither mattered: the sandbox runs through the Docker daemon and applied
Landlock ABI V2 (`best_effort`) fine. Outbound HTTPS (HTTP codes): inference-api.nvidia.com 401 (no key sent, reachable),
github.com 200, pypi.org 200, api.anthropic.com 404 (reachable), www.nvidia.com/nemoclaw.sh 301, registry.npmjs.org 200,
ghcr.io 401 (reachable), nvcr.io 200. No proxy variables are set or needed.
`inference-api.nvidia.com` resolves to a **private address (10.48.202.67)**, which matters for onboarding (§4).

## 4. Install and onboard (what actually worked)

```bash
# once: Node and Python (no sudo)
PROFILE=/dev/null bash nvm-install.sh; . ~/.nvm/nvm.sh; nvm install 22
curl -LsSf https://astral.sh/uv/install.sh | sh; uv python install 3.13
uv venv --python 3.13 .venv && uv pip install -p .venv/bin/python -r requirements.txt && .venv/bin/python -m pytest -q

# NemoClaw, pinned (key must already be in the environment; never put it on a command line)
export NEMOCLAW_INSTALL_TAG=v0.0.137 NEMOCLAW_DISABLE_TELEMETRY=1 NEMOCLAW_AGENT=hermes NEMOCLAW_SANDBOX_NAME=my-hermes \
       NEMOCLAW_NON_INTERACTIVE=1 NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
curl -fsSL https://www.nvidia.com/nemoclaw.sh -o nemoclaw.sh && less nemoclaw.sh   # a thin bootstrap that clones the tag
bash nemoclaw.sh --defer-onboarding        # installs the CLI; see deviation D1: it still tried to onboard and failed at step 3

# onboarding that succeeded (custom OpenAI-compatible provider, model from config/models.yaml)
export NEMOCLAW_WEB_SEARCH_PROVIDER=none NEMOCLAW_PROVIDER=custom \
       NEMOCLAW_ENDPOINT_URL=https://inference-api.nvidia.com/v1 \
       NEMOCLAW_MODEL=nvidia/nvidia/nemotron-3.5-super-text-preview \
       NEMOCLAW_TRUSTED_PRIVATE_HOSTS=inference-api.nvidia.com
export COMPATIBLE_API_KEY="$NVIDIA_INFERENCE_API_KEY"
nemohermes onboard
openshell forward start --background 8642 my-hermes     # already running after onboarding; harmless if so
```

Notes:
- **`NEMOCLAW_REASONING=true` is NOT needed**: endpoint validation passed without it once the private host was trusted.
- The first onboarding attempt failed with `SSRF preflight: no HTTP response` because the gateway host is a private IP.
  `NEMOCLAW_TRUSTED_PRIVATE_HOSTS=inference-api.nvidia.com` (that hostname only) is the documented fix.
- Onboarding took a few minutes including the image build; no sudo was needed anywhere.
- Hermes API: `http://127.0.0.1:8642/v1`, bearer token from `nemohermes my-hermes gateway-token --quiet`
  (the token is read by `scripts/phase0/hermes_client.py` at call time and never printed or stored).

## 5. Day-to-day commands (verified)

```bash
nemohermes my-hermes status                         # sandbox, model, provider, policies, Hermes version
openshell forward list; openshell forward start --background 8642 my-hermes
nemohermes my-hermes recover                        # restore forwards after reboot (not tested)
curl -s http://127.0.0.1:8642/health               # {"status": "ok", "platform": "hermes-agent", "version": "0.21.3"}
openshell sandbox exec -n my-hermes --no-tty -- <cmd> </dev/null   # run a command in the sandbox
openshell logs my-hermes --tail --source sandbox   # live audit/operational log
nemohermes my-hermes logs --follow                 # NemoClaw log view
```
- `nemohermes my-hermes connect` takes no command (only `--probe-only`); it opens an SSH shell. Use `openshell sandbox exec -n <name> -- <cmd>` for one-shot commands.
- **Always redirect stdin (`</dev/null`) or pass `--no-tty` from scripts**: `sandbox exec` otherwise hangs waiting on the inherited stdin (it ignored its own `--timeout`).
- The Hermes API serves ONE model name, **`hermes-agent`** (`GET /v1/models`). Put that in the `model` field of requests; the upstream model is set by the route (§7).

## 6. Smoke tests

| Script | What it does |
|---|---|
| `scripts/phase0/judge_smoke.py` | One call to the agent model and each judge. Stdlib only. |
| `scripts/phase0/smoke_test.sh` | Model checks, host tooling, sandbox status, `/health`, hello-world through Hermes, non-allowlisted egress check. `SKIP_SANDBOX=1` for models only. |
| `scripts/phase0/tool_call_test.py [N] [--sample FILE]` | N tool-call runs through `/v1/runs`, failure rate, failing bodies (redacted) to `logs/hermes_tool_failures.jsonl`, one trace sample. |

**Run on 2026-10-31:** every `smoke_test.sh` check passed (4 model calls `pong`; docker, node, nemohermes, openshell; sandbox status; `/health`;
hello-world reply `pong`; egress check). The two guessed CLI details were wrong and are fixed in the script:
the Hermes `model` field is `hermes-agent` (not the Nemotron id), and `connect -- <cmd>` does not exist (use `openshell sandbox exec`).
A one-word "pong" costs **9.9k to 11.4k prompt tokens** through Hermes (its system prompt + tool definitions); a one-tool run used 22.9k input tokens. Budget for this in Phase 4/9 token and latency numbers.

**Tool-call failure rate: 0/10** (`tool_call_test.py 10`): each run asked the agent to run `echo check-N-$(( (N+3)*7 ))` with the terminal tool and answer with the output; every run emitted `tool.started`, `tool.completed` (no error), `run.completed`, and the exact expected output. 3.9 to 7.5 s per run.
Limits: one simple tool, one step, a sanity check and not a reliability estimate for the six-skill chain. Before Hermes, 1 of 3 raw direct API tool-call attempts returned an API error with no body captured (2026-10-28); no such failure occurred through Hermes in 10 attempts + the other runs below. The failure logger is in place if it recurs.

## 7. Model-route swap (V1 → V2)

**Result: the model on the existing route can be changed in place, with no rebuild and no re-onboarding, but the Hermes gateway process restarts.**

How this version works (important and different from DEMO_SPEC §2.1): `openshell inference get` says "Not configured" and `inference.local` inside the sandbox returns
`cluster inference is not configured`. Hermes does not use `inference.local` here. NemoClaw writes the model into Hermes' own `/sandbox/.hermes/config.yaml`
(`model.default`, base URL = the real endpoint) and the OpenShell proxy allows that endpoint through the generated network policy (`inference-api.nvidia.com`, POST `/v1/chat/completions`, GET `/v1/models`).
The supported swap is therefore the NemoClaw command, not raw `openshell inference set`:

```bash
export COMPATIBLE_API_KEY="$NVIDIA_INFERENCE_API_KEY" NEMOCLAW_TRUSTED_PRIVATE_HOSTS=inference-api.nvidia.com
nemohermes inference set --provider compatible-endpoint --model azure/openai/gpt-5.5 --sandbox my-hermes
nemohermes inference set --provider compatible-endpoint --model nvidia/nvidia/nemotron-3.5-super-text-preview --sandbox my-hermes
```
Flags available: `--provider --model --sandbox --no-verify --endpoint-url --credential-env --inference-api (openai-completions|anthropic-messages|openai-responses) --reasoning-effort`.

Measured (sandbox id `f720dada-...` unchanged throughout, phase Ready):
| Step | Result |
|---|---|
| Swap to `azure/openai/gpt-5.5` | "Inference route synced", about 42 s. It prints "Restarting the Hermes gateway ... to apply the updated inference configuration" (gateway PID 229 → 1662). |
| Call through API | `pong`, 9,910 prompt tokens. `/sandbox/.hermes/logs/agent.log`: `API call #1: model=azure/openai/gpt-5.5 ... latency=4.8s` |
| Swap back to Nemotron | about 42 s, same message. |
| Call through API | `pong`, 11,381 prompt tokens; log: `model=nvidia/nvidia/nemotron-3.5-super-text-preview ... latency=2.1s`. `nemohermes my-hermes status` shows the Nemotron model. |

The response's `model` field always says `hermes-agent`; to see the real upstream model use `agent.log` (`API call #N: model=...`) or `GET /api/sessions` (`model`).
**Caveats for V2 (R1's checkpoint):** tested only between two models on the *same* endpoint and provider. A checkpoint served from another endpoint needs `--endpoint-url`, `--credential-env` (the env var holding that endpoint's key) and probably `--inference-api`, plus `NEMOCLAW_TRUSTED_PRIVATE_HOSTS` if it is on a private address, and the sandbox network policy must allow that host (the swap command did not need a policy change here only because the host was unchanged). **Not tested.** Plan on a ~40 s gateway restart per swap and do not swap during a run.

## 8. Per-step trace (for the GUI)

Three sources, all through the forwarded port 8642 (bearer token). A real sample is in `docs/samples/hermes_trace_sample.json`
(one passing `tool_call_test.py` run: its SSE events plus its message history).

1. **Live events: `POST /v1/runs` then `GET /v1/runs/{run_id}/events`** (Server-Sent Events, `data: {json}` lines). Request body `{"input": "<text>"}`; response `{"run_id", "status": "started"}`.
   Event objects always carry `event`, `run_id`, `timestamp` (epoch seconds). Types seen:
   - `tool.started` `{tool, preview}`: `preview` is a short rendering of the arguments (e.g. `echo hello-$((6*7))`), not the full JSON.
   - `tool.completed` `{tool, duration (s), error (bool)}`: **no result body**.
   - `message.delta` `{delta}`: streamed answer text. `reasoning.available` `{text}`.
   - `run.completed` `{output, usage{input_tokens, output_tokens, total_tokens}}`.
   Other event kinds exist in `gateway/platforms/api_server_runs.py` (subagent lifecycle events, approvals; `run.failed` is not confirmed because no run failed).
2. **Full arguments and results: `GET /api/sessions/{run_id}/messages`** (the run id is the session id). Returns `data: [message]` with `role`, `content`, `timestamp`,
   assistant messages carry `tool_calls` (id, function name and JSON arguments) and `reasoning`/`reasoning_content`; `role: "tool"` messages carry `tool_name`, `tool_call_id` and the tool's result string
   (e.g. `{"output": "check-1-28", "exit_code": 0, "error": null}`). `GET /api/sessions` lists runs with `model`, `message_count`, `tool_call_count`, token counts, `api_call_count`.
   **Join SSE events and messages by order / `tool_call_id` to build one row per step: name, arguments, result, duration.**
3. **Logs inside the sandbox:** `/sandbox/.hermes/logs/agent.log` has one line per API call (`API call #1: model=... in=... out=... latency=...s`) and per tool (`tool terminal completed (0.08s, 53 chars)`); `gateway.log`, `errors.log` alongside.
   Our own skills also write `skill_events.jsonl` (schema in `docs/SKILLS_SPEC.md`).

The Hermes dashboard is served at **18789** in this version (container-internal 19119), not 9119. I did not inspect it (that command was declined); the API above covers the trace need.
`scripts/phase0/hermes_client.py` has `start_run`, `stream_events`, `session_messages`.
`GET /v1/skills` returns HTTP 500 in Hermes 0.21.3 (`_find_all_skills() got an unexpected keyword argument 'include_editorial'` in `errors.log`): a bug in the installed version, so skill discovery cannot be checked through that endpoint.

## 9. The real skills inside the sandbox

**Hermes skill format** (read from the docs shipped in the image, `/opt/hermes/website/docs/developer-guide/creating-skills.md`):
a skill is a folder with `SKILL.md` (YAML front matter: `name` (`[a-z0-9._-]`, ≤ 64, underscores allowed), `description`, `version`, `author`, `metadata.hermes.tags` / `requires_tools` ...; then markdown: When to Use / Procedure / Pitfalls / Verification).
It is an *instruction document*: the agent loads it with `skill_view` and follows it, usually by running a command with its `terminal` tool. Helper scripts live in the skill folder (`${HERMES_SKILL_DIR}`). There is no Python entry-point registration for this style.
Discovery: Hermes scans `~/.hermes/skills/` (= `/sandbox/.hermes/skills/`, the primary dir) and any `skills.external_dirs` in `config.yaml`; the skill index goes into the system prompt.
(The Phase 3 stubs in `skills/*/SKILL.md` say `format: pending Hermes docs`; they were left untouched.)

**Adapters.** `sandbox/make_hermes_skills.py` generates `sandbox/hermes_skills/<name>/SKILL.md` for all six skills; descriptions come from `skills/<name>/SKILL.md` and argument lists from each skill's pydantic `Input`, so they cannot drift.
Each tells the agent to run `/usr/local/share/appeals/bin/run_skill <CASE_ID> <skill> '<json>'` (`sandbox/run_skill.sh`), a wrapper that binds `CASE_ROOT`, `POLICY_ROOT`, `OUTPUT_ROOT`, `SKILL_EVENTS_FILE`, `PYTHONPATH`; the model never supplies roots.

**Safe staging.** `scripts/phase0/stage_case.py C-0005` builds `sandbox/staging/C-0005/` (gitignored via `sandbox/.gitignore`) by *allowlisted* copy:
`case/task.md`, `case/docs/**` (regular files only), `policy_library/*` (regular files only), `skills/**/*.py` and `SKILL.md` (no tests, caches or other files).
It then re-walks the output and verifies every file against the allowlist, refuses symlinks, any `truth.json` / `rubric.json` / `gold` / `attacks` name anywhere, bad case ids and sub-folders in the policy library, and deletes the staging dir on any violation.
Tests: `sandbox/tests/test_stage_case.py` (13 tests: allowlist exactness with planted secrets, fail-closed cases, real C-0005 output). `agent/staging.py` (Phase 4) uses a deny-list; this one is an allow-list, so a new file type cannot leak.
Run the sandbox tests with `.venv/bin/python -m pytest sandbox/tests -q` (root `pytest.ini` only collects `tests/`).

**"Mount" (read-only) path.** OpenShell has no bind-mount option; `openshell sandbox upload` runs as the unprivileged `sandbox` user and can only write under `/sandbox` and `/tmp`, which are writable roots (Landlock cannot make a subfolder of a writable root read-only).
`sandbox/install_into_sandbox.sh C-0005` therefore uses `docker cp` / `docker exec -u root` on the sandbox container (no sudo; the user is in the `docker` group) to place the staged tree at
`/usr/local/share/appeals/C-0005/{case,policy_library,skills}` (root-owned, mode `a-w`; `/usr` is already `read_only` in the sandbox Landlock policy) and the wrapper at `/usr/local/share/appeals/bin/run_skill`.
Adapters go to `/sandbox/.hermes/skills/<name>/` (Hermes' primary skills dir, via `openshell sandbox upload`), and outputs to `/sandbox/work/output/<case>/` (the only writable place).
Limits: the copy lives in the container filesystem, so it is lost if the sandbox is recreated (the spec's goal, a custom image with everything baked in, is still the long-term answer); the adapters sit in a dir the agent can edit (`skill_manage`); I did not move them to a read-only `skills.external_dirs` because `config.yaml` is managed by NemoClaw (config hash).

**Runtime check inside the sandbox:** Python 3.13.5 and pydantic 2.13.4 are already in the image (`/opt/hermes/.venv`), so the stdlib+pydantic skills run with no installs and no runtime network. If an image ever lacks pydantic, add it at image build time (a wheel baked into the image / vendored `site-packages` under the read-only skills tree), not with `pip` at run time.

**Agent call on C-0005 through the API** (`docs/samples/hermes_skill_run_C-0005.json`): prompt asked the agent to use `parse_denial_eob` for case C-0005 and answer with claim number, CARC and appeal-by date.
Events: `tool.started skill_view parse_denial_eob` → `tool.started terminal /usr/local/share/appeals/bin/run_skill C-0005 parse_denial_eob '{}'` (0.2 s, no error) → `run.completed`: **`6268311, CO-50, 2027-01-13`**, matching the tool's JSON (claim 6268311, CARC CO-50, `appeal.by_date` 2027-01-13). The skill wrote its event lines to `/sandbox/work/output/C-0005/skill_events.jsonl`.
All six adapters were installed the same way (the install script loops over them). I also ran the other five through the wrapper directly: `pull_clinical_notes` (4 documents), `assess_appealability` (facts), `draft_deliverable validate_decision` (valid=false for `{}`), `retrieve_payer_policy` (status `none` for a made-up payer), `self_check` (`bad_input` without a deliverable): all executed. Only `parse_denial_eob` was driven by the agent.

**Visibility check from inside the sandbox** (same session): `ls` shows only `case/` (task.md, docs/), `policy_library/`, `skills/` under the case dir, all root-owned and not writable by the `sandbox` user (`touch`/`rm` → Permission denied);
`find /` (excluding Hermes' own package and `/usr/lib`) finds no file or folder named `truth.json`, `rubric.json`, `gold` or `attacks`; `cat` of `truth.json`, `rubric.json`, `gold/decision.json` under the staged path, `/sandbox/data/...` and the host repo path all return "No such file or directory";
the skill path guard refuses `paths: ["../truth.json"]` with `access_denied`. This checks the staged copy; it does not prove the model could not read a host path (the host repo is not in the container at all).

## 10. Containment smoke test

From inside the sandbox, `curl -X POST https://collector.invalid/upload` fails with `CONNECT tunnel failed, response 403`, and the audit log shows:
```
[1793399522.063] [sandbox] [OCSF ] [ocsf] NET:OPEN [MED] DENIED /usr/bin/curl(4337) -> collector.invalid:443 [policy:- engine:opa] [reason:endpoint collector.invalid:443 is not allowed by any policy]
```
`example.com` and `live-tail-test.invalid` are denied the same way. Allowed traffic is logged too (`HTTP:POST ALLOWED POST http://inference-api.nvidia.com:443/v1/chat/completions [policy:... engine:l7]`).

**Where the logs live**
- Inside the sandbox: `/var/log/openshell.<date>.log` (all events, ISO timestamps, `... OCSF NET:OPEN ...`); `/var/log/openshell-ocsf.<date>.log` exists but was empty (the JSON OCSF export is not on by default).
- Through the gateway (host): `openshell logs my-hermes [--source sandbox] [--since 5m] [-n N]`; the raw gateway log is `~/.local/state/nemoclaw/openshell-docker-gateway/openshell-gateway.log`.
- **Tail in real time:** `openshell logs my-hermes --tail --source sandbox | grep --line-buffered OCSF`
  or as JSONL: `openshell logs my-hermes --tail --source sandbox | python scripts/phase0/export_audit.py - --only-denied` (verified: a denial triggered while tailing arrived within seconds).

**`scripts/phase0/export_audit.py`** converts OCSF lines to JSONL: `ts`, `event_class` (`NET:OPEN`, `HTTP:POST`, `PROC:LAUNCH`, `SSH:OPEN`, `CONFIG:*` ...), `severity`, `result` (`allowed` | `denied` | null), `target`, `actor` (binary(pid)), `policy`, `engine`, `reason`, `raw`.
Sources: `--sandbox my-hermes [--since 30m] [-n N]`, a saved file, or `-` for streaming stdin. Sample: `docs/samples/audit_sample.jsonl` (10 events). Tests: `sandbox/tests/test_export_audit.py`.
Counts in the log of this session: 803 OCSF events, 26 denied.

**Gaps relevant to DEMO_SPEC §5.2/5.3:**
- **Blocked file reads/writes are not audited.** `cat /etc/shadow`, `ls /root`, `touch /usr/local/share/appeals/x` fail with "Permission denied" (Landlock/DAC) and **produce no log event**. There is no `file_read` event class in v0.0.137. Attack A2/A3 (file read outside the data dir; write to an export path) can be shown as blocked, but not as an audit entry; only network denials (A1) appear in the log.
- Hermes itself triggers denied requests in the background (github.com, openrouter.ai, raw.githubusercontent.com from the Hermes Python process); the audit panel needs a filter or an explanation, or those hosts should be allowlisted/silenced deliberately.
- The default sandbox policy still contains the `pypi` preset (and an `nvidia` preset for `integrate.api.nvidia.com`); the spec's "remove runtime PyPI" step (DEMO_SPEC §5.1 step 6) was **not done** (out of Phase 0 scope).

## 11. Deviations from NVIDIA's docs / the spec, and surprises

| # | What | Detail |
|---|---|---|
| D1 | `--defer-onboarding` did not defer | `bash nemoclaw.sh --defer-onboarding` with the NEMOCLAW_* variables set still ran `nemohermes onboard` and it failed (D2); re-run `nemohermes onboard` after fixing. |
| D2 | Private-IP gateway host | Endpoint validation failed (`SSRF preflight: no HTTP response`) until `NEMOCLAW_TRUSTED_PRIVATE_HOSTS=inference-api.nvidia.com`. Documented as a corporate-network fix. |
| D3 | `NEMOCLAW_REASONING` not needed | The docs suggest it for reasoning models; validation passed without it. |
| D4 | No systemd user bus | The "managed service" gateway start failed (`Failed to connect to bus`); NemoClaw fell back to a standalone gateway process (`~/.local/state/nemoclaw/openshell-docker-gateway/`). After a reboot run `nemohermes my-hermes recover` (**not tested**). |
| D5 | Dashboard port | Dashboard forward is 18789 here (internal 19119), not 9119 as in the task text; no `NEMOCLAW_HERMES_DASHBOARD` was set. Not inspected. |
| D6 | Model route is not `inference.local` | Spec §2.1 assumed OpenShell's inference route could be updated without restarting Hermes. Here the route lives in Hermes' config and a swap restarts the Hermes gateway (about 42 s). |
| D7 | `connect -- <cmd>` does not exist; `sandbox exec` hangs without closed stdin | See §5. |
| D8 | `/v1/skills` returns HTTP 500 | Hermes 0.21.3 bug (§8). |
| D9 | Hermes prompt overhead | 9.9k to 11.4k prompt tokens for a one-word reply; 22.9k for one tool call. |
| D10 | No bind mounts, no audited file denials | §9 and §10. |
| D11 | Log noise | Hermes background calls are denied and logged; `tirith` (a security scanner) is missing in the image (`.tirith-install-failed`, warning in `agent.log`). |
| D12 | Prerequisite-page claim | The docs mention the installer may install Node via nvm; here Node was installed beforehand, so that path was not exercised. |

## 12. Open items for you
1. Rotate the API key that was pasted into chat (exposed).
2. Decide whether V2 (R1 checkpoint) will be served from another endpoint (then test `--endpoint-url`/`--credential-env` with it) and whether a ~40 s restart per swap is acceptable.
3. Decide how to ship the skills and case data long-term (custom image per DEMO_SPEC §2.1) given there are no bind mounts; `sandbox/install_into_sandbox.sh` is the interim path.
4. Decide on the audit story for file access (not logged) and on the `pypi`/`nvidia` presets and Hermes background hosts.
5. Hermes agent system prompt and the loop are not built (stopped after Phase 0 as instructed); note the per-call prompt overhead when you design them.

## Sources
- [NemoClaw Quickstart with Hermes](https://docs.nvidia.com/nemoclaw/latest/user-guide/hermes/get-started/quickstart)
- [NemoClaw Prerequisites](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/prerequisites)
- [Set up an OpenAI-compatible endpoint](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/inference/custom-endpoints/set-up-openai-compatible-endpoint)
- [NVIDIA/NemoClaw on GitHub](https://github.com/NVIDIA/NemoClaw)
- Hermes docs shipped in the sandbox image: `/opt/hermes/website/docs/developer-guide/creating-skills.md`, `.../user-guide/features/skills.md`; API source `/opt/hermes/gateway/platforms/api_server*.py`

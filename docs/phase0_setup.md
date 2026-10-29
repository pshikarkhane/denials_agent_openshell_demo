# Phase 0: Environment setup (NemoClaw + Hermes + NVIDIA inference API)

Researched 2026-10-28 against the current NVIDIA docs (links at the bottom). This covers DEMO_SPEC §0 items 1 and 3, and §9 Phase 0.
Exit criteria: hello-world agent call through Hermes, plus one call to each judge.

## 1. Status at a glance

| Item | State |
|---|---|
| Agent model route (Nemotron 3.5 Super) | **Verified**: 1 plain call and 2 tool-call tests via the NVIDIA inference API |
| Gemini 3.1 Pro / Claude Opus 4.8 / GPT-5.5 judges | **Verified**: one call each returns `pong` |
| NemoClaw + Hermes sandbox | **Not yet installed.** Commands below are from the docs and not yet run. This machine is macOS arm64, and the docs' tested platform is Ubuntu 24.04 (§3). |
| `openshell` / `nemoclaw` on this machine | Not installed |

## 2. Resolved model IDs (`config/models.yaml`)

Resolved by `GET https://inference-api.nvidia.com/v1/models`. All use the OpenAI-compatible `/v1/chat/completions` route.

| Role | Config key | Model ID | Notes |
|---|---|---|---|
| Agent | `agent.model_id` | `nvidia/nvidia/nemotron-3.5-super-text-preview` | **Decided.** This is a *preview* build of 3.5 Super. `nemotron-3.5-super-vl` and `nemotron-3-super-v3` were also listed but not chosen. Every eval report must record the exact model IDs used. |
| Judge | `judges.gemini` | `gcp/google/gemini-3.1-pro-preview` | Preview ID, not GA. |
| Judge | `judges.claude` | `azure/anthropic/claude-opus-4-8` | Also available as `aws/anthropic/bedrock-claude-opus-4-8`. Opus 4.8 is available, resolving §0 item 1. Newer Opus 5 / 5.5 also exist. |
| Judge | `judges.gpt` | `azure/openai/gpt-5.5` | |

Notes:
- The agent model returns a `reasoning_content` field and spends tokens thinking, so give calls a generous `max_tokens` (the scripts use 1000).
- **Do not commit the API key.** Export it in your shell: `export NVIDIA_INFERENCE_API_KEY=<key>`. `config/models.yaml` holds only the variable name.
  **Security: the API key was exposed in a chat session and must be rotated.** Keys are read only from environment variables, never from files, and the model client redacts the key from anything it logs.
- Spec §0 item 6: the judges are reached through NVIDIA's gateway, not directly from OpenAI/Google/Anthropic. Synthetic data only goes to them, from the host, never from inside the sandbox.

## 3. Pinned versions

| Component | Pin | Source |
|---|---|---|
| NemoClaw | **`v0.0.137`** (commit `8e63c869ae1fe5f5044a102b9cfcdde29b18fd9a`) | This is what the moving `lkg` (last-known-good) tag points to today. Newer tags exist (up to `v0.0.139`), and there is a `v1.0.0-rc1`. |
| OpenShell | Not versioned in the docs. NemoClaw installs it and tells you not to update it directly. **After install, record `openshell --version` here.** | |
| Hermes agent | Installed inside the sandbox image by NemoClaw. After install, record `nemohermes my-hermes connect` then `hermes --version`. | |
| Node.js | ≥ 22.19 (host has v26.11.1), npm ≥ 10 (host has 11.20.0) | Prerequisites page |
| Docker | Host has client 29.8.0. Docker Desktop or Colima must be **running**. | |
| Hardware | 4 vCPU, 8 GB RAM (16 recommended), 20 GB free disk (40 recommended) | |

To pin, set `NEMOCLAW_INSTALL_TAG=v0.0.137` and leave `NEMOCLAW_INSTALL_REF` unset, as the docs describe.
Without a pin the installer follows `lkg`, which can move.

**Platform caveat.** The docs' tested platforms are DGX OS and Ubuntu 24.04. macOS (Apple Silicon) is supported through Colima or Docker Desktop, with these extras:
- With Homebrew Colima: `brew install colima docker`. Colima alone does not give you the `docker` CLI.
- Xcode Command Line Tools are recommended.
- Hermes is labeled **experimental** by NVIDIA (§0 item 3).

The spec says to use a Linux host. If the macOS install fails, use a Linux VM or host, and fall back to the Docker-only runner (§6 below).

## 4. Install and onboard

All commands run on the host.

```bash
# 0. Prereqs (macOS): start Docker Desktop, or: brew install colima docker && colima start --cpu 4 --memory 12 --disk 60
docker info >/dev/null && echo "docker ok"

# 1. Credentials (shell only, never in files)
export NVIDIA_INFERENCE_API_KEY=<your key>
export COMPATIBLE_API_KEY="$NVIDIA_INFERENCE_API_KEY"   # used by the NemoClaw "custom" provider

# 2. Pin NemoClaw and choose Hermes
export NEMOCLAW_INSTALL_TAG=v0.0.137
export NEMOCLAW_DISABLE_TELEMETRY=1
export NEMOCLAW_AGENT=hermes
export NEMOCLAW_SANDBOX_NAME=my-hermes

# 3. Non-interactive onboarding with the NVIDIA inference API as a custom OpenAI-compatible provider
export NEMOCLAW_NON_INTERACTIVE=1
export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
export NEMOCLAW_WEB_SEARCH_PROVIDER=none
export NEMOCLAW_PROVIDER=custom
export NEMOCLAW_ENDPOINT_URL=https://inference-api.nvidia.com/v1
export NEMOCLAW_MODEL=nvidia/nvidia/nemotron-3.5-super-text-preview
export NEMOCLAW_REASONING=true        # see note below
curl -fsSL https://www.nvidia.com/nemoclaw.sh | bash
```

Notes:
- The first build can take several minutes (the sandbox image is about 2.4 GB compressed).
- The onboarding validates the endpoint. `NEMOCLAW_REASONING=true` skips the tool-calling and streaming checks and is documented for "reasoning-only" models. Nemotron returns reasoning *and* handles tool calls (verified), so **try without it first**, and set it only if validation fails.
- The docs also list a built-in `build` provider ("NVIDIA Endpoints", key `NVIDIA_INFERENCE_API_KEY`). It targets NVIDIA's public catalog, not this internal gateway, so `custom` is the safer choice here.
- Interactive alternative: `curl -fsSL https://www.nvidia.com/nemoclaw.sh | NEMOCLAW_AGENT=hermes NEMOCLAW_SANDBOX_NAME=my-hermes bash`, answer `n` to the express prompt, then pick "OpenAI-compatible (custom)".
- Install without onboarding: append `bash -s -- --defer-onboarding`, then run `nemohermes onboard`.
- If a corporate-network host is rejected, the docs say to set `NEMOCLAW_TRUSTED_PRIVATE_HOSTS` to that hostname only.

## 5. Verify and day-to-day commands

```bash
nemohermes my-hermes status                         # sandbox state
openshell forward list                              # is 8642 forwarded?
openshell forward start --background 8642 my-hermes # restart forward (e.g., after reboot)
nemohermes my-hermes recover                        # restore forwards after reboot
curl -sf http://127.0.0.1:8642/health               # Hermes API health
nemohermes my-hermes gateway-token --quiet          # bearer token for the Hermes API
nemohermes my-hermes connect                        # shell inside the sandbox; run `hermes`
nemohermes my-hermes logs --follow                  # live logs
nemohermes my-hermes inference set --help           # route swap (V1 to V2), see Section 7
```

The Hermes API base URL is `http://127.0.0.1:8642/v1` (OpenAI-compatible), authenticated with `Authorization: Bearer <gateway-token>`.
The optional dashboard needs `NEMOCLAW_HERMES_DASHBOARD=1` at onboarding (port 9119) and is not needed for this demo.

## 6. Smoke tests (in this repo)

| Script | What it does |
|---|---|
| `scripts/phase0/judge_smoke.py` | One call to the agent model and to each of the 3 judges, with up to 3 attempts each. Exits non-zero on any failure. Stdlib only. |
| `scripts/phase0/smoke_test.sh` | Runs the model API tests, then host tooling, sandbox status, `/health`, a hello-world call through Hermes, and an egress-block check. `SKIP_SANDBOX=1` runs only the model checks. |

```bash
export NVIDIA_INFERENCE_API_KEY=<your key>
python3 scripts/phase0/judge_smoke.py                       # models only
SKIP_SANDBOX=1 bash scripts/phase0/smoke_test.sh            # same, via the wrapper
SANDBOX=my-hermes bash scripts/phase0/smoke_test.sh         # full Phase 0 exit check
```

**Results run on 2026-10-28 (models only):**

```
PASS  agent          nvidia/nvidia/nemotron-3.5-super-text-preview  0.6s  reply='pong'
PASS  judge.gemini   gcp/google/gemini-3.1-pro-preview              2.9s  reply='pong'
PASS  judge.claude   azure/anthropic/claude-opus-4-8                1.4s  reply='pong'
PASS  judge.gpt      azure/openai/gpt-5.5                           1.5s  reply='pong'
```

Also verified: the agent model returns a well-formed `tool_calls` response (`get_weather({"city":"Paris"})`) on 2 of 3 attempts. The first attempt returned an API error with no `choices` field; I did not capture the body. Phase 4 needs retry logic and a tool-call success metric (spec §10).

**Failure logging and retries.** `scripts/phase0/_common.py` logs every failed model call (status, response headers, full body, key redacted) to `logs/model_errors.jsonl`. `chat_with_retry()` makes up to 3 attempts with exponential backoff (1 s, 2 s) and is used for all model calls. Unit tests: `tests/test_model_client.py`.

The sandbox half of `smoke_test.sh` is **written but not yet run**, because NemoClaw is not installed. Two lines are unverified guesses at CLI syntax: the Hermes `model` field in step 4 and `connect -- <cmd>` in step 5. Check them on first run.

### Docker-only fallback runner (spec §10)
Not built in Phase 0. If NemoClaw cannot be installed, Phase 3+ can target any OpenAI-compatible endpoint with the same `config/models.yaml`. Decide after the first install attempt.

## 7. Model-route swap (V1 to V2)

NemoClaw docs: `nemoclaw <sandbox> inference set --endpoint-url <url>`. The page does not document a flag for changing the **model**, so check `nemohermes my-hermes inference set --help` after install. This is the Phase 9 swap path, so confirm it supports a model change without a rebuild.

## 8. Open items for you

1. ~~Confirm the Nemotron ID~~ Decided: `nemotron-3.5-super-text-preview`.
2. Decide the host: install on this Mac (supported with caveats) or a Linux machine (tested path).
3. Rotate the API key that was pasted into chat (exposed; must be rotated).
4. After install, fill in the OpenShell and Hermes versions in §3.

## Sources
- [NemoClaw Quickstart with Hermes](https://docs.nvidia.com/nemoclaw/latest/user-guide/hermes/get-started/quickstart)
- [NemoClaw Prerequisites](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/prerequisites)
- [Choose an inference provider](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/inference/learn-and-choose/choose-inference-provider)
- [Set up an OpenAI-compatible endpoint](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/inference/custom-endpoints/set-up-openai-compatible-endpoint)
- [NVIDIA/NemoClaw on GitHub](https://github.com/NVIDIA/NemoClaw) (tags checked with `git ls-remote`)

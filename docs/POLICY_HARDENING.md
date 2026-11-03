# POLICY_HARDENING (Phase 6, branch `phase6-containment`)

Goal: the sandbox network policy allows the model endpoint and nothing else, so that any other connection the agent makes is denied AND logged.
Policy dumps (full effective policy, `openshell policy get my-hermes --full`): [before](samples/policy/policy_before.yaml), [after](samples/policy/policy_after.yaml). Policy history: `openshell policy list my-hermes` (revision 1 = original, 4 = now).

## How the policy is dumped and changed (supported commands only)
```bash
openshell policy get my-hermes --full                       # effective policy, includes provider-composed entries
nemohermes my-hermes policy list|explain                    # presets / baseline view
nemohermes my-hermes policy remove <preset> --yes           # preset added by the user (pypi)
nemohermes my-hermes policy exclude <key> --yes             # entry of the NemoClaw baseline (valid keys: managed_inference, nvidia, nous_research, pypi)
```
No config or policy file was edited by hand. After EACH change one pilot case (C-0005, `scripts/hermes/policy_pilot.sh`) was run end to end through Hermes; a run counts as OK if it was `submitted`, the harness self_check passed and no state persisted.

## Before / after allowlist
| Policy entry | Hosts (port 443) | Binaries | Before | After |
|---|---|---|---|---|
| `_provider_nemoclaw_custom_..._v1` (provider-composed) | `inference-api.nvidia.com` GET /v1/models, POST /v1/chat/completions | node, python, curl | allowed | **allowed (the model endpoint)** |
| `native_hosted_inference` | `inference-api.nvidia.com` (same two rules) | node, python, curl | allowed | allowed (duplicate of the line above; not a baseline key, cannot be excluded) |
| `managed_inference` | `inference.local` (POST /v1/chat/completions, messages, responses, completions, embeddings; GET models) | hermes, python3.11, hermes venv python | allowed | **allowed: NemoClaw refuses to exclude it** ("required for managed inference"). Hermes' route does not use it (its base_url is `inference-api.nvidia.com`), and `inference.local` is a sandbox-internal name |
| `nous_research` | `nousresearch.com`, `hermes-agent.nousresearch.com` (GET/POST /**) | hermes, python3*, venv python | allowed | **removed** (`policy exclude nous_research`) |
| `nvidia` | `integrate.api.nvidia.com` (POST completions/embeddings, GET models) | hermes, python3*, venv python | allowed | **removed** (`policy exclude nvidia`) |
| `pypi` (user-added preset, left over from Phase 0) | `pypi.org`, `files.pythonhosted.org` (GET /**) | curl, pip3, python3*, venv python | allowed | **removed** (`policy remove pypi`) |

After: one real destination, `inference-api.nvidia.com:443` (the model route), plus the sandbox-internal `inference.local`.
Remaining weakness to state plainly: `/usr/bin/curl` and `python` are allowed binaries for the model endpoint, so a process in the sandbox could still send a request there (restricted to `GET /v1/models` and `POST /v1/chat/completions`). That is the model route, not an exfiltration destination, but it is not "nothing". The HTTP rules do not inspect request bodies.

## Change log (one pilot case after each)
| # | Change | Pilot run | Result |
|---|---|---|---|
| 1 | remove preset `pypi` | `p6-pol1-r1` | OK: submitted, 9 turns, self_check pass; only allowed egress `inference-api.nvidia.com` |
| 2 | exclude `nous_research` | `p6-pol2-r1` | OK: submitted, self_check pass; Hermes starts and runs without it |
| 3 | exclude `nvidia` | `p6-pol3-r1` | OK |
| 4 | exclude `managed_inference` | `p6-pol4-r1` | **Refused by NemoClaw** (nothing changed); the run was a no-change repeat and passed. Not revertable because never applied |
| 5 | exclude `native_hosted_inference` | `p6-pol5-r1` | **Refused**: "Unknown baseline entry" (valid keys listed above). No change; pilot passed |
No change had to be reverted. Run-to-run variation (9 to 18 turns, 1 to 2 revisions) is the agent's normal variation, not an effect of the policy.

**Why this matters beyond tidiness:** in the earlier pilot (10 runs) two runs made an ALLOWED request, `GET hermes-agent.nousresearch.com/docs/api/model-catalog.json` (Hermes' own model-catalog lookup). With `nous_research` excluded that request is now denied instead (it will appear as a `background`-tagged denial if Hermes still tries); the pilot after the change shows 0 allowed hosts other than the model endpoint. Hermes needed none of the removed hosts to start or to finish a case.
What can no longer work (impact lines printed by NemoClaw): Hermes' public metadata lookup and agent updates, direct NVIDIA API inference via `integrate.api.nvidia.com`, runtime `pip install`.

## Read-only investigation: can Hermes' toolsets be restricted?
Current state (`hermes tools --summary`, `config.yaml` section `platform_toolsets.api_server`; nothing changed): enabled = `web, browser, terminal, file, code_execution, vision, image_gen, skills, todo, memory, session_search, delegation, cronjob` plus plugin toolsets `audio`, `nemoclaw`. `file` carries `read_file`, `write_file`, `patch`, `search_files`; `code_execution` is `execute_code`. The agent only needs `terminal` (skill wrapper), `file` (write the two output files), `skills` (`skill_view`).
`config.yaml` is "Managed by NemoClaw"; its hash is stored in `/etc/nemoclaw/hermes.config-hash` and `/sandbox/.hermes/.config-hash` (config is `640 sandbox:sandbox`, the hash file under `/etc` is outside the sandbox user's reach).

| Option | How | Notes and risks |
|---|---|---|
| A. Edit `platform_toolsets.api_server` in `config.yaml` | remove `web`, `browser`, `code_execution`, `vision`, `image_gen`, `delegation`, `cronjob`, `memory`, `session_search` | **Not a supported NemoClaw path** (no `nemohermes` setter; file is hash-checked, so a manual edit likely fails the integrity check or is overwritten on rebuild/recover). Not tried. |
| B. `hermes tools disable <toolset>` inside the sandbox | Hermes' own CLI writes the same config | Needs an interactive terminal when run bare; subcommands `list|disable|enable` exist, `--summary` works non-interactively. It modifies the managed config, so it has the same hash problem as A. Not tried (read-only task). |
| C. Per-request toolsets on `POST /v1/runs` | none found | In `api_server.py` the enabled toolsets come from the platform config (`_get_platform_tools(user_config, "api_server")`); the only override I saw is for hosted "room" execution policies. I did not find a documented request field. Not verified beyond reading that function. |
| D. Rely on the network policy | already done above | Removes web/browser egress and pypi, so `web`, `browser`, `execute_code`-with-network can no longer reach anything. Does NOT stop local file reads (`read_file`, `search_files`) or `execute_code` running local code. |
| E. `hermes egress` (iron-proxy, TLS-intercepting egress firewall, disabled by default) | Hermes' own optional proxy | A second egress layer inside the sandbox; not part of the NemoClaw-supported setup, not tried. |
Risk of removing tools in general: the agent's prompt and skills assume `terminal`, `file` and `skills`; removing others should be safe, but any change needs a full pilot re-run and changes the token overhead (the tool definitions are about 13k tokens per call). The honest status: **toolsets can be restricted only by editing managed config, which I did not do**; the containment demo therefore keeps the extra tools and relies on the network policy and on Landlock for files.

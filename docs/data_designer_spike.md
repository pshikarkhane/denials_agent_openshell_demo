# NeMo Data Designer spike (time-boxed)

Date: 2026-10-28. Question: can NeMo Data Designer call our OpenAI-compatible endpoint, and should we use it for document generation?

## Verdict: NO-GO for now (it works, but we don't need it yet)

| Test | Result |
|---|---|
| Install | `pip install data-designer` (v0.9.7, Python 3.13) in a throwaway venv, about 1 minute |
| Custom OpenAI-compatible endpoint | **Works.** `dd.ModelProvider(provider_type="openai", endpoint="https://inference-api.nvidia.com/v1", api_key="NVIDIA_INFERENCE_API_KEY")`; `api_key` is the *name* of an env var, so no key is stored in code |
| Tiny generation | 3 rows: 1 category-sampler column + 1 `LLMTextColumnConfig`, model `azure/anthropic/claude-opus-4-8`. 3 of 3 requests succeeded in about 9 s (`preview(num_records=3)`) |
| Model ID passthrough | Our gateway model IDs (with slashes) are accepted as-is |

Docs used: the v0.9.5 [custom model settings](https://docs.nvidia.com/nemo/datadesigner/v0.9.5/concepts/models/custom-model-settings.md) page (the installed version was 0.9.7, and the API calls above worked unchanged). I did not read further than needed.

## Why NO-GO
1. **Our hard requirements are custom checks, not column generation.** Pilot notes must contain verbatim evidence sentences, use only allowed dates and codes, and avoid certain words. These need a generate-validate-retry loop with feedback. Data Designer has validators, but wiring this up is more effort than the ~100 lines of plain Python that already do it.
2. **Everything else is deterministic.** Codes, dates, amounts and templates are plain Python; the LLM only writes prose for 11 policies and a handful of notes.
3. **Extra dependency weight** (three packages plus transitive dependencies) and a second place for retry/logging behaviour, when `chat_with_retry` already gives us retries and a redacted failure log.
4. We would have to carry `data-designer` into the Linux VM environment for no gain.

## When to revisit
If we scale clinical-note generation to all 60 cases (about 250 notes) and want parallelism and column dependencies, Data Designer is a reasonable fit; the endpoint question is already answered. Spike script (not kept in the repo): sampler + LLM column, `preview(num_records=3)`.

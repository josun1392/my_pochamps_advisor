# v12.63 Actual Smoke Response Capture Hardening

## Purpose

Harden the response transport used by future actual smokes after v12.62
completed provider calls without recoverable semantic-evaluator output.

## Production Return Path

```text
run_ui_selected_advice(battle_input)
-> _build_ui_selected_prompt(...) -> str
-> call_gemini(prompt, model) -> (response_text: str, usage: dict)
-> _log_advisor_call(...) -> summary: dict
-> (response_text, usage, summary)
-> LLMAdviceWorker.finished(response_text, usage/summary wrapper)
```

`call_gemini` extracts text before returning. `run_ui_selected_advice` returns
that text unchanged. The worker passes it unchanged as the first `finished`
signal argument. Token logging occurs only after `call_gemini` has returned
text and usage.

## v12.62 Failure Taxonomy

| Candidate | Classification | Evidence |
| --- | --- | --- |
| A. `call_gemini` returns text but runner discards it | LIKELY | v12.62 completed calls did not yield evaluator output; the normal return path is covered offline. |
| B. `run_ui_selected_advice` drops the return value | REJECTED | It returns `recommendation`, usage, and summary directly. |
| C. Worker/signal loses text | REJECTED | Sentinel contract verifies `finished` receives the exact recommendation. |
| D. Execution channel cannot return sanitized output | REJECTED | An offline one-shot capture emitted sanitized status/summary successfully. |
| E. Provider text extraction is incomplete | REJECTED for the tested path | Fake-provider sentinel reaches the evaluator unchanged; no actual response is reconstructed. |
| F. Logger success is independent of extraction | REJECTED | Logging follows successful `call_gemini` text extraction in the production flow. |
| G. v12.62 smoke command did not produce usable capture output | CONFIRMED | Three completed calls had no returned sanitized evaluator output. |

This does not infer that the provider returned an empty response and does not
recover or inspect past response text.

## Minimal Capture Seam

`run_ui_selected_advice_with_sanitized_smoke_capture(...)` calls the existing
production entry point, passes its response text only in process memory to a
caller-supplied evaluator, and returns:

```text
provider_success + semantic pass/fail/response_unavailable + sanitized summary
```

Provider exceptions propagate for a separate `PROVIDER_FAILURE` classification.
Evaluator failure yields `provider_success + response_unavailable`, not a
semantic failure. The seam accepts no unknown semantic status, normalizes the
summary to a short single line, and rejects a summary containing the entire
provider response.

## Offline Contracts

Fake provider tests establish:

- Sentinel response preservation from production entry point to evaluator.
- No raw sentinel in the returned capture object.
- Worker `finished` signal preserves recommendation text.
- Evaluator failure is distinct from provider failure.
- Full-response evaluator output is rejected rather than persisted.

No response text is written to docs, a separate file, or TokenLogger.

## Readiness

**READY FOR CAPTURED ACTUAL STABILITY SMOKE**

This is offline readiness only. Any future actual call requires separate
approval and must use the capture seam with a fixed fixture, one allowed call
budget, no retry/fallback/second provider/Vertex AI, and sanitized reporting.

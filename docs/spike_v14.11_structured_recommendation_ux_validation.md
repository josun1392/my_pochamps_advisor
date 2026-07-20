# v14.11 structured recommendation UX validation

Legacy and structured recommendation flows coexist visibly. The legacy action
is labelled `기존 선택 기술 조언` with a freeform selected-move description;
the separate `구조화 추천 받기` action describes comparison of all candidate
moves and validated structured recommendation. Both controls have tooltips and
accessible names.

The shared panel tracks the active owner (`legacy` or `structured`). Both advice
actions disable while a request is active, and handlers suppress a result or
failure that does not own the panel. Worker cleanup clears references and the
active owner. Legacy output is headed `[기존 조언]`; validated structured output
is headed `[구조화 추천]` and continues through the formatter only.

Resolved structured text pairs move and slot and contains all sections. Empty
sections explicitly say `없음`; failure states use sanitized Korean messages
without raw JSON, provider/HTTP details, secrets, traces, or internal codes.
The offline smoke contracts cover labels, action separation, mode heading,
ownership, button restoration, cleanup, and raw-data exclusion.

Validation: 10 v14.11 UX tests, 14 structured regressions, and 2625 passed
with 2 deselected in the full suite. Actual provider smoke remains unverified
because credentials were unavailable in v14.10. Legacy replacement remains
unauthorized.

Next: v14.12: credential-enabled single-call structured provider smoke and
post-smoke stabilization. Requires explicit T1 confirmation that credentials
are available before execution.

# v12.69 Structured Trusted-Context Acknowledgement Contract

## Status

`BLOCKED - CLI CONTRACT CONFLICT`

## Repeated failure analysis

The v12.66 and v12.68 smoke runs produced six provider-success, response-
available, semantic-fail results. Capture transport is not the current
limitation. The relevant boundary is that the CLI's fixture evaluator still
uses free-form string anchors, while the requested contract requires a
deterministic acknowledgement parser and exact-set comparison.

No raw Gemini response was recovered or inspected. The following conclusions
are based only on sanitized summaries, current prompt/evaluator code, and
offline contracts:

| Candidate | Classification |
| --- | --- |
| Category/source-class distinction absent from the evaluated response | CONFIRMED BY CONTRACT |
| Current condition expressed as observed event | POSSIBLE |
| Observed item event expressed as current state | POSSIBLE |
| Side identity retained but attribution omitted | LIKELY |
| A required context omitted | POSSIBLE |
| Resolved/exact outcome promotion | NOT SUPPORTED by sanitized evidence |

## Proposed minimal acknowledgement contract

The intended format remains deliberately small and leaves natural-language
advice intact:

```text
[Trusted Context]
- Current condition | self | burn
- Current condition | opponent | unknown
- Observed item event | opponent | focus-sash | item_activation_observed

[Advice]
...
```

The parser would normalize case and Focus Sash spacing, then exact-compare the
acknowledged entries against validated `condition_context.current_conditions`
and `item_event_context.observed_events`. Missing, extra, duplicate, malformed,
side-swapped, category-swapped, or identity-changed entries would fail. The
existing semantic evaluator would remain responsible for forbidden resolved,
exact, timing, RNG/order, unknown-inference, and missing-advice claims.

## Confirmed conflict

The active production CLI evaluator is
`scripts/run_sanitized_condition_smoke.py:evaluate_current_condition_item_event_response`.
It is directly supplied to
`run_ui_selected_advice_with_sanitized_smoke_capture(...)` by that same script.
It does not import or call a parser from `llm/advisor_client.py`.

Therefore, implementing the requested parser and prompt block only in
`llm/**` would not affect the actual CLI semantic status. Updating the CLI
evaluator or its adapter is necessary for the required production-path flow,
but `scripts/run_sanitized_condition_smoke.py` is explicitly prohibited from
change in this task. Adding passing parser-only tests would create an
unevaluated contract and would not establish re-smoke readiness.

## Safe next action

A follow-up must explicitly authorize the minimal CLI evaluator integration:

1. Add the deterministic parser and exact-set validator in a small reusable
   helper.
2. Change the CLI evaluator to call it before the existing forbidden-claim
   checks, without changing stdout JSON schema or exit codes.
3. Add subprocess contracts for canonical/minor-valid and all required invalid
   acknowledgement cases.
4. Run offline regression before seeking a separate actual smoke approval.

No actual provider call, prompt/payload change, parser implementation, test
change, raw-response recovery, or token-log reading occurred in v12.69.

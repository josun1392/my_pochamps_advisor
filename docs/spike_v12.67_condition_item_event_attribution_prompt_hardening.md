# v12.67 Condition and Item-Event Attribution Prompt Hardening

## v12.66 analysis

Only sanitized results, current contracts, and prompt fixtures were used. The
three v12.66 semantic failures confirm that the evaluator did not receive the
required attribution boundary. They do not reveal the response wording.

| Candidate | Classification | Basis |
| --- | --- | --- |
| A. Categories were mentioned without source-class distinction | CONFIRMED BY CONTRACT | The v12.66 evaluator returned attribution failure for every available response. |
| B. Current condition was expressed as an observed event | POSSIBLE | Explicitly rejected by the strengthened synthetic contract; raw text is unavailable. |
| C. Observed item event was expressed as current state | POSSIBLE | Explicitly rejected by the strengthened synthetic contract; raw text is unavailable. |
| D. Identity retained but trusted-source attribution omitted | LIKELY | Existing guards were separate and did not require a combined category readback. |
| E. One context was omitted | POSSIBLE | Existing evaluator permits this failure class; raw text is unavailable. |
| F. Exact or resolved outcome promotion | NOT SUPPORTED | v12.66 sanitized results did not report it, and no raw response was recovered. |

## Prompt inventory and correction

Before this change, `condition_context` and `item_event_context` were each
serialized and each had an independent guard. They required local side/type or
side/item/event-type acknowledgement, but did not present one dynamic response
instruction that contrasts the two source classes together.

`_build_condition_item_event_attribution_prompt_guard(...)` now adds a compact
`Trusted context attribution` block from validated payload entries only:

- `Current condition - <side>: <type> (user-confirmed current state).`
- `Observed item event - <side>: <item> / <event type> (explicitly user-confirmed observation).`

It requires category and identity acknowledgement while forbidding category
merging and resolved/exact/timing/RNG/order promotion. Values are payload-driven;
burn, unknown, and Focus Sash are not hardcoded into the prompt logic.

## Conditional behavior

- Both contexts: emits distinct current-condition and observed-event lines.
- Condition only: emits only current-condition attribution.
- Item event only: emits only observed-event attribution.
- Disabled, absent, empty, or all-invalid context: emits no attribution block.
- `none` remains confirmed current absence; `unknown` remains non-inferential.

## Offline contracts

The response fixture evaluator now distinguishes category omission, generic
source collapse, observed-event-as-state, condition-as-event, identity mixing,
unknown inference, resolved promotion, timing promotion, and partial
attribution. It still accepts compact natural wording rather than requiring
source enum literals. Production-path mocked fixtures verify the payload-driven
block, required readback wording, and CLI schema/exit-code regression.

## Readiness

**READY FOR ATTRIBUTION RE-SMOKE**

This is offline readiness only. No actual provider call, credential check, raw
response recovery, or prompt change during a smoke was performed.

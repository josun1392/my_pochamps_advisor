# v12.44 Item Event Actual Gemini Smoke Design

## Purpose

Define the execution contract for one future controlled Gemini smoke. The
single question is whether Gemini treats an explicit user-confirmed observed
item event as limited observation, without upgrading it into a resolved effect,
exact calculation, post-turn state, RNG result, or speed/order result.

This document does not authorize or execute a provider call.

## Representative Fixture

Use one deterministic UI-selected fixture with distinct known-item and observed
event contexts:

- Known current item: self `leftovers`, user-confirmed current context only.
- Observed event: opponent `focus-sash` with
  `event_type=item_activation_observed`.
- Required metadata: `status=user_confirmed`,
  `source=explicit_user_event_confirmation`, and `confidence=observed`.
- Optional fixed values: `turn=5` and note `User saw Focus Sash activation
  text.`

Focus Sash is intentionally selected because it is easy to overinterpret as
exact HP=1, consumption, or resolved damage. A PASS must state only that the
user confirmed observation of an activation event. It must not confirm the
post-hit HP, consumption, exact damage, or a fully resolved effect.

## Future Production Execution Path

The future smoke must use the existing UI-selected advice path, not a separate
prompt builder or custom provider wrapper:

```text
MainWindow._item_event_confirmations
-> MainWindow._build_llm_battle_input(
     include_item_event_confirmations=True
   )
-> battle_input["item_event_confirmations"]
-> run_ui_selected_advice(..., enable_battle_state_context=True)
-> build_item_event_context_from_confirmations(...)
-> item_event_context.observed_events
-> _build_ui_selected_prompt(...)
-> call_gemini(...)
-> _log_advisor_call(...) / TokenLogger metadata
```

The existing limited-context UI gate is the source of
`include_item_event_confirmations=True`. The raw UI confirmation list must not
reach provider payload serialization; only normalized observed events may do
so.

## Input Boundary

The future fixture may contain only:

- `side`
- `item`
- `event_type=item_activation_observed`
- `status=user_confirmed`
- `source=explicit_user_event_confirmation`
- `confidence=observed`
- optional `turn` and `note`

It must exclude resolved-effect, post-turn, exact HP/damage, modifier, RNG, and
speed/order fields, including `resolved_item_effect`, `resolved_effects`,
`post_turn_item_state`, `post_turn_hp_from_item`, `exact_hp`, `exact_damage`,
`item_damage_modifier_applied`, `item_speed_modifier_applied`, `rng_roll`,
`speed_order_override`, `quick_claw_activated_by_rng`,
`focus_sash_post_hit_hp_1`, and `berry_recovered_exact_hp`.

## Single-Call Policy

- Maximum actual Gemini calls: one.
- Retry, automatic retry, fallback, second provider, Vertex AI, and diagnostic
  follow-up calls are prohibited.
- A provider failure ends the smoke immediately. Record only a sanitized failure
  result; do not retry or alter the repository.

## PASS Criteria

### Automatically Checkable

- Pre-call prompt/payload has the limited-context gate enabled and contains the
  normalized observed event with its source, status, and confidence.
- The raw confirmation list and forbidden fields are absent from provider input.
- Exactly one call is attempted, with retry count zero and no alternate provider.
- The response does not contain predefined positive resolved/exact/post-turn,
  RNG, order, hidden-item, or input-absent mechanic claim anchors.

### Manual Semantic Review

- Treats the Focus Sash event as user-confirmed observation, not resolved fact.
- Separates self known Leftovers current context from opponent observed Focus
  Sash activation.
- Does not assert exact HP, exact damage, actual recovery/prevention amount,
  consumption, post-turn state, RNG result, or final speed order.
- Does not infer hidden items, EVs, IVs, nature, or item modifiers.
- Uses uncertainty appropriate to the limited input.

PASS requires both automatic checks and manual review to pass.

## FAIL Criteria

Classify the smoke as FAIL if the response does any of the following:

- upgrades the observed event into a resolved result
- claims exact recovery, damage, prevented damage, or HP
- asserts Focus Sash left the target at exactly 1 HP without that observation
- asserts a Quick Claw RNG cause or final action order
- creates post-turn HP or item state
- infers activation/consumption from a known item alone
- infers a hidden opponent item or other input-absent exact mechanic result

Provider failure is not semantic PASS or FAIL. Record it as a sanitized
execution failure and do not retry.

## Security and Logging Policy

Never print API keys, `.env`, ADC credentials, service-account JSON,
authorization headers, raw credential/error payloads, the full environment, or
raw `logs/token_usage.jsonl` content.

The final report may include model identifier, success/failure, sanitized HTTP
status or error category, token counts, estimated cost, retry/call counts, and
a safety-verdict summary. Verify only that TokenLogger recorded metadata; do
not print the log file.

## Failure Handling

| Failure | Future smoke handling |
| --- | --- |
| Missing API key | Record sanitized configuration failure; no retry. |
| Invalid API key | Record sanitized authentication failure; no retry. |
| Quota or rate limit | Record sanitized quota/rate-limit failure; no retry. |
| Timeout or network error | Record sanitized transport failure; no retry. |
| Provider validation error | Record sanitized validation failure; no retry. |
| Unexpected response schema | Record sanitized schema failure; no retry. |

Every failure uses the same boundaries: no fallback, second provider, credential
output, repository modification, or extra diagnostic call.

## Future Approval Procedure

Actual execution is permitted only in a separate future task after all of the
following are explicitly approved:

1. T1 approves one actual Item Event smoke.
2. T2 approves the exact single command and fixture.
3. Working-tree status confirms protected-file handling.
4. Provider and model identifier are confirmed.
5. Maximum call count is one and cost cap is agreed.
6. Retry and fallback are disabled.

v12.44 is design-only and is not execution approval. A future v12.45
Controlled Item Event Gemini Smoke may execute only after this procedure.

## No Actual Gemini Call

- No actual Gemini/provider/network call was executed.
- No retry, second provider call, or Vertex AI call was executed.

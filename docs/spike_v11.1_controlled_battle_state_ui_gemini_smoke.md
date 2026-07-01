# v11.1 Controlled Battle State UI Gemini Smoke

## Purpose

Execute the v11.0 controlled smoke once after T1 approval and verify that the
UI-selected `battle_state_context` path keeps the model inside the existing
unknown-field, hidden-inference, and non-resolved-simulation boundaries.

## Prerequisite Checks Result

- Branch: `master`.
- Remote tracking: `origin/master`.
- Latest pushed baseline before this work: `e6a1228 docs(spike): design controlled battle state UI Gemini smoke`.
- Unpushed commits before the smoke: none.
- Working tree before the smoke: clean except the pre-existing unstaged `config/env.example`.
- Full pytest before the call: `1274 passed, 2 deselected`.
- API key availability: present, value not printed.
- Model: `gemini-2.5-flash`.
- Provider path: Gemini Developer API path from `scripts.spike_advisor.call_gemini(...)`; Vertex AI was not used.

## Exact Call Count

- Actual Gemini calls: `1`.
- Retry count: `0`.
- Second call for clarification: `NO`.
- Second call for a better answer: `NO`.
- Automatic rerun: `NO`.

The call result was not retried even though the local reporting script ended
with a post-call formatting error while reading the sanitized logging summary as
an object instead of a dict. The provider call itself had already completed and
the boundary checks had already passed.

## Fixture Summary

The smoke used the existing repo UI-selected opponent-move fixture style:

- limited context checkbox: ON.
- self active: `charizard`, HP percent `100`.
- opponent active: `garchomp`, HP percent `100`.
- existing limited contexts enabled together:
  - `turn_pipeline`
  - `turn_order_context`
  - `opponent_move_context`
  - `battle_state_context`

This differs from the v11.0 recommended Garchomp-vs-Charizard example only in
side assignment. The smoke kept the repo fixture consistent and still verified
the required species/HP visible-state boundary.

## Payload Boundary Result

Result: `PASS`.

- `battle_state_context` was included.
- `turn_pipeline` was included.
- `turn_order_context` was included.
- `opponent_move_context` was included.
- self species: `visible_ui` `charizard`.
- self HP percent: `visible_ui` `100`.
- opponent species: `visible_ui` `garchomp`.
- opponent HP percent: `visible_ui` `100`.
- self/opponent status, boosts, and item remained unknown.
- field weather, terrain, screens, hazards, and room remained unknown.
- `known_conditions` remained `[]`.
- No hidden item, EV/IV/nature, inferred status/boost/field, post-turn HP,
  item consumption, RNG, speed tie, Quick Claw activation, or full outcome
  fields were present in `battle_state_context`.

## Prompt Boundary Result

Result: `PASS`.

The prompt included:

- serialized `battle_state_context`.
- battle-state prompt guard.
- unknown-fields-must-remain-unknown anchor.
- hidden item inference forbidden anchor.
- EV/IV/nature inference forbidden anchor.
- boosts/status/weather/terrain/hazards/screens/room inference forbidden unless explicit anchor.
- damage/KO reverse inference forbidden anchor.
- non-resolved-turn-simulation anchor.
- post-turn HP, item consumption, RNG result, speed tie result, Quick Claw
  activation, and full turn outcome claim forbidden anchor.

## Response Boundary Result

Result: `PASS`.

The local smoke scanner found no forbidden hidden-state or resolved-outcome
phrases in the response. The response boundary check completed before the
post-call reporting-format error.

Observed response metadata:

- response character count: `721`.
- forbidden phrase categories matched: `none`.

The response text was not pasted into this document to avoid expanding the
smoke record beyond the necessary boundary result.

## Token and Cost Summary

Sanitized summary from the token log:

- model: `gemini-2.5-flash`.
- input tokens: `11054`.
- output tokens: `171`.
- cached tokens: `0`.
- pricing status: `free_tier_zero_cost`.
- estimated cost USD: `0.0`.

Raw token log lines were not pasted. `logs/token_usage.jsonl` was not committed
or reset.

## Pass/Fail Result

Result: `PASS`.

PASS basis:

- exactly one actual Gemini call.
- zero retries.
- payload boundary passed.
- prompt guard boundary passed.
- response scanner found no hidden-state certainty or resolved simulation claims.
- token/cost reporting was kept sanitized.

## Security Statement

- API key value was not printed.
- Credential values were not printed.
- Billing details were not printed.
- Raw token log lines were not printed.
- `.env` was not printed.
- `logs/token_usage.jsonl` was not committed or reset.

## Next Recommendation

Recommended next: `v11.2 Battle State Context Actual Smoke Closure`.

The closure should record the actual smoke PASS, preserve the one-call/no-retry
audit trail, and decide whether the next safe expansion is user-confirmed item
boundary design or field-state source design.

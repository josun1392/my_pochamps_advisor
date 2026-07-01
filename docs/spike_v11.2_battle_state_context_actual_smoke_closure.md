# v11.2 Battle State Context Actual Smoke Closure

## Purpose

Close the Battle State Context actual smoke phase after the v11.1 controlled
Gemini smoke completed with one approved provider call and no retry.

This closure records the verified boundary, known limitations, and next safe
expansion options. It does not change production code, UI behavior, payload
adapters, prompt guards, source adapters, or runtime provider behavior.

## v11.1 Smoke Summary

v11.1 executed the controlled UI-selected `battle_state_context` Gemini smoke
after T1 approval.

- Result: `PASS`.
- Model: `gemini-2.5-flash`.
- Provider path: Gemini Developer API.
- Vertex AI: not used.
- Network calls outside the approved Gemini provider call: none.

## Exact Call Count

- actual Gemini call count: `1`.
- retry count: `0`.
- second call: `NO`.
- second call for clarification: `NO`.
- second call for a better answer: `NO`.
- automatic rerun: `NO`.

The one-call boundary was preserved. The post-call local reporting issue did
not trigger a retry or second provider call.

## Fixture Summary

- self: `charizard`, HP `100`.
- opponent: `garchomp`, HP `100`.
- limited context checkbox: ON.
- `battle_state_context` source: species/HP `visible_ui` only.
- existing limited contexts enabled together:
  - `turn_pipeline`
  - `turn_order_context`
  - `opponent_move_context`
  - `battle_state_context`

The smoke used the repo's existing UI-selected fixture style. This differs from
the v11.0 suggested example only in side assignment.

## Payload Boundary Result

Result: `PASS`.

- `battle_state_context` included.
- `turn_pipeline` included.
- `turn_order_context` included.
- `opponent_move_context` included.
- self/opponent species and HP percent carried `visible_ui` source.
- status, boosts, and item remained unknown.
- field weather, terrain, screens, hazards, and room remained unknown.
- `known_conditions` remained `[]`.
- no hidden item.
- no EV/IV/nature.
- no inferred field/status/boosts.
- no post-turn HP.
- no item consumption.
- no RNG, speed tie, or Quick Claw resolution.
- no full turn outcome.

## Prompt Boundary Result

Result: `PASS`.

- serialized `battle_state_context` appeared.
- `battle_state_context` guard appeared.
- unknown fields must remain unknown.
- hidden item inference was forbidden.
- EV/IV/nature inference was forbidden.
- boosts/status/weather/terrain/hazards/screens/room inference was forbidden unless explicit.
- damage/KO reverse inference was forbidden.
- resolved turn simulation was forbidden.
- post-turn HP, item consumption, RNG, speed tie, Quick Claw, and full outcome
  claims were forbidden.

## Response Boundary Result

Result: `PASS`.

- forbidden hidden/resolved phrase scan match: `none`.
- no hidden state certainty was detected.
- no resolved simulation claim was detected.
- no Quick Claw activation certainty was detected.
- no selected opponent move certainty was detected.
- no post-turn HP certainty was detected.

This is a controlled fixture result, not a guarantee that every future model
response will always obey the guard.

## Sanitized Token and Cost Summary

- input tokens: `11054`.
- output tokens: `171`.
- cached tokens: `0`.
- pricing: `free_tier_zero_cost`.
- estimated cost: `$0.0`.

Raw token log lines were not printed. API keys, credentials, and billing details
were not printed.

## Post-Call Reporting Script Issue

Provider call itself succeeded. A local post-call reporting script hit a
dict/object access issue after the call. No retry or second provider call was
executed.

The issue affected only local sanitized reporting output after the successful
provider response and boundary scan. It did not affect payload construction,
prompt construction, provider routing, or the one-call audit result.

## Security and Logging Policy Confirmation

- `.env` was not printed.
- API key values were not printed.
- access tokens were not printed.
- ADC credentials were not printed.
- service account JSON was not printed.
- billing details were not printed.
- raw token log lines were not printed.
- `logs/token_usage.jsonl` remains modified from the actual call logging and
  must stay uncommitted and unreset.
- `config/env.example` remains an unrelated unstaged local change and must stay
  uncommitted and unreset.

## Known Limitations

- Smoke is one controlled fixture only.
- It does not prove broad advice quality.
- It does not validate every Pokemon/move matchup.
- It does not add item, field, status, or boost sources.
- It does not implement full Turn Engine behavior.
- It does not prove future model responses will always obey the guard.

## Final Status

Battle State Context actual smoke phase is closed as PASS.

The current supported `battle_state_context` UI path remains:

- existing limited-context checkbox default off.
- checkbox off omits `battle_state_context`.
- checkbox on includes `battle_state_context` with other limited contexts.
- self/opponent species and HP percent only.
- status, boosts, item, field state, and `known_conditions` remain unknown or `[]`.

## Next Recommendations

Recommended next: `v11.3 User-confirmed Item Boundary Design`.

Reason:

- `battle_state_context` currently carries only species/HP snapshot data.
- Item is the next high-value battle-state extension.
- Item handling has a sensitive hidden-vs-confirmed boundary, so a design step
  should come before implementation.

Alternatives:

- `v11.3 Field State Source Design`: design safe UI sources for weather,
  terrain, screens, hazards, and room.
- `v11.3 Battle State Context Hardening Backlog`: record guard/test/backlog
  improvements from the actual smoke result.

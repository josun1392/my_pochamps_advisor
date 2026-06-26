# v8.8 Opponent Move Context Closure

## Purpose

v8.8 closes the Opponent Move Context phase after the controlled one-call Gemini smoke passed in v8.7.

This closure records the current supported behavior, unsupported boundaries, smoke result, and next recommended phase. It does not implement production code, change UI behavior, run another provider call, or expand opponent move context into hidden moveset inference.

## Phase Completion Summary

- v8.0 designed battle-state and opponent-move context expansion as a safer path before full Turn Engine work.
- v8.1 locked the fixture-level `opponent_move_context` payload contract.
- v8.2 added `build_opponent_move_context(...)` as a source-bound helper.
- v8.3 added the optional/default-off top-level payload adapter.
- v8.4 added prompt guard wording for `opponent_move_context`.
- v8.5 verified payload and prompt behavior through a mocked offline advice fixture.
- v8.6 designed a controlled one-call Gemini smoke with no retry.
- v8.7 executed the controlled smoke and classified it PASS.

Summary:

```text
opponent_move_context contract -> helper -> payload adapter -> prompt guard -> offline fixture -> controlled Gemini smoke PASS
```

## Current Supported Behavior

- `opponent_move_context` is optional and default-off.
- Callers must pass `enable_opponent_move_context=True` and a valid non-empty context before it appears in the advice payload.
- Empty helper output is omitted from the top-level payload.
- Known opponent moves are accepted only from trusted explicit sources:
  - `user_confirmed`
  - `visible_ui`
  - `explicit_input`
- Known moves are represented as known move data, not selected move data.
- Candidate moves can come from safe candidate sources, but stay `confirmed=False` and `selected=False`.
- Positive-priority candidates can appear in `priority_move_candidates`, still unconfirmed and unselected.
- `selected_opponent_move` stays `unknown` unless an explicit trusted selected move is supplied.
- Prompt guard wording is emitted only when top-level `opponent_move_context` is present.
- The guard tells Gemini not to infer hidden movesets, opponent sets, selected moves, EV/IV/nature, hidden item, weather, terrain, boosts, RNG, item consumption, post-turn HP, or full turn resolution from this context.

## Current Unsupported Behavior

This phase does not implement:

- UI/source extraction
- automatic UI-selected opponent move context generation
- a new UI checkbox or saved setting
- hidden moveset inference
- opponent set inference
- species/common-set/meta-based move generation
- selected opponent move inference
- EV/IV/nature inference
- hidden item inference
- weather/terrain/boost inference
- speed tie resolution
- RNG resolution
- Quick Claw activation resolution
- item consumption
- post-turn HP update
- full Turn Engine behavior

`opponent_move_context` is a limited source-bound context surface. It is not an opponent set predictor and not a selected-move predictor.

## Smoke Result Summary

v8.7 controlled Gemini smoke:

- actual Gemini call count: 1
- retry count: 0
- Vertex AI call count: 0
- stop condition: none
- model: `gemini-2.5-flash`
- result classification: PASS

Response safety:

- Gemini treated `opponent_move_context` as explicitly known / visible context.
- Known Thunderbolt remained known move data, not selected move data.
- Candidate Quick Attack was not treated as confirmed.
- Candidate Quick Attack was not treated as selected.
- `selected_opponent_move` stayed unknown.
- No hidden moveset, opponent set, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, post-turn HP, or full turn resolution claim appeared.

## Known Limitations

- No runtime UI/source extraction currently builds `opponent_move_context`.
- The helper only normalizes caller-provided facts and candidates.
- Candidate move quality depends on the caller's source data.
- Move metadata is intentionally narrow.
- Unknown selected opponent moves remain unknown unless user/visible input explicitly supplies one.
- This context can improve LLM wording only when a caller supplies it; the default UI path does not automatically include it yet.

## Next Big Phase Candidates

### Option A: v9.0 Opponent Move UI/Source Integration Design

Goal:

```text
Design how the UI-selected advice path should safely supply known and candidate opponent moves into opponent_move_context.
```

Why this is recommended:

- The contract, helper, adapter, prompt guard, offline fixture, and provider smoke are complete.
- Advice quality now depends on safely sourcing real UI/cache move data.
- A design step can define source precedence, checkbox/flag behavior, no-call tests, and rollback boundaries before implementation.

### Option B: v9.0 Battle State Context Payload Contract

Goal:

```text
Add a separate optional battle_state_context for visible field/state facts without full turn simulation.
```

This is useful, but opponent move source integration is the more direct continuation of the completed v8 work.

### Option C: v9.0 Prompt Wording Polish

Goal:

```text
Tighten existing opponent_move_context wording without adding new context.
```

This should only be used if future verification finds ambiguous wording. The v8.7 smoke did not reveal a prompt failure.

## Recommendation

Recommended next:

```text
v9.0 Opponent Move UI/Source Integration Design
```

Do not implement automatic source extraction directly before the design step. The next step should define trusted UI/cache sources, default-off behavior, no-provider-call tests, and explicit unsupported boundaries.

## Safety Statement

- No production code was changed in v8.8.
- No actual Gemini call was made in v8.8.
- No retry was made in v8.8.
- No Vertex AI call was made in v8.8.
- No UI/source extraction was implemented.
- No UI checkbox behavior was changed.
- No saved setting auto-enable was added.
- No full Turn Engine was implemented.
- No hidden moveset, opponent set, selected opponent move, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, or post-turn HP inference was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl`, `.env`, secrets, API keys, and token log contents were not committed or recorded.

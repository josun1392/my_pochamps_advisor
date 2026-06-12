# v4.2 Turn Snapshot Payload Adapter Design

## Purpose

v4.1 added `core.turn_state` with `PokemonBattleSlot`, `BattleState`, `TurnInput`, `TurnSnapshot`, `to_dict()`, `from_dict(...)`, validation, and `normalize_turn_snapshot(...)`. That contract is intentionally inert: it is not connected to `advisor_client.py`, LLM payload generation, damage estimates, item contexts, or `ko_context`.

v4.2 designs the adapter that can eventually attach a normalized `TurnSnapshot` to the LLM advice payload without turning it into a full Turn Engine result.

This is design-only. No code implementation, Gemini call, Vertex AI call, Turn Engine simulation, item trigger evaluation, item consumption, HP update logic, speed/order simulation, damage formula change, raw damage roll change, Q12 change, `ko_context` change, or payload filtering change was made.

## Current Payload Shape

The current default advice payload is built from the UI-selected `battle_input` dictionary, filtered through `build_ui_advice_payload(...)`, and embedded in the prompt as JSON.

Current top-level sections include:

- `scenario`
- `pokemon`
- `stat_profiles`
- `item_profiles`
- `opponent_assumptions`
- `speed_context`
- `moves`
- `opponent_moves`

`scenario.known_limitations` is the right place for global limitations. Move-local damage estimates and item contexts remain under the existing move objects. `ko_context` remains limited damage-roll context attached near damage estimate data.

## Payload Location Options

| Candidate | Pros | Cons | Recommendation |
|---|---|---|---|
| `battle_input.turn_snapshot` | Matches the Python variable name used by builders; easy to reason about before filtering | `battle_input` is not a serialized top-level payload key, so documenting it as a payload location could confuse prompt readers | Use only as implementation phrasing, not serialized contract wording |
| top-level `turn_snapshot` | Minimal collision with existing sections; clear optional additive section; can be omitted without touching existing payload shape | Adds another top-level section that prompt/contract docs must guard carefully | Recommended |
| `advice_context.turn_snapshot` | Could group future advisor-only context | `advice_context` does not exist today; would introduce a broad wrapper before there is a need | Not recommended for v4.3 |
| nested under `scenario` | Keeps metadata near limitations | `scenario` currently describes mode/limitations, not mutable battle state; large nested state would blur contract intent | Not recommended |

Recommended serialized location:

```text
turn_snapshot
```

The adapter may accept a Python input parameter named `turn_snapshot`, but the emitted payload should add a top-level `turn_snapshot` section only when one is explicitly provided.

Do not name this section:

- `turn_engine_result`
- `battle_simulation`
- `engine_result`
- `final_turn_state`

Those names imply full simulation or final battle truth, which v4.3 will not provide.

## Optional Migration Path

v4.3 should preserve the current behavior by default:

1. If no `TurnSnapshot` is provided, `build_ui_advice_payload(...)` output remains unchanged.
2. If a `TurnSnapshot` is provided, the adapter normalizes it with `normalize_turn_snapshot(...)`.
3. The normalized `turn_snapshot.to_dict()` is added as top-level `turn_snapshot`.
4. Existing `damage_estimate`, `ko_context`, item contexts, item profile filtering, and prompt guard generation remain unchanged.
5. `scenario.known_limitations` gains turn-snapshot limitations only when `turn_snapshot` is present.

This keeps v4.3 additive and reversible. The first adapter should not derive trigger results from the snapshot. It should only serialize known state fields.

## Limitation Wording

When `turn_snapshot` is present, the prompt should make these limitations explicit:

- `turn_snapshot` is a pre-turn or selected-state snapshot, not full turn simulation.
- item trigger evaluation is not performed yet.
- item consumption is not simulated yet.
- post-damage HP updates are not finalized.
- speed/order simulation is not finalized.
- status, volatile, and stat-stage resolution are known-state fields only unless explicitly confirmed.

Forbidden user-facing implications:

- full turn simulation completed
- exact item trigger result
- item was consumed
- exact post-turn HP
- guaranteed move order
- exact status resolution

Allowed user-facing phrasing:

- current pre-turn snapshot indicates...
- known state fields suggest...
- item consumption is not simulated yet
- post-damage state updates are not finalized
- turn order is not finalized by this snapshot alone

The wording should be global and short. Do not duplicate long Turn Engine caveats into every item context.

## Serialization Policy

v4.3 should rely on the v4.1 contract:

- Accept `TurnSnapshot`, mapping, or `None`.
- Normalize through `normalize_turn_snapshot(...)`.
- Serialize through `to_dict()`.
- Preserve `None` for unknown scalar values.
- Preserve `unknown` item status as explicit unknown state.
- Serialize tuples as lists for JSON payload compatibility.
- Serialize `stat_stages` as a plain dict.
- Preserve `volatile_conditions` order from the source snapshot for stable output.
- Treat invalid side, item status, HP percent, stat stage, or turn number as validation errors in the adapter path.

Recommended error policy:

- Low-level normalization should fail fast with `ValueError`.
- `advisor_client` integration should not silently coerce invalid state into plausible battle truth.
- If a future UI caller needs soft failure, add an explicit `strict=False` adapter option later and document safe omission. Do not make silent omission the default.

## v4.3 Implementation MVP

Recommended milestone:

```text
v4.3 Turn Snapshot Payload Adapter
```

Scope:

- Add a small adapter helper near the LLM payload boundary, likely in `llm/advisor_client.py` or a tiny adjacent module.
- Accept optional `turn_snapshot` input.
- If absent, return the same advice payload as today.
- If present, add top-level `turn_snapshot`.
- Add turn snapshot limitations only when present.
- Do not connect to damage estimate, `ko_context`, item contexts, trigger results, HP updates, item consumption, or speed simulation.

Candidate helper shape:

```text
attach_turn_snapshot_to_advice_payload(payload, turn_snapshot)
```

or:

```text
build_ui_advice_payload(battle_input, turn_snapshot=None)
```

Prefer the smallest signature change that does not ripple through UI code. A helper called by tests first may be safer than changing UI entrypoints immediately.

## v4.3 Tests

Required tests:

1. `TurnSnapshot` absent means default advice payload output is unchanged.
2. `TurnSnapshot` present means top-level `turn_snapshot` is present and normalized.
3. Invalid `TurnSnapshot` data raises validation error in strict adapter path.
4. known HP, item_status, stat_stages, major_status, and volatile_conditions serialize as expected.
5. turn snapshot limitations are included only when `turn_snapshot` is present.
6. prompt does not claim full Turn Engine simulation, exact trigger result, item consumption, exact post-turn HP, guaranteed move order, or exact status resolution.
7. existing `damage_estimate`, `ko_context`, item contexts, and item-context mention guards are unchanged.
8. unavailable/deferred/blocked item context filtering remains unchanged.

## Future Connection Plan

After v4.3, connect the snapshot gradually:

1. UI selected active slot state
   - Map known active Pokemon, slot index, HP percent, and selected move into `TurnSnapshot`.
2. known item profile
   - Map user-confirmed, none, unknown, inferred, or consumed item status without changing item context filtering.
3. stat stages and conditions
   - Add UI fields only after the contract and prompt wording are stable.
4. speed/order context
   - Let `speed_context` and `speed_order_context` read known state later, but keep final order unsimulated until a Turn Engine milestone.
5. recovery and trigger planning
   - Use `current_hp_percent`, item status, and post-damage estimates to design Shell Bell and healing berry trigger results.
6. item trigger results
   - Add a separate trigger result contract before implementing consumption or post-damage HP updates.

## Non-Goals

- No full Turn Engine in v4.3.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.
- No damage estimate behavior change.
- No raw damage roll, Q12, `ko_context`, or payload filtering change.
- No actual Gemini verification as part of this design.

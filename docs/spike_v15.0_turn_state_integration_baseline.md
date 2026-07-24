# v15.0 Turn-State Integration Baseline

## Purpose and current flow

`MainWindow._build_llm_battle_input` captures selected panels, moves, and
confirmed context into a fresh dictionary. `StructuredRecommendationWorker`
deep-copies that dictionary and its selected moves before its thread starts.
`run_structured_ui_recommendation` calls `prepare_ui_recommendation_cycle`,
which builds deterministic candidates and then the provider-neutral payload.

`core.turn_state` already supplies frozen `PokemonBattleSlot`, `BattleState`,
`TurnInput`, and `TurnSnapshot` models. v15.0 connects that model to structured
preparation through `build_request_start_recommendation_snapshot`.

## UI-to-state inventory

| State | UI/runtime source | Trust | Snapshot/payload | Use |
| --- | --- | --- | --- | --- |
| active Pokémon and slot | selected panel / `pokemon` | user-selected | `BattleState.active_*` | structured + deterministic snapshot |
| selectable self moves | selected panel / `moves.my_available_moves` | user-confirmed | candidate exact set | structured candidate validation |
| HP | selected panel/current-HP confirmation | user-confirmed or unknown | slot HP | snapshot; deterministic contexts remain separate |
| item, condition, ability, stages | confirmation sessions | user-confirmed or unknown | existing normalized contexts | deterministic when enabled |
| weather, terrain, field effects | field confirmation | user-confirmed or unknown | existing field context | deterministic when enabled |
| observed/item events | session confirmations | observed/user-confirmed | existing event contexts | deterministic where supported |
| EV/IV/nature, unobserved moves, Tera | absent | unknown/forbidden inference | absent or unknown | not inferred |

## Baseline contract

At request start, preparation builds a frozen `TurnSnapshot` and serializes its
dictionary into `battle_snapshot_summary.turn_snapshot`. The worker receives
only deep-copied input; neither widgets nor request tokens are passed. If the UI
supplies `my_available_moves`, each non-empty candidate must match the same
slot and move ID or preparation returns sanitized `invalid_snapshot` before
candidate evaluation or provider construction. Missing active Pokémon is
blocked the same way.

The snapshot model is round-trip serializable. It preserves absent HP and item
information as `None`/`unknown`; it does not derive ability, item, weather,
terrain, stat, or event facts.

## Alignment and gaps

Structured preparation and deterministic candidates now share captured active
Pokémon identity and selectable move ownership. Existing deterministic damage
contexts still have richer, separately normalized inputs (HP, stages, field,
events); full one-model unification is deferred. This milestone adds no turn
transition, provider adapter change, persistence, inferred opponent state, or
damage-formula change.

## Verification

Pure tests cover mutation-after-capture, serialization, move ownership,
missing-state blocking before evaluation, unknown preservation, exact candidate
slot alignment, and token exclusion. Provider/network budget: 0.

# Advisor Payload Contract

**Milestone:** v0.10 — Four-Move Damage Comparison
**Payload mode:** `ui-selected-pokemon-v0.10`
**Status:** Current contract for the PySide6 UI to Gemini LLM advisor path.

## Purpose

The advisor payload is the boundary between deterministic UI / engine state and the Gemini natural-language recommendation layer. This contract prevents the LLM from treating incomplete UI metadata as confirmed battle math.

The current app can send selected Pokemon identity, HP percent, user-confirmed move metadata, and default-assumption damage estimates for user-confirmed moves. It does not yet send final battle stats, KO odds, turn order, or Turn Engine state.

## Current Payload Shape

Top-level sections:

- `scenario`
- `pokemon`
- `moves`

`scenario` contains:

- `mode`: currently `ui-selected-pokemon-v0.10`
- `format_note`: explains that this is selected Pokemon identity plus default-assumption user-confirmed move estimates, not full battle state
- `known_limitations`: guardrails the prompt and UI must preserve

`pokemon.my_active` and `pokemon.opponent_active` contain:

- `slot_index`
- `name_en`
- `name_ko`
- `types`
- `types_ko`
- `base_stats`
- `abilities`
- `abilities_ko`
- `hp_percent`
- `selected_move_index`

`moves` contains:

- `my_selected_move_index`
- `my_available_moves`
- `my_selected_move`
- `opponent_available_moves`
- `opponent_selected_move`
- `opponent_selected_move_index`
- `move_data_status`
- `notes`

User-confirmed move entries contain:

- `slot`
- `move_id`
- `name_en`
- `name_ko`
- `type`
- `category`
- `power`
- `accuracy`
- `pp`
- `damage_estimate` on each user-confirmed entry in `moves.my_available_moves`
- `damage_estimate` on `moves.my_selected_move`

Each move `damage_estimate` contains:

- `status`
- `scope`
- `is_final_battle_damage`
- `selected_move_id` when available
- `damage_range` when available
- `percent_range` when available
- `rolls` when available
- `assumptions`
- `derived_stats` when available
- `limitations`

## Explicitly Missing

The v0.10 payload does not contain:

- final calculated stats
- EV/IV/nature
- held item
- selected ability certainty
- weather
- terrain
- stat boosts
- exact current HP integer
- opponent moves
- OHKO/2HKO/KO chance
- turn order
- speed tie
- status duration
- Turn Engine state

## LLM Guardrails

The LLM must not:

- assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, move sets, or Tera types
- treat `base_stats` as final battle stats
- describe `damage_estimate` as final battle damage
- infer OHKO/2HKO, KO chance, survival, or speed order unless explicit calculated fields are present
- treat cache learnsets or unselected moves as available moves
- consider Terastallization, which is banned in PoChamps

The LLM may:

- explain broad type or role risks at a non-damage-exact level
- discuss user-confirmed move metadata such as type, category, power, accuracy, and PP
- discuss `damage_estimate` only under its stated default assumptions
- recommend a direction while naming the missing information that prevents a confident damage-based call
- ask for or point out missing final stats, items, field state, opponent moves, or damage estimates

## Damage Estimate Defaults

Move damage estimates use:

- level 50
- IV 31 all
- EV 0 all
- neutral nature
- no item
- no boosts
- no weather
- no terrain
- no screens
- no critical hit
- singles / non-spread assumption
- no ability effects unless explicitly selected and connected

`percent_range` uses default defender max HP as the denominator. It is not exact current HP.

Unavailable statuses include:

- `unavailable_no_selected_move`
- `unavailable_status_move`
- `unavailable_missing_power`
- `unavailable_missing_pokemon`
- `unavailable_missing_base_stats`
- `unavailable_missing_type`
- `unavailable_unsupported_category`
- `unavailable_engine_error`

## Future Field Locations

v0.10 extends the same `damage_estimate` shape to each user-confirmed move in `moves.my_available_moves`, enabling four-move comparison without changing the meaning of existing selected-move fields.

Opponent move data should later enter `moves.opponent_available_moves` and `moves.opponent_selected_move`.

Turn Engine state should later enter a separate top-level `battle_state` section instead of being mixed into Pokemon identity metadata.

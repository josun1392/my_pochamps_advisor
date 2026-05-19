# Advisor Payload Contract

**Milestone:** v0.8.3 — Advisor Payload Contract  
**Payload mode:** `ui-selected-pokemon-v0.8`  
**Status:** Current contract for the PySide6 UI to Gemini LLM advisor path.

## Purpose

The advisor payload is the boundary between deterministic UI / engine state and the Gemini natural-language recommendation layer. This contract prevents the LLM from treating incomplete UI metadata as confirmed battle math.

The current app can send selected Pokemon identity, HP percent, and user-confirmed move metadata. It does not yet send final battle stats, damage rolls, KO odds, turn order, or Turn Engine state.

## Current Payload Shape

Top-level sections:

- `scenario`
- `pokemon`
- `moves`

`scenario` contains:

- `mode`: currently `ui-selected-pokemon-v0.8`
- `format_note`: explains that this is selected Pokemon identity only, not full battle state
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

## Explicitly Missing

The v0.8 payload does not contain:

- final calculated stats
- EV/IV/nature
- held item
- selected ability certainty
- weather
- terrain
- stat boosts
- exact current HP integer
- opponent moves
- damage rolls
- OHKO/2HKO/KO chance
- turn order
- speed tie
- status duration
- Turn Engine state

## LLM Guardrails

The LLM must not:

- assume unprovided EVs, IVs, nature, held items, boosts, weather, terrain, exact HP, move sets, or Tera types
- treat `base_stats` as final battle stats
- infer exact damage, OHKO/2HKO, KO chance, survival, or speed order unless explicit calculated fields are present
- treat cache learnsets or unselected moves as available moves
- consider Terastallization, which is banned in PoChamps

The LLM may:

- explain broad type or role risks at a non-damage-exact level
- discuss selected move metadata such as type, category, power, accuracy, and PP
- recommend a direction while naming the missing information that prevents a confident damage-based call
- ask for or point out missing final stats, items, field state, opponent moves, or damage estimates

## Future Field Locations

v0.9 should add selected-move damage estimates under `moves.my_selected_move.damage_estimate` or a sibling `damage` section keyed by selected move. The estimate must include assumptions before the LLM may make damage-based claims.

v0.10 should extend the same shape to each user-confirmed move in `moves.my_available_moves`, enabling four-move comparison without changing the meaning of existing fields.

Opponent move data should later enter `moves.opponent_available_moves` and `moves.opponent_selected_move`.

Turn Engine state should later enter a separate top-level `battle_state` section instead of being mixed into Pokemon identity metadata.

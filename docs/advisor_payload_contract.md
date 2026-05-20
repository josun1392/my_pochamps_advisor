# Advisor Payload Contract

**Milestone:** v0.12 - Opponent Known Move Damage Estimate
**Payload mode:** `ui-selected-pokemon-v0.12`
**Status:** Current contract for the PySide6 UI to Gemini LLM advisor path.

## Purpose

The advisor payload is the boundary between deterministic UI / engine state and the Gemini natural-language recommendation layer. This contract prevents the LLM from treating incomplete UI metadata as confirmed battle math.

The current app can send selected Pokemon identity, HP percent, user-confirmed move metadata, default-assumption damage estimates for the user's confirmed moves, explicitly labeled opponent move information, and default-assumption damage estimates for user-confirmed opponent known moves. It does not yet send final battle stats, KO odds, turn order, candidate move damage estimates, or Turn Engine state.

## Current Payload Shape

Top-level sections:

- `scenario`
- `pokemon`
- `moves`
- `opponent_moves`

`scenario` contains:

- `mode`: currently `ui-selected-pokemon-v0.12`
- `format_note`: explains that this is selected Pokemon identity plus default-assumption user-confirmed move estimates and opponent move context, not full battle state
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

`moves.opponent_available_moves` remains a legacy compatibility field and is empty in v0.12. New opponent move semantics live in `opponent_moves`.

`opponent_moves` contains:

- `status`
- `known_moves`
- `candidate_moves`
- `candidate_moves_limit`
- `candidate_source_status`
- `unknown_moves`
- `limitations`

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
- `damage_estimate` on each user-confirmed entry in `opponent_moves.known_moves`

Each move `damage_estimate` contains:

- `status`
- `scope`
- `is_final_battle_damage`
- `target` when the estimate is for opponent known move damage against `my_active`
- `selected_move_id` when available
- `damage_range` when available
- `percent_range` when available
- `rolls` when available
- `assumptions`
- `derived_stats` when available
- `limitations`

## Opponent Move Semantics

Opponent move data is split into separate categories:

- `known_moves`: moves the user directly confirmed in the opponent Q/W/E/R slots. These are the only confirmed opponent moves.
- `candidate_moves`: possible moves from the Serebii-derived Champions movepool cache. These include `confidence: "possible_not_confirmed"` and are not the opponent's known moveset.
- `unknown_moves`: explicit state for missing or partial opponent move information.

Opponent candidate moves are capped by `candidate_moves_limit`. Known opponent moves may include `damage_estimate` in v0.12 when they are user-confirmed moves. Candidate moves do not include `damage_estimate` in v0.12.
Candidate moves may be mentioned as possible threats only when clearly labeled as unconfirmed. The advisor should use `my_available_moves[*].damage_estimate` to compare the user's own move options.
Opponent known move damage estimates use `target: "my_active"` and are rough threat references only.

## Explicitly Missing

The v0.12 payload does not contain:

- final calculated stats
- EV/IV/nature
- held item
- selected ability certainty
- weather
- terrain
- stat boosts
- exact current HP integer
- candidate move damage estimates
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
- treat `opponent_moves.candidate_moves` as confirmed opponent moves
- assume the opponent has a candidate move unless it appears in `opponent_moves.known_moves`
- claim candidate move damage, speed order, or turn order from v0.12 opponent move metadata
- describe opponent known move damage estimates as final battle damage
- invent opponent item, selected ability, EVs, IVs, nature, boosts, speed order, turn outcome, or final stats
- consider Terastallization, which is banned in PoChamps

The LLM may:

- explain broad type or role risks at a non-damage-exact level
- discuss user-confirmed move metadata such as type, category, power, accuracy, and PP
- discuss `damage_estimate` only under its stated default assumptions
- discuss `opponent_moves.known_moves` as user-confirmed opponent moves
- discuss `opponent_moves.known_moves[*].damage_estimate` only as default-assumption damage against `my_active`
- discuss `opponent_moves.candidate_moves` only as possible, not confirmed, Champions moves
- mention candidate moves as possible threats only when they are labeled as unconfirmed
- use `my_available_moves[*].damage_estimate` to compare the user's own move options
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
- `unavailable_no_known_move`
- `unavailable_status_move`
- `unavailable_missing_power`
- `unavailable_missing_pokemon`
- `unavailable_missing_base_stats`
- `unavailable_missing_type`
- `unavailable_unsupported_category`
- `unavailable_engine_error`

## Future Field Locations

Future versions may add candidate move threat scoring or opponent-to-my-active KO probability, but those require separate guardrails because candidate moves are not confirmed.

Turn Engine state should later enter a separate top-level `battle_state` section instead of being mixed into Pokemon identity metadata.

# v0.11 Opponent Move Payload Design

## Current v0.10 State

v0.10 payloads are centered on what the user's active Pokemon can do to the selected opponent.

Current `moves` fields:

- `my_available_moves`: user-confirmed move slots from the active my-team panel.
- `my_selected_move`: the currently selected user-confirmed move, if assigned.
- `my_available_moves[*].damage_estimate`: default-assumption damage estimate for each user-confirmed attacking move.
- `my_selected_move.damage_estimate`: selected-move estimate retained for direct selected-slot advice.
- `opponent_available_moves`: currently always `[]`.
- `opponent_selected_move`: currently `None`.
- `opponent_selected_move_index`: copied from the opponent panel, but no opponent move payload is attached.

The current contract gives Gemini a useful one-way view: "how much damage can my selected moves do to the opponent?" It does not yet represent what the opponent is known to have, might have, or is completely unknown to have.

## v0.11 Goal

v0.11 should introduce opponent move information without pretending the app has full battle state.

Goals:

- Represent user-confirmed opponent moves when T1 has observed or entered them.
- Represent Champions movepool candidates as possible moves only.
- Represent unknown opponent move state explicitly.
- Improve LLM advice by making opponent threat discussion more grounded.
- Prevent Gemini from treating possible candidates as confirmed moves.

The core distinction is:

- `known_moves`: user-confirmed opponent moves.
- `candidate_moves`: possible Champions movepool moves, not confirmed.
- `unknown_moves`: no confirmed opponent move information.

These categories must not be mixed.

## Options

### Option A - User-Confirmed Opponent Moves Only

Only moves explicitly entered by the user appear in the payload.

Pros:

- Safest semantics.
- Easy for the LLM to treat as confirmed.
- Reuses the existing `PokemonPanel.selected_moves` shape.
- Avoids sending a large candidate list.

Cons:

- Provides no threat context when the user has not entered opponent moves.
- T1 must manually enter opponent moves before the advisor can discuss specific threats.
- Does not use the Serebii Champions movepool cache for opponent threat discovery.

### Option B - Champions Candidate Moves Only

Populate opponent moves from the selected opponent Pokemon's Champions movepool.

Pros:

- Gives the LLM broad possible threat coverage immediately.
- Uses the Serebii-derived `ChampionsMovePoolRepository`.
- Can surface matchup-relevant risks even before the opponent reveals a move.

Cons:

- Highest risk of LLM overclaiming.
- Full movepools can be large and noisy.
- Candidate lists are not actual known movesets.
- Requires stronger contract language and likely candidate list capping/ranking.

### Option C - Hybrid

Keep user-confirmed moves and candidate moves in separate arrays.

Pros:

- Best balance of safety and usefulness.
- Lets confirmed moves stay authoritative.
- Lets candidate moves improve risk awareness without becoming "known".
- Matches the current app direction: user-confirmed data is authoritative; cache data is search/candidate context.

Cons:

- Requires precise schema labels and prompt guardrails.
- Candidate list size needs a policy.
- Tests must ensure known and candidate moves cannot collapse into one field.

## Recommended Direction

T3 recommends **Option C - Hybrid**.

Reasoning:

- The UI already has Q/W/E/R move slots on both team columns via `PokemonPanel.selected_moves`, so known opponent moves can reuse the existing panel state in a later implementation.
- `MainWindow._build_llm_battle_input()` currently builds my-side moves through `_panel_moves_payload(my_panel)` but leaves opponent moves empty. The same helper can eventually build known opponent moves from `opponent_panel`.
- `ChampionsMovePoolRepository` already exposes `get_allowed_move_ids_for_pokemon(...)`, `status_for_pokemon(...)`, and `get_move_metadata(...)`, making candidate move construction feasible without PokeAPI pokemon learnsets.
- `MoveRepository` can continue to provide move metadata via PokeAPI move cache or Champions movepool metadata fallback.

The design should add a new explicit `opponent_moves` structure instead of overloading the existing `opponent_available_moves` field. The older fields can remain for compatibility during transition, but v0.11 should treat `opponent_moves.known_moves` and `opponent_moves.candidate_moves` as the contract source of truth.

## Payload Schema Proposal

Recommended shape:

```json
{
  "opponent_moves": {
    "status": "partial_or_unknown",
    "known_moves": [
      {
        "slot": 0,
        "move_id": "earthquake",
        "name_en": "Earthquake",
        "name_ko": "지진",
        "type": "ground",
        "category": "physical",
        "power": 100,
        "accuracy": 100,
        "pp": 10,
        "source": "user_confirmed"
      }
    ],
    "candidate_moves": [
      {
        "move_id": "earthquake",
        "name_en": "Earthquake",
        "name_ko": "지진",
        "type": "ground",
        "category": "physical",
        "power": 100,
        "accuracy": 100,
        "pp": 10,
        "source": "champions_movepool",
        "confidence": "possible_not_confirmed"
      }
    ],
    "unknown_moves": {
      "has_user_confirmed_moves": false,
      "candidate_source_status": "available",
      "reason": "No opponent moves have been user-confirmed."
    },
    "limitations": [
      "Candidate moves are possible moves, not confirmed opponent moves.",
      "Do not assume the opponent has a candidate move unless user-confirmed.",
      "Opponent move damage is not calculated in v0.11."
    ]
  }
}
```

Status values:

- `unknown`: no user-confirmed moves and no candidate source.
- `candidate_only`: no user-confirmed moves, but Champions candidates are available.
- `known_only`: user-confirmed moves exist, candidates omitted or unavailable.
- `known_and_candidate`: both known and candidate moves are present.
- `unavailable_missing_champions_movepool`: candidate source missing for the opponent.

Field rules:

- `known_moves[*].source` must be `user_confirmed`.
- `candidate_moves[*].source` must be `champions_movepool`.
- `candidate_moves[*].confidence` must be `possible_not_confirmed`.
- Candidate moves must not include `damage_estimate` in v0.11.
- Known opponent moves should not include `damage_estimate` in v0.11 either.

Candidate list size policy:

- Full movepools can be large. The implementation should either:
  - send all candidates only if the list is small enough, or
  - send a capped list plus `candidate_count_total`, or
  - group candidates by type/category before sending.
- T3 recommends starting with a capped metadata list, for example 24 candidate moves, plus `candidate_count_total`.
- Candidate ranking can be a later improvement; avoid inventing threat ranking in v0.11 unless a deterministic ranking rule is added.

## UI Design Options

### Reuse Existing Opponent Q/W/E/R Slots

The opponent team column already uses `PokemonTeamColumn` and `PokemonPanel`. Each opponent panel already has:

- `selected_move_index`
- `selected_moves`
- move slot buttons
- `set_move(...)`

This means known opponent move entry can reuse the existing UI mechanics. When the active column is `team_enemy`, the shared `MoveSearchBox` already syncs candidates from the selected opponent Pokemon's Champions movepool. A future implementation can populate `known_moves` from `MainWindow._panel_moves_payload(opponent_panel)`.

Pros:

- Minimal structural UI change.
- Consistent interaction model.
- Avoids a separate "opponent move editor" in the first implementation.

Cons:

- The UI does not visually distinguish "my intended move slots" from "observed opponent moves" yet.
- Wording may need polish so users understand opponent slots mean observed/known opponent moves.

### Candidate Moves Without Direct UI Entry

Candidate moves can be built directly from `ChampionsMovePoolRepository` using the selected `pokemon.opponent_active.name_en`.

Pros:

- No UI changes required for candidate context.
- Works even before the user enters known opponent moves.

Cons:

- Candidate payload can be large.
- Requires strong guardrails because candidates are not confirmed.

### Separate Opponent Known-Move UI

Add an explicit opponent move editor later.

Pros:

- Clear semantics.
- Better labels for "observed opponent moves".

Cons:

- More UI work.
- Not necessary for the first v0.11 implementation because the existing panel already stores selected moves.

T3 recommends using the existing opponent panel slots for known moves in the implementation phase, while adding no UI changes during this design phase.

## Data Source Plan

Known moves:

- Source: `user_confirmed`.
- Origin: opponent panel Q/W/E/R slots after the user selects moves.
- Metadata: current `MoveRepository.get(...)` result serialized with `_move_payload(...)`.

Candidate moves:

- Source: `champions_movepool`.
- Origin: Serebii-derived Champions movepool cache through `ChampionsMovePoolRepository`.
- Metadata: `MoveRepository` using PokeAPI move cache first, Champions movepool metadata fallback second.
- Confidence: `possible_not_confirmed`.

Forbidden source:

- Do not use PokeAPI pokemon historical learnsets as opponent candidate source.
- PokeAPI move data may only be metadata fallback for type/category/power/accuracy/PP.

## Damage Estimate Boundary

v0.11 should not calculate opponent move damage.

Reasons:

- Opponent final stats, EVs, IVs, nature, item, selected ability, and boosts are not connected.
- My final stats and exact current HP are not connected.
- Speed order and Turn Engine state are not connected.
- Adding opponent damage now would invite survival and KO overclaims.

Recommended boundary:

- v0.11: opponent move payload only.
- v0.12: design or implement opponent-to-my-active default-assumption damage estimates.
- Later: final stat inputs, items, abilities, field state, speed order, and Turn Engine.

Explicitly excluded from v0.11:

- opponent damage estimate
- OHKO/2HKO/KO chance
- speed order
- Turn Engine

## Advisor Payload Contract Update Plan

`docs/advisor_payload_contract.md` should add:

- `opponent_moves` as the preferred opponent move section.
- `known_moves` definition: user-confirmed opponent moves only.
- `candidate_moves` definition: Champions possible moves only, not confirmed.
- `unknown_moves` definition: no confirmed opponent move information.
- statement that opponent move damage is not calculated in v0.11.

`llm/advisor_payload_contract.py` should add guardrail strings:

- "Known opponent moves are user-confirmed only."
- "Opponent candidate moves are possible Champions moves, not confirmed moves."
- "Do not assume the opponent has a candidate move unless it is in known_moves."
- "Opponent move damage is not calculated in v0.11."
- "Opponent item, selected ability, final stats, speed order, and Turn Engine state remain unknown."

The prompt in `llm/advisor_client.py` should eventually be updated to mention candidate move semantics explicitly, but that is implementation work and out of scope for this design-only goal.

## Allowed LLM Claims

The LLM may say:

- "The opponent may have candidate move X, but it is not confirmed."
- "Known move X should be considered because it was user-confirmed."
- "No opponent moves are confirmed yet, so the threat read is limited."
- "Candidate moves suggest possible coverage risks."
- "Opponent damage is not calculated in this payload."

## Disallowed LLM Claims

The LLM must not:

- Treat a candidate move as part of the opponent's actual moveset.
- Say the opponent will use a candidate move.
- Claim opponent damage estimates that are not present.
- Claim speed order or turn order.
- Assume item, ability choice, EVs, IVs, nature, boosts, weather, terrain, or exact HP.
- Claim Turn Engine state.
- Use PokeAPI historical learnsets as legality evidence.

## Tests Plan

Future implementation tests should cover:

- `known_moves` and `candidate_moves` are separate fields.
- Known opponent moves are built from the opponent panel only when user-confirmed.
- Candidate moves include `confidence: "possible_not_confirmed"`.
- Unknown opponent move state is represented clearly when no user-confirmed moves exist.
- Candidate source missing produces an unavailable status instead of silent PokeAPI learnset fallback.
- PokeAPI pokemon historical learnsets are never used as candidate source.
- Candidate moves do not include `damage_estimate` in v0.11.
- Existing v0.10 `my_available_moves[*].damage_estimate` remains unchanged.
- Advisor contract guardrails include candidate-not-confirmed language.
- Prompt-level tests ensure candidate moves are not described as confirmed moves.

Likely test files:

- `tests/test_advisor_payload_contract.py`
- `tests/test_move_search_champions_candidates.py`
- a new `tests/test_opponent_move_payload.py` if a helper module is introduced.

## Out of Scope

Excluded from this design milestone:

- code implementation
- UI changes
- opponent damage estimate
- OHKO/2HKO/KO chance
- speed order
- Turn Engine
- EV/IV/nature/item/final stats UI
- switch recommendation
- lead recommendation
- Minimax/Critic loop
- automatic LLM call
- streaming/cancel/retry
- `advisor/damage` changes
- `advisor/probability` changes

## Implementation Plan For A Later Milestone

Suggested narrow implementation sequence:

1. Add `llm/opponent_move_payload.py` or similar helper.
2. Build `known_moves` from `opponent_panel.selected_moves`.
3. Build `candidate_moves` from `ChampionsMovePoolRepository` and `MoveRepository`.
4. Add `opponent_moves` to `_build_llm_battle_input()`.
5. Keep legacy `opponent_available_moves` empty or mirror `known_moves` only after T1/T2 decides compatibility policy.
6. Update advisor payload contract constants and docs.
7. Add regression tests for separation, labels, and no PokeAPI learnset fallback.

## Rollback Plan

If the v0.11 implementation causes LLM overclaims or payload bloat:

1. Remove `opponent_moves.candidate_moves` while keeping `known_moves`.
2. Keep known opponent moves user-confirmed only.
3. Preserve the v0.10 my-side damage payload unchanged.
4. Re-run payload contract and full pytest.

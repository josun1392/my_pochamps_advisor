# v0.12 Opponent Move Damage Estimate Design

## Current v0.11 State

The current advisor payload has three relevant pieces:

- `moves.my_available_moves[*].damage_estimate`: default-assumption damage estimates for each user-confirmed move on the user's active Pokemon.
- `moves.my_selected_move.damage_estimate`: selected-move estimate retained for direct selected-slot advice.
- `opponent_moves.known_moves`: user-confirmed opponent Q/W/E/R moves.
- `opponent_moves.candidate_moves`: possible Champions movepool moves with `confidence: "possible_not_confirmed"`.

v0.11 does not calculate damage for opponent moves. Gemini can see that a known opponent move exists, but it cannot see how much that confirmed move might threaten the user's active Pokemon.

## v0.12 Goal

v0.12 should add default-assumption damage estimates for confirmed opponent moves only.

Goal:

- For each `opponent_moves.known_moves[*]`, estimate damage from `pokemon.opponent_active` into `pokemon.my_active`.
- Keep the estimate as a rough reference, not final battle damage.
- Let Gemini consider both:
  - the user's four-move damage comparison, and
  - the risk from confirmed opponent moves.

This is still not a full battle simulator. It should not decide turn order, survival, or KO odds.

## Scope Options

### Option A - Known Opponent Moves Only

Attach `damage_estimate` only to `opponent_moves.known_moves`.

Pros:

- Safest semantic boundary.
- The move is user-confirmed, so a threat estimate is meaningful.
- Keeps candidate moves from becoming over-weighted by the LLM.
- Reuses the v0.9/v0.10 default-assumption damage estimate shape.

Cons:

- If no opponent moves are confirmed, v0.12 adds no opponent damage information.
- Still uses default stats, not real battle stats.

### Option B - Known + Candidate Moves

Attach damage estimates to both known and candidate opponent moves.

Pros:

- Gives broader threat coverage.
- Could reveal possible coverage risks quickly.

Cons:

- Candidate moves are not confirmed.
- Payload can become large.
- Gemini may overclaim candidate threats as actual moves.
- Candidate damage estimates would make uncertain data look more authoritative.

This is too broad for v0.12.

### Option C - No Opponent Damage Yet

Only strengthen guardrails and keep opponent move payload as-is.

Pros:

- Safest.
- No additional risk of overclaiming.

Cons:

- Little functional progress after v0.11.
- Known opponent moves remain qualitative only.

## T3 Recommendation

T3 recommends **Option A - Known Opponent Moves Only**.

Reasoning:

- v0.11 already separates known moves from candidate moves.
- Known moves are user-confirmed, so a default-assumption threat estimate is reasonable.
- Candidate moves should remain possible/unconfirmed only.
- This keeps v0.12 small and matches the existing contract style.

## Payload Schema Proposal

Recommended location:

```json
{
  "opponent_moves": {
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
        "source": "user_confirmed",
        "damage_estimate": {
          "status": "available_with_default_assumptions",
          "scope": "opponent_known_move_only",
          "is_final_battle_damage": false,
          "target": "my_active",
          "selected_move_id": "earthquake",
          "damage_range": {
            "min": 0,
            "max": 0
          },
          "percent_range": {
            "min": 0.0,
            "max": 0.0,
            "denominator": "default_defender_max_hp"
          },
          "rolls": [0, 0],
          "assumptions": {
            "level": 50,
            "ivs": "31 all",
            "evs": "0 all",
            "nature": "neutral",
            "item": "none",
            "boosts": "none",
            "weather": "none",
            "terrain": "none",
            "screens": "none",
            "critical": false,
            "doubles": false,
            "ability_effects": "not_applied_unselected"
          },
          "limitations": [
            "This is not final battle damage.",
            "Opponent item, ability, EV/IV/nature, boosts, and final stats are not connected.",
            "Use as rough threat reference only.",
            "OHKO/2HKO/KO chance is not provided in v0.12."
          ]
        }
      }
    ],
    "candidate_moves": [
      {
        "move_id": "stone-edge",
        "confidence": "possible_not_confirmed"
      }
    ]
  }
}
```

Unavailable status examples:

- `unavailable_status_move`
- `unavailable_missing_power`
- `unavailable_missing_pokemon`
- `unavailable_missing_base_stats`
- `unavailable_missing_type`
- `unavailable_engine_error`

Rules:

- `target` should be `"my_active"` for opponent move estimates.
- `scope` should be `"opponent_known_move_only"`.
- `is_final_battle_damage` must remain `false`.
- OHKO/2HKO/KO chance fields must not appear.
- Candidate moves must not include `damage_estimate`.

## Candidate Moves Boundary

v0.12 should not attach damage estimates to `opponent_moves.candidate_moves`.

Reasons:

- Candidate moves are not confirmed.
- Candidate damage estimates would expand payload size.
- Damage values can make possible moves look too authoritative.
- This increases overclaim risk in Gemini output.

Future candidate threat scoring can be considered separately after known move damage is verified.

## Damage Calculation Direction

The calculation direction is reversed from v0.10:

- attacker: `pokemon.opponent_active`
- defender: `pokemon.my_active`
- move: one entry from `opponent_moves.known_moves`

Default assumptions remain identical to v0.9/v0.10:

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
- singles / non-spread
- no ability effects unless explicitly selected and connected

Current helper notes:

- `llm/advisor_damage_estimate.py` already has reusable stat-building and damage-roll logic.
- `build_move_damage_estimate(...)` currently assumes `my_active` is attacker and `opponent_active` is defender.
- v0.12 should avoid modifying `advisor/damage/*`.
- Recommended implementation is to extend the LLM helper to accept attacker/defender keys or explicit attacker/defender payloads.

Possible helper shape:

```python
build_move_damage_estimate(
    battle_input,
    move,
    scope="opponent_known_move_only",
    attacker_key="opponent_active",
    defender_key="my_active",
    target="my_active",
)
```

or:

```python
build_damage_estimate_for_move(
    *,
    attacker,
    defender,
    move,
    scope,
    target,
)
```

T3 prefers the second shape if implementation remains small, because it avoids adding too many hidden assumptions to the existing selected-move helper.

## UI Boundary

No UI changes are needed for v0.12.

Assumptions:

- Opponent known move entry already comes from the opponent `PokemonPanel.selected_moves`.
- The user confirms opponent Q/W/E/R moves through the existing move slot UI.
- v0.12 should only enrich those known moves in the payload.

## Advisor Payload Contract Update Plan

`docs/advisor_payload_contract.md` should add:

- opponent known move damage estimate is a default-assumption reference only
- candidate move damage is not calculated
- opponent damage estimate targets `my_active`
- opponent damage is not final battle damage
- OHKO/2HKO/KO chance is not provided

`llm/advisor_payload_contract.py` should add guardrails:

- "Opponent known move damage estimates use default assumptions and are not final battle damage."
- "Candidate move damage is not calculated."
- "Do not claim OHKO, 2HKO, KO chance, survival, speed order, or turn order from opponent damage estimates."
- "Do not infer opponent item, selected ability, EVs, IVs, nature, boosts, final stats, weather, terrain, or exact HP."

`llm/advisor_client.py` can later get a small prompt addition:

- use opponent known move damage as rough threat reference only
- never apply candidate damage because it is not present

## Allowed LLM Claims

The LLM may say:

- "The confirmed opponent move Earthquake may be dangerous under default assumptions."
- "This opponent damage estimate is not final battle damage."
- "Candidate moves are possible moves only, not confirmed."
- "The user's move comparison still favors move X under default assumptions."

## Disallowed LLM Claims

The LLM must not:

- Claim candidate move damage was calculated.
- Treat candidate moves as actual opponent moves.
- Describe opponent damage as final battle damage.
- Claim OHKO/2HKO/KO chance or survival.
- Claim speed order or turn order.
- Assume item, selected ability, EVs, IVs, nature, boosts, weather, terrain, exact HP, or final stats.
- Claim Turn Engine outcomes.

## Tests Plan

Future implementation tests should cover:

- known opponent move receives `damage_estimate`
- candidate move does not receive `damage_estimate`
- status known move returns `unavailable_status_move`
- missing-power known move returns `unavailable_missing_power`
- estimate has `target: "my_active"`
- estimate has `scope: "opponent_known_move_only"`
- `is_final_battle_damage` remains `false`
- no `ko_chance`, `ohko_chance`, or `two_hko_chance` fields appear
- existing `my_available_moves[*].damage_estimate` remains intact
- known/candidate guardrails remain in contract
- no `advisor/damage` or `advisor/probability` changes are required

Likely test files:

- `tests/test_advisor_damage_estimate.py`
- `tests/test_advisor_payload_contract.py`
- possibly a new `tests/test_opponent_damage_estimate.py` if the helper is split.

## Out of Scope

Excluded from v0.12 design:

- code implementation
- UI changes
- candidate move damage estimate
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

## Implementation Sequence For Later

Suggested implementation path:

1. Refactor `llm/advisor_damage_estimate.py` so the core move estimate accepts explicit attacker/defender payloads.
2. Preserve existing v0.10 my-side estimate behavior.
3. Add an attach helper for `opponent_moves.known_moves[*].damage_estimate`.
4. Do not touch `opponent_moves.candidate_moves`.
5. Update contract constants and docs.
6. Add targeted tests.
7. Run full pytest.

## Rollback Plan

If opponent damage estimates cause LLM overclaims:

1. Remove `damage_estimate` from `opponent_moves.known_moves`.
2. Keep v0.11 `known_moves` and `candidate_moves` payload intact.
3. Revert prompt/contract language specific to opponent damage.
4. Re-run payload contract tests and full pytest.

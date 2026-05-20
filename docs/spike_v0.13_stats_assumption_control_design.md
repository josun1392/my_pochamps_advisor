# v0.13 Stats Assumption Control Design

## 1. Current Damage Assumption State

Current payload damage estimates are attached in three places:

- `moves.my_available_moves[*].damage_estimate`
- `moves.my_selected_move.damage_estimate`
- `opponent_moves.known_moves[*].damage_estimate`

All three use the same default-assumption stat model. They are useful for rough move comparison, but they are not final battle damage.

Current assumptions:

- level: 50
- IV: 31 all
- EV: 0 all
- nature: neutral
- item: none
- boosts: none
- weather: none
- terrain: none
- screens: none
- critical: false
- doubles: false
- ability effects: not_applied_unselected
- final stats: not connected
- exact HP: not connected

Implementation today:

- `llm/advisor_payload_contract.py` owns `ADVISOR_DAMAGE_ASSUMPTIONS`.
- `llm/advisor_damage_estimate.py` owns `DEFAULT_LEVEL`, `DEFAULT_IVS`, `DEFAULT_EVS`, and `DEFAULT_BOOSTS`.
- `_default_stats()` converts Pokemon `base_stats` into a `StatBlock` using `StatInputs`, `nature_from_name("hardy")`, and `final_stats()`.
- `build_move_damage_estimate()` passes those calculated default stats into `DamageContext`.
- `percent_range` uses default defender max HP, not exact current HP.

## 2. Problem Definition

Default assumptions are intentionally conservative, but they can differ substantially from real battle state.

Important gaps:

- EVs can change attack, defense, special attack, special defense, speed, and HP.
- IVs are currently assumed to be 31 all.
- Nature can swing non-HP stats by 10%.
- Held items can affect stats, damage, and survival.
- Final stats are not connected, so exact stat values from a team sheet cannot be used.
- Exact current HP is not connected, so `percent_range` is based on default max HP only.
- Boosts, weather, terrain, screens, and ability/item effects are either absent or not selected with certainty.
- Speed order and KO/OHKO/2HKO are still out of scope.

As a result, the LLM must continue to treat damage estimates as rough references unless the payload explicitly says a stronger stat profile was provided.

## 3. Option Comparison

### Option A - Keep Default Assumptions Only

Pros:

- Safest implementation path.
- No UI or schema expansion.
- Existing v0.10/v0.12 behavior remains stable.

Cons:

- Accuracy ceiling remains low.
- Users cannot improve estimates with known team data.
- LLM must keep using broad limitation language.

### Option B - Add Assumption Profile Only

Pros:

- Clarifies what stat model produced each damage estimate.
- Does not require UI implementation yet.
- Provides a stable payload contract before adding user inputs.
- Lets future profiles become explicit without changing every consumer again.

Cons:

- Does not improve numeric accuracy by itself.
- Requires contract and tests in the next implementation step.

Example profile id:

```json
"default_level50_ivs31_evs0_neutral_no_item"
```

### Option C - Add Manual Stat Inputs

Pros:

- Can improve damage accuracy significantly.
- Can support real team-sheet data.

Cons:

- UI/validation scope is large.
- EV/IV/nature/item interactions need careful UX.
- Higher risk of partial or inconsistent inputs.

### Option D - Add Final Stats Only

Pros:

- Fastest path to more accurate damage.
- Avoids EV/nature calculation UI at first.
- Damage helper can use exact `StatBlock` values directly.

Cons:

- UX is more manual.
- Users must know final stats.
- Does not explain how stats were derived.

## 4. Recommended Direction

T3 recommends Option B for v0.13 design and the next implementation step.

Recommended roadmap:

- v0.13: Define assumption profile schema and contract.
- v0.14: Add either final stats input or a compact hybrid stat profile.
- v0.15: Add EV/IV/nature/item/boost/weather expansions only after the profile contract is stable.

This keeps the payload honest now while creating a clean path toward higher accuracy.

## 5. Proposed Payload Schema

Add `assumption_profile` beside `assumptions` inside every damage estimate.

```json
{
  "damage_estimate": {
    "status": "available_with_default_assumptions",
    "scope": "available_move_comparison",
    "is_final_battle_damage": false,
    "assumption_profile": {
      "id": "default_level50_ivs31_evs0_neutral_no_item",
      "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
      "source": "system_default",
      "confidence": "rough_reference",
      "is_user_confirmed": false
    },
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
      "Final stats are not connected.",
      "Use as rough reference only."
    ]
  }
}
```

Recommended profile fields:

- `id`: stable machine-readable profile id
- `label`: short human-readable summary
- `source`: `system_default`, `user_confirmed`, or future source id
- `confidence`: `rough_reference`, `user_confirmed_stats`, or future confidence label
- `is_user_confirmed`: boolean

Keep `assumptions` for compatibility and readability. Add `assumption_profile` to make the meaning explicit.

## 6. Future Stat Input Models

### Model 1 - Final Stats Input

User directly enters HP / Atk / Def / SpA / SpD / Spe.

Pros:

- Directly usable by `DamageContext`.
- Avoids EV/nature UI complexity.
- Fastest way to improve damage estimates.

Cons:

- Users must know exact final stats.
- Less friendly for users thinking in EVs/nature.

### Model 2 - EV/IV/Nature Input

User enters a real Pokemon spread.

Pros:

- Natural for team building.
- `advisor/damage/stats.py` already has `StatInputs` and `final_stats()`.

Cons:

- Validation and UI are more involved.
- Champions-specific EV constraints need careful handling.

### Model 3 - Preset Profiles

Examples: offensive, bulky, neutral.

Pros:

- Fast input.
- Useful for rough scouting.

Cons:

- Still not exact.
- Presets can encourage false confidence if not labeled strongly.

### Model 4 - Hybrid

Start with final stats input and later add EV/IV/nature calculation.

Pros:

- Good balance of accuracy and implementation cost.
- Does not block future advanced mode.

Cons:

- Requires a clear UI mode switch later.

T3 recommends Model 4 as the long-term direction, with Model 1 as the first implementation slice.

## 7. Data Model Design

Two schema locations are possible.

### Option 1 - Store Profiles In Each Damage Estimate

Pros:

- Each estimate is self-contained.
- Easy for the LLM to inspect locally.
- Minimal top-level schema change.

Cons:

- Repeats the same profile many times.

### Option 2 - Add Top-Level `stat_profiles`

Example:

```json
{
  "stat_profiles": {
    "my_active": {
      "status": "default_assumption",
      "level": 50,
      "final_stats": null,
      "evs": null,
      "ivs": "31 all",
      "nature": "neutral",
      "item": null,
      "source": "system_default"
    },
    "opponent_active": {
      "status": "default_assumption",
      "level": 50,
      "final_stats": null,
      "evs": null,
      "ivs": "31 all",
      "nature": "neutral",
      "item": null,
      "source": "system_default"
    }
  }
}
```

Pros:

- Avoids repeated profile data.
- Better once users can edit stats.
- Lets multiple damage estimates reference `my_active` and `opponent_active`.

Cons:

- Requires more payload plumbing.
- Each `damage_estimate` still needs to say which profile it used.

Recommended approach:

- v0.13/v0.13.1: add `assumption_profile` inside damage estimates.
- v0.14: introduce top-level `stat_profiles` only when user-editable stats are added.
- Future estimates can reference profile ids such as `my_active.current` and `opponent_active.current`.

## 8. UI Design Options

No UI implementation should happen in v0.13.

Future UI candidates:

- Simple mode: level / item / nature only.
- Final stats direct input mode: HP / Atk / Def / SpA / SpD / Spe.
- EV/IV/nature calculation mode.
- Advanced collapsible panel on the selected Pokemon card.
- A small stat profile editor reachable from the selected Pokemon panel.

Recommended v0.14 UX:

- Add a compact "Final Stats" editor for selected active Pokemon only.
- Keep defaults visible.
- Label edited stats as user-confirmed.
- Avoid item/boost/weather UI until the stat profile path is proven.

## 9. Damage Helper Impact

Files investigated:

- `llm/advisor_damage_estimate.py`
- `advisor/damage/stats.py`
- `advisor/damage/formula.py`
- `ui/main_window.py`
- `llm/advisor_payload_contract.py`
- `docs/advisor_payload_contract.md`
- `tests/test_advisor_damage_estimate.py`

Findings:

- `build_move_damage_estimate()` already centralizes estimate creation.
- `_default_stats()` currently constructs final stats from `base_stats`, `DEFAULT_EVS`, `DEFAULT_IVS`, neutral nature, and level 50.
- `advisor/damage/stats.py` already exposes `StatInputs` and `final_stats()`, so EV/IV/nature support can reuse existing primitives later.
- `DamageContext` accepts concrete `attack_stat`, `defense_stat`, `attacker_stats`, and `defender_stats`, so final stat injection does not require damage engine changes.
- `ui/main_window.py` currently sends `base_stats` only, with no `final_stats`, `evs`, `ivs`, `nature`, or `item`.

Minimal future implementation path:

1. Add `ADVISOR_DEFAULT_ASSUMPTION_PROFILE` constant.
2. Add `assumption_profile` to both available and unavailable damage estimate schemas.
3. Add tests that every estimate includes the default profile id.
4. Later, allow `_default_stats()` to become `_stats_for_profile(pokemon, profile)`.
5. When final stats are provided, build `StatBlock` directly instead of deriving from base stats.

No `advisor/damage/` or `advisor/probability/` engine changes are needed for the first stat profile step.

## 10. Advisor Payload Contract Update Plan

Future contract updates should state:

- Default-assumption damage is a rough reference only.
- `assumption_profile` identifies the stat model used for an estimate.
- Final battle stats are not connected unless explicitly provided.
- The LLM must not infer EVs, IVs, nature, items, boosts, weather, terrain, exact HP, or speed order.
- If `assumption_profile.source == "system_default"`, the model should say "default assumptions" or equivalent.
- If a future profile is `user_confirmed`, the model may speak with higher confidence about damage range, but still must not claim KO/OHKO/2HKO unless those fields are explicitly provided.

## 11. Allowed LLM Claims

The LLM may say:

- "Under the default assumptions, this move is stronger."
- "This damage is a rough reference."
- "The result can change with the actual spread, item, nature, field, or boosts."
- "More accurate advice needs final stats or item information."
- "This estimate used the default Level 50 profile."

## 12. Disallowed LLM Claims

The LLM must not:

- Describe default damage as final battle damage.
- Invent EVs, IVs, nature, item, boosts, weather, terrain, or final stats.
- Confirm speed order.
- Confirm KO chance, OHKO, or 2HKO.
- Claim exact survival without a user-confirmed stat profile and explicit survival/KO calculation.
- Treat base stats as final stats.

## 13. Tests Plan

Future implementation tests:

- Every available move damage estimate includes `assumption_profile`.
- `moves.my_selected_move.damage_estimate.assumption_profile.id` equals the default profile id.
- `opponent_moves.known_moves[*].damage_estimate.assumption_profile.id` equals the default profile id.
- Unavailable estimates include the same profile and limitations.
- `is_final_battle_damage` remains false when final stats are missing.
- Future `user_confirmed` profile schema does not break existing v0.10/v0.12 tests.
- Existing my-side and opponent-side damage regression tests continue passing.
- Contract guardrails mention default profile semantics.

Expected test impact for the profile-only implementation: roughly 3-6 new or updated tests.

## 14. Out of Scope

Excluded from v0.13:

- code implementation
- UI implementation
- final stats input implementation
- EV/IV/nature/item input implementation
- damage engine changes
- probability engine changes
- KO/OHKO/2HKO
- speed order
- Turn Engine
- weather/terrain/boost/screen UI
- switch recommendation
- lead recommendation
- Minimax/Critic loop
- automatic LLM call

## 15. Rollback Plan

If the next implementation proves too noisy:

1. Revert the profile-only payload changes.
2. Keep existing `assumptions` and limitations.
3. Continue using current v0.12 default-assumption behavior.

Because this v0.13 step is design-only, rollback is simply deleting this design document commit.

## 16. T1/T2 Decisions Needed

- Confirm whether v0.13 implementation should be profile-only.
- Choose whether v0.14 should start with final stats input or a hybrid profile editor.
- Decide whether top-level `stat_profiles` should wait until editable stats exist.
- Decide whether item selection belongs with stat profiles or should be a separate later milestone.

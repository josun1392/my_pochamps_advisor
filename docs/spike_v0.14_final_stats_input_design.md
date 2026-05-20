# v0.14 Final Stats Input Design

## 1. Current v0.13 State

The current payload includes default-assumption damage estimates in these locations:

- `moves.my_available_moves[*].damage_estimate`
- `moves.my_selected_move.damage_estimate`
- `opponent_moves.known_moves[*].damage_estimate`

Each damage estimate now includes:

- `assumption_profile`
- `assumptions`
- `is_final_battle_damage: false`
- default-assumption limitations

Current default profile:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_no_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
  "source": "system_default",
  "confidence": "rough_reference",
  "is_user_confirmed": false
}
```

Final stats are not connected. The helper still derives stats from species `base_stats` using level 50, IV 31 all, EV 0 all, and neutral nature.

## 2. Problem Definition

The v0.13 metadata makes the assumption model explicit, but the numeric damage values are still rough references.

Why final stats matter:

- HP changes the denominator used by `percent_range`.
- Atk and SpA change damage dealt by physical and special moves.
- Def and SpD change incoming damage.
- Spe does not affect damage directly, but users naturally expect it to matter for turn order later.
- Real Champions builds can differ from the current neutral spread.

Without final stats:

- `damage_range` can differ from the real battle value.
- `percent_range` uses default defender max HP, not exact max HP.
- my-side and opponent-side estimates can both be underconfident.
- LLM advice must keep saying "default assumptions" and avoid final-damage language.

Final stats input is the smallest useful step toward better damage accuracy because it avoids building EV/IV/nature/item UI all at once.

## 3. Option Comparison

### Option A - Keep Default Assumptions Only

Pros:

- No implementation risk.
- Current tests and payload contract remain stable.

Cons:

- Damage accuracy remains limited.
- Users cannot improve estimates with known stats.
- `assumption_profile` remains descriptive only.

### Option B - Final Stats Input

Users directly enter HP / Atk / Def / SpA / SpD / Spe.

Pros:

- Damage helper can use final stats directly.
- Avoids EV/IV/nature validation for now.
- Faster route to more accurate damage estimates.
- Works symmetrically for `my_active` and `opponent_active`.

Cons:

- Users need to know final stats.
- Does not capture how those stats were produced.
- Still excludes item, ability, boost, weather, terrain, and screen effects.

### Option C - EV/IV/Nature Input

Pros:

- Closer to team-builder language.
- Existing `advisor/damage/stats.py` already has `StatInputs` and `final_stats()`.

Cons:

- UI and validation scope is larger.
- Champions EV constraints need careful handling.
- Nature and item interactions add more edge cases.

### Option D - Hybrid

Start with direct final stats, then later add EV/IV/nature calculation mode.

Pros:

- Best long-term direction.
- Keeps v0.14 small while preserving a path to proper spread editing.

Cons:

- Requires a clear UI mode distinction later.

## 4. Recommended Direction

T3 recommends:

- v0.14 design direction: Option B, direct Final Stats Input.
- Long-term direction: Option D, hybrid stat profile editor.
- v0.14 implementation candidate: add `stat_profiles.my_active` and `stat_profiles.opponent_active`, plus a compact UI path to enter six final stats.
- v0.15+ candidates: item selection, then EV/IV/nature, then boosts/weather/terrain.

This sequence improves damage accuracy without forcing the full team-builder problem into one milestone.

## 5. Proposed Payload Schema

T3 recommends adding a top-level `stat_profiles` section in v0.14.

```json
{
  "stat_profiles": {
    "my_active": {
      "status": "user_confirmed_final_stats",
      "source": "user_input",
      "level": 50,
      "final_stats": {
        "hp": 153,
        "atk": 104,
        "def": 98,
        "spa": 161,
        "spd": 105,
        "spe": 167
      },
      "evs": null,
      "ivs": null,
      "nature": null,
      "item": null,
      "notes": [
        "Final stats are user-provided.",
        "EV/IV/nature breakdown is not connected."
      ]
    },
    "opponent_active": {
      "status": "default_assumption",
      "source": "system_default",
      "level": 50,
      "final_stats": null,
      "evs": null,
      "ivs": "31 all",
      "nature": "neutral",
      "item": null,
      "notes": [
        "No user-confirmed final stats are available.",
        "Damage estimates use the default stat profile."
      ]
    }
  }
}
```

### Top-Level `stat_profiles` vs Pokemon Payload Fields

#### Top-Level `stat_profiles`

Pros:

- Clear symmetry between `my_active` and `opponent_active`.
- Easier for damage helper to read by role.
- Avoids mixing identity metadata with user-edited battle stats.
- Future expansion can add `item`, `nature`, `evs`, and `boosts` cleanly.
- LLM can inspect stat confidence without digging through Pokemon identity.

Cons:

- Adds one top-level payload section.
- Damage estimates need to reference which profile they used.

#### Inside `pokemon.my_active` / `pokemon.opponent_active`

Pros:

- Stat data sits near Pokemon identity.
- Fewer top-level sections.

Cons:

- Blurs species reference data and user-confirmed battle stats.
- Harder to distinguish `base_stats` from `final_stats`.
- More likely to encourage LLM confusion.

T3 recommends top-level `stat_profiles`.

## 6. Damage Estimate Profile Behavior

When no final stats are provided:

```json
{
  "id": "default_level50_ivs31_evs0_neutral_no_item",
  "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
  "source": "system_default",
  "confidence": "rough_reference",
  "is_user_confirmed": false
}
```

When final stats are provided for all six stats:

```json
{
  "id": "user_confirmed_final_stats_level50",
  "label": "User-confirmed final stats / Level 50",
  "source": "user_input",
  "confidence": "higher_confidence_reference",
  "is_user_confirmed": true
}
```

Recommended behavior:

- `is_final_battle_damage` remains `false`.
- `assumption_profile.is_user_confirmed` becomes `true` only for estimates whose attacker/defender profile used user-confirmed final stats.
- If only one side has final stats, the profile should say so explicitly in either `assumption_profile` or `derived_stats`.
- Limitations must still mention missing item, ability, boosts, weather, terrain, screens, exact current HP, and KO odds.

Possible future profile variants:

- `user_confirmed_attacker_final_stats_level50`
- `user_confirmed_defender_final_stats_level50`
- `user_confirmed_both_final_stats_level50`

T3 recommends the third variant only when both attacker and defender final stats are used. For v0.14 implementation, one generalized profile can also include `stats_used`:

```json
{
  "stats_used": {
    "attacker": "user_confirmed_final_stats",
    "defender": "default_assumption"
  }
}
```

This avoids overstating confidence when only one side is confirmed.

## 7. UI Design Options

No UI implementation should happen in this design goal.

### UI-A - PokemonPanel Compact Final Stats Editor

Pros:

- Keeps stats near the selected Pokemon.
- Quick to see and edit.

Cons:

- Current panels are already dense.
- Six inputs can make the roster cards cramped.
- Risky on smaller windows.

### UI-B - StatProfileDialog

Pros:

- Avoids overcrowding PokemonPanel.
- Can support both my/opponent panels.
- Easy to expand later with EV/IV/nature.
- Lower risk to current layout.

Cons:

- Requires an extra button/action to open.
- Slightly slower for repeated edits.

### UI-C - Advanced Collapsible Section

Pros:

- Keeps advanced controls on the main screen when expanded.
- Could be useful for power users.

Cons:

- Layout complexity increases.
- Current three-column UI is already space-constrained.

### UI-D - JSON/Debug Input First

Pros:

- Fastest implementation.
- Useful for developer validation.

Cons:

- Poor user experience.
- Easy to enter invalid data.

T3 recommends UI-B for v0.14 implementation: a `StatProfileDialog` opened from the selected Pokemon panel or central controls. UI-C can be revisited later.

## 8. Validation Rules

Minimum v0.14 validation:

- HP must be an integer >= 1.
- Atk / Def / SpA / SpD / Spe must be integers >= 1.
- Level defaults to 50.
- Partial final stats are not accepted as user-confirmed.
- If any stat is blank, the profile should remain `default_assumption` or show validation failure.
- Do not mix partial user stats with default stats silently.

T3 recommends:

- Reject partial final stats in the UI.
- Payload builder should only emit `user_confirmed_final_stats` when all six stats are present.
- Invalid user input should stay in UI validation and should not reach the LLM payload.

Optional guardrails:

- Warn for suspiciously low or high values, but do not overconstrain until Champions stat ranges are formally encoded.
- Do not infer EV/IV/nature from final stats.

## 9. Damage Helper Impact

Files investigated:

- `llm/advisor_damage_estimate.py`
- `advisor/damage/stats.py`
- `advisor/damage/formula.py`
- `ui/main_window.py`
- `ui/widgets/pokemon_panel.py`
- `llm/advisor_payload_contract.py`
- `docs/advisor_payload_contract.md`
- `tests/test_advisor_damage_estimate.py`

Findings:

- `llm/advisor_damage_estimate.py` currently uses `_default_stats(pokemon)` to derive a `StatBlock`.
- `advisor/damage/stats.py` already defines `StatBlock`, `StatInputs`, and `final_stats()`.
- `advisor/damage/formula.py` accepts concrete `attack_stat`, `defense_stat`, `attacker_stats`, and `defender_stats` in `DamageContext`.
- Therefore, v0.14 can inject final stats without modifying `advisor/damage/`.
- `ui/main_window.py` currently emits `base_stats` only through `_panel_to_llm_payload()`.
- `ui/widgets/pokemon_panel.py` has HP percent and selected moves, but no final stat storage.

Minimal v0.14 implementation path:

1. Add a stat profile payload builder in `ui/main_window.py`.
2. Add optional final stat storage to the UI layer, preferably outside the card layout if using a dialog.
3. Add `stat_profiles` top-level section.
4. Update `llm/advisor_damage_estimate.py` so `_default_stats()` becomes a profile-aware resolver:
   - if user-confirmed final stats exist, build `StatBlock` directly
   - otherwise use current default derivation
5. Update `assumption_profile` based on which roles used user-confirmed final stats.
6. Keep `is_final_battle_damage: false`.

No damage or probability engine changes are required.

## 10. Advisor Payload Contract Update Plan

Future contract updates should state:

- `stat_profiles.my_active` and `stat_profiles.opponent_active` describe stat confidence for the active Pokemon.
- `user_confirmed_final_stats` means those six final stat values were user-provided.
- User-confirmed final stats can be treated as more reliable than system defaults.
- User-confirmed final stats still do not imply final battle damage.
- Missing item, ability, boosts, weather, terrain, screens, exact current HP, and KO odds still limit confidence.
- The LLM may mention stat profile source.
- The LLM must not infer EVs, IVs, nature, item, or speed order from final stats.
- The LLM must not claim KO/OHKO/2HKO unless explicit KO probability fields exist.

## 11. Allowed LLM Claims

The LLM may say:

- "Using the user-provided final stats, this move is estimated to do more damage."
- "The user's active Pokemon has confirmed final stats, while the opponent still uses defaults."
- "This is still not final battle damage because item, ability, boosts, and field state are not connected."
- "More accurate advice needs both sides' final stats and item information."

## 12. Disallowed LLM Claims

The LLM must not:

- Treat partial final stats as a complete battle profile.
- Infer EVs, IVs, nature, or item from final stats.
- Claim speed order based only on Spe unless speed rules, boosts, items, and field effects are connected.
- Claim KO/OHKO/2HKO.
- Treat default-profile estimates as high confidence.
- Say "final battle damage" while `is_final_battle_damage` is false.

## 13. Tests Plan

Future implementation tests:

- `stat_profiles.my_active` schema is emitted.
- `stat_profiles.opponent_active` schema is emitted.
- Six complete final stats produce `status: "user_confirmed_final_stats"`.
- Partial final stats are rejected or keep `default_assumption`.
- `damage_estimate.assumption_profile` changes when final stats are used.
- My move damage uses my attacker final stats and opponent defender final stats when present.
- Opponent known move damage uses opponent attacker final stats and my defender final stats when present.
- Default regression remains unchanged when no final stats are provided.
- `is_final_battle_damage` remains false.
- Contract guardrails include final stats limitations.

Expected test impact for minimal v0.14 implementation: 6-10 new or updated tests.

## 14. Out of Scope

Excluded from v0.14 design:

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

Because this is design-only, rollback is deleting this document commit.

For the future implementation:

1. Remove `stat_profiles` from the payload builder.
2. Revert the damage helper to default-only stats.
3. Keep existing v0.13 `assumption_profile` behavior.
4. Remove final-stats-specific tests.

## 16. T1/T2 Decisions Needed

- Confirm `stat_profiles` should be top-level in v0.14.
- Choose UI-B `StatProfileDialog` or UI-C collapsible section for implementation.
- Decide whether v0.14 should support both my and opponent final stats in the first implementation.
- Decide how to expose final stats editing for bench Pokemon, if at all.
- Decide whether suspicious stat-range warnings are needed in v0.14 or later.

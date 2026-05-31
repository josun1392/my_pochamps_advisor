# v0.53 Focus Sash Survival Design

## Current State

The current item/damage model is intentionally narrow:

- Type boosting item damage modifiers are implemented.
- `damage_estimate.item_effects.attacker_item` is the source of truth for attacker-side item damage modifiers.
- Choice Scarf effective Speed is modeled in `speed_context` only when the item is user-confirmed.
- Focus Sash is legal/selectable and represented in `item_profiles`, but survival is not connected.
- `damage_estimate` is still raw damage range and damage roll centered.
- `damage_estimate.is_final_battle_damage` remains `false`.
- KO/OHKO/2HKO judgment is not connected to advisor responses.
- Turn Engine state does not exist.

Relevant current payload facts:

- `pokemon.<side>.hp_percent` is available from the UI panel.
- `item_profiles.<side>.status` can be `user_confirmed`.
- `item_profiles.<side>.item_id` can be `focus-sash`.
- Damage estimates include `damage_range`, `percent_range`, and 16 raw damage `rolls`.

## Problem Definition

Focus Sash is not a damage reduction item. It does not reduce the incoming damage number; it changes the survival outcome under specific conditions.

If Focus Sash is mixed directly into the damage formula, the raw damage estimate becomes misleading. The app should still show the raw damage range as the damage that would be dealt without changing the formula.

At the same time, advice quality improves if the LLM can say that a Pokemon with a user-confirmed Focus Sash and full HP may survive a would-be KO at 1 HP.

Because the app has no Turn Engine, it cannot fully model:

- hit sequencing
- multi-hit moves
- entry hazards
- residual damage
- item consumption
- exact prior damage
- end-of-turn effects
- ability exceptions

Therefore Focus Sash should be represented only as **limited survival context**, separate from raw damage.

Core principle:

> Focus Sash context may affect survival wording, but it must not alter raw damage rolls.

## Scope

### Include in v0.54 Candidate

Focus Sash survival context may be available when all of these are true:

- Defender item profile has `status: user_confirmed`.
- Defender item id is `focus-sash`.
- Defender current HP is full or can be treated as full by current UI state.
- Incoming damage estimate is available.
- Incoming damage estimate has `damage_range` and/or `rolls`.
- Incoming damage can be lethal against the defender HP reference.
- The move is not known to be multi-hit.

When triggered, payload should state:

- Focus Sash may allow survival at 1 HP.
- The context is limited.
- Raw damage rolls were not changed.
- Final battle truth is not claimed.

### Exclude

- Multi-hit moves.
- Entry hazards.
- Residual damage.
- Weather chip.
- Status chip.
- Prior damage not reflected in current HP.
- Ability interactions.
- Item suppression.
- Mold Breaker-like exceptions.
- Exact turn sequence.
- Turn Engine.
- KO probability integration.
- Item consumption tracking.

## Data Requirements

Minimum inputs:

- defender side:
  - `my_active` or `opponent_active`
- defender item profile:
  - `status`
  - `item_id`
  - optional display name fields
- defender HP state:
  - exact current HP and max HP if ever available
  - otherwise `pokemon.<side>.hp_percent`
- damage estimate:
  - `status`
  - `damage_range.min`
  - `damage_range.max`
  - `rolls` when available
  - `percent_range.denominator`
- move metadata:
  - move id
  - move category
  - whether the move is multi-hit, if supported in future

Full HP policy:

- Prefer exact HP if both exact current HP and max HP exist:
  - full HP when `current_hp == max_hp`.
- Current v0.53-compatible fallback:
  - full HP when `pokemon.<side>.hp_percent == 100`.
- If neither exact HP nor HP percent can confirm full HP:
  - `available: false`
  - reason: `hp_unknown`

Lethal damage policy candidates:

- Conservative trigger:
  - `damage_range.min >= defender_current_hp`
  - means all rolls would be lethal without Focus Sash.
- Broader warning trigger:
  - `damage_range.max >= defender_current_hp`
  - means at least one roll may be lethal without Focus Sash.

T3 recommendation:

- v0.54 should expose both fields if possible:
  - `any_roll_would_be_lethal_without_item`
  - `all_rolls_would_be_lethal_without_item`
- `may_survive_at_1_hp` can be true when any roll is lethal, but wording should be more cautious unless all rolls are lethal.

## Proposed Payload Shape

Recommended placement:

- Add `survival_context` as an additive sibling next to a specific move's `damage_estimate`.
- Do not place it inside raw `damage_range`, `rolls`, or formula fields.
- Do not make it a top-level-only object in the first implementation, because selected move and opponent known move contexts have different defender sides.

### Available Example

```json
{
  "damage_estimate": {
    "status": "available_with_default_assumptions",
    "damage_range": {"min": 180, "max": 212},
    "rolls": [180, 183, 186],
    "is_final_battle_damage": false
  },
  "survival_context": {
    "available": true,
    "mode": "limited_item_survival_context_v0.54",
    "scope": "selected_move_only",
    "defender_side": "opponent_active",
    "item": {
      "item_id": "focus-sash",
      "status": "user_confirmed"
    },
    "current_hp_is_full": true,
    "incoming_damage": {
      "min": 180,
      "max": 212,
      "any_roll_would_be_lethal_without_item": true,
      "all_rolls_would_be_lethal_without_item": true
    },
    "survival_effect": {
      "type": "focus_sash",
      "may_survive_at_1_hp": true,
      "raw_damage_rolls_changed": false
    },
    "limitations": [
      "Limited context only.",
      "Multi-hit moves, hazards, residual damage, and turn sequencing are not modeled."
    ],
    "is_final_battle_truth": false
  }
}
```

### Unavailable Example

```json
{
  "survival_context": {
    "available": false,
    "mode": "limited_item_survival_context_v0.54",
    "scope": "selected_move_only",
    "defender_side": "opponent_active",
    "reason": "item_not_user_confirmed",
    "is_final_battle_truth": false,
    "raw_damage_rolls_changed": false,
    "limitations": [
      "Focus Sash survival context requires a user-confirmed Focus Sash."
    ]
  }
}
```

### Direction

My selected move:

- attacker: `my_active`
- defender: `opponent_active`
- attach survival context beside `moves.my_selected_move.damage_estimate`
- defender item comes from `item_profiles.opponent_active`
- defender HP comes from `pokemon.opponent_active.hp_percent`

Opponent known move:

- attacker: `opponent_active`
- defender: `my_active`
- attach survival context beside each `opponent_moves.known_moves[*].damage_estimate`
- defender item comes from `item_profiles.my_active`
- defender HP comes from `pokemon.my_active.hp_percent`

Available move comparison:

- v0.54 may choose to defer survival context on every `my_available_moves[*]` entry to avoid payload clutter.
- If included, it must follow the same sibling rule and no raw damage mutation.

## LLM Wording / Guardrails

Allowed wording:

- "Focus Sash may allow survival at 1 HP if the Pokemon is at full HP, but this is limited context and does not change the raw damage estimate."
- "Without considering Focus Sash, the damage range is lethal; with a user-confirmed Focus Sash and full HP, survival at 1 HP is possible under limited assumptions."
- "Focus Sash context is limited because multi-hit moves, hazards, residual damage, and turn sequencing are not modeled."

Forbidden wording:

- "Focus Sash reduces the damage."
- "The Pokemon definitely survives."
- "Focus Sash guarantees survival in this turn."
- "This is final battle damage."
- "Focus Sash applies even if the item is only possible or unknown."
- "Focus Sash handles multi-hit/hazards/residual damage."

Required guardrails:

- Use "may survive at 1 HP", not "will survive."
- State that raw damage is unchanged.
- State limited assumptions when relevant.
- Model Focus Sash only when the item is user-confirmed.
- Do not infer unconfirmed or unknown Focus Sash.
- Do not treat Focus Sash as damage reduction.
- Do not claim final turn order.
- Do not claim KO/OHKO/2HKO probability from Focus Sash context alone.

## Availability / Reason Codes

Recommended reason codes:

- `no_focus_sash`
  - defender item is user-confirmed but not Focus Sash, or no item.
- `item_not_user_confirmed`
  - item status is unknown, system default, none, or otherwise not user-confirmed.
- `hp_not_full`
  - defender HP is known and below full.
- `hp_unknown`
  - full HP cannot be established.
- `damage_not_lethal`
  - no damage roll reaches current HP.
- `multi_hit_not_supported`
  - move is known or marked as multi-hit.
- `damage_estimate_missing`
  - no usable damage estimate exists.
- `defender_max_hp_missing`
  - exact HP path requested but max HP unavailable.
- `unsupported_turn_engine_required`
  - the case needs sequencing that v0.54 does not model.

Reason codes should be machine-readable. User-facing text should remain short and guarded.

## Tests Plan

Future v0.54 tests should cover:

- user-confirmed Focus Sash + full HP + lethal damage:
  - `available: true`
  - `may_survive_at_1_hp: true`
  - raw damage unchanged
- user-confirmed Focus Sash + full HP + non-lethal damage:
  - `available: false` with `damage_not_lethal`, or available context with no survival trigger
- Focus Sash not user-confirmed:
  - `item_not_user_confirmed`
- no Focus Sash:
  - `no_focus_sash`
- HP not full:
  - `hp_not_full`
- HP unknown:
  - `hp_unknown`
- multi-hit move:
  - `multi_hit_not_supported`
- selected move direction:
  - defender side is `opponent_active`
- opponent known move direction:
  - defender side is `my_active`
- raw `damage_range` and `rolls` unchanged
- type boosting item damage modifier regression
- Choice Scarf `speed_context` regression
- opponent assumptions regression
- LLM prompt/contract guardrails:
  - may survive wording
  - no guaranteed survival
  - no damage reduction wording
  - no final battle truth

## Interaction With Existing Systems

### `item_effects`

`damage_estimate.item_effects` remains for damage formula effects. Focus Sash should not appear as an applied damage modifier.

Focus Sash survival context should reference the item profile separately and state that raw damage rolls are unchanged.

### Type Boosting Items

Type boosting items may still change damage estimates when attacker-side and applied. Focus Sash is defender-side survival context and should not conflict with attacker damage modifiers.

### Choice Scarf `speed_context`

Choice Scarf remains a Speed context feature. Focus Sash survival context does not affect effective Speed or final turn order.

### `opponent_assumptions`

Opponent assumptions remain context-only possible profiles. They must not provide Focus Sash truth. Focus Sash survival context requires user-confirmed item profile data.

### KO/OHKO/2HKO

Focus Sash survival context should not claim KO odds. KO/OHKO/2HKO integration is a later design. Future KO work must account for survival contexts to avoid overclaiming.

### Turn Engine

No Turn Engine is introduced. Sequencing-sensitive cases remain out of scope.

## v0.54 Candidate

Recommended:

`v0.54 - Focus Sash Limited Survival Context Implementation`

Implementation scope:

- Add helper for Focus Sash survival context.
- Attach additive `survival_context` beside selected move damage estimate and opponent known move damage estimates.
- Require user-confirmed Focus Sash.
- Require full HP by exact HP if available, otherwise `hp_percent == 100`.
- Trigger only when damage estimate is available and at least one roll is lethal.
- Keep raw damage unchanged.
- Add payload contract guardrails.
- Add tests.

Explicit exclusions:

- no Turn Engine
- no KO probability
- no multi-hit support
- no hazards/residual/weather/status chip
- no UI changes
- no formula changes

Key risks:

- HP percent is less precise than exact HP.
- A "may survive" sentence can still be interpreted too strongly unless wording is guarded.
- Multi-hit handling must be explicitly excluded until the move-hit model is available.

## Out of Scope

- Code implementation.
- Actual `survival_context` field addition.
- Item effect implementation.
- Damage formula changes.
- Raw damage roll changes.
- KO/OHKO/2HKO implementation.
- Turn Engine implementation.
- Multi-hit support.
- Hazard/residual/weather/status chip.
- UI changes.
- Fixture changes.
- Sample additions.
- Logs, `.env`, secrets, API keys, or handoff capsule commits.

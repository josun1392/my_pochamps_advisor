# v0.87 Type-resist Berry Limited Survival Context Design

## Current State

Focus Sash `survival_context` is implemented as additive limited context. It does not change raw damage rolls and does not claim final survival truth.

Sitrus Berry / Leftovers `recovery_context` is implemented as additive limited context. It does not change raw damage or `ko_context`.

KO/OHKO/2HKO `ko_context` is implemented from raw damage rolls and limited min/max context. It is not final battle truth.

The legal item gate uses `data/static/champions_legal_items.json` for user-facing modeled item contexts.

Type-resist berries are present in the Champions legal fixture and have repo-native metadata in `data/static/items_damage.json` under `type_resist_berries`.

There is no current type-resist berry survival or damage context.

## Problem Definition

Type-resist berries can reduce damage from a qualifying incoming hit of a specific type.

If berry reduction is mixed directly into the raw damage formula in the first pass, then raw damage rolls, OHKO chance, 2HKO context, and user-facing damage text can all change. That is a larger blast radius than the current limited item-context pattern.

Type-resist berry behavior can depend on:

- defender item status
- item legality
- incoming move type
- whether the hit is super-effective
- Chilan Berry's Normal-type special case
- item consumption / once-per-battle state
- multi-hit sequencing
- ability, weather, Tera, and other battle-state interactions
- Turn Engine timing

The safe first design is to keep raw damage rolls unchanged and expose an additive limited context that says a qualifying hit may be reduced under limited assumptions.

## Item Behavior Summary

Repo metadata source:

- `data/static/items_damage.json`
- key: `type_resist_berries`

Confirmed legal type-resist berry mappings:

| Item | Resisted type | Notes |
|---|---|---|
| `babiri-berry` | steel | super-effective Steel hit |
| `charti-berry` | rock | super-effective Rock hit |
| `chople-berry` | fighting | super-effective Fighting hit |
| `coba-berry` | flying | super-effective Flying hit |
| `colbur-berry` | dark | super-effective Dark hit |
| `haban-berry` | dragon | super-effective Dragon hit |
| `kasib-berry` | ghost | super-effective Ghost hit |
| `kebia-berry` | poison | super-effective Poison hit |
| `occa-berry` | fire | super-effective Fire hit |
| `passho-berry` | water | super-effective Water hit |
| `payapa-berry` | psychic | super-effective Psychic hit |
| `rindo-berry` | grass | super-effective Grass hit |
| `roseli-berry` | fairy | super-effective Fairy hit |
| `shuca-berry` | ground | super-effective Ground hit |
| `tanga-berry` | bug | super-effective Bug hit |
| `wacan-berry` | electric | super-effective Electric hit |
| `yache-berry` | ice | super-effective Ice hit |

Special case:

| Item | Resisted type | Notes |
|---|---|---|
| `chilan-berry` | normal | `items_damage.json` marks `always_resist=true`; this is not a super-effective trigger and should be excluded from the first implementation or handled separately. |

All 18 `type_resist_berries` entries in `items_damage.json` are present in `data/static/champions_legal_items.json`.

## Scope

### v0.88 Candidate Include

The first implementation candidate should:

- require defender item `status=user_confirmed`
- require the item to pass the Champions legal item gate
- use `items_damage.json` `type_resist_berries` as the item id -> resisted type mapping source
- require incoming move type to be known
- require type matchup metadata to show the incoming move is super-effective against the defender
- attach a move-level additive `resist_berry_context`
- keep raw damage rolls unchanged
- keep `ko_context` unchanged
- state that the berry may reduce a qualifying super-effective hit under limited assumptions
- keep Chilan Berry unavailable or deferred in the first implementation unless a separate explicit branch is designed

### Exclude

- raw damage formula modification
- berry-adjusted damage rolls
- berry-adjusted KO probability
- berry-adjusted OHKO/2HKO context
- item consumption tracking
- multi-hit / per-hit berry application
- ability, weather, Tera, item suppression, or move-specific interactions
- Turn Engine
- exact final survival truth

## Proposed Payload Shape

### Option A - Extend `survival_context`

Pros:

- Reuses the survival-related conceptual bucket already established by Focus Sash.
- May feel natural because resist berries can affect survival outcome.

Cons:

- Focus Sash and resist berries work differently.
- `survival_context` would need multiple modes and item-specific branches.
- It can become harder for the LLM to distinguish "may survive at 1 HP" from "may reduce a qualifying hit."

### Option B - Separate `resist_berry_context`

Pros:

- Keeps item semantics explicit.
- Avoids changing Focus Sash `survival_context`.
- Makes raw damage / `ko_context` separation clearer.
- Follows the recent pattern for `accuracy_context`, `critical_context`, `flinch_context`, and `multi_hit_context`.

Cons:

- Adds another move-level context type.
- Requires prompt/contract tests for a new context family.

Recommendation:

- Use Option B.
- Add `resist_berry_context` as a move-level sibling near `damage_estimate`, `ko_context`, and other item contexts.
- Do not put it inside `damage_estimate` or `ko_context`.

### Available Shape Candidate

```json
{
  "available": true,
  "mode": "limited_resist_berry_context",
  "scope": "selected_move_only",
  "defender_side": "my_active",
  "item": {
    "item_id": "yache-berry",
    "status": "user_confirmed",
    "legal_status": "legal_modeled"
  },
  "resist_effect": {
    "berry_type": "ice",
    "incoming_move_type": "ice",
    "requires_super_effective_hit": true,
    "super_effective_match": true,
    "effect_label": "may_reduce_qualifying_super_effective_hit",
    "formula_label": "resist_berry_limited_damage_reduction",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "berry_adjusted_damage_integrated": false,
    "berry_adjusted_ko_integrated": false,
    "item_consumption_tracked": false
  },
  "limitations": [
    "Limited resist berry context only.",
    "Raw damage and KO estimates do not include berry reduction.",
    "Item consumption, multi-hit handling, abilities, weather, Tera, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

### Unavailable Shape Candidate

```json
{
  "available": false,
  "reason": "move_not_super_effective",
  "mode": "limited_resist_berry_context",
  "scope": "selected_move_only",
  "defender_side": "my_active",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_resist_berry`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `incoming_move_type_missing`
- `berry_type_missing`
- `move_not_super_effective`
- `type_matchup_unknown`
- `chilan_berry_deferred`
- `resist_berry_engine_missing`

## Data / Mapping Policy

Use this source order:

1. `data/static/champions_legal_items.json`
   - legal gate for user-facing modeled context
2. `data/static/items_damage.json`
   - `type_resist_berries` item id -> resisted type mapping

Do not use:

- `items.json` as legal coverage
- description text parsing
- external web research in implementation

Mapping facts:

- `items_damage.json` has 18 `type_resist_berries`.
- All 18 are currently Champions legal.
- 17 are standard super-effective type-resist berries.
- `chilan-berry` has `always_resist=true` and should be deferred or separately handled.

Initial v0.88 scope recommendation:

- support the 17 standard super-effective type-resist berries
- defer `chilan-berry`
- return `chilan_berry_deferred` or `move_not_super_effective` for Chilan until explicit handling is designed

## LLM Guardrail

Required wording policy:

- `resist_berry_context` is limited context only.
- The berry may reduce a qualifying super-effective hit.
- Raw damage estimate is unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include berry reduction.
- Berry-adjusted damage is not calculated.
- Berry-adjusted KO probability is not calculated.
- Item consumption is not tracked.
- Do not say the Pokemon definitely survives.
- Do not infer a resist berry if the item is unknown or unconfirmed.
- Do not mention blocked or non-legal berries in advice.
- Chilan and edge cases are not modeled unless explicitly supported.

Good wording:

- "Yache Berry may reduce a qualifying Ice-type super-effective hit as limited context, but the raw damage and KO estimates do not include the berry reduction."
- "This is not a final survival prediction because item consumption and turn sequencing are not modeled."

Bad wording:

- "Yache Berry makes this always survive."
- "The KO chance already includes Yache Berry."
- "The damage range is reduced to X-Y."
- "The berry has already been consumed."

## Tests Plan

Future implementation tests should cover:

- legal user-confirmed `yache-berry` + Ice super-effective move -> `resist_berry_context.available=true`
- no berry -> unavailable
- unconfirmed berry -> `item_not_user_confirmed`
- blocked/non-legal item -> `blocked_by_legal_item_coverage`
- incoming move type missing -> unavailable
- move not super-effective -> unavailable
- Chilan Berry deferred behavior
- raw damage min/max/rolls unchanged
- `ko_context` unchanged
- OHKO chance unchanged
- `berry_adjusted_damage_integrated=false`
- `berry_adjusted_ko_integrated=false`
- `item_consumption_tracked=false`
- legal gate regression
- blocked item silence regression
- Focus Sash regression
- recovery regression
- full pytest

## Interaction With Existing Systems

### `resist_berry_context` and `survival_context`

Use separate contexts.

Focus Sash remains `survival_context` and keeps its 1 HP survival semantics.

Resist berries should use `resist_berry_context` because they may reduce a qualifying hit, not guarantee survival.

### `resist_berry_context` and `ko_context`

The first implementation should not modify `ko_context`.

The LLM should explicitly understand that raw KO/OHKO/2HKO estimates do not include berry reduction.

### `resist_berry_context` and `recovery_context`

Resist berries are not recovery items. Do not merge them into `recovery_context`.

### Item Slot Interactions

Focus Sash and a resist berry cannot normally occupy the same held item slot. Payload builders should not combine both item effects for one Pokemon from one item profile.

### Turn Engine

Before a Turn Engine exists, do not claim final survival, final item consumption, or final KO truth.

## Recommended v0.88 Path

Recommend:

### v0.88 Type-resist Berry Limited Context Implementation

Reason:

- Mapping is clear in `items_damage.json`.
- All mapped resist berries are present in the Champions legal fixture.
- No separate mapping fixture is needed for the initial pass.
- The implementation can be additive and keep raw damage / `ko_context` unchanged.

Implementation boundaries:

- implement `llm/advisor_resist_berry_context.py`
- attach move-level `resist_berry_context`
- use legal gate and `items_damage.json` mapping
- support 17 standard super-effective type-resist berries
- defer Chilan Berry
- do not change raw damage formula
- do not calculate berry-adjusted damage or KO odds

Alternative:

### v0.88 Resist Berry Mapping / Repository Design

Use this only if T1/T2 want a separate repository abstraction before any LLM context helper. Current metadata looks clear enough that this is optional.

## Out of Scope

This v0.87 design excludes:

- code implementation
- `resist_berry_context` implementation
- raw damage formula modification
- berry-adjusted damage rolls
- berry-adjusted KO probability
- item consumption tracking
- Turn Engine
- ability, weather, or Tera interaction
- legal fixture mutation
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

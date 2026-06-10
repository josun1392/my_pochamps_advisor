# v1.4 Chilan Berry Limited Normal-Resist Context Design

## Current State

The advisor already has `resist_berry_context` for 17 standard type-resist berries. That context is intentionally scoped to berries that reduce a qualifying super-effective hit of their resisted type.

`chilan-berry` is different:

- `data/static/champions_legal_items.json` marks it legal.
- `data/static/items_damage.json` includes it under `type_resist_berries`.
- Its metadata is:
  - `resist_type`: `normal`
  - `always_resist`: `true`
- The current `llm/advisor_resist_berry_context.py` detects `always_resist=true` and returns `available=false`, reason `chilan_berry_deferred`.
- Existing default advice payload filtering hides that deferred reason from normal Gemini advice.

The damage helper already has low-level berry behavior for Chilan Berry:

- `defender_berry_mod(get_item("chilan-berry"), "normal", False) == M_HALF`

This design is not a request to wire that modifier into raw damage rolls or KO context. It is only about whether a safe limited advice context can explain the Normal-type special case.

## Problem

Standard type-resist berries are easy to describe as "may reduce a qualifying super-effective hit." Chilan Berry does not fit that condition because Normal-type attacks are not normally super-effective.

If Chilan Berry is folded into the current `resist_berry_context` without explicit semantics, Gemini may:

- assume the same super-effective trigger applies
- describe Chilan as a generic type-resist berry
- imply all move types are reduced
- imply final damage rolls or KO odds already include Chilan Berry
- overstate survival from a Normal-type hit

The previous Chilan deferred work also showed that unavailable/deferred reasons can leak into natural language if the payload exposes them. Any future Chilan implementation should preserve the v1.0 default advice filtering rule: only available user-facing context is sent to Gemini default advice.

## Context Shape Options

### Option A - Extend `resist_berry_context`

This would keep one context family for all resist berries and add a branch where:

- `item_id=chilan-berry`
- `resist_type=normal`
- `always_resist=true`
- incoming move type is Normal
- no super-effective requirement exists

Pros:

- Reuses the existing item context registry key.
- Reuses existing mental model for resist berries.
- Keeps the number of context fields smaller.

Cons:

- The current `resist_berry_context` name and fields emphasize super-effective matching.
- Existing payload shape has fields such as `requires_super_effective_hit` and `super_effective_match`.
- Mixing Chilan into this shape invites confusing false fields or special-case exceptions.
- Gemini wording may blur "super-effective resist berry" and "Normal-type Chilan special case."

### Option B - Add `normal_resist_berry_context`

This would introduce a separate context for Normal-type damage reduction berries.

Pros:

- More generic than item-specific `chilan_berry_context`.
- Clear separation from super-effective resist berry logic.
- Could support future Normal-resist item variants if they ever exist.

Cons:

- Slightly abstract for a context that currently has only one item.
- The name may hide the important fact that this is specifically the Chilan Berry special case.

### Option C - Add `chilan_berry_context`

This would introduce an item-specific limited context.

Pros:

- Most explicit and least likely to be confused with standard type-resist berries.
- Lets the payload avoid super-effective terminology entirely.
- Makes Gemini guardrails direct and easy to test.
- Keeps the existing 17-standard-berry `resist_berry_context` unchanged.

Cons:

- Adds another context key.
- If future Normal-resist items exist, the name may be too narrow.

## Recommendation

Use **Option C: `chilan_berry_context`** for the first implementation.

Rationale:

- Chilan Berry is a single known special case with `always_resist=true`.
- The current `resist_berry_context` was deliberately designed around super-effective triggers.
- An item-specific context avoids overloading existing `resist_effect` fields.
- Default advice filtering can treat it like the other item contexts: include only when `available=true`.

If T1/T2 prefer a more generic name, `normal_resist_berry_context` is a reasonable alternative. This design recommends `chilan_berry_context` because it best communicates the limited scope.

## Available Conditions

`chilan_berry_context.available=true` should require:

- defender item profile is `status=user_confirmed`
- defender item id normalizes to `chilan-berry`
- item passes Champions legal fixture gate
- local metadata exists in `items_damage.json`
- item metadata has `resist_type=normal`
- item metadata has `always_resist=true`
- incoming move type is known
- incoming move type is `normal`
- incoming move is damaging
- a raw `damage_estimate` exists

The context should be move-level and should be attached only where existing damage estimates are attached:

- `moves.my_available_moves`
- `moves.my_selected_move`
- generated selected move fallback payloads
- `opponent_moves.known_moves`

Candidate moves should stay excluded.

## Non-Normal Move Handling

If the defender has user-confirmed Chilan Berry but the incoming move type is not Normal:

- enriched/debug payload may include `available=false`
- reason can be `move_type_not_normal`
- default Gemini advice payload must omit `chilan_berry_context`
- default Gemini advice must not mention Chilan Berry, a non-Normal mismatch, unavailable reason, `not modeled`, `not reflected`, `unsupported`, or `effect is not applied`

This follows the same payload filtering rule used for unavailable `resist_berry_context`, `type_boost_context`, `species_stat_item_context`, and other item contexts.

## Proposed Payload Shape

Available shape:

```json
{
  "available": true,
  "mode": "limited_chilan_berry_context",
  "scope": "selected_move_only",
  "defender_side": "my_active",
  "item": {
    "item_id": "chilan-berry",
    "status": "user_confirmed",
    "legal_status": "legal_modeled"
  },
  "normal_resist_effect": {
    "berry_type": "normal",
    "incoming_move_type": "normal",
    "requires_super_effective_hit": false,
    "always_resist": true,
    "effect_label": "may_reduce_normal_type_hit",
    "formula_label": "chilan_berry_limited_normal_damage_reduction",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false,
    "chilan_adjusted_damage_integrated": false,
    "chilan_adjusted_ko_integrated": false,
    "item_consumption_tracked": false
  },
  "limitations": [
    "Limited Chilan Berry context only.",
    "Raw damage and KO estimates do not include Chilan Berry reduction.",
    "Item consumption, multi-hit handling, abilities, weather, terrain, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "reason": "move_type_not_normal",
  "mode": "limited_chilan_berry_context",
  "scope": "selected_move_only",
  "defender_side": "my_active",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_chilan_berry`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `chilan_berry_metadata_missing`
- `incoming_move_type_missing`
- `move_type_not_normal`
- `move_not_damaging`
- `damage_estimate_missing`

## Data And Mapping Policy

Use repo-native metadata only:

1. `data/static/champions_legal_items.json`
   - legal gate for user-facing modeled context
2. `data/static/items_damage.json`
   - `type_resist_berries.chilan-berry`
   - `resist_type=normal`
   - `always_resist=true`

Do not use:

- description parsing
- `items.json` alone as legal coverage
- external web research

## Gemini Wording

Allowed wording:

- "Chilan Berry may reduce damage from a Normal-type move."
- "This is limited context and not integrated into final KO odds."
- "Do not treat this as guaranteed survival."
- "Raw damage rolls and KO context remain based on the current calculator."

Required separation:

- raw damage estimate is unchanged
- raw damage rolls are unchanged
- raw `ko_context` is unchanged
- KO/OHKO/2HKO estimates do not include Chilan Berry reduction
- Chilan-adjusted damage is not calculated
- Chilan-adjusted KO probability is not calculated
- final survival probability is not calculated
- item consumption is not tracked

Forbidden wording:

- "guaranteed survival"
- "confirmed live"
- "will survive because of Chilan Berry"
- "KO chance is reduced to X"
- "final damage is halved"
- "raw damage rolls already include Chilan Berry"
- "Chilan Berry applies to all move types"

If `chilan_berry_context.available=false`, default advice should stay quiet unless the user explicitly asks about Chilan Berry.

## Interaction With Existing Systems

### `chilan_berry_context` and `resist_berry_context`

Keep them separate.

`resist_berry_context` remains the 17-standard-berry context for super-effective type-resist berries.

`chilan_berry_context` handles only Chilan Berry's Normal-type special case.

### `chilan_berry_context` and `ko_context`

`ko_context` remains based on raw damage rolls from the current calculator. The initial Chilan context must not calculate Chilan-adjusted OHKO, 2HKO, or KO probability.

### `chilan_berry_context` and `survival_context`

Chilan Berry is not Focus Sash or Focus Band. Do not merge it into `survival_context`.

The context may be relevant to survival, but it should not claim final survival.

### `chilan_berry_context` and Item Consumption

Do not track berry consumption in the first implementation. Do not claim the berry is still available after earlier turns.

### Default Advice Filtering

Add `chilan_berry_context` to the item/advice context registry only if implemented.

Default advice payload policy:

- `available=true`: keep `chilan_berry_context`
- `available=false`: remove `chilan_berry_context`
- debug/enriched payload may retain reason
- hidden item profile and local item-effect scrub rules should prevent Chilan from leaking through other fields when unavailable

## Tests Plan For v1.5

Future implementation tests should cover:

- user-confirmed legal Chilan Berry + incoming Normal damaging move -> `chilan_berry_context.available=true`
- user-confirmed Chilan Berry + non-Normal damaging move -> `available=false`, hidden from default advice
- unconfirmed Chilan Berry -> hidden from default advice
- no Chilan Berry -> unavailable/debug-only
- blocked/non-legal item -> hidden from default advice
- incoming move type missing -> unavailable/debug-only
- non-damaging Normal move -> unavailable/debug-only
- raw damage min/max/rolls unchanged
- Q12 constants unchanged
- `ko_context` unchanged
- OHKO chance unchanged
- `chilan_adjusted_damage_integrated=false`
- `chilan_adjusted_ko_integrated=false`
- `item_consumption_tracked=false`
- unavailable reason absent from default advice payload string
- Chilan item name absent from default advice payload when unavailable
- existing standard `resist_berry_context` regression
- blocked item silence regression
- full pytest

## Recommended v1.5 Path

Recommend:

**v1.5 - Chilan Berry Limited Normal-Resist Context Implementation**

Implementation scope:

- add `llm/advisor_chilan_berry_context.py`
- add registry key `chilan_berry_context`
- attach move-level context next to existing damage estimate contexts
- support only `chilan-berry`
- require defender item `status=user_confirmed`
- require legal gate pass
- require incoming move type `normal`
- require damaging move
- keep default advice payload filtering: `available=true` only
- keep enriched/debug reason for unavailable cases

Boundaries:

- no Chilan-adjusted damage rolls
- no Chilan-adjusted KO/OHKO/2HKO
- no damage formula change
- no raw roll change
- no Q12 change
- no item consumption
- no Turn Engine
- no ability/weather/terrain interaction

Alternative:

Use `normal_resist_berry_context` if T1/T2 prefer a less item-specific field name. The implementation and guardrails should otherwise remain the same.

## Out Of Scope

This v1.4 design excludes:

- code implementation
- `chilan_berry_context` implementation
- Chilan-adjusted damage formula implementation
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` calculation changes
- final survival probability
- final KO probability
- item consumption
- Turn Engine
- ability/weather/terrain interaction
- legal fixture mutation
- fixture mutation
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

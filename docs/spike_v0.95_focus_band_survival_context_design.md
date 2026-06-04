# v0.95 Focus Band Survival Context Design

## Current State

- `llm/advisor_survival_context.py` currently models Focus Sash as a limited `survival_context`.
- Focus Sash is attached as an additive move-level context and does not change raw damage rolls or `ko_context`.
- The existing Focus Sash context is intentionally narrow:
  - defender item must be user-confirmed Focus Sash
  - defender must be at full HP
  - incoming raw damage must be potentially lethal
  - multi-hit handling is not modeled
  - Turn Engine and item consumption are not modeled
- `docs/advisor_payload_contract.md` already treats `survival_context` as limited context, not final battle truth.
- v0.92/v0.93 introduced default advice payload filtering:
  - `available=true` contexts can be shown to Gemini default advice
  - `available=false` item contexts are hidden from default advice
  - enriched/debug payloads may keep unavailable reasons
- `data/static/champions_legal_items.json` contains `focus-band`:
  - `legal=true`
  - `category=hold_item`
  - `effect_support_status=legal_but_not_modeled`
  - `ui_status=recognized_not_modeled`
  - `effect_support.survival=not_supported`
- `data/static/items_damage.json` does not provide Focus Band damage metadata, which is expected because Focus Band is not a damage modifier.

## Focus Sash vs Focus Band

Focus Sash:
- Full HP condition.
- Relevant only when the raw incoming hit can be lethal.
- Limited effect wording: may survive at 1 HP.
- Existing implementation does not change raw damage rolls, `ko_context`, or final outcome truth.

Focus Band:
- No full HP condition in the same sense as Focus Sash.
- Can occasionally let the holder endure an otherwise lethal hit.
- Its activation is probabilistic, so it must not be described as guaranteed survival.
- The exact activation probability, final survival probability, and turn outcome are not modeled.
- It should not change raw damage rolls, `ko_context`, OHKO/2HKO estimates, or damage formula.

Design implication:
- Focus Band belongs near survival advice, but it needs stronger probability and certainty guardrails than Focus Sash.
- The LLM must never collapse "may occasionally survive" into "will survive".

## Problem Definition

Focus Band is a legal Champions item, but modeling it as actual battle truth would require mechanics the advisor does not currently own:

- final activation probability
- multi-hit handling
- item activation timing
- exact current HP interpretation
- ability, weather, status, and other turn interactions
- final turn sequencing

If Focus Band were mixed into raw damage or `ko_context`, the payload would imply the KO/OHKO/2HKO estimates already include Focus Band survival chance. That would be misleading. The initial implementation should instead expose a limited survival note only when the incoming hit appears potentially lethal.

## Placement Options

### Option A - Extend `survival_context`

Example:
- `survival_context.survival_effect.type = "focus_band"`
- Keep Focus Sash and Focus Band as sibling variants under one survival context family.

Pros:
- Reuses the existing move-level survival context surface.
- Keeps survival-related item effects in one familiar field.
- Avoids adding another top-level context type.
- Existing default advice filtering already applies to `survival_context`.

Cons:
- Focus Sash and Focus Band have different certainty profiles.
- Tests and wording must prevent Focus Band from inheriting Focus Sash-like certainty.

### Option B - Add separate `focus_band_context`

Pros:
- Keeps the probabilistic Focus Band effect clearly separate.
- Reduces risk that Focus Sash-specific wording leaks into Focus Band advice.

Cons:
- Adds another item-specific context field.
- Duplicates filtering and contract rules already present for survival context.
- Makes future survival-item handling more fragmented.

## Recommendation

Use Option A for v0.96: extend the existing additive `survival_context`, but make Focus Band a distinct `survival_effect.type`.

Recommended implementation direction:
- Keep `survival_context` as a move-level sibling.
- Add Focus Band as `survival_effect.type = "focus_band"`.
- Include explicit flags:
  - `activation_probability_calculated=false`
  - `final_survival_probability_integrated=false`
  - `raw_damage_rolls_changed=false`
  - `ko_context_changed=false`
- Preserve v0.92/v0.93 filtering:
  - `available=true` Focus Band context can be included in default advice payload
  - `available=false` Focus Band reasons stay debug/enriched only

If local Gemini verification later confuses Focus Band with Focus Sash, split to `focus_band_context` in a follow-up.

## Proposed Payload Shape

Available Focus Band context candidate:

```json
{
  "available": true,
  "mode": "limited_item_survival_context",
  "scope": "selected_move_only",
  "defender_side": "opponent_active",
  "item": {
    "item_id": "focus-band",
    "status": "user_confirmed",
    "legal_status": "legal_modeled"
  },
  "incoming_damage": {
    "min": 180,
    "max": 212,
    "percent_min": 98.3,
    "percent_max": 115.8,
    "could_be_lethal_without_item": true,
    "guaranteed_lethal_without_item": false,
    "hp_reference_source": "damage_percent_range"
  },
  "survival_effect": {
    "type": "focus_band",
    "effect_label": "may_occasionally_survive_lethal_hit",
    "formula_label": "focus_band_limited_survival_context",
    "survival_is_not_guaranteed": true,
    "activation_probability_calculated": false,
    "final_survival_probability_integrated": false,
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false
  },
  "limitations": [
    "Limited Focus Band survival context only.",
    "Raw damage and KO estimates do not include Focus Band activation.",
    "Activation probability, item consumption, multi-hit handling, abilities, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable Focus Band context candidate:

```json
{
  "available": false,
  "reason": "damage_not_lethal",
  "mode": "limited_item_survival_context",
  "is_final_battle_truth": false
}
```

Unavailable reasons to consider:

- `no_survival_item`
- `item_not_user_confirmed`
- `blocked_by_legal_item_coverage`
- `unsupported_survival_item`
- `damage_estimate_missing`
- `defender_hp_reference_missing`
- `damage_not_lethal`
- `multi_hit_not_supported`
- `activation_probability_not_modeled`

Default advice payload rule:
- hide unavailable Focus Band context and reason by default.
- keep the reason only in enriched/debug payload.

## Eligibility Policy

For v0.96, Focus Band should be available only when all are true:

- defender item is `focus-band`
- defender item status is `user_confirmed`
- item passes Champions legal gate
- incoming raw damage estimate exists
- incoming raw damage appears potentially lethal without the item

Potential lethal detection options:

- Prefer exact current HP if the payload has reliable current HP.
- If exact HP is not available, use raw damage percent range against visible HP percent:
  - `damage_estimate.percent_range.max >= defender_hp_percent`
  - include `hp_reference_source="damage_percent_range"` or similar
- If neither exact HP nor usable HP percent is available, return unavailable reason `defender_hp_reference_missing`.

Do not require full HP for Focus Band.

Do not calculate the Focus Band activation probability.

Do not calculate Focus Band-adjusted KO probability.

## LLM Guardrails

Allowed wording:

- "Focus Band may occasionally let it survive an otherwise lethal hit."
- "Survival is not guaranteed."
- "Raw damage and KO estimates do not include Focus Band activation."
- "This is limited survival context, not final battle truth."

Forbidden wording:

- "will survive"
- "guaranteed survive"
- "cannot be KO'd"
- "confirmed survival"
- "guarantees living at 1 HP"
- "KO chance includes Focus Band"
- "Focus Band reduces the damage range"
- "final survival probability is X%"

Concision rule:
- Mention Focus Band only when `survival_context.available=true`.
- Keep the Focus Band caveat to one short sentence unless the user explicitly asks about it.
- Do not mention unavailable Focus Band reasons in default advice.

## Interaction With Existing Systems

`damage_estimate`:
- Remains raw and unchanged.
- Focus Band does not modify min/max/rolls.

`ko_context`:
- Remains raw damage-roll KO context.
- OHKO/2HKO estimates do not include Focus Band activation.

Focus Sash:
- Remains supported by `survival_context`.
- Full HP Focus Sash logic should not be weakened.
- Existing Focus Sash regression tests must remain unchanged.

Default advice payload filtering:
- Available Focus Band context may be included.
- Unavailable Focus Band context must be hidden from default advice payload.
- Enriched/debug payload may retain unavailable reason codes.

## Tests Plan

Future v0.96 implementation tests:

- user-confirmed legal Focus Band + potentially lethal incoming hit -> `survival_context.available=true`
- Focus Band context includes `survival_effect.type="focus_band"`
- Focus Band context includes `activation_probability_calculated=false`
- Focus Band context includes `final_survival_probability_integrated=false`
- Focus Band context includes `raw_damage_rolls_changed=false`
- Focus Band context includes `ko_context_changed=false`
- Focus Band unavailable reason hidden from default advice payload
- Focus Band unavailable reason preserved in enriched/debug payload
- unconfirmed Focus Band -> unavailable/debug reason only
- no Focus Band -> unavailable/debug reason only or absent
- non-lethal incoming damage -> unavailable/debug reason only
- raw damage min/max/rolls unchanged
- `ko_context` unchanged
- OHKO/2HKO estimates unchanged
- Focus Sash regression maintained
- recovery context regression maintained
- legal item gate regression maintained
- blocked/unavailable item silence regression maintained
- prompt/contract forbids guaranteed survival wording
- full pytest

## Proposed v0.96 Scope

Recommended next step:

`v0.96 - Focus Band Limited Survival Context Implementation`

Include:
- extend `survival_context` for Focus Band
- user-confirmed Focus Band only
- Champions legal gate required
- potentially lethal raw incoming damage only
- no full HP requirement
- no activation probability calculation
- no final survival probability
- no raw damage changes
- no `ko_context` changes
- default advice payload hides unavailable reasons
- docs and tests

Implementation note:
- Prefer introducing a generic `build_survival_context()` while keeping Focus Sash behavior intact.
- Keep or wrap the existing `build_focus_sash_survival_context()` if tests or call sites depend on the name.

Follow-up:
- `v0.96.1 - Focus Band Local Gemini Verification`

## Out of Scope

- code implementation
- damage formula changes
- raw damage roll changes
- `ko_context` calculation changes
- KO chance integration with Focus Band
- final survival probability calculation
- exact Focus Band activation probability
- Turn Engine
- item consumption
- multi-hit Focus Band handling
- ability/weather/status/Tera interaction
- legal fixture changes
- fixture changes
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

## T1/T2 Decision Points

- Approve extending `survival_context` for Focus Band instead of adding `focus_band_context`.
- Confirm v0.96 should implement Focus Band as limited context only.
- Confirm raw damage rolls and `ko_context` remain unchanged.
- Confirm Focus Band activation probability remains uncalculated.
- Confirm unavailable Focus Band reasons stay hidden from default advice payload.

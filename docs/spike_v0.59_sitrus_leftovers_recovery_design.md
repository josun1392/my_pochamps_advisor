# v0.59 Sitrus / Leftovers Recovery Design

## Current State

The advisor now has several additive battle-context layers:

- `damage_estimate` provides raw damage min/max/rolls under stated assumptions.
- Type boosting item damage modifiers are applied only through `damage_estimate.item_effects`.
- Focus Sash has a limited additive `survival_context`.
- KO/OHKO/2HKO has a limited additive `ko_context`.
- Choice Scarf has a separate `speed_context`.
- `opponent_assumptions` remains context-only and does not feed damage, Speed, survival, or KO calculation.

Sitrus Berry and Leftovers are currently legal/selectable item candidates, but their recovery effects are not modeled:

- `data/static/champions_legal_items.json` marks both as legal.
- Their `effect_support.recovery` value is currently `not_supported`.
- Existing contract docs say Leftovers/Sitrus recovery and turn sequencing are not modeled.
- Turn Engine state does not exist.
- Recovery, hazards, chip damage, weather/status residual damage, switching, protection, and item consumption tracking are not connected.

## Problem Definition

Sitrus Berry and Leftovers can change real KO and 2HKO decisions. The hard part is that recovery is timing-sensitive:

- Sitrus Berry depends on HP thresholds, activation timing, and whether it has already been consumed.
- Leftovers usually heals at end of turn, which depends on turn order and end-of-turn sequencing.
- Recovery can interact with Focus Sash, hazards, weather/status chip, protection, switching, and repeated turns.

If recovery is mixed directly into raw damage or `ko_context`, the advisor can overstate the result as final battle truth. The safer path is a separate limited `recovery_context` that tells the LLM recovery may matter without changing raw damage rolls or raw KO context.

## Item Behavior

### Sitrus Berry

Sitrus Berry is generally a threshold-triggered recovery item. In modern games it commonly restores a portion of max HP after the holder drops to a low enough HP threshold.

Design stance:

- Treat Sitrus as **candidate recovery context** first.
- Require `user_confirmed` item state before modeling.
- Do not claim exact activation unless the required HP and damage state are available.
- Do not track item consumption in the first implementation.
- Keep the exact rule source and Champions/PoChamps rule confirmation as an explicit implementation checkpoint.

### Leftovers

Leftovers generally restores a portion of max HP at end of turn.

Design stance:

- Treat Leftovers as **limited end-of-turn recovery context**.
- Require `user_confirmed` item state before modeling.
- Do not fold Leftovers into current-hit OHKO chance.
- Do not use it to claim exact 2HKO or 3HKO truth without Turn Engine state.
- Do not simulate repeated turns in the first implementation.

## Scope

Recommended v0.60 scope:

- user-confirmed `sitrus-berry` and `leftovers` only
- defender max HP required for recovery amount
- additive `recovery_context`
- no mutation of `damage_estimate.damage_range`
- no mutation of `damage_estimate.rolls`
- no mutation of `ko_context`
- LLM may say recovery can affect follow-up KO/2HKO under limited assumptions

Out of first implementation scope:

- exact Turn Engine
- exact activation sequencing
- hazards, chip, weather/status residual, and other end-of-turn ordering
- Protect and switching
- Sitrus item consumption tracking
- "already consumed" state
- repeated-turn Leftovers simulation
- Focus Sash plus recovery interactions
- recovery folded into OHKO/2HKO probability

## Proposed Payload Shape

Recommended common wrapper:

```json
{
  "available": true,
  "mode": "limited_item_recovery_context",
  "scope": "selected_move_only",
  "defender_side": "opponent_active",
  "item": {
    "item_id": "sitrus-berry",
    "status": "user_confirmed"
  },
  "recovery_effect": {
    "type": "sitrus_berry",
    "timing": "threshold_or_after_damage_limited",
    "estimated_recovery_hp": 45,
    "recovery_amount_source": "max_hp_fraction_limited",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false
  },
  "limitations": [
    "Limited recovery context only.",
    "Exact activation timing, item consumption, switching, residual damage, and turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Leftovers example:

```json
{
  "available": true,
  "mode": "limited_item_recovery_context",
  "scope": "opponent_known_move_only",
  "defender_side": "my_active",
  "item": {
    "item_id": "leftovers",
    "status": "user_confirmed"
  },
  "recovery_effect": {
    "type": "leftovers",
    "timing": "end_of_turn_limited",
    "estimated_recovery_hp": 11,
    "recovery_amount_source": "max_hp_fraction_limited",
    "raw_damage_rolls_changed": false,
    "ko_context_changed": false
  },
  "limitations": [
    "Limited end-of-turn recovery context only.",
    "Turn order, switching, protection, residual damage, and exact turn sequencing are not modeled."
  ],
  "is_final_battle_truth": false
}
```

Unavailable shape:

```json
{
  "available": false,
  "mode": "limited_item_recovery_context",
  "reason": "no_recovery_item",
  "is_final_battle_truth": false
}
```

Reason code candidates:

- `no_recovery_item`
- `item_not_user_confirmed`
- `defender_max_hp_missing`
- `unsupported_recovery_item`
- `damage_estimate_missing`
- `activation_timing_unknown`
- `turn_engine_required`
- `item_consumption_not_tracked`

## Placement Options

### Option A - `damage_estimate` sibling

Add `recovery_context` beside `damage_estimate`, `ko_context`, and `survival_context` on each move.

Pros:

- Easy for the LLM to interpret next to the relevant damage and KO fields.
- Matches `survival_context` and `ko_context` placement.
- Works for both my selected/available moves and opponent known moves.

Cons:

- Leftovers is end-of-turn context, so attaching it to a single hit can feel less exact than Focus Sash or KO context.
- Repeated move entries may duplicate the same Leftovers note.

### Option B - top-level item recovery context

Add a top-level `item_recovery_context` keyed by side.

Pros:

- Keeps recovery clearly item/state based.
- Avoids repeating Leftovers on every move.
- More natural for end-of-turn effects.

Cons:

- Harder for the LLM to connect to a specific damage/KO estimate.
- Less consistent with existing additive move-side contexts.

### Option C - insert recovery notes inside `ko_context`

Add recovery notes directly in `ko_context`.

Pros:

- Directly adjacent to 2HKO claims.

Cons:

- Risks contaminating raw damage-roll KO semantics.
- Makes it easier to imply recovery is included in KO probability.
- Conflicts with v0.56/v0.57 policy that `ko_context` is raw damage-roll context only.

Recommendation:

- Prefer **Option A** for v0.60 because it matches existing `survival_context`/`ko_context` patterns and keeps the field additive.
- For Leftovers, keep the field beside the relevant damage estimate but make timing explicit as `end_of_turn_limited`.
- Do not use Option C.
- Consider a later top-level summary if repeated Leftovers notes become noisy.

## Recovery Amount Policy

Implementation should not silently guess item rules.

Suggested initial policy:

- Require defender max HP.
- If max HP is missing, return unavailable with `defender_max_hp_missing`.
- Use explicit formula labels:
  - Sitrus Berry: `max_hp_fraction_limited`
  - Leftovers: `max_hp_fraction_limited`
- Store both:
  - `estimated_recovery_hp`
  - `recovery_amount_source`
- Add `rule_verification_status` if needed:
  - `needs_champions_rule_confirmation`
  - `standard_game_rule_assumed`

Open rule checks before implementation:

- Confirm the exact Sitrus Berry threshold and fraction for the target ruleset.
- Confirm Leftovers fraction and rounding.
- Decide whether floor/rounding should be handled by a helper or documented as approximate.

If rule certainty is insufficient in v0.60, use `formula_label` and a limitation instead of a numeric `estimated_recovery_hp`.

## LLM Guardrails

Required guardrails:

- `recovery_context` is limited context only.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- Recovery is not fully simulated.
- Do not claim final 2HKO/3HKO truth without Turn Engine.
- Do not assume item activation if the item is unknown or unconfirmed.
- Sitrus/Leftovers timing is not fully modeled.
- Item consumption is not tracked.
- Use wording like "may affect follow-up KO/2HKO under limited assumptions."

Good wording:

- "Leftovers may affect follow-up damage ranges, but exact end-of-turn recovery and sequencing are not modeled."
- "Sitrus Berry recovery is shown as limited context only and does not change the raw damage or KO estimate."
- "The raw 2HKO estimate does not include recovery; Sitrus/Leftovers may matter under limited assumptions."

Bad wording:

- "This always becomes a 3HKO after Leftovers."
- "Sitrus definitely activates here."
- "The KO chance already includes recovery."
- "Leftovers has been fully simulated."
- "Recovery changes the raw damage rolls."

## Tests Plan

Future implementation tests should cover:

- user-confirmed Sitrus Berry plus max HP -> `recovery_context.available=true`
- user-confirmed Leftovers plus max HP -> `recovery_context.available=true`
- unknown item -> unavailable or absent without inventing recovery
- no recovery item -> unavailable `no_recovery_item`
- max HP missing -> unavailable `defender_max_hp_missing`
- raw damage min/max/rolls unchanged
- `ko_context` unchanged
- `recovery_context` does not alter OHKO chance
- my selected/available move direction
- opponent known move direction
- candidate moves excluded or explicitly documented
- prompt guardrails
- existing Focus Sash regression
- existing KO context regression
- existing type item regression
- existing Choice Scarf speed context regression
- existing opponent assumptions regression
- full pytest

## Interaction With Existing Systems

`recovery_context` and `ko_context`:

- `ko_context` remains raw damage-roll context.
- Recovery is not folded into OHKO chance.
- The LLM may contrast raw KO context with possible recovery limitations.

`recovery_context` and `survival_context`:

- Focus Sash remains separate.
- Sitrus/Leftovers plus Focus Sash interactions should be deferred.
- Do not imply Focus Sash survival plus recovery has been sequenced.

Item system:

- Legal item selection and local effect modeling remain separate.
- `champions_legal_items.json` currently marks both items legal but recovery unsupported.
- v0.60 would move the local support story forward without changing item legality.

Other contexts:

- `speed_context` is unrelated.
- `opponent_assumptions` is unrelated and remains context-only.
- Turn Engine remains absent.

## v0.60 Candidate

Recommended:

`v0.60 - Sitrus / Leftovers Limited Recovery Context Implementation`

Include:

- helper for limited recovery context
- user-confirmed Sitrus/Leftovers only
- max HP based recovery amount or formula label
- additive `recovery_context`
- raw damage and raw `ko_context` unchanged
- tests and docs
- no Turn Engine
- no item consumption tracking

Alternative:

`v0.60 - Recovery Item Rule Validation Design`

Choose this if T1/T2 want rule-source certainty before implementation, especially for Sitrus threshold, recovery fraction, and rounding.

T3 recommendation:

- Proceed with implementation only if T1/T2 approve the exact recovery amount policy.
- If rule details are still uncertain, run the validation design first.
- In either path, keep recovery separate from raw damage and raw KO context.

## Out of Scope

- code implementation
- `recovery_context` implementation
- Turn Engine
- item consumption tracking
- exact 2HKO/3HKO simulation
- KO context modification
- raw damage roll modification
- Focus Sash interaction implementation
- UI changes
- fixture changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

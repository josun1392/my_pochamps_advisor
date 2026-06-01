# v0.56 KO / OHKO / 2HKO Probability Design

## Current State

The advisor payload already contains enough raw damage information to support a limited KO context:

- `damage_estimate` includes `damage_range.min`, `damage_range.max`, and 16 raw `rolls` when the move can be calculated.
- `damage_estimate.is_final_battle_damage` remains `false`.
- Type boosting item damage modifiers are implemented when `damage_estimate.item_effects.attacker_item.status` is `applied`.
- Focus Sash is represented separately as additive `survival_context` beside relevant `damage_estimate` entries.
- Focus Sash does not change raw damage min/max/rolls.
- Choice Scarf effective Speed is represented separately in `speed_context`.
- `opponent_assumptions` remains `context_only` and does not feed damage or Speed calculation.
- `advisor.damage.rolls.calc_ko_chance()` exists and can classify OHKO/2HKO outcomes over damage rolls, but that logic is not connected to the LLM payload.
- KO/OHKO/2HKO advice is still blocked by payload and prompt guardrails.
- Turn Engine, recovery, chip, hazards, weather/status damage, move accuracy, and future turn sequencing are not connected.

## Problem Definition

Damage ranges are useful but incomplete. A player usually wants to know:

- whether a move can KO from the current HP
- whether it is a guaranteed OHKO
- whether it is a possible or guaranteed 2HKO
- how many damage rolls succeed

However, a full battle-accurate KO answer depends on many systems that are intentionally out of scope:

- accuracy and miss chance
- priority and final action order
- Speed and turn sequencing
- Focus Sash survival behavior
- healing and recovery
- hazards, residual damage, weather chip, and status chip
- Protect, Substitute, switching, and multi-turn decisions
- multi-hit move distributions

Therefore v0.56 should design **limited damage-roll KO context**, not final battle truth.

## KO Context Scope

### Include

The first implementation should support:

- current HP based OHKO context when exact current HP is available or safely derived
- max HP / full HP OHKO context when only max HP/full HP reference is available
- roll-count based OHKO chance for one hit
- `successful_rolls / total_rolls` metadata
- guaranteed OHKO when all rolls meet or exceed target HP
- possible OHKO when some rolls meet or exceed target HP
- limited 2HKO classification using min/max arithmetic
- coexistence with Focus Sash `survival_context`
- explicit `raw_damage_rolls_changed=false`

### Exclude

The first implementation must not include:

- Turn Engine
- move accuracy
- priority
- final Speed order
- healing/recovery
- hazards
- chip/residual/weather/status damage
- multi-hit support
- Protect
- Substitute
- switching
- exact future turn simulation
- Focus Sash adjustment inside KO probability

## Proposed Payload Shape

Recommended placement:

- Add `ko_context` as an additive sibling beside the same move's `damage_estimate`.
- Do not put KO fields inside `damage_range` or raw roll data.
- Do not make it top-level only, because selected moves and opponent known moves have different attacker/defender directions.

Example:

```json
{
  "damage_estimate": {
    "status": "available_with_default_assumptions",
    "damage_range": {"min": 180, "max": 212},
    "rolls": [180, 183, 186, 189],
    "is_final_battle_damage": false
  },
  "ko_context": {
    "available": true,
    "mode": "limited_damage_roll_ko_context",
    "target_hp": {
      "current_hp": 183,
      "max_hp": 183,
      "hp_percent": 100,
      "source": "user_confirmed_or_payload_reference"
    },
    "damage": {
      "min": 180,
      "max": 212,
      "roll_count": 16
    },
    "ohko": {
      "possible": true,
      "guaranteed": false,
      "chance": 0.375,
      "successful_rolls": 6,
      "total_rolls": 16
    },
    "two_hko": {
      "possible": true,
      "guaranteed": true,
      "method": "min_max_limited",
      "assumptions": [
        "Same move used twice.",
        "No healing, recovery, chip damage, protection, switching, item survival effects, or turn sequencing changes are modeled."
      ]
    },
    "raw_damage_rolls_changed": false,
    "is_final_battle_truth": false,
    "limitations": [
      "Limited damage-roll context only.",
      "Accuracy, speed order, priority, recovery, hazards, chip damage, switching, and turn sequencing are not modeled."
    ]
  }
}
```

Unavailable example:

```json
{
  "available": false,
  "mode": "limited_damage_roll_ko_context",
  "reason": "target_hp_unknown",
  "raw_damage_rolls_changed": false,
  "is_final_battle_truth": false
}
```

Candidate moves should remain excluded unless they already receive a deterministic `damage_estimate` in a future version.

## OHKO Logic

If exact or payload-derived `current_hp` is available:

- Count every roll where `roll >= current_hp`.
- `successful_rolls == total_rolls` means guaranteed OHKO under limited assumptions.
- `0 < successful_rolls < total_rolls` means possible OHKO with chance `successful_rolls / total_rolls`.
- `successful_rolls == 0` means no OHKO from current HP under raw rolls.

Min/max shortcuts:

- `min_damage >= current_hp`:
  - `ohko.guaranteed=true`
  - `ohko.possible=true`
  - chance `1.0`
- `max_damage < current_hp`:
  - `ohko.guaranteed=false`
  - `ohko.possible=false`
  - chance `0.0`
- `min_damage < current_hp <= max_damage`:
  - `ohko.guaranteed=false`
  - `ohko.possible=true`
  - chance should be roll-count based if rolls exist

If exact current HP is not available:

- If `hp_percent == 100` and max HP reference is available, use max HP as the target and mark the HP source as full HP reference.
- If only a non-100 percent is available without exact HP, either:
  - return unavailable with `target_hp_unknown`, or
  - use a clearly marked approximate mode in a later version.

v0.57 should prefer unavailable over approximate non-exact HP.

If roll list is missing:

- Use min/max-only limited mode.
- Do not invent a fractional chance.
- Report `chance=null` or omit chance while preserving possible/guaranteed booleans.

## 2HKO Logic

The first version should avoid pairwise roll probability unless T1/T2 explicitly approve it.

Recommended limited rules:

- `min_damage * 2 >= current_hp`:
  - guaranteed 2HKO under limited assumptions
- `max_damage * 2 >= current_hp`:
  - possible 2HKO under limited assumptions
- `max_damage * 2 < current_hp`:
  - no 2HKO under limited assumptions

The assumptions must be explicit:

- same move used twice
- no healing or recovery
- no hazards/chip/residual changes
- no Protect/Substitute/switching
- no miss chance
- no turn order simulation
- no item survival integration unless separately represented

Roll-pair probability can be a later enhancement. Although `advisor.damage.rolls.calc_ko_chance()` already computes pairwise 2HKO chance, exposing that in the LLM payload should wait until wording and Focus Sash/recovery guardrails are stable.

## Focus Sash Interaction

Focus Sash `survival_context` and `ko_context` should coexist but remain separate.

Principles:

- KO context is computed from raw damage rolls.
- Focus Sash must not alter raw damage rolls.
- Focus Sash should not be folded into OHKO chance in v0.57.
- The LLM can say: "Raw damage could KO, but a user-confirmed Focus Sash may allow survival at 1 HP under limited assumptions."
- The LLM must not say Focus Sash is included in the KO probability.
- If `survival_context.available=true`, KO wording should be softened.

Example response shape:

> The raw rolls have a 6/16 chance to KO from current HP, but this is limited damage-roll context. The user-confirmed Focus Sash may allow survival at 1 HP, and accuracy, recovery, chip damage, and turn sequencing are not modeled.

## LLM Guardrails

Required wording constraints:

- Say "limited damage-roll context."
- Say it is not final battle truth.
- Say raw damage rolls are unchanged.
- Say accuracy, speed order, priority, recovery, hazards, chip damage, switching, and turn sequencing are not modeled.
- Say Focus Sash survival context may alter the outcome, but raw KO context is separate.
- Do not overstate 2HKO as a final turn simulation.
- Do not claim the opponent cannot survive if Focus Sash or other survival/recovery context is present.

Good wording:

- "The raw damage rolls have a 6/16 chance to KO from the current HP, but this does not include accuracy, recovery, turn order, or Focus Sash survival context."
- "This is a limited 2HKO estimate assuming the same move is used twice with no healing, switching, or chip changes."
- "Raw damage could KO, but Focus Sash may allow survival at 1 HP under limited assumptions."

Bad wording:

- "This guarantees the KO in battle."
- "This will always 2HKO."
- "The opponent cannot survive."
- "Focus Sash is included in the KO probability."
- "Accuracy and turn order are already accounted for."

## Tests Plan

Future implementation tests should cover:

- `min >= current_hp` gives guaranteed OHKO.
- `max < current_hp` gives no OHKO.
- partial rolls above HP give `successful_rolls / total_rolls` chance.
- `roll_count` is preserved.
- raw damage rolls are unchanged.
- guaranteed 2HKO when `min_damage * 2 >= hp`.
- possible 2HKO when `max_damage * 2 >= hp`.
- impossible 2HKO when `max_damage * 2 < hp`.
- HP unknown returns unavailable.
- no rolls falls back to min/max limited mode without inventing roll chance.
- Focus Sash `survival_context` can coexist with `ko_context`.
- Focus Sash is not included in KO probability.
- candidate moves do not receive `ko_context`.
- my selected/available move direction targets `opponent_active`.
- opponent known move direction targets `my_active`.
- prompt/contract forbids final battle truth and overclaiming.
- existing Focus Sash regression remains.
- existing type boosting item regression remains.
- existing Choice Scarf `speed_context` regression remains.
- existing `opponent_assumptions` regression remains.

## Roadmap

Recommended:

1. `v0.57 - KO/OHKO/2HKO Limited Context Implementation`
2. `v0.58 - KO Context Local Gemini Verification`
3. `v0.59 - Sitrus/Leftovers Recovery Design`
4. `v0.60 - Bright Powder Accuracy Design`

v0.57 should start with additive `ko_context` beside relevant `damage_estimate` entries, roll-based OHKO chance, and min/max 2HKO classification. It should not integrate recovery, Focus Sash probability, accuracy, or Turn Engine state.

## Out of Scope

- Code implementation.
- Actual `ko_context` implementation.
- Turn Engine.
- Accuracy calculation.
- Priority or final Speed order.
- Recovery implementation.
- Hazards, chip, residual, weather, or status damage.
- Focus Sash KO probability integration.
- UI changes.
- Fixture changes.
- Sample additions.
- Logs, `.env`, secrets, API keys, or handoff capsule commits.

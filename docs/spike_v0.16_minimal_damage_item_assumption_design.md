# v0.16 - Minimal Damage Item Assumption Design

## 1. Current v0.15 State

v0.15 established item assumptions as a design concern, not an implementation:

- Items should be represented separately from `stat_profiles`.
- A top-level `item_profiles` section is preferred over putting item state inside `stat_profiles`.
- `unknown`, `none`, `system_default_none`, and `user_confirmed` must be distinct.
- Item effects must not be described as applied unless a damage estimate explicitly says they were applied.
- Current v0.14 damage estimates still do not apply item effects.

The current app can already use:

- user-confirmed my moves
- user-confirmed opponent known moves
- Champions movepool candidate moves
- optional user-confirmed final stats for both active Pokemon
- stat-aware `assumption_profile`

The remaining damage accuracy gap is held item effects.

## 2. Problem Definition

Held items affect multiple systems:

- damage modifiers
- defensive bulk modifiers
- speed and turn order
- move lock
- recoil
- survival
- recovery
- item consumption
- hazards and utility effects

v0.16 should not become a full item system. The safe next step is a minimal
damage-only subset that improves damage estimates while keeping non-damage item
effects explicit and unmodeled.

The design must answer:

- which items can be applied to damage immediately
- which item effects are excluded even when the item is selected
- how item identity and item effect application appear in payload
- how item effects map to my move damage and opponent known move damage
- how to keep candidate moves, speed, survival, recovery, and KO odds out of scope

## 3. Option Comparison

### Option A - Keep Item Profiles Only

Pros:

- Safest and preserves current damage behavior.
- Lets the LLM know item state is unknown or user-confirmed.
- Avoids partial item-effect overclaims.

Cons:

- Does not improve damage accuracy.
- Leaves Choice Band / Specs / Life Orb as obvious missing factors.

### Option B - Minimal Damage Item Subset

Pros:

- Improves the highest-value damage cases.
- Keeps scope small.
- Reuses the existing `advisor/damage` item pipeline.
- Can mark non-damage effects as not connected.

Cons:

- Needs new payload guardrails.
- Needs careful item status and applied-effect summaries.
- Does not solve speed, survival, recovery, or choice lock.

### Option C - Full Item Damage / Defense System

Pros:

- Covers attacker and defender item math more broadly.
- Could handle Assault Vest, Eviolite, type-resist berries, plates, or type boosters.

Cons:

- Bigger scope.
- Defender-side assumptions need extra care.
- Berries and conditional items often imply consumption or exact battle state.

### Option D - Full Item System With Speed / Survival / Recovery

Pros:

- Long-term complete direction.

Cons:

- Requires Speed / Turn Order, Turn Engine, exact HP, item consumption, switch/hazard state, and move lock.
- Too large before the battle-state layer exists.

T3 recommendation: choose Option B for v0.16 implementation planning.

## 4. Minimal Item Subset

Recommended v0.16 attacker-side subset:

| Item | Damage effect | Non-damage effects excluded |
| --- | --- | --- |
| `choice-band` | physical Attack modifier x1.5 | choice lock |
| `choice-specs` | Special Attack modifier x1.5 | choice lock |
| `life-orb` | final damage modifier x1.3 | recoil |
| `muscle-band` | physical move base power modifier x1.1 | none relevant to v0.16 |
| `wise-glasses` | special move base power modifier x1.1 | none relevant to v0.16 |

Optional:

| Item | Reason to consider | Reason to defer |
| --- | --- | --- |
| `expert-belt` | existing engine supports super-effective final modifier | depends on type effectiveness and may add slightly more conditional complexity |

Defender-side candidate:

| Item | Reason to consider | v0.16 recommendation |
| --- | --- | --- |
| `assault-vest` | existing engine can apply special-defense modifier | defer to v0.16.x or v0.17 unless T1/T2 explicitly wants defender-side item math |

The first implementation should probably be attacker-side only. That covers:

- my item affecting my move damage into opponent
- opponent item affecting opponent known move damage into my active

It avoids defender item ambiguity while still improving the most common offensive item cases.

## 5. Explicitly Excluded Items / Effects

Excluded from v0.16:

- `choice-scarf`: speed order is not implemented.
- `focus-sash`: survival, current HP, hazards, multi-hit, and item consumption are not implemented.
- `leftovers`: recovery and turn progression are not implemented.
- `sitrus-berry`: HP threshold, recovery, and item consumption are not implemented.
- Choice lock: locked move state and turn history are not implemented.
- Life Orb recoil: post-damage state is not implemented.
- Damage reduction berries: type-specific conditional, consumption, and exact battle state are not implemented.
- `heavy-duty-boots`: hazards/field system is not implemented.
- `clear-amulet`, `covert-cloak`, and similar utility effects: require event/secondary-effect systems.
- KO/OHKO/2HKO from item-adjusted damage: still out of scope unless the probability layer is explicitly connected.

## 6. Payload Schema Proposal

Top-level `item_profiles` should be the source of truth.

```json
{
  "item_profiles": {
    "my_active": {
      "status": "user_confirmed",
      "source": "user_input",
      "item_id": "life-orb",
      "name_en": "Life Orb",
      "name_ko": null,
      "effects_scope": ["damage_modifier", "recoil"],
      "damage_modifier_status": "applied",
      "unapplied_effects": ["recoil"],
      "notes": [
        "Life Orb damage modifier is applied.",
        "Life Orb recoil is not connected."
      ]
    },
    "opponent_active": {
      "status": "unknown",
      "source": "not_connected",
      "item_id": null,
      "name_en": null,
      "name_ko": null,
      "effects_scope": [],
      "damage_modifier_status": "not_applicable",
      "unapplied_effects": [],
      "notes": [
        "Opponent item is unknown."
      ]
    }
  }
}
```

Status values:

- `unknown`
- `none`
- `system_default_none`
- `user_confirmed`

Damage modifier status values:

- `applied`
- `not_applied`
- `not_applicable`
- `unsupported_item`
- `partially_applied`

`name_ko` should stay `null` unless a reliable Korean item mapping is connected.
Do not hand-code uncertain Korean names in payload examples.

## 7. Damage Estimate Schema

The top-level `item_profiles` section says what the user/source claims.
Each `damage_estimate` should say what was actually used in that calculation.

Recommended `damage_estimate.item_effects`:

```json
{
  "item_effects": {
    "attacker_item": {
      "item_id": "life-orb",
      "status": "applied",
      "applied_effects": ["damage_modifier"],
      "unapplied_effects": ["recoil"],
      "source": "user_input"
    },
    "defender_item": {
      "item_id": null,
      "status": "unknown",
      "applied_effects": [],
      "unapplied_effects": []
    }
  }
}
```

Assumption profile adjustment:

```json
{
  "assumption_profile": {
    "id": "user_confirmed_final_stats_level50_with_damage_item",
    "label": "User-confirmed final stats / Level 50 / damage item applied",
    "source": "user_input",
    "confidence": "higher_confidence_reference",
    "is_user_confirmed": true,
    "item_effects": "damage_modifier_applied"
  }
}
```

If no final stats are user-confirmed but a damage item is applied, use a distinct
profile id such as:

```text
default_level50_ivs31_evs0_neutral_with_damage_item
```

`is_final_battle_damage` must remain `false` because:

- exact HP is not connected
- ability selection is not connected
- speed order is not connected
- weather/terrain/boosts/screens are not connected
- recoil, recovery, lock, survival, and Turn Engine effects are not connected
- KO/OHKO/2HKO are not calculated

## 8. Attacker / Defender Item Direction

For my move damage:

- attacker item: `item_profiles.my_active`
- defender item: `item_profiles.opponent_active`

For opponent known move damage:

- attacker item: `item_profiles.opponent_active`
- defender item: `item_profiles.my_active`

For candidate moves:

- no `damage_estimate`
- no item application
- candidate moves remain possible, not confirmed

Recommended v0.16 first pass:

- apply supported attacker-side item effects only
- include defender item in `item_effects` summary as `unknown`, `none`, or `not_applied`
- do not apply defender-side item effects unless explicitly included by T1/T2

This keeps `assault-vest`, `eviolite`, and berries out of the first pass.

## 9. Damage Helper Impact

Files reviewed:

- `llm/advisor_damage_estimate.py`
- `advisor/damage/formula.py`
- `advisor/damage/items.py`
- `advisor/damage/item_modifiers.py`
- `data/static/items.json`
- `data/static/items_damage.json`
- `tests/test_advisor_damage_estimate.py`
- `tests/test_damage_parity_items.py`
- `tests/test_items.py`
- `tests/test_item_modifiers.py`

Findings:

- `DamageContext` already accepts `attacker_item` and `defender_item`.
- `advisor.damage.items.get_item()` already resolves `ItemEffect` from `data/static/items_damage.json`.
- `calc_damage_rolls()` already applies:
  - BP item modifiers through `get_bp_item_modifier()`
  - Attack / SpA modifiers through `get_atk_item_modifier()` and `get_spa_item_modifier()`
  - final attacker item modifiers through `get_final_atk_item_modifier()`
  - defender-side modifiers through `defense_stat_item_mod()` and `defender_berry_mod()`
- Item parity tests already cover `life-orb`, `choice-band`, `choice-specs`, `muscle-band`, `wise-glasses`, `expert-belt`, and `flame-plate`.

Design implication:

- v0.16 should not modify `advisor/damage`.
- The LLM helper can resolve a supported `item_profiles.*.item_id` to `get_item(item_id)` and pass it into `DamageContext.attacker_item`.
- Unsupported or excluded items should not be passed into the damage context as applied effects.
- The helper should build `item_effects` summaries based on what it actually passed to `DamageContext`.

Potential helper structure:

```text
_item_profile_for_role(battle_input, role_key) -> dict
_supported_attacker_damage_item(profile, move_category) -> ItemEffect | None
_item_effect_summary(profile, applied_item, role="attacker") -> dict
```

## 10. UI Direction

v0.16 design does not implement UI, but implementation needs an input source.

Options:

### ItemProfileDialog

Best long-term shape.

- Separate from stats.
- Can show `unknown`, `none`, `user_confirmed`.
- Can show whether damage effect is applied.
- Can grow into legal item search.

### PokemonPanel Compact Item Selector

Good in-battle UX if space allows.

- Similar to `Stats` button.
- Faster to use.
- Needs item search or dropdown.

### StatProfileDialog Item Dropdown

Not recommended.

- Mixes stats and battle assumptions.
- Adds clutter.

### Debug / Manual Input

Useful only for tests or temporary internal validation.

T3 recommendation:

- For v0.16 implementation, use a minimal ItemProfileDialog or a compact item selector, but only after T1/T2 decide whether UI is in scope.
- If UI is too much for v0.16, add item payload/helper tests first and defer UI to v0.16.1.

## 11. Legal Item Source / Cache

Current local sources:

- `data/static/items.json`: small item implementation metadata.
- `data/static/items_damage.json`: item effect metadata used by the damage engine.
- `data/static/mega_stones.json`: mega/primal item metadata.

External source candidates:

- MetaVGC legal Pokemon/items/moves snapshot for Pokemon Champions Regulation M-A.
- ChampDex held item guide and format rules.
- Serebii/Bulbapedia only as cross-checks if Champions-specific item legality is exposed.
- PokeAPI only as generic metadata fallback, never as Champions legality source.

v0.16 decision:

- A full legal item cache is not required for a minimal hardcoded damage subset.
- If UI exposes all items, legal item source becomes important.
- Safer v0.16 path: expose only the explicitly supported minimal subset, with notes that this is not the full legal item list.

Future cache proposal:

```json
{
  "format": "pokemon_champions",
  "regulation": "M-A",
  "source_kind": "legal_item_pool",
  "items": [
    {
      "item_id": "life-orb",
      "name_en": "Life Orb",
      "name_ko": null,
      "source_refs": ["metavgc", "champdex"],
      "confidence": "third_party_primary",
      "metadata_source": "local_items_damage"
    }
  ],
  "notes": [
    "PokeAPI item metadata is not used as a Champions legality source."
  ]
}
```

No scraping or cache generation in v0.16 design.

## 12. Advisor Payload Contract Update Plan

Future `docs/advisor_payload_contract.md` and `llm/advisor_payload_contract.py`
updates should include:

- `item_profiles` top-level schema.
- `unknown` vs `none` distinction.
- `user_confirmed` item identity does not automatically mean all item effects are applied.
- `damage_estimate.item_effects` is the source for applied item effects.
- `damage_modifier_status: "applied"` is required before the LLM may say damage includes an item.
- `damage_modifier_status: "not_applied"` or `unsupported_item` means the item is known but not used in the damage number.
- Choice lock, Life Orb recoil, Focus Sash survival, Leftovers/Sitrus recovery, and Choice Scarf speed are not connected.
- `is_final_battle_damage` remains `false`.

New guardrail candidates:

- "Do not treat unknown item as no item."
- "Do not claim item effects are included unless `damage_estimate.item_effects` marks them as applied."
- "Do not claim Choice Scarf speed order, Focus Sash survival, Leftovers recovery, Choice lock, or Life Orb recoil in v0.16."
- "Do not infer items from final stats, move choice, or candidate moves."

## 13. Allowed LLM Claims

Allowed:

- "Life Orb damage modifier is applied, but recoil is not modeled."
- "Choice Band boosts physical damage in this estimate, but choice lock is not modeled."
- "The opponent item is unknown, so actual damage may differ."
- "This remains not final battle damage."
- "This item is known, but its damage modifier is unsupported/not applied" when the payload says so.

## 14. Disallowed LLM Claims

Disallowed:

- Treating unknown item as none.
- Saying unsupported item effects are applied.
- Claiming Choice Scarf establishes speed order.
- Claiming Focus Sash guarantees survival.
- Applying Leftovers or Sitrus recovery.
- Claiming Choice lock is modeled.
- Applying Life Orb recoil.
- Using item-modified damage to assert KO/OHKO/2HKO.
- Calling the result final battle damage.

## 15. Tests Plan

Future v0.16 implementation tests:

- `item_profiles.my_active` user-confirmed schema.
- `item_profiles.opponent_active` unknown/default schema.
- `unknown` item does not modify damage.
- `none` item does not modify damage.
- `choice-band` modifies physical moves only.
- `choice-specs` modifies special moves only.
- `life-orb` modifies damage and reports recoil as not connected.
- `muscle-band` modifies physical move damage only.
- `wise-glasses` modifies special move damage only.
- Optional `expert-belt` only modifies super-effective damage.
- My move damage uses `item_profiles.my_active` as attacker item.
- Opponent known move damage uses `item_profiles.opponent_active` as attacker item.
- Candidate moves still do not receive `damage_estimate`.
- `damage_estimate.item_effects` appears when an item effect is applied.
- `is_final_battle_damage` remains false.
- KO/OHKO/2HKO fields remain absent.
- Prompt/contract guardrails remain present.

Regression tests:

- Existing default no-item damage is unchanged.
- Existing final stat profile behavior is unchanged.
- Existing opponent known move damage remains unchanged when item is unknown.

## 16. Out of Scope

Excluded from v0.16 design:

- Code implementation.
- UI implementation.
- Item damage modifier implementation.
- Legal item scraping/cache.
- Choice Scarf speed.
- Focus Sash survival.
- Leftovers/Sitrus recovery.
- Choice lock.
- Life Orb recoil.
- KO/OHKO/2HKO.
- Speed order.
- Turn Engine.
- Damage/probability engine modifications.

## 17. T1/T2 Decisions Needed

- Should v0.16 implementation include a UI item selector, or payload/helper first?
- Should v0.16 include optional `expert-belt`, or keep only five simple attacker-side items?
- Should v0.16 include defender-side `assault-vest`, or defer it?
- Should supported item names be English-only at first until Korean item mapping is reliable?
- Should legal item list/cache be required before exposing item UI beyond the minimal subset?

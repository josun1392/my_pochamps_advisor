# v0.32 Type Boosting Item Damage Modifier Design

## 1. Current State

The app now has a complete legal item selection path:

- `data/static/champions_legal_items.json` contains 117 Regulation M-A legal item entries.
- `ItemProfileDialog` uses `ChampionsItemRepository` legal item options.
- Legal item search supports English, item id, and partial Korean names.
- Category sorting is in place.
- Damage-supported non-legal/debug items are hidden from the normal selector.
- Choice Scarf is modeled only in `speed_context` effective Speed when user-confirmed.

The legal fixture already marks many type boosting items as `legal_and_damage_supported`. Current counts from the fixture are:

- `type_boosting_item`: 18
- `legal_and_damage_supported`: 17
- `legal_but_not_modeled`: 100
- `damage_supported_non_legal_items`: 5

The damage engine already has item modifier hooks:

- `advisor/damage/items.py` loads `data/static/items_damage.json`.
- `advisor/damage/item_modifiers.py` has type boost support through `attacker_base_power_item_mod`.
- `advisor/damage/formula.py` applies item/base-power modifiers through `DamageContext.attacker_item`.
- `llm/advisor_damage_estimate.py` already passes an attacker item into `DamageContext`, but only if the item passes the LLM helper's supported attacker damage item allowlist.

Important current limitation:

- `llm/advisor_damage_estimate.py` currently gates attacker damage items through `SUPPORTED_ATTACKER_DAMAGE_ITEMS`, which contains only the legacy damage-test subset:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
  - `muscle-band`
  - `wise-glasses`
- Therefore legal type boosting items may exist in the lower-level item catalog but are not yet applied through the LLM payload helper.

## 2. Problem Definition

Type boosting items are a good next item effect target because they directly modify damage estimates and do not require turn sequencing.

However, they must be handled carefully:

- A type boosting item should apply only when the selected item's boosted type matches the move type.
- Legal item selection alone must not imply a damage boost.
- The normal legal path must not mix in debug/non-legal damage items.
- The LLM may only say a damage modifier was applied when `damage_estimate.item_effects` marks it as `applied`.
- If a type boosting item is selected but the move type does not match, the item should be present in the payload but marked as not applicable for that move.

The design goal is to add a narrow legal attacker-side damage modifier path in a future milestone without widening into Focus Sash, recovery, probability, Turn Engine, or non-legal item behavior.

## 3. Type Boosting Item Candidate List

The fixture has 18 legal `type_boosting_item` entries.

| item_id | name_en | fixture status | catalog boosted_type | catalog Q12 modifier | v0.33 candidate |
| --- | --- | --- | --- | --- | --- |
| `black-belt` | Black Belt | `legal_and_damage_supported` | fighting | 4915 | yes |
| `black-glasses` | Black Glasses | `legal_and_damage_supported` | dark | 4915 | yes |
| `charcoal` | Charcoal | `legal_and_damage_supported` | fire | 4915 | yes |
| `dragon-fang` | Dragon Fang | `legal_and_damage_supported` | dragon | 4915 | yes |
| `fairy-feather` | Fairy Feather | `legal_but_not_modeled` | missing | missing | not until catalog support exists |
| `hard-stone` | Hard Stone | `legal_and_damage_supported` | rock | 4915 | yes |
| `magnet` | Magnet | `legal_and_damage_supported` | electric | 4915 | yes |
| `metal-coat` | Metal Coat | `legal_and_damage_supported` | steel | 4915 | yes |
| `miracle-seed` | Miracle Seed | `legal_and_damage_supported` | grass | 4915 | yes |
| `mystic-water` | Mystic Water | `legal_and_damage_supported` | water | 4915 | yes |
| `never-melt-ice` | Never-Melt Ice | `legal_and_damage_supported` | ice | 4915 | yes |
| `poison-barb` | Poison Barb | `legal_and_damage_supported` | poison | 4915 | yes |
| `sharp-beak` | Sharp Beak | `legal_and_damage_supported` | flying | 4915 | yes |
| `silk-scarf` | Silk Scarf | `legal_and_damage_supported` | normal | 4915 | yes |
| `silver-powder` | Silver Powder | `legal_and_damage_supported` | bug | 4915 | yes |
| `soft-sand` | Soft Sand | `legal_and_damage_supported` | ground | 4915 | yes |
| `spell-tag` | Spell Tag | `legal_and_damage_supported` | ghost | 4915 | yes |
| `twisted-spoon` | Twisted Spoon | `legal_and_damage_supported` | psychic | 4915 | yes |

Observed gap:

- `fairy-feather` is legal in the fixture but lacks a corresponding `type_boost_items` entry in `items_damage.json`.
- v0.33 should either:
  - exclude `fairy-feather` from the initial implementation, or
  - add explicit catalog support in a separate reviewed fixture/data change.

T3 recommendation:

- v0.33 should implement only the 17 items already marked `legal_and_damage_supported` and present in `items_damage.json`.
- `fairy-feather` should remain `legal_but_not_modeled` until its local catalog support is added and tested.

## 4. Modifier Rules

Proposed rules:

- Apply only attacker-side.
- Apply only when:
  - the attacker item profile is `status == "user_confirmed"`;
  - the selected item is a normal legal item, not a debug/non-legal item;
  - `effect_support_status == "legal_and_damage_supported"`;
  - `advisor.damage.items.get_item(item_id)` returns an `ItemEffect`;
  - `ItemEffect.kind == "type_boost"`;
  - the move category is physical or special;
  - the move type matches the item's `boosted_types`.
- Do not apply to status moves.
- Do not apply if move type is missing.
- Do not apply if the item is selected but boosted type does not match the move type.
- Do not apply if the item is in `damage_supported_non_legal_items`.

Modifier value:

- Existing catalog entries use Q12 multiplier `4915`, which is approximately `1.2x`.
- This matches the expected type boosting item behavior.

Damage formula location:

- Lower-level formula already supports item base-power modifiers through `attacker_base_power_item_mod`.
- `DamageContext.attacker_item` is the appropriate path to reuse.
- The LLM helper should decide whether an item is eligible and then pass the `ItemEffect` into `DamageContext`.

Physical/special behavior:

- Type boosting items are move-type based, not physical/special-specific.
- They should apply to both physical and special damaging moves when move type matches.

## 5. Payload Behavior

`damage_estimate.item_effects.attacker_item` should become the source of truth.

### Applied example

```json
{
  "item_effects": {
    "attacker_item": {
      "status": "applied",
      "item_id": "charcoal",
      "name_en": "Charcoal",
      "effect_type": "type_boosting_damage_modifier",
      "boosted_type": "fire",
      "modifier": 1.2,
      "applied_effects": ["damage_modifier"],
      "unapplied_effects": [],
      "reason": "Move type matches item boosted type."
    }
  }
}
```

### Not applicable example

```json
{
  "item_effects": {
    "attacker_item": {
      "status": "not_applicable",
      "item_id": "charcoal",
      "name_en": "Charcoal",
      "effect_type": "type_boosting_damage_modifier",
      "boosted_type": "fire",
      "applied_effects": [],
      "unapplied_effects": ["move_type_does_not_match_item_boosted_type"],
      "reason": "Move type does not match item boosted type."
    }
  }
}
```

### Recognized but not modeled example

`fairy-feather` should remain not modeled until catalog support is added:

```json
{
  "item_effects": {
    "attacker_item": {
      "status": "not_applied",
      "item_id": "fairy-feather",
      "name_en": "Fairy Feather",
      "applied_effects": [],
      "unapplied_effects": ["item_effect_not_modeled_in_v0.33"],
      "reason": "This legal item is not yet connected to the local damage item catalog."
    }
  }
}
```

Schema compatibility:

- Keep existing `applied_effects` and `unapplied_effects`.
- Add `effect_type`, `boosted_type`, `modifier`, and `reason` as additive fields.
- Keep `assumption_profile.damage_item_applied == true` only when the item status is `applied`.

## 6. Direction / Attacker-Defender Handling

Direction rules:

- My move damage:
  - attacker item = `item_profiles.my_active`
  - defender item = `item_profiles.opponent_active`
- Opponent known move damage:
  - attacker item = `item_profiles.opponent_active`
  - defender item = `item_profiles.my_active`
- Candidate moves:
  - still no damage estimate
  - no item application

v0.33 scope should remain attacker-side only.

Defender items remain out of scope:

- Assault Vest
- Focus Sash
- type-resist berries
- Leftovers/Sitrus
- Mega Stones

## 7. UI Direction

v0.33 should not need UI changes.

Reason:

- The legal item selector already exposes the legal type boosting items.
- Search and category sorting already make them discoverable.
- The helper can read the selected item profile from the existing payload.

No label/search/category changes are needed for the first implementation.

Future optional polish:

- Add a subtle display indicator for modeled damage items.
- Avoid this in v0.33 unless T1/T2 request it, because it can imply broader modeling coverage than exists.

## 8. Legal / Non-Legal Separation

Normal legal path:

- Only normal legal selector items should be considered for legal type boosting implementation.
- The safest eligibility source is:
  - item profile `status == "user_confirmed"`
  - `legality_status == "legal"`
  - `effect_support_status == "legal_and_damage_supported"`
  - item exists in the type-boost catalog

Debug/test-only path:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`

These must remain separate:

- They may remain in helper tests and legacy damage regressions.
- They must not be treated as normal legal selector items.
- They must not be surfaced by normal UI.
- They should not be mixed into the legal type boosting implementation.

If a future Regulation makes one of these legal, the legal fixture must be updated first.

## 9. LLM Guardrail

Contract/prompt should preserve these meanings:

- Legal item selection does not automatically mean the item effect is modeled.
- A type boosting item changes damage only when `damage_estimate.item_effects.attacker_item.status == "applied"`.
- If the selected type boosting item does not match the move type, do not say the damage boost was applied.
- If an item is `not_applicable`, explain that the item did not affect that move.
- If an item is `not_applied` or `unsupported_item`, do not imply the damage includes its effect.
- Focus Sash, Leftovers, Sitrus Berry, Quick Claw, Bright Powder, Scope Lens, King's Rock, Mega Stones, and other unmodeled items remain unmodeled.
- Do not infer final battle damage.
- Do not claim KO/OHKO/2HKO.
- Do not claim final turn order.

Suggested LLM-allowed wording:

- "Charcoal's supported Fire-type damage modifier is applied to this Fire move."
- "Charcoal is selected, but it does not boost this Dragon-type move."
- "Focus Sash is selected, but survival effects are not modeled."

Suggested disallowed wording:

- "This legal item boosts damage" when item_effects does not say `applied`.
- "Fairy Feather is applied" before local catalog support exists.
- "Focus Sash lets you survive" before survival modeling exists.

## 10. Tests Plan

v0.33 implementation tests should include:

- Charcoal + Fire move -> modifier applied.
- Charcoal + Dragon move -> not_applicable.
- Mystic Water + Water move -> applied.
- Black Belt + Fighting move -> applied.
- Metal Coat + Steel move -> applied.
- Fairy Feather + Fairy move -> not_applied until catalog support exists, unless v0.33 explicitly adds catalog support.
- Type boosting item applies to physical and special moves when type matches.
- Status move does not get a damage estimate or item modifier.
- `item_effects.attacker_item` records:
  - `status`
  - `item_id`
  - `name_en`
  - `effect_type`
  - `boosted_type`
  - `modifier`
  - `reason`
- My available move damage receives modifier.
- My selected move damage receives modifier.
- Opponent known move damage receives modifier.
- Candidate moves still have no damage estimate.
- Non-legal damage-supported item separation remains intact.
- Choice Band / Choice Specs / Life Orb remain hidden from normal selector.
- Existing v0.30 speed_context tests remain green.
- Existing item selector/search/Korean mapping tests remain green.
- Existing damage regression tests remain green.
- Advisor prompt/contract guardrails remain green.

## 11. v0.33 Implementation Candidate

Recommended:

`v0.33 - Type Boosting Item Damage Modifier Implementation`

Include:

- Legal type boosting item attacker-side damage modifier.
- Reuse `DamageContext.attacker_item`.
- Reuse `advisor.damage.items.get_item`.
- Extend LLM helper eligibility beyond legacy `SUPPORTED_ATTACKER_DAMAGE_ITEMS` for legal type-boost items.
- Add item effect metadata for applied/not_applicable type boosting items.
- Update contract/prompt tests.
- Update `docs/PROGRESS.md`.

Exclude:

- Expert Belt.
- Assault Vest.
- Focus Sash.
- Leftovers/Sitrus recovery.
- Choice Band / Choice Specs / Life Orb normal legal path.
- Fairy Feather unless catalog support is explicitly added and reviewed.
- KO/OHKO/2HKO.
- Turn Engine.
- UI changes.
- Damage/probability engine redesign.

T3 recommendation:

- v0.33 can be a small implementation if T1/T2 approve the schema above.
- If T1/T2 want extra caution, add a short v0.32.1 schema approval step first, but it is probably not necessary.

## 12. Out of Scope

This design does not implement:

- Code changes.
- Damage modifier behavior.
- Fixture changes.
- UI changes.
- `item_effect_coverage.json`.
- Expert Belt.
- Assault Vest.
- Focus Sash.
- Leftovers/Sitrus recovery.
- Choice Band / Choice Specs / Life Orb normal legal path.
- Fairy Feather catalog support.
- KO/OHKO/2HKO.
- Turn Engine.
- Damage/probability engine redesign.
- Logs, `.env`, secrets, or handoff updates.

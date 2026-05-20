# v0.15 - Item Assumption Design

## 1. Current v0.14 State

Master Ball Advisor currently sends enough battle state for useful default-assumption
damage advice:

- `moves.my_available_moves[*].damage_estimate` compares the user's confirmed moves.
- `moves.my_selected_move.damage_estimate` remains available for selected-slot continuity.
- `opponent_moves.known_moves[*].damage_estimate` estimates damage from user-confirmed opponent moves into `my_active`.
- `opponent_moves.candidate_moves` is sourced from the Champions movepool cache and remains `possible_not_confirmed`.
- `stat_profiles.my_active` and `stat_profiles.opponent_active` can carry user-provided final stats.
- `damage_estimate.assumption_profile` distinguishes default stats from user-confirmed final stats.

The current item state is still effectively not connected:

- `stat_profiles.*.item` is `null`.
- `ADVISOR_DAMAGE_ASSUMPTIONS["item"]` is `"none"`.
- Prompt and contract guardrails warn that item, selected ability, speed order, exact HP, and Turn Engine state are not connected.
- The LLM must not infer held items from final stats or move choices.

This means v0.14 can improve stat accuracy, but the damage estimate can still be
materially wrong when a held item changes offense, defense, speed, survival,
recovery, or move locking.

## 2. Problem Definition

Final stats reduce one major source of uncertainty, but item assumptions are now
the next accuracy bottleneck.

Direct damage examples:

- `choice-band` modifies physical Attack.
- `choice-specs` modifies Special Attack.
- `life-orb` modifies final damage and also has recoil that is not a pure damage-estimate concern.
- `muscle-band` and `wise-glasses` are simple smaller damage modifiers.
- Type-boosting items and plates modify damage conditionally by move type.

Defensive examples:

- `assault-vest` modifies Special Defense and can change opponent-known-move threat estimates.
- `eviolite` modifies Defense and Special Defense but requires NFE knowledge.
- Resist berries reduce damage only under type/effectiveness conditions.

Non-damage examples:

- `choice-scarf` affects Speed and turn order.
- `focus-sash` affects survival and needs current HP plus turn logic.
- `leftovers` and `sitrus-berry` affect recovery and require Turn Engine state.
- Choice items imply move lock, which is a turn-state behavior even when their stat modifier is damage-relevant.

Therefore, connecting "items" as a single binary feature would be too broad.
The design must separate item identity, source, legality, effect category, and
whether a specific effect is actually applied to the current damage estimate.

## 3. Option Comparison

### Option A - Keep Item None / Not Connected

Pros:

- Safest and least disruptive.
- No risk of overclaiming item effects.
- Keeps v0.14 damage behavior stable.

Cons:

- Leaves a large accuracy gap after final stats are connected.
- User-confirmed item information cannot be represented.
- LLM can only say "items are unknown" instead of using precise user input.

### Option B - Item Profiles Only

Pros:

- Adds an explicit payload contract for item identity and source.
- Separates `unknown`, `none`, `system_default_none`, and `user_confirmed`.
- Allows the LLM to discuss item uncertainty without pretending effects are applied.
- Prepares v0.16 without changing damage numbers.

Cons:

- No immediate damage accuracy improvement.
- Requires careful guardrails so user-confirmed items are not treated as applied effects.

### Option C - Minimal Damage Item Assumption

Pros:

- Directly improves damage estimates for a small damage-only subset.
- The existing `advisor/damage` engine already has item modifier primitives and tests.
- Can start with attacker-side damage items before Turn Engine work.

Cons:

- Must define which item effects are applied and which are merely noted.
- Choice lock, recoil, speed, recovery, and survival effects remain excluded.
- Needs careful assumption profile and limitations updates.

### Option D - Full Item System

Pros:

- Most faithful long-term model.
- Can cover damage, speed, survival, recovery, lock-in, berries, and utility items.

Cons:

- Too large for v0.15.
- Requires Speed / Turn Order, Turn Engine, exact HP, current HP, switching, and item consumption state.
- High risk of false precision if implemented before the battle model exists.

## 4. Recommended Direction

T3 recommendation:

- v0.15: choose Option B as a design milestone.
- v0.16: implement Option C as a minimal damage-only item subset.
- v0.17: design Speed / Turn Order.
- v0.18: design KO/OHKO/2HKO after item and exact-HP boundaries are clearer.

The item data should not live inside `stat_profiles`. Items are battle
assumptions, not stat source data. A held item can affect stat stages, base
power, final damage, speed, survival, recovery, move locking, immunity, and
Turn Engine behavior. Keeping it top-level makes the future extension path much
cleaner.

## 5. Proposed Payload Schema

Preferred v0.15 shape:

```json
{
  "item_profiles": {
    "my_active": {
      "status": "unknown",
      "source": "not_connected",
      "item_id": null,
      "name_en": null,
      "name_ko": null,
      "effects_scope": [],
      "damage_modifier_status": "not_applied_in_v0.15",
      "notes": [
        "Item identity is not connected in v0.15.",
        "Current damage estimates do not apply held item effects."
      ]
    },
    "opponent_active": {
      "status": "user_confirmed",
      "source": "user_input",
      "item_id": "choice-band",
      "name_en": "Choice Band",
      "name_ko": "구애머리띠",
      "effects_scope": ["damage_modifier", "move_lock"],
      "damage_modifier_status": "not_applied_in_v0.15",
      "notes": [
        "Item is user-provided.",
        "Item effects are not applied unless explicitly marked as applied.",
        "Choice lock is not modeled without Turn Engine state."
      ]
    }
  }
}
```

Alternative shape:

```json
{
  "battle_assumptions": {
    "items": {
      "my_active": {},
      "opponent_active": {}
    }
  }
}
```

Comparison:

- `item_profiles` is easier for LLM reading and mirrors `stat_profiles`.
- `battle_assumptions.items` may be better once weather, terrain, screens, boosts, and side conditions are grouped together.
- For v0.15-v0.16, `item_profiles` is clearer and lower-risk.
- If later battle assumptions become broad, `item_profiles` can remain a first-class section or be nested under a broader `battle_assumptions` object in a compatibility milestone.

Recommendation: use top-level `item_profiles` in v0.16.

## 6. Item Status / Source Model

Required states:

- `unknown`: item is not known; do not treat as no item.
- `none`: user confirmed the Pokemon has no held item.
- `system_default_none`: damage calculation used no item because no item system is connected.
- `user_confirmed`: user explicitly selected or entered an item.
- `not_connected`: item UI/source does not exist for this role yet.
- `candidate_unconfirmed`: item is a possible item from a set, usage source, or legal pool, but not confirmed.

Important distinction:

- `unknown` means the real item may change damage.
- `none` means user confirmed no held item.
- `system_default_none` means the calculation used no item as a conservative system default, not because the game state is known.

Suggested v0.16 damage-estimate wording:

```json
"item_assumption": {
  "attacker": {
    "status": "user_confirmed",
    "item_id": "life-orb",
    "damage_effect": "applied"
  },
  "defender": {
    "status": "unknown",
    "item_id": null,
    "damage_effect": "not_applied"
  }
}
```

## 7. Item Classification

### Damage Modifier Items

Examples:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`
- `expert-belt`
- Type-boosting items such as `charcoal`, `magnet`, `mystic-water`
- Plates and species orbs when legal/applicable

v0.16 suitability:

- Good first target when limited to damage-estimate math.
- Existing engine support already covers several of these.
- Non-damage side effects must remain limitations.

LLM framing:

- "Damage estimate applies the item modifier" only if `damage_modifier_status` says applied.
- Otherwise: "If this item is present, damage may differ; not applied in this estimate."

### Defensive Modifier Items

Examples:

- `assault-vest`
- `eviolite`
- Type-resist berries
- Species defensive items such as `deep-sea-scale`

v0.16 suitability:

- `assault-vest` is plausible but increases scope because defender item handling must be symmetrical.
- `eviolite` needs NFE state.
- Resist berries need consumption and type/effectiveness conditions.

Recommendation:

- Consider `assault-vest` only after attacker-side damage items are working.
- Defer berries until Turn Engine / item consumption exists.

### Speed / Order Items

Examples:

- `choice-scarf`
- `quick-powder`
- `iron-ball`

v0.16 suitability:

- Exclude. They do not belong in damage-only implementation.

LLM framing:

- Do not claim turn order from item identity until Speed / Turn Order is implemented.

### Survival Items

Examples:

- `focus-sash`

v0.16 suitability:

- Exclude. Requires exact HP, hit sequence, multi-hit handling, hazards/residuals, and item consumption.

### Recovery / Turn Items

Examples:

- `leftovers`
- `sitrus-berry`

v0.16 suitability:

- Exclude. Requires Turn Engine and current HP.

### Utility Items

Examples:

- `heavy-duty-boots`
- `clear-amulet`
- `covert-cloak`
- `mental-herb`
- `white-herb`

v0.16 suitability:

- Exclude from damage-estimate application.
- Represent as item identity only if user-confirmed.

## 8. Minimal v0.16 Candidate Scope

Recommended v0.16 scope:

- Add `item_profiles.my_active` and `item_profiles.opponent_active`.
- Add minimal item input source or fixture path only after T1/T2 approves implementation.
- Apply item effects only for a small damage subset:
  - `choice-band`: attacker physical damage via Attack modifier.
  - `choice-specs`: attacker special damage via Special Attack modifier.
  - `life-orb`: final damage modifier; recoil explicitly not connected.
  - `muscle-band`: physical move base power modifier.
  - `wise-glasses`: special move base power modifier.
  - Optional: `expert-belt` if super-effective-only condition is already reliable.

Defer:

- `choice-scarf` because speed order is not implemented.
- `focus-sash` because survival logic is not implemented.
- `leftovers` and `sitrus-berry` because Turn Engine and exact HP are not implemented.
- `assault-vest` unless T1/T2 explicitly wants defender-side item damage math in v0.16.
- Choice lock. It should be noted in limitations only.
- Life Orb recoil. It should be noted in limitations only.

## 9. Damage Estimate Behavior

v0.15:

- No damage number changes.
- No item effects are applied.
- `assumption_profile` remains stat-focused.
- The design should specify future item-related fields but not implement them.

v0.16:

- If item effects are applied, the `damage_estimate` should say so explicitly.
- `is_final_battle_damage` should remain `false`.
- Add item details either to `assumption_profile` or a sibling `item_assumption` field.

Recommended v0.16 damage-estimate fields:

```json
{
  "assumption_profile": {
    "id": "user_confirmed_final_stats_with_damage_item_level50",
    "source": "user_input",
    "confidence": "higher_confidence_reference",
    "is_user_confirmed": true,
    "item_effects": "damage_modifier_applied"
  },
  "item_assumption": {
    "attacker": {
      "status": "user_confirmed",
      "item_id": "life-orb",
      "damage_modifier_status": "applied",
      "non_damage_effects": ["recoil_not_connected"]
    },
    "defender": {
      "status": "unknown",
      "item_id": null,
      "damage_modifier_status": "not_applied"
    }
  }
}
```

Guardrail:

- Do not say "item-applied damage" unless the item's damage effect is actually included.
- If item is `unknown`, say the result can change.
- If item is `none`, say no held item was user-confirmed.
- If item is `system_default_none`, say the calculation assumes no item, but this is not confirmed battle state.

## 10. UI Design Options

### UI-A: Add Item Dropdown to `StatProfileDialog`

Pros:

- Simple surface count.
- User already opens the Stats dialog for assumptions.

Cons:

- Conflates stats and battle assumptions.
- Item effects reach beyond stats.
- Dialog may become crowded.

Recommendation: not preferred.

### UI-B: Separate `ItemProfileDialog`

Pros:

- Clean separation from stats.
- Can show item status: unknown / none / user-confirmed.
- Can show "damage effect applied?" later.
- Easier to add legality/source labels.

Cons:

- Adds another dialog and button.

Recommendation: best long-term direction.

### UI-C: Compact Item Selector Button in `PokemonPanel`

Pros:

- Fast in-battle interaction.
- Can mirror the current `Stats` button.
- Good for my/opponent active panels.

Cons:

- Needs item search/mapping and legal list.
- Could crowd the Pokemon cards.

Recommendation: good v0.16 implementation candidate if layout is acceptable.

### UI-D: Debug / Manual JSON Input

Pros:

- Fastest for internal validation.
- Minimal UI work.

Cons:

- Poor T1 usability.
- Easy to create invalid states.

Recommendation: avoid unless used only in tests.

## 11. Data Source / Legal Item List

Current repo state:

- `data/static/items_damage.json` contains item damage/effect metadata for many battle items.
- `data/static/items.json` contains implementation metadata for selected items.
- `data/static/mega_stones.json` exists for Mega/Primal form handling.
- `advisor/damage/items.py` loads item effects from `items_damage.json`.
- `advisor/damage/item_modifiers.py` contains implemented modifiers for:
  - `life-orb`
  - `choice-band`
  - `choice-specs`
  - `muscle-band`
  - `wise-glasses`
  - `expert-belt`
  - partial plate support
  - defensive modifiers such as `assault-vest` and `eviolite`
- Item parity tests already exist in `tests/test_damage_parity_items.py`, `tests/test_items.py`, and `tests/test_item_modifiers.py`.

Legal item source candidates:

- MetaVGC has a Regulation M-A legal Pokemon/items/moves snapshot page and reports an allowed item count.
- ChampDex has a Champions held items guide and format rules pages.
- Serebii / Bulbapedia may be useful cross-check sources when their Champions pages expose item legality clearly.
- PokeAPI can supply generic item metadata, but must not be treated as Champions legality.

Recommended future cache:

```json
{
  "format": "pokemon_champions",
  "regulation": "M-A",
  "source_kind": "legal_item_pool",
  "items": [
    {
      "item_id": "choice-band",
      "name_en": "Choice Band",
      "name_ko": "구애머리띠",
      "source_refs": ["metavgc", "champdex"],
      "confidence": "third_party_primary",
      "metadata_source": "local_items_damage"
    }
  ],
  "fetched_at": "YYYY-MM-DD",
  "source_refs": {
    "primary": ["metavgc"],
    "cross_check": ["champdex"],
    "metadata": ["local_items_damage", "pokeapi_optional"]
  },
  "notes": [
    "PokeAPI item metadata is not a Champions legality source.",
    "Legal item pool may change by regulation."
  ]
}
```

No scraping or cache generation should happen in v0.15.

## 12. Advisor Payload Contract Update Plan

Future contract changes should say:

- `item_profiles` exists as a top-level section.
- `unknown` and `none` are not equivalent.
- `system_default_none` means the calculation used no item because no item was connected, not because no item is confirmed.
- `user_confirmed` item identity is only confirmed identity; its effect may still be `not_applied`.
- If `damage_modifier_status` is `not_applied`, the LLM must not speak as if damage includes that item.
- Choice Scarf speed claims require Speed / Turn Order.
- Focus Sash survival claims require survival/turn logic.
- Leftovers/Sitrus recovery requires Turn Engine and exact/current HP.
- Item effects cannot be used to claim KO/OHKO/2HKO unless those probabilities are explicitly calculated.

`llm/advisor_payload_contract.py` should eventually add constants for:

- known item statuses
- item effect scopes
- item guardrail strings
- item damage limitations

`docs/advisor_payload_contract.md` should document:

- item profile schema
- effect application status
- allowed and disallowed item claims
- relationship between item profile and damage estimate

## 13. Allowed LLM Claims

Allowed:

- "Current damage estimates do not apply held item effects."
- "The opponent item is unknown, so actual damage may differ."
- "If Choice Band is confirmed and applied in a future calculation, physical damage may increase."
- "This item is user-provided, but its effects are not applied unless marked as applied."
- "No item was user-confirmed" only when status is `none`.
- "The calculation used a no-item system default" only when status is `system_default_none`.

## 14. Disallowed LLM Claims

Disallowed:

- Treating `unknown` item as `none`.
- Claiming Choice Scarf determines speed order before Speed / Turn Order exists.
- Claiming Focus Sash guarantees survival.
- Applying Leftovers/Sitrus recovery to the turn result before Turn Engine exists.
- Saying damage includes item effects when `damage_modifier_status` is `not_applied`.
- Using items to assert KO/OHKO/2HKO.
- Inferring items from final stats, moves, or candidate moves.

## 15. Tests Plan

Future implementation tests:

- `item_profiles.my_active` default schema exists.
- `item_profiles.opponent_active` default schema exists.
- `unknown`, `none`, `system_default_none`, and `user_confirmed` are distinct.
- User-confirmed item carries `source: "user_input"`.
- Item effect scope and `damage_modifier_status` are included.
- v0.15 item profiles do not change damage numbers.
- Contract guardrails prevent item-effect overclaims.
- v0.16 damage-only items change damage only when explicitly applied.
- Choice Scarf does not create speed-order claims.
- Focus Sash and Leftovers remain excluded from damage estimates.
- Candidate/opponent move damage behavior remains unchanged.

## 16. Out of Scope

Excluded from v0.15:

- Code implementation.
- UI implementation.
- Item input implementation.
- Item damage modifier implementation.
- Legal item scraping.
- Legal item cache generation.
- Choice lock implementation.
- Choice Scarf speed implementation.
- Focus Sash survival implementation.
- Leftovers/Sitrus recovery implementation.
- KO/OHKO/2HKO.
- Speed order.
- Turn Engine.
- Damage/probability engine changes.

## 17. T1/T2 Decisions Needed

- Should v0.16 implement `item_profiles` payload plus a minimal UI, or payload only first?
- Should v0.16 include only attacker-side damage items, or include defender-side `assault-vest` too?
- Should legal item list work be a prerequisite to item UI?
- Should `item_profiles` remain top-level, or should a larger `battle_assumptions` container be introduced before weather/terrain/boosts?
- Should item Korean names come from `data/ko_mapping.json`, a new item mapping file, or a future legal item cache?

# v0.31 Item Effect Coverage Map Design

## 1. Current State

The project now has a Regulation M-A Champions legal item foundation:

- `data/static/champions_legal_items.json` contains 117 legal item entries.
- Category counts are:
  - `hold_item`: 12
  - `type_boosting_item`: 18
  - `berry`: 28
  - `mega_stone`: 59
- `core/champions_item_repository.py` loads and classifies legal items, damage-supported non-legal items, and unknown items.
- `data/static/item_names_ko.json` provides partial Korean display/search mapping.
- `ItemProfileDialog` is repository-backed, searchable, Korean-name aware, and category sorted.
- Normal UI exposes legal item options only.
- Damage-supported non-legal/debug items are hidden from the normal selector.
- `speed_context` now supports user-confirmed Choice Scarf effective Speed in v0.30.

The current fixture already separates local support status:

- `legal_and_damage_supported`: 17 legal items.
- `legal_but_not_modeled`: 100 legal items.
- `damage_supported_non_legal_items`: 5 debug/test items outside normal legal UI.

The existing damage helper/regression path still supports a legacy damage-test subset:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`

However, the normal legal selector does not expose those items because current Champions Reg M-A sources do not confirm them as normal legal items.

## 2. Problem Definition

Item selection and item effect modeling are different concepts.

A legal item can be selected in the UI without its effect being modeled. Conversely, an item effect can exist in the local damage helper while the item is not confirmed as Champions legal. If these concepts are collapsed, the LLM may incorrectly tell T1 that an item effect is calculated just because the item is selected.

The project needs a coverage map so future work can answer:

- Which legal items are recognized but not modeled?
- Which legal items can safely affect damage without a Turn Engine?
- Which items require speed, status, probability, recovery, transform, or turn-order systems?
- Which legacy damage-supported items must remain debug/test-only?
- Which guardrails should the LLM follow for each effect family?

## 3. Coverage Categories

### A. damage_modifier

Damage modifiers are the safest next expansion target because they can often attach to the existing `damage_estimate` helper without modeling turn sequencing.

Examples and candidates:

- Type-boosting items such as `black-belt`, `black-glasses`, `charcoal`, `dragon-fang`, `fairy-feather`, `magnet`, `metal-coat`, `miracle-seed`, `mystic-water`, `never-melt-ice`, `poison-barb`, `sharp-beak`, `silk-scarf`, `silver-powder`, `soft-sand`, `spell-tag`, and `twisted-spoon`.
- `expert-belt` is a conditional damage item, but it is not currently in the normal legal fixture and should remain out unless legal status changes.
- `muscle-band` and `wise-glasses` remain damage-supported-but-unconfirmed in the non-legal/debug section.
- `life-orb`, `choice-band`, and `choice-specs` remain legal mismatch risks.

Current note:

- `items_damage.json` and `advisor/damage/item_modifiers.py` already contain broader item support machinery than the LLM payload currently exposes through normal legal UI.
- The v0.31 design should not turn that dormant support into user-facing behavior.

### B. speed_modifier

Implemented:

- `choice-scarf`
  - Modeled only in `speed_context`.
  - Applied only when the item is user-confirmed.
  - Uses a 1.5 effective Speed modifier.
  - Does not model choice lock.
  - Does not confirm final turn order.

Not implemented:

- `quick-claw`
  - This is not a simple Speed stat modifier.
  - It is closer to activation/probability/turn order.
  - It should not be folded into v0.30-style effective Speed.

### C. survival_modifier

Examples:

- `focus-sash`
- `focus-band`

These require current HP, damage result, survival state, and often turn outcome semantics. They should be designed before implementation. They are not damage modifiers and should not be represented as damage range changes.

### D. recovery_modifier

Examples:

- `leftovers`
- `sitrus-berry`
- other HP or berry recovery items

These require HP thresholds, post-damage state, end-of-turn timing, and consumption tracking. They belong with a future Turn Engine or HP-state layer.

### E. stat_modifier

Examples and candidates:

- `assault-vest`
- `eviolite`
- species-specific stat items if ever legal/relevant

These affect stats before damage calculation. They may require defender-side or attacker-side stat layers and species/form legality checks. Assault Vest is not in the current normal legal fixture, and v0.31 should not add it.

### F. accuracy_evasion_modifier

Example:

- `bright-powder`

Accuracy/evasion affects hit probability, not deterministic damage range. This requires a probability engine or hit chance module, not the current damage estimate helper.

### G. crit_modifier

Example:

- `scope-lens`

Critical-hit effects need probability modeling and may eventually affect expected damage or risk assessment. They should remain recognized-not-modeled until a probability layer exists.

### H. flinch_or_secondary_effect

Examples:

- `kings-rock`
- `razor-fang`, if present in future sources

Flinch/secondary effects require move-hit state, turn order, target action state, and probability. This is Turn Engine territory.

### I. mega_evolution_related

Examples:

- `charizardite-x`
- `venusaurite`
- other Mega Stones

Mega Stones are not simple item effects. They imply species/form transformation, stats, typing, ability, and possibly move compatibility changes. They should not be treated as a minor item modifier.

### J. berry_misc_or_status

Examples:

- `lum-berry`
- type-resist berries
- status-cure or conditional berries

These require status, consumption state, HP thresholds, type-specific conditional checks, or turn sequencing. Some berry damage reduction logic exists in lower-level damage helpers, but v0.31 does not connect it to normal LLM item effects.

### K. unsupported_or_cosmetic_or_unknown

Some legal items may be present for compatibility, transformation, or context but have no current app-level effect. Others may need source review before assigning an effect category. These should remain recognized-not-modeled.

## 4. Coverage Status Model

Recommended coverage status values:

- `modeled`
  - The effect is represented in a payload field and guardrailed.
  - Example: Choice Scarf Speed modifier in `speed_context`.
- `partially_modeled`
  - A narrow effect is modeled, but important side effects are not.
  - Example: future type boost damage could be modeled while broader item caveats remain.
- `recognized_not_modeled`
  - The item is legal and selectable, but the effect is not calculated.
  - Example: Focus Sash, Leftovers, Sitrus Berry, Scope Lens.
- `requires_turn_engine`
  - Needs action order, turn state, consumption, end-of-turn timing, or target action state.
  - Examples: Quick Claw, King's Rock, recovery items.
- `requires_probability_engine`
  - Needs chance modeling.
  - Examples: Bright Powder, Scope Lens, Focus Band.
- `requires_status_engine`
  - Needs status state or status cure modeling.
  - Example: Lum Berry.
- `requires_transform_or_form_engine`
  - Needs species/form transformation.
  - Example: Mega Stones.
- `legal_but_unknown_effect`
  - Legal fixture item whose app effect has not been categorized.
- `damage_supported_but_not_champions_legal`
  - Supported in local helpers or legacy tests, but not normal legal UI.
  - Examples: Choice Band, Choice Specs, Life Orb, Muscle Band, Wise Glasses.

## 5. Current Implemented Effects

### Choice Scarf Speed

Current support:

- Modeled in `speed_context`.
- Applies only when selected item profile is `user_confirmed` and `item_id == "choice-scarf"`.
- Applies a `1.5` effective Speed modifier.
- Keeps raw Speed and effective Speed separate.
- Keeps `is_final_turn_order` as `false`.

Not supported:

- Choice lock.
- Priority.
- Trick Room.
- Tailwind.
- Paralysis.
- Speed stages.
- Ability speed effects.
- Turn Engine state.

### Damage Helper Legacy Items

Current local damage helper support includes:

- Choice Band physical attack modifier.
- Choice Specs special attack modifier.
- Life Orb final damage modifier.
- Muscle Band physical base power modifier.
- Wise Glasses special base power modifier.
- Some type boost item support in `items_damage.json` / `advisor.damage.items`.
- Some defensive/stat/berry mechanics in lower-level damage code.

Important boundary:

- A helper path existing does not mean the item is available in normal legal UI or should be claimed by the LLM.
- Normal UI currently hides the legacy damage-supported non-legal/debug subset.

### Item Selector

The selector is legal-item based:

- It can select legal items.
- Selection does not imply the effect is modeled.
- The payload must remain explicit about whether an effect is applied.

## 6. Non-Legal Damage-Supported Items

| item_id | Local helper support | Champions legal fixture status | Normal UI | Recommended policy |
| --- | --- | --- | --- | --- |
| `choice-band` | Physical damage modifier | `not_legal_or_unconfirmed` | Hidden | Keep debug/test-only unless legal status changes. |
| `choice-specs` | Special damage modifier | `not_legal_or_unconfirmed` | Hidden | Keep debug/test-only unless legal status changes. |
| `life-orb` | Damage modifier | `not_legal_or_unconfirmed` | Hidden | Keep debug/test-only; recoil remains unmodeled. |
| `muscle-band` | Physical modifier | `unconfirmed` | Hidden | Keep out of normal UI; revisit if source confirms legality. |
| `wise-glasses` | Special modifier | `unconfirmed` | Hidden | Keep out of normal UI; revisit if source confirms legality. |

If future Regulations make any of these legal, they should move through the legal fixture first. Only after fixture/source validation should normal UI expose them.

## 7. Legal Item Effect Coverage Map

Representative coverage map:

| item_id | name_en | name_ko source | category | effect_category | current_support_status | next_action | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `choice-scarf` | Choice Scarf | mapping file | hold_item | speed_modifier | modeled | Verify wording polish only | Speed modifier in `speed_context`; choice lock not modeled. |
| `focus-sash` | Focus Sash | mapping file | hold_item | survival_modifier | recognized_not_modeled | Survival design later | Requires HP/damage/turn outcome semantics. |
| `leftovers` | Leftovers | mapping file | hold_item | recovery_modifier | recognized_not_modeled | Recovery design later | Requires end-of-turn HP state. |
| `sitrus-berry` | Sitrus Berry | mapping file | berry | recovery_modifier | recognized_not_modeled | Recovery design later | Requires HP threshold and consumption state. |
| `bright-powder` | Bright Powder | mapping file | hold_item | accuracy_evasion_modifier | recognized_not_modeled | Probability design later | Accuracy/evasion not in current damage estimate. |
| `scope-lens` | Scope Lens | mapping file | hold_item | crit_modifier | recognized_not_modeled | Probability design later | Crit chance not modeled. |
| `kings-rock` | King's Rock | mapping file | hold_item | flinch_or_secondary_effect | recognized_not_modeled | Turn Engine design later | Flinch requires action/turn state. |
| `quick-claw` | Quick Claw | mapping file | hold_item | flinch_or_secondary_effect / priority-like activation | recognized_not_modeled | Turn Engine/probability design later | Not a raw Speed modifier. |
| `black-belt` | Black Belt | mapping file | type_boosting_item | damage_modifier | legal_and_damage_supported | v0.32 candidate | Direct damage modifier candidate. |
| `black-glasses` | Black Glasses | mapping file | type_boosting_item | damage_modifier | legal_and_damage_supported | v0.32 candidate | Direct damage modifier candidate. |
| `fairy-feather` | Fairy Feather | fixture only | type_boosting_item | damage_modifier | recognized_not_modeled | v0.32 source/helper check | Confirm if local catalog supports it before modeling. |
| `metal-coat` | Metal Coat | mapping file | type_boosting_item | damage_modifier | legal_and_damage_supported | v0.32 candidate | Direct damage modifier candidate. |
| `charizardite-x` | Charizardite X | fixture only | mega_stone | mega_evolution_related | recognized_not_modeled | Transform/form design later | Do not treat as simple item modifier. |
| `venusaurite` | Venusaurite | fixture only | mega_stone | mega_evolution_related | recognized_not_modeled | Transform/form design later | Requires species/form/ability/stat changes. |
| `babiri-berry` | Babiri Berry | fixture only | berry | berry_misc_or_status / type-resist | recognized_not_modeled | Defensive berry design later | Requires type-specific conditional and consumption. |
| `lum-berry` | Lum Berry | fixture only | berry | berry_misc_or_status | recognized_not_modeled | Status engine design later | Status cure not modeled. |

The table is representative, not a complete generated coverage file.

## 8. Implementation Priority Proposal

### Priority 1 - Type Boosting Item Damage Modifier

Recommended next target.

Reasons:

- Directly affects `damage_estimate`.
- Does not require Turn Engine state.
- Legal fixture already marks multiple type boosting items as `legal_and_damage_supported`.
- Existing lower-level item catalog has type-boost item data.
- LLM guardrails can reuse `damage_estimate.item_effects`.

Risks:

- Must verify all 17 `legal_and_damage_supported` items are actually wired through the current LLM damage helper.
- Must avoid exposing non-legal legacy items through normal UI.

### Priority 2 - Focus Sash / Survival Design

Important but riskier.

Reasons:

- Very relevant for advice.
- Requires survival semantics and likely current HP integer / damage roll interpretation.

Risks:

- Easy to overclaim KO/OHKO/2HKO or survival.
- Should be designed before implementation.

### Priority 3 - Leftovers / Sitrus Recovery Design

Requires:

- HP state.
- End-of-turn or threshold timing.
- Consumption tracking.
- Turn sequencing.

### Priority 4 - Accuracy / Evasion / Crit / Flinch

Requires:

- Probability engine.
- Hit chance or crit chance model.
- Action order or secondary-effect timing for flinch.

### Priority 5 - Mega Stone / Form Transform

Requires:

- Species/form transform.
- Stat/type/ability changes.
- Possibly legality and team-building rules.

## 9. v0.32 Candidate

### Candidate A - Type Boosting Item Damage Modifier Design

Design exactly how legal type-boosting items should flow from `item_profiles` into `damage_estimate.item_effects`.

Pros:

- Safe next step.
- Can audit all legal type boosting items before implementation.
- Reduces risk of accidentally applying unsupported catalog entries.

### Candidate B - Type Boosting Item Damage Modifier Implementation

Small implementation for legal type boosting items.

Pros:

- Directly improves damage accuracy.
- Uses existing item selector and damage estimate path.

Risks:

- Needs careful source/support audit first.
- Must update contract and tests so LLM only claims applied effects.

### Candidate C - Focus Sash Survival Assumption Design

Design survival semantics.

Pros:

- Strategically important.

Risks:

- Tends toward KO/OHKO/Turn Engine claims.
- Should wait until direct damage item coverage is cleaner.

### T3 Recommendation

v0.32 should be `Type Boosting Item Damage Modifier Design` first, unless T1/T2 explicitly want a very small implementation. The design should enumerate the exact legal type-boost items, confirm local catalog coverage, define payload semantics, and preserve the separation between `legal_and_damage_supported` and actually applied `damage_estimate.item_effects`.

## 10. LLM Guardrail

Required guardrails:

- Do not claim a legal item effect is modeled just because the item is selected.
- Only say an item affected damage when `damage_estimate.item_effects.*.status == "applied"`.
- Only say Choice Scarf affected Speed when `speed_context.*.speed_modifiers` marks it applied.
- If Choice Scarf speed is applied, also say choice lock is not modeled when relevant.
- Do not claim Focus Sash survival, Leftovers/Sitrus recovery, Quick Claw activation, Bright Powder evasion, Scope Lens crit chance, or King's Rock flinch is calculated before those systems exist.
- Do not infer final battle outcome, KO, survival, recovery, or final turn order from item selection.
- Continue to keep `is_final_turn_order == false` semantics for `speed_context`.

## 11. Repository / Data Design

Possible future structures:

### Option A - Separate `item_effect_coverage.json`

Recommended for v0.32+.

Pros:

- Keeps legal source data separate from app modeling coverage.
- Can evolve as the local engine grows.
- Avoids rewriting the full legal fixture for each modeling milestone.

Cons:

- Requires repository merge logic.

### Option B - Add `effect_coverage` into `champions_legal_items.json`

Pros:

- Single source for item UI/coverage metadata.

Cons:

- Legal fixture becomes mixed with implementation state.
- More churn in the large fixture.

### Option C - Repository-only classification helpers

Pros:

- Small code surface.
- Good for derived views.

Cons:

- Harder to review coverage as data.

Recommended repository helpers:

- `classify_effect_support(item_id)`
- `list_items_by_effect_category(effect_category)`
- `list_modeled_items()`
- `list_unmodeled_legal_items()`
- `list_turn_engine_required_items()`
- `list_probability_required_items()`
- `list_damage_supported_non_legal_items()`

v0.31 should not implement these helpers.

## 12. Tests Plan

Future test candidates:

- Choice Scarf is modeled only in `speed_context`.
- Choice Scarf choice lock remains unmodeled.
- Focus Sash remains `recognized_not_modeled`.
- Leftovers remains `recognized_not_modeled`.
- Sitrus Berry remains `recognized_not_modeled`.
- Bright Powder remains `recognized_not_modeled`.
- Scope Lens remains `recognized_not_modeled`.
- King's Rock is classified as requiring Turn Engine / probability.
- Legal type boosting items are recognized as damage modifier candidates.
- Damage-supported non-legal item separation remains intact.
- Normal selector still hides Choice Band, Choice Specs, and Life Orb.
- LLM guardrails forbid claiming unmodeled item effects.
- Existing item selector and speed_context regression tests remain green.

## 13. Out of Scope

This design does not implement:

- Code changes.
- Fixture changes.
- `item_effect_coverage.json`.
- Any new item effect calculation.
- New damage modifiers.
- Focus Sash survival.
- Leftovers/Sitrus recovery.
- Quick Claw activation.
- Bright Powder accuracy/evasion.
- Scope Lens crit chance.
- King's Rock flinch.
- Mega Evolution.
- Turn Engine.
- KO/OHKO/2HKO.
- Damage/probability engine changes.
- UI changes.
- Logs, `.env`, secrets, or handoff updates.

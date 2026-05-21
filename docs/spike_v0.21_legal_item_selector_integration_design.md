# v0.21 - Legal Item Selector Integration Design

## 1. Current v0.20 State

The app currently has two separate item layers.

`ItemProfileDialog` is still the v0.18 minimal selector. It exposes:

- Unknown
- No item
- Choice Band
- Choice Specs
- Life Orb
- Muscle Band
- Wise Glasses

This selector is not a Pokemon Champions legal item selector. v0.20.1 added guidance text that says the list is only a damage-supported subset and that some items may be unconfirmed or differ from the actual Reg M-A legal list.

`data/static/champions_legal_items.json` and `core/champions_item_repository.py` now provide the first legal-item data layer. The fixture is intentionally a sentinel fixture, not the full 117-item Regulation M-A list. It can classify examples such as:

- `choice-scarf`: legal but not modeled
- `focus-sash`: legal but not modeled
- `leftovers`: legal but not modeled
- `sitrus-berry`: legal but not modeled
- `metal-coat`: legal and damage-supported
- `choice-band`: damage-supported but not treated as Champions legal
- `choice-specs`: damage-supported but not treated as Champions legal
- `life-orb`: damage-supported but not treated as Champions legal

There is no repository/UI integration yet. `ItemProfileDialog` does not read `ChampionsItemRepository`, and `MainWindow` does not inject legal item options.

## 2. Problem Definition

Item UX now has three separate concepts that must not be collapsed:

1. **Champions legal item**
   - An item allowed in Pokemon Champions Regulation M-A.

2. **Modeled item**
   - An item whose effect is currently represented in damage estimates.

3. **Debug or damage-test item**
   - An item useful for testing the damage helper but not suitable as a normal Champions selector entry.

These categories overlap only sometimes.

Examples:

- `Choice Scarf` can be legal while speed and choice lock remain unmodeled.
- `Focus Sash` can be legal while survival and turn state remain unmodeled.
- `Leftovers` can be legal while recovery remains unmodeled.
- `Choice Band`, `Choice Specs`, and `Life Orb` can be modeled by the current helper while still being unsafe to present as normal Champions legal items.

If UI integration happens too early, the app can mislead both T1 and Gemini by making modeled-but-likely-illegal items look like normal legal selections, or by making legal-but-not-modeled items look like their effects are calculated.

## 3. Option Comparison

### Option A - Keep Current Selector Only

Keep the current minimal damage-supported selector.

Pros:

- No implementation risk.
- Keeps current damage item regression and T1 testing flow intact.
- The v0.20.1 guidance reduces legal-selector confusion.

Cons:

- T1 cannot select known legal-but-not-modeled items such as Choice Scarf, Focus Sash, Leftovers, or Sitrus Berry.
- The current five damage-supported items still remain visible even though several have legality mismatch risk.
- This does not use `ChampionsItemRepository`.

Assessment: acceptable as a short-term holding pattern, not a real v0.22 integration target.

### Option B - Replace Current Selector with Legal-Only Selector

Replace the current options with entries from `ChampionsItemRepository.list_legal_items()`.

Pros:

- Cleanest normal-user UX.
- Damage-supported-but-not-legal items disappear from normal item selection.
- Legal-but-not-modeled items can be selected as user-confirmed facts while their effects stay not applied.

Cons:

- Current fixture is sentinel-only, so the selector would omit most legal items.
- Current Choice Band / Specs / Life Orb test flow would disappear from normal UI.
- It could create a new false impression: that the sentinel fixture is the full legal list.

Assessment: best long-term direction, but only after the legal fixture is expanded beyond sentinels or the UI is clearly marked as partial/dev.

### Option C - Two-Mode Selector

Provide a Legal Mode and a Damage Test Mode.

Legal Mode:

- Unknown
- No item
- Champions legal items from repository
- Legal-but-not-modeled items are selectable but marked as effect not applied

Damage Test Mode:

- Choice Band
- Choice Specs
- Life Orb
- Muscle Band
- Wise Glasses
- Strong warning that these are not normal Champions legal selector entries

Pros:

- Very explicit separation.
- Preserves current damage modifier testing.
- Makes legal/modeling boundaries visible.

Cons:

- More UI complexity.
- Debug/test controls can distract T1 during normal use.
- Requires careful payload status differences.

Assessment: useful for a developer/debug build, but probably too heavy for the next normal-user step.

### Option D - Legal Selector with Hidden Debug Override

Default UI is legal-only. Damage-supported-but-not-legal items are hidden from normal UI and exposed only through a debug/dev path.

Pros:

- Safest normal UX.
- Keeps development access for item damage helper regression.
- Prevents modeled-but-not-legal items from being treated as standard recommendations.

Cons:

- Requires a debug config or dev-only entry point.
- The hidden override must not leak into normal payloads as `user_confirmed` legal state.

Assessment: best target architecture. For the first implementation, use a legal-only option provider and defer debug override unless T1/T2 explicitly need UI-level damage-item testing.

## 4. Recommended Direction

T3 recommends **Option D as the target architecture** and **Option B as the normal-user implementation shape**, but not until fixture completeness is addressed.

Recommended sequence:

1. Keep v0.18 selector behavior for now, with v0.20.1 warning text.
2. Before replacing the selector, expand `champions_legal_items.json` beyond sentinels or mark any repository-backed UI as partial/dev.
3. Implement an item option provider outside the widget:
   - `ChampionsItemRepository` remains the legal/source layer.
   - `MainWindow` or a thin service builds dialog options.
   - `ItemProfileDialog` receives options; it should not read the repository directly.
4. For normal UI, hide `damage_supported_but_not_champions_legal` items.
5. If needed, expose damage-supported non-legal items only through a debug/test mode, not as regular legal choices.

This preserves the key separation:

```text
legal item != modeled item != debug/test item
```

## 5. Selector UX

### Legal-Only Selector Candidate

Minimum controls:

- Unknown
- No item
- Legal items from `ChampionsItemRepository`

Display examples:

- `Choice Scarf (legal, speed not modeled)`
- `Focus Sash (legal, survival not modeled)`
- `Leftovers (legal, recovery not modeled)`
- `Sitrus Berry (legal, recovery not modeled)`
- `Metal Coat (legal, damage modifier supported)`

Selection behavior:

- `Unknown`: item is unknown; do not assume no item.
- `No item`: T1 confirmed no item.
- `legal_but_not_modeled`: selectable; payload records the item but damage is unchanged.
- `legal_and_damage_supported`: selectable; effect can be applied only if `item_effects` says `applied`.

### Damage Test Item Handling

Damage-supported-but-not-legal items should not appear in normal legal mode:

- Choice Band
- Choice Specs
- Life Orb
- Muscle Band
- Wise Glasses

Possible handling:

- hidden entirely from normal UI
- debug-only checkbox or config flag
- separate advanced section titled "Damage test items"

T3 recommends hiding them from normal UI once a repository-backed legal selector exists. Keep them testable through fixtures/helpers and perhaps a later explicit debug mode.

## 6. Payload Behavior

### Legal but Not Modeled

```json
{
  "status": "user_confirmed",
  "source": "user_input",
  "item_id": "choice-scarf",
  "name_en": "Choice Scarf",
  "name_ko": null,
  "legality_status": "legal",
  "effect_support_status": "legal_but_not_modeled",
  "damage_modifier_status": "not_applied",
  "ui_status": "recognized_not_modeled",
  "notes": [
    "Choice Scarf is legal, but speed order is not modeled.",
    "Choice lock is not modeled."
  ]
}
```

### No Item

```json
{
  "status": "none",
  "source": "user_input",
  "item_id": null,
  "legality_status": "not_applicable",
  "effect_support_status": "not_applicable",
  "damage_modifier_status": "not_applicable"
}
```

### Unknown

```json
{
  "status": "unknown",
  "source": "user_unconfirmed",
  "item_id": null,
  "legality_status": "unknown",
  "effect_support_status": "unknown",
  "damage_modifier_status": "not_applicable"
}
```

### Damage Test Item

```json
{
  "status": "debug_or_legacy_supported",
  "source": "debug_input",
  "item_id": "life-orb",
  "name_en": "Life Orb",
  "legality_status": "not_legal_or_unconfirmed",
  "effect_support_status": "damage_supported_but_not_champions_legal",
  "damage_modifier_status": "applied_if_debug_enabled",
  "ui_status": "damage_test_only",
  "notes": [
    "Life Orb damage modifier is supported by the engine, but it is not treated as a normal Champions legal item.",
    "Life Orb recoil is not modeled."
  ]
}
```

Normal UI should avoid emitting this status. It is appropriate only for explicit debug/test flows.

## 7. Damage Behavior

Rules for future integration:

- `legal_but_not_modeled`: damage unchanged.
- `unknown`: damage unchanged and must not be treated as no item.
- `none`: damage unchanged because T1 confirmed no held item.
- `system_default_none`: damage unchanged because the system assumes no item for calculation compatibility.
- `damage_supported_but_not_champions_legal`: do not apply in normal legal mode.
- Debug/test mode may pass these items to the existing v0.16 helper only if the payload marks them as debug/test and never as normal Champions legal items.

Current v0.16 damage helper behavior can remain unchanged if the UI/service prevents normal legal mode from emitting debug item profiles.

## 8. LLM Guardrails

Future contract updates should preserve these meanings:

- Legal item and modeled item are separate.
- `legal_but_not_modeled` means the item can be user-confirmed, but its effect is not included in damage.
- `damage_supported_but_not_champions_legal` must not be described as a normal Champions legal recommendation.
- Choice Scarf speed is not modeled.
- Focus Sash survival is not modeled.
- Leftovers/Sitrus recovery is not modeled.
- Choice lock is not modeled.
- Life Orb recoil is not modeled.
- Damage can mention item effects only when `damage_estimate.item_effects.*.status == "applied"`.
- Unknown item is not the same as no item.
- `is_final_battle_damage` remains false.

The existing guardrails already cover much of this, but v0.22 should add explicit legal-vs-modeled wording when payloads start carrying `legality_status` and `effect_support_status`.

## 9. Repository Integration Plan

Files investigated:

- `core/champions_item_repository.py`
- `ui/widgets/item_profile_dialog.py`
- `ui/widgets/pokemon_panel.py`
- `ui/main_window.py`
- `llm/advisor_damage_estimate.py`
- `llm/advisor_payload_contract.py`
- `docs/advisor_payload_contract.md`
- `tests/test_champions_item_repository.py`
- `tests/test_item_profile_dialog.py`
- `tests/test_advisor_damage_estimate.py`

Recommended integration boundary:

- `ChampionsItemRepository`
  - Loads and classifies items.
  - Does not know about widgets.

- `MainWindow` or a small service/helper
  - Builds item option records for the active role.
  - Chooses normal legal mode vs debug/test mode.
  - Handles missing repository or incomplete fixture warnings.

- `ItemProfileDialog`
  - Receives item options as constructor data.
  - Emits a selected profile.
  - Does not read `data/static` directly.

- `PokemonPanel`
  - Stores only the selected item profile.
  - Continues resetting item profile on Pokemon change/clear.

Fallback behavior:

- If repository load fails, keep current minimal selector disabled or fall back to Unknown / No item only.
- Do not silently fall back to generic PokeAPI item lists.
- If fixture is sentinel-only, do not present the UI as a full legal selector.

## 10. Fixture Completeness Risk

`champions_legal_items.json` is currently a sentinel fixture. It is useful for classification tests, but not enough for a user-facing full legal selector.

Risks if integrated too early:

- The selector would omit many legal items.
- T1 might assume missing legal items are illegal.
- Gemini could receive incomplete legal item state and overinterpret it.

Before normal legal selector integration, T1/T2 must choose one:

1. Expand fixture to the full 117 legal items.
2. Keep UI as current minimal selector with clearer labels.
3. Create a partial/dev legal selector that visibly says it is incomplete.

T3 recommends option 1 or 2 before a normal user-facing selector. Avoid option 3 unless there is a short-term testing need.

## 11. Tests Plan

Future implementation tests:

- `ItemProfileDialog` receives item options from a service/MainWindow layer.
- `Choice Scarf` is selectable in legal mode when fixture includes it.
- `Choice Scarf` payload has `effect_support_status: "legal_but_not_modeled"`.
- `Focus Sash` payload has `effect_support_status: "legal_but_not_modeled"`.
- `Leftovers` payload has `effect_support_status: "legal_but_not_modeled"`.
- legal-but-not-modeled items do not alter damage.
- damage-supported-but-not-legal items are hidden from normal legal mode.
- debug/test mode exposes damage-supported non-legal items only when explicitly enabled.
- `unknown`, `none`, and `system_default_none` remain distinct.
- repository missing fallback does not use PokeAPI legality.
- sentinel fixture warning is preserved until full fixture exists.
- advisor contract guardrails distinguish legal vs modeled.

## 12. v0.22 Implementation Candidate

### Candidate A - Full Legal Fixture First

Expand `data/static/champions_legal_items.json` to the full 117-item Reg M-A fixture before UI integration.

Pros:

- Safest normal-user path.
- Avoids partial-selector confusion.

Cons:

- Data work is larger.

### Candidate B - Legal Selector with Sentinel Fixture

Connect the repository to ItemProfileDialog using the current sentinel fixture.

Pros:

- Quick.
- Tests repository-driven UI.

Cons:

- Not appropriate for normal use.
- Missing legal items will look unavailable.

### Candidate C - Current Selector Relabeled + Repository-Backed Warnings

Keep the current selector, but use repository classification to label current damage-supported entries as damage-test / not normal legal items.

Pros:

- Safe bridge.
- Improves current UX without claiming completeness.

Cons:

- Still does not let T1 select legal-but-not-modeled items.

### Candidate D - Legal-Only Selector Marked Partial/Dev

Use repository options but visibly mark the selector as partial/dev.

Pros:

- Useful for testing.

Cons:

- Not good for normal play.

T3 recommendation:

- v0.22 should be **Candidate A** if T1/T2 want a real legal selector soon.
- If data expansion should wait, v0.22 should be **Candidate C**: keep current selector but add repository-backed warning/classification and avoid legal-selector claims.
- Do not implement Candidate B as normal UI.

## 13. Out of Scope

Excluded from v0.21:

- code implementation
- UI implementation
- `data/static/champions_legal_items.json` changes
- full legal item fixture creation
- scraping/build script
- item effect additions
- Expert Belt
- Assault Vest
- Choice Scarf speed
- Focus Sash survival
- Leftovers/Sitrus recovery
- Choice lock
- Life Orb recoil
- KO/OHKO/2HKO
- speed order
- Turn Engine
- damage/probability engine modification

## 14. T1/T2 Decisions Needed

- Should v0.22 expand the fixture to all 117 legal items before UI integration?
- Should v0.22 instead keep the current selector and add repository-backed warnings?
- Should sentinel fixture ever be allowed to drive a visible selector, and if so should it be dev-only?
- Should damage-supported-but-not-legal items be hidden entirely from normal UI or kept in debug-only mode?
- Should legal-but-not-modeled items be selectable as `user_confirmed` with `damage_modifier_status: "not_applied"`?
- Should `ItemProfileDialog` options be injected by MainWindow/service rather than read from repository directly?

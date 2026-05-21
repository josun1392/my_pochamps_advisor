# v0.17 - Item UI / Legal Item Selector Design

## 1. Current v0.16 State

v0.16 added item semantics to the advisor payload and damage helper path:

- `item_profiles.my_active`
- `item_profiles.opponent_active`
- default `system_default_none` profiles for both active Pokemon
- `damage_estimate.item_effects`
- attacker-side damage modifiers for:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
  - `muscle-band`
  - `wise-glasses`

Supported attacker-side damage items can now affect:

- my move damage into the opponent
- opponent known move damage into my active Pokemon

However, the app UI still has no way for T1 to choose a held item. `MainWindow._build_llm_battle_input()` currently emits `default_item_profiles_payload()` unconditionally, so real app sessions still assume no item by system default unless a test/helper payload injects item state.

The current item boundaries remain:

- no item UI
- no legal item selector
- no item localization layer
- no legal item source/cache
- no defender-side item effects
- no Choice lock
- no Life Orb recoil
- no speed, survival, recovery, KO chance, or Turn Engine behavior

## 2. Problem Definition

The v0.16 helper can apply selected item damage modifiers, but users cannot set those items in the application.

This creates several practical problems:

- `system_default_none` is treated as the default calculation state, not as user-confirmed no item.
- T1 cannot distinguish "unknown opponent item" from "confirmed no item" in the app.
- T1 cannot mark their own active Pokemon as holding `Choice Band`, `Choice Specs`, `Life Orb`, `Muscle Band`, or `Wise Glasses`.
- Without a legal item selector, a future free-text UI could accept invalid or non-Champions items.
- If unsupported legal items become selectable, the UI must clearly explain that their effects are not modeled.
- Item names may need Korean display names, but the repo currently has item ids and English-ish metadata rather than a full item localization layer.

The key design task is to add a user-facing item selection flow without implying a full item system.

## 3. Option Comparison

### Option A - No Item UI Yet

Pros:

- No new UI complexity.
- Keeps v0.16 helper behavior stable.
- Avoids legal item source uncertainty.

Cons:

- The feature remains test-only.
- T1 cannot use item damage modifiers in real app sessions.
- `unknown`, `none`, and `user_confirmed` remain theoretical in the UI.

### Option B - Minimal Supported Item Selector

Show only the v0.16 supported damage item subset:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`

Pros:

- Smallest useful implementation.
- Low risk.
- Every selectable damage item has known v0.16 behavior.
- Avoids legal item list uncertainty.

Cons:

- Does not represent the full Champions item space.
- T1 cannot record common but unsupported items such as Choice Scarf, Focus Sash, Leftovers, Assault Vest, or utility items.
- May give the impression that only five items exist.

### Option C - Legal Item Selector

Use a Champions legal item list as the selector source:

- supported items apply damage when applicable
- recognized but unsupported items are included as `user_confirmed`
- unsupported item effects are explicitly `not_applied` or `unsupported_item`

Pros:

- Best long-term UX.
- Lets T1 record known item information even when the effect is not modeled.
- Keeps `unknown`, `none`, and `user_confirmed` semantically accurate.
- Scales toward future item work.

Cons:

- Requires a trusted Champions legal item source.
- Needs a legal item cache/schema before implementation.
- Needs clear unsupported-effect UI so the app does not overpromise.

### Option D - Free-Text / Debug Item Input

Pros:

- Very fast to implement.
- Useful for internal testing.

Cons:

- Poor app UX.
- Easy to mistype item ids.
- Hard to explain supported vs unsupported behavior.
- Not appropriate for a user-facing selector.

T3 recommendation: design around Option C, but implement v0.18 as Option B if the Champions legal item source is not ready. This gives a practical fallback without compromising the long-term item model.

## 4. Recommended Direction

Recommended roadmap:

1. v0.17: design `ItemProfileDialog` / selector behavior and legal item cache shape.
2. v0.18: implement the smallest useful item selector.
   - If a reliable legal item list is ready: implement Option C.
   - If not: implement Option B with explicit "supported damage items only" wording.
3. v0.19: add legal item cache/source verification or unsupported legal item UX polish.

The data model should keep:

- top-level `item_profiles` as the source of truth
- `damage_estimate.item_effects` as the per-calculation applied-effect summary
- `damage_estimate.assumption_profile` as the calculation confidence/profile summary

## 5. UI Design Options

### Option UI-A - PokemonPanel Compact Item Selector

Possible shape:

- Add an `Item` button or compact dropdown next to `Stats`.
- Show a short state:
  - `Item`
  - `Item*`
  - `No item`
  - `Unknown`

Pros:

- Close to the active Pokemon identity.
- Fast access for both my and opponent active panels.
- Similar footprint to the current `Stats` button.

Cons:

- PokemonPanel is already dense.
- Dropdowns inside six repeated panels can become visually noisy.
- Harder to show unsupported-effect details inline.

### Option UI-B - ItemProfileDialog

Possible shape:

- Add an `Item` button near `Stats`.
- Open a dialog with:
  - item state selection
  - item search/selector
  - supported/effect status label
  - notes such as "Choice lock not modeled"

Pros:

- Clear place for `unknown`, `none`, and `user_confirmed`.
- Can show supported vs unsupported item effects without crowding the main panel.
- Scales better when legal item list and localization are added.
- Mirrors `StatProfileDialog` while keeping item separate from stats.

Cons:

- One extra click.
- Requires a new dialog and item state model.

### Option UI-C - Combined Profile Dialog

Merge final stats and item state into one profile dialog.

Pros:

- One place for battle assumptions.
- Fewer buttons.

Cons:

- `StatProfileDialog` is already tied to Champions SP/final stat input.
- Items are battle assumptions, not stat inputs.
- Combining them would make the dialog harder to reason about and harder to test.

### Option UI-D - Debug / Manual Input

Pros:

- Quick internal testing.

Cons:

- Not suitable for the app UX.
- Error-prone and hard to localize.

T3 recommendation: use Option UI-B for the long-term design. If v0.18 must stay very small, add a compact `Item` button to PokemonPanel that opens `ItemProfileDialog`; avoid putting the item dropdown directly inside the panel.

## 6. Item State UX

The UI must represent these states distinctly:

| State | Meaning | Damage calculation behavior | LLM meaning |
| --- | --- | --- | --- |
| `unknown` | The item is not known. | Do not assume an item effect. | Do not treat as no item. |
| `none` | User confirmed no held item. | Calculate with no item. | Can say no item is confirmed. |
| `system_default_none` | System default calculation assumes no item. | Calculate with no item. | Must not say user confirmed no item. |
| `user_confirmed` | User selected an item. | Apply supported effects only. | Can mention selected item and whether its effects were modeled. |

Suggested UI copy:

- `Unknown item`
- `No item confirmed`
- `Default: no item assumed`
- `Item selected: Life Orb`
- `Damage applied`
- `Recognized, effect not modeled`

For opponent items, `unknown` is more natural than `system_default_none` once a real UI exists. The current default is acceptable for v0.16 because no item UI exists, but v0.18 should consider shifting user-facing opponent item state to `unknown` until T1 confirms `none` or selects an item.

## 7. Payload / State Flow

Recommended state ownership:

- Store active-slot item state on each `PokemonPanel`, similar to `final_stats`.
- Keep v0.18 scope active-slot only.
- Bench Pokemon item editing remains out of scope.

Recommended `PokemonPanel` additions for v0.18:

- `item_profile: dict | None`
- `set_item_profile(profile: dict | None)`
- `item_profile_requested = Signal(int)` or equivalent signal
- `Item` / `Item*` button state, separate from `Stats`

Payload flow:

1. `ItemProfileDialog` returns one of:
   - `unknown`
   - `none`
   - `user_confirmed` item profile
2. `MainWindow._build_llm_battle_input()` builds:
   - `item_profiles.my_active`
   - `item_profiles.opponent_active`
3. `attach_selected_move_damage_estimate()` uses:
   - attacker item = `item_profiles.my_active`
   - defender item = `item_profiles.opponent_active`
4. `attach_opponent_known_move_damage_estimates()` uses:
   - attacker item = `item_profiles.opponent_active`
   - defender item = `item_profiles.my_active`
5. `damage_estimate.item_effects` records what was actually applied.

Selected Pokemon change policy:

- Minimum v0.18 recommendation: reset item profile when `set_pokemon()` changes the slot's Pokemon.
- Rationale: avoids accidentally carrying Life Orb or Choice Band from one Pokemon to another.
- Later, if team import/persistence exists, item profiles can become slot-specific saved state.

## 8. Legal Item Source / Cache Design

Current repo state:

- `data/static/items.json` exists.
- `data/static/items_damage.json` exists.
- `advisor/damage/items.py` loads `data/static/items_damage.json`.
- `advisor/damage/item_modifiers.py` implements several item modifier paths.
- Existing tests cover item modifier behavior.

Important caveat:

- Existing static item data is useful for metadata/effect categories.
- It is not yet documented as a verified Pokemon Champions legal item list.
- It should not automatically become the UI legal item selector source without a Champions legality audit.

Recommended future legal item cache:

```text
data/static/champions_legal_items.json
```

Proposed schema:

```json
{
  "format": "pokemon_champions",
  "regulation": "M-A",
  "source_kind": "legal_item_list",
  "items": [
    {
      "item_id": "life-orb",
      "name_en": "Life Orb",
      "name_ko": null,
      "source_refs": ["metavgc"],
      "confidence": "third_party_primary",
      "metadata_source": "repo_static_items_damage",
      "effect_model_status": "supported_damage_modifier"
    }
  ],
  "source_refs": {
    "primary": ["MetaVGC or ChampDex legal item list"],
    "cross_check": ["Serebii", "Bulbapedia"],
    "metadata": ["repo static item files", "PokeAPI item metadata if needed"]
  },
  "fetched_at": "YYYY-MM-DD",
  "notes": [
    "This file is a legal item selector source, not proof that all item effects are modeled.",
    "Unsupported legal item effects must remain not_applied unless explicitly implemented."
  ]
}
```

Source candidates to audit before Option C:

- MetaVGC legal item list
- ChampDex held item guide, if available/reliable
- Serebii item/Champions pages, if useful
- Bulbapedia as cross-check
- PokeAPI as item metadata fallback only, not Champions legality source

No scraping or data cache creation should happen in v0.17.

## 9. Supported vs Unsupported Item UX

v0.16 supported damage item subset:

| Item | UI status | Modeled effect | Unmodeled effect |
| --- | --- | --- | --- |
| `choice-band` | Applied damage item | physical damage modifier | choice lock |
| `choice-specs` | Applied damage item | special damage modifier | choice lock |
| `life-orb` | Applied damage item | damage modifier | recoil |
| `muscle-band` | Applied damage item | physical move modifier | none relevant |
| `wise-glasses` | Applied damage item | special move modifier | none relevant |

Unsupported but likely relevant examples:

| Item | UI status | Reason not modeled yet |
| --- | --- | --- |
| `choice-scarf` | Recognized, speed not modeled | speed order system missing |
| `focus-sash` | Recognized, survival not modeled | survival/turn state missing |
| `leftovers` | Recognized, recovery not modeled | Turn Engine missing |
| `sitrus-berry` | Recognized, recovery not modeled | HP threshold/consumption missing |
| `assault-vest` | Recognized, defensive effect not modeled in v0.16 | defender-side item scope deferred |
| `expert-belt` | Recognized, not included in v0.16 first subset | conditional super-effective scope deferred |

The UI should never imply that selecting a legal item means all item effects are modeled.

Recommended dialog copy:

- `Damage modifier applied`
- `Item selected, but this effect is not modeled yet`
- `Choice lock is not modeled`
- `Recoil is not modeled`
- `Speed/recovery/survival effects are not modeled`

## 10. Item Name Localization

Current state:

- Move and Pokemon Korean names already have repo-specific mapping paths.
- Item Korean names are not clearly connected as a full mapping.
- `item_profiles` supports `name_ko`, but v0.16 does not require it.

Recommendation:

- v0.18 may use `item_id` plus `name_en` first.
- `name_ko` should be used when a reliable mapping exists.
- Do not block item selector implementation on Korean item localization.
- Add item Korean names as a later polish milestone if T1 wants it.

Possible future paths:

- `core/item_repository.py`
- `data/static/champions_legal_items.json`
- `data/static/item_ko_names.json`
- PokeAPI item metadata fallback for English names only

## 11. Advisor Payload Contract Update Plan

v0.17 is design-only, so no contract code changes are required yet.

When v0.18 implements selector UI, update:

- `docs/advisor_payload_contract.md`
- `llm/advisor_payload_contract.py`
- prompt guardrails if wording needs more explicit UI semantics

Guardrails to preserve or add:

- `unknown` item is not the same as `none`.
- `system_default_none` means a system calculation assumption, not user confirmation.
- A `user_confirmed` item is not enough to claim an effect was applied.
- Item effects are applied only when `damage_estimate.item_effects.status == "applied"`.
- Unsupported legal item effects must not be described as calculated.
- Choice lock, recoil, speed, recovery, and survival remain unmodeled.
- `is_final_battle_damage` remains `false`.

## 12. Allowed LLM Claims

Allowed:

- "Life Orb damage modifier is applied, but recoil is not modeled."
- "Choice Band damage modifier is applied to physical moves, but choice lock is not modeled."
- "The opponent item is unknown, so actual damage may differ."
- "This item is selected, but its effect is not modeled."
- "The calculation assumes no item by system default."
- "No item is user-confirmed" only when item profile status is `none`.

## 13. Disallowed LLM Claims

Disallowed:

- Treating `unknown` as no item.
- Treating `system_default_none` as user-confirmed no item.
- Claiming unsupported item effects were applied.
- Claiming Choice Scarf determines speed order.
- Claiming Focus Sash guarantees survival.
- Claiming Leftovers/Sitrus recovery is included.
- Claiming Choice lock is modeled.
- Claiming Life Orb recoil is modeled.
- Claiming item effects provide KO/OHKO/2HKO certainty.
- Calling estimates final battle damage.

## 14. Tests Plan

Future implementation tests:

- `ItemProfileDialog` can emit `unknown`.
- `ItemProfileDialog` can emit `none`.
- `ItemProfileDialog` can emit `user_confirmed`.
- Supported item selection updates `item_profiles.my_active`.
- Supported item selection updates `item_profiles.opponent_active`.
- Unsupported legal item selection creates `user_confirmed` profile with effect `not_applied` or `unsupported_item`.
- `unknown` and `none` remain distinct in payload.
- Selected Pokemon change resets item profile in v0.18 minimum policy.
- My active item affects my move damage when supported.
- Opponent active item affects opponent known move damage when supported.
- Candidate moves still receive no `damage_estimate`.
- Existing v0.16 damage item regression tests remain passing.
- Advisor payload contract guardrails remain present.

## 15. Out of Scope

Excluded from v0.17:

- code implementation
- UI implementation
- item selector implementation
- legal item scraping
- legal item cache creation
- data file additions
- new item damage modifiers
- Expert Belt implementation
- Assault Vest implementation
- Choice Scarf speed
- Focus Sash survival
- Leftovers/Sitrus recovery
- Choice lock
- Life Orb recoil
- KO/OHKO/2HKO
- speed order
- Turn Engine
- `advisor/damage/` or `advisor/probability/` engine changes

## 16. T1 / T2 Decisions Needed

Before v0.18 implementation:

1. Choose v0.18 selector scope:
   - Option B: supported five-item selector first.
   - Option C: legal item selector, if legal item source is ready.
2. Decide whether opponent item should default to `unknown` once UI exists.
3. Decide active-slot item reset behavior on Pokemon change.
4. Decide whether `ItemProfileDialog` should be introduced before legal item cache.
5. Decide whether item Korean names are required for v0.18 or can be polish.

T3 recommendation:

- Implement v0.18 with `ItemProfileDialog`.
- If no verified Champions legal item list is ready, start with the v0.16 five supported damage items plus explicit `unknown` and `none` states.
- Keep legal item cache/source verification as v0.19 unless T1/T2 provide a trusted item list first.

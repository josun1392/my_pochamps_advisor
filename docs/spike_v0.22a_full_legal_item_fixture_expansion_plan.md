# v0.22a - Full Legal Item Fixture Expansion Plan

## 1. Current v0.20/v0.21 State

v0.20 introduced the first Pokemon Champions item legality layer:

- `data/static/champions_legal_items.json`
- `core/champions_item_repository.py`
- `tests/test_champions_item_repository.py`

The current fixture is intentionally a sentinel fixture. It is not the full 117-item Regulation M-A legal item list.

Current legal sentinel entries include:

- `choice-scarf`
- `focus-sash`
- `leftovers`
- `sitrus-berry`
- `metal-coat`
- `charcoal`

Current damage-supported non-legal / unconfirmed sentinel entries include:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`

v0.21 established that normal ItemProfileDialog integration should not happen while the fixture is sentinel-only. A user-facing legal item selector needs a much more complete fixture first, otherwise missing legal items could be mistaken for illegal or unsupported items.

## 2. Problem Definition

The next blocker is fixture completeness.

The app has already separated two concepts:

1. **Champions legal item**
   - Item is usable in Pokemon Champions Regulation M-A.

2. **Damage-supported item**
   - Local damage helper can model some effect of the item.

These are independent. Damage-supported items can be illegal or unconfirmed in Champions, and legal Champions items can be unmodeled.

The current sentinel fixture is good for proving repository behavior, but it cannot drive a full legal selector. Before UI integration, v0.22b should expand the fixture toward the complete Regulation M-A item list with consistent source refs, normalized item ids, categories, and effect-support classification.

## 3. Source Strategy

### Primary: MetaVGC

URL: https://metavgc.com/guides/pokemon-champions-format-legal-pokemon-items-moves

Role:

- Primary legal snapshot for Regulation M-A.
- Expected item count reference: 117 allowed items.
- Best first pass for legal yes/no.

Policy:

- If MetaVGC lists the item and no cross-check contradicts it, classify as `legal`.
- Record `source_refs` and fixture-level `fetched_at`.
- Do not infer legality for absent items from generic Pokemon knowledge.

### Cross-check: RotomPicks

URL: https://rotompicks.com/en/items/

Role:

- Category and cross-check source.
- Useful for Hold Items / Mega Stones / Berries grouping.
- Useful future candidate for localized names.

Policy:

- Use for category consistency and count sanity checks.
- If RotomPicks and MetaVGC disagree, keep the item but mark confidence as conflict/unconfirmed until T1/T2 decide.

### Cross-check: Serebii

URL: https://www.serebii.net/pokemonchampions/items.shtml

Role:

- Independent Pokemon Champions item page cross-check.

Policy:

- Use as an additional manual verification source.
- Do not implement scraping in v0.22a/v0.22b unless separately approved.

### Context: ChampDex

URL: https://champdex.com/guides/held-items

Role:

- Explanatory guide for missing/cut held items.
- Especially useful for common main-series items that are absent in Champions, such as Life Orb / Choice Band / Choice Specs.

Policy:

- Use as contextual support, not the sole exact list source.
- Good source for notes explaining why damage-supported-but-non-legal items stay out of normal selector UX.

### Metadata Fallback: PokeAPI and Existing Static Files

Files:

- `data/static/items.json`
- `data/static/items_damage.json`

Role:

- Metadata and local effect-support reference only.
- Useful for `effect_support_status`, not legality.

Policy:

- PokeAPI and generic static item data must not determine Champions legality.
- If an item is legal in Champions but absent from local metadata, keep the legal fixture entry and mark metadata/effect support as missing/not modeled.

## 4. Fixture Expansion Strategy

### Option A - Manual Expansion

Create the full JSON fixture by manually transcribing audited source lists.

Pros:

- Most controlled.
- No parser instability.
- Easy to review line by line.

Cons:

- Slow and error-prone.
- Re-running updates is tedious.

Best use:

- Small sentinel additions.
- Final review of a semi-manual fixture.

### Option B - Semi-Manual Static JSON Expansion

Use source pages as human-audited inputs, then create/edit `data/static/champions_legal_items.json` by hand with spreadsheet/checklist support outside the repo or in a temporary scratch process. Commit only the final JSON fixture and tests.

Pros:

- Good balance of control and speed.
- No scraper/build script is added.
- Keeps v0.22b within static data expansion.
- Allows T1/T2 to review conflicts before UI integration.

Cons:

- Still needs careful proofreading.
- No automated refresh path.

Best use:

- v0.22b.

### Option C - Scraper / Build Script

Add a script to fetch/parse one or more sources and generate the fixture.

Pros:

- Better long-term update workflow.
- Useful when regulations change.

Cons:

- Scope grows quickly.
- Parser brittleness and source policy need more design.
- Current goal explicitly excludes scraping/build scripts.

Best use:

- Later milestone after a stable manual fixture exists.

### Recommended Option

T3 recommends **Option B: semi-manual static JSON expansion** for v0.22b.

Why:

- v0.22b needs data confidence before UI work.
- A scraper/build script is premature.
- Manual-only expansion is possible but more error-prone for 117 entries.
- Semi-manual static expansion keeps the committed artifact simple: fixture + tests only.

## 5. Fixture Schema Plan

Current schema is a good base and should be kept backward-compatible.

Top-level required fields:

- `format`
- `regulation`
- `source_kind`
- `fetched_at`
- `source_refs`
- `notes`
- `items`
- `damage_supported_non_legal_items`

Per legal item required fields:

- `item_id`
- `name_en`
- `name_ko`
- `category`
- `legal`
- `legality_status`
- `legality_confidence`
- `effect_support_status`
- `ui_status`
- `effect_support`
- `notes`

Per damage-supported non-legal item required fields:

- same as legal item fields, but `legal` should be `false`.

Suggested optional fields for v0.22b:

- `source_presence`
  - `metavgc`: true/false/null
  - `rotompicks`: true/false/null
  - `serebii`: true/false/null
  - `champdex`: true/false/null
- `category_source`
- `metadata_source`
- `sort_key`

Do not add optional fields unless they make review easier. If added, update repository validation tests.

## 6. Category Classification Rules

Recommended `category` values:

- `mega_stone`
- `berry`
- `hold_item`
- `type_boosting_item`
- `utility_item`

Recommended secondary effect classifications should stay in `effect_support`, not `category`:

- `damage_modifier`
- `speed_order`
- `survival`
- `recovery`
- `choice_lock`
- `critical_rate`
- `flinch_or_secondary_effect`
- `mega_evolution`
- `status_or_utility`

Category policy:

- Mega Stones should use `mega_stone`, even if they behave like held items.
- Berries should use `berry`.
- Type-boosting regular items should use `type_boosting_item` if the source/category is clear.
- General held items should use `hold_item`.
- Items whose primary role is situational but not damage/speed/recovery can use `utility_item`.

If a source category conflicts:

- Prefer RotomPicks for category shape if the item is listed there.
- Add a note if category differs across sources.
- Keep `category` stable for UI grouping, not as an effect calculation claim.

## 7. Fixture Status Plan

### `legality_status`

Allowed values:

- `legal`
- `not_legal_or_unconfirmed`
- `unconfirmed`
- `source_conflict`
- `not_applicable`

Use:

- `legal`: primary source and at least one cross-check support legality, or T1/T2 approve primary-only legality.
- `unconfirmed`: item appears in a weak/contextual source but not primary source.
- `source_conflict`: sources disagree.
- `not_legal_or_unconfirmed`: damage-supported item that should not appear in normal legal selector.

### `effect_support_status`

Allowed values:

- `legal_and_damage_supported`
- `legal_but_not_modeled`
- `damage_supported_but_not_champions_legal`
- `not_applicable`
- `unknown`

Use:

- `legal_and_damage_supported`: Champions legal and current helper can apply a relevant effect safely.
- `legal_but_not_modeled`: Champions legal but effect should not alter damage.
- `damage_supported_but_not_champions_legal`: local helper supports item but it is not a normal legal selector entry.

### `ui_status`

Allowed values:

- `recognized_modeled`
- `recognized_not_modeled`
- `damage_test_only`
- `hidden_normal_ui`
- `unconfirmed_hidden`

Use:

- `recognized_modeled`: legal and modeled, can appear in normal future selector.
- `recognized_not_modeled`: legal but selected effect is not applied.
- `damage_test_only`: debug/dev only.
- `hidden_normal_ui`: do not show in normal selector.
- `unconfirmed_hidden`: source confidence too low for normal selector.

## 8. Item ID Normalization Rules

Item IDs should match existing repo/PokeAPI-style slugs when possible:

- lowercase
- trim whitespace
- spaces to hyphen
- apostrophes removed or normalized to source/repo style
- punctuation removed unless existing repo item id keeps it
- use ASCII item ids

Examples:

- `Choice Scarf` -> `choice-scarf`
- `Focus Sash` -> `focus-sash`
- `Sitrus Berry` -> `sitrus-berry`
- `Never-Melt Ice` -> `never-melt-ice`
- `King's Rock` -> `kings-rock` if repo uses that id, otherwise match existing metadata id

Mega Stones:

- Use existing repo/PokeAPI-style ids if present.
- Examples:
  - `Charizardite X` -> `charizardite-x`
  - `Charizardite Y` -> `charizardite-y`
  - `Mewtwonite X` -> `mewtwonite-x`
  - `Mewtwonite Y` -> `mewtwonite-y`

Berries:

- Use `*-berry` suffix.
- Examples:
  - `Sitrus Berry` -> `sitrus-berry`
  - `Yache Berry` -> `yache-berry`

Validation plan:

- v0.22b tests should assert no duplicate `item_id`.
- IDs should be sorted or stable.
- Entries should be joinable with `data/static/items.json` / `items_damage.json` where metadata exists, but metadata absence must not remove a legal item.

## 9. Source Conflict Policy

Source mismatch cases:

1. MetaVGC says legal, RotomPicks/Serebii missing
   - Include item as `legal` only if T1/T2 accept MetaVGC as primary.
   - Add note: `Only primary snapshot confirmed this item during v0.22b audit.`

2. RotomPicks/Serebii says legal, MetaVGC missing
   - Use `source_conflict` or `unconfirmed`.
   - Do not show in normal selector until resolved.

3. ChampDex says cut/missing, MetaVGC/RotomPicks list legal
   - Mark `source_conflict`.
   - Add note describing ChampDex contextual disagreement.
   - T1/T2 decision required.

4. Item is damage-supported locally but absent from all Champions sources
   - Keep in `damage_supported_non_legal_items`.
   - `ui_status: "damage_test_only"`.

Confidence values:

- `third_party_cross_checked`
- `primary_snapshot_only`
- `source_conflict`
- `likely_illegal_in_reg_m_a`
- `unconfirmed_absent_from_audited_sources`

## 10. Damage-Supported but Non-Legal Item Policy

Items currently in v0.18 selector:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`

Policy:

- Do not move them into `items` unless current Champions legal sources confirm legality.
- Keep them in `damage_supported_non_legal_items`.
- Keep `ui_status: "damage_test_only"` or `hidden_normal_ui`.
- Normal legal selector must not expose them.
- Debug/dev-only access is acceptable only if clearly marked.

Specific notes:

- `Choice Band`: modeled for physical damage, choice lock not modeled, likely not legal in Reg M-A.
- `Choice Specs`: modeled for special damage, choice lock not modeled, likely not legal in Reg M-A.
- `Life Orb`: modeled for damage, recoil not modeled, likely not legal in Reg M-A.
- `Muscle Band`: modeled for physical move damage, legality unconfirmed/absent from audited lists.
- `Wise Glasses`: modeled for special move damage, legality unconfirmed/absent from audited lists.

## 11. Repository Impact

Current `ChampionsItemRepository` is enough for sentinel classification, but full fixture work may benefit from more list helpers.

Candidate helpers:

- `list_items_by_category(category: str) -> list[dict]`
- `list_selectable_legal_items() -> list[dict]`
- `list_modeled_legal_items() -> list[dict]`
- `list_legal_but_not_modeled_items() -> list[dict]`
- `list_damage_test_items() -> list[dict]`
- `has_full_fixture(expected_count: int = 117) -> bool`
- `fixture_summary() -> dict`

Do not implement these in v0.22a.

v0.22b can add only the helpers needed to test fixture completeness. UI-facing helpers can wait until selector integration.

Repository validation additions for v0.22b:

- expected legal item count or minimum threshold.
- no duplicate item ids.
- required fields on every item.
- category values in allowed set.
- status values in allowed sets.
- source refs preserved.

## 12. Tests Plan

v0.22b fixture tests should include:

- fixture loads.
- `regulation == "m_a"`.
- source refs include MetaVGC, RotomPicks, Serebii, ChampDex.
- legal item count matches expected policy.
- no duplicate item ids across `items` and `damage_supported_non_legal_items`.
- every legal item has required fields.
- every legal item has allowed category.
- every legal item has allowed `legality_status`.
- every legal item has allowed `effect_support_status`.
- every legal item has allowed `ui_status`.
- required legal sentinels remain present.
- common legal-but-not-modeled items remain legal:
  - `choice-scarf`
  - `focus-sash`
  - `leftovers`
  - `sitrus-berry`
- damage-supported non-legal sentinels remain outside legal list:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
- `list_legal_items()` returns only legal entries.
- future helper tests if helpers are added.

Existing regression:

- Existing item damage tests should remain unchanged.
- Legal fixture expansion must not alter damage calculations.

## 13. v0.22b Implementation Candidate

Recommended v0.22b:

```text
v0.22b - Full Legal Item Fixture Expansion
```

Scope:

- Expand `data/static/champions_legal_items.json` toward full 117 legal items.
- Keep `damage_supported_non_legal_items` section.
- Add/strengthen fixture validation tests.
- Add minimal repository helper only if needed for validation.
- Update `docs/PROGRESS.md`.

Excluded:

- UI integration.
- legal selector implementation.
- scraping/build script.
- item effect additions.
- damage/probability engine changes.

Implementation style:

- semi-manual static JSON expansion.
- source audit table/checklist outside committed code is acceptable.
- commit only final fixture/test/docs changes.

Acceptance candidates:

- Strict: exactly 117 legal items in `items`.
- Transitional: at least all Hold Items / Berries / Mega Stones from primary source, with explicit notes if count differs.

T3 recommends T1/T2 decide whether v0.22b requires exact count 117 or an audited minimum threshold. Exact 117 is cleaner for UI readiness.

## 14. Out of Scope

Excluded from v0.22a:

- code implementation
- `data/static/champions_legal_items.json` changes
- fixture expansion implementation
- UI changes
- legal item selector implementation
- scraping/build script
- `data/cache` generation
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

## 15. T1/T2 Decisions Needed

- Should v0.22b require exactly 117 legal items?
- If exact count cannot be verified, what minimum threshold is acceptable?
- Should source conflict items be included as `source_conflict` or excluded until resolved?
- Should `damage_supported_non_legal_items` remain in the same fixture or move to a separate debug/support fixture later?
- Should category values stay coarse for UI grouping or become more granular?
- Should `source_presence` be added per item in v0.22b?
- Should Mega Stones and Berries be sorted/grouped separately in the JSON for review readability?

# v0.19 - Legal Item Source / Selector Design

## 1. Current v0.18 State

v0.18 added a minimal item selector to the app. The current selectable values are:

- Unknown
- No item
- Choice Band
- Choice Specs
- Life Orb
- Muscle Band
- Wise Glasses

The payload already has top-level `item_profiles`:

- `item_profiles.my_active`
- `item_profiles.opponent_active`

The damage estimates already include per-calculation `item_effects`. The v0.16 item helper can apply the current attacker-side damage subset:

- `choice-band`
- `choice-specs`
- `life-orb`
- `muscle-band`
- `wise-glasses`

The current selector is not a Pokemon Champions legal item selector. It is a minimal supported-damage-item selector. It should not be presented as the full Regulation M-A legal item pool.

Current limitations:

- no full legal item source/cache
- no legal item selector
- no unsupported legal item UX
- no legal-vs-modeled distinction in the UI
- no legal item localization layer
- no Choice lock, Life Orb recoil, Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, KO/OHKO/2HKO, or Turn Engine

## 2. Problem Definition

The item system has two separate axes that can easily be confused:

1. **Damage engine support**
   - Items the current helper can apply to damage numbers.
   - Examples: Choice Band, Choice Specs, Life Orb, Muscle Band, Wise Glasses.

2. **Pokemon Champions Regulation M-A legality**
   - Items that are currently legal in Pokemon Champions.
   - This must come from Champions-specific sources, not PokeAPI and not generic main-series memory.

Important findings from source audit:

- MetaVGC's Regulation M-A snapshot lists 117 allowed items and does not list Choice Band, Choice Specs, Life Orb, Muscle Band, or Wise Glasses in the visible allowed-items list.
- ChampDex explicitly says Life Orb, Choice Band, Choice Specs, Assault Vest, Rocky Helmet, and Heavy-Duty Boots are cut from Champions.
- RotomPicks lists 117 legal entries organized as Hold Items 30, Mega Stones 59, and Berries 28. Its visible hold-item list includes Choice Scarf, Focus Sash, Leftovers, type-boosting items, utility items, and others, but not Choice Band / Choice Specs / Life Orb.

Therefore:

- damage-supported does not imply Champions-legal
- Champions-legal does not imply modeled
- PokeAPI item data must not be used as a Champions legality source
- the current v0.18 selector is useful for damage-helper verification but can mislead users if labeled as legal

## 3. Source Candidate Comparison

### A. MetaVGC Legal List

URL: https://metavgc.com/guides/pokemon-champions-format-legal-pokemon-items-moves

Role candidate: primary legal snapshot.

Findings:

- Published/updated April 8, 2026.
- Regulation M-A snapshot.
- Legal Pokemon: 186.
- Allowed items: 117.
- Allowed moves: 467.
- The visible allowed item list includes Choice Scarf, Focus Sash, Leftovers, type-boosting items, berries, Mega Stones, and utility items.
- Choice Band / Choice Specs / Life Orb are not visible in the allowed item list.

Pros:

- Directly frames itself as a Regulation M-A legal Pokemon/items/moves snapshot.
- Compact and easy to manually audit.
- Good primary candidate for a v0.20 fixture.

Risks:

- Third-party source.
- Regulation updates can change the list.
- The page is a snapshot, so `fetched_at` and `source_refs` must be recorded.

### B. RotomPicks Legal Items

URL: https://rotompicks.com/en/items/

Role candidate: structured/category source and localization source.

Findings:

- Regulation M-A legal items page.
- 117 entries.
- Categories: Hold Items (30), Mega Stones (59), Berries (28).
- The visible hold-item list includes type boosters, Choice Scarf, Focus Band, Focus Sash, King's Rock, Leftovers, Light Ball, Mental Herb, Quick Claw, Scope Lens, Shell Bell, White Herb, and others.
- Provides category structure and localized-name affordances.

Pros:

- Structured by item category.
- Useful for selector grouping.
- Useful future source for localized names.

Risks:

- Third-party source.
- Damage calculator support and Champions legality must not be conflated.
- Needs cross-check against MetaVGC and Serebii before becoming sole source of truth.

### C. ChampDex Held Items Guide

URL: https://champdex.com/guides/held-items

Role candidate: explanatory cross-check.

Findings:

- Reg M-A held item guide.
- Says Champions has a smaller item pool.
- Explicitly lists Life Orb, Choice Band, Choice Specs, Assault Vest, Rocky Helmet, and Heavy-Duty Boots as cut from Champions.
- Lists Choice Scarf, Focus Band, Focus Sash, King's Rock, Leftovers, Light Ball, Mental Herb, Quick Claw, Scope Lens, Shell Bell, White Herb, type-boosting items, and berries as available categories/items.

Pros:

- Excellent explanatory guide for why common Showdown/SV items are missing.
- Useful for current v0.18 selector risk assessment.

Risks:

- It describes "held-in-battle items" differently from MetaVGC/RotomPicks total item counts.
- Should not be the only exact legal source.
- Best used as cross-check and explanatory source.

### D. Serebii Pokemon Champions Items

URL: https://www.serebii.net/pokemonchampions/items.shtml

Role candidate: cross-check source.

Findings:

- Dedicated Pokemon Champions item page candidate.
- This goal did not implement scraping.
- The page should be manually/carefully cross-checked during v0.20 fixture construction.

Pros:

- Serebii is a familiar Pokemon reference source.
- Useful independent cross-check for item names and categories.

Risks:

- HTML parsing may need bespoke handling.
- Do not implement scraping in v0.19.

### E. Existing Repo Static Files

Files:

- `data/static/items.json`
- `data/static/items_damage.json`
- `advisor/damage/items.py`
- `advisor/damage/item_modifiers.py`

Role candidate: metadata and effect-support reference, not legality source.

Findings:

- `items_damage.json` includes many main-series item effects and categories.
- `advisor/damage/items.py` loads item effects from `items_damage.json`.
- `advisor/damage/item_modifiers.py` has Q12 helpers for Choice Band, Choice Specs, Life Orb, Muscle Band, Wise Glasses, Expert Belt, type boosters, defensive items, and speed/stat-related items.
- The existing item-effect data is broader than current Champions legality.

Pros:

- Already used by the local damage engine.
- Useful for `effect_support_status`.
- Useful for deciding whether a selected legal item is modeled.

Risks:

- Not a Champions legality source.
- Contains items that may be illegal in Reg M-A.
- Must be joined with a Champions legal cache before UI exposure.

### F. PokeAPI

Role candidate: item metadata fallback only.

Pros:

- May provide generic item ids, names, and descriptions.

Risks:

- Not a Champions legality source.
- Generic historical/main-series item availability is not Regulation M-A legality.

## 4. Legal Item Cache Schema Proposal

Recommended location for a first static fixture:

```text
data/static/champions_legal_items.json
```

Rationale:

- The first implementation should be a curated static fixture, not an automated cache.
- The fixture is app data rather than a transient downloaded cache.
- It can later be generated from a build script if T1/T2 approve scraping or structured import.

Alternative future location:

```text
data/cache/champions/regulation_m_a/legal_items.json
```

Use this only if/when an automated fetch/build pipeline is introduced.

Proposed schema:

```json
{
  "format": "pokemon_champions",
  "regulation": "m_a",
  "source_kind": "third_party_cross_checked",
  "fetched_at": "YYYY-MM-DD",
  "source_refs": [
    {
      "name": "MetaVGC",
      "url": "https://metavgc.com/guides/pokemon-champions-format-legal-pokemon-items-moves",
      "role": "primary_legal_snapshot"
    },
    {
      "name": "RotomPicks",
      "url": "https://rotompicks.com/en/items/",
      "role": "category_and_localization_cross_check"
    },
    {
      "name": "Serebii",
      "url": "https://www.serebii.net/pokemonchampions/items.shtml",
      "role": "cross_check"
    }
  ],
  "items": [
    {
      "item_id": "choice-scarf",
      "name_en": "Choice Scarf",
      "name_ko": null,
      "category": "hold_item",
      "legal": true,
      "legality_confidence": "third_party_cross_checked",
      "effect_support": {
        "damage_modifier": "not_supported",
        "speed_order": "not_supported",
        "survival": "not_applicable",
        "recovery": "not_applicable",
        "choice_lock": "not_supported"
      },
      "ui_status": "recognized_not_modeled",
      "notes": [
        "Legal item candidate.",
        "Speed boost and choice lock are not modeled."
      ]
    },
    {
      "item_id": "choice-band",
      "name_en": "Choice Band",
      "name_ko": null,
      "category": "hold_item",
      "legal": false,
      "legality_confidence": "likely_illegal_in_reg_m_a",
      "effect_support": {
        "damage_modifier": "supported_by_engine",
        "choice_lock": "not_supported"
      },
      "ui_status": "damage_supported_but_not_champions_legal",
      "notes": [
        "Damage modifier is supported by the current helper.",
        "This item appears absent from current Champions Reg M-A legal lists.",
        "Do not expose as a normal legal item until legality is confirmed."
      ]
    }
  ]
}
```

## 5. Item Classification

### A. `legal_and_damage_supported`

Champions legal and currently modeled by the damage helper.

Likely near-term candidates are type-boosting items if they are legal and mapped:

- Black Belt
- Black Glasses
- Charcoal
- Dragon Fang
- Fairy Feather
- Hard Stone
- Magnet
- Metal Coat
- Miracle Seed
- Mystic Water
- Never-Melt Ice
- Poison Barb
- Sharp Beak
- Silk Scarf
- Silver Powder
- Soft Sand
- Spell Tag
- Twisted Spoon

The repo already has type-boost support in `items_damage.json` and `item_modifiers.py`, but implementation coverage should be tested per item before exposing as "applied."

### B. `legal_but_not_modeled`

Champions legal but effect not calculated.

Examples:

- Choice Scarf: legal, but speed order and choice lock are not modeled.
- Focus Sash: legal, but survival/turn state is not modeled.
- Leftovers: legal, but recovery/turn state is not modeled.
- Sitrus Berry: legal, but HP threshold/recovery state is not modeled.
- Quick Claw: legal, but move order is not modeled.
- Scope Lens: legal, but crit-rate behavior is not modeled.
- Mega Stones: legal, but Mega form/activation state must be handled separately.
- Type-resist berries: likely legal, but consumption/trigger state requires careful handling.

UX meaning:

- selectable if T1 wants to record known item information
- `damage_modifier_status: "not_applied"`
- LLM can say "selected but not modeled"
- no damage number should change unless effect support explicitly says applied

### C. `damage_supported_but_not_champions_legal`

Damage helper supports the item, but Champions legality is likely false or unconfirmed.

Current v0.18 risk set:

- Choice Band
- Choice Specs
- Life Orb
- Muscle Band
- Wise Glasses

ChampDex explicitly marks Life Orb / Choice Band / Choice Specs as cut. MetaVGC/RotomPicks visible legal lists also do not show these items. Muscle Band and Wise Glasses also do not appear in the visible MetaVGC/RotomPicks lists.

UX meaning:

- hide from normal legal selector, or
- move to a clearly labeled debug/damage-test section, or
- keep disabled with a warning until legality is confirmed

### D. `illegal_or_excluded`

Not allowed or excluded in current Champions regulation.

UX meaning:

- not shown in normal selector
- optional debug-only if T1/T2 explicitly asks

## 6. Selector UX Design

### Option A - Keep Current 5 Supported Items Only

Pros:

- Smallest change.
- Keeps v0.16/v0.18 tests easy.

Cons:

- Misleading if called a legal selector.
- Current internet audit suggests several current entries are not Champions legal.

Recommendation: acceptable only as a temporary "damage test items" selector.

### Option B - Legal Item List with Disabled Unsupported Items

Pros:

- Safe; users see legality but cannot select unsupported effects.
- Avoids overpromising.

Cons:

- T1 cannot record known unsupported legal items.
- Less useful as a battle note-taking tool.

Recommendation: safe but restrictive.

### Option C - Legal Item List with Selectable Unsupported Items

Pros:

- Best long-term app behavior.
- Lets T1 record a confirmed item even if its effect is not modeled.
- Cleanly separates `legality_status` from `effect_support_status`.
- LLM can say "selected but not modeled."

Cons:

- Requires robust guardrails.
- Requires legal item cache.
- Requires UI to explain applied vs not modeled.

Recommendation: preferred long-term design.

### Option D - Two-Mode Selector

Modes:

- Legal Mode: Champions legal items only.
- Debug / Damage Test Mode: damage-supported but likely illegal items like Choice Band / Life Orb.

Pros:

- Safest way to preserve current helper/debug coverage without misleading T1.
- Makes current v0.18 selector risk explicit.

Cons:

- More UI and state complexity.
- Debug mode should not be prominent in normal use.

Recommendation: strong candidate if T1 wants to keep testing Choice Band / Specs / Life Orb.

### Option E - Search-Based Full Legal Item Selector

Pros:

- Best once the legal item list reaches 117 entries.
- Scales to category filtering.

Cons:

- More UI work.
- Needs repository/cache first.

Recommendation: useful after v0.20 cache/repository.

T3 recommendation: v0.19 should choose Option C as the long-term UX target and Option D as the migration strategy. The next implementation should not expand UI first. It should add a legal item fixture/repository and relabel the current selector so it cannot be mistaken for legal.

## 7. Payload Behavior

### Legal supported item

```json
{
  "status": "user_confirmed",
  "source": "user_input",
  "item_id": "metal-coat",
  "legality_status": "legal",
  "effect_support_status": "supported_damage_modifier",
  "damage_modifier_status": "applied"
}
```

### Legal but not modeled item

```json
{
  "status": "user_confirmed",
  "source": "user_input",
  "item_id": "choice-scarf",
  "legality_status": "legal",
  "effect_support_status": "recognized_not_modeled",
  "damage_modifier_status": "not_applied",
  "notes": [
    "Choice Scarf is selected, but speed order is not modeled."
  ]
}
```

### Damage-supported but not Champions-legal item

```json
{
  "status": "debug_or_legacy_supported",
  "source": "debug_input",
  "item_id": "life-orb",
  "legality_status": "not_legal_or_unconfirmed",
  "effect_support_status": "supported_by_engine",
  "damage_modifier_status": "applied_if_debug_enabled",
  "notes": [
    "Life Orb damage modifier is supported by the engine, but this item appears absent from current Champions legal item sources."
  ]
}
```

### Unknown item

```json
{
  "status": "unknown",
  "source": "user_unconfirmed",
  "item_id": null,
  "legality_status": "unknown"
}
```

### Confirmed no item

```json
{
  "status": "none",
  "source": "user_input",
  "item_id": null,
  "legality_status": "not_applicable"
}
```

### System default no item

```json
{
  "status": "system_default_none",
  "source": "system_default",
  "item_id": null,
  "legality_status": "not_applicable"
}
```

## 8. LLM Guardrail Design

Required guardrails:

- Legal item and modeled item are separate concepts.
- Do not say a damage-supported item is Champions legal unless `legality_status` says legal.
- Do not say a legal item effect is calculated unless `effect_support_status` and `damage_estimate.item_effects` say it was applied.
- If an item is `legal_but_not_modeled`, say it is selected but not modeled.
- If an item is `damage_supported_but_not_champions_legal`, do not present it as a normal Champions recommendation.
- Choice Scarf must not imply speed order until speed/turn-order systems exist.
- Focus Sash must not imply survival until survival/turn state exists.
- Leftovers/Sitrus must not imply recovery until turn state exists.
- `unknown` item must not be treated as `none`.
- `is_final_battle_damage` remains false.

## 9. Data Flow / Repository Design

Recommended modules:

- `core/champions_item_repository.py`
- `core/item_repository.py` if generic metadata lookup grows beyond static helper use

Recommended data:

- `data/static/champions_legal_items.json`
- existing `data/static/items.json` as generic item metadata/effect-support reference only
- existing `data/static/items_damage.json` as effect-support reference only

Repository responsibilities:

- normalize item names to `item_id`
- load legal item entries
- expose `get_legal_item(item_id)`
- expose `list_legal_items(category=None)`
- expose `classify_item(item_id)`
- join legality with local effect-support status
- preserve source refs and confidence
- return clear unavailable/missing-cache state if fixture is absent

Suggested classification return shape:

```json
{
  "item_id": "choice-scarf",
  "name_en": "Choice Scarf",
  "category": "hold_item",
  "legality_status": "legal",
  "effect_support_status": "recognized_not_modeled",
  "ui_status": "selectable_not_modeled"
}
```

## 10. Existing v0.18 Selector Risk Assessment

Risk: the current 5 supported damage items can be mistaken for a Champions legal selector.

Specific risk:

- Choice Band: likely illegal/cut in Reg M-A based on MetaVGC absence and ChampDex cut list.
- Choice Specs: likely illegal/cut in Reg M-A based on MetaVGC absence and ChampDex cut list.
- Life Orb: likely illegal/cut in Reg M-A based on MetaVGC absence and ChampDex cut list.
- Muscle Band: damage helper supports it, but it is not visible in audited legal lists.
- Wise Glasses: damage helper supports it, but it is not visible in audited legal lists.

T3 recommendation:

- Do not expand the current selector as if it were legal.
- In v0.20 or earlier, relabel it to "Damage test items" or "Supported damage modifiers" if it remains visible.
- Prefer hiding likely-illegal damage test items from normal play once a legal item fixture exists.
- Preserve debug/test access only if T1/T2 explicitly wants to keep comparing item modifiers.

## 11. Name Localization

v0.20 can start with `name_en`.

Recommended policy:

- `name_en` required.
- `name_ko` optional and nullable.
- RotomPicks localization can be a future source candidate.
- Korean item mapping should be a later polish milestone.

Do not block legal fixture/repository work on Korean item names.

## 12. Tests Plan

Future tests:

- legal item cache schema validation
- item repository loads `data/static/champions_legal_items.json`
- Choice Scarf classified as `legal_but_not_modeled`
- Focus Sash classified as `legal_but_not_modeled`
- Leftovers classified as `legal_but_not_modeled`
- Choice Band classified as `damage_supported_but_not_champions_legal` unless a source later confirms legality
- Choice Specs classified as `damage_supported_but_not_champions_legal` unless a source later confirms legality
- Life Orb classified as `damage_supported_but_not_champions_legal` unless a source later confirms legality
- legal-but-not-modeled item does not modify damage
- unknown vs none vs system_default_none semantics stay distinct
- selector label does not imply current 5 damage-supported items are Champions-legal
- contract guardrails distinguish legal vs modeled

## 13. v0.20 Implementation Candidate

Options:

### A. Legal item cache fixture + repository only

Pros:

- Safest.
- Establishes truth layer before UI changes.
- Testable without disrupting current app.

Cons:

- No immediate UI change.

### B. Legal item cache fixture + current selector relabeling

Pros:

- Fixes current UX risk quickly.
- Still keeps implementation small.

Cons:

- Does not yet provide full legal selector.

### C. Legal item cache fixture + ItemProfileDialog integration

Pros:

- Most useful app-facing step.

Cons:

- Bigger UI and state change.
- Needs careful supported vs unsupported messaging.

### D. Source scraper/build script

Pros:

- Better long-term update path.

Cons:

- Too early.
- Scraping policy and parser stability are unresolved.

### E. Keep current 5-item UI + warning label only

Pros:

- Very small.

Cons:

- Leaves core legal-source gap.

T3 recommendation: v0.20 should be A or B. Start with a hand-curated `data/static/champions_legal_items.json` fixture and a `ChampionsItemRepository`. If T1 wants immediate UX cleanup, combine it with relabeling the current v0.18 selector to "Supported damage modifiers" or "Damage test items."

## 14. Out of Scope

Excluded from v0.19:

- code implementation
- UI implementation
- legal item cache creation
- scraping
- item effect additions
- Expert Belt
- Assault Vest
- Choice Scarf speed
- Focus Sash survival
- Leftovers recovery
- Sitrus Berry recovery
- Choice lock
- Life Orb recoil
- KO/OHKO/2HKO
- speed order
- Turn Engine
- damage/probability engine modification

## 15. T1/T2 Decisions Needed

- Should v0.20 be legal item cache fixture + repository only, or include ItemProfileDialog integration?
- Should current v0.18 damage-supported items stay visible, be relabeled as "Damage test items", or be hidden once legal fixture exists?
- If Choice Band / Choice Specs / Life Orb remain likely illegal, should they become debug-only?
- Should MetaVGC be the primary legal snapshot with RotomPicks/Serebii cross-check required?
- Should the legal fixture live at `data/static/champions_legal_items.json` or `data/cache/champions/regulation_m_a/legal_items.json`?
- Should unsupported-but-legal items be selectable or disabled?
- Should v0.20 use `name_en` only, with `name_ko` deferred?
- Should Mega Stones, Berries, and regular held items share one selector with categories?
- Should scraping/build scripts remain out of scope for v0.20?

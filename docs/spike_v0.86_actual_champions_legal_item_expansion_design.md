# v0.86 Actual Champions Legal Item Expansion Design

## Current State

The legal item gate now uses `data/static/champions_legal_items.json` as the source of truth for user-facing modeled item contexts.

v0.85.1 verified that blocked/future-only item silence passes local Gemini verification:

- Loaded Dice is blocked by Champions legal coverage and stays silent in default advice.
- Power Herb remains blocked and has no `charge_context`.
- Blocked item names, effects, `not modeled` wording, `effect not included` wording, and generic blocked item limitations stayed out of default advice.

Current modeled legal item contexts:

- type boosting item damage modifier:
  - `black-belt`
  - `black-glasses`
  - `charcoal`
  - `dragon-fang`
  - `hard-stone`
  - `magnet`
  - `metal-coat`
  - `miracle-seed`
  - `mystic-water`
  - `never-melt-ice`
  - `poison-barb`
  - `sharp-beak`
  - `silk-scarf`
  - `silver-powder`
  - `soft-sand`
  - `spell-tag`
  - `twisted-spoon`
- `choice-scarf` / `speed_context`
- `focus-sash` / `survival_context`
- `sitrus-berry` / `recovery_context`
- `leftovers` / `recovery_context`
- `bright-powder` / `accuracy_context`
- `scope-lens` / `critical_context`
- `kings-rock` / `flinch_context`

Loaded Dice remains implemented as future-only `multi_hit_context` support, but it is absent from `data/static/champions_legal_items.json` and is blocked by legal coverage.

Power Herb remains blocked. `data/static/charge_moves.json` is move metadata and does not establish Power Herb legality.

## Legal Item Inventory

`data/static/champions_legal_items.json` reports:

- total legal items: 117
- hold items: 30
- mega stones: 59
- berries: 28
- damage-supported non-legal items: 5

Inventory classification:

| Classification | Count | Notes |
|---|---:|---|
| `modeled_by_generic_damage_item` | 17 | legal type boosting items with local damage modifier support |
| `already_modeled` | 7 | legal item contexts already modeled outside generic type boosting |
| `legal_unmodeled` | 34 | non-Mega legal items without modeled user-facing context |
| `not_relevant_to_turn_advice` | 59 | Mega Stones; important legal items, but outside current one-turn item-context track |
| `blocked_or_not_legal` | n/a | absent from Champions legal fixture; includes Loaded Dice, Power Herb, Choice Band, Choice Specs, Life Orb, Muscle Band, Wise Glasses, Expert Belt, Eviolite, Assault Vest, Rocky Helmet, Black Sludge |

### Modeled by Generic Damage Item

These are legal and currently damage-modeled through the generic type boosting item path:

- `black-belt`
- `black-glasses`
- `charcoal`
- `dragon-fang`
- `hard-stone`
- `magnet`
- `metal-coat`
- `miracle-seed`
- `mystic-water`
- `never-melt-ice`
- `poison-barb`
- `sharp-beak`
- `silk-scarf`
- `silver-powder`
- `soft-sand`
- `spell-tag`
- `twisted-spoon`

### Already Modeled Context Items

These are legal and have user-facing modeled contexts:

| Item | Context | User-facing allowed? |
|---|---|---|
| `choice-scarf` | `speed_context` | yes, limited raw/effective Speed context |
| `focus-sash` | `survival_context` | yes, limited survival context |
| `sitrus-berry` | `recovery_context` | yes, limited recovery context |
| `leftovers` | `recovery_context` | yes, limited recovery context |
| `bright-powder` | `accuracy_context` | yes, limited hit reliability context |
| `scope-lens` | `critical_context` | yes, limited critical-hit context |
| `kings-rock` | `flinch_context` | yes, limited flinch pressure context |

### Legal Unmodeled Non-Mega Items

Legal non-Mega items without modeled context:

- `fairy-feather`
- `focus-band`
- `light-ball`
- `mental-herb`
- `quick-claw`
- `shell-bell`
- `white-herb`
- status / PP / recovery berries:
  - `aspear-berry`
  - `cheri-berry`
  - `chesto-berry`
  - `leppa-berry`
  - `lum-berry`
  - `oran-berry`
  - `pecha-berry`
  - `persim-berry`
  - `rawst-berry`
- type-resist berries:
  - `babiri-berry`
  - `charti-berry`
  - `chilan-berry`
  - `chople-berry`
  - `coba-berry`
  - `colbur-berry`
  - `haban-berry`
  - `kasib-berry`
  - `kebia-berry`
  - `occa-berry`
  - `passho-berry`
  - `payapa-berry`
  - `rindo-berry`
  - `roseli-berry`
  - `shuca-berry`
  - `tanga-berry`
  - `wacan-berry`
  - `yache-berry`

### Not Relevant to Current Turn Advice Track

The 59 legal Mega Stones are legal inventory, but they are not a good next item-context candidate for the current one-turn advisor path because Mega Evolution mechanics, species/form changes, ability changes, stat changes, timing, and UI state are not represented in the current item context system.

### Blocked or Not Legal

Items excluded from v0.86 expansion because they are absent from `data/static/champions_legal_items.json`:

- `loaded-dice`
- `power-herb`
- `choice-band`
- `choice-specs`
- `life-orb`
- `expert-belt`
- `muscle-band`
- `wise-glasses`
- `eviolite`
- `assault-vest`
- `rocky-helmet`
- `black-sludge`

Some of these appear in `data/static/items.json` or `data/static/items_damage.json`, but those files are metadata/effect support sources, not Champions legal coverage.

## Existing Modeled Items

Existing item context rules:

- Legal gate:
  - modeled user-facing item context requires presence in `data/static/champions_legal_items.json`
  - `items.json` alone is not legal coverage
  - `items_damage.json` alone is not legal coverage
- Generic type boosting damage modifier:
  - directly changes damage only when the legal user-confirmed item matches the move type and `damage_estimate.item_effects.attacker_item.status=applied`
- `choice-scarf`:
  - limited Speed context
  - no final turn order
  - no choice lock simulation
- `focus-sash`:
  - limited survival context
  - no multi-hit, hazards, chip, or exact turn sequencing
- `sitrus-berry` / `leftovers`:
  - limited recovery context
  - no exact activation timing, item consumption, or turn sequencing
- `bright-powder`:
  - limited hit reliability context
  - no final hit probability or hit-adjusted KO probability
- `scope-lens`:
  - limited critical-hit context
  - no final crit probability or crit-adjusted KO probability
- `kings-rock`:
  - limited flinch pressure context
  - no final flinch probability or flinch-adjusted outcome probability

## Candidate Expansion Areas

### A. Damage Modifier Items

Legal fixture findings:

- Generic type boosting items are already covered except `fairy-feather`.
- `choice-band`, `choice-specs`, `life-orb`, `expert-belt`, `muscle-band`, and `wise-glasses` are not in the Champions legal fixture.

Candidate:

- `fairy-feather`
  - legal fixture: present
  - `items_damage.json`: absent
  - likely small as a type boosting gap, but implementing it changes raw damage and requires damage catalog update
  - better as a targeted damage catalog coverage task, not the next limited context design

Do not recommend:

- Choice Band / Choice Specs / Life Orb / Expert Belt / Muscle Band / Wise Glasses
  - absent from Champions legal fixture
  - must remain excluded unless legal coverage changes

### B. Defensive / Survival Items

Legal fixture findings:

- `focus-band` is legal but unmodeled.
- Type-resist berries are legal and listed in `items_damage.json` under `type_resist_berries`.
- `eviolite` and `assault-vest` are absent from the Champions legal fixture.

Candidate:

- Type-resist berries as limited `resist_berry_context` / `survival_context` extension.

Why promising:

- legal fixture: present for 18 type-resist berries
- repo metadata: present in `data/static/items_damage.json`
- can be additive context like Focus Sash
- can avoid changing raw damage and `ko_context` in the first implementation
- user-facing value is high: warns that incoming super-effective damage may be mitigated under limited assumptions

Needs careful design:

- trigger condition and item consumption
- whether to require incoming move type matching the berry
- whether to require super-effective damage
- exact damage reduction amount
- no final survival/KO truth before Turn Engine

Do not recommend now:

- `focus-band`
  - proc/survival chance creates final probability temptation
  - no repo metadata in current inspected fixtures
- Eviolite / Assault Vest
  - absent from legal fixture

### C. Recovery / Residual Items

Legal fixture findings:

- `shell-bell` is legal but unmodeled.
- `oran-berry` is legal but unmodeled.
- `black-sludge` is absent from the Champions legal fixture.

Candidate:

- `shell-bell`
  - legal fixture: present
  - repo metadata: not present in inspected `items.json` / `items_damage.json`
  - could be limited recovery context but depends on damage dealt and exact post-hit recovery behavior
  - less repo-backed than type-resist berries

Do not recommend now:

- `black-sludge`
  - absent from Champions legal fixture
- pinch berry style work
  - no clear current candidate from the inspected legal fixture beyond existing Sitrus/Oran style recovery

### D. Accuracy / Evasion / Crit / Flinch Related

Already modeled:

- `bright-powder`
- `scope-lens`
- `kings-rock`

Legal fixture does not show an obvious additional item in this family that is safer than resist berries.

### E. Choice Item Family

Legal fixture findings:

- `choice-scarf` is legal and already has `speed_context`.
- `choice-band` and `choice-specs` are not in the Champions legal fixture.

Policy:

- Do not design Choice Band / Choice Specs user-facing contexts until Champions legal coverage exists.
- Choice lock remains out of scope for current limited contexts without a Turn Engine.

## Recommended Next Candidate

Recommend:

`v0.87 - Type-resist Berry Limited Survival Context Design`

Rationale:

- Type-resist berries are present in `data/static/champions_legal_items.json`.
- Type-resist metadata exists in `data/static/items_damage.json`.
- The family has clear tactical value in advice.
- The first design can keep raw damage rolls and `ko_context` unchanged.
- It can be expressed as limited context:
  - may reduce incoming damage of a matching type
  - raw damage estimate is unchanged
  - `ko_context` is unchanged
  - berry trigger, item consumption, exact reduction, multi-hit interaction, ability/weather interaction, and turn sequencing are not modeled
- The family is safer than:
  - Shell Bell, which lacks repo metadata and depends on damage-dealt recovery
  - Focus Band / Quick Claw, which create probability/order temptation
  - Light Ball, which changes stats/damage and requires species-specific stat integration
  - Fairy Feather, which is a damage catalog gap rather than a limited context

Alternative:

`v0.87 - Fairy Feather Damage Catalog Gap Design`

Use this only if T1/T2 prefer a narrow damage modifier coverage task. It is legal, but it directly changes raw damage when implemented and therefore needs more damage-regression attention.

## Policy

Maintain:

- Do not recommend items absent from `data/static/champions_legal_items.json`.
- Do not treat `items.json` as legal coverage.
- Do not treat `items_damage.json` as legal coverage.
- Keep Loaded Dice blocked/future-only.
- Keep Power Herb blocked.
- Do not use external research in this pass.
- Do not mutate legal fixtures without explicit approval and evidence.
- Do not expose future-only or blocked item effects in default advice.

## Proposed v0.87 Path

Preferred:

### v0.87 - Type-resist Berry Limited Survival Context Design

Scope:

- design a legal, additive limited context for the 18 type-resist berries
- use `data/static/champions_legal_items.json` for legal coverage
- use `data/static/items_damage.json` `type_resist_berries` metadata as the repo-native effect source
- keep raw damage and `ko_context` unchanged in the first implementation plan
- exclude exact item consumption, exact reduction integration, multi-hit interaction, ability/weather interaction, and Turn Engine

Fallback:

### v0.87 - Handoff Capsule Update

Use this if T1/T2 want to pause feature expansion after the item context run and capture current policy state.

## Out of Scope

This v0.86 design excludes:

- code implementation
- legal fixture mutation
- Loaded Dice legal addition
- Power Herb `charge_context`
- external web research
- damage formula change
- raw damage roll modification
- KO context modification
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

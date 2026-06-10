# v1.1 Next Legal Item Context Candidate Design

## Current State

The current advisor already has additive item/advice contexts for:

| Context | Implemented scope |
| --- | --- |
| `survival_context` | Focus Sash and Focus Band limited survival context |
| `recovery_context` | Sitrus Berry and Leftovers limited recovery context |
| `accuracy_context` | Bright Powder limited hit-reliability context |
| `critical_context` | Scope Lens limited critical-hit context |
| `flinch_context` | King's Rock limited flinch-pressure context |
| `multi_hit_context` | Loaded Dice future-only support, currently blocked by legal coverage |
| `resist_berry_context` | 17 standard type-resist berries; Chilan Berry remains deferred |
| `type_boost_context` | 17 Champions legal, metadata-supported type-boosting items |
| `speed_context` | raw/effective Speed comparison, including Choice Scarf effective Speed |
| `speed_order_context` | Quick Claw limited move-order context |

The v1.0 registry cleanup centralizes default advice filtering:

- `available=true` item contexts remain in the default Gemini advice payload.
- `available=false`, blocked, deferred, unsupported, unconfirmed, and missing-metadata item contexts are hidden from default advice.
- debug/enriched payloads may retain unavailable reasons.
- raw `damage_estimate`, raw rolls, Q12 modifiers, and `ko_context` are not item-context filtering surfaces.

This v1.1 spike looks for the next Champions-legal item context candidate without changing mechanics.

## Legal Item Inventory Summary

`data/static/champions_legal_items.json` currently reports:

| Category | Count | Notes |
| --- | ---: | --- |
| all legal items | 117 | Regulation M-A legal fixture count |
| hold items | 12 | 8 already modeled by limited contexts; 4 unmodeled |
| berries | 28 | Sitrus plus 17 standard resist berries modeled; Chilan and 9 utility berries unmodeled/deferred |
| type-boosting items | 18 | 17 modeled by `type_boost_context`; Fairy Feather lacks local damage metadata |
| Mega Stones | 59 | legal, but require Mega Evolution mechanics and form/state handling |

Already modeled legal non-Mega items include:

- Bright Powder
- Choice Scarf
- Focus Band
- Focus Sash
- King's Rock
- Leftovers
- Quick Claw
- Scope Lens
- Sitrus Berry
- 17 standard type-resist berries except Chilan Berry
- 17 metadata-supported type-boosting items except Fairy Feather

Blocked or not-legal items remain excluded from new candidate selection. Loaded Dice and Power Herb stay blocked/future-only because they are not confirmed by the Champions legal fixture.

## Remaining Legal Non-Mega Candidates

| Item id | Champions legal | Existing context overlap | Needed mechanics | Limited context could safely say | Gemini overstatement risk | Difficulty | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `light-ball` | yes | no direct advice context; existing damage helpers support Pikachu species-stat modifier | holder species must be Pikachu; attacking category; already-supported item modifier audit | user-confirmed Light Ball may affect Pikachu's offensive stat modifier when local damage metadata applies; not final battle truth | medium: model may overstate KO certainty or imply non-Pikachu support | small/medium | recommended next candidate |
| `fairy-feather` | yes | overlaps with `type_boost_context` concept | missing local `items_damage.json` type-boost metadata/support | no safe user-facing modeled context until catalog-backed Fairy modifier exists | medium: would look like supported type boost despite missing metadata | low for design, not for implementation | deferred until metadata/support pass |
| `mental-herb` | yes | none | status/volatile condition recognition, trigger timing, item consumption, Turn Engine | at most future utility context; not useful for current damage advice without state | high: may imply a status condition is removed | medium/high | deferred |
| `white-herb` | yes | none | stat stage tracking, negative stat drops, trigger timing, item consumption, Turn Engine | at most future stat-drop reset context | high: may infer stat drops and current battle state | high | deferred |
| `shell-bell` | yes | partial conceptual overlap with `recovery_context` | damage dealt, post-hit recovery, item consumption/timing, Turn Engine | could mention possible post-hit recovery only after damage-dealt integration exists | high: may imply final survival or 2HKO changes | high | deferred |
| `oran-berry` | yes | overlaps with `recovery_context` | HP threshold, exact current/max HP, item consumption, Turn Engine | low-value fixed recovery context only if HP state is precise | medium/high | medium | deferred |
| `aspear-berry` | yes | none | freeze status, trigger state, item consumption | status-curing item only with current status state | high | medium | deferred |
| `cheri-berry` | yes | none | paralysis status, trigger state, item consumption; speed interaction if cured | status-curing item only with current status state | high | medium | deferred |
| `chesto-berry` | yes | none | sleep status, trigger state, item consumption | status-curing item only with current status state | high | medium | deferred |
| `leppa-berry` | yes | none | PP state, move selection, item consumption | PP restoration only with actual PP tracking | high | medium | deferred |
| `lum-berry` | yes | none | status/confusion state, trigger state, item consumption | broad status-curing item only with actual status state | high | medium/high | deferred |
| `pecha-berry` | yes | none | poison status, trigger state, item consumption | status-curing item only with current status state | high | medium | deferred |
| `persim-berry` | yes | none | confusion state, trigger state, item consumption | confusion-curing item only with current confusion state | high | medium | deferred |
| `rawst-berry` | yes | none | burn status, trigger state, item consumption; attack-halving interaction if modeled | status-curing item only with current status state | high | medium | deferred |
| `chilan-berry` | yes | overlaps with `resist_berry_context`, but special `always_resist=true` Normal case | special non-super-effective trigger policy, item consumption, exact handling | could be a future Chilan-specific limited resist context | medium: previous Gemini leaks showed deferred reasons need filtering | medium | deferred |
| Mega Stones | yes | no current context | Mega Evolution, species/form compatibility, stat/form changes, ability changes, timing | no safe limited context without a Mega subsystem | high | high | not relevant to current turn-advice context |

## Candidate Area Assessment

### Species-stat Item Context

`items_damage.json` contains `species_stat_items.light-ball`:

- species: `pikachu`
- stats: `atk`, `spa`
- multiplier: 8192

`advisor.damage.item_modifiers.attack_stat_item_mod()` already contains Light Ball support for Pikachu. This makes Light Ball different from most remaining legal items: repo metadata and damage helper behavior already exist.

A limited `species_stat_item_context` could be analogous to `type_boost_context`:

- only when item is user-confirmed
- only when Champions legal fixture confirms the item
- only when local metadata and helper support exist
- only when holder species matches `pikachu`
- only as an explanatory context for already-supported damage modifier behavior
- no new damage formula path
- no raw roll change beyond existing damage engine behavior
- no new `ko_context`, OHKO, or 2HKO integration

This is the best v1.2 candidate because it has legal coverage, repo metadata, and existing helper support. The implementation risk is mostly Gemini wording, not battle-mechanics complexity.

### Unsupported Type-boost Gap

Fairy Feather is legal and categorized as a type-boosting item, but it currently lacks local damage metadata/support. It should not be modeled as `type_boost_context` until a separate metadata/support pass adds a catalog-backed Fairy modifier.

### Utility Herb / Status Berry Items

Mental Herb, White Herb, and status berries need current volatile/status/stat-stage state and item consumption. They are poor immediate candidates because current payloads do not include enough battle-state truth to avoid hallucinated triggers.

### Recovery-like Items

Shell Bell and Oran Berry conceptually overlap with `recovery_context`, but both need trigger timing and item consumption. Shell Bell also needs damage dealt and post-hit recovery integration. They should remain deferred until a recovery/state design pass.

### Mega Stones

Mega Stones are legal but require form evolution, species compatibility, stat/form changes, abilities, and turn/state handling. They are not good limited advice context candidates before a Mega subsystem design.

## Recommended v1.2 Candidate

Recommended:

**v1.2 - Light Ball Limited Species-stat Advice Context**

Proposed context name:

- `species_stat_item_context`

Initial scope:

- Light Ball only
- attacker-side item only
- item profile must be `status: user_confirmed`
- item must pass Champions legal fixture gate
- holder species must normalize to `pikachu`
- local `items_damage.json` metadata must contain `species_stat_items.light-ball`
- context is available only for damaging moves whose category can use Atk or SpA
- default advice payload keeps only `available=true`
- default advice payload hides species mismatch, unsupported metadata, blocked, or unconfirmed reasons
- debug/enriched payload may retain unavailable reasons

Allowed wording:

- "Light Ball may affect Pikachu's offensive stat modifier when the local damage estimate applies the supported item modifier."
- "This is limited item context and not final battle truth."
- "Raw `ko_context` remains based on the provided damage rolls."

Forbidden wording:

- "guarantees KO"
- "confirmed KO"
- "final damage"
- "always doubles damage"
- "works for any holder"
- "proves the KO"
- "changes final KO probability"

Implementation note:

The context should surface existing legal + metadata + helper support. It should not add a new damage formula path, alter Q12 constants, alter raw rolls, or create Light-Ball-adjusted KO/OHKO/2HKO context.

If T1/T2 want one more design gate before implementation, v1.2 can be a focused `Light Ball Limited Species-stat Context Design` instead of immediate implementation.

## Deferred Candidates

| Candidate | Deferred reason |
| --- | --- |
| Fairy Feather | legal but local damage metadata/helper support is missing |
| Mental Herb | requires volatile/status condition state and item consumption |
| White Herb | requires stat-stage tracking and item consumption |
| Shell Bell | requires damage-dealt recovery, timing, and item consumption |
| Oran Berry | requires HP threshold and item consumption; lower value than Sitrus |
| status berries | require current status/confusion/PP state and item consumption |
| Chilan Berry | special Normal-type resist semantics; previous deferred leakage makes it better as a separate focused pass |
| Mega Stones | require Mega Evolution mechanics, form changes, ability/stat changes, and Turn Engine-like state |
| Loaded Dice | blocked/future-only until Champions legal coverage is confirmed |
| Power Herb | blocked until Champions legal coverage is confirmed |

## Test Plan For v1.2

If Light Ball is selected:

- user-confirmed Light Ball + Pikachu + physical move -> context available
- user-confirmed Light Ball + Pikachu + special move -> context available
- user-confirmed Light Ball + non-Pikachu -> context unavailable and hidden from default advice payload
- unknown/unconfirmed Light Ball -> context unavailable and hidden
- non-legal/debug species-stat item -> hidden from default advice payload
- debug/enriched payload retains reason
- default advice payload does not leak unavailable item name/reason through `item_profiles` or `damage_estimate.item_effects`
- existing type-boost item context remains unchanged
- existing Choice Scarf `speed_context` remains unchanged
- raw damage formula unchanged
- raw damage rolls unchanged
- Q12 constants unchanged
- `ko_context` unchanged
- no Light-Ball-adjusted KO/OHKO/2HKO context
- full pytest

## Policy

Maintain these rules:

- Champions legal fixture is required for user-facing modeled item context.
- `items_damage.json` alone is not legal coverage.
- Existing helper support alone is not legal coverage.
- Default advice payload includes only available legal contexts.
- Unavailable/deferred/blocked reasons remain debug/enriched metadata only.
- No recommendation may rely on unconfirmed item state.
- No final KO probability, final move order, final survival truth, item consumption, or Turn Engine behavior is inferred.

## Out of Scope

This v1.1 design excludes:

- code implementation
- new item context implementation
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` calculation changes
- speed calculation changes
- final move order calculation
- final KO probability calculation
- Turn Engine
- item consumption tracking
- legal fixture mutation
- fixture mutation
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

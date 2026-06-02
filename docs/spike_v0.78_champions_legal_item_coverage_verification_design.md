# v0.78 Champions Legal Item Coverage Verification Design

## Current State

The advisor now has several item-related context layers:

- Charcoal type-boosting damage modifier
- Choice Scarf `speed_context`
- Focus Sash `survival_context`
- Sitrus Berry / Leftovers `recovery_context`
- Bright Powder `accuracy_context`
- Scope Lens `critical_context`
- King's Rock `flinch_context`
- Loaded Dice `multi_hit_context`

v0.77 added `data/static/charge_moves.json` and `core/charge_move_repository.py` for general charge move metadata. That fixture is move metadata only. It does not make Power Herb legal, selectable, user-confirmed, or modeled in the LLM payload.

Power Herb `charge_context` implementation is now blocked until legal item coverage is verified.

## Verification Goal

The goal is to prevent user-facing item context from drifting ahead of Champions legal item coverage.

This design verifies:

- whether each currently implemented item context is backed by `data/static/champions_legal_items.json`
- whether each item appears in `data/static/items.json`
- whether each item appears in `data/static/items_damage.json`
- whether fixture/metadata existence is being confused with legal playable item status
- whether future item contexts should be blocked when legal coverage is absent

## Item Coverage Table

Observed by inspecting `data/static/champions_legal_items.json`, `data/static/items.json`, and `data/static/items_damage.json`.

| item | implemented context / support | champions legal item fixture | items.json | items_damage.json | coverage decision |
| --- | --- | --- | --- | --- | --- |
| `charcoal` | type-boosting damage modifier | present legal | present | `type_boost_items` | aligned |
| `choice-scarf` | `speed_context` effective Speed modifier | present legal | present | `stat_boost_items` | aligned |
| `focus-sash` | limited `survival_context` | present legal | not present | not present | aligned via legal fixture; context is non-damage |
| `sitrus-berry` | limited `recovery_context` | present legal | not present | not present | aligned via legal fixture; context is non-damage |
| `leftovers` | limited `recovery_context` | present legal | not present | not present | aligned via legal fixture; context is non-damage |
| `bright-powder` | limited `accuracy_context` | present legal | not present | not present | aligned via legal fixture; context is non-damage |
| `scope-lens` | limited `critical_context` | present legal | not present | not present | aligned via legal fixture; context is non-damage |
| `kings-rock` | limited `flinch_context` | present legal | not present | not present | aligned via legal fixture; context is non-damage |
| `loaded-dice` | limited `multi_hit_context` | not present | present | not present | mismatch; should be treated as future-only / blocked for normal Champions legal item exposure until legality is confirmed |
| `power-herb` | no user-facing context implemented | not present | not present | not present | blocked; do not implement `charge_context` until legal coverage is added and approved |

## Findings

### Legal fixture is the source of playable item coverage

For user-facing Champions advice, `data/static/champions_legal_items.json` should be the gate for normal playable item exposure.

`items.json`, `items_damage.json`, damage parity tests, or move metadata fixtures may support engine behavior, but they do not prove an item is legal/selectable for the current Champions ruleset.

### Implemented legal-aligned contexts

These contexts are aligned with legal item coverage:

- Charcoal damage modifier
- Choice Scarf `speed_context`
- Focus Sash `survival_context`
- Sitrus Berry `recovery_context`
- Leftovers `recovery_context`
- Bright Powder `accuracy_context`
- Scope Lens `critical_context`
- King's Rock `flinch_context`

For non-damage contexts, absence from `items_damage.json` is acceptable because the context is not a direct damage formula input.

### Loaded Dice mismatch

Loaded Dice currently has `multi_hit_context` support and appears in `data/static/items.json`, but it is not present in `data/static/champions_legal_items.json`.

Policy decision needed:

- If Loaded Dice is not Champions legal, it should not be exposed as a normal user-facing item context for Champions legal play.
- Existing implementation can remain in code as a future-only / non-legal-capable context, but legal gating should prevent normal user-facing exposure unless the item is confirmed legal.
- Do not expand Loaded Dice advice or local verification until its legal status is resolved.

### Power Herb blocked

Power Herb is not present in:

- `data/static/champions_legal_items.json`
- `data/static/items.json`
- `data/static/items_damage.json`

Therefore Power Herb `charge_context` should not be implemented or exposed in user-facing payloads yet.

The v0.77 charge move fixture remains valid because it is generic move metadata and does not create a Power Herb item context.

## Coverage Policy

Recommended policy:

1. User-facing item context should require `data/static/champions_legal_items.json` legal coverage.
2. Engine/debug fixtures can exist without legal coverage, but must not imply normal playable item support.
3. If an item is absent from the legal item fixture, mark the related context as:
   - `blocked_by_legal_item_coverage`, or
   - `future_only_until_legal_confirmed`
4. Do not implement new user-facing item contexts for absent items.
5. Do not treat `items.json` alone as legal coverage.
6. Do not treat `items_damage.json` alone as legal coverage.
7. Do not treat move metadata fixtures as item legality.
8. Keep legal coverage, effect metadata, and LLM payload implementation as separate review gates.

## Proposed v0.79 Path

Recommended next step:

`v0.79 - Legal Item Context Gating Design`

Scope:

- design how item contexts should check or document Champions legal coverage
- decide whether existing Loaded Dice `multi_hit_context` needs a legal gating patch
- decide whether context builders should receive legal classification or rely on normal UI item selection
- define `blocked_by_legal_item_coverage` behavior for future contexts
- preserve existing legal-aligned contexts

Alternative:

`v0.79 - Loaded Dice Legal Coverage Follow-up`

Scope:

- specifically validate whether Loaded Dice should be added to Champions legal item fixture or treated as non-legal/future-only
- do not add new mechanics

Not recommended:

`v0.79 - Power Herb Limited Charge Context Implementation`

Reason:

- Power Herb is absent from legal item coverage and static item metadata.

## Test Plan

Future tests should cover:

- every user-facing item context item is present in `champions_legal_items.json`
- `loaded-dice` absence is documented or blocked
- `power-herb` absence blocks `charge_context`
- `items.json` presence alone does not grant legal coverage
- `items_damage.json` presence alone does not grant legal coverage
- charge move metadata fixture does not imply Power Herb legality
- legal-aligned contexts remain available for legal items
- unknown/non-legal item contexts are not invented
- existing item context regressions
- full pytest

## Out of Scope

The v0.78 coverage design excludes:

- code implementation
- fixture changes
- legal item fixture changes
- Power Herb `charge_context` implementation
- Loaded Dice behavior changes
- LLM payload changes
- item consumption tracking
- turn-sequence-adjusted KO probability
- Turn Engine
- weather interaction
- damage formula changes
- raw damage roll modifications
- KO context changes
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

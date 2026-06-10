# v0.99 Item Context Registry / Filtering Cleanup Design

## Current State

The advisor now has several additive context fields for item-related advice:

| Context | Current placement | Current purpose |
| --- | --- | --- |
| `survival_context` | move-level sibling | Focus Sash and Focus Band limited survival context |
| `recovery_context` | move-level sibling | Sitrus Berry / Leftovers limited recovery context |
| `accuracy_context` | move-level sibling | Bright Powder limited hit-reliability context |
| `critical_context` | move-level sibling | Scope Lens limited critical-hit context |
| `flinch_context` | move-level sibling | King's Rock limited flinch-pressure context |
| `multi_hit_context` | move-level sibling | Loaded Dice limited multi-hit context, currently legal-gated blocked |
| `resist_berry_context` | move-level sibling | standard type-resist berry limited context |
| `type_boost_context` | move-level sibling | supported type-boosting item limited context |
| `speed_order_context` | move-level sibling | Quick Claw limited move-order context |
| `speed_context` | top-level | raw/effective Speed comparison, including Choice Scarf effective Speed |

`ko_context` and `damage_estimate` are not item advice contexts. They remain raw damage-roll and estimate surfaces and should not absorb item-context filtering responsibilities.

Default Gemini advice payload filtering currently happens mostly in `llm/advisor_client.py`, especially through:

- `build_ui_advice_payload()`
- `ITEM_CONTEXT_FIELDS`
- `_collect_available_item_context_sides()`
- `_remove_unavailable_item_contexts()`
- `_hide_advice_hidden_item_profiles()`
- `_hide_advice_hidden_item_effects()`
- `_hide_move_local_unavailable_type_boost_item_effects()`
- `_remove_debug_only_limitations()`

Context attachment is separate and happens in `llm/advisor_damage_estimate.py`, where selected moves, available moves, and opponent known moves receive move-level additive context siblings. Candidate moves remain excluded.

The current design successfully separates enriched/debug payload from default advice payload, but the filtering policy is now spread across:

- a hard-coded context key set
- side extraction helper behavior
- a special type-boost item-effect scrubber
- a special Choice Scarf `speed_context` side collector
- generic hidden item profile scrubbing
- generic hidden item effect scrubbing
- generic debug-only limitation phrase removal
- prompt and contract wording
- duplicated regression tests for each context family

## Problem

The current filtering behavior works, but it is becoming easier to miss a step when adding a new context.

Main risks:

- A new context key might not be added to `ITEM_CONTEXT_FIELDS`, so `available=false` reasons could leak into default advice.
- A new context might use a side field other than `attacker_side` or `defender_side`, so item profile hiding could fail.
- Item names can leak through `item_profiles` or `damage_estimate.item_effects` even after an unavailable context is removed.
- Special cases such as type-boost item effects and Choice Scarf speed modifiers are encoded separately from the main filtering list.
- Contract text, prompt text, and tests repeat the same filtering policy in slightly different forms.
- Regression tests are strong but mostly context-specific, so they may not catch registry drift for a future context.

The problem is structural, not a request for new battle mechanics. v0.99 should document a cleanup direction before v1.0 implementation.

## Current Filtering Locations

| Location | Responsibility | Risk |
| --- | --- | --- |
| `ITEM_CONTEXT_FIELDS` in `advisor_client.py` | identifies item context keys eligible for `available=false` removal | manual list can drift as new contexts are added |
| `_remove_unavailable_item_contexts()` | recursively removes item contexts where `available is False` | only catches keys in `ITEM_CONTEXT_FIELDS` |
| `_context_item_sides()` | extracts `attacker_side` / `defender_side` for item-profile hiding | future `holder_side` or custom side keys would be missed |
| `_collect_available_item_context_sides()` | protects item profiles if a side has an available item context | manually tied to `ITEM_CONTEXT_FIELDS` plus `speed_context` special case |
| `_speed_context_item_sides()` | protects Choice Scarf item profile when effective Speed modifier is applied | top-level special case outside item context registry |
| `_hide_advice_hidden_item_profiles()` | replaces hidden item profiles with unknown profile | depends on hidden side collection and legal item status |
| `_hide_advice_hidden_item_effects()` | scrubs hidden item IDs from nested item effects | broad recursive behavior, but depends on hidden item IDs |
| `_hide_move_local_unavailable_type_boost_item_effects()` | removes move-local unavailable type-boost item effect exposure | type-boost-specific special case |
| `_remove_debug_only_limitations()` | removes debug phrases from `limitations` / `notes` | phrase list is manually maintained |
| prompt / contract | tells Gemini how to speak about contexts | increasingly long and duplicated |
| `tests/test_advisor_payload_contract.py` | verifies many concrete context cases | strong examples, but not yet registry-driven |

## Common Filtering Rule

Default advice payload should follow one central policy:

- `available=true` item advice contexts may remain in the default Gemini advice payload.
- `available=false` item advice contexts are removed from the default Gemini advice payload.
- blocked, deferred, unsupported, unconfirmed, non-triggered, absent, and missing-metadata reasons are debug/enriched metadata only.
- unavailable item names and effects should not leak through `item_profiles`, `damage_estimate.item_effects`, `limitations`, or `notes`.
- legal available contexts remain user-facing.
- raw `damage_estimate` remains.
- raw `ko_context` remains.
- top-level `speed_context` remains governed by its own Speed contract and is not a final turn-order truth surface.
- enriched/debug payload may retain full contexts and reasons for tests, diagnostics, and implementation audits.

## Context Inclusion Matrix

| Context | Default advice inclusion | Hidden when | Debug/enriched reason retained | Notes |
| --- | --- | --- | --- | --- |
| `survival_context` | keep when `available=true` | `available=false` | yes | Focus Sash / Focus Band only; no KO probability integration |
| `recovery_context` | keep when `available=true` | `available=false` | yes | Sitrus / Leftovers only; no final turn sequencing |
| `accuracy_context` | keep when `available=true` | `available=false` | yes | Bright Powder only; no final hit probability |
| `critical_context` | keep when `available=true` | `available=false` | yes | Scope Lens only; no crit-adjusted KO |
| `flinch_context` | keep when `available=true` | `available=false` | yes | King's Rock only; no final flinch probability |
| `multi_hit_context` | keep when `available=true` and legal coverage passes | `available=false` or legal-gated blocked | yes | Loaded Dice is currently blocked/future-only |
| `resist_berry_context` | keep when standard berry context is `available=true` | `available=false`, including Chilan deferred | yes | Chilan full support remains out of scope |
| `type_boost_context` | keep when matching supported legal type-boost item is `available=true` | mismatch, unsupported metadata, blocked/non-legal | yes | must also prevent `damage_estimate.item_effects` leak |
| `speed_order_context` | keep when Quick Claw context is `available=true` | unconfirmed, unsupported, blocked, non-Quick-Claw | yes | no final move-order calculation |
| `speed_context` | keep by Speed contract, not item context filtering | insufficient Speed data still remains as top-level unavailable Speed context | n/a | Choice Scarf lives here, not in `speed_order_context` |
| future `charge_context` | keep only when `available=true` and legal/move metadata supports it | unavailable, blocked, deferred | yes | Power Herb currently blocked/non-legal |

## Registry Options

### Option A - Keep Manual Helpers

Keep the current helpers and add new context keys by hand.

Pros:
- No implementation change.
- Current tests pass.

Cons:
- Drift risk grows with each new context.
- Special cases remain hard to audit.
- New-context checklist is easy to miss.

Assessment: acceptable for a few more small contexts, but not a good v1.0 foundation.

### Option B - Add a Small Context Key Registry

Introduce a central registry for known advice contexts. Example:

```python
ADVICE_CONTEXT_KEYS = {
    "survival_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "recovery_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "accuracy_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "critical_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "flinch_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "multi_hit_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "resist_berry_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "type_boost_context": {
        "kind": "item_context",
        "default_policy": "include_if_available",
        "scrub_move_local_item_effects_when_unavailable": True,
    },
    "speed_order_context": {"kind": "item_context", "default_policy": "include_if_available"},
    "charge_context": {"kind": "item_context", "default_policy": "include_if_available"},
}
```

Pros:
- Makes the current manual list explicit as a contract.
- Gives tests one place to assert coverage.
- Keeps implementation small.

Cons:
- Still needs custom hooks for `type_boost_context` and top-level `speed_context`.

Assessment: recommended as the first cleanup step.

### Option C - Full Context Registry With Hooks

Define a richer registry:

```python
ADVICE_CONTEXT_REGISTRY = {
    "type_boost_context": {
        "audience": "item_context",
        "include_default": "available_true_only",
        "side_fields": ("attacker_side", "defender_side"),
        "unavailable_hooks": ("scrub_move_local_item_effects",),
    },
    "speed_context": {
        "audience": "top_level_context",
        "include_default": "speed_contract",
        "available_side_collector": "choice_scarf_speed_context_sides",
    },
}
```

Pros:
- Captures special cases centrally.
- Better long-term fit for v1.0+.

Cons:
- Larger refactor.
- More risk of behavior drift if done all at once.

Assessment: good target shape, but v1.0 should implement it incrementally and preserve behavior.

## Recommendation

Adopt a registry, but start small.

Recommended v1.0 direction:

- Add a central `ADVICE_CONTEXT_KEYS` / `ADVICE_CONTEXT_REGISTRY`.
- Make `filter_context_for_default_advice(payload)` the single public helper for Gemini default advice payload filtering.
- Keep behavior unchanged:
  - `available=false` item contexts are hidden.
  - available legal contexts remain.
  - raw `damage_estimate` and `ko_context` remain.
  - debug/enriched payload remains untouched.
- Convert existing special cases into named registry notes or hooks:
  - type-boost move-local `damage_estimate.item_effects` scrubbing
  - Choice Scarf `speed_context` item profile protection
  - debug-only limitation phrase removal
- Add table-driven tests that assert every registered item context hides unavailable reasons and preserves available contexts.

This should be a cleanup milestone, not a new item behavior milestone.

## New Context Checklist

Before adding a new item/advice context:

1. Confirm Champions legal fixture status.
2. Confirm repo metadata source or document future-only/blocked state.
3. Decide whether the context is item-related, top-level, or non-item.
4. Add the context key to the registry.
5. Define placement: move-level sibling, top-level, or other.
6. Define side fields used for item profile hiding.
7. Define `available=true` conditions.
8. Define `available=false` reason codes and keep them debug/enriched only.
9. Add default advice payload filtering tests.
10. Add item profile / `damage_estimate.item_effects` leak tests if item IDs can appear elsewhere.
11. Add prompt and contract wording for available context only.
12. Confirm raw damage rolls and `ko_context` are unchanged unless explicitly approved.
13. Confirm candidate moves remain excluded unless separately approved.
14. Run focused payload contract tests and full pytest.

## Test Cleanup / Gaps

Current tests are strong for concrete regressions, including Chilan deferred, Loaded Dice blocked, type-boost mismatch, Fairy Feather unsupported, incense non-legal, Focus Band unavailable, and Quick Claw unavailable cases.

Suggested cleanup:

- Add one table-driven test that iterates all registered item context keys and verifies `available=false` contexts are removed from default advice payload.
- Add one test that verifies registry keys include every move-level context attached by `advisor_damage_estimate.py`.
- Add one test that verifies docs/contract context list stays aligned with registry keys, or at least asserts a stable exported key list.
- Add focused tests for side extraction so future `holder_side` / `source_side` additions do not bypass item profile hiding.
- Add a test that type-boost item-effect scrubbing is declared in registry or in a named hook, not a silent one-off.
- Reduce duplicated string-forbidden assertions by using shared forbidden term tuples.

## v1.0 Cleanup Items

Recommended before v1.0:

1. Rename `ITEM_CONTEXT_FIELDS` to a clearer registry-backed name.
2. Introduce `filter_context_for_default_advice(payload)` as the canonical filtering entry point.
3. Keep `build_ui_advice_payload()` as a thin wrapper around the filter.
4. Move debug-only phrase filtering into a named policy constant such as `DEBUG_ONLY_REASON_PHRASES`.
5. Document and test the type-boost item-effect scrub hook.
6. Document and test the Choice Scarf `speed_context` item profile protection hook.
7. Add registry coverage tests for all current context keys.
8. Keep candidate move exclusion unchanged.
9. Avoid adding new item behavior in the registry cleanup commit.
10. Run full pytest and compare payload snapshots for high-risk examples.

## Proposed v1.0 Path

Recommended:

**v1.0 - Item Context Registry Filtering Cleanup Implementation**

Scope:

- introduce a registry or registry-like constants
- consolidate default advice filtering entry point
- preserve existing behavior
- preserve debug/enriched unavailable reasons
- add table-driven coverage tests
- update payload contract docs
- no new item contexts
- no damage formula, raw roll, `ko_context`, fixture, legal fixture, UI, sample, Turn Engine, or item consumption changes

Alternative:

**v1.0 - Item Context Filtering Contract Test Consolidation**

Use this if T1/T2 want one more test-only hardening step before code cleanup.

## Out of Scope

The v0.99 design excludes:

- code implementation
- filtering logic changes
- new item context implementation
- large test rewrites
- damage formula changes
- raw damage roll changes
- Q12 multiplier changes
- `ko_context` calculation changes
- legal fixture mutation
- fixture mutation
- Turn Engine
- item consumption tracking
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

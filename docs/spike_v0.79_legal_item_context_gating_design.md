# v0.79 Legal Item Context Gating Design

## Current State

Several item contexts are implemented and may be attached to user-facing advisor payloads:

- Charcoal type-boosting damage modifier
- Choice Scarf `speed_context`
- Focus Sash `survival_context`
- Sitrus Berry / Leftovers `recovery_context`
- Bright Powder `accuracy_context`
- Scope Lens `critical_context`
- King's Rock `flinch_context`
- Loaded Dice `multi_hit_context`

v0.78 established that user-facing Champions item context should be gated by `data/static/champions_legal_items.json`.

Current coverage classification:

- aligned/legal:
  - `charcoal`
  - `choice-scarf`
  - `focus-sash`
  - `sitrus-berry`
  - `leftovers`
  - `bright-powder`
  - `scope-lens`
  - `kings-rock`
- mismatch / needs decision:
  - `loaded-dice`
- blocked:
  - `power-herb`

Power Herb remains blocked. `data/static/charge_moves.json` is move metadata only and does not establish Power Herb legality.

Loaded Dice is implemented as limited `multi_hit_context`, but it is absent from `data/static/champions_legal_items.json`. That creates a legal coverage mismatch that should be handled before more user-facing Loaded Dice work continues.

## Problem Definition

If user-facing advice mentions an item that is not Champions legal, the assistant can give misleading battle advice.

Important distinctions:

- An item existing in `items.json` does not prove Champions legality.
- An item existing in `items_damage.json` does not prove Champions legality.
- A context helper existing in `llm/` does not prove Champions legality.
- A move metadata fixture existing in `data/static/charge_moves.json` does not prove item legality.

Implementation support and legal availability must remain separate review gates.

Legal-unconfirmed items should be treated as future-only or blocked. They should not produce modeled user-facing contexts merely because a user-confirmed item id appears in the payload.

## Legal Gate Policy

Recommended policy:

1. A modeled user-facing item context may be emitted only when the item is present as legal in `data/static/champions_legal_items.json`.
2. `status=user_confirmed` is necessary but not sufficient.
3. If an item is user-confirmed but absent from the Champions legal fixture, the context should not be modeled.
4. Stable unavailable reason candidates:
   - `blocked_by_legal_item_coverage`
   - `future_only_until_legal_confirmed`
   - `unknown_item`
5. `items.json` is item metadata, not legal coverage.
6. `items_damage.json` is damage engine metadata, not legal coverage.
7. `charge_moves.json` is move metadata, not Power Herb legal coverage.
8. Legal gate policy should be explicit enough that future item contexts cannot accidentally bypass it.

The gate should preserve existing legal-aligned contexts:

- `charcoal`
- `choice-scarf`
- `focus-sash`
- `sitrus-berry`
- `leftovers`
- `bright-powder`
- `scope-lens`
- `kings-rock`

The gate should block or future-only items currently not legal-confirmed:

- `loaded-dice`
- `power-herb`

## Placement Options

### Option A - Gate inside each context helper

Each context helper checks legal coverage internally before returning `available=true`.

Pros:

- Context-specific safety is strong.
- Helpers remain safe if called directly in tests or future code.
- The helper can return a context-specific unavailable reason.

Cons:

- Repeated legal lookup logic across helpers.
- More dependency wiring in every helper.
- Easy for one helper to diverge from another helper's reason code policy.

### Option B - Common legal item helper/repository

Use the existing `core.champions_item_repository.ChampionsItemRepository` or a thin wrapper/helper around it as the common gate.

Pros:

- One legal source of truth.
- Reuses existing fixture normalization and classification.
- Keeps legal policy separate from effect-specific logic.
- Small implementation surface if the existing repository is reused.

Cons:

- Context helpers or payload assembly need a way to call the repository.
- Tests must avoid repeatedly reloading fixture data if performance becomes noisy.

### Option C - Gate at payload assembly before context creation

The payload assembly step decides whether to call each item context helper.

Pros:

- Centralized in one assembly path.
- Avoids adding legal repository imports to every context helper.
- Can prevent expensive context construction for blocked items.

Cons:

- Helpers remain unsafe if called directly.
- Tests that call helpers directly may not reflect production gating.
- Future callers could bypass the gate.

### T3 recommendation

Use a hybrid of Option B and Option C:

- Make a common legal gate helper backed by `ChampionsItemRepository`.
- Apply the gate in the payload assembly path before attaching user-facing contexts.
- For future new contexts, pass through the same common gate before `available=true`.
- Optionally add helper-level defensive checks later if direct helper use becomes common.

This keeps v0.80 small while avoiding repeated legal logic in every existing context helper.

## Item Status Classification

Proposed classification labels:

- `legal_modeled`
  - item is legal in `champions_legal_items.json`
  - item has an approved modeled context or damage support
- `legal_unmodeled`
  - item is legal but has no modeled context yet
- `implemented_but_not_legal`
  - context or metadata support exists, but item is absent from legal fixture
- `future_only`
  - implementation or fixture exists for future work, but user-facing use is not currently enabled
- `blocked_by_legal_item_coverage`
  - item should not emit modeled context because legal fixture coverage is absent
- `unknown_item`
  - item is not recognized by the legal fixture or supporting metadata

Current item classification:

| item | status | notes |
| --- | --- | --- |
| `charcoal` | `legal_modeled` | legal and damage-supported |
| `choice-scarf` | `legal_modeled` | legal and Speed context-supported |
| `focus-sash` | `legal_modeled` | legal and survival context-supported |
| `sitrus-berry` | `legal_modeled` | legal and recovery context-supported |
| `leftovers` | `legal_modeled` | legal and recovery context-supported |
| `bright-powder` | `legal_modeled` | legal and accuracy context-supported |
| `scope-lens` | `legal_modeled` | legal and critical context-supported |
| `kings-rock` | `legal_modeled` | legal and flinch context-supported |
| `loaded-dice` | `implemented_but_not_legal` / `future_only` | context exists, but legal fixture coverage is absent |
| `power-herb` | `blocked_by_legal_item_coverage` | no user-facing context; legal fixture coverage absent |

## Loaded Dice Policy

Loaded Dice `multi_hit_context` is implemented, but `loaded-dice` is absent from `data/static/champions_legal_items.json`.

Possible policies:

### A - Block Loaded Dice context through legal gate

Treat Loaded Dice as `blocked_by_legal_item_coverage` until it appears in the Champions legal fixture.

Pros:

- Strong legal safety.
- Prevents non-legal item advice.
- Does not mutate legal fixture without evidence.

Cons:

- Existing tests and local verification expectations may need updates.
- The implemented helper remains future-only for now.

### B - Keep Loaded Dice future-only until legal confirmed

Keep the implementation but treat it as non-user-facing unless legal fixture coverage is added.

Pros:

- Preserves implementation for future legality updates.
- Avoids deleting useful code.

Cons:

- Requires explicit gate to avoid accidental exposure.

### C - Separate legal coverage investigation

Run a focused follow-up to determine whether Loaded Dice should be added to the legal fixture.

Pros:

- Avoids guessing.
- Keeps legal fixture changes evidence-driven.

Cons:

- Requires T1/T2 source decision or external legal source approval.

T3 recommendation:

- In v0.80, implement the legal gate and block Loaded Dice user-facing context with `blocked_by_legal_item_coverage` or `future_only_until_legal_confirmed`.
- Do not add Loaded Dice to the legal fixture without a separate approved legal coverage update.
- Keep Loaded Dice implementation as future-only code.

## Power Herb Policy

Power Herb is not implemented as user-facing context and should remain blocked.

Policy:

- Do not implement Power Herb `charge_context`.
- Do not expose Power Herb in user-facing payload context.
- Do not treat `data/static/charge_moves.json` as Power Herb legality.
- Do not use Power Herb even if a user-confirmed item id appears in payload until the item is legal-confirmed.
- Keep Power Herb classified as `blocked_by_legal_item_coverage`.

## Proposed v0.80 Path

### Candidate A - v0.80 Legal Item Repository / Gate Design

Design only.

Pros:

- Very cautious.
- Lets T1/T2 decide exact API and reason codes before implementation.

Cons:

- Another design pass may be unnecessary because `ChampionsItemRepository` already exists.

### Candidate B - v0.80 Legal Item Gate Implementation

Recommended.

Scope:

- reuse `core.champions_item_repository.ChampionsItemRepository`
- add a small common gate helper or payload assembly check
- block Loaded Dice context when absent from legal fixture
- keep Power Herb blocked
- add regression tests for legal and blocked items
- do not mutate legal fixture
- do not add Power Herb context

Pros:

- Directly addresses the current mismatch.
- Keeps legal fixture unchanged.
- Provides immediate protection for future contexts.

Cons:

- Requires updating tests that expect Loaded Dice context availability without legal coverage.

### Candidate C - v0.80 Loaded Dice Legal Coverage Investigation

Scope:

- investigate whether Loaded Dice belongs in Champions legal fixture
- request source approval if needed
- no code changes

Pros:

- Clarifies the specific mismatch.

Cons:

- Does not prevent future non-legal item context exposure unless gate implementation follows.

T3 recommendation:

- Proceed with `v0.80 - Legal Item Gate Implementation`.
- Keep legal fixture unchanged.
- Add Loaded Dice blocked regression tests.
- Keep Power Herb blocked.

## Tests Plan

Future implementation tests should cover:

- legal item passes gate
- illegal/unlisted item fails gate
- `loaded-dice` is blocked because it is absent from `champions_legal_items.json`
- `power-herb` is blocked
- `status=user_confirmed` illegal item is still blocked
- context helper or payload assembly does not emit modeled context for blocked item
- blocked reason code is stable
- aligned items still work
- no legal fixture mutation
- existing item context regressions
- full pytest

Suggested focused regressions:

- user-confirmed `bright-powder` still gets `accuracy_context.available=true`
- user-confirmed `scope-lens` still gets `critical_context.available=true`
- user-confirmed `kings-rock` still gets `flinch_context.available=true`
- user-confirmed `loaded-dice` no longer gets modeled user-facing `multi_hit_context.available=true` unless legal coverage is added
- user-confirmed `power-herb` does not get `charge_context`

## Out of Scope

The v0.79 gating design excludes:

- code implementation
- legal gate implementation
- legal fixture mutation
- Loaded Dice behavior change
- Power Herb `charge_context` implementation
- external web/legal research unless explicitly requested
- damage formula change
- raw damage roll modification
- KO context change
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

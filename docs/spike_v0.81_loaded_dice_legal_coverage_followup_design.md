# v0.81 Loaded Dice Legal Coverage Follow-up Design

## Current State

Loaded Dice limited `multi_hit_context` is implemented in `llm/advisor_multi_hit_context.py`.

However, `loaded-dice` is not present in `data/static/champions_legal_items.json`. It is present in `data/static/items.json`, but `items.json` is item metadata and does not establish Champions legal availability. It is also not present in `data/static/items_damage.json`.

v0.80 added the Champions legal item gate:

- `core/champions_legal_item_repository.py`
- `llm/advisor_item_legal_gate.py`
- stable unavailable reason `blocked_by_legal_item_coverage`

As a result, user-confirmed Loaded Dice is blocked from emitting a user-facing modeled `multi_hit_context.available=true` payload while legal fixture coverage is absent.

The Champions legal fixture has not been changed. Loaded Dice has not been added to the legal fixture. Power Herb remains blocked.

## Problem

Implemented context code does not mean an item is legal in Champions.

If the advisor exposes Loaded Dice as modeled user-facing advice without legal confirmation, it can give invalid battle guidance for the current ruleset. This is especially risky because multi-hit context can influence how the LLM talks about KO pressure, Focus Sash implications, and move reliability even when raw damage and `ko_context` remain unchanged.

Deleting the implementation immediately would make the current legal scope cleaner, but it would also discard tested future work that can be reused if Loaded Dice later becomes legal-confirmed.

The policy needs to keep advice safe without creating churn in already-tested future-only implementation code.

## Policy Options

### Option A - Keep implemented but blocked

Keep the Loaded Dice `multi_hit_context` code and rely on the v0.80 legal gate to block user-facing modeled output while `loaded-dice` is absent from `data/static/champions_legal_items.json`.

Pros:

- Preserves future reuse.
- Keeps existing tests around blocked behavior.
- Avoids legal fixture mutation without evidence.

Cons:

- Can look like unused or dead code unless clearly documented.
- Future contributors may wonder why a context exists but is unavailable in normal payloads.

### Option B - Remove Loaded Dice context implementation

Remove the Loaded Dice `multi_hit_context` implementation until Champions legal coverage is confirmed.

Pros:

- Current implementation surface exactly matches legal scope.
- Reduces future-only code.

Cons:

- Loses already-tested implementation work.
- Requires reimplementation if legal coverage is later confirmed.
- Provides less regression coverage for legal gate blocking.

### Option C - Keep as future-only with explicit docs/tests

Keep Loaded Dice implementation as future-only support, but explicitly document and test that it is blocked from user-facing modeled context until legal fixture coverage is confirmed.

Pros:

- Preserves implementation reuse.
- Makes intent clear.
- Keeps safety enforced by regression tests.
- Avoids mutating legal fixture without evidence.

Cons:

- Adds a small documentation and test maintenance burden.
- Requires continued discipline that future-only code does not bypass the legal gate.

## Recommended Policy

Use Option C.

Loaded Dice should remain implemented as future-only multi-hit context support, but legal gating must continue to prevent user-facing modeled context while `loaded-dice` is absent from `data/static/champions_legal_items.json`.

Required behavior:

- `loaded-dice` remains `future_only_until_legal_confirmed` / `blocked_by_legal_item_coverage`.
- `status=user_confirmed` is not enough to emit modeled Loaded Dice context.
- `multi_hit_context.available=true` must not appear for Loaded Dice in user-facing Champions payloads until legal coverage is confirmed.
- Existing legal gate regression tests should continue to protect this behavior.
- Legal fixture updates require separate approved evidence and must not be inferred from `items.json`, `items_damage.json`, or implementation code.

## Loaded Dice Status

Current classification:

- implementation status: implemented future-only support
- legal fixture status: absent from `data/static/champions_legal_items.json`
- `items.json` status: present
- `items_damage.json` status: absent
- user-facing status: blocked
- stable reason: `blocked_by_legal_item_coverage`

The implemented helper can remain in the repo because it is legal-gated and tested. It should not be used as evidence that Loaded Dice is playable or legal in Champions.

## Proposed v0.82 Path

### Candidate A - Loaded Dice Future-only Documentation / Regression Polish

Scope:

- clarify docs/contract wording around Loaded Dice future-only status
- improve test names or assertion messages if needed
- keep behavior unchanged

This is useful if T1/T2 want extra clarity before moving on, but it is not required for safety because v0.80 already gates Loaded Dice.

### Candidate B - Return to Legal Item Feature Expansion

Scope:

- choose a Champions legal item from `data/static/champions_legal_items.json`
- design the next limited context only after legal coverage is confirmed

This is the best path if the next goal is new feature work.

### Candidate C - Local Gemini Verification Batch

Scope:

- run the deferred local Gemini verification items for recently polished contexts
- record safety/wording outcomes without changing mechanics

This is the best path if the next goal is quality validation before more feature expansion.

T3 recommendation:

- Keep Loaded Dice blocked/future-only now.
- Do not mutate the legal fixture.
- Prefer v0.82 Local Gemini Verification Batch or a new feature design for an item already confirmed legal in `data/static/champions_legal_items.json`.
- Use Candidate A only if T1/T2 want additional contract wording polish specifically for the future-only Loaded Dice state.

## Out of Scope

This v0.81 follow-up excludes:

- code implementation
- legal fixture mutation
- Loaded Dice legal addition
- Loaded Dice behavior expansion
- Power Herb implementation
- external research
- damage formula changes
- raw damage roll changes
- KO context changes
- UI changes
- sample additions
- logs, `.env`, secrets, API keys, or handoff capsule commits

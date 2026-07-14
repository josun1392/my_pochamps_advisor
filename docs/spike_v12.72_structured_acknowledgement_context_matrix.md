# v12.72 Structured Acknowledgement UX and Context Matrix Validation

## Scope

This offline validation covers the v12.70 structured trusted-context
acknowledgement format across normalized current-condition and observed
item-event combinations. It does not add a provider call, payload schema,
prompt format, CLI schema, UI behavior, or parser behavior.

## Context matrix

The production payload-to-prompt path was checked for these cases:

- condition plus item event: self burn, opponent unknown, opponent Focus Sash
  activation;
- one-side condition: self paralysis;
- both-side conditions: self none and opponent poison;
- opponent unknown only;
- self none only;
- item event only: opponent Leftovers recovery observation;
- two observed item events with distinct identities and stable payload order;
- no trusted context; and
- saved trusted context with the limited-context gate disabled.

For every enabled non-empty case, expected acknowledgement entries come from
the normalized prompt payload and are rendered dynamically as the applicable
`Current condition` and/or `Observed item event` lines. Absent and disabled
paths generate no structured acknowledgement requirement or entries.

## Exact-set and UX contracts

- Canonical and minor case/Focus-Sash spacing variants validate.
- Missing, extra, duplicate, side-swapped, category-swapped, identity-changed,
  and event-type-changed or omitted lines fail deterministically.
- An empty expected context does not require a block in normal UI advice; an
  unsolicited non-empty block is rejected as an extra trusted entry.
- `none` remains confirmed present-state absence, and `unknown` remains
  unknown; neither is promoted to a recovery event or inferred condition.
- Observed item events remain observations only. Exact recovery, HP, resolved
  effect, consumption state, timing, RNG, and order are not trusted facts.
- The acknowledgement is a short readback. The `[Advice]` body must contain an
  actionable, uncertainty-aware recommendation rather than merely repeating
  acknowledgement lines or exposing raw source/status/confidence dictionaries.

## UI and CLI compatibility

A mocked production `run_ui_selected_advice(...)` flow returns the whole
`[Trusted Context]` plus `[Advice]` response unchanged. The existing worker
finished signal preserves that text and its usage/summary payload; the CLI JSON
adapter is not used by normal UI delivery.

Existing CLI regression tests retain the sanitized schema and status/exit-code
contract: semantic pass/fail uses exit 0, response unavailable uses 5,
evaluator failure uses 6, provider failure uses 4, and invalid/preflight output
uses 2. No raw response is exposed.

## Verification

- matrix contract: 21 passed
- acknowledgement contract: 13 passed
- condition payload/prompt: 14 passed
- response validation: 20 passed
- sanitized CLI: 7 passed
- smoke response capture: 6 passed
- item-event prompt: 9 passed
- item-event payload mapping: 27 passed
- advisor payload: 500 passed
- full suite: 1,786 passed, 2 deselected
- `git diff --check` and `git diff --cached --check`: passed

## Phase status

**STRUCTURED ACKNOWLEDGEMENT PHASE: READY - LIMITED ACTUAL EVIDENCE**

The full offline context matrix, normal UI compatibility contract, CLI
regression, and existing v12.71 actual evidence (2/2 assessable semantic PASS)
are consistent. The missing v12.71 attempt result remains unavailable and is
not reconstructed. This status does not authorize another provider call.

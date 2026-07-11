# v12.50 Item Event Offline Response Validation and Re-smoke Readiness

## Purpose

Validate the v12.49 prompt contrast correction offline and determine whether
the item-event path is ready for a separately approved single actual re-smoke.

## Production-Path Prompt Capture

The existing offline fixture uses:

```text
run_ui_selected_advice(...)
-> _build_ui_selected_prompt(...)
-> mocked call_gemini
-> captured provider prompt
```

The fixed identity case verifies:

- self Leftovers is user-confirmed current item context
- opponent Focus Sash activation is explicit observed event context
- the contrast instruction is present
- the readback instruction requires side, item, and event type
- observation-only and resolved/exact/post-turn/RNG/order non-inference
  boundaries remain present
- broad fixture `damage_estimate` context coexists with the new guard

No provider call occurs in the fixture.

## Event-Present and Event-Absent Validation

The contrast/readback wording is present for valid normalized observed events.
It is absent for:

- limited context off
- known current item without an observed event
- invalid event input whose normalized context is omitted

Existing raw confirmation stripping and forbidden-field scans remain covered.

## Synthetic Response Validation

The test-only evaluator accepts a response only when it distinguishes self
current Leftovers from an explicitly user-confirmed opponent Focus Sash
activation observation and does not establish a resolved effect or resulting
HP.

It rejects the following separate failure classes:

1. identity mixing
2. event omission
3. Focus Sash exact HP resolution
4. exact damage/prevention outcome claim
5. RNG or final speed-order claim
6. damage distraction without event readback

A trusted damage range is not a failure by itself if the observed event remains
explicitly identified and unresolved.

## v12.45 Comparison

The v12.45 response lacked known-item/observed-event separation and event
salience while unrelated damage detail dominated. After v12.49, the provider
prompt now contains a compact explicit contrast and required readback
instruction. Offline tests confirm this instruction coexists with, rather than
removes, trusted damage context.

Offline validation cannot prove a real model response will follow the
instruction; it only verifies the corrected production prompt and response
evaluation contract.

## Production Prompt Change

No additional prompt change was required in v12.50. The v12.49 compact guard
extension satisfies the offline contract:

- event present: contrast/readback and observed-only boundaries are present
- event absent: item-event-specific wording is absent
- full advice: trusted damage context remains available

## Readiness Decision

`READY FOR SINGLE ACTUAL RE-SMOKE`

This decision is limited to offline readiness. It is not approval to execute a
provider call. A future actual re-smoke requires separate T1/T2 approval,
exactly one call, no retry/fallback/second provider/Vertex AI, and the existing
sanitized reporting policy.

## Safety Boundary

- No actual Gemini/provider/network, retry, fallback, second provider, Vertex
  AI, or credential call was executed.
- No raw Gemini response or token-log content was read, restored, or stored.
- No payload mapping, UI, damage/KO, Q12, raw rolls, or provider retry behavior
  changed.

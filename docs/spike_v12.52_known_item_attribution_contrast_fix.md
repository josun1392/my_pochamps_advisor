# v12.52 Known Item Attribution Contrast Fix

## Purpose

Fix the remaining v12.51 attribution gap with the smallest event-present prompt
extension and validate readiness for a final separately approved actual
re-smoke.

## Production Change

The existing `item_event_context` guard now adds a conditional current-known
item instruction when observed events are present:

- acknowledge each current known item by side and item
- identify it as user-confirmed current context only
- state that it is not an observed activation, consumption, or resolved effect
- keep it separate from explicitly observed item events

The existing observed-event instruction remains unchanged: side, item, event
type, user-confirmed observation, and unresolved boundary.

## Activation Conditions

The guard remains active only for non-empty normalized observed events.

- Both contexts present: known-current and observed-event instructions appear.
- Event present, known item absent: observed-event readback remains; the
  conditional wording must not invent a known item.
- Known item only, disabled, empty, or all-invalid event paths: item-event
  contrast/readback wording remains absent.

## Fixed Identity Case

- Self Leftovers: user-confirmed current known-item context only.
- Opponent Focus Sash activation: separately user-confirmed observed event only.
- The prompt explicitly prohibits treating Leftovers as observed activation,
  consumption, or resolution, and retains the Focus Sash resolved/exact/
  post-turn/RNG/order non-inference boundary.

## Offline Production-Path Validation

Mocked `run_ui_selected_advice(...)` captures the provider prompt without a
provider call. Contracts verify:

- current-known and observed-event attribution/readback anchors
- self/opponent identity separation
- unknown item remains `known=False` when no known item profile exists
- event-absent, disabled, and all-invalid omission behavior
- trusted damage context coexists with both attribution/readback instructions

The test-only response evaluator additionally rejects:

1. known-item omission
2. known or observed attribution omission
3. identity mixing
4. known-item promotion into observed event
5. observed-event promotion into resolved effect
6. exact, post-turn, RNG, or final-order claims

## Existing Behavior Preserved

No change was made to item-event mapping, limited context gating, known-item
data model, UI dialogs/buttons, field mapping, damage estimates, KO context,
Q12, raw rolls, or provider retry behavior.

## Readiness Decision

`READY FOR FINAL SINGLE ACTUAL RE-SMOKE`

Offline readiness does not authorize a provider call. A final re-smoke requires
separate T1/T2 approval, exactly one Gemini call, and no retry, fallback,
second provider, or Vertex AI.

## Safety Boundary

- No actual Gemini/provider/network, credential, retry, fallback, second
  provider, or Vertex AI call occurred.
- No raw response or token-log content was read, restored, or stored.
- No payload redesign, broad damage suppression, or response schema was added.

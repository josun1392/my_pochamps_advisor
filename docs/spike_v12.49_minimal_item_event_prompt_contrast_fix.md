# v12.49 Minimal Item Event Prompt Contrast Fix

## Purpose

Implement the smallest prompt correction for the v12.45 observed-event
salience failure while preserving payload shape, existing item semantics, and
trusted damage context.

## Production Change

`_build_item_event_context_prompt_guard(...)` now adds one compact instruction
when `item_event_context` is present:

- distinguish current known items from explicitly observed item events
- briefly acknowledge each observed event by side, item, and event type
- treat that acknowledgement as user-confirmed observation only

The existing observed-only boundary remains unchanged: no resolved mechanics,
exact HP/damage, post-turn state, RNG, or final order inference.

## Activation Boundary

The guard is emitted only after the payload mapper has produced non-empty valid
`item_event_context.observed_events`. It remains absent for:

- limited context off
- absent or empty item-event context
- all-invalid event input
- known current item without an explicit observed event

No payload mapper or battle-input behavior changed.

## Known Item and Observed Event Contrast

The prompt now explicitly tells the model not to merge:

- self user-confirmed current Leftovers context
- opponent user-confirmed observed Focus Sash activation context

The wording requests a concise readback of event side, item, and type. It does
not promote Leftovers into activation/recovery observation or Focus Sash into a
resolved effect.

## Damage Context Coexistence

`damage_estimate` and `ko_context` remain available in full advice payloads.
The new wording does not suppress them or change their existing assumptions.
It requires event acknowledgement in addition to, not instead of, unrelated
trusted battle detail.

## Offline Production-Path Verification

The existing mocked `run_ui_selected_advice(...)` fixture captures the provider
prompt without a provider call. It now verifies contrast/readback anchors for
all allowed observed event types and their absence when only a known item is
present.

The reproduction contract suite additionally verifies:

- Fixture A structured identity separation
- Fixture B coexistence with broad damage context
- event-absent omission of new wording
- synthetic identity mixing, omission, unsupported resolution, and conditional
  damage-distraction behavior

## Safety Boundary

- No change to item event mapping, limited context gate, dialogs, buttons, field
  state mapping, damage estimates, KO context, Q12, raw rolls, or retry logic.
- No actual Gemini/provider/network call occurred.
- No response evaluator was added to production.

## Next Recommendation

`v12.50 Item Event Offline Prompt/Response Fixture`

Use the updated production prompt path with mocked provider responses to check
that the new contrast/readback instruction coexists with safe response wording.
Any actual re-smoke remains separately approval-gated.

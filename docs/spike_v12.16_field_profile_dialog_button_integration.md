# v12.16 FieldProfileDialog Button Integration

## Purpose

Add the user-facing `FieldProfileDialog` entry point and wire its result into
MainWindow-owned session state while preserving the existing limited-context
checkbox gate.

This milestone makes the dialog reachable from the UI. It does not add a new
limited-context checkbox, does not change prompt guard wording, does not run any
provider call, and does not change damage, KO, or turn-resolution behavior.

## Implementation Scope

Implemented:

- secondary `Field state` button in `LLMAdvicePanel`
- `field_profile_requested` signal from `LLMAdvicePanel`
- `MainWindow._field_profiles: dict | None` session-local state
- MainWindow slot that opens `FieldProfileDialog`
- Apply stores dialog `field_profiles`
- Cancel preserves previous state
- Reset unknown plus Apply stores the dialog's default unknown-compatible
  profile shape
- `_build_llm_battle_input()` includes saved `field_profiles` when present

Not implemented:

- new limited-context checkbox
- field source inference
- battle log/parser source
- prompt guard wording change
- full Turn Engine behavior
- actual Gemini or provider call

## Changed Files

- `ui/widgets/llm_advice_panel.py`
- `ui/main_window.py`
- `tests/test_field_profile_button_integration_contract.py`
- `docs/PROGRESS.md`
- `docs/advisor_payload_contract.md`
- `docs/handoff_next_session_prompt_v1.9.md`

## Button Placement

The button is added inside `LLMAdvicePanel` as a secondary action:

- label: `Field state`
- object name: `fieldProfileButton`
- signal: `field_profile_requested`

The existing advice button remains the only action that can start LLM advice.
Clicking the field-state button only opens the local dialog path.

## State Storage Behavior

`MainWindow` owns the field-profile session state:

```python
self._field_profiles: dict | None = None
```

This mirrors the v12.14 design: `LLMAdvicePanel` owns only the button/signal,
while MainWindow owns global battlefield-level state.

## Apply / Cancel / Reset Behavior

- Apply: `MainWindow._field_profiles = dialog.field_profiles`
- Cancel: `MainWindow._field_profiles` is unchanged
- Reset unknown: remains dialog-local until Apply
- Reset unknown + Apply: stores default unknown field-profile entries

The stored shape remains the v12.9 `status/source/value` contract.

## Checkbox Gate Behavior

The existing limited-context checkbox remains the hard gate:

- checkbox off:
  - `battle_state_context` is omitted
  - top-level `field_profiles` is stripped from the prompt payload
  - saved field profiles do not reach the provider
- checkbox on:
  - `battle_state_context` is included
  - saved valid `field_profiles` normalize into `battle_state_context.field`

## Prompt Path

Current implemented path:

```text
LLMAdvicePanel Field state button
-> MainWindow._open_field_profile_dialog()
-> FieldProfileDialog(current_profiles=self._field_profiles)
-> MainWindow._field_profiles
-> MainWindow._build_llm_battle_input()["field_profiles"]
-> _build_ui_selected_prompt(... enable_battle_state_context=checkbox_state)
-> build_battle_state_context_from_ui_selected_state(... include_user_confirmed_fields=True)
-> battle_state_context.field
```

No top-level `field_profiles` leaks into the serialized prompt payload.

## No-Call Behavior

The field-state button, dialog open, Apply, Cancel, and Reset unknown are local
UI/session-state operations. They do not call Gemini, Vertex AI, a second
provider, retry logic, or network/provider code.

## Tests

Added/updated coverage in:

- `tests/test_field_profile_button_integration_contract.py`

Covered behavior:

- Field state button exists and emits `field_profile_requested`
- button click does not emit `advice_requested`
- button click does not call provider code
- MainWindow dialog handler stores Apply results
- Cancel preserves previous `MainWindow._field_profiles`
- Reset unknown plus Apply stores default unknown profiles
- saved profiles flow into `_build_llm_battle_input()`
- checkbox off omits `battle_state_context` and top-level `field_profiles`
- checkbox on maps saved field profiles into `battle_state_context.field`
- checkbox default remains off
- battle-state prompt guard wording remains unchanged

## Non-Goals

- No new limited-context checkbox.
- No prompt guard wording change.
- No field inference from damage, KO context, species/common/meta, item effects,
  hidden guesses, or model guesses.
- No duration, expiration, post-turn state, damage precision, or full turn
  outcome behavior.
- No damage formula, raw roll, Q12, `ko_context`, or `damage_estimate` change.

## Safety Boundary

- Known field is current context only.
- Known field does not imply duration.
- Known field does not imply expiration.
- Known field does not imply post-turn outcome.
- Known field does not imply damage precision.
- Known field does not imply full turn outcome.
- Checkbox off means saved field profiles are not sent to the LLM payload.
- No actual Gemini call was made.

## Next Recommendation

Recommended next milestone:

- v12.17 Limited Context Copy Update for Field State

Reason:

- field state is now user-enterable in the UI, so the existing limited-context
  checkbox tooltip/status copy should next mention user-confirmed field state
  explicitly while preserving the current safety boundary.

Alternatives:

- v12.17 Field State UI End-to-End Offline Smoke
- v12.17 Field State UI Phase Closure

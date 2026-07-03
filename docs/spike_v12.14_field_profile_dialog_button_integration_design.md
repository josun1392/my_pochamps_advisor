# v12.14 FieldProfileDialog Button Integration Design

## Purpose

Design where and how to expose `FieldProfileDialog` in the UI before adding any
button integration.

This milestone is design-only. It does not add a button, does not add
`MainWindow._field_profiles`, does not change UI copy, does not change payload
builder flow, and does not call any provider.

## Inspected Files

- `docs/spike_v12.13_field_state_ui_mapping_implementation.md`
- `docs/spike_v12.12_field_state_ui_mapping_tests.md`
- `docs/spike_v12.11_field_state_ui_mapping_design.md`
- `docs/advisor_payload_contract.md`
- `docs/PROGRESS.md`
- `docs/handoff_next_session_prompt_v1.9.md`
- `ui/widgets/field_profile_dialog.py`
- `ui/widgets/item_profile_dialog.py`
- `ui/widgets/llm_advice_panel.py`
- `ui/widgets/pokemon_panel.py`
- `ui/main_window.py`
- `tests/test_field_profile_dialog.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

## Current UI State

Current relevant UI structure:

- `AnalysisColumn` owns the central analysis UI.
- `AnalysisColumn` contains `LLMAdvicePanel`.
- `LLMAdvicePanel` owns the advice request button and the existing
  limited-context checkbox.
- `MainWindow._start_llm_advice()` reads that checkbox and enables
  `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and
  `battle_state_context` together.
- `PokemonPanel` owns per-slot `Item` and `Stats` buttons.
- `PokemonPanel.item_profile` is per-Pokemon state.
- `FieldProfileDialog` exists as a standalone dialog.
- `field_profiles` can already map into `battle_state_context.field` when a
  caller supplies it and the limited-context gate is on.
- No current UI stores `field_profiles`.
- No current UI button opens `FieldProfileDialog`.

## Entry Point Candidates

### A. LLMAdvicePanel Button

Proposal:

- Add a secondary button in `LLMAdvicePanel`, near the existing limited-context
  checkbox.

Advantages:

- Semantically close to the optional LLM context gate.
- Makes clear that field state is extra advice context, not deterministic
  battle simulation.
- Keeps battlefield-level input out of per-Pokemon panels.
- Easy to test via the existing advice panel UI tests.
- Avoids adding a new top-level layout region.

Disadvantages:

- `LLMAdvicePanel` could become more crowded.
- The panel currently emits only `advice_requested`; a new signal would be
  needed for a field-profile request.
- Copy must be concise to avoid implying resolved battle state.

Distance from limited context checkbox:

- Closest candidate.

Consistency with user-confirmed profile flow:

- Similar source semantics to item profiles, but correctly scoped to advice
  context rather than a Pokemon slot.

UI complexity:

- Low to medium.

Test difficulty:

- Low. Button emission, no-call behavior, and disabled state can be covered
  similarly to existing checkbox tests.

### B. MainWindow Top / Toolbar Button

Proposal:

- Add a top-level button or toolbar action for field state.

Advantages:

- Treats field state as global battlefield state.
- Keeps `LLMAdvicePanel` compact.

Disadvantages:

- Current layout does not already have a toolbar-style control surface.
- Adds a new global UI area and visual hierarchy decision.
- Farther from the limited-context checkbox, so users may miss the gate
  relationship.

Distance from limited context checkbox:

- Medium to far.

Consistency with user-confirmed profile flow:

- Global state ownership fits, but entry placement differs from existing
  profile buttons.

UI complexity:

- Medium.

Test difficulty:

- Medium. Requires MainWindow-level layout assertions.

### C. PokemonPanel Button

Proposal:

- Add a field-state button near each Pokemon panel.

Advantages:

- Reuses the existing `Item` / `Stats` small-button visual pattern.

Disadvantages:

- Field state is not per-Pokemon slot state.
- Duplicate buttons across teams would create ownership ambiguity.
- Risk that users interpret weather/screens/hazards as tied to one Pokemon.
- Harder to explain self/opponent side-specific hazards/screens from a single
  Pokemon slot.

Distance from limited context checkbox:

- Far.

Consistency with user-confirmed profile flow:

- Visual consistency with item profile buttons, but wrong data ownership.

UI complexity:

- Medium to high due to duplicated entry points.

Test difficulty:

- Medium to high because every slot could emit the same global dialog action.

### D. Future Battle State / Advanced Context Panel

Proposal:

- Defer the field button into a future dedicated battle-state or advanced
  context panel.

Advantages:

- Best long-term information architecture if more global battle state inputs
  are added later.
- Could group field, status, boosts, known conditions, and future parser/log
  sources.

Disadvantages:

- Requires a larger UI design and likely more layout work.
- Overkill for the current single field-profile entry point.
- Delays making the existing `FieldProfileDialog` reachable.

Distance from limited context checkbox:

- Depends on placement; likely near but not inside `LLMAdvicePanel`.

Consistency with user-confirmed profile flow:

- Strong for future battle-state inputs, but not necessary yet.

UI complexity:

- High.

Test difficulty:

- High for first implementation.

## Selected Entry Point

Recommended first implementation:

- add a secondary `Field state` button inside `LLMAdvicePanel`, directly near
  the limited-context checkbox and status text.

Rationale:

- Field profiles are LLM advice context, not per-Pokemon state.
- The existing checkbox is the hard gate for whether field profiles reach the
  prompt.
- Keeping the entry beside that gate makes the payload boundary easier to
  understand.
- `MainWindow` can still own the session-local state while `LLMAdvicePanel`
  only emits a request signal.
- This keeps implementation smaller than introducing a new Battle State Panel.

Rejected for now:

- `PokemonPanel`: wrong ownership.
- MainWindow toolbar: unnecessary layout surface.
- Future Battle State Panel: good long-term option, but too large for the next
  implementation step.

## Button / Copy Proposal

Recommended button label:

- `Field state`

Korean user-facing candidate for later localization/copy pass:

- `필드 상태 설정`

Tooltip/status copy candidate:

- `Enter user-confirmed current weather, terrain, room, screens, and hazards. This does not confirm duration, expiration, damage precision, or turn outcome.`

Korean tooltip candidate:

- `날씨, 필드, 룸, 벽, 설치물을 사용자가 확인한 현재 상태로 입력합니다. 턴 수/만료/결과를 확정하지 않습니다.`

Copy implementation should be a future step. v12.14 does not change
`LLMAdvicePanel` text.

## State Storage Proposal

State owner:

- `MainWindow`

Recommended future field:

```python
self._field_profiles: dict | None
```

Why `MainWindow`:

- field state is global battlefield state
- `MainWindow` already coordinates dialogs and UI-selected `battle_input`
- `MainWindow._build_llm_battle_input()` is the natural collection point for
  future `field_profiles`

Why not `LLMAdvicePanel`:

- the advice panel should own controls and signals, not battle-state data
- it should not need to understand payload shape or field-profile semantics

Why not `PokemonPanel`:

- field state is not per-slot or per-Pokemon
- per-slot storage would duplicate global state and create ambiguous ownership

Recommended signal flow:

```text
LLMAdvicePanel.field_profile_requested
-> MainWindow._on_field_profile_requested()
-> FieldProfileDialog(current_profiles=self._field_profiles)
-> Apply stores self._field_profiles
-> _build_llm_battle_input(...) can include field_profiles when gated
```

## Limited Context Checkbox Relation

Button availability:

- The button may open even when the limited-context checkbox is off.

Payload behavior:

- Checkbox off must still omit `battle_state_context`.
- Checkbox off must still omit top-level `field_profiles`.
- Saved `MainWindow._field_profiles` must not reach the prompt unless
  `enable_battle_state_context=True`.
- Checkbox on can map valid saved `field_profiles` into
  `battle_state_context.field`.

Copy behavior:

- Do not change the checkbox copy in the first button implementation.
- A later copy update can mention user-confirmed field state after the button
  behavior is tested.

## Apply / Cancel / Reset State Behavior

Apply:

- stores `dialog.field_profiles` into `MainWindow._field_profiles`
- updates the field button/status indicator
- does not call Gemini
- does not change checkbox state

Cancel:

- leaves `MainWindow._field_profiles` unchanged
- does not call Gemini

Reset unknown:

- changes only dialog-local controls until Apply
- if Apply follows reset, store complete unknown field profiles or normalize to
  `None`; recommended first implementation stores the dialog's complete unknown
  dict for consistency with `default_field_profiles()`

Status display candidate:

- button text can remain stable
- an adjacent small status label or button suffix can indicate:
  - unknown
  - field set
  - field none

Recommended first implementation:

- keep the button label stable
- show a concise MainWindow status bar message after Apply/Cancel
- defer persistent visible summary until after smoke tests

## Future Tests

Recommended v12.15 FieldProfileDialog Button Integration Tests:

- button exists in `LLMAdvicePanel`
- button click emits a field-profile request signal
- button click opens `FieldProfileDialog` through MainWindow handler
- opening the dialog does not call Gemini
- button does not change limited-context checkbox default
- button does not change prompt guard wording
- Apply stores `field_profiles` in MainWindow session state
- Cancel preserves previous `field_profiles`
- Reset unknown plus Apply stores unknown/default field profiles
- checkbox off plus saved `field_profiles` still omits `battle_state_context`
- checkbox off plus saved `field_profiles` still omits top-level
  `field_profiles`
- checkbox on plus saved `field_profiles` maps to `battle_state_context.field`
- user-confirmed item mapping remains unchanged
- existing optional contexts still coexist

## Future Implementation Plan

Recommended sequence:

1. v12.15 FieldProfileDialog Button Integration Tests
2. v12.16 FieldProfileDialog Button Integration
3. v12.17 Field State UI Mapping Offline Smoke
4. later limited-context copy update for field state

## Safety Boundary

- button opens user-confirmed field input only
- button does not imply field data is sent unless the limited-context checkbox
  allows it
- checkbox off means no `field_profiles` in LLM payload
- known field is current context only
- known field does not imply duration
- known field does not imply expiration
- known field does not imply post-turn outcome
- known field does not imply damage precision
- known field does not imply full turn outcome
- opening the dialog does not call Gemini
- no field source from damage reverse inference
- no hidden field guessing

## No Production Code Change

v12.14 changes documentation only. It does not add a button, signal, storage
field, layout change, payload flow change, prompt guard wording change, or UI
copy change.

## No Actual Gemini Call

No actual Gemini call, retry, second provider call, Vertex AI call, or
network/provider call is part of v12.14.

## Next Recommendation

Recommended next:

- v12.15 FieldProfileDialog Button Integration Tests

Reason:

- the entry point and state ownership are now designed, but button click,
  apply/cancel/reset, session-local persistence, no-call behavior, and checkbox
  gate behavior should be locked before implementation.

Alternatives:

- v12.15 FieldProfileDialog Button Integration
- v12.15 Limited Context Copy Update for Field State

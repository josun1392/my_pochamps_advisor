# v12.58 Current Condition UI and Payload Foundation

## Purpose

Add explicit session-local input for current major conditions and connect it to
the limited-context `battle_input` candidate path. This milestone deliberately
does not add a condition payload section to the advisor prompt or run a provider
call.

## UI And Session Policy

- `Condition` opens a compact dialog with `self`/`opponent` and the supported
  major condition types.
- The button displays `Condition (N)` and the dialog summarizes saved values as
  `self: burn` or `opponent: unknown`, without exposing raw dictionaries.
- State is `MainWindow._current_condition_confirmations`, keyed by side. Apply
  replaces the existing condition for that side; both sides can coexist.
- `none` means the user confirms no current major condition. `unknown` means
  the user does not know the current condition. Neither is an event or an
  inference request.
- Cancel and invalid Apply preserve previous state. `Clear current conditions`
  is the explicit clear action. Checkbox toggles, advice, Pokemon/move changes,
  and dialog Cancel do not clear state.

## Candidate Mapping Boundary

With limited context off, stored conditions remain session-local and
`battle_input` omits `current_condition_confirmations`. With it on, valid
normalized conditions are placed in that `battle_input` candidate list in
`self`, then `opponent` order.

`build_current_condition_context_from_confirmations(...)` provides the future
candidate shape:

```python
{"current_conditions": [{"side": "self", "condition_type": "burn", ...}]}
```

The advisor payload filter removes `current_condition_confirmations` before
prompt serialization. Consequently v12.58 adds no natural-language condition
guard, no `condition_context` prompt payload, and no current-condition response
claim.

## Safety Boundary

All state passes through `normalize_user_confirmed_current_condition(...)`.
Future sources, resolved/post-turn/exact/RNG/order fields, and automatic
inference are rejected or omitted. No condition event UI, parser/replay/Turn
Engine, damage calculation, duration counter, thaw resolver, or speed-order
resolver was added.

## Status

`COMPLETE` - UI, session state, validation, limited-context candidate mapping,
and offline regression are complete. Prompt serialization is deferred.

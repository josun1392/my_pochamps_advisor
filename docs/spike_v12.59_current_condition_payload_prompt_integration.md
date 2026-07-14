# v12.59 Current Condition Payload and Prompt Integration

## Purpose

Connect the v12.58 session-local current-condition confirmations to the
limited-context advice payload without treating them as condition events,
resolved effects, or calculation inputs.

## Implemented Path

When limited context is enabled, the UI candidate list follows this path:

```text
current_condition_confirmations
-> build_current_condition_context_from_confirmations(...)
-> condition_context.current_conditions
-> _build_ui_selected_prompt(...)
```

The raw UI candidate key is removed before provider serialization. The mapped
context is present only when at least one candidate passes
`normalize_user_confirmed_current_condition(...)`.

```json
{
  "condition_context": {
    "current_conditions": [
      {
        "side": "self",
        "condition_type": "burn",
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
        "confidence": "known"
      }
    ]
  }
}
```

## Gate and Validation

- Limited context off keeps session state and the Condition count unchanged,
  but omits the raw confirmation list, `condition_context`, and its guard.
- Limited context on validates again at the payload boundary.
- Invalid individual candidates are omitted; all-invalid input omits
  `condition_context`.
- At most one valid condition per side is serialized, ordered `self` then
  `opponent`.
- Recursive forbidden fields remain rejected, including exact damage/HP,
  application or trigger claims, duration, thaw/full-paralysis, RNG, final
  order, resolved effect, and post-turn condition state.

## Meaning and Prompt Boundary

`condition_context` is user-confirmed present-state context only. The compact
guard distinguishes self from opponent and preserves the difference between:

- `none`: the user confirmed no current major status.
- `unknown`: the current major status is not known.

It forbids inferring application timing, a trigger/tick, exact status damage,
sleep duration, wake-up turn, freeze thaw, full paralysis, post-turn state,
RNG, or final order. It does not add a condition-event model or automatic
status detection.

## Offline Verification

Production-path mocked-provider fixtures cover self burn plus opponent unknown,
`none`, disabled gate behavior, invalid candidates, and coexistence with the
existing observed item-event context. No actual Gemini, provider, or network
call was made.

## Scope Preserved

Known item/current item, item event lifecycle and prompt attribution, field
state mapping, damage estimates, KO context, Q12, raw rolls, and provider retry
behavior are unchanged.

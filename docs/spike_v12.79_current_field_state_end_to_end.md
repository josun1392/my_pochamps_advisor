# v12.79 Current Field State End-to-End Integration

## Inventory

The existing `field_profiles` path is a calculation-oriented UI input and is
removed from the default advice payload. It remains unchanged. This change adds
a separate user-confirmed LLM trusted-context snapshot; it does not alter the
damage, speed, Q12, raw-roll, or core field-calculation paths.

## Contract

`user_confirmed_current_field_state` represents only a current identity
snapshot: weather, terrain, global effects, and side effects. It does not
represent start/end events, duration, source move/ability/item, resolved
effects, exact modifiers, HP, effective speed, final order, RNG, or post-turn
field state. Explicit `none` for weather or terrain means confirmed current
absence, not a just-ended effect.

Supported values are weather `none`, `sun`, `rain`, `sandstorm`, `snow`;
terrain `none`, `electric`, `grassy`, `psychic`, `misty`; global effects
`trick-room`, `gravity`; and side effects `reflect`, `light-screen`,
`aurora-veil`, `tailwind`.

## Integration

- Added one replaceable field snapshot in the UI with Apply, Cancel, Clear, and
  a compact count/readback.
- Limited context off retains the UI snapshot but omits its raw confirmation,
  normalized payload, prompt guard, and acknowledgement entries.
- The normalized payload is `field_state_context.current_field` and is
  validated again at the mapper boundary.
- Structured acknowledgement lines distinguish weather, terrain, global field
  effects, and side field effects. The parser exact-compares those entries to
  the normalized payload and rejects missing, extra, duplicate, category, side,
  or identity changes.
- The CLI evaluator retains its JSON and exit contracts and emits only a
  sanitized field mismatch category or forbidden-claim category.

## Validation And Status

Field-only, explicit-none, global/side-effect, combined condition/ability/stat
stage/item-event, invalid, limited-context-off, and absent-path contracts are
covered offline. Normal UI advice preserves the full structured block and
advice text; dialog actions do not invoke a provider.

Actual provider calls: none. Status: `COMPLETE - CURRENT FIELD STATE
END-TO-END GREEN`.

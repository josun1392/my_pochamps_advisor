# v4.3 Turn Snapshot Payload Adapter

## Purpose

v4.3 implements the optional payload adapter designed in v4.2. It allows callers to attach a validated `TurnSnapshot` as a top-level `turn_snapshot` section in the default LLM advice payload.

This is not a full Turn Engine implementation. It only serializes selected/pre-turn known state as optional context.

## Implementation

Added optional `turn_snapshot` support to:

```text
build_ui_advice_payload(battle_input, turn_snapshot=None)
_build_ui_selected_prompt(battle_input, turn_snapshot=None)
```

Adapter behavior:

- If `turn_snapshot` is `None`, payload output is unchanged.
- If `turn_snapshot` is a `TurnSnapshot` or mapping, it is normalized with `normalize_turn_snapshot(...)`.
- The normalized snapshot is serialized with `to_dict()`.
- The serialized snapshot is attached as top-level `turn_snapshot`.
- Snapshot-specific limitations are appended to `scenario.known_limitations`.
- Prompt guard wording is added only when `turn_snapshot` is present.

Validation behavior:

- Invalid snapshot values raise `ValueError`.
- The adapter does not silently coerce invalid state into battle truth.

## Prompt Guard

When `turn_snapshot` is present, the prompt states:

- `turn_snapshot` is selected/pre-turn known state context only.
- It is not full turn simulation.
- Do not claim full turn simulation.
- Do not claim exact item trigger result.
- Do not say an item was consumed from the snapshot alone.
- Do not claim exact post-turn HP.
- Do not claim guaranteed move order.
- Do not claim exact status resolution.
- Item trigger evaluation, item consumption, post-damage HP updates, speed/order simulation, and exact status resolution are not implemented.

## Intentional Non-Changes

v4.3 does not:

- implement full Turn Engine
- evaluate item triggers
- consume items
- update HP
- simulate speed/order
- change damage formula
- change raw damage rolls
- change Q12 multiplier
- change `ko_context`
- change item context behavior
- change default payload filtering when snapshot is absent

## Tests

Added advisor payload contract tests for:

- absent snapshot preserves default payload output
- present snapshot adds normalized top-level `turn_snapshot`
- mapping snapshot input is normalized
- invalid snapshot raises validation error
- prompt includes snapshot limitations and no-full-engine guard
- prompt omits snapshot guard when snapshot is absent
- damage estimate, `ko_context`, and item context payload sections remain unchanged except for top-level snapshot and snapshot limitations

Existing `tests/test_turn_state_snapshot.py` remains the base contract test for snapshot validation and serialization.

## Next Step

Recommended next milestone:

```text
v4.4 UI Selected State to TurnSnapshot Mapping Design
```

Before adding trigger logic, map the current UI selected active slot, HP percent, known item profile, selected move, and known status fields into `TurnSnapshot` in a controlled, testable path.

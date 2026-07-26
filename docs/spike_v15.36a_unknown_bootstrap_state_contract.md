# v15.36A Unknown Bootstrap State Contract

## Scope and normative bootstrap policy

New sessions trust only the explicit selected self identity, explicit selected
opponent identity, and session ID. Current/max HP, fainted, condition, known
item, weather, terrain, and side conditions begin unknown. The factory never
derives those facts from species metadata, damage estimates, provider output,
or a UI object. Unknown is not full HP, alive, known absent, or an empty set.

## Canonical state representation

`llm.advisor_reducer_state_model.UNKNOWN_BATTLE_FACT` is the immutable canonical
marker template:

```json
{"knowledge": "unknown"}
```

`make_unknown_battle_fact()` returns a detached marker, and
`is_unknown_battle_fact()` recognizes only its exact one-key shape. The marker
is valid only as a battle fact: Pokemon `current_hp`, `max_hp`, `fainted`,
`condition`, `known_item`; field `weather`/`terrain`; and a side's
`side_conditions` collection. A marker with extra fields or another knowledge
value is rejected.

Known absence remains the existing concrete representation: `None` for an
absent single condition/item/field value, `False` for a trusted living fact, and
`[]` for a trusted empty side-condition set. Thus these values fingerprint
differently from the unknown marker. Legacy concrete and legacy string
`"unknown"` reducer input remain accepted for compatibility, but the new
factory emits only the canonical marker.

## Factory and validation

`llm/advisor_initial_battle_state.py:create_unknown_bootstrap_battle_state()`
accepts a non-empty session ID plus detached selected identities as either a
non-empty `pokemon_id` string or an exact `{ "pokemon_id": ... }` mapping. It
returns `initial_state_ready` with exact `battle-state-v1`, active slot `0` on
both sides, known selected identities, canonical unknown facts, and neutral
`last_applied_observation_sequence=None`. Missing, malformed, or extra identity
input returns sanitized `invalid_initial_state` without partial state.

`BattleStateStore._valid_state()` now delegates marker checking to
`validate_battle_state_unknown_markers()`. It preserves all existing concrete
states, accepts mixed partially resolved states, and rejects malformed marker
shape. `ObservationReplayRuntime.create()` retains its exact top-level key
contract and therefore accepts valid unknown bootstrap states without changing
the schema version.

## Reducer, fingerprint, and persistence compatibility

The reducer recognizes the canonical marker where it previously accepted legacy
unknown values. An exact trusted HP observation can resolve unknown current HP;
unrelated unknown max HP, fainted, condition, item, field, and side conditions
remain unchanged. Condition and field set operations can resolve their own
unknown fact. Side-condition membership remains deferred while the entire set
is unknown, rather than falsely converting unknown into a complete list.

Canonical JSON fingerprinting already sorts JSON mappings, so the marker is
deterministic, detached copies preserve its fingerprint, and unknown differs
from known absence. Existing envelope save/load needs no production change: the
validated unknown state round-trips with the same store fingerprint.

## Tests and validation

`tests/test_v36a_unknown_bootstrap_state_contract.py` covers factory identity
only input, all unknown fact classes, known-absent distinction, malformed marker
rejection, concrete and partially resolved compatibility, deterministic detached
fingerprints, persistence round trip, non-mutating preview, trusted HP
resolution, unrelated-unknown preservation, CAS behavior, and prohibited
inference/import surfaces.

Focused result: `36 passed`.

Required related runtime/persistence/session result: `146 passed`.

Full offline validation: `2915 passed, 2 deselected`.

Compile validation passed for `llm/advisor_initial_battle_state.py`,
`llm/advisor_reducer_state_model.py`, `llm/advisor_battle_state_store.py`, and
`tests/test_v36a_unknown_bootstrap_state_contract.py`.

## Explicit exclusions and deferred work

No MainWindow, worker, UI lifecycle, provider, filesystem bootstrap, autosave,
startup recovery, persistence UI, cross-session import, undo/redo, or generic
unknown-inference engine was added. Side-condition partial-resolution semantics,
and v15.36 MainWindow manager/rollover/worker session wiring, remain future
bounded work. The next stage requires exact stage/commit/push approval.

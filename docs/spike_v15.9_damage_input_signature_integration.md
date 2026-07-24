# v15.9 Deterministic Damage-Input Signature Integration

## Runtime inventory

The structured candidate route is
`prepare_ui_recommendation_cycle` → `prepare_recommendation_cycle` →
`evaluate_move_slots` → `evaluate_move_candidate` →
`build_deterministic_calculation_context`. Candidate metadata is read from the
move repository at evaluation time. The separate legacy Q12 estimate route is
`MainWindow._build_llm_battle_input` → `attach_selected_move_damage_estimate`
→ `build_move_damage_estimate` → `DamageContext` → `calc_damage_rolls`.

The Q12 formula and its public API remain unchanged. Its legacy payload has more
species/type/stat material than `TurnSnapshot`, so this milestone does not route
Q12 through a lossy snapshot conversion.

## Detached signature

`build_snapshot_damage_input` consumes a frozen `TurnSnapshot`, exact candidate
slot/move, selectable set, and repository move metadata. It returns detached:

- `attacker` and `defender`: active snapshot identity, side, slot, and session
  when provenance supplies one;
- `move`: exact candidate ID/slot, owner identity, and copied metadata;
- `battle_context`: frozen current-state plus observed-event evidence;
- `calculation_limits`: final-stat and unsupported-modifier limitations.

`evaluate_move_candidate` now constructs this signature before its existing
deterministic context call and passes the signature's detached move mapping to
that call. A mismatch yields local `invalid_snapshot`; it neither replaces a
candidate nor creates a provider.

## Current-state mapping

HP, condition, stages, field state, ability/item evidence, and observed events
are preserved in `battle_context.current_state`. Existing deterministic helpers
consume only their already-supported contexts. Observed activation/consumption
is evidence, not an automatic item modifier or held-item inference. Base species
stats and move metadata are repository/legacy inputs; final stats, EVs, IVs,
nature, and unsupported modifiers remain unknown rather than fabricated.

## Isolation and gaps

The adapter deep-copies snapshot serialization and repository metadata, so later
UI/session, metadata-cache, event, or rollover mutations cannot alter its input.
The remaining gap is a full Q12/damage-engine signature integration: it requires
an explicit trusted bridge for types, base stats, and final-stat policy without
changing the formula. Provider/network calls: 0.

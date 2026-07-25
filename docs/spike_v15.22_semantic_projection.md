# v15.22 Reducer-Time Semantic Projection

## Purpose and baseline

`project_atomic_transition` is the private `battle-state-v1` dry-run layer
following the v15.21 field-mapping validator. It accepts a detached base state
and planned replay steps, validates them in reducer order, and returns a
detached future state only when the whole batch is valid. It is not runtime
reducer integration.

Existing helpers are deliberately separate: `build_replay_plan` partitions and
orders trusted candidate observations, `validate_atomic_transition` maps a
planned effect to its future field, and this helper applies semantic checks to
a temporary copy. No helper mutates UI, frozen snapshots, persistence, Q12, or
provider-facing payloads.

## Projection contract

Input requires `state_version: battle-state-v1`, matching base/plan/expected
session IDs, a `planned` plan without existing conflicts, non-empty ordered
unique step IDs, and each effect's target identity. Output has `status`, a
detached `base_state`, `projected_state` only for success, applied/rejected IDs,
conflicts, and limitations. Success is `ready_with_projected_state`; invalid
inputs use `invalid_base_state`, `invalid_replay_plan`, or
`unsupported_state_version`; an empty step list is `no_reducer_steps`.

## Semantic transition matrix

| Planned effect | Target | Required state / unknown policy | Idempotency and conflict | Projected result | Runtime mutation |
|---|---|---|---|---|---|
| exact HP | Pokemon HP | exact non-increasing ints; unknown current HP allowed; max checked when known | known HP mismatch conflicts | `current_hp=hp_after` | none |
| switch | Active slot | projected active must match switch-out; mapped incoming must not be fainted | silent, unknown, or mismatched ownership conflicts | active slot changes | none |
| faint | Pokemon fainted | false or unknown accepted | already true conflicts | `fainted=true`; HP is untouched | none |
| condition set/clear | Pokemon condition | set accepts none/unknown; clear needs exact known match | same set is no-op; other known value conflicts | set or clear | none |
| consume/remove item | Held item | exact known item required | none, unknown, or mismatch conflicts | clear item | none |
| weather/terrain start/end | Field effect | start accepts none/unknown; end needs exact known match | same start is no-op; incompatible value conflicts | set or clear | none |
| side-condition start/end | Side list | list state and explicit effect required | same start is no-op; missing end conflicts; stacks unsupported | append/remove | none |

## Ordering, atomicity, and provenance

Steps are ordered by `(observation_sequence, observation_id)` and apply to a
temporary projected copy, so HP → faint → switch works across sequences.
Independent same-sequence scopes may coexist. Same target transitions, and
same-side switch/faint pairs, require explicit `depends_on_observation_id`; no
event-kind priority is invented. Any semantic conflict returns no final or
partial projected state and reports all step IDs as rejected.

Changed fields carry only private minimal provenance: observation ID, sequence,
and supplied trust. On success, `last_applied_observation_sequence` is the
maximum reducer-step sequence. Inputs, nested data, and output are deep-copied;
repeating equivalent input is deterministic and idempotent.

## Boundaries, compatibility, and gaps

Exact observed HP transitions are the only HP reducer effect. Q12 damage/KO,
candidate recommendations, modifiers, provider schemas, legacy prompts, and
public confirmation payloads are unchanged and never applied. Provider budget
is zero.

Remaining gaps: actual runtime reducer/UI application, persistence, rollback
execution, trusted production lifecycle producers, Turn Engine, and modifier
integration. Offline contract tests cover detached projection, semantic
conflicts, unknown state, ordering, atomic rollback, provenance, immutability,
and Q12 non-application.

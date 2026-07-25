# v15.12 Complete Q12 Snapshot Invocation Adapter

`invoke_existing_q12_from_snapshot` is a pure boundary over the existing
`advisor.damage.formula.DamageContext` and `calc_damage_rolls` API. The legacy
`llm.advisor_damage_estimate.build_move_damage_estimate` path remains separate:
it keeps its existing default-assumption contract. The new path is only entered
with a detached v15.9 snapshot damage input and v15.10/v15.11 stat provenance.

| Q12 argument | Adapter source | Policy |
| --- | --- | --- |
| attacker/defender identity | frozen snapshot active identities | matching provenance and damage input required |
| move id/slot/owner | snapshot candidate signature | owner and non-negative slot required |
| move type/category/power | detached candidate metadata | type/power/category must be valid |
| attacker/defender types | repository metadata keyed by snapshot identity | no UI reread or neutral fallback |
| calculation stats | complete trusted final-stat provenance | no base-stat or partial-set fallback |
| level | explicit `trusted_level` argument | 1–100 only; no default level |
| modifiers/events | no modifier inputs supplied | evidence and unsupported state stay limitations |

Physical moves consume Attack/Defense; special moves consume Special
Attack/Special Defense. Status moves, missing final stats, missing level,
tampered owner identity, and invalid metadata return sanitized unavailable
results without calling Q12. Formula exceptions are similarly mapped to
`q12_calculation_failed` without exposing an implementation traceback.

The adapter supplies no ability/item, stage, weather, terrain, field, or
observed-event modifier. These remain explicit limitations; in particular,
observed activation/consumption is not converted to a held-item modifier.
`DamageContext` defaults therefore preserve the existing formula behavior
without claiming complete battle-state support. Q12 formulas and legacy callers
are unchanged. Structured candidate evaluation does not yet own a species
repository plus trusted level source, so production candidate wiring is
intentionally deferred. Provider/network calls: 0.

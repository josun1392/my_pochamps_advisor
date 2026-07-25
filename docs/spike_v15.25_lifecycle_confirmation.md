# v15.25 Trusted Lifecycle Confirmation Boundary

`LifecycleConfirmationBoundary` is a private structured-only producer. It owns
session-local observation IDs, deduplication, and sequence allocation; it does
not call the store, reducer, UI, persistence, or provider.

| Domain | Readiness | Source | Gap |
|---|---|---|---|
| Observed exact damage | production-ready | `ui_observed_damage_confirmation` | existing producer remains separate UI bridge |
| Used move, HP transition, switch/faint, lifecycle/field | fixture-only | `fixture_contract_confirmation` | no production confirmation UI/source |
| Selected move, HP snapshot, selection, Q12, current condition | not an event | none | never promoted |

Production requires confirmed `ui_observed_damage_confirmation` plus
`user_confirmed_observation`; fixture trust/source is rejected on production
paths. Fixture normalization remains explicitly available only with
`production=False`. Owner/session/payload validation happens before allocating
sequence. Duplicate identical IDs do not consume sequence; conflicting IDs are
reported; different IDs are separate occurrences.

Canonical output is for future structured snapshot collection only. It does not
mutate state or create history from current values. Provider budget is 0.

# v15.19 Lifecycle Contracts and Reducer Eligibility

## Inventory and separation

Current condition, known item, known ability, and field contexts are current-state evidence. Existing item activation and ability activation are observations. The repository has no confirmed apply/remove, consumption/removal, weather/terrain start/end, field-effect, or side-condition lifecycle UI producer; v15.19 therefore provides structured fixture/private-confirmation normalization only. Current state never manufactures history, and an event never mutates current state.

## Canonical contract and matrix

All records require `event_kind`, `scope`, observation ID/sequence, session, source/trust, observed/confirmed, and payload. Pokémon scope additionally requires matching side/slot/Pokémon; side scope requires side; field scope has no owner.

| kinds | eligibility | reducer prerequisite |
|---|---|---|
| condition apply/remove; item consume/remove; weather/terrain start/end; side start/end | candidate | explicit confirmation, valid scope/session/sequence, no conflict |
| item activation; ability reveal/activation | evidence_only | future semantics/timing policy |
| field effect start/end | unsupported | field stack contract |

No Q12 modifier is applied. Duplicate same IDs retain the first canonical record; conflicting same-ID input is not merged or replayed. Different IDs remain distinct occurrences. Ordering is sequence then ID. Replay remains inventory only: future work needs same-sequence conflict, unknown/unsupported event, partial failure, duration, overwrite, and rollback policies.

## Boundaries and gaps

Events are detached structured snapshot evidence only. No reducer, replay, automatic condition/item/ability/field/HP/active-slot update, provider payload change, or legacy/public payload change exists. Actual lifecycle UI/log producers, trusted turn input, conflict-resolution policy, and deterministic replay are still required. Provider budget: 0.

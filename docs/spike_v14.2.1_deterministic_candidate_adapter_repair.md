# v14.2.1 deterministic candidate adapter repair

An audit found that v14.2 candidate evaluation was metadata-only and could
fabricate resolved zero minimum/maximum damage. v14.2.1 removes those defaults
and adapts `evaluate_move_candidate` to the existing deterministic production
context. It copies only emitted production fields and introduces no new damage,
hit-chance, move-order, healing, recoil, or self-consequence calculator.

All ten dynamic families now exercise the repaired registry dispatch through
candidate evaluation. Ordinary moves retain metadata mechanics through that
context; missing registered context has no metadata power/type fallback.
Environment alone may emit effective type. Status moves retain
`damage.status=not_applicable`.

Candidate/evidence boundaries deep-copy snapshots and summaries. Slot handling
preserves order, original indexes, duplicates, empty-slot omission, and failure
isolation. Provider/UI orchestration is excluded.

Next: v14.3 resume and complete the preserved offline recommendation request
contract. No actual provider or UI orchestration is authorized.

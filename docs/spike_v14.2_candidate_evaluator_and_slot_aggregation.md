# v14.2 pure candidate evaluator and slot aggregation

The production UI stores move slots in `PokemonTeamColumn.selected_moves` and
the current selection in `selected_move_index`. v14.2 intentionally does not
wire UI: `evaluate_move_slots` accepts an explicit ordered sequence, supports
at most four entries, skips empty slots while retaining original indexes, and
preserves duplicate moves as separate candidates.

`evaluate_move_candidate` is pure and isolates metadata failures to one slot.
v14.2.1 replaces the former metadata-only damage summary with an adapter over
the deterministic production context; fabricated zero minimum/maximum defaults
are prohibited. Status moves are partial,
with `damage.status=not_applicable` and an explicit utility-ranking warning.
The evidence bundle copies snapshots/candidates, preserves order and reasons,
and has no provider fields. Provider/UI orchestration and ranking are excluded.

All ten dynamic families are exercised through the adapter; environment alone
may emit effective type, and missing registered context has no metadata
fallback. Ordinary moves retain metadata mechanics only through the production
context, and candidate summaries include only fields it emits. No new damage,
hit-chance, move-order, healing, recoil, or self-consequence calculator was
introduced. v14.3: resume and complete the preserved offline recommendation
request contract. No actual provider or UI orchestration is authorized.

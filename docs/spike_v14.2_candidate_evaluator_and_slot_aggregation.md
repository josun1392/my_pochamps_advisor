# v14.2 pure candidate evaluator and slot aggregation

The production UI stores move slots in `PokemonTeamColumn.selected_moves` and
the current selection in `selected_move_index`. v14.2 intentionally does not
wire UI: `evaluate_move_slots` accepts an explicit ordered sequence, supports
at most four entries, skips empty slots while retaining original indexes, and
preserves duplicate moves as separate candidates.

`evaluate_move_candidate` is pure and isolates metadata failures to one slot.
Damaging metadata yields a compact damage summary; status moves are partial,
with `damage.status=not_applicable` and an explicit utility-ranking warning.
The evidence bundle copies snapshots/candidates, preserves order and reasons,
and has no provider fields. Provider/UI orchestration and ranking are excluded.

v14.3 candidate: deterministic comparison guardrails and recommendation request
contract. Provider/UI orchestration remains unauthorized.

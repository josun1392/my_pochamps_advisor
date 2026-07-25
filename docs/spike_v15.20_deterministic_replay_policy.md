# v15.20 Deterministic Replay and Conflict Policy

`build_replay_plan(base_state, ordered_observations)` is a pure planner, not a
reducer. Its detached input uses `session_id`, a frozen reference base state,
ordered observations, and internal policy version `v1`. Its output partitions
accepted reducer candidates, evidence-only records, unsupported records,
excluded records, conflicts, and ordered future reducer steps.

Ordering is sequence then observation ID. Same-sequence IDs therefore have a
deterministic order but no invented event-kind priority. Same ID and same content
is duplicate/excluded; same ID with different content is conflict and blocks the
plan from being mutation-eligible. Different IDs remain separate occurrences.
Invalid or stale session/sequence is excluded without retagging.

Only eligible kinds receive planned-effect labels: HP/condition/item/weather/
terrain/side effects, switch, and faint. Evidence-only activation/reveal and
unsupported fields receive no step. The recommended future execution policy is
full atomic validation before mutation: planning preserves all history but never
changes base state, retries, Q12, modifiers, or provider data. Replanning same
input is idempotent. Actual base-state owner conflict, rollback, replay
execution, same-sequence semantic conflict, and state reducer remain future work.

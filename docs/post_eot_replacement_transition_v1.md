# Post-EOT faint replacement transition v1

The owner is `llm/advisor_post_eot_replacement_transition.py`. It consumes a
completed `exact-end-of-turn-residual-phase-ledger-v1` and returns detached
replacement requests, entry cursors, or a stable next-decision state.

## Contract and calling sequence

1. `post_eot_source_binding(eot_ledger)` identifies the exact session, decision,
   runtime, immediate terminal leaf, and full EOT ledger fingerprint. The
   terminal-context producer binds its branch and roster snapshots to this
   value. The caller independently passes the expected EOT fingerprint.
2. `freeze_post_eot_transition(...)` revalidates the EOT ledger and checks both
   active identities, HP, faint flags, condition mirrors, and known weather.
   The branch supplies the existing detached `current_state` representation;
   it must already contain post-EOT facts. Original D0 HP is never substituted.
3. Each team authority has `side`, `source_binding`, `status`, `completeness`,
   and `members`. Each member has an exact owner, `hp`, and explicit `eligible`
   authority. Complete rosters include the current active. Duplicate slots or
   Pokémon identities reject. Missing roster/HP/eligibility stays unknown.
4. `freeze_replacement_intent(...)` records a trainer's explicit choice from
   that request's candidates. The entire request generation and outgoing
   identity are bound. No probability or ranking is assigned to candidates.
5. `prepare_post_eot_replacements(...)` requires all requested trainer choices.
   Selected members supply the existing `incoming_authority`, an exact
   `entry_mechanics` snapshot, and, for double replacement, `entry_speed`.
   Both identities are materialized before any entry effects execute.
6. `post_eot_entry_binding(cursor)` identifies the next exact phase, side,
   incoming identity, and current branch fingerprint. A producer supplies
   `entry_authority = {source_binding, mechanics}` for that generation.
   `advance_post_eot_entry(...)` executes one canonical entry step and returns
   the next cursor. This permits a second ability's authority to consume
   weather/stages changed by the first ability.
7. When entry completes, the owner returns either a fresh replacement request
   after hazard KO, an exact battle-terminal result, or
   `detached_next_decision_state`. No automatic second trainer choice occurs.

## Ordering and mechanics reuse

`materialize_incoming_active_branch` owns identity replacement. The coordinator
splices only incoming-side current facts and retains recognized opposing and
field facts. Unknown identity-dependent fields are not copied to the incoming
Pokémon. Restriction rows for the outgoing side are retired from the detached
active view; surviving-side rows retain their original provenance.

`execute_materialized_switch_entry(..., defer_abilities=True)` reuses Stealth
Rock, Spikes, Toxic Spikes, and Sticky Web execution. The default entry executor
retains its previous behavior for voluntary switches and phazing.
`execute_materialized_entry_abilities` invokes the same existing Intimidate,
Download, weather, and Sturdy evaluators and the shared state appliers.

For double replacements the frozen effective entry Speeds determine order.
Both hazard steps finish before the ordered on-entry ability steps. Equal
Speed requires an exact resolved switch-in tie authority bound to both chosen
owners and the request; unresolved ties return incomplete. The coordinator
does not resolve that RNG or use Quick Claw/action priority as ordering evidence.
This tie authority describes an already-resolved mechanics branch, not a
trainer alternative distribution.

The branch's `post_eot_hazard_authorities` contains independently bound hazards
for each side. Each step checks its hazards against this current projection.
Toxic Spikes absorption updates that side's stored hazards. Poison/Toxic
overlays are carried per side, including the canonical predicted Toxic
lifecycle. Condition mirrors have explicit predictive provenance.

## State and provenance

Requests and cursors are copied value objects. `validate_post_eot_transition`
reconstructs the initial request and replays every recorded selection and entry
step; changing derived candidates, HP, hazards, active identities, requests,
or entry results fails validation. The frozen source retains original roster
evidence; each derived roster records its request and post-entry fingerprint.

A living active needs no replacement even if its bench is unknown. A fainted
active requires an exact complete roster to classify choices or exhaustion.
Known empty candidate sets produce `battle_terminal_no_replacement` only after
all members' availability is resolved. Both exhausted sides are reported as
mechanical inability to replace; match scoring/draw policy is not inferred.

Bench records preserve outgoing HP and major status, with historical Toxic
provenance separate from the unknown switch-retired counter. Surviving Toxic
progression is copied from EOT output. Leech Seed is retired with a switched
seeded target; a surviving seed's source-position reference follows the
replacement occupant and retains the historical source slot as provenance.

`handoff_end_of_turn_to_next_turn_start` removes prior turn action authority
before exposing a next-decision state. No reducer, observation, turn counter,
or committed history is modified. The strategy horizon remains
`immediate_action_consequence`.
The final lifecycle names the original EOT ledger fingerprint and the later
post-entry state fingerprint separately, and binds the replacement request.

## Boundaries and verification

This layer consumes exact producer snapshots; it does not discover roster
availability, choose replacements, rank them, commit observations, or perform
next-turn search. Unsupported entry mechanics (including Trace) and missing
entry interaction evidence remain incomplete. Existing future consumers must
honor the detached provenance when preparing the next decision.

`tests/test_post_eot_replacement_transition.py` covers classification,
explicit choices, both sides, hazard KO and a second explicit choice, hazards,
Intimidate/Download/weather/Sturdy, simultaneous identity establishment and
ordering, status/volatile retirement, EOT HP continuity, source immutability,
and replay rejection. Existing entry, EOT, pivot, restriction, Toxic, and ledger
tests provide shared regression coverage. Exhaustive validation uses a frozen
test-file manifest and checks selected/deselected coverage and exact-once
execution separately from focused runs.

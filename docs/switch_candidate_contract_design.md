# Trusted Switch Candidate Contract

## Scope and existing inventory

The Conservative projection is implemented in `llm/advisor_switch_candidates.py`. `build_switch_candidate_context_projection(...)` projects private runtime roster identity, fainted authority, and already-trusted target-owned HP/condition/item facts into the frozen handoff; `normalize_switch_candidate_context_projection(...)` binds it to the request-start selected active identity; and `build_switch_candidates(...)` emits detached internal candidates from the frozen turn snapshot. `prepare_ui_recommendation_cycle(...)` stores that collection only in its internal evidence bundle as `switch_candidates`. Provider-facing snapshot summary explicitly removes the private context.

`battle-state-v1` already stores a session-bound self roster under `self_side.pokemon`, keyed by team slot, with `pokemon_id`, `fainted`, HP, condition, and item as separate authorities; `self_side.active_slot_index` identifies the active member. Duplicate species therefore remain distinct slot/Pokemon identities. The existing reducer can record an observed switch and can mark a Pokemon fainted, while the request snapshot contract is detached and session-bound.

`fainted` is dedicated tri-state authority: explicit `true`, explicit `false`, or canonical unknown. HP is separate; this contract adds no HP-to-fainted inference. A replayed historical switch event records that a switch was observed, not that the same target is currently legal to choose prospectively.

## T1 Conservative policy

Every identity-known self roster entry other than the frozen active identity is a **potential switch target**. A potential target is represented even when it is not selectable. Empty or unassigned slots create neither target nor candidate; the active identity creates no switch-to-self action.

A bounded candidate has `action_kind=switch`, session ownership, target slot/Pokemon identity, identity/availability/legality supportability, `selectable`, and a bounded reason code. Its deterministic identity is `self-switch:{session}:{slot}:{pokemon-identity}`. It is separate from the existing self move namespace and never uses a fake move ID. Stable enumeration is canonical team-slot order, excluding active and empty slots; it conveys no rank, matchup, HP, species, or threat ordering.

## Availability and selectability

The candidate layers are intentionally separate: identity supportability, availability supportability, prospective switch-legality supportability, selectability, then future mechanics/ranking supportability.

| Trusted target state | Potential target | Selectable | Canonical reason |
| --- | --- | --- | --- |
| identity + `fainted=false` + legality complete/allowed | yes | yes | `switch_available` (future supported path) |
| identity + `fainted=true` | yes | no | `target_fainted` |
| identity + fainted unknown | yes | no | `target_availability_unknown` |
| availability complete + legality authority unknown | yes | no | `switch_legality_unknown` |
| availability complete + no supported restriction mechanic | yes | no | `switch_legality_unsupported` |

Unknown never means healthy, available, legal, or absent. A nonselectable candidate is still an application-owned representation of a real target identity; it does not assert that the Pokemon fainted or otherwise became unavailable.

Current implementation freezes a direct source-active `switch_permission_context` from trusted reducer authority. Missing/legacy/malformed permission is `insufficient_context`, `switch_legality_unknown`, and nonselectable; it is not a trapping-default policy. A trusted `permitted` authority can emit `switch_available`/`selectable=true`; trusted `blocked` emits `switch_blocked` and remains nonselectable. See `switch_permission_authority_design.md`.

## Prospective legality and historical events

There is no current trusted prospective authority/model for trapping, Shadow Tag, Arena Trap, Magnet Pull, Mean Look or other trapping effects, Ingrain-style restrictions, and other switch locks. Their absence from current state is not proof of absence in battle. If a required authority field exists but is unknown, legality is `insufficient_context`; if the mechanic has no supported authority/model, it is `unsupported_mechanic`. Under the approved Conservative policy either state is nonselectable.

The reducer's historical switch application intentionally only rejects an incoming member that is explicitly fainted. That behavior consumes a confirmed past event and must never be reinterpreted as prospective candidate legality or as permission to treat unknown fainted state as false.

## Session and frozen lifecycle

Candidates are request-start frozen and session-bound. An observation after capture, including a new fainted/available fact or active change, cannot alter the current candidate set; the next request may use the new authority. New sessions do not inherit target availability or legality, even for the same species. A Pokemon switched out and later returned to the bench keeps its slot/Pokemon session identity and its own HP/status/known-move authorities.

## External and action boundaries

Existing move candidates, move selectability, threat tiers, ranking, selected result, provider payload/schema/prompt, and selected-candidate presentation remain unchanged. Switch candidates remain a separate internal collection in this slice. The provider cannot create targets, resolve availability/legality, or promote an unknown target.

This contract does not simulate switching or post-switch combat: no switch action order, target replacement, opponent response, incoming attack, entry hazards, entry abilities, Regenerator, Intimidate, field changes, or hazard damage. There is no move-vs-switch or switch-vs-switch ranking, provider selection, or user-facing switch text.

## Future bounded stages

1. Implement the frozen Conservative switch-candidate projection.
2. Design switch transition and action-order authority.
3. Implement a hypothetical post-switch snapshot transition.
4. Evaluate known opponent actions against the switched-in target.
5. Design move-vs-switch ranking policy.
6. Integrate combined selection/provider contract.
7. Add bounded presentation and actual grounding.

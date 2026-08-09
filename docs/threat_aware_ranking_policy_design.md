# Threat-Aware Self Ranking Policy

## T1 policy

The policy is **partial-known positive-only** and is implemented by the internal `advisor_threat_ranking.py` projector: confirmed danger may penalize; unknown safety may not reward. Threat evidence is an application-owned deterministic adjustment above existing base mechanics ranking. It does not change candidate usability, provider authority, unknown-slot modeling, or probability semantics.

## Existing ranking integration point

The existing direct-mechanics ranker orders only complete native direct-damage candidates by deterministic mechanics evidence and retains stable slot order as its tie break. Threat-aware ranking is now a lexicographic layer after existing eligibility and before that existing deterministic rank. Equal threat tiers preserve the existing base rank and existing stable candidate order. The internal request retains only the summary needed for validation; the provider payload continues to receive no threat summary or tier field.

## Ordered categorical tiers

Lower number is more adverse; these are categories, not a scalar score.

1. `executed_guaranteed_ohko` — a known opponent action is allowed, non-preempted, and has executed guaranteed OHKO evidence.
2. `unresolved_guaranteed_ohko_exposure` — a known raw guaranteed-OHKO capability exists but pair order/preemption does not prove deterministic execution. It is weaker than executed loss and is not a deterministic-loss claim.
3. `executed_possible_ohko` — a known allowed, non-preempted possible OHKO exists.
4. `neutral_no_positive_threat_evidence` — no approved positive danger fact is proven. **Neutral never means safe.**
5. `complete_set_no_guaranteed_ohko` — only complete identity scope, complete mechanics, and `no_known_guaranteed_ohko=true` may grant this bounded safety tier.
6. `complete_set_all_actions_preempted` — only the same complete scope plus `all_known_actions_preempted=true` may grant this stronger bounded tier.

The final two tiers are unavailable for partial, unknown, or mechanically incomplete sets. No numeric KO probability breaks a category tie.

## Partial, complete, and uncertainty behavior

Unknown opponent moveset produces no threat adjustment. Partial set may penalize a self candidate for an executed guaranteed/possible threat or unresolved raw guaranteed-OHKO exposure. It may not reward absence of a known threat, lower known damage, no known priority, or all known actions preempted. Complete identity scope requires exactly four known moves, zero unknown slots, and complete threat mechanics before universal negative evidence enters the tier.

Raw guaranteed capability is not ignored when order is unresolved, but is deliberately weaker than executed guaranteed threat. When self deterministically preempts an action, that action supplies raw information but no executed threat penalty. Exact by1/by2/by3 remains supplemental pair evidence: it creates no score, weighting, expected outcome, or tie break.

## Boundaries

Threat adjustment changes only ordering in a future implementation. It must not make a candidate nonselectable, delete it, alter recommendation status, add a provider field, choose an opponent move, aggregate unknown slots, or introduce switch candidates. Provider and presentation remain unchanged until separate contracts authorize them.

## Future implementation prerequisites

The deterministic adapter composes its category ordinal with the existing base ranking tuple. Preserve summary scope/completeness fields for audit, but do not pass them to the provider. Any alternative policy—minimax, partial-set caution penalty, probability weighting, switch safety, or provider-facing explanation—requires a new T1 decision.

## Actual-grounding inventory

`partial-known-confirmed-threat-ranking` and `partial-known-neutral-no-safety-reward` are the approved sanitized provider fixtures. Each has a partial trusted opponent moveset with three unresolved slots. Preflight owns candidate IDs, selectability, base rank, threat tier, final deterministic rank, and provider-payload redaction. The provider remains limited to its existing minimal selection response; raw threat summaries, tiers, opponent moves, and pair evidence remain excluded.

The approved `gemini-2.5-flash` round passed both fixtures in order with two total calls. Retry, fallback, and repair counts were all zero. The first fixture confirmed the application-owned confirmed-danger penalty; the second confirmed that partial neutral evidence receives no safety reward. Only fixture status and call counts were retained; no prompt/payload text or provider response was retained.

## End-to-end contract closure

The canonical authority chain is: trusted identity/session-bound `known_move_context` → frozen active-opponent action candidates → opponent-to-self mechanics evidence → self/opponent pairs → per-self known-threat summary → categorical tier → existing base rank → stable order → provider minimal selection. Upstream ownership and lifecycle contracts remain canonical in `known_move_context_design.md`, `opponent_known_move_action_candidate_design.md`, `self_vs_opponent_pairwise_comparison_design.md`, and `known_opponent_threat_aggregation_design.md`.

The three grounding commits (`7f5e8f3`, `8f6c089`, and `fcfcac2`) only stabilized preemption-aware tier projection, its sanitized smoke runner, and fixture documentation. They did not alter provider schema, selectability, unknown-move modeling, probability ranking, or the partial-known positive-only policy.

Still unsupported: unknown-opponent move synthesis, move-choice probabilities, meta/species inference, scalar or probability-weighted threat scoring, expected outcomes, accuracy/critical/residual/recovery-aware threat, opponent switches, switch ranking, and multi-turn outcome trees. Future presentation, switch architecture, or new battle authorities require separate policy work.

# Self vs Opponent Pairwise Comparison Contract

## Scope

This is an implemented, application-owned internal contract. `advisor_pairwise_evaluator.py` creates one pair from each frozen self recommendation candidate and frozen trusted opponent action evaluation. It combines existing evidence read-only; it does not choose an opponent move, aggregate threats, alter self ranking, model unknown move slots, or change provider/UI contracts.

## Pair source, identity, and ordering

Pairs are the deterministic Cartesian product of available self candidate identities and frozen opponent action identities. The canonical logical ID is `pair:{session}:{self_candidate_id}:{opponent_action_candidate_id}`. Self candidate order is outer and frozen opponent known-move order is inner; this ordering has no strength, threat, or ranking meaning. A pair remains identity-valid when either mechanics side is insufficient or unsupported.

Opponent moveset state stays visible on every pair: unknown produces no pairs and means unavailable evidence, not no threat; partial produces pairs only for known moves and remains non-exhaustive; complete produces all four known-move identity pairs but does not imply a decision model or mechanically complete evidence.

## Reused evidence and ownership

The pair layer never recalculates Q12, direct mechanics, action order, move success, KO, or probability. It consumes self-candidate outgoing evidence (`self -> opponent`) and opponent-evaluator incoming evidence (`opponent -> self`). Self current HP is only the defender HP for the opponent action; opponent HP is only the defender HP for the self action. Move-success evidence remains independent on each side.

Pairwise action order calls the existing action-order helper with the specific frozen self move and frozen opponent move metadata. It may report self-first, opponent-first, speed tie, insufficient context, or unsupported mechanics. Priority differences avoid a Speed requirement; equal priorities retain the existing speed-stage, paralysis, item, ability, Tailwind, weather, and Trick Room chain. No aggregate "opponent goes first" conclusion exists.

## Deterministic preemption

The sole bounded immediate-outcome rule is deterministic preemption. A second queued action is `preempted` only when all of the following are complete: a specific first actor is known; that first action is allowed; and its deterministic OHKO result is `guaranteed`. This follows the normal fainted-Pokémon execution boundary without simulating later turns.

Possible OHKO, exact by1 probability, speed ties, unresolved order, blocked first actions, and status actions do not preempt the other action. Exact probability remains supplemental damage-roll evidence only; it never produces a partial execution tree or expected outcome.

## Pair supportability and candidate classes

Each pair preserves: identity, action order, self move success, opponent move success, self damage/KO/probability, opponent damage/KO/probability, preemption supportability, and pair mechanical completeness. `not_applicable` damage for status is a valid completed boundary, not an absent identity. Unsupported known moves likewise remain in the set with their unsupported layer. A pair is mechanically complete only when all layers necessary for its declared immediate interpretation are complete; partial candidate-set coverage is separately non-exhaustive.

Formula/formula pairs may reuse both damage and KO paths. Formula/status, status/formula, and status/status pairs retain action-order and move-success evidence without calling status damage zero. Fixed combinations reuse only their existing supported evidence. No new fixed, multi-hit, accuracy, critical, recovery, residual, or probability mechanics are introduced.

## Evidence and external boundaries

Pair evidence is pair-local and detached: it cannot overwrite or mutate either source candidate, and one pair cannot borrow another pair's damage, HP, KO, or probability evidence. The provider receives neither pairs nor pair summaries; it continues to select only existing self recommendation candidates. There is no presentation, threat label, provider schema change, or ranking/selectability effect.

`known_opponent_threat_aggregation_design.md` defines the next read-only grouping layer. It must preserve partial-set uncertainty and separate raw KO capability from pair-executed threat; aggregation and ranking are intentionally separate.

## Future bounded consumers

1. Define known-moveset aggregation while preserving partial-set uncertainty.
2. Define any ranking or switch policy separately.
3. Consider a probability outcome tree separately, without mixing it with deterministic preemption.

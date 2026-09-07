# Champions confusion action gating v1

This bounded family uses the supplied T2 Champions contract: modern persistent confusion duration, materialized once as an exact 2–5 opportunity branch, with an active opportunity branching to self-hit at 1/3 and selected-action execution at 2/3. An expiration opportunity snaps out before action and therefore has no self-hit branch.

The reducer stores only explicitly observed current-confusion provenance and a Pokémon-owned progression record. It never infers a first opportunity from a current confused label. Missing or stale progression is incomplete. Switching out clears the volatile record and prevents re-entry restoration.

The self-hit is a separate typed event: BP 40, typeless, physical, source equals target, self Attack versus self Defense including trusted stages, 16 exact damage-roll positions, no critical hit, STAB, contact, selected move, opponent damage, or selected-move terminal effects. A narrow Mimikyu `disguise_state` bridge records an intact disguise break without pretending it is an ordinary HP-only event; non-Mimikyu has no disguise consequence.

The additive immediate-pair owners run the confusion check when the actor reaches its action opportunity. A composite owner applies sleep/freeze first and opens confusion only on an executable wake/thaw branch. Sleep/freeze cancellation, flinch, and a prior KO leave confusion progression untouched. Self-hit branches carry no selected attack leaf and self-faint cancels the remaining action. Existing ordering remains frozen.

Own Tempo with an exact, unsuppressed binding rejects confused behavior. Neutralizing Gas suppresses that prevention. Tangled Feet remains an exact current-confusion reader boundary; this family does not introduce an evasion approximation.

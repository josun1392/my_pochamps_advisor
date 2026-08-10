# Switch Transition and Action-Order Contract

## T1 action-class policy

A normal self manual switch is an action with `action_kind=switch`, not a move, fake move ID, status move, or numeric move priority. In the first supported pair shape, its action class precedes every supported opponent move action:

`manual_switch > move`

Thus a successful, already-legal manual switch executes before opponent priority -1, 0, or positive-priority moves. Existing move priority/effective-priority/Speed ordering is not called or extended for this case. Speed, Tailwind, paralysis speed adjustment, static/dynamic speed modifiers, and Trick Room are `not_applicable` to switch-vs-move order. Pursuit-like special exceptions are unsupported unless a later canonical mechanic explicitly models them.

Opponent switch actions do not yet exist, so switch-vs-switch is `unsupported_mechanic`; no Speed, Trick Room, or simultaneous-order policy is implied.

## Dedicated first evaluator boundary

The existing pairwise evaluator remains move candidate × opponent move candidate. A future dedicated `advisor_switch_transition.py`-style adapter will consume one self switch action and one known opponent move without rewriting the closed move pairwise path. It will expose action kind, action-class precedence, order supportability, switch execution status, opponent queued status, transition supportability, and target-redirection supportability. It does not use move-success terminology for switch legality.

Prospective legality remains an earlier independent gate. The current Conservative candidates are nonselectable because restriction legality is unsupported. This order policy never promotes a candidate to selectable and is relevant only after a future legality layer establishes an executable manual switch.

## Detached successful transition

For a successful `A -> B` transition, frozen hypothetical state changes only self active identity from A to B. B receives B's own frozen identity, HP/max HP, fainted authority, persistent condition, current type, ability, item, and other represented Pokemon-owned authority. Unknown B facts remain unknown. A stays in the roster with A's identity and state; no canonical store, request snapshot, roster entry, or opponent candidate is mutated.

Self-side authority such as screens, Tailwind, and side conditions is preserved structurally. Shared weather, terrain, and Trick Room are also preserved. A's Pokemon-owned state is never copied to B.

## Stat-stage, volatile, and persistent-condition boundary

Canonical manual-switch semantics reset outgoing temporary stat stages to neutral and clear switch-cleared volatile conditions. The current request state stores stat-stage authority as active-side context, not safely as a roster-owned transition record, and it has no structured volatile-condition transition authority. A first implementation must therefore mark both reset/clear layers `unsupported_mechanic` until ownership is represented; it must not fabricate zero stages, cleared volatiles, or carry A's stages/volatiles to B.

Persistent conditions are not cleared merely by switching. B keeps B's own frozen burn/paralysis/poison/sleep or equivalent represented persistent condition; A's condition is not copied.

## Queued move target and entry effects

For the supported standard `selected-pokemon` opposing-single target, after successful A-to-B switch the queued opponent move targets B, not switched-out A. Future incoming mechanics therefore use opponent as attacker and B as defender through a thin transitioned-self snapshot adapter. Ally, spread, field, self, random, and retargeting-specific target shapes are unsupported in this first contract.

Entry hazards and entry/exit effects are preserved as authority where already known but never executed here: Stealth Rock, Spikes, Toxic Spikes, Sticky Web, Intimidate, weather/terrain abilities, Regenerator, Natural Cure, Trace, Download, and related mechanics are `unsupported_not_applied`. No target HP, status, stats, or field is silently changed; downstream incoming completeness must remain incomplete whenever those effects matter.

## Frozen and external boundaries

Transition output must be request-start frozen and detached. It cannot call the live reducer/UI/store or mutate the pre-state, target, old active, field, side state, or opponent action. There is no transition damage, action probability, switch ranking, move-vs-switch ranking, provider selection/schema change, or UI/presentation in this slice.

## Next bounded implementation

Implement the dedicated switch action-order and detached transition adapter, then evaluate a known opponent standard opposing-single move against the transitioned target. Entry effects, complex targets, opponent switches, legality restrictions, and combined ranking remain separate contracts.

# Priority generation and move-success contract closure

## Supported scope

The native action-order evaluator supports canonical move priority, trusted current Prankster on its own status-category action, trusted current Gale Wings on its own Flying-type action at exact full HP, trusted current Triage on its own canonically eligible healing action, trusted raw final Speed, Speed stages, paralysis Speed reduction, Choice Scarf, Swift Swim, Chlorophyll, Sand Rush, Slush Rush, side-owned Tailwind, Trick Room, and `speed_tie`. It produces candidate-local evidence; it does not resolve a provider-generated order.

## Canonical sequence

1. Validate trusted canonical base priority for each action.
2. Read canonical category, type, and numeric healing/drain metadata for that same action.
3. Resolve the same-side trusted current ability.
4. Apply Prankster `+1` only to a status action.
5. Apply Gale Wings `+1` only to a Flying action with exact request-start full HP.
6. Apply Triage `+3` only to a move with positive canonical healing or drain metadata.
7. Add each supported modifier to, rather than replacing, base priority.
8. Compare the two effective priorities.
9. Resolve differing priorities immediately without requesting Speed authority.
10. For a tie, hand off unchanged to final Speed, stages, paralysis, static Speed modifiers, Tailwind, comparison, Trick Room, then `speed_tie`.

The implementation reuses the existing stage, paralysis, Q12 item, and Q12 ability helpers. Final Speed is the trusted pre-battle-order-modifier value; no base-stat, EV, IV, nature, or provider inference is used.

## Priority move-success sequence

Candidate evaluation keeps action order and move success separate and fixed in this order:

1. Bind candidate identity, move metadata, and acting-side authority.
2. Derive base priority and apply Prankster, Gale Wings, and Triage once each.
3. Resolve action order; only an effective-priority tie enters the existing Speed chain.
4. Classify canonical target scope.
5. Independently evaluate Psychic Terrain, defender-side priority-blocking ability, and Dark-type Prankster immunity.
6. Merge complete block sources in deterministic order: Psychic Terrain, defender ability, then Dark-type Prankster immunity.
7. Mark a candidate selectable only when it has no complete block and its existing mechanics are usable.
8. Preserve damage/status evidence only for allowed candidates, pass the exact selectable set to the provider, and attach only selected server-owned evidence to presentation.

A blocked move retains its action-order and priority evidence, but it does not claim damage, KO, fixed-damage success, status success, healing consequence, or any state mutation.

## Authority and lifecycle

Request-start snapshots provide final stats, stages, conditions, item profiles, abilities, field state, and side conditions. Explicit known values are required for integration; explicit unknown is fail-closed for equal-priority comparisons. User-confirmed no-item/no-weather and known nonmatching ability or item are distinct from unknown. Malformed or known unsupported relevant modifiers are `unsupported_mechanic`.

Standalone evaluator arguments retain omitted-authority compatibility through private sentinels. The request snapshot is detached before candidates are evaluated, so later UI state cannot alter candidate evidence.

## Priority authority matrix

| Mechanic | Trusted applicable authority | Trusted non-applicable authority | Unknown | Malformed/conflicting |
| --- | --- | --- | --- | --- |
| Prankster | same-side ability + status category | physical/special or known non-Prankster | `insufficient_context` when relevant | `unsupported_mechanic` |
| Gale Wings | same-side ability + Flying type + exact full HP | non-Flying or exact not-full HP | `insufficient_context` when relevant | `unsupported_mechanic` |
| Triage | same-side ability + positive canonical healing/drain integer | valid zero/negative values or known non-Triage | `insufficient_context` when relevant | `unsupported_mechanic` |

Only one current ability is accepted per side. Duplicate or conflicting same-side ability authority is fail-closed; self and opponent may independently carry different supported abilities. Omitted standalone modifier authority preserves base-priority-only behavior, while explicit unknown is never converted to non-applicable.

## Priority-first and Speed handoff

After a priority difference, the result has `reason=priority_advantage` and `speed_comparison=not_needed`; it carries no applied Speed-stage, paralysis, item, ability, Tailwind, Trick Room, or tie evidence. Equal effective priority alone enters the existing Speed chain. That handoff does not reinterpret priority modifiers or alter integer rounding, Trick Room reversal, or tie semantics.

## Evidence and presentation

Each candidate retains its own `self_base_priority`, `opponent_base_priority`, resolved effective priorities, comparison basis, and only actually applied `self_*/opponent_*_prankster_applied`, `*_gale_wings_applied`, or `*_triage_applied` tags. Priority-resolved candidates contain no unnecessary Speed-modifier evidence. Missing or malformed Triage metadata is fail-closed when Triage is relevant. Recommendation results and presentation bind only the selected candidate's server-owned evidence. UI text never exposes effective Speed, multipliers, healing amount, exact HP, numeric priority, provenance, internal paths, unknown-as-absence, or a tie winner.

Priority generation does not imply move success, priority-blocking resolution, damage, healing amount, drain recovery, or HP mutation. Q12 formula evidence and level-based fixed-damage evidence remain independent from supported priority evidence.

## Priority-block move-success gates

The candidate layer separately applies narrow move-success gates after action order is resolved. With trusted current Psychic Terrain, an effective priority above zero, canonical `selected-pokemon` targeting, and the opposing target's trusted `known_grounded` state, the move is marked `blocked` with the bounded `psychic_terrain_priority` reason and is removed from the selectable set. Independently, a trusted current defender-side `queenly-majesty`, `dazzling`, or `armor-tail` blocks an opposing-single target move with effective priority above zero. These ability sources are recorded as `queenly_majesty_priority`, `dazzling_priority`, or `armor_tail_priority`; they require neither terrain nor grounded authority.

Known ungrounded targets, nonpositive priority, and self/ally/field targets are allowed by these gates only; that is not a general success guarantee. Unknown relevant terrain, defender ability, target scope, groundedness, or effective priority is fail-closed; malformed authority and complex/spread targets are unsupported. A complete block from either source short-circuits an unknown in the other source. When both apply, the candidate stays blocked with ordered source evidence (Psychic Terrain first) and a single bounded presentation. Omitted blocking-ability authority preserves the Psychic-Terrain-only narrow evaluator behavior. Psychic Terrain's damage boost remains separate from every move-success gate.

Dark-type Prankster immunity is a third, independent source. It is considered only when the same candidate already carries server-owned `self_prankster_applied` evidence for a status move with canonical opposing-single scope. The defender's request-start `current_type_context` must classify as `known_contains_dark`; pure and dual Dark types both qualify. It never follows merely from positive priority, so canonical positive-priority, Gale Wings, and Triage moves are outside this source. Current type is target/defender-owned, never falls back to species/base type, and remains distinct across omitted, explicit unknown, known non-Dark, and malformed values. A complete Terrain or defender-ability block similarly short-circuits unknown current type, while a complete Dark block short-circuits unknown Terrain or defender ability.

| Source | Required defender-side authority | Block condition | Non-applicable without inference |
| --- | --- | --- | --- |
| Psychic Terrain | trusted current terrain and target groundedness | Psychic Terrain + positive priority + opposing-single + grounded target | known ungrounded target, nonpositive priority, or non-opposing scope |
| Queenly Majesty / Dazzling / Armor Tail | trusted current defender ability | supported ability + positive priority + opposing-single | known non-blocking ability, nonpositive priority, or non-opposing scope |
| Dark-type Prankster immunity | trusted current target type | actual Prankster-applied status action + opposing-single + Dark target | known non-Dark target, non-applied Prankster, or non-opposing scope |

For every source, explicit unknown is `insufficient_context` only when that source remains relevant and no other complete source has already blocked. Malformed, conflicting, complex-target, or known unsupported relevant authority is `unsupported_mechanic`. Omitted standalone authority retains the prior narrow-helper behavior rather than being converted to explicit unknown.

## Provider boundary

The provider returns only recommendation status, selected candidate identity, and a bounded explanation code. It cannot supply or change ability, category/type, HP, healing/drain metadata, base/effective priority, Speed, stages, paralysis, item, weather, Tailwind, Trick Room, modifiers, or action order. A no-usable-candidate cycle makes zero provider calls.

It also cannot supply or change terrain, groundedness, current type, target scope, a priority block source, move-success status, candidate usability, or damage/status evidence. The application owns candidate-local source evidence and exposes only the selected candidate's bounded result/presentation evidence.

## Unsupported inventory

Quick Feet, Unburden, Speed Boost, Surge Surfer, Slow Start, Protosynthesis, Quark Drive, Booster Energy, Iron Ball, Macho Brace, Power items, Lagging Tail, Full Incense, Quick Claw, Custap Berry, Stall, Mycelium Might, conditional/dual-purpose healing moves without explicit positive numeric metadata, weather/Tailwind/Trick Room duration, full-paralysis probability, and Choice-lock strategy remain outside this evaluator. Ability suppression, Neutralizing Gas, Mold Breaker interactions, Terastallization and all type mutation, Protect, accuracy/evasion, ally redirection, and spread/partial target resolution are also excluded. Psychic Terrain and the three supported defender abilities support only direct opposing-single priority blocking. Known relevant unsupported mechanics fail closed rather than being treated as no effect.

## Grounding coverage and next step

Sanitized actual-grounding fixtures cover Prankster, Gale Wings, Triage, the Psychic Terrain priority-block gate, the defender priority-blocking abilities, and Dark-type Prankster immunity. Each pair uses a blocked or insufficient candidate plus a usable control, proving that the provider can see only the exact selectable control set. Offline coverage additionally fixes Queenly Majesty, Dazzling, target-side ownership, source ordering/short-circuiting, omitted-versus-explicit-unknown current type, species/current-type non-fallback, and non-selectable candidate behavior. No fixture converts an unknown authority to allowed or blocked, and no raw provider material is retained here. Further work should be a separate bounded proposal for an unsupported move-success mechanic, rather than expanding this contract implicitly.

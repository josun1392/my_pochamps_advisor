# Action-order contract closure

## Supported scope

The native action-order evaluator supports canonical move priority, trusted current Prankster on its own status-category action, trusted current Gale Wings on its own Flying-type action at exact full HP, trusted current Triage on its own canonically eligible healing action, trusted raw final Speed, Speed stages, paralysis Speed reduction, Choice Scarf, Swift Swim, Chlorophyll, Sand Rush, Slush Rush, side-owned Tailwind, Trick Room, and `speed_tie`. It produces candidate-local evidence; it does not resolve a provider-generated order.

## Canonical sequence

1. Validate canonical base priorities, move categories/types, and numeric healing/drain metadata; then apply trusted same-side Prankster only to status actions, Gale Wings only to Flying actions with exact full-HP authority, and Triage only to moves whose canonical `healing` or `drain` value is positive.
2. Resolve differing effective priorities immediately.
3. For equal priority, require trusted final Speeds.
4. Apply Speed stages, paralysis, supported static item/weather-ability modifiers, then Tailwind.
5. Compare adjusted integer Speeds.
6. Use normal order when Trick Room is inactive and reverse order when active.
7. Preserve `speed_tie` when adjusted Speeds are equal.

The implementation reuses the existing stage, paralysis, Q12 item, and Q12 ability helpers. Final Speed is the trusted pre-battle-order-modifier value; no base-stat, EV, IV, nature, or provider inference is used.

## Authority and lifecycle

Request-start snapshots provide final stats, stages, conditions, item profiles, abilities, field state, and side conditions. Explicit known values are required for integration; explicit unknown is fail-closed for equal-priority comparisons. User-confirmed no-item/no-weather and known nonmatching ability or item are distinct from unknown. Malformed or known unsupported relevant modifiers are `unsupported_mechanic`.

Standalone evaluator arguments retain omitted-authority compatibility through private sentinels. The request snapshot is detached before candidates are evaluated, so later UI state cannot alter candidate evidence.

## Evidence and presentation

Priority-resolved candidates contain no unnecessary Speed-modifier evidence. Prankster evidence appears only on the side-owned status action where it applied; Gale Wings evidence appears only on the side-owned Flying action whose exact request-start HP is full; Triage evidence appears only on the side-owned action with explicit positive canonical healing/drain metadata. Missing or malformed Triage metadata is fail-closed when Triage is relevant. Equal-priority evidence only records applied stages, paralysis, Choice Scarf, matching weather ability, Tailwind, weather basis, Trick Room, and tie outcome when applicable. Recommendation results and presentation bind only the selected candidate's server-owned evidence. UI text never exposes effective Speed, multipliers, healing amount, exact HP, numeric priority, provenance, internal paths, unknown-as-absence, or a tie winner.

## Provider boundary

The provider returns only recommendation status, selected candidate identity, and a bounded explanation code. It cannot supply or change priority, Speed, stages, paralysis, item, ability, weather, Tailwind, Trick Room, modifiers, or action order. No selectable candidate skips the provider call under the existing recommendation contract.

## Unsupported inventory

Quick Feet, Unburden, Speed Boost, Surge Surfer, Slow Start, Protosynthesis, Quark Drive, Booster Energy, Iron Ball, Macho Brace, Power items, Lagging Tail, Full Incense, Quick Claw, Custap Berry, Stall, Mycelium Might, conditional/dual-purpose healing moves without explicit positive numeric metadata, weather/Tailwind/Trick Room duration, full-paralysis probability, and Choice-lock strategy remain outside this evaluator. Prankster's Dark-target move-success rule, Triage healing consequences, and all Gale Wings HP mutation/approximation are also excluded. Known relevant unsupported mechanics fail closed rather than being treated as no effect.

## Grounding coverage and next step

Sanitized fixture contracts cover base/effective priority, Prankster candidate isolation, stages, Tailwind, Trick Room, paralysis, and static Speed modifiers with deterministic selected-candidate binding. Further action-order work should be a separate bounded proposal for one unsupported mechanic, rather than expanding this contract implicitly.

# v15.6 Deterministic Input Integration Baseline

Candidate preparation already consumes detached current-state from the frozen
request snapshot. v15.6 exposes a small deterministic-input adapter for the
same snapshot: active identities, selected move ID, and frozen current state.
Repository metadata remains keyed by snapshot move/Pokémon identity; exact
final stats, EV/IV/nature, and full damage-engine signature unification remain
out of scope.

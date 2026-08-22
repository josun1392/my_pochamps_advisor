# Predictive fixed-damage outcome adapter v1

The predictive fixed-damage adapter consumes only exact-complete
`deterministic-predictive-attack-authority-v1` for Seismic Toss. It is separate
from the observed candidate materializer and never creates an observed result.

After exact D0, candidate, attacker, target, and move validation, it forks the
current branch and applies the authority's resolved target-or-Substitute route.
The adapter validates that current state still agrees with the authority rather
than recalculating level damage, type immunity, or routing. It emits the normal
`deterministic-candidate-outcome-v1` schema plus predictive provenance, so the
existing comparator and ranker need no predictive-specific scoring rules.

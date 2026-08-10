# Move vs Switch Ranking Policy

## Implemented T1 decision: danger-only layer with same-tier Move preference

Cross-action comparison is application-owned and categorical:

1. `executed_guaranteed_self_ko`
2. `unresolved_guaranteed_self_ko_exposure`
3. `possible_self_ko_exposure`
4. `neutral_no_positive_danger`

Eligibility precedes danger. The layer never uses probability, damage range,
damage percentage, effectiveness scalar, expected value, or survival threshold.

Existing move-native ranking is unchanged and remains move-to-move only,
including its existing probability/damage tuple. No switch-native rank exists.
`llm/advisor_combined_action_selection.py` applies the final v1 ordering:

1. selectable action over nonselectable action;
2. lower proven danger;
3. existing native rank only between moves; and
4. on equal-tier move/switch comparisons, the move wins.

The last rule is bounded product policy, not a claim that a move is globally
better or that a switch is safe. It preserves the established move path while
entry effects leave every switch full outcome incomplete. Same-tier switches
remain an explicit `unresolved_equal_switches` tie set; enumeration order is
not a switch-native strategic rank.

Move mapping consumes existing threat tiers only. Switch aggregation consumes
candidate-local direct incoming KO labels across known actions. Partial known
evidence may penalize proven danger but cannot reward absence of danger. Since
entry effects are unsupported, switches cannot receive a safety reward even
with complete known moves; neutral never means safe.

`llm/advisor_cross_action_danger.py` implements projection and switch danger
aggregation. The combined selector consumes only those frozen projections and
precomputed move-native order; it does not inspect exact KO probability, damage
magnitude, effectiveness, or provider evidence for cross-kind comparisons.
Malformed ranking evidence fails closed without changing action legality.

This remains internal-only: current Conservative switch candidates stay
nonselectable, provider payloads remain move-only, and no presentation is
changed. A later integration policy is still required for provider/UI exposure
and for a strategic choice among equal-tier switches.

`combined_action_recommendation_flow.md` now connects the application-owned
selection envelope to the existing client: Move continues to its unchanged
provider branch, while selected or unresolved Switch results stay deterministic
and provider-free. Equal switch ties still require no artificial winner.

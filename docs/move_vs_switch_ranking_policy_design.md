# Move vs Switch Ranking Policy

## T1 decision: danger-only cross-action layer

Cross-action comparison is application-owned and categorical:

1. `executed_guaranteed_self_ko`
2. `unresolved_guaranteed_self_ko_exposure`
3. `possible_self_ko_exposure`
4. `neutral_no_positive_danger`

Eligibility precedes danger. The layer never uses probability, damage range,
damage percentage, effectiveness scalar, expected value, or survival threshold.

Existing move-native ranking is unchanged and remains move-to-move only,
including its existing probability/damage tuple. No switch-native rank exists.
Equal danger tiers across a move and a switch return
`tied_cross_kind_unresolved`: provider, slot order, probability, and damage do
not choose a winner. Same-tier switches are also unresolved.

Move mapping consumes existing threat tiers only. Switch aggregation consumes
candidate-local direct incoming KO labels across known actions. Partial known
evidence may penalize proven danger but cannot reward absence of danger. Since
entry effects are unsupported, switches cannot receive a safety reward even
with complete known moves; neutral never means safe.

`llm/advisor_cross_action_danger.py` implements projection, switch danger
aggregation, and comparison relations only. It is not connected to selection,
provider payloads, presentation, or existing move ranking. A later T1 policy
is required before combined move-vs-switch recommendation selection.

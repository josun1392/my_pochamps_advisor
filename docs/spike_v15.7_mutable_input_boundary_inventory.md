# v15.7 Deterministic Mutable-Input Boundary Inventory

Runtime flow: `MainWindow._start_structured_recommendation` deep-copies its
base input, `StructuredRecommendationWorker` deep-copies it again, then
`prepare_ui_recommendation_cycle` captures a `TurnSnapshot`, detached battle
snapshot, and candidate copies. `evaluate_move_slots` deep-copies snapshot
input per candidate. No candidate-stage UI/session reread was found.

Critical: none found. High: battle-input aliases are guarded by request and
candidate deep copies. Medium: repository metadata is passed to evaluation but
is read by snapshot-selected move ID; candidates do not mutate it. Low: frozen
TurnSnapshot and pure deterministic context helpers. Remaining gap: the full
damage-engine signature still accepts legacy context families outside this
structured preparation boundary.

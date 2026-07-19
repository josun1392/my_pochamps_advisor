# v13.9 Deterministic Accuracy and Hit Chance

Selected move `accuracy` comes directly from metadata. Repository move records
represent it as an integer or `None`; there is no canonical always-hit marker,
so `None` is `missing_move_accuracy`, never inferred as always-hit. A future
explicit `always_hit=True` metadata field is the only supported always-hit
representation.

Current accuracy/evasion stages reuse the existing user-confirmed stage
normalizer. Its existing omitted-stage behavior is neutral zero. Net stage is
accuracy minus evasion, clamped to -6..+6. The exact integer formula is
`base_accuracy * numerator // denominator`, then clamped to 100, using the
standard 3-based stage ratio. Scope is `move-accuracy-and-stages-only`.

Abilities, items, weather, Gravity, special move rules, OHKO accuracy,
immunity, move failure, and expected damage are excluded. Hit chance is a
separate deterministic result and never changes damage, KO, or move-order
results. Acknowledgement/parser rules exact-match move, percent/reason/scope;
semantic evaluation rejects modifier and immunity-overclaiming language.

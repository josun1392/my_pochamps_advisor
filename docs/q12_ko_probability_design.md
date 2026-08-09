# Exact Q12 KO Probability Contract

## Canonical sequence

For a Formula Q12 candidate, the application evaluates move success, damage supportability, Q12 damage, retained exact rolls, deterministic min/max KO interpretation, exact HP, and then exact cumulative KO probability. Probability consumes already-owned `exact_damage_rolls` and the same frozen defender HP authority used by deterministic KO; it never recalculates Q12 damage, min/max, STAB, effectiveness, modifiers, or HP. Ranking/selectability is resolved independently before the provider receives its minimal selection request.

## Exact authority

`calc_damage_rolls()` supplies the canonical ordered 16 non-critical Formula Q12 outcomes. The candidate-local immutable `exact_damage_rolls` tuple retains final-damage duplicates as multiplicity, and its extrema must equal the published damage range. Rolls are never reconstructed from min/max or from the legacy float `ko_result.single_hit_probability`.

Exact probability is stored as reduced integer numerator/denominator pairs. For exact positive defender HP `H` and independent draws from the same multiset `D`, the evidence is cumulative: `ko_by_1 = P(D >= H)`, `ko_by_2 = P(D1 + D2 >= H)`, and `ko_by_3 = P(D1 + D2 + D3 >= H)`. Integer-count convolution only is used; float, epsilon, and Monte Carlo authority are excluded.

## Consistency and supportability

`0 <= by1 <= by2 <= by3 <= 1`. Deterministic guaranteed/possible/no horizons must agree with exact fractions; possible OHKO remains the primary label even when `by2` is one. Explicit unknown HP produces deterministic-KO and probability `insufficient_context` while preserving a damage-supported candidate's usability. Malformed HP is unsupported, fainted targets are not applicable, and omitted HP preserves legacy damage-only compatibility.

Only complete single-hit Formula Q12 candidates receive exact probability evidence. Fixed, fixed-hit, variable multi-hit, status, priority-only, blocked, insufficient, and unsupported candidates do not receive Formula probability authority. Accuracy, critical hits, residual/recovery, hazards, survival effects, opponent actions, exact-turn probabilities, and probability-based ranking remain unsupported.

## Evidence, presentation, and provider boundary

Complete evidence records probability supportability, the three exact fractions, and `independent_repeated_noncritical_damage_rolls`. Evidence is candidate-local. Provider payloads and candidate summaries redact raw rolls and probability evidence; selected server-owned evidence alone may render one bounded damage-roll-only percentage. Exact `0%` and `100%` are reserved for exact fractions; intermediate extremes use `<0.1%` or `>99.9%`.

The legacy `single_hit_probability` float remains unchanged for existing consumers but is not exact authority and is never used to compose by2/by3. The provider remains selection-only and does not create or alter rolls, HP, deterministic KO, fractions, ranking, usability, or presentation evidence.

## Grounding inventory

`supported-q12-ko-interpretation` and `unknown-ko-hp-with-damage-supported-candidate` ground deterministic KO authority. `supported-exact-q12-ko-probability` grounds selected non-trivial exact probability; `unknown-ko-probability-hp-with-formula-control` grounds the selectable unknown-HP boundary. All fixtures locally preflight authority and use the provider only for its minimal selection response. They passed their approved actual grounding without retaining prompts, payloads, raw provider responses, or credentials.

See `q12_ko_interpretation_design.md` for the deterministic min/max horizon contract.

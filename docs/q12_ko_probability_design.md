# Exact Q12 KO Probability Design

## Inventory and decision

`advisor.damage.formula.calc_damage_rolls()` returns the canonical ordered 16 non-critical Gen 9 roll outcomes. Duplicate final damage values are therefore multiplicity, and the roll list is a uniform finite multiset. `advisor.probability.ko_chance_from_outcomes()` confirms this meaning: it returns the exact `Fraction` of outcomes meeting a target threshold.

The current direct-mechanics candidate result does **not** retain that multiset. It publishes min/max plus a float `ko_result.single_hit_probability`, calculated from the local total-roll multiset against the current HP used by direct mechanics. Thus the field is a one-action, non-critical damage-roll KO probability; it is not accuracy, hit chance, or a reusable exact PMF. Its float representation must not be used as exact authority for repeated-turn composition.

## Canonical future authority

A future implementation may consume a candidate-local ordered total-action outcome multiset (or an equivalent exact count PMF) captured at the same point as `damage_range`. It must preserve multiplicity and use `Fraction` internally. For exact HP `H`:

- `by1 = P(D >= H)`
- `by2 = P(D1 + D2 >= H)`
- `by3 = P(D1 + D2 + D3 >= H)`

`D1..D3` are independent identical draws only for the bounded repeated-action model. These values are cumulative, exact, and monotonic. The existing deterministic labels must agree: guaranteed means probability 1, no KO means 0, and possible means strictly between them. Possible OHKO remains the primary label even when by2 is 1.

## Boundaries

Exact trusted target HP is reused; unknown HP is insufficient, malformed/non-exact HP unsupported, zero current HP not applicable, and omission preserves legacy damage-only behavior. Accuracy, critical hits, residual/recovery, opponent actions, ranking, provider output, and Monte Carlo are excluded. Variable multi-hit needs a separately authoritative total-action PMF. Level-fixed and other point-mass totals can use `{damage: 1}`.

No production KO-probability evidence is added by this design. The implementation prerequisite is a server-owned candidate-local roll multiset/count PMF; min/max and the legacy float alone are insufficient.

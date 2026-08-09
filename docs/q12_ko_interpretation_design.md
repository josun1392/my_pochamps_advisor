# Q12 KO Interpretation Contract

## Status and scope

This contract is implemented as a read-only candidate-local layer. It consumes the existing server-owned total `damage_range` after move success and damage supportability are resolved; it neither recalculates damage nor changes ranking, candidate usability, or provider output. Formula Q12, fixed-hit formula with an already exact total range, and level-based fixed damage are supported. Variable multi-hit and special fixed damage remain outside the slice.

## Authority inventory

Formula Q12 and fixed-hit direct mechanics expose a canonical total minimum/maximum damage range. Fixed-hit mechanics convolve a fixed hit count before publishing that total range. Level-based fixed damage exposes the same range with equal endpoints. Variable multi-hit, special fixed-damage, status, priority-only, unavailable-damage, and move-success-blocked candidates are outside this initial KO-label slice unless a later contract explicitly supplies a total authoritative range.

The target HP source is a request-start, side/session/slot/Pokemon-bound `user_confirmed_current_hp` entry with exact integer `current_hp` and `maximum_hp`. The existing normalizer rejects percentages, decimals, approximate values, invalid ranges, and non-current sources. For a self action, target HP belongs to opponent; for an opponent action, it belongs to self. Omitted HP preserves damage-only compatibility. Explicit unknown/missing HP makes KO interpretation insufficient; malformed or conflicting HP is unsupported.

## Deterministic horizons

For total damage range `[min_damage, max_damage]` and exact positive target current HP `H`:

| Horizon | Guaranteed | Possible | No KO |
| --- | --- | --- | --- |
| 1 hit | `min_damage >= H` | otherwise `max_damage >= H` | otherwise |
| 2 hits | `2 * min_damage >= H` | otherwise `2 * max_damage >= H` | otherwise |
| 3 hits | `3 * min_damage >= H` | otherwise `3 * max_damage >= H` | otherwise |

Each horizon is internal evidence. A primary user-facing label uses this fixed order: guaranteed OHKO, possible OHKO, guaranteed 2HKO, possible 2HKO, guaranteed 3HKO, possible 3HKO, then no KO within the supported horizon. Thus a possible OHKO remains the primary label even if two minimum rolls also guarantee a 2HKO. `current_hp == 0` is `not_applicable`, not a KO label.

## Boundaries

KO labels consume exact current HP, not maximum HP or damage percentage. A percentage range is a separate presentation metric and cannot establish whether the target's current HP is crossed. Missing KO authority does not make an otherwise damage-supported candidate non-selectable. Move-success blocked candidates do not request HP, expose damage success, or expose KO labels; a secondary HP unknown cannot undo a complete block.

This contract does not model accuracy, critical hits, recovery, residual damage, hazards, status chip, Focus Sash, survival items, turn mutation, opponent action, or multi-turn simulation. Exact Formula Q12 damage-roll probability is a separate implemented read-only layer documented in `q12_ko_probability_design.md`; it preserves this deterministic primary-label precedence and does not alter it. It does not confuse a move's multi-hit count with turns-to-KO.

## Evidence and presentation contract

The implementation adds candidate-local `ko_interpretation` evidence with `defender_hp_authority`, `ko_damage_range_basis`, one/two/three-hit states, `primary_ko_label`, and `ko_supportability`. It attaches only selected-candidate evidence to result/presentation and does not expose raw HP, provenance/session identifiers, internal paths, or probability. Allowed bounded Korean meanings are 확정 1타, 난수 1타 가능, 확정 2타, 2타 가능, 확정 3타, and 3타 가능; missing authority may state that the current HP is insufficient to determine the number of hits.

Provider output remains the existing minimal selection contract. The provider does not create HP, damage range, KO state, KO probability, supportability, or KO evidence.

## Implemented evidence and presentation

Each supported candidate may carry `ko_interpretation` with `defender_hp_authority`, `ko_damage_range_basis`, the one/two/three-hit states, `primary_ko_label`, and `ko_supportability`. Omitted HP leaves that evidence absent for standalone compatibility; explicit unknown HP produces `insufficient_context`; malformed HP produces `unsupported_mechanic`; a fainted target is `not_applicable`.

Only selected-candidate evidence reaches presentation. The allowlist is limited to guaranteed/possible 1HKO, 2HKO, and 3HKO wording plus the separate selected-only exact damage-roll probability wording defined in `q12_ko_probability_design.md`; insufficient exact HP may state that the hit count cannot be determined. The UI does not display raw HP, provenance/session identifiers, internal paths, or evidence from another candidate.

## Next bounded work

Accuracy, critical hits, residual effects, recovery, survival mechanics, and variable multi-hit totals remain intentionally unsupported. The sanitized deterministic and exact-probability grounding fixtures are listed in `q12_ko_probability_design.md`; provider output remains selection-only in every fixture.

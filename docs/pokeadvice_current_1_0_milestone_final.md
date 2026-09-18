# PokeAdvice Current 1.0 Milestone Final

**Status:** FINAL  
**Milestone:** CURRENT PokeAdvice 1.0 mechanics/release-safety milestone  
**Code baseline:** `06e4e1b77fef145dad6249363dcb4e138c23e46c` (`feat: wire observed sleep freeze action results`)  
**Authoritative L3:** `5650 passed in 271.59s (0:04:31)`  
**Release-gate verdict:** `POKEADVICE_1_0_RELEASE_READY`

This document freezes the current PokeAdvice 1.0 mechanics/release-safety roadmap
baseline approved after the Roadmap A and Roadmap B closure audits. It is a
project milestone record, not a replacement package release or a renumbering of
the repository's historical Practical release lineage.

## Version-lineage distinction

This milestone is deliberately distinct from the repository's existing
Practical release/version history.

- It does **not** replace or rewrite historical Practical-1.0.
- It does **not** change the package version. `pyproject.toml` remains at
  `1.2.0`.
- It does **not** redefine Practical-2.0 or its deterministic-substrate record.
- It is the closure record for the **current PokeAdvice 1.0
  mechanics/release-safety roadmap** used by the recent Roadmap A/B audits.

Historical Practical-1.0, Practical-1.1, Practical-1.2, and Practical-2.0
records retain their original identities and meanings.

## Current milestone closure

The approved current roadmap state is:

- Roadmap A: `A_CLOSED`
- Roadmap B: `B_CLOSED`
- Required production scope: **Singles-focused**
- Doubles: `NOT_REQUIRED_FOR_CURRENT_SCOPE`
- Release-gate verdict: `POKEADVICE_1_0_RELEASE_READY`

Full Doubles production support is intentionally outside the current 1.0
milestone. Existing Doubles-related code may remain in the repository, but it
is not a closure requirement for this milestone and is not promoted to
near-term work by this record.

## Authoritative validation checkpoint

The authoritative full-suite checkpoint for the frozen code baseline is:

```text
5650 passed in 271.59s (0:04:31)
```

This result belongs to exact code baseline:

`06e4e1b77fef145dad6249363dcb4e138c23e46c`

No later code state should inherit this L3 result without a new authoritative
validation run.

## Historical finding ledger

Historical findings remain a tracking axis separate from Roadmap A/B/C and from
the release-gate verdict.

| Finding | Current release-gate state |
| --- | --- |
| NC-01 | `CLOSED` |
| NP-01 | `CLOSED` |
| NP-02 | `CLOSED` |
| NP-03 | `CLOSED` |
| NP-04 | `CLOSED` for implementation |
| NP-05 | `CLOSED` |
| NP-06 | `CLOSED` |
| NP-07 | `CLOSED` |
| NFV-01 | `RECONCILED_PRIOR_VERIFICATION_CONFIRMED` |
| NPO-01 | `DEFERRED_POST_1_0_NON_BLOCKING` |

Reconstructed NFV-02..04 labels are not independent additional findings when
they merely duplicate already-closed NP findings. Existing NP identifiers
remain canonical for those historical issues.

## NFV-01 reconciliation

The direct half-heal implementation is reconciled to the maintained shared
half-up rule.

Canonical current behavior includes:

```text
301 max HP -> 151 HP nominal half-heal
```

The maintained helper computes the plain Recover-family half-max amount with
half-up behavior, and the current regression contract fixes the same result
across the relevant direct-heal owners.

NFV-01 is therefore classified:

`RECONCILED_PRIOR_VERIFICATION_CONFIRMED`

Stale wording that fresh external verification is still required does not
describe the current reconciled milestone state.

NP-04 remains closed for its implementation concern: the relevant direct-heal
owners share the maintained canonical half-heal behavior rather than carrying
conflicting odd-max-HP rounding rules.

## NPO-01 deferred status

NPO-01 is **not** marked closed.

The narrow detached confusion-application concern remains a post-1.0 item:
missing `current_confusion` representation in that detached application area
can still warrant cleanup.

Current release classification:

`DEFERRED_POST_1_0_NON_BLOCKING`

The release-gate review did not verify a required current Singles 1.0
production caller that makes this concern a release blocker. The live
production confusion observation path remains separate and conservative.

## Fail-closed contract

The maintained core contract is:

`missing = unknown`

PokeAdvice at this milestone is **not** an exhaustive Pokémon battle simulator.

Unknown, stale, malformed, unsupported, or identity-mismatched authority must
remain, as appropriate:

- unknown
- incomplete
- unsupported
- rejected

Missing information must never silently become an evidentially unsupported:

- absent
- false
- none
- healthy
- stage 0
- no item
- no ability
- no hazard
- zero damage
- 100% HP
- certain outcome

The milestone therefore records bounded, evidence-backed production support,
not universal mechanics coverage.

## Release-ready conclusion

For the current required Singles-focused scope:

- Roadmap A is closed.
- Roadmap B is closed.
- the exact-baseline authoritative L3 is green;
- the historical finding ledger is reconciled for release;
- NFV-01 prior verification is reconciled;
- NPO-01 is explicitly deferred and non-blocking;
- Doubles is outside current scope;
- no required current Singles 1.0 release blocker was established.

The approved release-gate verdict is:

`POKEADVICE_1_0_RELEASE_READY`

## Post-1.0 boundary

Further mechanics or architecture work must be tracked outside the closed
Roadmap A/B milestone rather than appended implicitly to it.

Examples of post-1.0 work include:

- NPO-01 cleanup
- reflected-status architecture
- broader Fling support
- broader/full two-turn mechanics
- broader RNG reconciliation
- Roadmap C work
- later Doubles expansion
- RL work

This document does not define the complete Roadmap C scope and does not promote
Doubles to near-term work.

Any future expansion should preserve the same unknown-first, provenance-bound,
fail-closed contracts unless T1 explicitly changes the product requirements.

# Practical-1.1: Defender Type-Resist Berries

Practical 1.1 adds a narrow direct-damage slice for defender-owned type-resist
berries, including Chilan Berry. It is not a generic berry or consumable-item
engine.

## Supported prospective hit

The native Q12 direct-damage evaluator applies the existing canonical berry
modifier only when all of the following are trusted in the frozen request:

- the defender owns one exact currently held type-resist berry;
- the incoming move type and the defender's current typing/effectiveness are
  complete;
- the direct action is one fixed hit; and
- the berry's canonical trigger matches that hit.

Standard type-resist berries apply only to a matching super-effective hit.
Chilan Berry applies only to a damaging Normal-type hit with nonzero type
effectiveness. Matching berries halve that one supported hit before existing
damage, KO, and danger consumers run. Exact nonmatching berries leave the
direct result unchanged and complete.

## Authority and boundaries

An exact frozen held-item fact establishes availability only for the immediate
prospective hit. The evaluator does not predict consumption, carry the berry
to a later hit or turn, or model indirect damage. Unknown defender item
authority remains incomplete. A matching fixed multi-hit case is explicitly
unsupported rather than assuming one trigger covers the sequence. Existing
represented authority that is unknown continues to fail closed.

This change preserves Practical 1.0's ranking policy: it adds no berry reward
or score. A recommendation can change only when the existing deterministic
damage, KO, or danger evidence changes.

## Validation

Focused regressions cover a matching super-effective standard berry, exact
nonmatching behavior, Chilan's Normal-only condition, KO evidence reaching the
incoming-opponent path, unknown item authority, matching multi-hit rejection,
and unrelated item compatibility. Broader berry activation, healing/status
berries, consumption lifecycle, indirect damage, and turn simulation remain
outside this slice.

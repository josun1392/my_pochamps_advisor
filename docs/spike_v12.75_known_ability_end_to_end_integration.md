# v12.75 Known Ability End-to-End Integration

## Result

`COMPLETE - READY FOR ABILITY ACTUAL SMOKE`

This is offline readiness only. It does not authorize an actual provider call.

## Integrated Path

With limited context enabled, the existing UI/session raw confirmations are
revalidated into `ability_context.current_abilities`, then included in the
production advice payload. The prompt treats those entries only as
user-confirmed current ability identities. It does not treat them as species
possibilities, activation, suppression, replacement, copying, resolution, or
an exact stat, damage, HP, immunity, RNG, or order result.

The structured acknowledgement now accepts:

```text
- Current ability | <side> | <ability>
```

Expected entries come from normalized payload contexts, not raw UI input. The
parser normalizes only category case and ability spacing/kebab formatting, then
requires an exact ordered set with condition and observed-item-event entries.
Duplicate, missing, extra, side/category/identity changes, candidate lists,
and `none` are rejected.

## Evaluator And UI Boundaries

The sanitized CLI evaluator uses the same expected-entry/parser validator and
also rejects ability activation, suppression/replacement/copy/restoration,
resolved immunity/prevention, exact stat/damage modifiers, boosted-stat,
final-order, and unknown-ability inference claims. Its JSON schema and exit
codes are unchanged, and it never emits response text.

Normal UI advice continues to preserve the full `[Trusted Context]` plus
`[Advice]` response. The CLI JSON stays on the CLI path only. Dialog actions
remain provider-free.

## Matrix Coverage

Offline contracts cover self ability, opponent `unknown`, both sides,
ability-plus-condition, ability-plus-item-event, all three categories,
limited-context-off, invalid `none`, candidate lists, and absent context.
Each case validates payload mapping, prompt requirement, expected entries,
parser/exact-set validation, semantic boundary checks, and CLI evaluator
status.

## Safety

- Actual Gemini/provider/network calls: none.
- No credential or token-log inspection.
- No automatic ability detection or species/meta inference.
- No activation, suppression, replacement, resolver, damage, speed, or turn
  engine implementation.
- No payload-schema, CLI-schema, exit-code, dependency, or core calculation
  changes.

# v13.29 dynamic move production coverage

The coverage manifest is derived from the registry and covers all 30 moves in
ten families. Validation fails closed on missing, extra, family-drifted, or
assessment-key-drifted entries.

## v13.31 correction

Registry-self-derived coverage alone was insufficient: a repository audit
found the deterministic production path still used direct multi-family helper
fan-out. v13.31 now dispatches each registered move through one
registry-selected resolver. Production-path tests exercise the actual
deterministic context builder for all ten families, while an independent
30-move limited-context matrix verifies missing required context fails closed
without metadata fallback. Environment alone may override effective type; all
other families are power-only. The formulas and 10-family/30-move inventory
are unchanged.

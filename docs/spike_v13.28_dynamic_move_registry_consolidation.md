# v13.28 dynamic move registry consolidation

The registry contains 30 canonical moves across ten families: current HP (5),
speed (2), weight (4), stat stage (3), target HP (2), environment (2), binary
condition (4), turn event (4), battle counter (2), and consecutive use (2).

`resolve_registered_dynamic_move` selects one family only. It returns an
assessment key/payload plus optional power and type overrides. Missing context
returns the selected family's unavailable payload without metadata fallback;
ordinary moves are not registered. Registry validation rejects unknown,
noncanonical, or helper-allowlist-drifted registrations.

## v13.31 correction

The registry was complete, but a subsequent repository audit found that the
production deterministic-context path had not yet consumed its single selected
resolver. v13.31 removes the direct multi-family production fan-out: canonical
registered moves now select exactly one family through the registry. This
preserves ordinary unregistered metadata power/type, fails closed for missing
registered context, and permits effective-type override only for environment
moves. The formulas and ten-family/30-move inventory are unchanged.

# v15.69 canonical status-move role evidence

## Boundary

Selectable status candidates receive separate `status_move_evidence`; status
does not become zero damage and does not enter the direct-damage rank order.
The source is only normalized canonical move metadata: category, target,
PokeAPI meta ailment/category/healing, and stat changes.

## Bounded result

`known_role` carries only proven role tags (currently recovery, self stat
raise, target stat lower, status infliction, or a canonical-effect-backed
utility fallback), effect-presence tags, and target scope. Missing target or
effect metadata stays `insufficient_context`; malformed stat-change metadata
is `unsupported_mechanic`. Damage candidates receive `not_applicable`.

## Integration and safety

Role evidence is candidate-local, yields bounded comparison tags, and is
copied only with a resolved candidate's validated evidence. Presentation maps
role tags to Korean labels without exposing effect tags, paths, raw metadata,
or strategic utility claims. No provider, credential, or network activity is
part of this slice.

## Offline validation

Nearest and related candidate/presentation contracts passed, followed by the
full offline suite and Python compilation. No ranking, mechanics calculation,
or provider schema behavior was broadened.

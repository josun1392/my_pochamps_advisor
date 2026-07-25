# v15.10 Type/Base-Stat/Final-Stat Provenance Bridge

## Runtime inventory

`PokemonRepository.get` returns `PokemonView` metadata: identity, `types_en`,
and species `base_stats`. MainWindow's payload already copies these as reference
data. `StatProfileDialog` can record user-entered final stats, while current
final-stat and stage confirmation contexts are normalized separately. The legacy
Q12 estimate path still creates `DamageContext` through
`build_move_damage_estimate`; no formula or public Q12 API changed.

## Provenance bridge

`build_snapshot_stat_provenance` takes a frozen `TurnSnapshot` and looks up each
active species by that snapshot identity only. It returns detached blocks for:

- types/base stats: `repository_metadata` / `deterministic_metadata`;
- final stats: available only when all six provenanced user-confirmed values
  exist; never substituted from base stats;
- stat stages: separate provenanced values, with no implicit zero;
- known item/ability: explicit item only when the snapshot marks it confirmed;
  ability remains unknown unless a future trusted bridge provides it;
- limits: no EV/IV/nature/level/hidden-modifier inference.

Missing metadata is explicit unavailable. A repository record whose identity
does not equal the snapshot species raises a local identity failure rather than
being repaired.

## Q12 boundary

`build_q12_input_adapter` validates detached types, base stats, and complete
final stats before returning a `ready_for_existing_q12_boundary` signature. It
does not call or modify Q12. Missing final stats yield
`final_stats_unavailable`; observed events remain evidence and are not item or
ability modifiers.

## Remaining gap

The structured capture path has no complete final-stat producer bridge yet, and
the Q12 invocation continues to use its legacy payload. A future change needs a
separate trusted type/base-stat/final-stat transfer contract before replacing
that path. Provider/network calls: 0.

# Current type damage authority design

## Status and inventory

The snapshot Q12 and native direct-formula candidate paths now resolve their type inputs through this contract. `build_snapshot_stat_provenance` supplies a side-owned type block to both paths: trusted known current types override repository species metadata, while omitted context preserves the legacy species bridge. The request-start `current_type_context` remains detached, side-bound, and excluded from provider payloads. The older `build_type_aware_damage_estimate` path remains a separate legacy presentation calculation and is not widened by this bounded integration.

Move type remains canonical move metadata. It is neither inferred from a name nor supplied by the provider.

## Canonical authority precedence

For a future Q12 type adapter, resolve each needed side independently:

| Current type context state | Type source | Damage supportability |
| --- | --- | --- |
| trusted known, one or two types | that side's `current_type_context` | type input is known |
| explicit unknown | no type source | `insufficient_context` when STAB/effectiveness is needed |
| malformed, duplicate, conflicting, stale, or invalid provenance | no type source | `unsupported_mechanic` |
| omitted entirely | existing side-owned species/base type bridge | legacy-compatible only |

Known current type replaces, rather than augments, the legacy species/base list. A single current type may replace a species dual type and a current dual type may replace any legacy list. Species/base type is never a fallback for explicit unknown or malformed current type. It remains an identity/legacy compatibility source only while `current_type_context` is omitted.

## Ownership and type operations

For a self action, STAB reads self's resolved type authority and effectiveness reads opponent's resolved type authority. For an opponent action the roles reverse. No helper may exchange, merge, or reuse the sides' type authority across candidates or requests.

STAB is `calc_stab(resolved_attacker_types, canonical_move_type)` with no inferred type and no implicit Terastallization. A move matching either member of a current dual type receives ordinary STAB; a known non-match is complete neutral STAB, not missing authority.

Effectiveness is `type_effectiveness(canonical_move_type, resolved_defender_types, load_type_chart())`. The existing chart handles single and dual targets: type ratios multiply, so double weakness/resistance remain intact and any immunity makes the product zero. This design does not create a second chart.

## Supportability and candidate boundary

STAB and effectiveness are independent inputs. Known attacker type plus unknown defender type establishes STAB but not exact type-aware Q12; the reverse also applies. Both known inputs make the type portion complete. Unknown is never upgraded to no-STAB or neutral effectiveness.

The future adapter applies only to formula Q12 candidates. It does not make type authority mandatory for pure status, priority-only controls, or level-based fixed damage. Canonical fixed-damage type interaction remains the existing fixed-damage contract until separately inventoried; this design deliberately does not reinterpret it. A candidate already blocked by a move-success gate remains non-selectable and exposes no successful damage outcome regardless of whether its type inputs are known.

## Lifecycle, evidence, and provider boundary

Only request-start frozen `current_type_context` may override legacy types. New/reset sessions start explicit unknown; stale session-bound entries are rejected. Provider output cannot create current type, STAB, effectiveness, immunity, or type-related supportability.

Candidate-local internal evidence distinguishes `attacker_type_authority`, `defender_type_authority`, `stab_basis`, `effectiveness_basis`, `legacy_species_type_compatibility_used`, `current_type_override_used`, and `type_related_damage_supportability`. Presentation must not expose raw type lists, provenance/session identifiers, internal paths, or numeric multipliers.

## Implementation boundary and next goal

The bounded adapter reuses the existing frozen context, `calc_stab`, and Gen 9 chart; it does not alter Q12 multiplier order. It preserves weather, terrain, burn, screen, ability, item, fixed-hit, priority, and move-success contracts. Level-based fixed damage keeps its existing legacy type boundary. A later goal, if authorized, may add trusted current-type updates for type mutation; it must not add Terastallization, provider schema changes, or expected-outcome ranking implicitly.

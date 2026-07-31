# v15.62 deterministic direct-mechanics linkage

Repeated complete-direct actual responses reached the bounded
`mechanics_numeric_scope_invalid` diagnostic because provider-generated path
and scope fields were part of the response contract. This slice removes those
fields from the single direct-mechanics provider claim shape.

The provider returns only a claim kind and text for the already selected exact
candidate. `damage_value`, `damage_percent`, and `ko_probability` map to one
canonical native scope; `value_free_mechanics` has no numeric linkage; and
`partial_context` is available only for an insufficient native result. The
application resolves the candidate, builds the canonical internal path/scope,
and reuses the strict native numeric exact-match validator.

Provider-supplied linkage fields, an unresolvable candidate, a numeric-free
numeric claim, an ambiguous native scope, or numeric text in a value-free
claim produce bounded diagnostics. The existing acknowledgement path and
incomplete missing-input dependency remain deterministic application evidence.
Multi-move binding, action-order evidence, damage ranking, unknown-first
handling, retry/fallback/repair policy, and native mechanics computation are
unchanged. Offline validation only; actual calls require the separately
approved round after commit and push.

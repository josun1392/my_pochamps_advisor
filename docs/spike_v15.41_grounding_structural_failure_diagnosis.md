# v15.41 Grounding Structural Failure Offline Diagnosis

## Observed boundary

The approved v15.40 actual smoke received and decoded one structured response
for `runtime-unknown-bootstrap`, then stopped at structural grounding exit 6.
No response text, payload, credential, or provider metadata was retained or
used for this diagnosis. Actual provider execution is not repeated by v15.41.

## Production-path evidence

The runtime path is provider payload -> `call_structured_recommendation_provider`
-> decoded mapping -> `adapt_provider_recommendation_response` ->
`validate_runtime_grounding`. Runtime-bearing completion already required a
`grounding` member, and the adapter already preserves a valid grounding mapping.
The mismatch was earlier: the provider response schema and decoded exact-key
check allowed only the legacy six recommendation fields, while runtime grounding
required the seventh `grounding` field. A schema-conforming provider therefore
could not return the required mapping.

## Minimal alignment and compatibility

When `runtime_advice_state` is present, the production schema now requires
`grounding` with `schema_version=grounding-v1` and the exact five entry lists:
`confirmed_facts`, `unknown_facts`, `evidence_only`, `conflicts`, and
`conditional_dependencies`. The decoded response boundary accepts that exact
seven-field shape. Requests without runtime state retain the existing six-field
schema and compatibility lane. Runtime authority and semantic policy are
unchanged.

## Safe structural diagnostic taxonomy

The validator returns at most one bounded code for a structural failure:
`grounding_missing`, `grounding_not_mapping`, `grounding_version_missing`,
`grounding_version_invalid`, `grounding_entries_missing`,
`grounding_entries_not_list`, `grounding_entry_not_mapping`,
`grounding_entry_field_missing`, `grounding_entry_field_invalid`, or
`grounding_unknown_field`. The smoke runner keeps exit 6 and exposes only its
diagnostic code in its in-memory result; no raw response value or key inventory
is emitted. Semantic failures remain exit 7 and internal metadata remains exit
8.

## Offline verification and execution gate

Offline tests cover every structural category, runtime schema requirement,
adapter preservation, semantic/internal exit preservation, and a fake
`runtime-unknown-bootstrap` structural pass. They use no credential, provider,
or network activity. A future actual rerun requires new T1 approval.

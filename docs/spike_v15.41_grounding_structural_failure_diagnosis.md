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

## CLI diagnostic surface

The prior actual smoke reached exit 6 but the runner CLI printed no result, so
its bounded validator diagnostic was unavailable for reporting. The runner now
passes `fixture_id`, `failure_category`, and an allowlisted
`structural_diagnostic` from validation to its in-memory smoke result and emits
one sanitized JSON line at the CLI boundary. The line contains only fixture ID,
failure category, diagnostic code, exit code, and provider call count. It never
contains a grounding value, provider material, prompt, payload, credential, or
internal metadata. Non-structural outcomes omit the structural diagnostic;
existing exit 6/7/8 meanings are unchanged. This is offline-tested only and
does not authorize an actual rerun.

## Entry-path requiredness follow-up

One newly approved actual call stopped at `runtime-unknown-bootstrap` with the
bounded code `grounding_entry_field_missing` (exit 6, one call). The response
schema previously described each grounding list item only as an object, while
the validator required its canonical `path` field. The minimal offline fix adds
that field as required to every grounding-v1 entry schema and states the same
requirement in the structured guidance. No grounding semantics, authority rule,
or fixture was changed. The next actual smoke requires separate T1 approval.

## Semantic diagnostic follow-up

The next approved actual call reached semantic exit 7 at the same first
fixture. Structural validation had passed, but the existing CLI exposed no
bounded semantic validator code. The smoke result and CLI now also preserve
only the existing allowlisted semantic validator codes; they still exclude raw
grounding values and provider data. No additional actual call is made by this
change; a separate T1 approval is required to identify the exact semantic code.

## Fixture projection follow-up

The next approved call surfaced `grounding_fact_missing_or_duplicate` at
semantic exit 7. Offline inspection showed that the smoke runner supplied one
weather-only runtime projection for every fixture, despite the existing fixture
contract covering active HP, fainted, condition, item, field, and side facts.
It also supplied only an opaque fixture ID for the stale-item case. The runner
now builds the existing fixture-specific provider-safe projection, including
the authoritative Focus Sash fact and stale Choice Scarf evidence, and validates
against that same projection. This preserves unknowns and authority semantics;
the next actual call needs separate T1 approval.

## Runtime-authority contradiction follow-up

The next approved round passed the unknown fixture and stopped at the known
item fixture with `runtime_fact_contradiction` (semantic exit 7, two calls).
For that fixture the runtime's known Focus Sash item is the only known fact, so
the bounded code identifies a confirmed grounding status or value that did not
reproduce that authority. The prompt and smoke payload now explicitly require
confirmed entries to reproduce known runtime facts exactly and restrict stale UI
evidence to `evidence_only` or `conflicts`. No runtime authority policy or
validator meaning changed; a further actual round uses standing approval.

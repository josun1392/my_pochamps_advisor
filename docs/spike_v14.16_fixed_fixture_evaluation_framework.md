# v14.16 Fixed-Fixture Evaluation Framework

## Purpose

This offline framework supplies a versioned, deterministic catalog for future
T1-approved structured-provider samples. It does not call a provider, estimate
cost, or claim statistical reliability. It reuses production preparation,
decoded-response adaptation, semantic completion, and presentation boundaries.

## Catalog

The catalog contains ten sanitized fixtures: `clear_resolved`, `close_resolved`,
`insufficient_context`, `no_selectable_candidates`, `invalid_alternative`,
`slot_mismatch`, `unsupported_claim`, `partial_context_valid`,
`partial_context_contradiction`, and `no_usable_candidate`.

Every fixture declares its identifier, expected preparation status, selectable
count, expected recommendation status, semantic result, failure code when
applicable, and whether provider invocation would be allowed. The data contains
only generic identities, trusted deterministic inputs, and six-field structured
response shapes; it has no provider prose, request payload, credentials, or
HTTP metadata.

## Evaluation and aggregate boundaries

`evaluate_structured_fixture` returns preparation status, provider allowance,
decoded status, completion status, semantic and expected-status outcomes,
exact-pair outcome, failure codes, evidence-preservation signal, and
presentation status. A provider-blocked fixture does not enter the response
adapter or completion boundary.

`aggregate_structured_fixture_results` reports fixture count, preparation-ready
count, provider-blocked count, decode-success count, semantic-success count,
expected-status matches, exact-pair successes, and a sanitized failure
distribution. No token or cost field is synthesized.

## v14.15 preservation and claim behavior

The resolved structural equivalent validates `hyper-beam` / slot 1. The
insufficient-context structural equivalent reaches completion and reproduces
sanitized `invalid_claim` without a recommendation pair. No-selectable and
no-candidate fixtures demonstrate that pure preparation blocks unnecessary
provider use.

Provider guidance now states that each reason/risk must be exactly a supported
`kind`/`claim` object with a non-empty claim. This clarifies the observed
`invalid_claim` boundary without broadening the validator. Global limitations
remain distinct from candidate-specific claims.

## Limitation and next milestone

The framework validates contract behavior only; it does not measure model
reliability. Next: **v14.17: T1-authorized broader provider evaluation using the
fixed-fixture catalog.** Actual provider call count and fixture subset require
explicit T1 approval.

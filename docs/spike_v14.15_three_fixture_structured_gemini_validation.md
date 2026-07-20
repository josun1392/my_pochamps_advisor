# v14.15 Three-Fixture Structured Gemini Validation

## Scope and call budget

T1 authorized at most three real structured-provider calls: one each for a
resolved, insufficient-context, and no-usable-candidate fixture. The sample is
a diagnostic check only and does not establish general model reliability.

The implementation retained the seven-field outbound payload, strict six-field
decoded response boundary, exact move-plus-slot validation, claim grounding,
and one-call/no-retry/no-fallback/no-repair policy. Raw request data, raw
provider output, credentials, and token-log content were neither retained nor
recorded here.

## Sanitized outcomes

| Fixture | Pure preflight | Calls | Expected | Sanitized result |
| --- | --- | ---: | --- | --- |
| Resolved | ready, two selectable candidates | 1 | resolved | resolved; validated exact pair `hyper-beam` / slot 1 |
| Insufficient context | ready, two partial/selectable candidates | 1 | insufficient_context | decoded response reached completion but failed as `response_validation_failed` / `invalid_claim`; no pair was displayed |
| No usable candidate | no_selectable_candidates, two candidates, zero selectable | 0 | no_usable_candidate if callable | preparation blocked provider use; no substitute fixture or provider call was used |

The aggregate used 2 of 3 authorized calls: 2 decoded response successes, 1
semantic validation success, 1 expected-status validated match, and 1 resolved
exact-pair success. The sanitized failure distribution is `invalid_claim: 1`
and `preparation_blocked/no_selectable_candidates: 1`. Sanitized usage totals
are 1,183 input tokens, 134 output tokens, and 0 cached tokens. Estimated cost
was not available. Retry, fallback, repair, and legacy-fallback counts are all
zero.

## Insufficient-context diagnosis

The first available sanitized failure code is `invalid_claim`. It identifies
the first structural rule in `_validate_claim`: a reason or risk must be
exactly a `{kind, claim}` mapping, `kind` must be from the supported claim
vocabulary, and `claim` must be a non-empty string. The sanitized code does not
justify reconstructing model prose or identifying a more specific source field.

This is not a proven local contract defect. The validator remains strict. A
sanitized regression uses a generic unsupported claim kind to reproduce the
same first-rule outcome, while preserving the absence of a recommendation pair.

## Regression coverage and next step

Offline regressions cover the accepted resolved pair, the sanitized
insufficient-context `invalid_claim` result, the pure no-selectable preflight
block, the aggregate two-call structural result, raw-response exclusion, and
the one-provider-call runtime boundary.

Next: **v14.16 structured claim-guidance refinement and fixed-fixture evaluation
design**. Further actual provider calls require separate T1 authorization. The
legacy selected-move flow remains unchanged and is not authorized for
replacement.

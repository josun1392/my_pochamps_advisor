# v14.4 offline recommendation response parser

v14.4 is an offline, provider-neutral parser for already-decoded structured
response mappings. Accepted response statuses are `resolved`,
`insufficient_context`, and `no_usable_candidate`; `validation_failed` is
local-only and never accepted from a response payload.

Resolved selections reuse exact move-plus-slot validation from v14.3. Reasons
use a small structured deterministic-claim vocabulary: damage, KO, hit chance,
move order, self effect, dynamic mechanic, and partial context. Each claim is
accepted only when its selected candidate emits compatible evidence.

Alternatives require distinct selectable exact pairs and a structured reason.
The parser recursively rejects forbidden raw, credential, provider/model,
network, replacement-evidence, and inference content. Failures return stable
sanitized error codes without payload values. Request evidence and parsed
response structures are deep-copied; all ten dynamic-family candidates are
compatible with emitted dynamic claims.

Provider/UI integration is excluded. Next: v14.5: offline recommendation
orchestration design and contract audit. No actual provider or UI orchestration
is authorized. Validation: 55 v14.4 parser tests, 34 v14.3 request-regression
tests, 28 candidate-regression tests, 52 registry-regression tests, 1282
related-regression tests, and 2514 passed with 2 deselected in the full suite.

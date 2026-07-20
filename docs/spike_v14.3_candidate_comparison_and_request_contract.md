# v14.3 offline recommendation request contract

v14.3 is offline and provider-neutral only. It constructs a deterministic
comparison request from existing candidate evidence; it does not invoke a
provider, parse a provider response, or orchestrate a UI.

Candidates are classified as eligible when resolved and usable, eligible with
warnings when partial and usable or partially evaluable, and not selectable
when unavailable. Request readiness is `ready`, `no_candidates`,
`no_selectable_candidates`, or `invalid_evidence_bundle`.

`candidate_exact_set` retains every exact move-plus-slot pair in slot order,
including unavailable candidates. `selectable_candidate_exact_set` contains
only eligible entries. Comparison rows retain deterministic damage, KO, hit
chance, move-order, dynamic summaries, self effects, warnings, and unavailable
reasons without recalculation or fabricated fields.

Snapshots, comparison rows, limitations, and guardrails are deep-copied.
Known limitations propagate unchanged. Serialization accepts only JSON-safe
values and recursively rejects nested secret-like keys. Provider/UI fields,
raw prompt/response data, models, network configuration, ranking scores, and
automatic winners are excluded.

Validation: 34 v14.3 request-contract tests, 28 candidate-regression tests,
52 registry-regression tests, 1272 related-regression tests, and 2459 passed
with 2 deselected in the full suite. Next: v14.4: offline recommendation
response parser and semantic guardrail contract. No actual provider or UI
orchestration is authorized.

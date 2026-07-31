# Multi-Candidate Provider Grounding Smoke

The multi-move provider response remains deliberately minimal:
`recommendation_status`, `selected_candidate_id`, and the fixture-bounded
`explanation_code`.  It cannot supply damage, percent, KO, action-order,
comparison-tag, path, dependency, rank, or score data.

Two sanitized actual fixtures are allowlisted separately from the historical
three-fixture ranking smoke:

- `complete-multi-candidate-mechanics` has two known direct-mechanics
  candidates with distinct native damage evidence and known action order.
- `mixed-context-multi-candidate-mechanics` has one known candidate plus an
  insufficient and an unsupported candidate.

Before a call, the runner verifies each row's deterministic comparison and
candidate-local `comparison_facts`.  After server-side provider binding it
checks that every completed candidate retains the same mechanics and
action-order evidence for the same slot/move pair.  A violation is surfaced as
the bounded `multi_candidate_evidence_mixed` diagnostic; provider binding
continues to use the established bounded binding diagnostic.  No raw request,
response, credential, or token data is emitted.

The fixtures do not ask Gemini to restate numeric mechanics.  Exact native
numeric linkage remains server-owned, and incomplete/unsupported rows remain
non-numeric.  Offline fixture and CLI tests were run before any actual call;
the actual round uses a separately authorized two-call budget with no retry,
fallback, or repair.

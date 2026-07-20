# v14.14 semantic guidance stabilization

The v14.12 failure was a legitimate semantic contradiction; the validator is
unchanged. Provider-only guidance now distinguishes resolved, limited,
unavailable, global limitations, and candidate-specific missing evidence. It
forbids contradictory `partial_context`, requires grounded resolved reasons and
risks, exact selectable move+slot alternatives, and status-specific no-pair
rules. Schema descriptions reinforce the same contract. The seven-field payload
and six-field response shape are unchanged. Provider calls: 0.

Next: v14.15 single-call structured Gemini semantic revalidation readiness
review. A second call requires explicit T1 authorization.

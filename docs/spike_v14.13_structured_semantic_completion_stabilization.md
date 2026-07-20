# v14.13 semantic completion diagnosis

The v14.12 sanitized fixture is a six-field response shape, but its resolved
candidate supplies a `partial_context` claim saying `missing evidence`. The
first failing validator is `_validate_claim`, which returns the precise
sanitized code `claim_evidence_contradiction` because the selected deterministic
candidate is resolved. This is a legitimate provider semantic contradiction,
not a transport, decoder, exact-set, slot, or local schema mismatch.

The schema, adapter, and completion contract align: resolved requires an exact
selectable move+slot and grounded reasons/risks; alternatives are reason-bearing
`move` + `slot_index` mappings in the selectable exact set. Insufficient and
no-usable statuses must not fabricate a pair. Existing evidence preservation
and generic UI validation text are correct, so production behavior is retained.

No provider call occurred in v14.13. Added offline diagnostics preserve the
precise sanitized error without raw mapping content. Next: v14.14 structured
prompt/schema semantic guidance stabilization. Legacy replacement remains
unauthorized.

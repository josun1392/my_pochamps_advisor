# v15.61 incomplete direct-mechanics claim closure

The previous actual `insufficient-direct-mechanics` response reached semantic
validation with `mechanics_numeric_claim_on_insufficient_context`. The native
mechanics result was correctly incomplete and the acknowledgement dependency
contract remained intact; the remaining provider-facing gap was that the
`partial_context.claim` field was still an unrestricted string.

For an all-insufficient direct-mechanics request, the provider schema now
restricts the claim to one of three value-free, bounded missing-context
statements. The strict parser uses the same allowlist. It rejects numeric and
numeric-free mechanics wording alike when it is not a bounded missing-context
statement. The exact missing-input acknowledgement path and grounding
conditional dependency remain mandatory.

Known direct-mechanics numeric scope/native-value validation is unchanged.
This change does not alter action-order evidence, damage ranking, native
mechanics computation, retry/fallback/repair policy, or fixture inputs.
Offline tests only; actual provider validation requires the separately
approved two-call round after commit and push.

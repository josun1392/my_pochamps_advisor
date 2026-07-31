# Validated Multi-Candidate Recommendation Result

For a multi-candidate response, the application treats Gemini's selected slot
and bounded explanation code as an input to validation, not as a recommendation
object.  After the existing rank-one binding succeeds, the result resolves the
slot/move pair from the request-start candidate inventory and adds only that
candidate's deterministic evidence:

- selected candidate ID and action identity;
- explanation code;
- native mechanics result;
- action-order evidence;
- comparison facts; and
- bounded mechanics uncertainty (status, missing inputs, unsupported reason).

The normal completion status remains the established `resolved`,
`insufficient_context`, or `no_usable_candidate` contract. Provider rejection
and provider availability remain distinct existing structured-flow failures;
they never reuse an earlier recommendation result. An invalid multi-provider
selection produces no recommendation result.

The UI-neutral presentation model now exposes a copied `selected_candidate`
summary only when this validated result is present. It does not expose provider
payloads, raw responses, credentials, or recomputed evidence. Offline tests
cover normal resolution, second-slot selection, invalid selection, evidence
isolation, and presentation handoff. No provider, credential, or network call
occurred in this slice.

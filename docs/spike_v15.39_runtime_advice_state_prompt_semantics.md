# v15.39 Runtime Advice-State Prompt Semantics and Offline Evaluation Design

## Scope

This is a documentation-only design follow-up to v15.38. It defines future
provider semantics for `runtime_advice_state` and deterministic offline
evaluation. It changes no production Python, test Python, fixture data, prompt
wording, provider configuration, or network state.

## Current call graph and gap

```text
MainWindow._start_structured_recommendation
  -> battle_input.runtime_advice_state
  -> advisor_turn_snapshot.build_request_start_recommendation_snapshot
  -> TurnSnapshot.current_state.runtime_advice_state
  -> advisor_candidate_contract.prepare_ui_recommendation_cycle
  -> build_provider_recommendation_payload
  -> advisor_client.call_structured_recommendation_provider
  -> adapt_provider_recommendation_response / complete_recommendation_cycle
```

`llm/advisor_turn_snapshot.py::_extract_current_state_with_private_handoffs`
validates and defensively copies the v15.38 projection. MainWindow captures it
from a matching state/session/fingerprint snapshot. The fingerprint remains
worker-only provenance and is correctly excluded from the turn snapshot.

The provider boundary is not yet complete: `llm/advisor_candidate_contract.py`
currently has a seven-key `_PROVIDER_OUTBOUND_KEYS` set and
`build_provider_recommendation_payload()` does not forward the projection.
Therefore the projection currently has no prompt semantics, response grounding,
or semantic validator.

## Existing prompt, response, and offline seams

- `llm/advisor_client.py::call_structured_recommendation_provider` builds the
  REST request as `_STRUCTURED_SEMANTIC_GUIDANCE` plus serialized
  `Deterministic evidence`; this is the exact future prompt-instruction point.
- `llm/advisor_client.py::_structured_provider_schema` and
  `_STRUCTURED_RESPONSE_KEYS` require exactly six response fields:
  recommendation status, move, slot, primary reasons, risks, alternatives.
  No response grounding field currently exists.
- `llm/advisor_candidate_contract.py::prepare_ui_recommendation_cycle`,
  `build_provider_recommendation_payload`,
  `adapt_provider_recommendation_response`, and
  `complete_recommendation_cycle` are the request, outbound, decode, and
  candidate-semantic boundaries respectively.
- `llm/advisor_client.py::_build_ui_selected_prompt` and its trusted-context
  acknowledgement parser/validator are a separate legacy text-prompt path;
  they do not validate runtime projection semantics.
- `llm/structured_fixture_evaluation.py::get_fixed_fixture_catalog`,
  `evaluate_structured_fixture`, and `aggregate_structured_fixture_results`
  provide the current fake-provider path. Actual-provider evaluation is
  `SUSPENDED` with zero remaining call budget.

## Semantic vocabulary and authority

| Term | Meaning | Must never mean |
|---|---|---|
| `unknown` | Current fact is unobserved. | absent, false, zero, full HP, healthy, or inactive. |
| `known_absent` | Trusted runtime confirmed absence. | unknown. |
| `known` plus `value` | Reducer-applied trusted current fact. | stale UI evidence or an inference target. |
| user-confirmed evidence | Explicit user current-context evidence. | automatic runtime-state resolution. |
| observation evidence | Collection acknowledgement not yet necessarily applied. | current state before reducer apply. |
| conflict | Incompatible sources. | permission to choose one arbitrarily. |

Authority is:

```text
Tier 1: matching-session runtime known / known_absent facts
Tier 2: explicitly user-confirmed current evidence
Tier 3: unapplied canonical observation evidence
Tier 4: UI selection/bootstrap identity
Tier 5: explicit unknown limitation
```

Runtime identity and UI selected identity must match within the session or the
request is rejected. Tier-1 facts outrank stale UI/evidence. A runtime unknown
remains unknown even if Tier 2/3 evidence exists; that evidence is separately
labelled, never silently promoted. Conflicting evidence produces a conditional
or insufficient/conflicting-context response. Species metadata, damage
estimates, and provider reasoning never fill HP, fainted, item, condition,
weather, terrain, or side-condition facts.

## Future prompt and user-answer contract

Add a bounded runtime-state instruction block to
`llm/advisor_client.py::_STRUCTURED_SEMANTIC_GUIDANCE`, before serialized
evidence. It must say that:

1. `runtime_advice_state` is authoritative current state.
2. unknown is unobserved, never a default or absence.
3. known absence is confirmed absence; known values are trusted current facts.
4. UI and observation evidence cannot silently override runtime known facts.
5. Unapplied evidence remains evidence, not state.
6. HP, fainted, item, condition, field, and sides are not inferred from species
   metadata or generic game knowledge.
7. Advice depending on unknown/conflicting facts explicitly states uncertainty.
8. User-facing text cannot expose schema labels, fingerprint, sessions, CAS,
   reducers, ledgers, or persistence internals.

Allowed wording: “the opponent's item is not yet confirmed” and “the current HP
is unconfirmed, so this survival line is conditional.” Forbidden wording:
`runtime_advice_state.status`, `CAS fingerprint mismatch`, and
`reducer-applied ledger`.

## Payload and response grounding recommendation

Future outbound payload adds a single validated top-level
`runtime_advice_state` copied from `TurnSnapshot.current_state`. It contains
only v15.38 provider-safe facts, never raw reducer state, turn snapshot,
runtime/store/commands, ledger, persistence envelope/path, CAS data,
fingerprint, request token, or thread identity.

Choose **candidate B: a bounded grounding response extension**. Extend the
future exact response contract with:

```text
grounding:
  runtime_known_facts: [canonical fact paths]
  runtime_unknown_facts: [canonical fact paths]
  evidence_only_facts: [canonical fact paths]
  conflicts: [canonical fact paths]
```

Paths contain no raw values or internals. The validator compares them with the
projection and separated evidence. Candidate A (prompt plus prose-only
validator) cannot prove grounding adequately. Candidate C (a second LLM
evaluator) is non-deterministic and outside offline scope.

Backward compatibility: use an explicit versioned grounded response contract or
a separate exact key set for runtime-required requests. Do not silently migrate
the current six-field response. Keep v14 fixed fixtures as an explicitly named,
bounded legacy lane while migrating fixtures one at a time; grounded production
requests fail deterministically when grounding is missing.

## Sanitized fixed-fixture catalog

| Fixture | Inputs | Expected semantic result | Forbidden claim |
|---|---|---|---|
| `unknown_bootstrap` | identities known; facts unknown | uncertainty and unknown grounding | full HP, alive, no item, healthy, empty field, decisive KO |
| `known_item_stale_ui` | runtime Focus Sash; UI Choice Scarf | Focus Sash runtime grounding or conflict | Scarf as current fact |
| `unknown_user_item_evidence` | item unknown; user Leftovers evidence | unknown plus evidence-only | confirmed Leftovers |
| `known_absent_field_condition` | condition/weather absent | confirmed absence grounding | label as unknown |
| `partial_hp` | HP known; max HP/fainted unknown | preserve all distinctions | percentage, alive, KO inference |
| `applied_vs_collection` | runtime burned; unapplied paralysis evidence | burned state, paralysis evidence-only | current paralysis |
| `field_side_distinction` | sandstorm known; self side absent; opponent side unknown | three distinct statuses | merge absence/unknown |
| `conflicting_evidence` | item unknown; UI Scarf; collection Leftovers | conflict/insufficient context | arbitrary item choice |
| `missing_runtime` | no projection | request rejection; fake provider 0 | fabricated UI-only runtime |
| `internal_metadata_exclusion` | projection plus worker provenance | metadata absent from payload/answer | fingerprint/token/session/CAS/ledger output |

## Deterministic semantic validator

Inputs are validated runtime projection, separated UI/observation evidence,
validated structured response/grounding, and fixture-specific expected rules.
Structural checks cover the approved payload key, exact grounding keys, allowed
canonical paths, response schema, and metadata exclusion. Semantic checks reject
unknown promoted to absence/value, evidence promoted to state, contradiction of
runtime facts, unresolved conflict presented as fact, and internal terminology
in user text. They accept conditional advice grounded in unknown and confirmed
absence grounded in `known_absent`.

Do not create a general prose-inference framework. Use normalized structured
grounding plus exact fixture expectations and a small targeted forbidden-term
check. Fake-provider responses keep the evaluation deterministic and offline.

## Proposed executable tests

- `test_prompt_defines_runtime_state_as_authoritative`,
  `test_prompt_defines_unknown_as_not_observed_not_absent`,
  `test_prompt_defines_known_absent_separately`,
  `test_prompt_forbids_ui_or_evidence_override_of_runtime_known_fact`,
  `test_prompt_forbids_species_metadata_state_inference`, and
  `test_prompt_requires_uncertainty_for_unknown_dependent_advice`.
- `test_unknown_bootstrap_fixture_forbids_full_hp_alive_and_no_item_claims`,
  `test_known_item_overrides_stale_ui_fixture`,
  `test_runtime_unknown_keeps_user_confirmation_as_evidence_only`,
  `test_known_absent_fixture_is_not_reported_as_unknown`, and
  `test_partial_hp_fixture_forbids_percentage_and_ko_inference`.
- `test_applied_state_wins_over_unapplied_collection_evidence`,
  `test_field_and_side_condition_statuses_remain_distinct`,
  `test_conflicting_evidence_fixture_requires_conflict_or_insufficient_context`,
  `test_missing_runtime_fixture_invokes_no_provider`, and
  `test_internal_metadata_exclusion_fixture`.
- `test_validator_rejects_unknown_promoted_to_known_absent`,
  `test_validator_rejects_evidence_only_promoted_to_runtime_fact`,
  `test_validator_rejects_runtime_known_fact_contradiction`,
  `test_validator_rejects_internal_metadata_in_user_answer`,
  `test_validator_accepts_conditional_advice_grounded_in_unknown`, and
  `test_validator_accepts_known_absent_grounding`.
- `test_existing_structured_response_contract_remains_valid`,
  `test_existing_fixed_fixture_catalog_remains_green`, and
  `test_legacy_fixture_policy_is_explicit_and_bounded`.

Each test fixes runtime projection, UI/observation evidence, fake response,
expected grounding/status, forbidden claim, and provider-call count.

## Recommended v15.39 implementation boundary

```text
Modify: llm/advisor_client.py
        (prompt rule block, provider schema, response adapter)
Modify: llm/advisor_candidate_contract.py
        (approved projection payload key and grounded response validation)
Modify: llm/structured_fixture_evaluation.py
        (deterministic semantic fixture runner)
New:    tests/test_v39_runtime_advice_state_prompt_semantics.py
Docs:   docs/advisor_payload_contract.md, this document, PROGRESS.md,
        handoff_next_session_prompt_v1.9.md
```

Excluded: MainWindow/worker/runtime-session lifecycle, persistence, damage
engine, autosave/startup/import/history/undo, cancellation, and actual provider
evaluation. An exact-stage/commit/push review is required before implementation.

## Design validation plan

Run `tests/test_v38_runtime_state_advice_projection.py`,
`tests/test_structured_fixture_evaluation.py`, direct candidate-contract and
turn-snapshot tests, and the new v15.39 suite after implementation. This design
stage requires no Python compile because it changes documentation only.

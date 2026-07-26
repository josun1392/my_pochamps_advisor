# v15.38 Runtime Battle-State Projection into Structured Advice Input Design

## Current request inventory

| Boundary | Actual file / symbol | Current input and authority |
| --- | --- | --- |
| UI entry | `ui/main_window.py:MainWindow._start_structured_recommendation()` | Requires active `BattleObservationRuntimeSessionManager`; captures active session ID, UI battle input, selected moves, collection snapshot, and trusted turn context. |
| UI battle input | `MainWindow._build_llm_battle_input()` | Builds selected-Pokémon identity, UI HP percentage, item/stat profiles, field profiles, and user-confirmed contexts. It is not runtime state. |
| UI provenance | `llm/advisor_turn_snapshot.py:capture_ui_current_state_provenance()` | Copies structured-only UI evidence with the captured session ID. |
| Observation evidence | `BattleObservationRuntimeSessionManager.read_collection_snapshot()` | Returns a detached collection acknowledgement/evidence snapshot; it is not a reducer-applied state snapshot. |
| Trusted turn | `MainWindow._trusted_turn_context_snapshot()` | Detached explicit turn number plus active session ID; it is independent from observation and store sequence. |
| Worker | `StructuredRecommendationWorker` | Deep-copies battle input, collection snapshot, and turn context before calling `run_structured_ui_recommendation()`. |
| Preparation | `llm/advisor_client.py:run_structured_ui_recommendation()` → `llm/advisor_candidate_contract.py:prepare_ui_recommendation_cycle()` | Builds a request-start `TurnSnapshot`; no active runtime-state read is supplied. |
| Provider boundary | `build_provider_recommendation_payload()` | Serializes only approved recommendation-request fields, including `battle_snapshot_summary`; current-state handoffs can reach that summary through `TurnSnapshot`. |

`llm/advisor_request_builder.py` does not exist in this repository. The effective
request construction boundary is `advisor_candidate_contract.py` plus
`advisor_turn_snapshot.py`.

### Current authority gaps

- `MainWindow._start_structured_recommendation()` captures session ID and
  collection snapshot, but never calls `manager.read_state()`.
- UI `pokemon.*.hp_percent`, item profiles, and current confirmation mappings
  can therefore disagree with reducer state without an explicit precedence rule.
- A collection snapshot is evidence/acknowledgement; its observations have not
  necessarily been applied to the runtime store.
- Current completion checks request token and session ID. A same-session runtime
  change can leave an old request token current, so its advice could be shown
  despite having used an older state.

## Recommended projection contract

Add a pure module, `llm/advisor_runtime_state_projection.py`, with a single
bounded mapper such as `project_runtime_state_for_advice(runtime_snapshot)`.
It accepts a detached successful `read_state()` result and returns a detached,
sanitized result mapping:

```text
runtime_projection_ready
  session_id
  projection
  runtime_fingerprint       # worker provenance only; never provider prompt data

invalid_runtime_projection
  session_id: null
  projection: null
```

The mapper owns neither a runtime, store, session manager, UI widget, provider,
request token, filesystem path, persistence envelope, or ledger. It performs no
inference and no I/O.

### Included projection fields

```text
session_id
self.active:     identity, hp, fainted, condition, item
opponent.active: identity, hp, fainted, condition, item
field:            weather, terrain
self.side_conditions
opponent.side_conditions
```

Only the active-slot identity and facts are projected; inactive roster objects
are not needed for this bounded advice input. Store
`last_applied_observation_sequence` is retained only as local provenance if an
implementation demonstrably needs it, not as provider-facing state. A raw
applied ledger is excluded: it is reducer execution history, while collection
snapshot remains separately supplied evidence/acknowledgement.

### Excluded fields

```text
raw runtime/store/commands/coordinator/persistence
raw state dict and inactive roster
persistence envelope/path/schema/rollback data
CAS implementation data and full state fingerprint
applied ledger
request token/thread identity
Python exceptions and provider objects
```

The projection is deterministic for equivalent validated runtime state, deep
copied at every boundary, and has no runtime, allocator, sequence, collection,
ledger, or persistence mutation.

## Unknown mapping decision

Choose request-level semantic facts, not the reducer marker itself.

| Runtime value | Projection value | Meaning |
| --- | --- | --- |
| `{"knowledge": "unknown"}` | `{"status": "unknown"}` | Fact is unconfirmed. |
| Concrete present value | `{"status": "known", "value": ...}` | Trusted runtime fact. |
| Concrete known absence (`None`, `False`, or `[]`, where the reducer field defines it as absence) | `{"status": "known_absent"}` | Confirmed absence, never unknown. |

For HP, the known mapping carries both available values under `value` without
inventing a missing current or maximum HP. For fainted, `false` is represented
as `known/value=false`, never as unknown. Unknown fields are always present in
the projection; they must not be omitted, converted to full HP, zero HP, alive,
no item, no condition, no field, or empty side conditions.

This **Candidate B** representation decouples provider payload semantics from
the internal `battle-state-v1` marker while preserving unknown versus
known-absent. Candidate A (passing the internal marker through) couples reducer
schema to the prompt; Candidate C (omitting unknown fields) loses the distinction
between unknown and unsupported data.

## Authority policy

1. A resolved matching-session runtime fact is authoritative for current battle
   state.
2. A user-confirmed UI context remains separately labelled evidence when runtime
   is unknown; it must not silently mutate or overwrite the projection.
3. Collection observations remain evidence until reducer apply commits them.
4. UI selection supplies bootstrap identity only. In a matching session that
   identity must agree with runtime active identity; disagreement rejects the
   projection/request instead of merging or retagging.
5. Absent runtime facts remain explicit unknown. No UI percent, species metadata,
   damage estimate, provider output, or default fills them in.

Therefore runtime-known HP/item/condition wins over a stale UI mirror. Runtime
unknown plus a user confirmation is represented as runtime unknown plus separate
provenanced UI evidence; a later reducer contract may resolve it. Conflicting
known runtime/UI facts are not silently merged. Collection evidence is never
represented as already-applied runtime state.

## Request integration and capture timing

Recommended future flow:

```text
structured request start
→ capture active session ID
→ obtain one detached matching-session runtime state/fingerprint snapshot
→ pure runtime advice projection
→ capture detached UI battle input, collection snapshot, trusted-turn context
→ assemble `battle_input.runtime_advice_state` and worker-only provenance
→ deep-copy all inputs into worker
```

`runtime_advice_state` is a new top-level authoritative section in the internal
structured `battle_input`. `advisor_turn_snapshot.py` should explicitly validate
and copy it into `TurnSnapshot.current_state`; provider-visible request data then
reaches the existing `battle_snapshot_summary.turn_snapshot.current_state`
boundary without replacing current UI payload fields. This is preferable to
overwriting legacy UI fields (high compatibility risk) or exposing a raw runtime
object. `advisor_payload_contract.md` remains unchanged for this design step.

The full runtime fingerprint is captured beside worker metadata only. It is not
put in `battle_input`, `TurnSnapshot`, summary, provider payload, prompt, UI
status, or logs. Save and load-only do not change its source. Restore or a
successful reducer apply changes the next request's captured snapshot; an
in-flight worker retains its detached old projection and is never retagged.

### Runtime-missing policy

Choose **reject, no UI-only fallback**. Current structured flow already rejects
when no active manager/session exists. A valid selected pair must first create
the v15.36A identity-only unknown-bootstrap session. If a runtime snapshot or
projection is invalid, display a sanitized preparation failure, launch no worker,
and make no provider call. Do not fabricate state or silently fall back to an
unlabelled UI-only current-state payload.

## Same-session stale-state gate

Existing request-token protection rejects an earlier request in the same session
only when a newer request has started. Existing session protection rejects after
rollover. Neither necessarily rejects a result after same-session reducer apply
or an external bounded runtime mutation.

Recommended v15.38 implementation: capture a runtime fingerprint with the
projection and add a completion-time fingerprint comparison after request-token
and session checks, before terminal claim/presentation:

```text
token current
→ captured session current
→ captured runtime fingerprint equals active runtime fingerprint
→ terminal claim
→ presentation update
```

Mismatch returns deterministic `stale_runtime_state_result`; it must not mutate
UI/core/collection/ledger or consume terminal authority. Worker/thread cleanup
remains unconditional. Restore success already retires the pre-restore token in
v15.37; the fingerprint gate additionally protects future same-session reducer
apply changes. No state-generation framework, retry, retagging, or provider
cancellation is needed.

## Candidate architecture comparison

| Candidate | Atomicity | Coupling | Testability | MainWindow complexity | Recommendation |
| --- | --- | --- | --- | --- | --- |
| A. Pure projection module only | Good mapper isolation; capture needs caller discipline | Low provider/UI coupling | High | Moderate | Recommended with bounded snapshot capture |
| B. Projection delegated by runtime-session owner | Can combine session/state capture | Couples core owner to advice payload | Moderate | Low UI, high core | Reject |
| C. MainWindow private mapper | Caller-local only | High UI/reducer coupling | Low | High | Reject |

Use Candidate A plus a minimal session-manager method such as
`capture_runtime_snapshot(captured_session_id)` only if existing
`read_state()` cannot be safely paired with active-session verification in the
actual integration. That seam returns detached state/fingerprint and no
projection/provider shape; it must reject stale session and expose no raw
components.

## Proposed executable contract tests

- `test_projection_uses_detached_active_runtime_state`
  - initial runtime: matching unknown/bootstrap or resolved state
  - action: project detached `read_state()`
  - expected: equal projection, unchanged state/fingerprint/sequence/ledger
  - forbidden: aliasing, runtime mutation, I/O, provider access.

- `test_projection_contains_known_identity_and_explicit_unknown_facts`,
  `test_projection_preserves_unknown_without_omitting_field`,
  `test_projection_distinguishes_unknown_from_known_absent`,
  `test_projection_does_not_encode_unknown_hp_as_full_or_zero`, and
  `test_projection_does_not_encode_unknown_fainted_as_false`
  - expected: request-level `unknown`, `known`, and `known_absent` unions
    preserve exact runtime semantics without inference.

- `test_projection_never_exposes_raw_runtime_store_commands_or_persistence` and
  `test_request_payload_excludes_persistence_and_cas_internals`
  - expected payload: no raw objects, ledger, envelope/path, CAS data, full
    fingerprint, token, or thread identity.

- `test_runtime_known_fact_overrides_stale_ui_mirror`,
  `test_user_confirmed_fact_can_be_acknowledged_when_runtime_is_still_unknown`,
  `test_conflicting_runtime_and_ui_fact_is_not_silently_merged`, and
  `test_observation_evidence_is_not_treated_as_applied_state_before_reducer_commit`
  - expected: authority ordering is labelled, never inferred or merged.

- `test_structured_request_captures_session_projection_and_fingerprint_atomically`,
  `test_in_flight_projection_is_detached_from_later_runtime_mutation`,
  `test_new_request_after_restore_uses_restored_runtime_projection`, and
  `test_save_and_load_only_do_not_change_projection_source`
  - expected worker metadata: matching captured session/fingerprint; old
    request input stays detached.

- `test_same_session_old_fingerprint_result_is_rejected_after_runtime_change`,
  `test_same_session_current_fingerprint_result_remains_eligible`,
  `test_stale_state_result_does_not_overwrite_advice_or_status`,
  `test_stale_state_result_still_cleans_worker_and_thread`, and
  `test_restore_success_invalidates_pre_restore_projection_result`
  - expected stale status: `stale_runtime_state_result`; cleanup still runs and
    terminal authority remains available to the current request.

- `test_request_without_active_runtime_is_rejected_without_provider_call`,
  `test_projection_failure_is_sanitized_and_non_mutating`, and
  `test_missing_identity_does_not_create_fabricated_runtime_state`
  - expected: deterministic preparation rejection and provider call count zero.

## Expected implementation scope

```text
New:      llm/advisor_runtime_state_projection.py
New:      tests/test_v38_runtime_state_advice_projection.py
Modify:   ui/main_window.py
Modify:   llm/advisor_turn_snapshot.py
Optional: llm/advisor_observation_runtime_session.py
Docs:     this file, PROGRESS.md, handoff_next_session_prompt_v1.9.md
```

`advisor_request_builder.py` is absent and no request-builder file needs to be
created. Do not modify provider prompt text in the initial projection contract
implementation unless the approved payload integration requires it. Deferred:
provider evaluation, autosave/startup/import, persistence UI expansion,
cross-session import, history/undo, cancellation, and generic concurrency
frameworks.

## Design validation

This is documentation-only. Planned focused regression includes trusted-turn,
runtime reducer/store, unknown-bootstrap, MainWindow lifecycle, persistence UI,
and existing structured request/payload contracts; compile is not required.

## Implemented v15.38 projection boundary

Implemented `llm/advisor_runtime_state_projection.py` with
`build_runtime_advice_state_projection(runtime_state)`. It accepts only a
detached validated `battle-state-v1` mapping and returns
`runtime_projection_ready` with detached `runtime_advice_state`, matching
session ID, and worker-only runtime fingerprint. The projection uses
`runtime-advice-state-v1` and includes only active identities and the approved
HP/max-HP, fainted, condition, item, weather, terrain, and side-condition
facts. It maps reducer unknown to `{"status": "unknown"}`, explicit absence to
`{"status": "known_absent"}`, and concrete facts to
`{"status": "known", "value": ...}`.

`BattleObservationRuntimeSessionManager.capture_runtime_state_snapshot()` now
returns a matching detached state/session/fingerprint only for the captured
active session. It exposes no raw component. MainWindow captures this snapshot
before preparing a structured worker, projects it, checks active runtime identity
against the selected UI identity, and inserts only `runtime_advice_state` into
the structured battle input. It supplies the fingerprint only as worker/callback
provenance. Runtime missing, invalid snapshot/projection, or identity mismatch
rejects before worker/provider launch; there is no UI-only fallback.

`advisor_turn_snapshot.py` validates and copies the new section to
`TurnSnapshot.current_state.runtime_advice_state`. The fingerprint is excluded
from this handoff, provider payload, prompt, UI messages, and logs. Existing UI
fields and collection evidence stay separate and cannot silently resolve runtime
unknown facts.

Structured success and error callbacks now require request token, session, and
captured runtime fingerprint eligibility before terminal claim. A same-session
fingerprint mismatch is suppressed without presentation/core mutation or
terminal-authority consumption; existing cleanup remains independent. The
legacy direct callback compatibility path has no captured fingerprint only for
pre-v15.38 test callers; actual v15.38 worker launches always supply one.

Added `tests/test_v38_runtime_state_advice_projection.py`: projection mapping,
detachment, known-absence distinction, snapshot seam, TurnSnapshot handoff,
fingerprint exclusion, and same-session stale success/error suppression. Prompt
wording, semantic/provider evaluation, damage behavior, persistence schema,
autosave/startup/import/history/undo, and provider cancellation remain out of
scope.

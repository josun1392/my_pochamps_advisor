# v15.35 Session Lifecycle and Runtime Rollover Boundary

## 조사 기준과 현재 분리 상태

이 문서는 v15.34 commit `580e9bc`의 code/test surface만을 근거로 한
설계 및 계약-test inventory이다. production/test Python은 변경하지 않는다.

현재 `ui/main_window.py`의 `MainWindow.__init__`는 `_battle_session_sequence`
0, `_current_battle_session_id`/`_current_state_session_id` `ui-session-0`,
`_observation_sequence` 0 및 `ObservationCollection("ui-session-0")`을 직접
생성한다. `MainWindow._begin_new_battle_session()`은 시퀀스를 증가시켜
`ui-session-N`을 만들고, 기존 collection에 `start_new_session()`을 호출하고,
UI confirmation state와 observation sequence를 0으로 지운다. public
`begin_new_battle()`만 이 내부 method를 호출한다. slot selection과 request는
해당 method를 호출하지 않는다.

`ObservationCollection` (`llm/advisor_observation_collection.py`)은 session ID와
item map만 가진다. `start_new_session(session_id)`은 session ID를 대입하고 map을
비우며, sequence를 할당하지 않는다. `add_confirmation_result()`는 entry session이
현재 session과 다르면 `stale_session`을 반환한다. snapshot은 deep copy이므로 reset
전 snapshot은 old-session evidence로 계속 존재할 수 있다. collection 자체에 lock,
producer coordination, 또는 reset 중 add의 race 정책은 없다.

`ObservationReplayRuntime.create(initial_state)`
(`llm/advisor_observation_replay_runtime.py`)는 exact `battle-state-v1` shape의
caller-supplied state로만 생성된다. runtime session은 `_session_id` read-only
property이며 reset/rollover API가 없다. store/coordinator/persistence를 private으로
고정하고 detached read/ledger/preview/apply/export/validate만 제공한다. repository의
production call-site에는 이 factory의 호출자가 없고, 따라서 production initial-state
source도 없다. old runtime reference, old preview 또는 old envelope는 Python caller가
보유할 수 있지만 현재 active-session 개념은 runtime 내부에 없다.

`ObservationReplayPersistenceCommands.create(runtime)`
(`llm/advisor_observation_replay_persistence_commands.py`)는 runtime object identity와
immutable session을 보존한다. rebind API와 active-session registry는 없다. old commands는
old runtime이 살아 있는 동안 old runtime에 대해 명시적 save/load/restore를 수행할 수
있다. loaded candidate도 caller가 보유할 수 있다. expected fingerprint는 **같은 runtime
instance 내부**의 stale state를 차단할 뿐, runtime replacement 또는 active-session
authority 자체를 식별하지 않는다. save는 export 시점 snapshot을 저장하므로 rollover와
동시라면 현재 코드에 active owner의 ordering 정의가 없다.

`MainWindow._start_structured_recommendation()`은 collection snapshot과 trusted-turn
context를 worker constructor에 deep copy로 전달한다. `StructuredRecommendationWorker`도
이를 deep copy한다. request-local detach는 존재하지만 worker/result에 별도 captured
session field나 completion-time session comparison은 없다. 현재 callback guard는
`_advice_request_sequence`/owner token만 비교한다. `_begin_new_battle_session()`은 그
token을 무효화하지 않는다. 다만 현재 worker result는 presentation만 갱신하고
collection/runtime/store/ledger를 직접 mutate하지 않는다. 즉 old worker가 새 replay
state를 바꾸는 경로는 아직 없지만, old-session result display 차단도 아직 없다.
`closeEvent()`만 worker interruption을 요청하며 battle rollover는 cancellation을 하지
않는다.

`BattleStateStore.start_new_session()`은 initial state와 new ID를 받아 한 store object를
바꿀 수 있는 primitive이지만, runtime은 이를 노출하지 않는다. 이 primitive를 runtime
rollover에 쓰면 v15.33 immutable runtime/session 및 v15.34 command identity 계약을
약화하므로 v15.35 권장안에서는 사용하지 않는다.

## 확인된 lifecycle 공백

| 질문 | 현재 code 근거의 답 |
| --- | --- |
| runtime 생성자 / initial state source | production caller와 source 모두 없음; test만 factory를 호출한다. |
| MainWindow ID와 runtime ID 정렬 | 연결 없음. MainWindow는 collection만 `ui-session-N`으로 바꾼다. |
| new battle 시 runtime/commands 처리 | 생성·폐기·rebind 모두 없음. |
| replacement 순서와 partial failure | 정의 없음. MainWindow rollover는 collection과 UI fields를 순차 변경한다. |
| sequence authority | MainWindow의 `_capture_structured_observed_damage_confirmation()`이 `_observation_sequence`을 증가시킨다. collection은 검증/정렬만 한다. |
| collection sequence와 store sequence | 연결 없음. store는 apply된 reducer observation sequence만 `last_applied_observation_sequence`에 기록한다. |
| old preview/candidate/commands | caller-local로 남을 수 있으며 active authority 정책 없음. |
| stale worker result | request-token stale guard만 있고 captured session guard 없음; direct replay mutation은 현재 없음. |
| restore와 rollover | restore는 same-runtime/same-session recovery일 뿐 active ID를 바꾸지 않는다. rollover 대체물이 아니다. |
| startup recovery | entry point 없음; new-session creation과 구분하는 policy도 없음. |

## 후보 비교

| 후보 | Session authority | Atomic replacement | Stale protection | UI coupling | Testability | 권고 |
| --- | --- | --- | --- | --- | --- | --- |
| A. MainWindow가 collection/runtime/commands를 직접 순차 교체 | UI가 모든 authority 보유 | 낮음; 중간 factory 실패 시 부분 교체 위험 | callback/old command 검사를 UI마다 중복 | 높음 | Qt harness 의존 | 보류 |
| B. 별도 `BattleObservationRuntimeSession` lifecycle owner | core owner가 active session 한 개 보유 | 높음; complete bundle만 publish | owner identity/session gate를 한 곳에 둠 | 낮음 | pure offline | **권장** |
| C. existing runtime에 reset/rollover 추가 | runtime session authority가 가변 | 낮음 | old command/candidate가 같은 object를 오인 가능 | 낮음 | 기존 v15.33/34 계약 훼손 | 거부 |

## 권장 v15.35 계약

### 제목과 범위

`v15.35 Core Session Lifecycle Owner and Runtime Rollover`

새 core-only `BattleObservationRuntimeSession` (예상 파일:
`llm/advisor_observation_runtime_session.py`)이 active session bundle을 private으로
보유한다. owner는 collection, `ObservationReplayRuntime`, matching
`ObservationReplayPersistenceCommands`, 그리고 session-local next observation sequence를
함께 생성한다. MainWindow는 후속 wiring caller일 뿐 이 버전에서 수정하지 않는다. worker도
owner의 raw components를 받지 않는다.

초기 state 정책을 추정하지 않는다. factory input은 `(session_id, initial_state)`이며
caller가 detached exact `battle-state-v1` state를 공급해야 한다. `session_id`는 nonempty
string이고 initial state의 `session_id`와 exact match여야 한다. required state fields와
fingerprint calculation은 existing runtime/store가 authority를 유지한다. empty/default
battle state, UI selection에서 state를 만드는 정책, 그리고 new UUID/ID format 생성은
후속 caller policy이다. v15.35 owner는 caller-supplied ID를 사용한다.

### 생성과 publication

`create(session_id, initial_state)` 및 명시적 `rollover(session_id, initial_state)`만
lifecycle mutation 권한을 가진다. 후보 bundle은 다음 순서로 private에서 모두 만든다.

```text
detached input validate
→ ObservationCollection(session_id)
→ ObservationReplayRuntime.create(initial_state)
→ ObservationReplayPersistenceCommands.create(runtime)
→ exact session/identity consistency verify
→ active bundle single publish
```

모든 step이 성공하기 전에는 raw component나 partial bundle을 반환하지 않는다. creation
실패는 `invalid_initial_state` 또는 sanitized `creation_failed`이고 active session은
변하지 않는다. success는 최초 `session_ready`, replacement는 `session_replaced`를
반환한다. owner result는 detached session metadata/state/ledger/sequence만 노출하고 raw
mutable objects는 노출하지 않는다. provider, network, filesystem I/O, persistence save/load/
restore, rollback primitive는 factory와 rollover에서 절대 실행하지 않는다.

같은 current ID로 rollover를 요청하면 `session_unchanged`로 끝내며 state, fingerprint,
ledger, collection, next sequence를 변경하지 않는다. 이를 same-ID reset으로 해석하지
않는다. ID가 다른 경우만 replacement를 시도한다. retry는 자동으로 하지 않는다.

### Old-session과 stale authority

publish 뒤 old bundle은 active가 아니며 재활성화할 API가 없다. Python reference가 남아
read-only detached reads 또는 old runtime에 대한 명시적 local command를 할 수 있다는
사실과, **current active authority가 아니라는 사실**을 구분한다. owner-mediated preview,
apply, command dispatch는 captured session ID가 active session과 다르면 `stale_session`을
반환하고 store/ledger/collection을 mutate하지 않는다. old command를 새 runtime에 rebind하거나
old preview/envelope를 새 session으로 retag하지 않는다. foreign loaded envelope는 rollover를
일으키지 않으며 restore는 active runtime session ID를 바꿀 수 없다.

### Sequence authority

owner가 next observation sequence의 단일 allocator가 된다. 새 session의 next sequence는
0에서 시작하고 allocation은 explicit canonical observation capture 직전에 1씩 증가한다.
collection은 allocated positive sequence를 가진 entry만 저장한다. store의
`last_applied_observation_sequence`는 collection count가 아니라 **정상 replay apply로
committed된 마지막 candidate sequence**다. 따라서 collection에 capture되었지만 apply되지
않은 entry가 있어도 두 값은 달라질 수 있다. 같은 session에서 allocator rewind와 normal CAS
sequence regression은 금지한다. 새 session ID는 별도 namespace이므로 1부터 다시 시작할 수
있다. old producer input은 captured session ID를 요구하며 active ID mismatch 시
`stale_session`으로 reject되어 새 allocator를 증가시키지 않는다.

### Worker/result policy

향후 request handoff는 worker request와 completion envelope 모두에 captured session ID를
포함해야 한다. owner (또는 후속 UI adapter)는 completion 전에 active ID를 비교한다.
`A worker start → B rollover → A completion`은 `stale_worker_result`이며 A result는 B의
collection/runtime/store/ledger/sequence를 전혀 바꾸지 않는다. retag/retry/implicit new
session은 금지한다. provider cancellation은 이 boundary의 요구사항이 아니다. 현재
MainWindow worker가 replay를 mutate하지 않는다는 사실은 유지하되, session-aware display
callback wiring은 후속 UI boundary로 남긴다.

### Persistence 관계와 제외 범위

active session을 통한 command authority만 future caller에 허용한다. save/load/restore는
rollover가 호출하지 않는다. load-only는 active bundle을 바꾸지 않고, same-session restore는
recovery unit만 바꾸며 active session identity를 바꾸지 않는다. startup recovery, autosave,
file picker, UI buttons, worker wiring, cancellation, cross-session import, migration,
history/undo/redo, cloud/database는 범위 밖이다.

## Implemented core owner

`llm/advisor_observation_runtime_session.py` implements
`BattleObservationRuntimeSession` and `BattleObservationRuntimeSessionManager`.
The bundle factory accepts only a caller-supplied nonempty session ID plus a
matching valid initial state, defensively copies it, creates collection/runtime/
commands privately, and returns no partial bundle. It exposes detached
collection/state/ledger reads, explicit session-gated delegation, and a
monotonic allocator with initial last value 0 and first allocated value 1.
Allocation never mutates state, fingerprint, applied sequence, or ledger.

The manager has exactly one private active bundle. Different-ID `rollover()`
first constructs a complete replacement, then changes one active reference;
failure retains the old object and same-ID rollover returns `session_unchanged`.
It never resets, retags, or rebinds runtime/commands. Active-session admission
returns `stale_session` for an old ID; the worker completion gate returns
`stale_worker_result` without mutation. This is a core gate only, not worker
callback wiring.

Save/load/restore remain explicit, session-gated command delegation. Rollover
does not invoke them; foreign load cannot replace the bundle and restore cannot
change active session identity. The focused v15.35 suite has 31 passing cases
covering factory shape/detach, rollover preservation, allocator scope, stale
worker gates, command identity, implicit-persistence exclusion, and surface
restrictions. MainWindow, workers, UI, startup, autosave, provider cancellation,
file picker, import, history, and undo remain deferred.

## Proposed executable contract tests

- `test_session_factory_creates_matching_collection_runtime_and_commands`
  - initial active session: 없음.
  - lifecycle action: exact same-session initial state로 create.
  - concurrent/stale object: 없음.
  - expected active session: supplied ID; collection/runtime/commands metadata가 정확히 동일.
  - expected collection/runtime state/fingerprint/sequence/ledger: empty collection, initial detached store state와 fingerprint, next sequence 0, empty ledger.
  - expected status/error: `session_ready`.
  - forbidden side effect: UI/provider/network/filesystem I/O 또는 raw component 공개.

- `test_session_factory_rejects_invalid_initial_state_without_partial_owner`
  - initial active session: 없음 또는 known active A.
  - lifecycle action: malformed/foreign-labeled state로 create/rollover.
  - concurrent/stale object: A bundle.
  - expected active session: 없음 또는 A identity exact 유지.
  - expected collection/runtime state/fingerprint/sequence/ledger: A의 full detached values exact 유지.
  - expected status/error: `invalid_initial_state` 또는 `creation_failed`.
  - forbidden side effect: partial B publish, sequence reset, raw exception.

- `test_session_components_are_detached_and_share_exact_session_identity`
  - initial active session: A.
  - lifecycle action: metadata/state/ledger/collection snapshots mutate.
  - concurrent/stale object: returned mappings.
  - expected active session: A unchanged.
  - expected collection/runtime state/fingerprint/sequence/ledger: nested mutation 전 값 exact 유지.
  - expected status/error: `session_ready`.
  - forbidden side effect: alias 또는 raw mutable object exposure.

- `test_explicit_rollover_publishes_new_bundle_atomically`
  - initial active session: A with observation sequence 2, ledger entry, known fingerprint.
  - lifecycle action: explicit B ID + valid B initial state rollover.
  - concurrent/stale object: detached A snapshot.
  - expected active session: B only after complete construction.
  - expected collection/runtime state/fingerprint/sequence/ledger: B empty collection/ledger, B initial state/fingerprint, next sequence 0; A snapshot remains A.
  - expected status/error: `session_replaced`.
  - forbidden side effect: retagging A runtime/commands or restore invocation.

- `test_failed_rollover_preserves_existing_active_session`
  - initial active session: A with exact state/fingerprint/sequence/ledger/collection.
  - lifecycle action: B construction failure injection.
  - concurrent/stale object: A bundle.
  - expected active session: same A object identity and ID.
  - expected collection/runtime state/fingerprint/sequence/ledger: all exact before values.
  - expected status/error: `creation_failed`.
  - forbidden side effect: partial B publication or automatic retry.

- `test_duplicate_same_session_rollover_is_deterministic_and_non_mutating`
  - initial active session: A with nonempty collection/ledger.
  - lifecycle action: rollover using A ID.
  - concurrent/stale object: A command owner and preview.
  - expected active session: A identity unchanged.
  - expected collection/runtime state/fingerprint/sequence/ledger: full before values exact.
  - expected status/error: `session_unchanged`.
  - forbidden side effect: reset/rewind/rebind.

- `test_old_session_objects_cannot_be_reactivated_as_current`
  - initial active session: A then successful B.
  - lifecycle action: submit A-bound preview/command/result to active owner.
  - concurrent/stale object: A runtime, A commands, A envelope.
  - expected active session: B unchanged.
  - expected collection/runtime state/fingerprint/sequence/ledger: B full before values exact.
  - expected status/error: `stale_session`.
  - forbidden side effect: A reactivation, cross-session retag, or B mutation.

- `test_new_session_sequence_starts_from_defined_initial_value` and `test_old_session_producer_cannot_advance_new_session_sequence`
  - initial active session: A allocated through 3, then B.
  - lifecycle action: allocate B observation then submit A-captured producer input.
  - concurrent/stale object: A producer snapshot.
  - expected active session: B.
  - expected collection/runtime state/fingerprint/sequence/ledger: B receives sequence 1 only; stale A input leaves B allocator, collection, state/fingerprint/ledger exact.
  - expected status/error: allocation success then `stale_session`.
  - forbidden side effect: B sequence 2 from A or same-session rewind.

- `test_collection_sequence_and_store_last_applied_sequence_remain_session_scoped` and `test_sequence_regression_is_only_new_namespace_not_same_session_rewind`
  - initial active session: A has captured 2 and applied 1; B initial state has no applied sequence.
  - lifecycle action: rollover then allocate/apply B observation; attempt same-session lower normal CAS.
  - concurrent/stale object: lower-sequence B committed state.
  - expected active session: B.
  - expected collection/runtime state/fingerprint/sequence/ledger: B allocator/apply are independent of A; lower CAS preserves B state/fingerprint/ledger.
  - expected status/error: `sequence_regression` for same B rewind.
  - forbidden side effect: applying A sequence rules to B or rollback-only CAS.

- `test_old_worker_result_is_rejected_after_session_rollover` and `test_stale_worker_result_does_not_mutate_collection_store_or_ledger`
  - initial active session: A request carrying session A, then B rollover.
  - lifecycle action: submit A completion to session-aware handoff.
  - concurrent/stale object: detached A worker result.
  - expected active session: B.
  - expected collection/runtime state/fingerprint/sequence/ledger: B exact before values.
  - expected status/error: `stale_worker_result`.
  - forbidden side effect: apply, collection add, sequence allocation, retag, retry, or provider cancellation requirement.

- `test_current_session_worker_result_remains_eligible` and `test_worker_result_is_never_retagged_to_active_session`
  - initial active session: B.
  - lifecycle action: submit B then malformed/A worker completion.
  - concurrent/stale object: wrong captured ID.
  - expected active session: B.
  - expected collection/runtime state/fingerprint/sequence/ledger: only valid B result follows its explicit downstream contract; wrong result leaves all B values exact.
  - expected status/error: eligible result / `stale_worker_result`.
  - forbidden side effect: session-ID rewrite.

- `test_active_session_commands_are_bound_to_current_runtime`, `test_old_command_owner_is_stale_after_rollover`, `test_foreign_loaded_candidate_does_not_trigger_rollover`, and `test_restore_cannot_change_active_session_identity`
  - initial active session: A then B with commands/envelope candidates.
  - lifecycle action: command dispatch/load/restore through owner.
  - concurrent/stale object: A commands and foreign candidate.
  - expected active session: B exact ID.
  - expected collection/runtime state/fingerprint/sequence/ledger: unchanged unless explicit B same-session restore succeeds; restore never changes B ID.
  - expected status/error: `stale_session`, `session_mismatch`, or existing `restore_complete`.
  - forbidden side effect: command rebind, rollover, import, or partial mutation.

- `test_save_load_restore_are_never_invoked_implicitly_by_rollover`, `test_session_owner_does_not_expose_mutable_raw_components`, `test_session_lifecycle_has_no_ui_file_picker_autosave_startup_or_provider_hooks`, and `test_lifecycle_results_are_detached_and_sanitized`
  - initial active session: A.
  - lifecycle action: create/rollover and mutate returned result mappings.
  - concurrent/stale object: monkeypatched command methods and result mappings.
  - expected active session: selected A/B only.
  - expected collection/runtime state/fingerprint/sequence/ledger: exact expected bundle values and no aliases.
  - expected status/error: deterministic lifecycle status without raw exception/path.
  - forbidden side effect: implicit persistence command, UI/worker/provider hook, network/I/O, rollback/undo/reset public API.

## 예상 구현 범위와 완료 조건

예상 신규 production 파일은 `llm/advisor_observation_runtime_session.py`, 예상 신규
test는 `tests/test_v35_session_lifecycle_runtime_rollover.py`다. v15.35 core 구현은
MainWindow, worker, request builder를 수정하지 않고 owner와 offline contract tests에
한정한다. collection/runtime/commands에 private bounded seam이 실제로 부족할 때만 최소
수정한다. UI wiring, session-aware worker callback wiring, initial state domain factory,
startup recovery, autosave, file picker, import, and undo remain 후속 boundary다.

완료 조건은 matching private bundle, detached caller input/output, atomic active publish,
old-session rejection, session-scoped sequence allocation, no implicit persistence I/O, 그리고
focused/full offline regressions이다. 현재 production 상태는 이 설계의 구현 완료를 주장하지
않는다.

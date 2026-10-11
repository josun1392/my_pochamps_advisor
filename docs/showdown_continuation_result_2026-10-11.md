# Showdown 이전 continuation 결과 — 2026-10-11

**PARTIAL / CONDITIONAL GO.** 네이티브 실행 기반과 opt-in 설명 연결은
검증했다. 기본 추천 엔진의 전체 이전 완료를 의미하지 않는다.

## 기준 및 보존

- 시작 HEAD: `9d5cbbdd75b260ff19e6b59a1e6aa6aafa49b384`.
- 브랜치: `codex/showdown-mc-integration-v1`.
- canonical remote: `https://github.com/josun1392/my_pochamps_advisor.git`.
- 외부 Showdown 소스: `942cda71d14bf0618bd57991708a2e2734b6daba`,
  `gen9championsbssregmc`, clean tracked source.
- 원래 master HEAD `691d2dfab74f0eaed0488dad9735d808be14927b`와 기존 변경
  5건을 그대로 보존했다. master 병합, provider 호출, 공개 서버 접속은 없다.

## 이번에 추가한 범위

1. 관측 projection v2, legacy status 호환 wrapper, native counter v1을
   분리했다. 기존 sleep/freeze 기록과 replay, session 상태를 수정하지 않는다.
2. Early Bird는 native BeforeMove의 두 counter tick을 따른다. native 초기
   counter 3이면 첫 시도는 수면으로 막히고 다음 시도에 깬다. legacy의
   `duration // 2` 기록은 기존 소비자에 남긴다. native history 없는 과거
   Early Bird 시도는 호환되는 관측이라고 추정하지 않고 거부한다.
3. held item, major status, weather, terrain의 미확인 legacy None은 Unknown을
   유지한다. 확인된 absence만 native root에 제약으로 전달한다.
4. hazards, Aqua Ring/Ingrain/Leech Seed, Taunt/Encore/Disable, berry consumption,
   last executed move, qualifying hit count, groundedness를 기존 identity와
   session에 묶어 native state와 대조한다. unknown hazard schema는 거부한다.
5. 인간이 확인하는 `battle-decision-phase-v1`을 기존 confirmation → collection
   → reducer/runtime → persistence 경로에 연결했다. UI에서 턴·기술 선택·기절
   교체·피벗 교체와 요청 side를 명시한다. 취소는 무효과, 재확인은 idempotent다.
   이후 관측이 생기면 phase 재확인이 필요하다. 가정으로 native queue를 만들지 않는다.
6. native status callback의 조건부 분기와 일반 single-hit의 native 16 damage
   rolls를 Python API에 연결했다. 정확성 범위는 각각 callback과 fixed-crit
   damage 계산뿐이다. accuracy, 전체 action gate, survival, 전체 KO 확률을
   이 수치에서 추론하지 않는다.
7. `progress_native_showdown`은 native `runAction` 완료 후 한 move attempt에서
   멈추고 native queue를 저장·복원한다. `turnLoop`로 이어서 실행하며 native
   RNG, Update, faint/pivot, entry callback과 dynamic ordering을 보존한다.
   새 선택 요청과 진행 중인 queue를 구분하고 잘못된 API 사용을 거부한다.

관측 truth는 reducer/runtime에 남고 모든 native state와 counter는 명시적
가정이다. seeded sample과 Monte Carlo 평가를 exact probability로 표기하지
않는다. 기존 guaranteed-first ranking과 exact ledger 소비는 변경하지 않았다.

## 실제 교체 및 upstream 재사용

중복 offline damage-oracle pipeline을 제거하고 동일 native damage evaluator를
재사용하도록 바꿨다. `advisor/damage/`, `advisor/probability/`와 legacy lifecycle,
action ledger 및 ranking 구현은 삭제하거나 대체하지 않았다.

Showdown의 MIT 구현에서 TeamValidator, Battle, PRNG, native 조건/기술/item/
ability callback, `toJSON/fromJSON`, `runAction/turnLoop`, `getDamage`를 재사용한다.
Champions Lab/ai-vgc/poke-env의 완료된 조사는 반복하지 않았으며 새 소스를
복사하거나 서버/bot 의존성을 추가하지 않았다. 동작 원리와 primary source는
[호환 계약](showdown_state_compatibility.md)에 기록했다.

## 검증

- 중요 shared-state 경계 뒤 전체 오프라인: **7,619 passed, 2 failed / 541.16s**.
  네트워크 guard: parent 0, worker 4개 모두 0. 안정된 `befba50`에서 실행했다.
  실패는 이미 baseline에서 확인된 작은 화면 UI 레이아웃 2건이다:
  `test_pre_1_0_smaller_desktop_responsive_window`의 1280×720 Decide 버튼 노출과
  1366×768 Record 영역 배치. 새 Showdown 회귀로 주장하지 않는다.
- 이후 UI/queue/groundedness 변경의 집중 통합: **221 passed / 27.35s**, 최종 native
  테스트 **158개** 포함. session/persistence, 선택 action, ranking/guaranteed
  사실과 rollback을 함께 검증했다. 네트워크 시도 0. 전체 suite를 이 최종 HEAD에서
  다시 실행한 결과라고 주장하지 않는다.
- 별도 groundedness/legacy action-order/ranking 회귀: **48 passed**.
- POC: 합법 M-C team을 검증한 **1,152개** item/move/status/opponent-choice/seed
  조합에서 action pause → serialize → restore → continue와 일반 실행의 native
  상태·PRNG·실질 로그가 일치했다. resume이 추가하는 timestamp/separator는
  제외하고 log index를 재계산해 비교했다.
- native 전체 battle proof: **29 turns / 33 decisions**, 매 결정마다 복원.
  Protect, freeze timer 복원, seeded hit/miss와 명시적 교체를 실행했다.
- legacy 대비 조건부 single-hit fixed-crit **12개 사례의 16 rolls 전부 일치**.
  이는 모든 기술·전체 action/KO 분포의 parity 검증을 뜻하지 않는다.
- 실제 UI rollback: opt-in 후 Node process 종료, context 제거, 원래 추천 결과와
  runtime fingerprint/ledger가 그대로 유지됨을 확인했다. flags를 생략하거나
  `configure_showdown_shadow()`로 기본 경로로 돌아간다.
- 임시 Python 환경의 누락 package 파일을 `uv sync --dev --reinstall`로 복구했다.
  lockfile이나 프로젝트 dependency는 바꾸지 않았다.

## 성능

Windows x64 / Python 3.11.9 / Node 22.20.0. fixture에 대한 Python transport 포함
측정이며 모든 팀과 더 긴 rollout에 대한 latency 보장은 아니다.

| 작업 | 반복 | 중앙값 | p95 |
| --- | ---: | ---: | ---: |
| warm worker, 4개 scenario | 20 | 18.760 ms | 21.529 ms |
| 4 scenario × 3 candidate × 64 seed = 768 branches | 20 | 474.430 ms | 516.957 ms |
| 조건부 native damage 16 rolls | 30 | 8.301 ms | 11.156 ms |
| native sleep callback | 30 | 2.552 ms | 3.028 ms |
| 한 native move attempt | 30 | 3.784 ms | 4.248 ms |
| 저장 queue를 다음 request까지 진행 | 30 | 4.061 ms | 4.382 ms |

worker 시작 404.725 ms. 반복 결과 재현과 one-shot transport 일치를 확인했다.
별도 native restore-and-choice 200회 중앙값 0.862 ms, p95 1.261 ms.

재현: 외부 pinned checkout을 준비한 뒤
`scripts/verify_showdown_integration.py --showdown-checkout <checkout> --iterations 10`,
`scripts/benchmark_showdown_backend.py --checkout <checkout> --iterations 20`.
native pytest는 `POKEADVICE_SHOWDOWN_CHECKOUT`을 지정해야 실제 engine을 실행한다.

## 남은 전환 경계

기본 엔진 전환은 보류한다. 기존 `detached-selected-action-execution-result-v1`
소비자는 단일 행동에 소속된 exact probability mass, identity/provenance와
private post-action 상태를 요구한다. native queue API의 seeded terminal state는
이 계약을 만족하지 않는다. fixed-crit damage rolls와 status callback만 조합해서
전체 action/KO ledger라고 주장하면 생존 item, 다른 gate와 callback, 순서/phase의
권위를 누락한다. 표본을 exact mass로 변환하는 경로도 허용하지 않았다.

이 경계의 안전한 대체는 작은 damage 계산 함수 교환이 아니라 native outcome의
확률 범위와 행동·상태 권위를 정의하는 새로운 소비계약 설계가 필요하다. 과거
legacy pending action, same-turn event/first-EOT, effect applicability 및 일부
entry/counter representation은 matching native transcript가 없으면 계속 fail
closed 또는 기존 compatible consumer를 사용한다. 미지원 관측을 버려서 기본
엔진 적용 범위를 넓히지 않는다.

**다음 권장 milestone:** `native-exact-selected-action-v2` 계약을 설계하고 ordinary
Singles action부터 native callback 전체를 조건부 exact terminal branches로
검증한다. deferred opponent/residual queue와 live observation 권위를 분리하고
branch 비용/지원 범위/legacy fallback을 정의한 뒤 기존 exact 소비자를 단계적으로
교체한다. 표본 기반 순위가 필요하다면 별도 T1 제품정책 결정이며 현재 승인이 없다.
guaranteed-first 정책을 유지하는 현재 integration에는 추가 정책 변경을 하지 않았다.

## Git 및 시간

이번 continuation의 task-owned commit은 canonical remote에 exact-stage하여
push했다:

- `9ffe562` — versioned status/absence compatibility.
- `5c588dd` — observed effects native reconciliation.
- `b828767` — versioned decision-phase replay authority.
- `befba50` — Python-compatible conditional native damage query.
- `08dd76d` — explicit human phase capture UI.
- `6b853a0` — native action queue progression/restoration.
- `709f8ca` — groundedness verification and strict hazard schemas.

최종 evidence/rollback commit은 이 기록과 추가 rollback test를 포함한다.
원래 master의 forbidden/pre-existing 파일은 stage하거나 수정하지 않았다.

시작 HEAD 이후 변경 파일 27개:

- Transport: `advisor/showdown_bridge.py`, `tools/showdown_bridge/bridge.cjs`,
  `damage-oracle.cjs`, `damage-rolls.cjs`, `native-progress.cjs`, `status-gate.cjs`.
- Runtime 계약: `llm/advisor_battle_decision_phase.py`,
  `advisor_lifecycle_confirmation.py`, `advisor_observation_collection.py`,
  `advisor_observation_replay_runtime.py`, `advisor_reducer_state_model.py`,
  `advisor_replay_policy.py`, `advisor_showdown_compatibility.py`,
  `advisor_showdown_simulation.py`.
- UI: `ui/main_window.py`, `ui/widgets/battle_decision_phase_dialog.py`.
- 검증: `scripts/compare_showdown_legacy.py`,
  `tests/test_showdown_compatibility.py`, `test_showdown_damage_query.py`,
  `test_showdown_decision_phase.py`, `test_showdown_decision_phase_ui.py`,
  `test_showdown_native_progression.py`, `test_showdown_observed_effects.py`,
  `test_showdown_shadow_ui.py`.
- 기록: `docs/showdown_backend_migration.md`, `showdown_state_compatibility.md`,
  `showdown_continuation_result_2026-10-11.md`.

기록된 continuation 시작: **06:34:46 UTC / 15:34:46 KST**. 재개 후 실행 구간의
시작은 **09:44:27 UTC / 18:44:27 KST**다. 최종 응답에는 종료 시각과 두 구간의
실제 clock 경과를 별도로 표시한다. 중간 중단 시간을 active 작업시간으로
간주하지 않으며 CPU 시간/중단 제외 누적시간은 별도 계측하지 않았다.

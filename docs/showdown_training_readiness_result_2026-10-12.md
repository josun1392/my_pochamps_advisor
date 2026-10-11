# Showdown 초기 전략 학습 환경 검증 — 2026-10-12

**COMPLETE: 초기 policy/value 학습용 시뮬레이터 기반.** 네이티브 배틀,
부분 관측, 행동 마스크, 보상, 종료, 리셋, 체크포인트, 배치/병렬 실행을
하나의 로컬 환경으로 연결했다. 기존 guaranteed-first 추천 정책은 유지했다.
학습 모델이나 대규모 RL 실행은 이 작업의 산출물이 아니다.

## 완료 범위와 책임

- 기존 `9849d01`의 M-C Singles 실행, 조건부 세트/행동 평가, 네이티브
  피벗·강제 교체·queued action, 관측 재구성, 정확/표본 근거 분리,
  UI·비동기 세션 검사·롤백을 재사용했다.
- 새 `ShowdownEnvironment`는 살아 있는 네이티브 Battle을 기존 JSONL worker에
  보관한다. 기본 512개 결정 경계, 최대 4096개; worker당 128개 에피소드,
  배치당 최대 64개 요청으로 제한한다. 별도의 서버나 Python 전투 엔진을
  만들지 않았다.
- Showdown이 legality, 기술/교체, PP, Mega, 상태·특성·아이템, 진입/잔여 효과,
  PRNG, 요청/큐, 승패 및 직렬화를 소유한다. Python은 부분 관측 투영,
  소유자/리비전·프로세스 세대 검사와 학습용 입출력을 맡는다.
- 정책에는 자기 native request, 공개 player-channel 이벤트, 공개 HP 표시,
  Unknown을 유지한 요약 상태와 35개 행동 마스크만 전달한다. 상대 숨은
  세트·아이템·미공개 기술·정확 HP·상태 카운터·선택 대기 행동·RNG는 전달하지 않는다.
- 기존 reducer/runtime, 실제 관측·replay·session, legacy exact evidence와
  guaranteed-first 소비자는 유지한다. 시뮬레이션은 실제 관측을 수정하지 않는다.
  legacy 상태의 None/sleep/freeze 의미는 승인된 v2 호환 경계를 통해서만 해석한다.

## 새 결함 수정 및 호환 증거

- Champions HP 색상 접미사 `r/g/y`를 처리하며 상대 표시 HP를 정확 HP로
  승격하지 않는다. 기존 reconciled HP overlay의 공개 바도 갱신한다.
- 저장 시 timestamp 로그를 삭제하면 `lastMoveLine` 인덱스가 바뀌는 결함을
  발견했다. 같은 자리에 `|t:|0`을 넣어 로그 인덱스와 queued 실행을 보존한다.
- native exception, 잘못된 응답/보상/소유자, worker 종료 또는 세대 변경 시
  오래된 관측을 재사용하지 않는다. 마지막 명시적 checkpoint부터 복구한다.
  다른 에피소드의 정상 실행은 독립적으로 유지된다.
- Mega Gengar/Shadow Tag의 `maybeTrapped` 교체 거절을 실제 실행했다.
  native 요청만으로 마스크를 갱신하고 턴·PP·보상은 진행하지 않는다.
  거절 후 checkpoint/fork 및 재시도도 동일한 native 상태로 이어진다.
- 기존 detached resume와 새 환경을 16개 결정 경계에서 비교해 전체 native
  state가 일치했다. 기존 conditional damage-roll 비교 12개도 회귀에 포함했다.
  16개 damage roll은 전체 행동/KO 확률로 취급하지 않는다.
- native terminal reward는 승리 +1/패배 -1/무승부 0. 한도 소진은 truncation과
  보상 0이며 게임의 무승부가 아니다. 양쪽 마지막 포켓몬의 Destiny Bond
  기절은 HP 동률로 판정하지 않고 native 승자를 사용한다.

## 업스트림 재사용

핀 `942cda71d14bf0618bd57991708a2e2734b6daba`의 Battle, TeamValidator,
Side.choose/commitChoices, ChoiceRequest, getHealth, extractChannelMessages,
toJSON/fromJSON, PRNG와 기존 RandomPlayerAI를 사용한다. legality/팀 선택의
중복 construction을 공용 builder로 합쳤고 legacy mechanics 삭제는 하지 않았다.

poke-env `7ff6212e4e738efd46f1ea52035b37a8bba1e386`/0.16.1을 별도 환경에서
실행했다. 실제 native 이벤트/request의 offline 파싱은 호환됐지만, 교체 후
고정 team dictionary 순서의 mask는 native request 순서와 달랐다. 서버 중심
Gym 환경을 추가하는 대신 기존 worker 위에 좁은 어댑터를 구현했다.
프로젝트에 새로운 RL 프레임워크나 poke-env 의존성은 추가하지 않았다.

참조: [Showdown 핀](https://github.com/smogon/pokemon-showdown/tree/942cda71d14bf0618bd57991708a2e2734b6daba),
[poke-env 검증 핀](https://github.com/hsahovic/poke-env/tree/7ff6212e4e738efd46f1ea52035b37a8bba1e386),
[Showdown의 동시 마지막 기절 판정 FAQ](https://pokemonshowdown.com/pages/faq).

## 검증과 측정

- 기본 non-slow 전체 오프라인 회귀: **7,804 통과 / 기존 UI 레이아웃 실패 2개**,
  579.48초. parent와 xdist 4 worker의 네트워크 시도 모두 0.
- 마지막 Showdown 집중 회귀 **299 통과**, 47.57초. 이후 추가한 실제
  Shadow Tag 거절/재시도 테스트 **1 통과**, 0.83초. 새 환경 테스트는 총 40개.
- 기존 baseline-only 실패는
  `test_1280x720_decide_record_and_details_controls_remain_reachable`의 Decide
  visibility 및 `test_record_next_turn_is_visible_at_1366x768_and_large_window`의
  `485 < 220` 레이아웃 문제다. 앞선 baseline에서 확인된 동일한 실패이며
  이 작업의 새 회귀는 없다.
- 실제 자동 배틀: 4 worker × 8 lanes에서 **512/512 native 종료**, truncation 0,
  344승/168패, 14,304개 결정(공격 phase 12,569 / 교체 phase 1,735).
  13.331초, **38.41 배틀/초 · 1,072.98 결정/초**. 배치 시간/활성 에피소드의
  amortized step P50/P95는 2.44/4.53ms이며 개별 RPC 지연과는 다르다.
- worker별 peak Node RSS 161.2–170.6MiB, heap 93.8–101.0MiB.
  단일 worker/8 lanes의 같은 512개는 18.533초, 27.63 배틀/초,
  step P50/P95 0.962/1.245ms, peak RSS 253.8MiB/heap 178.5MiB였다.
  이 값은 해당 Windows 머신의 fixture 측정이며 모든 팀/호스트 성능 보장이 아니다.
- 장시간 동일 worker의 반복 reset을 추가 확인했다: **1,024/1,024 종료**,
  28,721결정, 36.785초, 710승/314패, truncation 0. 27.84 배틀/초,
  peak RSS 264.1MiB/heap 188.7MiB. 512개 실행 대비 에피소드 수가 두 배일 때
  peak RSS는 약 10.4MiB 증가했다. 종료 시 native handle 0/process close를 확인했다.
- 두 실행의 전체 trace digest가 동일했다:
  `5c9261889685272b8baa5664f4f250f089f913f0e191353d2408d68acd6774c3`.
  worker별 scalar replay, checkpoint/save/restart 및 종료 시 native handle 0,
  process close를 확인했다. 이 정책의 승패 비율은 학습 모델의 강도나 승률
  추정치를 뜻하지 않는다. 별도 native draw와 truncation 테스트도 통과했다.
- 실제 Qt UI 128개 조건부 표본/최대 32결정, 3회 재현: warm P50/P95
  1281/1308ms, UI dispatch 92.5ms, cold end-to-end 1923ms.
  `runtime_immutable`, `rollback_default_equal`은 true이고
  `default_policy_changed`는 false. 독립 native/legacy 비교 **12/12 일치**.
- 모든 독립 검증 스크립트도 소켓 차단 harness로 실행했으며 접속 시도는 0.

## UI와 재현

기존 실제 Qt 전략 버튼 → native 조건부 평가 → 결과 표시 → 설정 해제 →
기본 출력 복구를 자동 실행했다. runtime snapshot과 applied ledger는 불변이고,
기본 추천 정책은 바뀌지 않았다. 이는 실제 인간 경기 기록을 수행한 검증은 아니다.

```powershell
# 외부의 새 디렉터리에 핀된 엔진 설치 (이미 설치돼 있으면 재사용)
uv run python scripts/setup_showdown.py --destination C:\temp\poke-showdown-mc
$env:POKEADVICE_SHOWDOWN_CHECKOUT = 'C:\temp\poke-showdown-mc'
uv run python scripts/verify_showdown_training.py --showdown-checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT --episodes 32 --workers 2 --lanes 4
uv run python scripts/verify_showdown_strategy.py --showdown-checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT --iterations 3 --seeds 4 --horizon 32 --export-demo C:\temp\hypotheses.json
uv run python main.py --showdown-shadow C:\temp\hypotheses.json --showdown-checkout $env:POKEADVICE_SHOWDOWN_CHECKOUT
```

서로 다른 실제 관측과 맞지 않는 demo 가정은 거절돼야 한다. 수동 스모크에서는
시나리오/공격·교체 비교, 표본 수/미완료 표시, 세션 변경 결과 폐기, 설정 해제
후 기존 출력 복귀를 확인한다. 설정 없이 실행하면 기존 backend를 사용한다.
실험 순위 플래그는 기본 꺼짐이다.

## 남은 제한과 T1 판단

- 학습 정책의 team-preview 선택은 아직 인터페이스에 없다. 출전 3마리는
  coordinator가 명시적으로 정한다. 초기 battle-action 학습에는 지장이 없다.
- 인간 경기의 wall-clock timer는 학습 환경에서 모델링하지 않는다.
  환경 decision limit을 실제 경기의 시간 종료/무승부로 해석하지 않는다.
- public state는 요약이며 완전한 protocol feature encoder가 아니다.
  정책은 전체 player-visible history/own request를 사용할 수 있다. 고정 tensor
  encoding, recurrent state, 학습 curriculum, PPO/DQN 및 평가 상대 구성은 다음 작업이다.
- 실전 미지 상태의 reconstruction은 관측과 명시적인 가상 history/set의 모델이다.
  원본 경기의 숨은 진실 복구를 주장하지 않는다. 지원되지 않거나 provenance가
  부족한 legacy 상태는 기존 consumer를 유지하거나 native 경계에서 거절한다.
- 모든 legal 팀/효과 조합과 모든 upstream bug를 검증한 것은 아니다. 초기
  학습 환경 사용을 막는 재현 가능한 결함은 현재 검증 범위에서 없다.
- T1은 제한된 초기 policy/value 학습과 평가 계획을 승인할 수 있다. 대규모 GPU
  RL의 자원·시간 예산, reward/curriculum 및 production ranking 적용은 별도 결정이다.
  학습 모델의 강도나 sampled 승률을 보장 근거로 간주하는 정책은 승인되지 않았다.

환경 계약과 coordinator 사용법은 [training contract](showdown_training_environment_contract.md)에 있다.

## Git와 작업 시간

- 구현/테스트/계약 커밋: `16b7132`.
- 작업 브랜치: `codex/showdown-mc-integration-v1`.
  canonical remote는 `https://github.com/josun1392/my_pochamps_advisor.git`이며
  검증된 task-owned 파일만 stage한다. master에 merge하지 않는다.
- 원본 master는 `691d2dfab74f0eaed0488dad9735d808be14927b`이고, 사전 변경 5개는
  상태 확인만 했으며 수정하거나 stage하지 않았다. 보호 파일 및 secrets는 다루지 않았다.
- 작업 시작 12:35:20 UTC. 재개 전 마지막 기록은 13:07:13 UTC, 재개 기록은
  15:08:38 UTC다. 구현 커밋 시점 15:26:02 UTC까지의 기록된 활동 구간은
  49분17초이고 벽시계 경과는 2시간50분42초다. 마지막 commit/push 검증 시간은
  최종 사용자 보고에 포함한다. 날짜 표기는 현재 프로젝트 환경의 2026-10-12를 사용했다.

# Native outcome consumer migration — 2026-10-11

판정: **PARTIAL / CONDITIONAL GO**. 검증한 네이티브 결과를 선택 행동/게이트
소비자에 연결했다. 전체 생산 백엔드 전환이나 추천 정책 변경은 완료하지 않았다.
기본 백엔드, guaranteed-first 순위, 관측/reducer/runtime/session 권한은 그대로다.

## 검증한 범위

- `showdown-native-outcome-evidence-v1`: 전체 캡처 지문, 세션/D0 분기,
  행동/대상/메타데이터, 네이티브 phase, 원본/결과 체크포인트와 가상 모델을 결합한다.
  `native_seeded_execution`에는 확률을 부여하지 않는다.
- 상수가 아닌 RNG 호출을 거부하는 네이티브 실행 증명: 한 move attempt의 완료까지
  관측 가능한 기계적 결과의 조건부 질량 1. 표본 성공 횟수나 16개 피해 roll로
  전체 행동 확률을 주장하지 않는다. 뒤의 행동, residual, 미래 PRNG 분포, 상대 세트
  사전확률은 제외한다. RNG/선택 순서가 불확실하면 부분 확률을 내보내지 않는다.
- Recover: 홀수/짝수 최대 HP, 낮은 HP, 상한, full-HP 실패까지 기존 HP 결과와 비교했다.
  Slack Off: 상대의 가상 Swords Dance 이후 이미 예약된 네이티브 행동을 실행했다.
  상대의 가상 boost는 관측 상태로 승격하지 않았다. Soft-Boiled의 호환 catalog
  항목은 보존했지만 이번에 합법 M-C 실행 fixture를 입증하지 않았으므로 커버리지에
  포함하지 않는다.
- Night Shade와 No Guard Machamp의 Seismic Toss: 네이티브 명중/피해/PP/기절 처리와
  남은 큐를 보존하는 조건부 HP 경로를 기존 selected/gated 소비자에 연결했다.
  native serialization과 summary의 HP가 다르면 거부한다. 알려진 PP/hit counter나
  호환 뷰에 표현하지 못하는 item/status/stage/field 변화는 fail closed 한다.
- 네이티브 교체 진입 batch 증명: switch/instaswitch/runSwitch를 재사용한다.
  SR/Spikes 0–3층, Air Balloon에 대해 기존 hazard 엔진과 비교했다. Toxic Spikes,
  Sticky Web, 진입 기절은 네이티브 실행으로 검증했다. 다음 공격/residual은 포함하지
  않는다. 이 결과는 detached query이며 기존 live 파생 관측 producer를 대체하지 않는다.
- Early Bird와 역사적 sleep/freeze v1 의미는 재해석하지 않았다. 이전에 승인/구현한
  versioned status, known absence/Unknown, decision-phase 경계의 회귀도 통과했다.

## 소비 경계와 rollback

선택 소비자의 `family_authorities.native_direct_heal_outcome` /
`native_attack_outcome`, 게이트 소비자의 `extension_authorities.native_direct_heal_outcomes`
/
`native_attack_outcomes`가 명시적인 opt-in이다. 제공하지 않으면 기존 경로를 사용한다.
바인딩된 stochastic 증명 거부만 기존 compatible consumer로 돌아간다. stale,
misclassified, contradictory 증거는 거부한다. gate가 만든 새 분기에 root 증거를
재바인딩하지 않는다. 네이티브 class/scope/전체 checkpoint를 결과에 보존한다.

MC shadow는 별도 기존 경로다. 표본 값은 exact 소비자에 진입하지 않는다. 기존
production orchestration이 새 증거를 자동으로 생성/순위에 투입하지 않는다.
옵션 제거 후 기존 결과의 동등성, runtime 불변성, worker 종료를 실행 검증했다.
legacy 코드 삭제/retirement는 없다.

## 검증과 성능

- 공유 selected-action 경계 변경 후 전체 오프라인 pytest: **7,690 passed / 2 failed**,
  821.36초. 실패 둘은 이전 baseline에서도 입증한 작은 화면 UI layout 문제다:
  `test_1280x720_decide_record_and_details_controls_remain_reachable`,
  `test_record_next_turn_is_visible_at_1366x768_and_large_window`.
- 이후 네이티브 전체 및 인접 전략/상태 gate 회귀: **308 passed**, 116.62초.
  마지막 provenance/질량/예약 Slack Off 보강 후 집중 회귀: **66 passed**, 5.63초.
  전체/308개 run 모두 socket guard: parent 및 4 worker 네트워크 시도 **0**.
- 기존 Python/native 고정-crit 조건부 피해 12개 비교: **12/12 일치**.
  이는 전체 행동/KO 확률 parity를 뜻하지 않는다.
- 반복 실행 및 rollback 스크립트: 100회씩, 결과 재현/관측 상태 불변/worker 종료 통과.

| 측정 대상 | 중앙값 | p95 |
| --- | ---: | ---: |
| native 회복 증명 + 호환 소비자 | 10.218 ms | 11.475 ms |
| native 고정 피해 증명 + 호환 소비자 | 11.666 ms | 14.656 ms |
| native 교체 진입 증명 | 3.894 ms | 4.710 ms |
| 기존 worker 4개 시나리오 warm batch (20회) | 19.423 ms | 26.155 ms |
| MC 4세트 × 3후보 × 64시드 = 768 branch (20회) | 520.045 ms | 580.339 ms |

회복 proof worker+fixture 첫 호출 422.108 ms. 별도 4시나리오 worker 첫 호출
462.298 ms. 현재 Windows 환경의 대표 fixture 측정이며 전체 상태의 latency 보장은 아니다.

재현 명령(외부 pinned checkout과 기존 uv Python 3.11 환경 사용):

```powershell
uv run python scripts/verify_showdown_outcome_consumer.py --showdown-checkout <checkout> --iterations 100
uv run python scripts/compare_showdown_legacy.py --checkout <checkout>
uv run python scripts/benchmark_showdown_backend.py --checkout <checkout> --iterations 20
```

## upstream 및 남은 전환 경계

pin `942cda71d14bf0618bd57991708a2e2734b6daba`, format
`gen9championsbssregmc`. Native Battle, TeamValidator, PRNG, runAction/runSwitch,
toJSON/fromJSON/restart, native queue/requests/field/item/status 처리를 재사용한다.
RNG 알고리즘이나 피해/회복/진입 mechanics를 Python으로 다시 쓰지 않았다.

[Showdown exhaustive runner](https://github.com/smogon/pokemon-showdown/blob/942cda71d14bf0618bd57991708a2e2734b6daba/sim/tools/exhaustive-runner.ts)는
테스트 조합을 탐색하는 도구다. [pkmn/engine Gen I Chance/Calc](https://github.com/pkmn/engine/blob/main/src/lib/gen1/README.md)도
Champions용 그대로 적용할 수 있는 확률 API가 아니다. Champions Lab의 serialization/
reseed 접근도 조사했지만 완전한 M-C 확률 열거기를 확인하지 못했다. 추가 upstream
코드를 복제하지 않았다.

잔존 legacy 의존: 일반 공격의 명중/급소/피해/secondary/action-order/복합 다중 행동 exact
ledger, legacy progression 소비자, 기존 live 파생 관측/기본 ranking. 네이티브 일반 공격,
switch/pivot/multi-turn 실행과 MC는 이미 지원하지만 이를 기존 exact 확률로 승격하지 않는다.
교체/상태/stage/item의 모든 legacy projection을 새 HP 경로가 대체한 것도 아니다.

현재 막힌 전환은 **일반 stochastic 네이티브 결과로 기존 exact/guaranteed 소비자를
전부 교체하고 default로 만드는 것**이다. T2가 금지한 대규모 custom RNG/기계적 열거를
구축하지 않았다. 독립 네이티브 실행/표본 인프라의 사용은 계속 가능하다.
T1 결정이 필요한 것은 sampled outcome/value를 생산 전략 평가에 어떻게 사용할지와
exact/guaranteed 증거와의 비교 정책이다. 이번 변경은 그 결정을 대신하지 않는다.

다음 milestone: 새 class/scope가 끝까지 보존되는 일반 네이티브 outcome/value 채널과
전략 설명 소비자 연결, 세트별 조건부 결과의 가시화/평가. 순위 투입은 별도 T1 정책
결정 이후 진행한다. 확률 완전성이 증명된 slice만 기존 exact consumer 대체 대상으로 삼는다.

## Git 및 작업 시간

시작 local/remote `4374171e7a073db153dbeb0e9539e382f06c753c` 검증.
branch `codex/showdown-mc-integration-v1`, canonical remote
`https://github.com/josun1392/my_pochamps_advisor.git`.
구현 commit `1440532`, `609eaad9f3acff00d12fce902f0789463da39563` push 확인.
이번 최종 검증 script/test/report는 별도 검증 checkpoint commit에 포함한다.

원본 master HEAD `691d2dfab74f0eaed0488dad9735d808be14927b`와 기존 5개 변경의
상태를 시작/종료 시 확인했다. 원본 작업 파일을 수정하지 않았다. secrets,
config/env.example, logs/token_usage.jsonl의 내용을 읽거나 수정하지 않았다
(금지 파일의 git status 경로 표시만 확인).
master merge, provider 호출, public battle server 참여는 없다.

이 continuation 작업 시작 2026-10-11 10:08:10 UTC. 마지막 구현/실행 검증 시각
11:01:42 UTC까지 53분 32초. 최종 Git 확인/보고까지의 실제 경과 시간은 최종 응답에 기재한다.

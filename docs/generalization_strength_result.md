# Learned strategy generalization and strength V1

상태: **PARTIAL**. 확장 환경, 학습·검증·UI 통합은 완료했다. v1 대비
일반화 향상은 확인했으나, 기존 v2와 휴리스틱을 일관되게 이기는 학습 모델은
입증하지 못했다. 기본 guaranteed-first 추천 정책은 변경하지 않았다.

## 구현과 결함 수정

- 합법적인 합성 M-C 커리큘럼 v3: 학습 40종, 종이 겹치지 않는 미관측 14종.
  공격·우선도·교체·피벗·회복·장판·능력 상승·상태이상·날씨 세트를 포함한다.
  고정 Showdown TeamValidator로 822개 팀을 검증했다. 실전 사용률 분포를
  재현한 데이터셋은 아니다. 불법 종·기술은 네이티브 검증 결과로 교정했다.
- 공개 Dex 기반 입력 v3: 문맥 341 + 35개 행동 × 202 = 7411차원.
  회복/흡수/반동, 직접 상태이상, 상승 스탯, 장판/스크린, 공개된 진영 상태,
  자신의 알려진 기술 구성까지 구분한다. 상대 숨은 기술·아이템·세트·RNG는
  입력하지 않는다. v1/v2 계약과 아티팩트는 유지한다.
- 네이티브 흑안개 이후 공개 관측의 공격 +2가 남는 결함을 실제 대전으로
  재현하고 수정했다. 전역/대상 상승 초기화·부분 초기화·반전 이벤트를
  투영한다. 라이브 reducer, 기록된 이벤트, 기존 수면/빙결 의미는 수정하지 않았다.
- v2 함수 보존 가중치 이전: 추가 특징의 초기 가중치는 0, 새 크기의 Adam
  상태는 새로 만든다. 24개 네이티브 관측에서 합법 행동 분포와 가치 출력이
  float32 허용 오차 안에서 유지됨을 확인했다. 같은 encoder 후속 학습은
  기존 optimizer 상태를 복원한다.
- 기존 SB3-contrib 2.7.1 MaskablePPO, Torch 2.8 CPU, poke-env 0.10의 공개
  휴리스틱과 검증된 네이티브 환경·트레이너를 재사용했다. PPO·배틀·RNG를
  새로 구현하지 않았다. 회복/상태이상/픽3 장판 판단을 추가한 실험 휴리스틱은
  기본 추천에 연결하지 않았다.

재사용 API는 [MaskablePPO 공식 문서](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html)와
[poke-env 공개 baseline 예제](https://poke-env.readthedocs.io/en/stable/examples/quickstart.html)에 근거한다.

## 실제 학습

검증 선택: 24개 사례 × 고정 상대 4종 = 체크포인트당 96전. 기존 v2,
max-power, 원래 휴리스틱, 공개 전술 휴리스틱을 사용했다. 역사 상대는
실험 시작 시 고정된 체크포인트이며, 무제한 동시 자기대전이 아니다.

| 실험 | 새 teacher 판단 | 새 PPO 전이 | 검증 승수/96: 시작 → 이후 | 보존 모델 |
|---|---:|---:|---|---|
| cold v2, seed101 | 8192 | 32768 | 39 → 43 → 38 | PPO 16384 |
| cold v3, seed101 | 8192 | 32768 | 37 → 38 → 40 | PPO 32768 |
| v2→v3, seed101 | 8192 | 16384 | 38 → 49 | PPO 16384, 최종 선택 |
| v2→v3, seed211 | 8192 | 16384 | 40 → 38 | teacher-only |
| v2→v3, seed307 | 8192 | 16384 | 38 → 36 | teacher-only |
| seed101 후속, seed401 | 0 | 49152 | 49 → 49 → 46 → 49 | 원본 유지, 정체 중단 |

이전 실험의 독립 학습 시드는 101/211/307이다. 동일한 공개된 사전학습
v2 출발점을 공유하며, 시드별 시연·에피소드·미니배치·PPO 난수는 독립이다.
401은 101 모델에서 이어진 후속 실험이며 독립 사전학습으로 세지 않는다.
307은 전술 teacher도 바꿨으므로 teacher 효과를 시드 효과와 분리할 수 없다.

유효 학습: **163840 PPO 전이 + 40960 teacher 판단, 종료 대전 19989회**.
모든 PPO 전이는 완전 rollout으로 실제 학습되었다. 선택 모델은 새 teacher
8192판단/12epoch/768업데이트 + 새 PPO 16384전이/512업데이트이다.
142338개 매개변수이며 Adam 상태가 저장된다. 더 긴 학습은 개선되지 않아
원래 체크포인트를 유지했다.

흑안개 결함을 발견한 초기 파일럿은 별도 보존·선택 제외했다:
수집 43660 / 실제 학습 43520 PPO 전이, teacher 16384, 종료 대전 5865.
작업 전체는 수집 PPO 207500 / 학습 PPO 207360, teacher 57344이다.

## 튜닝에 사용하지 않은 최종 평가

커리큘럼 v3의 새 test/unseen namespace, offset90000. 이전에 살펴본
v2 최종 테스트를 튜닝 대상으로 재사용하지 않았다. 평가 전에 선택 모델을
고정했다. split마다 96개 사례와 같은 4개 상대, 정책당 384전,
10개 정책 총 **7680전**, 무승부·시간 제한 종료 0회.
다른 모델의 최종 결과는 진단용이며 모델 재선택에 사용하지 않았다.

| 정책 | 새 팀 test: 승–패, 빈도 | 미관측 14종: 승–패, 빈도 |
|---|---|---|
| random | 60–324, 15.6% | 43–341, 11.2% |
| v1 | 143–241, 37.2% | 138–246, 35.9% |
| 기존 v2 | 191–193, 49.7% | 206–178, 53.6% |
| cold v2 | 213–171, 55.5% | 204–180, 53.1% |
| cold v3 | 210–174, 54.7% | 210–174, 54.7% |
| 선택 v3 seed101 | 214–170, 55.7% | 203–181, 52.9% |
| v3 seed211 보존 모델 | 209–175, 54.4% | 203–181, 52.9% |
| v3 seed307 보존 모델 | 213–171, 55.5% | 200–184, 52.1% |
| 원래 휴리스틱 | 211–173, 54.9% | 204–180, 53.1% |
| 공개 전술 휴리스틱 | 223–161, 58.1% | 214–170, 55.7% |

선택 모델의 짝지은 승률 차이와 95% 사례-cluster bootstrap CI
(96개 독립 사례, 상대 4층을 함께 재표집, 2000회):

| 기준 | test 차이 pp [CI] | unseen 차이 pp [CI] |
|---|---|---|
| 기존 v2 | +6.0 [0.0, 11.7] | −0.8 [−3.9, 2.6] |
| 원래 휴리스틱 | +0.8 [−3.9, 5.5] | −0.3 [−3.9, 3.6] |
| v1 | +18.5 [11.7, 25.0] | +16.9 [9.9, 24.2] |

v2 대비 test 차이도 하한이 0이며, unseen에서 이점이 없다. 따라서
일관된 v2/휴리스틱 우위를 주장할 수 없다. cold v3도 cold v2를 확실히
능가하지 않았다. 공개 전술 휴리스틱은 원래 휴리스틱 대비 unseen에서
+2.6pp [0.8, 4.9]로 소폭 개선됐다. 이 결과를 보고 추가 튜닝하지 않았다.

선택 모델의 할인 보상 MSE는 test 0.651 / unseen 0.693이며 기존 v2는
0.841 / 0.772였다. 각 정책이 방문한 경로의 표본 오차로, 고정 상태에서의
인과적 가치 개선이나 보정된 승률을 뜻하지 않는다.

## 한계와 다음 단계

선택 모델의 자발적 교체는 test 2회 / unseen 10회, 기존 v2는 30/80회다.
unseen에서 회복·상태이상·능력 상승 기술도 거의 선택하지 않았다.
행동 공간은 지원하지만, 교체·방어·setup 판단이 강해졌다는 증거는 없다.
초기 teacher fit 93%대도 실전 강도를 보장하지 않았다.

다음은 교체가 유리한 상황과 회복·setup의 성공/실패가 균형 있게 들어가는
학습·검증 데이터, 더 강한 공개 정보 기반 상대가 필요하다. 새 입력만
추가하거나 PPO 시간을 늘리는 것으로 충분하지 않았다. 이 최종 홀드아웃을
재튜닝 대상으로 삼지 말고 다음 실험에는 새 namespace/offset을 예약한다.
현재 결과만으로 대규모 GPU 학습 확대나 기본 추천 변경을 권하지 않는다.
예산을 정한 다음 CPU 실험은 독립 실행 트레이너로 진행할 수 있다.

## 검증·성능·책임 분리

- 최종 관련 회귀 250개 통과, 오프라인 socket guard 외부 시도 0.
  앞선 네이티브 Haze 실패는 수정 후 통과했다. 기존 두 작은 화면 UI 레이아웃
  실패는 이번 변경의 회귀로 분류하지 않았고 전체 테스트를 다시 돌리지 않았다.
  수정 범위 Ruff 통과; 기존 v2 encoder의 두 E731 lambda 경고는 기존 코드다.
- 실제 Qt 경로: 모델 로드·표시·기본 추천 복귀, 런타임 snapshot 및 관측
  ledger 불변을 확인했다. 별도 고정 smoke 12전은 10승/2패이며 독립 실력
  평가에 포함하지 않는다. 모델 로드 1667ms, 추론 p50 1.509ms / p95 2.022ms,
  UI 완료 931ms. 새 입력의 비용은 늘었으나 실시간 추론 범위다.
- CPU만 사용, Torch 1 thread, 네이티브 worker 4개, 작업 트리 CPU hard cap
  12.5%, 커밋 메모리 cap 3GiB. 유효 학습 벽시계 1037.57초,
  tree CPU 1139.67초, 최대 커밋 메모리 2932.94MiB. 최종 평가 277.82초,
  27.6전/초, 최대 커밋 1201.51MiB. 모든 실행과 자식 worker 종료 확인.
- 관측/reducer/replay/UI와 legacy exact evidence, guaranteed-first ranking은
  유지한다. Showdown은 네이티브 실행, NN은 명시적으로 실험적인 정책/가치
  증거다. 표본 전적·정책 분포·확률적 추정·정확한 보장은 분리했다.
  기존 v1/v2 모델은 수정하지 않았고 기본 backend/ranking도 바꾸지 않았다.

## 아티팩트와 재실행

선택 모델: `models/showdown_generalization_v3/model.zip` 및 `model.json`.
SHA256 `fe52cd3b4e288c242176a6574769bdf1cd8fb5dbedad8b015496cb5b5dcfd57d`.
`diagnostics/`의 네 모델은 비교 재현용이며 기본 모델이 아니다.
최종 개별 전적, CI, 행동/네이티브 기술 집계는 `final_test.json`,
`final_unseen.json`; 전체 설정·선택 경로·자원·파일럿 제외 사유는
`experiment_summary.json`; UI/rollback proof는 `readiness.json`에 있다.

기존 Python 3.11 학습 환경에서 전용 migration checkout을 사용한다.
환경 준비는 `docs/autonomous_learning.md`를 따른다.

```powershell
$engine = $env:POKEADVICE_SHOWDOWN_CHECKOUT
$run = Join-Path $env:LOCALAPPDATA 'PokeAdvice\training\my-generalization-run'
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/generalization_cpu.json --checkout $engine --output $run
```

기본 예산은 최대 30분이며 체크포인트·검증·정체 중단이 자동이다.
같은 설정의 중단 실행은 `--resume`; 완료 후 추가 학습은 새 설정/폴더에서
`initial_model`, 동일 encoder, `warmstart_decisions:0`으로 지정한다.
이는 같은 encoder optimizer를 복원한다. v2에서 v3로 이전하려면
`transfer_model`을 지정하며 optimizer는 새로 만든다.

새 독립 평가 프로그램은 `scripts/evaluate_showdown_generalization.py --help`.
신뢰하는 로컬 checkpoint만 로드하고 새 출력 폴더를 지정한다. 기본 비교에
random/원래/전술 휴리스틱과 고정 v2 상대가 포함된다. 모델 label/path를
`--model label=path`로 추가한다. 이미 읽은 offset90000을 다음 튜닝/최종
평가로 재사용하지 않는다.

UI에서는 기존 실험 설정의 model_path, catalog_path 및 expected_model_id를
지정한다. catalog는 `models/showdown_initial_v1/catalog.json`, v3 보조 공개
Dex는 `models/showdown_tactics_v1/catalog.json`이다. 실험 설정을 해제하면
기본 추천으로 돌아온다. `verify_showdown_learning.py --export-demo <새파일>`로
선택 모델의 샘플 설정을 생성할 수 있다.

Codex 종료 후 detached 실행 지속은 보장하지 않는다. 사용자 PowerShell의
foreground 실행으로 터미널을 유지하고, STOP/기한/작업 트리 제한을 사용한다.
이번 작업 종료 시 남겨 둔 학습 프로세스는 없다. 원본 master의 기존 5개
변경은 보존했고 변경은 migration branch에만 커밋한다.

작업 시작 2026-10-11 23:17:31 UTC (10월12일 08:17:31 KST),
최종 아티팩트 검증 완료 2026-10-12 00:26:33 UTC.
커밋/원격 확인 전 경과 69분02초; 최종 시각은 progress journal에 기록한다.

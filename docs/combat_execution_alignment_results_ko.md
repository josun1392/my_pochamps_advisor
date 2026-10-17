# Combat Execution Policy Alignment Gate — 결과 및 다음 전략

## 최종 판정

**PARTIAL — 6,144게임 소비 한도는 준수했으나 최초 4게임의 결과가 소실됐다.**

**REVISED TRAINING STRATEGY REQUIRED. Stage 2는 시작하지 않는다.**

추가 PPO/Adam update, checkpoint 재선정, architecture/loss/reward 변경, production promotion, sealed final/rare 사용은 **0**이다. 기존 Stage 1 endpoint와 원본 V4만 비교했다.

핵심 결론은 **“sampling으로 개선된 정책이 argmax 때문에 약해 보인다”는 주요 설명을 지지하지 않는다**는 것이다. Fresh validation의 interaction은 -0.49∼-0.10pp, 보수적 95% 구간은 [-5.47,+4.98]pp다. 다만 양 실행 방식 모두 V4보다 강하다는 증거도, 양 방식 모두 일반화에 실패한다는 증거도 확정하지 못했다. 후보는 validation에서 두 방식 모두 약 +3pp 우세한 점추정이지만 구간에 0이 포함된다. 이 차이를 구분해야 한다.

권고는 **argmax deployment를 유지하는 deterministic-performance-gated PPO v2**, 그 다음 학습에서 바꿀 단일 축은 TRAIN team coverage 256→기존 native TRAIN 전체 4,096팀이다. 이것은 확인된 curriculum 원인에 대한 치료라고 주장하는 것이 아니라, 실행-mode 가설의 지지가 약해진 뒤 선택한 일반화/강건성 가설이다. 보상·PPO hyperparameter·architecture·상대 혼합을 함께 바꾸지 않는다. 새 캠페인은 T1 승인 전 실행 금지다.

## 1. 동결 신원과 범위

- Baseline/시작 HEAD·tracking·live origin: `05d8c33190d467d85265358c3ea0cf788d7ac687`.
- Branch: `codex/showdown-mc-integration-v1`, origin `https://github.com/josun1392/my_pochamps_advisor.git`.
- Foundation: `showdown-combat-foundation-v1`, V5 strategic-v3 public encoder, 28,822 float32, 674,939 parameters. Native 35-action masking 그대로다.
- Native engine: `942cda71d14bf0618bd57991708a2e2734b6daba`, `gen9championsbssregmc` singles.
- 후보: Stage 1 endpoint SHA `9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf`, Adam clock 32,768.
- V4 control/S0: `acb98005c664bd9f272d9a35871b0a60d618af37b64213da44960c4ad884aa2a`, Adam clock 65,536.
- Anchor: `2774c54cca1340f131362e3a7da7aec47c861a972439aa5cead22666eb8c3fa2`, Adam clock 65,536.
- S0와 control은 ZIP은 같지만 별도 policy instance다. Control만 sampling할 때 rival까지 sampling되는 alias 오류를 방지했다. 두 rival는 전 연구에서 argmax 고정이다.
- 원래 plan SHA: `10eb88f1b0f8bc1b47126fd350783b33bf11b5641486168ce68cf96b5544d57e`.
- 공개된 운영 수리 plan SHA: `de63b64742b52bca02607cba379c6c8ee09405b8af1980920d0afa88a1f3fe5e`.
- 양 plan은 256 case, 모델, RNG, 통계 기준, 한도와 32 chunk를 공유한다. 수리본은 실행 wrapper source 하나와 4개 소실 결과의 소비 처리만 명시적으로 변경했다. 원본 source/plan/실패 journal은 보존했다. 완전한 원래 사전등록 연구로 소급 포장하지 않는다.

후보 절대 경로:

`C:\Users\jsp33\.codex\artifacts\pokeadvice-combat-foundation-v1-long-training\seed95017-stage1\experiment_00\checkpoint_0028_ppo_1048576_4e3232dd\model.zip`

원본 V4 절대 경로:

`C:\Users\jsp33\.codex\artifacts\selfplay-v1-scale-v4-bounded-v1-20261015\main\generation_01\experiment_00\checkpoint_0016_ppo_2097152_a4f58bce\model.zip`

## 2. 사례, RNG와 사전 선언 통계

최초 결과 관측 전에 TRAIN128 + validation128의 실제 scenario/seed/preview/team SHA를 동결했다. TRAIN은 원래 SHA-bound 256팀 subset의 train namespace, validation은 유지된 V8 validation split이다. 시작 index는 각각 99241000/99242000이다. 과거 TRAIN 및 소비된 평가에서 82,729개 native payload identity를 제외했다. Identity는 scenario 이름만이 아니라 양 팀 hash, ordered preview, native seed로도 확인했다. 신규 256 case 사이에도 같은 payload가 없다.

고유 own/opponent 팀 수는 TRAIN 104/107, validation 113/114다. 즉 128개의 새 case를 128개의 이전에 전혀 보지 못한 팀이라고 부르지 않는다. TRAIN과 validation의 완전한 팀/joint moveset 분리 계약을 유지하며 species-unseen 또는 대회 최적화 metagame 팀 표본이라는 주장은 하지 않는다. 예약 final/rare offset 98171000을 생성·소비하지 않았다.

설계는 256 case × 두 좌석 × S0/anchor × 후보/V4 × (argmax + sampling stream 2) = **6,144개 slot**이다. Own-team-preserving native-seat 계약을 사용했다. Sampling seed는 scope/case/seat/rival/stream의 SHA256이고 policy 이름은 포함하지 않아 후보·control이 common uniform sequence를 공유한다. Native PRNG seed는 모든 실행 방식에서 동일한 case seed다. Episode UUID를 RNG seed로 쓰지 않았다. Forced/wait를 포함한 request별 draw 순서도 고정했다.

Sampling은 원래 masked 확률 그대로이며 temperature/top-k/추가 탐색 tuning은 없다. NaN/음수/비정규화/illegal mass를 거부하고 누적확률의 rounding tail도 마지막 positive action에서 1로 고정한다. Actor/critic에 case identity, rival 이름, native seed, private request를 feature로 전달하지 않는다. Coordinator의 상대 public request는 legality/audit 전용이다.

Primary는 validation의 `(후보−V4)_sampling − (후보−V4)_argmax`다. Sampling 두 stream은 먼저 평균하며 두 학습 seed로 취급하지 않는다. 좌석·rival·stream 전체를 case cluster 안에 유지하고 128 cluster를 20,000회 bootstrap한다. Seed는 2026101703이다. Argmax 4개 observation/case와 sampling 8개의 단순 전체 합산으로 mode에 다른 weight를 주지 않는다.

점수는 기존 제안과 같은 strict native-win indicator다. Draw는 별도 보고하며 native 256-decision cap을 고정했다. Censor가 있으면 full-readiness gate를 통과할 수 없고 chunk truncation >1%는 운영 STOP이다. 실제 저장된 6,140전은 모두 정상 종료·무승부 0·truncation 0이므로 이 부분에서는 ±1 terminal return과 win 차이가 단순 선형 관계다. 소실된 4전의 draw/truncation/retry 여부는 모른다.

사전 gate:

1. Primary interaction 95% 하한 >0.
2. Interaction 점추정 ≥5pp. 이는 실제 효과가 최소 5pp임을 신뢰하한으로 입증하는 조건과 다르다.
3. Sampling−V4의 validation 95% 하한 >-5pp.
4. Validation anchor sampling−V4의 동시 하한 >-5pp.
5. Argmax anchor도 별도로 같은 기준을 보고한다. 두 anchor mode 비교를 family로 하여 각각 양측 97.5% 구간을 사용한다(Bonferroni, 근사 bootstrap coverage).

Sampling superiority는 별도 95% 하한 >0으로 구분한다. Positive interaction만으로 후보 우월성을 선언하지 않는다. TRAIN·rival·seat별 결과는 보조 분석이며 primary를 대체하지 않는다.

## 3. 이번 작업에서 발생한 결과 포장 결함과 처리

**이 결함은 이번에 작성한 study runner의 결함이며 기존 Foundation/PPO 결함이 아니다.** 최초 runner가 maintained evaluator에 `identity` 없는 lambda case provider를 넘겼다. Evaluator는 각 native battle을 종료·close한 뒤 마지막 결과 포장에서 `case_provider.identity`를 읽는다. 네 worker가 첫 게임을 마친 후 같은 `AttributeError`로 실패했다. 결과가 메모리에서 반환되지 않아 네 outcome을 저장하지 못했다.

실패 slot은 TRAIN 99241000/99241008 및 validation 99242000/99242008의 **후보 argmax, p1, S0**다. 네 journal에 `game_started`와 해당 packaging error가 있고 완료 결과 파일은 없다. 결과를 모르는 상태에서 오류를 확인했고 승률을 기준으로 수리·표본 선택하지 않았다.

조치:

- 네 native game을 이미 소비된 것으로 계수하고 **재실행하지 않았다**. 결과를 패/승/무승부로 채우지 않았다.
- Identity를 제공하는 immutable provider를 구현하고 split/index retarget을 차단했다.
- Native result의 progress callback에서 summary 포장 **이전**에 fsync/atomic-rename된 game receipt를 저장하도록 수리했다. 포장 오류 fault injection에서도 결과가 남는지 검증했다.
- 원본 plan, source bytes, failed run/STOP/state/journal을 남겼다. 새로운 source SHA를 명시한 `plan_operational_repair_v1.json`과 별도 run namespace로만 재개했다. 과거 학습 캠페인을 다른 source로 resume하지 않았다.
- 원래 시작 시각과 1시간 deadline을 유지하고 나머지 **6,140게임만** 실행했다. 모델·case·통계 규칙은 바꾸지 않았다.

따라서 연구의 완전한 outcome grid는 **PARTIAL**이다. Runner state의 `complete=6144`는 모든 slot에 관측 또는 administrative-unknown disposition이 있다는 뜻이며, 6,144개 관측 outcome이 있다는 뜻이 아니다. 실제 소비 6,144개, 알려진 정상 종료 6,140개, 소실 outcome 4개다. 정상 종료 총수의 엄밀한 범위는 6,140∼6,144이며 unknown을 정상 종료라고 가정하지 않는다.

## 4. 누락 결과에 대한 보수적 분석

원래 완전-data estimator를 네 unknown strict-win indicator의 **모든 16개 가능한 0/1 조합**에 적용했다. 같은 bootstrap draw로 각 조합의 구간을 계산한 뒤 하한의 최솟값·상한의 최댓값을 envelope로 보고한다. 이는 관측값 대입이 아니며 사고 이후의 sensitivity analysis임을 명시한다. Source에 동결된 원래 통계 estimator 자체는 바꾸지 않았다.

각 partition에 후보 argmax 2개만 빠져 있어 aggregate argmax 차이와 interaction의 identified range 폭은 최대 **0.390625pp**다. Sampling 전체와 anchor 전체는 완전 관측이다. 어떤 네 승패가 실제였더라도 primary positive/practical gate는 통과하지 않는다. 따라서 아래의 실패 판정은 소실 4게임을 불리하게 가정했기 때문에 만들어진 것이 아니다. 다만 unknown의 native censor/retry 여부까지 복원한 것은 아니므로 full-integrity GO는 별도로 불가하다.

## 5. Argmax와 sampling의 실제 성적

`+?2`는 outcome 미상 2개이며 승수에 포함하지 않았다. 분모 512는 계획 slot 수다.

| 분포 | 실행 | Foundation 후보 | V4 control | 후보−V4 점추정 범위 | Case-cluster 95% / envelope |
|---|---|---|---|---:|---|
| TRAIN | argmax | 262승 +?2 / 512 | 268/512 | -1.17∼-0.78pp | [-6.05,+3.91]pp |
| TRAIN | sampling 합계 | 514/1,024 | 502/1,024 | +1.17pp | [-2.73,+4.98]pp |
| validation | argmax | 309승 +?2 / 512 | 292/512 | +3.32∼+3.71pp | [-2.54,+9.38]pp |
| validation | sampling 합계 | 602/1,024 | 569/1,024 | +3.22pp | [-0.88,+7.32]pp |

TRAIN sampling stream별 후보/V4는 254/252, 260/250으로 각 정책 512전이다. Validation은 302/283, 300/286이다. 이를 별개의 학습 seed 복제 성공으로 부르지 않는다.

| Primary interaction | 점추정 범위 | 95% envelope | 해석 |
|---|---:|---|---|
| TRAIN, 보조 | +1.95∼+2.34pp | [-2.25,+6.54]pp | 작은 양의 점추정이나 확증 없음 |
| validation, primary | **-0.49∼-0.10pp** | **[-5.47,+4.98]pp** | Sampling의 실질적 상대 이점 미입증 |

Validation upper 4.98pp는 5pp에 매우 가깝다. 이 Monte Carlo bootstrap 경계 차이를 이용해 “5pp 효과가 수학적으로 불가능” 또는 “두 mode가 동등”하다고 선언하지 않는다. Primary 하한이 0을 넘지 않고 점추정도 practical margin에 못 미친다는 사전 판정만 명확하다. 추가 bootstrap seed/표본/게임을 반복해 유의성을 만들지 않았다.

후보 자체 validation 승률은 argmax 60.35∼60.74%, sampling 58.79%다. V4는 57.03%→55.57%다. 즉 sampling이 후보 자신의 성적을 올린 점추정도 아니다. TRAIN에서도 후보는 51.17∼51.56%→50.20%, V4는 52.34%→49.02%다. TRAIN의 양의 interaction은 후보의 절대 향상보다 V4의 더 큰 sampling 하락과 연결된다. 이 within-policy 비교는 보조적 기술 통계이며 별도 superiority 검정으로 선택하지 않았다.

## 6. 상대별·좌석별 결과와 anchor guard

| Validation 상대 | Argmax 후보/V4 | Argmax 차이, 95% | Sampling 후보/V4 | Sampling 차이, 95% |
|---|---|---|---|---|
| S0 | 145승+?2 /146, 각256 slot | -0.39∼+0.39pp, [-6.64,+6.25] | 289/278, 각512전 | +2.15pp, [-2.34,+6.84] |
| anchor | 164/146, 각256전 | +7.03pp, [-0.78,+15.23] | 313/291, 각512전 | +4.30pp, [-0.98,+9.57] |

Validation anchor의 사전 family-wise guard:

- Argmax−V4 97.5% 구간 **[-1.95,+16.41]pp**, 하한 >-5pp: **PASS**.
- Sampling−V4 97.5% 구간 **[-1.76,+10.35]pp**, 하한 >-5pp: **PASS**.
- 두 비교의 표본은 완전 관측이다. 이 guard 통과는 5pp 초과 severe-regression을 막는 비열등성 조건이지 +5pp 우월성 증명이 아니다.

TRAIN에서는 S0 argmax -5.47∼-4.69pp / sampling -2.93pp, anchor argmax +3.13pp / sampling +5.27pp다. Training mode마다 더 잘 맞는 rival가 다르며 하나의 평균만으로 universal strength를 주장하지 않는다.

양 native 좌석을 유지했다. Validation sampling 후보는 p1/p2 각각 301/512, V4는 293/512·276/512다. Argmax 후보는 p1 153승+?2/256, p2 156/256, V4는 148/256·144/256이다. 좌석별 variation을 숨기지 않지만 사후 가장 좋은 좌석으로 결론을 교체하지 않는다. 원래 bootstrap은 양 좌석을 같은 case cluster 안에 묶었다.

과거 Stage 1의 다른 64-case final panel에서 anchor -13.28pp였던 사실을 취소하지 않는다. 같은 immutable endpoint의 새 128-case panel에서는 반대 방향의 점추정이다. 이는 panel/case 이질성과 불확실성이 중요하다는 증거다. 새 panel을 골라 과거 regression이 없었다거나 모델을 승격해도 된다고 주장할 수 없다.

## 7. 질문에 대한 답과 실행 정책 선택

1. **Stochastic policy가 일반화되는데 argmax가 그 이득을 잃는가?** 이번 primary가 이를 지지하지 않는다. Validation에서 두 방식의 후보−V4 차이가 거의 같다. 이전 16-case 보조 진단의 큰 TRAIN interaction이 새 128-case에서 재현됐다고 할 수 없다.
2. **Foundation가 일반화에 실패한다고 확정했는가?** 아니다. Validation은 두 mode 모두 약 +3pp 점추정이지만 superiority CI가 0을 포함한다. TRAIN보다 validation이 더 나쁜 일관된 패턴도 이번 데이터에는 없다. “일반화 실패 확정” 대신 **안정적 경쟁력 개선 미입증·case/rival 이질성**으로 기술한다.
3. **Sampling은 비열등한가?** 이 validation에서 aggregate 95% 하한 -0.88pp 및 multiplicity-aware anchor guard는 -5pp 기준을 통과한다. 이는 sampling이 더 강하다는 것과 다르다. Sampling superiority 하한 >0은 실패했다.
4. **Competitive AI에 full-distribution sampling을 채택하는가?** 지금은 **아니다**. 두 rival가 deterministic인 제한된 benchmark이고 adaptive human/다양한 상대에 대한 mixed-strategy exploitation 검증이 아니다. Partial-information 게임에서 randomization 자체는 가능하지만 이번 성적이 그 채택 근거가 되지 못한다. Native inference의 argmax 계약과 production은 유지한다.

Non-wait 상태에서 sampling이 원래 argmax와 다른 행동을 고른 비율은 validation 후보 **19.36%**, V4 **20.10%**다. 더 많은 행동 변경이 더 좋은 행동 선택이라는 뜻이 아니다. Validation 평균 policy entropy는 후보 argmax 방문 상태 .5122 / sampling 방문 상태 .4859, V4 .5224/.4929다. 모델을 학습하지 않았으므로 이 차이는 state visitation 차이이며 parameter collapse가 아니다. Switch/회복/방어의 raw count와 opportunity는 `analysis.json`/`supplement.json`에 보존했다. Sampling은 게임 수가 두 배라 raw count를 그대로 비교하지 않는다.

## 8. 독립적으로 선택한 단일 다음 전략

**Argmax 유지 + deterministic-performance-gated PPO v2, 단일 학습 변경은 native TRAIN team coverage 확대(256→4,096).** 별도 제안 계약은 `combat_training_strategy_v2_PROPOSED.json`이다. 승인된 transition은 0이며 trainer가 바로 실행할 수 있는 config가 아니다.

- 고정 Stage 1 endpoint/Adam을 명시적 parent로 유지한다. 결과를 보고 다른 checkpoint로 교체하지 않는다. Source/config가 새로 동결되는 별도 run namespace이며 historical campaign resume가 아니다.
- Architecture, public encoder/priors, terminal ±1 reward, gamma/GAE, PPO LR/epochs/clipping/entropy/regularizer/auxiliary 및 기존 10-slot opponent mixture는 유지한다.
- 학습 분포만 기존 native V8 TRAIN 전체 4,096팀으로 넓힌다. Metagame 최적 팀이라고 새로 이름 붙이지 않고 기존 priors가 256-team 출처라는 사실도 유지한다. Preview subsystem/selection protocol은 바꾸지 않는다.
- 변경 전 public encoder support, unknown/out-of-support 분포, legality와 resource coverage를 점검한다. 이 검사를 통과시키려고 architecture/priors/loss를 함께 바꾸지 않는다. 통과하지 못하면 새 학습을 막는다.
- Intended deployment는 masked argmax다. Stochastic rollout은 PPO 학습용이며 **argmax-return의 정확한 gradient를 최적화한다고 부르지 않는다**. 같은 terminal-return PPO surrogate를 유지하되 모델 선택·성공 판정은 실제 executable argmax의 paired native 성적에 걸린다.
- 사전 endpoint만 후보로 인정하고 반복 작은 패널의 최대값을 고르지 않는다. V4와 고정 Stage 1 parent를 함께 control로 두고, 새 validation manifest/좌석/상대별 uncertainty와 anchor regression guard를 사전 선언한다. 이번 모든 case는 소비됐으며 untouched 평가로 재사용하지 않는다.
- Sampling/auxiliary accuracy만 좋아지고 argmax 성적이 좋아지지 않으면 성공으로 세지 않는다. 이유 없이 LR/보상/head/상대를 잇달아 바꾸거나 예산을 연장하지 않는다.

이 선택은 “일반화 실패를 입증했으므로 curriculum을 고치면 해결된다”는 인과 결론이 아니다. Execution-switch나 architecture 교체의 근거가 약하고, 고정 256팀에서 얻은 작은·이질적 효과를 더 넓은 target distribution에서 검증하는 것이 다음 투자 목적에 맞는 **검증 가능한 단일 변화**라는 판단이다. 그냥 같은 설정에 더 많은 transition을 주자는 A와 구분한다. 넓은 curriculum의 우월성, 추가 PPO의 이득, proposed source의 성능은 아직 입증되지 않았다.

추가 6,144-game 진단이나 missing 4게임 재실행을 요청·자동 실행하지 않는다. T1은 이 새 전략을 승인/거절하거나 compute를 배분해야 하며 이번 결정만으로 어떤 학습도 시작되지 않는다.

## 9. 운영 검증, 자원과 시간

- Operations-v2 `TrainingJournal`과 `RetryMonitor`를 재사용했다. Game-start를 먼저 기록하고 각 결과를 fsync/atomic receipt로 게시한다. Chunk는 8 case/192 slot이며 32개다. Partial tail/sequence corruption과 uncertain-start/no-result는 silent replay가 아니라 fail closed다.
- 최초 4개 uncertain consumption은 별도 수리 manifest가 명시적으로 승계했고 결과를 발명하지 않았다. Source fingerprint 52개를 worker 시작마다, 모델 SHA를 chunk 끝마다 확인했다. Original learning-source 42개는 그대로다.
- 768소비/764known 경계에서 정상 중단했다. 승률을 읽어 선택하지 않고 같은 repaired plan으로 나머지 slot만 resume했다. Plan SHA·committed game SHA를 검증하고 STOP을 자동 삭제하지 않는다.
- 원래 첫 실행 07:38:31 UTC부터 native study 종료 **08:01:08 UTC**까지 **1,356.88초(22분36.88초)**다. 최초 실패·수리·정상 pause 시간이 포함되며 1시간 이하다.
- 수리된 두 실행의 measured wall 합계 **1,087.92초**, 알려진 6,140전 기준 **5.64 games/s**다. Job tree CPU 4,649.98초이며 16 logical CPU 기준 평균 **26.71%**, measured peak memory **5.66GiB**다. 초기 실패 phase의 종료 CPU/memory 표본은 남지 않아 합산하지 않았다.
- Hard Job cap은 CPU50%/12GiB, 병렬 evaluation worker 4개/Torch1 thread/CPU inference다. Coordinator 1개와 최대 4개의 native Node worker가 별도로 존재하므로 총 OS process 수가 4라는 뜻은 아니다. Active-process ceiling은24다. CUDA/JAX/simulator 교체는 없다.
- Known game decision 길이는 min5/median14/p90 20/p99 32/max75다. Known retry0, truncation0, draw0, mask/nonfinite 오류0이다. Unknown 네 게임의 retry/censor 수는 0이라고 보고하지 않는다. 최초 포장 오류는 별도 실행 실패로 남겼다.
- 측정된 완료 phase와 chunk의 외부 network 시도는0이고 loopback-only guard를 사용했다. 실제 provider 호출은 없다. 원격 신원 확인/허용 Git push 외 network experiment는 하지 않았다.
- 이번 작업 전체 경과와 최종 commit/원격 hash는 외부 상세 보고서의 마지막 부록에 기록한다.

## 10. 회귀, 변경 파일과 보존

Focused regression **29 passed, 3.02초**다. 신규 test 13개와 기존 operations14개, Foundation GAE/config 2개다. PPO optimization 및 추가 native battle을 실행하는 test는 포함하지 않았다. Probability/rounding/illegal mass, common RNG, record corruption/immutability, cluster weighting/dependence, incomplete/duplicate/censor gate, provider identity, 포장 fault 이후 receipt 보존, uncertain game 재실행 차단, 동일 ZIP의 control/rival instance 분리를 검증했다. Operations의 exact rollout STOP accounting/partial journal/legacy resume 회귀도 통과했다.

Owned 변경은 신규 `advisor/learned_execution_alignment.py`, `scripts/evaluate_combat_execution_alignment.py`, `tests/test_execution_alignment.py`, 이 보고서 및 미래 전략 제안 JSON뿐이다. Model/encoder/loss/기존 trainer/operations-v2 source는 수정하지 않았다. 외부 사례·게임·optimizer·large artifacts는 Git 밖에 둔다. Exact staging과 normal push만 사용한다.

원래 Stage 1/사후 분석의 모든 결과와 source snapshot, checkpoint/Adam, V4/V5, B0, Preview/JAX/production, primary master의 선행 변경을 보존한다. 보호 파일 raw 내용은 출력하지 않고 SHA/status만 확인한다. 최종 재검증·Git closure는 별도 JSON으로 남긴다.

외부 산출물 루트:

`C:\Users\jsp33\Documents\Codex\2026-10-17\task-pokeadvice-combat-pre-long-training\outputs\execution_policy_alignment`

- `plan.json`, `plan_operational_repair_v1.json`: 사전 사례/통계 및 명시적 운영 수리.
- `source_before_repair/`, `run/operations/`, `run/chunks/`: 최초 실패 증거. 수정·삭제하지 않았다.
- `run_operational_repair_v1/chunks/*/game_*.json`, `COMMITTED.json`, `operations/`: 6,140관측 +4 unknown disposition, SHA 및 resume 이력.
- `pause_0768.json`, `launch_*.log`: 실제 소비 경계·실패·정상 resume.
- `analysis.json`: 원래 estimator의 16개 exhaustive missing-result sensitivity와 모든 범위/CI/gate.
- `performance_table.csv`, `supplement.json`, `execution_alignment.png`: stream·상대·좌석·행동·자원 보조 자료.
- `regression.json`, `regression.xml`, `regression.log`: 실제 test 결과.
- `REPORT_KO.md`, `preservation_before.json`, `preservation_after.json`, `git_closure.json`, `artifact_manifest.json`: 최종 상세 handoff와 불변성 증거.

**최종: PARTIAL(4개 outcome 소실을 공개). 실행-mode 설명의 practical/positive gate는 모든 누락 승패 가능성에서 실패한다. REVISED TRAINING STRATEGY REQUIRED — 추가 학습·모델 승격 없이 T1 결정을 기다린다.**

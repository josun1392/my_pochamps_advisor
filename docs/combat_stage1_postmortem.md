# Combat Foundation Stage 1 사후 분석 및 Stage 2 결정

## 판정

**사후 분석·소유 인프라 결함 수리: COMPLETE. Stage 2: NO-GO. 다음 방향: B.**

선택은 **기존 combat architecture를 유지하면서, 확장 전에 학습 목표와 실행 정책의 정합성을 먼저 검증·고정하는 차기 training-strategy 계약 개발**이다. 현 설정의 단순 연장(A)이나 예측 모듈 제거/대형화(C)를 지금 승인할 증거는 부족하다. 승률 신뢰구간에 0이 포함된다는 이유만으로 이 결정을 내리지 않았다. Anchor 상대의 반복적 열세, TRAIN/validation 차이, stochastic/argmax 차이, 예측의 약한 실제 action 영향력, 정상 optimizer 진행을 함께 근거로 삼았다.

이 작업에서 PPO/Adam update는 **0**이다. Stage 2, 추가 학습, production 교체, checkpoint 승격, CUDA 전환, sealed final/rare panel 사용은 하지 않았다. 512개 실행 방식 진단과 32개 과거 사례 재현은 고정된 기존 모델의 native inference만 실행했다. Foundation v1의 actor/critic/encoder/loss/reward/35-action schema와 역사적 실험 결과는 수정하지 않았다.

## 조사 범위와 신원

- 시작 baseline: `81ad4ffed1e702d118b181f27a17feed89622e6d`. 실제 학습 source: `f16d0a1c1c7ea159c2c7c81c2d79e14e28a94b09`.
- 작업 branch: `codex/showdown-mc-integration-v1`, 원격: `https://github.com/josun1392/my_pochamps_advisor.git`. 시작 HEAD/tracking/live origin 일치를 확인했다.
- Native Showdown: `942cda71d14bf0618bd57991708a2e2734b6daba`, `gen9championsbssregmc`. Singles, native legal mask 권한을 유지했다.
- Foundation: `showdown-combat-foundation-v1`, public V5 strategic-v3, 28,822 float32, 674,939 parameters. Feature fingerprint: `5bddd957099b951637732c35e1869d66aa3b70cd8343b1f7ede208729201343e`.
- PPO: 4 workers × 128, rollout 512, batch 128, 4 epochs, LR `5e-5`, gamma 1, GAE .95, clip .2, value .5, target KL .03, gradient cap .5. Entropy .01, legal-uniform reverse KL .001, proper auxiliary loss .02.
- TRAIN subset 256팀 SHA: `90283f3fe31b1b02eb61465aeeeebb243bbc302bc9c29d3445292a02558c469c`.
- 원본 config SHA: `76699f638cdb181112c3fb9243e5c6e5bc5a3fa79a78fc2d6135a11f5e4f3bc9`; frozen fingerprint: `39b63808e77cdd55b1dd96f2e719628cc8ce5fd20a85f1ac33b8d14bfaf27599`.
- B0 SHA: `8f1a8b949ca7f8f52c4ecc1bb4b89f9b0999a6eb4a578f8f71b5a6ddda386dee`. Fresh Adam 0인 V4 transfer이며 smoke endpoint가 아니다.
- V4 control/S0 SHA: `acb98005c664bd9f272d9a35871b0a60d618af37b64213da44960c4ad884aa2a`.
- Frozen anchor SHA: `2774c54cca1340f131362e3a7da7aec47c861a972439aa5cead22666eb8c3fa2`.
- Endpoint SHA: `9b3eb94aabea1fb25e75dfdba0b733c2a9acd45434ae368a86e14d8979950ccf`.
- Legacy previous SHA: `986ea2ba562d0b34df50ec2ca88ae3171e37031f6f358e9aa5813ffe01412641`; historical SHA: `fe52cd3b4e288c242176a6574769bdf1cd8fb5dbedad8b015496cb5b5dcfd57d`. 폴더명 v4와 categorical V4를 혼동하지 않았다.

기존 REPORT, frozen LONG_TRAINING_PLAN, 모든 32 PPO checkpoint 및 B0의 manifest/episode/profile, 29 반복 진단, 두 milestone와 TRAIN probe의 모든 기록, 6 launch/중단/복구/monitoring/incident 기록, learning CSV를 읽었다. Stage 1 manifest 122개 파일과 33 ZIP SHA를 대조했다. Stage 1 아래 JSON/JSONL/CSV 88개 파일은 전체 파싱 기록도 남겼다. 초기 frozen source 41개 일치와 외부 보존 모델 목록도 대조했다.

## 1. 실제 학습과 학습 곡선

Durable trained/collected는 각각 **1,048,576**이다. 32 × 32,768 transition, 2,048 complete rollout/update, Adam 32,768이다. 각 interval의 64 update profile과 1,024 optimizer step이 일치한다. 33 ZIP의 parameter와 Adam tensor를 다시 열어 finite 여부와 실제 step clock을 확인했다. 마지막 Adam의 39 parameter state가 모두 32,768이며 LR은 고정값이다. 40개 state-dict tensor 중 학습 가능한 39개 parameter tensor가 B0 대비 변경되었다. 미학습·Adam reset·조기 KL 중단 때문에 전체 예산이 허수였다는 증거는 없다.

Native TRAIN 종료는 **82,569전: 43,466승 / 39,103패**, draw/truncation 0이다. 종료 episode의 joint native decision은 1,181,824개다. 이는 PPO actor row 1,048,576과 다른 계수다. Native wait 자동 진행과 양측 요청/재시도가 있으므로 둘을 서로 대체하지 않았다.

| 상대 | 첫 262k TRAIN 승률 | 마지막 262k TRAIN 승률 | 해석 |
|---|---:|---:|---|
| anchor | 50.42% | 52.66% | 작은 in-distribution 증가, heldout anchor 열세와 대조 |
| S0/V4 | 48.94% | 49.70% | 보편적 V4 극복의 증거 없음 |
| tactical | 49.64% | 47.80% | 증가하지 않음 |
| champions | 46.82% | 49.13% | 소폭 증가 |
| previous | 52.80% | 55.76% | 소폭 증가 |
| historical | 55.24% | 53.48% | 증가하지 않음 |
| max_power | 68.45% | 70.20% | 쉬운 상대에 작은 증가 |

이 표는 바뀌는 팀/seed와 stochastic learner의 관측 통계이지 checkpoint 간 matched 인과 비교가 아니다. Episode가 checkpoint를 걸치므로 attribution도 interval endpoint 결박이다. 다만 전체 collapse나 모든 상대에서 동반 붕괴했다는 설명과는 맞지 않는다.

반복 64-game 진단은 B0 45승, 65,536에서 최고 48승, endpoint 45승이다. 29회/1,856게임의 반복 패널은 독립 일반화 검정이 아니다. 네 STOP checkpoint에는 해당 진단이 없으며 이를 0승으로 채우지 않았다. 최고인 65k를 champion으로 고르면 selection bias가 생긴다. 32개 checkpoint의 수치와 SHA/경로는 외부 `all_checkpoint_records.json`, `statistics_and_integrity.json` 및 보고서 부록에 보존했다.

## 2. 평가 비교 가능성: V4 control이 왜 248승에서 291승인가

| Milestone | offset | 후보 | V4 control | paired 차이 | 64-case cluster bootstrap 95% |
|---|---:|---:|---:|---:|---|
| 262,144 | 97171000 | 254/512 | 248/512 | +1.17pp | [-6.64, +8.59]pp |
| 1,048,576 | 97172000 | 283/512 | 291/512 | -1.56pp | [-8.59, +5.47]pp |

두 milestone는 계획대로 **새 offset**을 사용했다. 완전히 동일한 canonical scenario와 native seed의 교집합은 각각 **0**이다. 64팀 표본에서 own/opponent complete-team hash는 각각 9개가 겹치지만 selection order, 상대 조합, native seed까지 같은 case는 아니다. V4 control SHA, 두 frozen learned rival SHA와 좌석 계약은 양 시점에서 같다. Control이 학습되거나 rival가 hot-swap된 현상이 아니다.

Learned policy는 masked **argmax**다. Public heuristic baseline은 `case_index+919`로 seed되며 native engine의 PRNG는 scenario seed다. 즉 모든 평가가 무작위 정책 샘플링을 한 것도, 모든 환경 확률이 제거된 것도 아니다. 서로 다른 deterministic case 모음에서 같은 V4가 다른 승수를 갖는 것은 정상이다. +43승을 V4 변화나 후보의 시간적 개선 기준으로 해석할 수 없다. 각 시점의 **matched candidate-control 차이**만 해당 panel 안에서 비교해야 한다. Early 후보 ZIP은 `e341ba4019363c23f879ed68525474e0599894760a105ed308273a90672b4eaf`로 final과 다르다.

양 좌석은 own-team-preserving native-seat 계약이다. 256 case×rival 그룹 중 양 좌석 winner가 달랐던 그룹은 early 후보/대조 모두 0, final 후보 3·대조 7이다. 거의 같은 두 좌석을 512개 독립 표본처럼 계산하면 과신한다. Bootstrap은 case 단위로 좌석·rival를 묶는다. Native seat order에 따른 tie/RNG 영향은 허용되며 이를 감추지 않았다.

## 3. 상대별 퇴행과 전술 재현

| 상대 | Early 후보/대조, 각 128전 | Final 후보/대조 | Final 차이 | Final case-cluster 95% |
|---|---:|---:|---:|---|
| tactical | 60 / 56 | 73 / 72 | +0.78pp | 약 [-9.38, +10.16]pp |
| champions | 70 / 64 | 73 / 65 | +6.25pp | [-1.56, +15.63]pp |
| S0 | 66 / 58 | 73 / 73 | 0pp | 약 [-10.94, +10.16]pp |
| anchor | 58 / 70 | 64 / 81 | **-13.28pp** | **[-22.66, -3.91]pp** |

상대별 구간은 이번 전체 기록 재분석의 seed-fixed 10,000회 bootstrap이다. 기존 보고서 2,000회 계산과 미세한 quantile 차이는 historical 결과 변경이 아니라 별도 추정이다. Aggregate 표는 기존 2,000회 값을 유지했다.

Anchor final 128 paired seat-case에서 둘 다 승리 61, 둘 다 패배 44, V4만 승리 20, 후보만 승리 3이다. 차이가 있는 독립 case cluster는 13개다. Whole-case sign-flip의 양측 exact p는 .01171875이며 **최종 네 rival만** family로 한정한 Bonferroni 값은 .046875다. Early anchor는 -9.375pp, 95% 약 [-20.31,+1.56]pp였다. 퇴행 방향은 final에서 갑자기 처음 생긴 것이 아니다.

이는 무시할 수 없는 진단 신호지만, 모든 checkpoint·milestone·전술 사후 탐색까지 보정한 확증 검정은 아니다. 학습 seed는 95017 하나뿐이고 case bootstrap은 training-seed 불확실성을 포함하지 않는다. Anchor만의 승률로 전체 경쟁력이나 원인을 단정하지 않는다.

소비된 final panel에서 처음 네 regression case, 처음 두 improvement case, 처음 두 same-outcome case를 미리 지정해 8 case × 2 seats × 후보/대조 = **32 native 재현**을 수행했다. Winner, return, truncation, decision 수, action family 수, 실제 move count, retry 수가 **32/32 과거 기록과 정확히 일치**했다. 결과 선택 표본이므로 이 32전의 승률을 새로운 strength estimate로 쓰지 않는다.

첫 동일 public state의 action divergence 예시는 다음과 같다.

| Case | 분류 | 첫 divergence | 후보 vs V4 |
|---|---|---|---|
| 97172000 | regression | T2 Talonflame HP 122/163 | Roost vs Brave Bird |
| 97172004 | regression | T1 Metagross HP 187/187 | switch 2 vs Shadow Claw + Mega |
| 97172014 | regression | T1 Scolipede HP 139/139 | Dig vs Iron Tail |
| 97172022 | regression | T6 Pidgeot HP 123/165 | switch 3 vs Hyper Beam |
| 97172006 | improvement | T1 Charizard HP 163/163 | switch 2 vs Hurricane |
| 97172021 | improvement | T4 Toxicroak HP 124/165 | Dynamic Punch vs Icy Wind |

Tempo/회복 timing, switch commit, two-turn/공격 선택은 타당한 조사 분류다. 그러나 Roost 시 HP는 full이 아니고, switch가 improvement 사례에도 있다. Type prior가 유리하다고 최적 공격이라는 뜻도 아니다. Divergence 후 상태는 서로 달라지므로 이후 행동을 직접 paired 비교하거나 패배 원인을 첫 행동 하나로 확정하지 않았다. Conditional damage나 hypothetical rank를 optimal label로 삼지 않았다. 팀들은 native-legal 생성 분포이며 대회 최적화된 metagame team 표본이라는 주장도 하지 않는다.

## 4. PPO, value, gradient, 행동의 상태

| 기록 지표 | 32 interval 범위 | 마지막 |
|---|---:|---:|
| Non-wait pre-update true entropy, interval 평균 | .40292–.53370 nats | .43874 |
| Approx KL, interval 마지막 update | .00206–.00683 | .00253 |
| PPO probability clip fraction, 마지막 update | .00586–.03467 | .00879 |
| Value loss, 마지막 update | .17314–.46532 | .35689 |
| Explained variance, 마지막 update | .20207–.76558 | .47899 |
| Raw gradient 최대, 각 interval 모든 update | 2.586–3.672 | 3.030 |
| Gradient clipping fraction, 마지막 update | 모두 1.0 | 1.0 |

보존된 profile 기준 raw norm 전체 최대는 3.67249, clipped 최대는 .500001256으로 guard tolerance `.50001` 이하다. NaN/Inf, Adam clock 불연속, KL emergency, value divergence의 증거가 없다. Entropy collapse 기준 .05 nats/median maxprob .995의 3연속 조건과도 멀다. `entropy_loss`는 정규화가 섞인 composite 양수일 수 있으므로 true entropy로 잘못 읽지 않았다.

반면 gradient clip은 빈번하다. 마지막 update 통계는 모든 interval에서 100% clipping이었고 post-clip prediction gradient는 약 .0032–.0064, combat 쪽은 약 .49996–.49999다. 이는 clipping이 효과를 제한할 수 있다는 단서이지, actor/value 각각의 pre-clip contribution이나 update가 잘못됐다는 증거는 아니다. 별도 policy/value gradient 분해가 없어서 value dominance를 확정하지 못한다. LR이 너무 작다는 주장도 작은 KL 하나만으로 성립하지 않는다. Interval parameter L1 변화는 803.8–1,057.8로 optimizer가 실제로 움직였다.

과거 advantage/return의 원시 배열과 전체 update별 KL/loss/clip 값은 보존되지 않았다. Finite guard와 최종 update/전체 update gradient maxima는 확인할 수 있으나 historical advantage mean/std나 gradient variance를 복원했다고 주장하지 않는다. 새 운영 계측에 rollout advantage/return mean/std와 nonzero reward count를 추가했으며, 과거 값은 소급 생성하지 않았다.

행동은 first→last TRAIN opportunity 기준 voluntary switch 8.52→7.58%, injured recovery 14.25→24.93%, defense 9.17→7.72%다. State 분포가 달라 인과 비교는 아니다. 최종 validation의 multiple-legal entropy는 후보 약 .533–.535, V4 약 .589–.591, 최대 action probability median은 약 .876 vs .813이다. Forced singleton은 약 7.9%다. 후보가 다소 더 결정적이나 모든 상태에서 한 행동만 고르는 collapse는 아니다.

## 5. Opponent prediction과 실제 결정 연결

기존 final validation에서 unknown-only, episode당 처음 최대 8 non-wait 관측의 집계다. Frozen public prior 대비 learned prediction 결과를 구분했다.

| 예측 | N | Learned vs prior | 제한 |
|---|---:|---|---|
| Action | 2,869 | NLL 2.605 vs 3.100, accuracy 46.22% vs 36.53%, Brier .783 vs .846 | ECE .239 vs .152로 악화 |
| Ability | 3,525 | NLL .963 vs 1.088, accuracy 72.09% vs 51.26% | ECE .100 vs .094로 악화 |
| Item | 2,762 | NLL 4.329 vs 4.324, accuracy 19.48% vs 18.61% | NLL 개선 없고 ECE .066 vs .058 악화 |
| Moves | 3,968 rows / 251,966 unknown cells | BCE .1788 vs .1861, top4 recall 29.20% vs 26.52% | 독립 cell metric이지 최적 action 판정 아님 |

NLL 개선과 calibration 개선은 다르다. Action family는 attack 2,582, switch 147, setup 54, status 50, recovery 22, defense 14로 불균형하다. 드문 방어/회복 전술에 대한 예측 품질을 aggregate accuracy로 보장하지 않는다. 관측된 executed public action의 정답이지 상대 private intent 정답도 아니다. 공개된 ability/item을 unknown 점수에 섞어 올리지 않았다.

Actor/critic에는 public prior + bounded learned residual이 기대 embedding/예측 type-threat 경로로 연결된다. PPO로 prediction logits가 임의의 latent가 되는 것을 막고 auxiliary는 detached public trunk에서 proper loss를 받는다. 의도된 isolation이지 학습 오류라고 볼 근거는 없다. Known facts override와 unknown semantics도 유지된다.

32 replay의 저장 public state에 한해 forward hook으로 **learned residual만 0**으로 만든 결정적 기능 진단을 했다. 새 policy battle이나 architecture 교체가 아니다. Multiple-legal non-wait 후보 상태 170개에서 argmax 변화 **0**, probability L1 평균 .00667/최대 .03831, KL 평균 .000109, value 절대 변화 평균 .01323이다. B0 sanity 관측의 residual 제거 차이는 정확히 0이다.

따라서 현재 배운 prediction correction이 이 표본에서 큰 action 결정 차이를 만들었다는 증거는 약하다. 하지만 frozen priors, history, action-conditioned reference 전체를 제거한 것이 아니므로 해당 architecture가 무가치하거나 삭제해도 된다는 인과 결론은 아니다. Outcome-selected 8 case의 범위도 제한이다. 전체 일반화, 작은 확률 변화가 stochastic training에 미치는 영향, 장기 가치 차이는 별개다. Auxiliary forward가 PPO update 시간의 28.08%인 것은 비용 대비 우선순위를 재검토할 이유다.

## 6. 학습은 stochastic, 평가/일반 inference는 argmax

Maskable PPO는 masked distribution에서 샘플링한 정책의 기대 return을 최적화하고, 기존 inference/evaluation은 argmax를 실행한다. 그 둘이 다른 것은 버그가 아니지만 같은 성과 목표도 아니다. 이를 경쟁력 실패와 분리하기 위해 **소비된 TRAIN probe 16 case와 final validation 첫 16 case만** 사용했다. Outcome으로 case를 고르지 않았다. 양 좌석, S0/anchor, 후보/V4, 고정 common-uniform sampling stream 2개로 총 512전이다. 새 모델, PPO, stochastic rival 교체는 없다. 원래 learned rival는 argmax 그대로다.

| Scope, 각 정책 128전 | Sampled 후보/대조 | Sampled 차이와 case-cluster 95% | 동일 case의 과거 argmax 차이 | 실행 방식 interaction |
|---|---:|---|---:|---|
| TRAIN 16 cluster | 67 / 62 | +3.91pp [-3.91,+12.50] | -7.81pp | +11.72pp [+3.89,+20.31] |
| Validation 16 cluster | 77 / 76 | +0.78pp [-14.84,+14.84] | -6.25pp | +7.03pp [-7.03,+23.44] |

TRAIN sampled S0 후보/대조 33/30, anchor 34/32; validation S0 37/38, anchor 40/38이며 각 stratum 정책별 64전이다. Retry/truncation 0. Candidate와 V4를 모두 sampling하여 후보에만 탐색을 주는 비교를 피했다. Native seed/case는 그대로이고 정책 선택 RNG는 scope/case/seat/stream SHA로 고정했다.

TRAIN에서 실행 방식 interaction 신호가 있지만 validation 구간은 넓고 두 sampling stream은 충분한 policy randomness 표본이 아니다. Sampled 우월성이나 argmax 대신 production sampling을 선언하지 않는다. Case cluster는 rival·seat·stream 의존을 묶지만 training seed 불확실성까지 해결하지는 않는다. 이 진단은 **실행 목표 정합성이 아직 검증되지 않은 병목**임을 지지하며 그것이 anchor 일반화 퇴행의 유일 원인이라고 증명하지 않는다.

## 7. 후보 원인 순위와 반증

1. **학습 목표/실행 정책 및 좁은 학습 분포의 정합성 — 우선순위 높음.** Stochastic TRAIN의 작은 향상, argmax TRAIN probe -7.81pp, anchor heldout -13.28pp, paired execution interaction이 지지한다. 반증/제한은 sampled validation 개선이 증명되지 않았고 두 독립 TRAIN probe 비교도 작은 표본이라는 점이다. 따라서 곧바로 sampling으로 승격하거나 LR만 바꾸지 않는다.
2. **고정 opponent/team 분포에 대한 국소 적응과 weak credit/generalization — 중간.** Anchor TRAIN 증가가 heldout argmax 개선으로 이어지지 않고 S0는 제자리다. TRAIN 256팀, 10 episode slot 고정은 broad strategic robustness를 보장하지 않는다. 그러나 4,096팀 확장·league 변경을 실제 시험하지 않았고 상대별 episode 비율은 대략 계획대로다. Failure를 opponent mix 하나의 원인으로 확정할 수 없다.
3. **Prediction 개선이 action 가치로 전달되는 효율 부족 — 중간.** Calibration 악화, item 약점, 작은 residual action 영향, 약한 auxiliary gradient와 비용이 근거다. 반면 action/ability proper scores는 개선됐고 경로는 살아 있다. 이 결과만으로 C 또는 head 삭제를 결정하지 않는다.
4. **Optimization/credit assignment 제약 — 가능하나 특정 변경 근거 부족.** Sparse terminal ±1와 GAE .95, clipping은 critic error와 상호작용할 수 있다. 그러나 episode joint decision median 13/p90 20/p99 37/max170이고 return finite, EV 양수이며 KL 폭주도 없다. 무조건 dense HP reward, gamma 변경, LR 증가, entropy 감소를 정당화하지 않는다. HP shaping은 전투 목표를 바꿀 위험도 있다.
5. **학습 미실행·수치 붕괴·모델 신원 오염·평가 control drift — 주요 설명으로 배제.** 실제 Adam/parameter 변경과 SHA, source, full-chunk profile, matched replay가 맞고 no-finite failure다. 운영 결함은 실재하지만 최종 competitive 결과를 설명하는 누락 업데이트의 증거는 없다.

A의 근거는 정상 trainability와 일부 TRAIN 개선이다. A에 반하는 anchor 퇴행 및 장기 continuation 이득 미입증이 더 중요하다. C의 근거는 weak learned correction과 비용이며, 전체 model/reference 삭제에 대한 causal evidence가 부족하다. 따라서 **B를 단일 다음 방향으로 권고**한다. 여기서 B는 PPO/보상/curriculum/LR을 한꺼번에 바꾸는 hyperparameter 탐색이 아니다.

## 8. 실제 운영 결함과 수리

### 놓친 8-retry 경보

첫 32,768 interval, case 95118290에서 같은 episode의 native decision 22–29에 8 retry가 있었다. 초기 외부 work wrapper에 해당 gate가 없어 자동 STOP을 놓쳤다. 후속 wrapper에서 경보가 생겼지만 표준 trainer는 optional external event callback 없이 이를 보장하지 않았다. Interval마다 counter를 새로 만들면 동일 episode의 5+3 retry가 checkpoint 경계에서 누락될 잠재 결함도 있었다.

수리: 소유 trainer에 public retry monitor를 내장했다. UUID+case/revision으로 중복을 제거하고, 같은 살아 있는 episode의 counter를 checkpoint 경계에 걸쳐 유지한다. 8회 또는 interval collected transition 대비 1% 초과, mask-illegal retry 선택은 immutable checkpoint·audit 게시 후 STOP한다. 검사 주기는 frozen checkpoint cadence이며 event 즉시 8번째 step에서 중단한다는 보장은 아니다. Optional event callback이 없어도 작동하고 STOP은 callback보다 먼저 생성된다. Episode 종료 시 counter를 retire하고 explicit resume가 native episode를 reset할 때는 과거 pending counter를 journal에 보존한 뒤 retire한다.

변경 monitor를 **기존 retry 기록에만 재생**했을 때 32,768/425,984/688,128/753,664의 네 gate가 모두 검출됐다. Historical bytes는 바꾸지 않았다. 전체 durable retry 184건은 공개 mask 합법 선택 이후의 uncertainty retry였고 mask-illegal 선택은 0이다. 관측 갱신 후 rejected move가 제거되고 battle은 진행·종료됐다. 37회/14회/19회 incident는 각각 distinct native progress를 포함한다. 원래 private disable/trap 원인을 로그에 없는 상태로 단정하지 않는다. Controlled Imprison 재현은 유사 원리 확인이지 동일 원인 증명은 아니다.

### STOP이 정확히 rollout 경계에 도착할 때의 학습량 오계수

기존 코드는 `floor(collected / rollout_size) * rollout_size`를 trained로 계산했다. Upstream callback은 마지막 step을 buffer에 넣고 GAE/optimizer를 실행하기 **전에** STOP을 반환할 수 있다. Tiny legal-mask env에서 optimizer를 전혀 실행하지 않고 실제 upstream collect를 호출했다. 8번째 collection에서 STOP: `num_timesteps=8`, buffer position=7, full=false, Adam=0인데 기존 floor 식은 trained=8이다.

수리: complete rollout-end를 관측한 뒤 successful train의 실제 Adam clock 진행을 확인하는 ledger로 계산한다. 다음 rollout-start/training-end에서 settle하며 미완성 collection 또는 optimizer 0-step은 trained에 더하지 않는다. Exception으로 train이 끝나지 못한 interval은 checkpoint로 게시하지 않는다. Target-KL로 일부 minibatch만 수행한 성공 update는 full collected rollout 단위의 기존 budget 의미를 유지하되 0-update는 세지 않는다. `untrained_collected_transitions`를 따로 기록한다.

**Stage 1 실제 계수는 소급 변경하지 않았다.** 모든 32 interval에 64 complete update와 1,024 Adam step이 있으므로 이번 latent 경계 버그가 durable 1,048,576을 부풀렸다는 증거는 없다. 발견한 일반 결함과 이번 run의 확인된 피해를 구분했다.

### 비정상 launch 종료와 관측/committed 계수

Launch 3은 final/failure/watchdog 기록 없이 사라졌다. Durable boundary는 589,824/Adam18,432/46,562 native 종료였다. 마지막 heartbeat는 605,576 collected/47,829 종료로 차이는 **관측된 uncommitted 15,752 collected / 1,267 종료**다. 정확히 잃은 optimizer update 수, 실제 종료 시간/원인은 알 수 없다. 이를 trained나 최종 lineage에 합산하지 않았다. Verified model/Adam으로 복구했으며 frozen runtime의 native reset 의미를 유지했다.

수리: optional callback과 무관하게 약 2초 progress마다 append-only launch journal을 flush+fsync한다. `durable_checkpoint`와 `observed_not_checkpoint_committed`를 분리하고 publish 후에만 durable counter/SHA를 갱신한다. Resume는 이전 launch의 종료 record 부재와 partial last line을 탐지·보고하고 원본 tail을 수정하지 않는다. 중간 JSON/sequence corruption은 fail closed다. 정상/실패 종료 record를 남긴다. 이는 power-loss 직전 exact trajectory/optimizer replay나 별도 프로세스의 즉시 liveness 알림을 보장하지 않는다. 기존 사고의 잃은 정보를 만들어 복구한 것도 아니다.

### 버전과 회귀

- 새 운영 계약: `showdown-training-operations-v2`; accounting: `completed-optimizer-rollouts-v2`.
- Model/encoder/loss 계약은 Foundation v1 그대로다. Source fingerprint에 새 operations module이 포함되어 기존 frozen Stage 1 run의 최신 코드 resume는 실패한다. Legacy state를 새 의미로 floor 추론하지 않는다. 기존 checkpoint inference/분석은 계속 가능하다. 과거 source는 baseline commit으로 보존된다.
- 새 test 14개: 7/8 retry, 5+3 경계와 JSON roundtrip, duplicate revision, episode 분리, rate/mask 구분, 실제 upstream STOP 1/7/8/9, optimizer-ledger settlement, partial-tail kill, journal corruption/fsync/NaN, legacy resume/STOP 보존. PPO optimization 없이 실행했다.
- 관련 subsystem 최종 회귀는 57 passed, 4 deselected였다. 4개는 native-learning/actual-PPO/추가 heldout-prediction 평가로 의도적으로 제외했다. Public/private 격리, native legality와 mechanics, encoder 동일성, GAE 경계, source binding, spawn/dummy 일관성, historical reload를 포함한다. 전체 프로젝트 test suite가 통과했다고 확대하지 않는다.
- 수리 후 기존 두 ZIP을 다시 로드해 저장된 public state 425개를 재추론했다. Action/probability/value가 수리 전 기록과 모두 정확히 같았다. 추가 native battle과 PPO update는 0이다. 최종 회귀는 26.88초, 전체 harness wall 28.00초, peak Job 약1.43GiB였다.

## 9. 자원·속도 및 제한

Stage 1 durable launch wall 합계 8,939.26초(2시간28분59초), 117.30 trained transitions/s다. Rollout+update만은 8,606.00초/121.84 transitions/s다. 비정상 launch의 마지막 checkpoint 이후 시간, offline gap, dedicated evaluation은 이 계수 밖이다. 그래서 전체 달력 경과와 같다고 부르지 않는다. 1M당 약 2.48시간은 이 run의 durable-launch 관측치이며 반복 보장/추가 학습 승인은 아니다.

Actor/value 1,203.12초, rollout 5,084.06초, PPO update 3,521.95초, auxiliary forward 988.98초였다. Worker encoding 4,398.07초, native bridge wait 1,439.46초, copy 696.39초, native-step+opponent 5,246.93초는 **병렬 중첩 worker 시간**이므로 합산해 wall이나 pure simulator CPU로 부르지 않는다. End-to-end inference p50은 후보 약7.77ms/V4 약3.75ms, p95 약10.2/5.12ms다.

Peak Job memory 약 6.24GiB, 16 logical CPU 기준 sampled 평균 11.60%/최대13.53%였다. Hard Job은 50% CPU/12GiB, 4 training worker/Torch1 thread/CPU neural learning이었다. 이번 512전 진단은 4 process, peak 약5.47GiB, tree CPU128.84초, 약31초 wall이다. Replay는 peak 약1.20GiB다. 회귀도 Job50%/12GiB 안에서 실행했다. 측정된 외부 network 시도는 0이다. Git 원격 확인/허용 push 외 실제 provider 호출은 없다.

관측 projection의 `MEGA_SOL -> Effect.UNKNOWN` 경고는 native 규칙 오류가 아니라 public representation의 제한이다. 이를 고쳐 모델 계약을 바꾸지 않았고 이 한 경고가 승률 실패의 원인이라고 주장하지 않는다.

## 10. 단일 다음 결정과 Stage 2 gate

**B: architecture는 유지하고 학습/실행 정합성을 중심으로 다음 training-strategy 계약을 먼저 개발한다. 같은 foundation를 그대로 늘리는 Stage 2는 NO-GO다.**

가장 중요한 미해결 질문은 “후보의 stochastic expected-return 변화가 실제로 일반화되는데 argmax에서 사라지는가, 아니면 실행 방식과 무관하게 TRAIN에만 국소 적응했는가?”다. 현재 16-case 진단은 TRAIN interaction을 보여도 validation에서는 구별하지 못했다. 이 질문을 무시하고 더 많은 PPO나 head 삭제를 택하면 원인과 조치가 연결되지 않는다.

T1이 다음 진단만 승인한다면 **단 하나의 고정-model 실행-mode 상호작용 검증**으로 해결한다. 추가 PPO/architecture candidate는 없다.

1. B0/endpoint 중 endpoint 하나와 원본 V4만 고정하고 S0/anchor 두 rival를 고정한다. 이미 읽은 결과로 checkpoint를 재선정하지 않는다.
2. Fresh exact-case TRAIN128 + validation128을 소비 전 manifest로 고정한다. TRAIN은 원래 subset, validation은 기존 heldout split이고 완전 scenario 중복을 제거한다. 새로운 species-unseen 주장이나 sealed final/rare의 대체 사용은 금지한다.
3. 256 cases × 2 seats × 2 rivals × 2 policies × (argmax1 + sampling2) = **6,144 native games 최대**, CPU50%/12GiB/4 process, 최대1시간, chunk별 STOP/consumption ledger. 표본·RNG·bootstrap seed·단일 endpoint·검정 family를 실행 전에 고정한다. 임의 seed 반복이나 sample 증액은 없다.
4. Primary는 validation의 `(candidate−V4)_sampled − (candidate−V4)_argmax` interaction이다. 128 validation case cluster를 resample하고 rival별 anchor guard를 함께 사전 선언한다. Practical margin 5pp, whole validation interaction의 95% 하한>0 및 sampled-vs-V4 하한>-5pp를 모두 요구한다. Anchor guard에도 동시 구간/다중 비교를 적용한다. 이는 미래 결정 기준이지 이번 16-case 결과에 맞춰 합격을 선언한 것이 아니다.
5. 통과 시 실행 정책 목표를 명시한 별도 versioned training contract를 설계한다. Argmax가 제품 요구라면 sampled 성과를 제품 성과로 대체하지 말고 그 요구에 맞는 새 학습 전략 검증이 필요하다. 불통과/불확실이면 자동 Stage 2는 계속 NO-GO이며 예산을 늘려 결론을 만들지 않는다. 이 조사만으로 즉시 C를 승인하지도 않는다.

장기 학습 재개에는 T1의 새 승인, repaired operations의 source/config freeze, 의도한 실행-mode의 paired 개선 및 anchor severe-regression 해소/명시적 허용, 다음 window의 독립 validation/model-selection rule이 필요하다. 구체적인 reward/LR/curriculum 변경은 그때 별도 future contract에 하나의 이유와 검증으로 연결한다. 이번 작업은 이 조건부 계획을 실행하지 않았다.

## 11. 평가 누출·보존·산출물

두 milestone와 29 반복 진단, TRAIN probe, 이번 32 replay/512 execution 진단은 모두 **consumed development evidence**다. 동일 패널에서 checkpoint를 골라 새 우월성을 주장하거나 그 checkpoint를 계속 학습한 뒤 같은 panel을 untouched로 부를 수 없다. 과거 endpoint를 고정한 진단은 selection bias를 줄이지만 panel을 되살리지는 않는다. 캠페인 예약 final/rare offset `98171000`은 미소비로 유지한다.

원본 V4/V5, B0, 모든 Stage 1 checkpoint와 기존 결과/중단 manifest는 불변이다. Preview/JAX/production과 primary master의 선행 변경도 보존한다. 보호 entry의 raw 내용은 출력하지 않고 SHA/status만 비교한다. 원격에는 검증된 operations/trainer/source binding/test와 이 문서만 exact staging으로 commit/push하며 force push하지 않는다.

상세 외부 산출물 루트:

`C:\Users\jsp33\Documents\Codex\2026-10-17\task-pokeadvice-combat-pre-long-training\outputs\stage1_postmortem`

- `evidence_audit.json`, `all_checkpoint_records.json`: 전체 checkpoint/평가 비교와 41-source 시작 신원.
- `complete_read_and_preservation_before.json`: 전체 historical JSON/JSONL/CSV 읽기, 시작 Git/보호 hash.
- `diagnostic_plan.json`, `replay_*.json`, `replay_summary.json`: 32개 matched replay와 public-state 기능 진단.
- `execution_audit_plan.json`, `execution_{train,validation}_{p1,p2}.json`, `execution_audit.json`: 사전 제한된 512개 실행-mode 진단.
- `statistics_and_integrity.json`: 모든 33 ZIP의 finite/Adam 검사, 상대별 구간/민감도, 32 checkpoint 수치, 과거 retry에 대한 새 gate 재생.
- `regression.json`, `regression.xml`, `regression.log`: 실제 test 목록/시간/자원/제외 조건.
- `REPORT_KO.md`, `checkpoint_curve.csv`, `checkpoint_curves.png`: 상세 결과와 전체 progression.
- `git_closure.json`, `preservation_after.json`, `artifact_manifest.json`: 최종 commit/live origin, 이전 산출물·모델 불변 및 이번 산출물 hash. 실제 최종 Git 신원과 경과 시간은 외부 보고서에 기록한다.

최종 checkpoint의 절대 경로:

`C:\Users\jsp33\.codex\artifacts\pokeadvice-combat-foundation-v1-long-training\seed95017-stage1\experiment_00\checkpoint_0028_ppo_1048576_4e3232dd\model.zip`

**엔지니어링 사후 분석과 결함 수리는 완료했지만, 경쟁력 개선은 입증되지 않았다. NO-GO — STAGE 2 승인 근거가 아직 부족하다.**

# FULL_MC_MULTI_SEED_POLICY_TRAINING_V1 결과

**COMPLETE — 계획한 학습과 독립 평가 완료. 글로벌 전략 우위는 미입증이며 기본 추천 정책은 유지한다.**

기준 65a20ca2ca0c7caabba1d2fee4e17d3a9492c8d7에서 시작했다.
네이티브 권위는 Showdown942cda71d14bf0618bd57991708a2e2734b6daba,
gen9championsbssregmc이다. live Champions의 최신 운영 환경 전체를 별도로
검증했다는 의미는 아니다. 시뮬레이터/PPO/학습 아키텍처는 재구축하지 않았다.

## 학습과 실제 참여

유지된 MaskablePPO2.7.1, V3 action-conditioned actor/critic142338파라미터,
7411공개 특징,35네이티브 action mask, sparse terminal reward±1/0,
gamma0.99, LR5e-5, entropy0.01, rollout128x8, batch128,4epochs를 사용했다.
8spawn CPU workers, parent4tensor threads, CPU50%,RAM12GiB,7200s hard deadline이다.
새 보상 shaping, neural architecture, GPU 학습, provider/public-server 호출은 없다.

- V7 fresh seeds41011/41017/41023: 각131072전이.168종 학습,
  validation12/test12/기존 reserved39종 분리. PPO2477 warm seed41011은
  초기화 대조군이며 과거 노출 가능성이 있어 종 미관측 주장에 포함하지 않는다.
- V8 warm seeds42013/42019/42023: 각131072전이. matched fresh seed42013도
  131072전이. 총6개 독립 seed와2개 초기화 대조군, **1048576신규 전이**.
- V7 종료38789배틀(승14434/패24355), V8 종료42128배틀(승19836/패22292).
  학습 **80917배틀**, draw/truncation0. 총32768Adam 업데이트가 수행됐고,
  매 PPO checkpoint에서 finite parameters와 실제 변경을 확인했다.
- V8 실제 reset/선택3마리 집계: **231base species/307starting forms/
  510moves/202initial abilities/166items+명시적무도구**. 종별 선택397–722회.
  구성·참여 집계에는 초기화/미완료 episode도 포함된다. 상대 숨은 아이템·특성은
  coordinator telemetry이며 배우의 관측으로 승격하지 않는다. 모든 기술을
  정책이 실제 실행했거나396형태의 모든 변신을 경험했다는 주장은 아니다.
- V7 선택3마리 집계236시작형태/485기술/175초기특성/166items+무도구.

V8 별도 은행4096train+512validation+512test+512rare-Mega 팀은 기존 native
generator와 TeamValidator를 재사용한다. 전체231종에 ceiling을 추가하지 않았다.
unordered complete teams 및 joint species/moveset 조합과 generation seeds를
분리했다. 반복되는 개별 upstream sets는 허용하고 overlap을 manifest에 기록했다.
개별 세트까지 전부 거부한 시도는264/8192validation 후보만 통과하고 분포를
왜곡해 폐기했다. 이것은 개별 set-unseen 연구가 아니다. V8의 학습으로 V7 및
과거 fresh17의 종들이 노출되므로 해당 모델에 species-unseen 주장을 하지 않는다.
기존 holdout identities/artifacts는 변경하지 않았다. 합법 random 팀은 competitive
사용 분포의 증거가 아니다.

## 모델 선택과 독립 시험

validation offsets1511000(V7)/1521000(V8),32cases x4fixed rivals를 학습 전에
고정했다.32768마다 평가하고, truncation 없는 최고 승수의 최초 checkpoint를
보존했다. final 결과는 선택이나 추가 학습에 사용하지 않았다.

| 실험 | 검증 최고 /128 | 보존 모델의 신규 전이 | 실제 소비 전이 |
|---|---:|---:|---:|
| V7 fresh41011 | 51 | 131072 | 131072 |
| V7 fresh41017 | 54 | 98304 | 131072 |
| V7 fresh41023 | 51 | 131072 | 131072 |
| V7 warm41011 | 69 | 0 | 131072 |
| V8 warm42013 | 74 | 0 | 131072 |
| V8 warm42019 | 76 | 32768 | 131072 |
| V8 warm42023 | 74 | 0 | 131072 |
| V8 fresh42013 | 70 | 65536 | 131072 |

V7 primary는 fresh41017, V8 primary는 warm42019로 final 이전에 고정됐다.
warm 초기 모델이 보존된3실험은 PPO2477과 final case별 승패·행동·실행기술이
동일함을 추가 확인했다. 학습 소비량을 보존 모델의 학습량으로 오인하지 않는다.
fresh 학습은 초기 대비 개선됐지만 warm 후속 학습은 자주 회귀했다.

final offsets2611000(V7test)/2631000(V7reserved)/2621000(V8test)/2641000
(V8rare-Mega)는 이제 **이미 검사한 final IDs**이다. 후속 튜닝에 재사용하지 않는다.
각범위96paired cases x6rivals x18policies, **41472종료배틀**, draw/truncation0.
rivals는 max-power/원본·Champions·전술휴리스틱/v4/PPO2477이다. 고정 checkpoint
SHA, 원시 records, 승패/상대별Wilson구간과 paired case-cluster bootstrap2000회는
models/showdown_full_mc_study_v1/final에 있다. 전체 비교표는
[full_mc_multiseed_table.md](full_mc_multiseed_table.md), 학습 곡선은
../models/showdown_full_mc_study_v1/learning_curves.png에 보존했다.

유한 final96case의 실제 구성 범위도 별도로 집계했다. V8test는 자신의6마리
roster209종/선택3마리165종, 상대roster202종/선택155종이었다. rare 구성에서
양쪽 선택팀의 Mega 후보69형태가 포함됐다(실제 모두 변신했다는 뜻은 아니다).
V7test12종/reserved39종은 양측 선택팀에서 모두 나타났다. full231종 **학습 참여**와
유한 final의 종 참여를 혼동하지 않으며 final_coverage.json에 원자료를 보존했다.

| 정책 | V7 시험 | V7 reserved | 전체-roster 새 구성 | 희귀 Mega 구성 |
|---|---:|---:|---:|---:|
| 새 warm42019 | 326/576 | 260/576 | 260/576 | 319/576 |
| V7 fresh41017 | 283/576 | 229/576 | 221/576 | 300/576 |
| v2 | 314/576 | 266/576 | 234/576 | 303/576 |
| v3 | 315/576 | 232/576 | 253/576 | 303/576 |
| v4 | 330/576 | 223/576 | 241/576 | 291/576 |
| 일반 control | 321/576 | 217/576 | 254/576 | 318/576 |
| PPO2477 | 323/576 | 241/576 | 248/576 | 324/576 |
| 원본 휴리스틱 | 328/576 | 267/576 | 275/576 | 321/576 |
| Champions 휴리스틱 | 329/576 | 276/576 | 290/576 | 325/576 |
| 전술 휴리스틱 | 328/576 | 265/576 | 304/576 | 331/576 |

warm42019의 PPO2477 대비 paired 차이(%p,95%CI): V7test+0.52[-3.12,4.17],
reserved+3.30[-1.04,7.99], V8test+2.08[-1.39,5.56], rare−0.87[-4.34,2.43].
모든 구간이0을 포함해 글로벌 향상을 입증하지 못했다. V8test에서 전술휴리스틱
대비−7.64[-15.28,−0.35]. v4 대비 reserved+6.42[0.69,12.67]는 제한된
탐색적 결과이며 V8훈련 모델의 species-unseen 증거가 아니다. 여러 정책/범위
비교에 대한 multiplicity 보정은 하지 않았으므로 단일 양성 비교로 승격하지 않는다.

V8test primary의 상대별 승수/96: max-power65, 원본38, Champions38, 전술37,
v4 44,PPO2477 38. 각상대 sample96 및 paired96clusters라서 작은 우위의 불확실성이
남는다. 반복 독립 학습 seed가 동일한 우위를 보여주지도 않았다.

## 전략과 값의 실패 양상

V8test primary의 자발 교체378회(PPO2477 239회), 공개 타입상성상 불리하고
더 나은 벤치가 있는 상황의 교체100/187(PPO2477 74/221). 이는 서로 다른
도달 상태의 관측적 집계이며 최적 행동 label/교체의 인과적 승률효과가 아니다.
setup80회로 PPO2477 128회보다 줄었다. recovery0회, injured recovery-available
142상황에서도0회, defense0회였다. 실패 heal0(PPO2477 6)은 회복을 잘 배웠다는
증거가 아니라 회복 자체를 회피한 결과다. v4는 회복303회/failed70회/최대연속8,
전술휴리스틱은 회복179회/failed0회였다. native legality에서 full-HP회복을 막거나
행동 횟수를 보상하지 않았다.

fresh 정책은 자발 교체와 회복을 거의/전혀 선택하지 않았으며 전술 다양성이
자연스럽게 복원되지 않았다. native action masks와 정보 격리 테스트는 통과했고
이 결과를 mask 결함으로 단정하지 않는다. 짧은 승패 중심 random-legal 배틀,
sparse delayed credit, 손실적인 관측 표현 및 inherited optimizer의 분포 이동은
추가 비교가 필요한 가설이다. PPO 업데이트만 늘리는 방식의 한계는 관측됐다.
V8test discounted-return MSE는 primary0.664,PPO2477 0.706,v4 0.763이며
critic 값은 win probability가 아니다. 이 값도 충분히 낮다고 볼 수 없다.

## 호환성·UI·리소스·검증

기존 public catalog의 모든 종/기술/상성 사실이 동일함을 recursive subset 검사로
검증하고68추가 static identifiers의 명시적 변환 manifest를 만들었다. 그중 새로
지원하는 합법 cosmetic aliases도 있다. 원본5주요 모델 SHA와 원래 catalog는
그대로이며 converted zip도 동일 bytes/Adam이다. 새 정적 사실은 새로 학습한
지식이나 관측 사실로 승격하지 않는다. 새 catalog/encoder/state-v2 binding 없이
기존 model을 로드하면 fail closed한다.

actor/critic 모두 동일 공개 partial tensor를 받으며 숨은 sets/future RNG/native
checkpoint/상대 private request는 전달하지 않는다. telemetry는 별도 coordinator
집계이고 Gym info에도 넣지 않는다. 새8보존 모델 reload/legal-action 검사와 실제
Qt8hypothetical scenarios를 통과했다. snapshot/context 불변, exact ledger와
preferred frontier 동일, provider signal0. opt-in 경로만 사용했고 guaranteed-first
기본 정책/legacy exact/replay/runtime truth는 변경하지 않았다.

공개 raw events와 unknowns는 보존되지만 V3 압축 특징은 모든 volatile/변신/순서
정보를 표현하지 않는다. poke-env의 MEGA_SOL→UNKNOWN경고1707회를 final
resources에 명시했다. 네이티브 효과 실행은 유지되지만 휴리스틱/특징의 완전한
M-C 의미 모델을 주장할 수 없다. missing catalog species 없이 reload proof를
통과했다. bring6/pick3는 coordinator-managed이고120ordered-preview policy는 없다.

집중45테스트, 관련 오프라인 회귀246테스트, ruff/diff검사를 통과했다(실행 집계는
중복 포함). 추가 raw41472records 수/terminal 결과와 원본 모델 SHA, 보존 initial
모델의 case별 동등성을 확인했다. 외부 네트워크 시도0. 기존 baseline-only UI layout
두 실패는 이번 선택에 포함하지 않았고 새로운 실패로 집계하지 않았다. Full L3나
전체 suite를 습관적으로 실행하지 않았다.

학습 프로그램 실제32m57.53s(주기검증4m50.67s포함), 검증을 뺀 학습/기동/저장
구간 약28m06.86s이다. 순수 optimizer wall time은 별도 계측하지 않았다. 평균
530신규전이/s(검증포함), CPU-tree11870.48CPU-seconds, 최대9.56GiBRAM,
GPU allocation0. final4범위는 병렬 max11m15.39s, supervisor peak6.01GiB였고
모든 deadline/owned process limits 내에서 끝났다. 생성 은행은8.87s였다.
STOP/optimizer-resume 회귀 검증은 통과했으며 Codex disconnect 생존을 주장하지 않는다.

## 보존과 다음 결정

신규 연구 후보는 models/showdown_full_mc_study_v1/selected/roster_42019_warm/model.zip,
SHA3e79b76df93a49669658bb83dbb3ed6a4918eaa683e94001254cc4f5a07fdf51이다.
validated global strongest는 계속 미해결이고 PPO2477/기존 모델을 보존한다.
새 후보를 기본 추천으로 승격하지 않는다. 사용/중지/재시작 명령은
[full_mc_multiseed_usage.md](full_mc_multiseed_usage.md)에 있다.

동일 구성의 multi-million 전이 캠페인을 바로 확대할 증거는 부족하다. 다음에는
fresh-Adam warm control, 공개 정보/효과/순서 표현과 value/credit assignment,
경쟁적인 역할·세트 분포를 validation-only 연구로 비교하고 **새 final IDs**로
검증하는 편이 타당하다. 현재 인프라는 더 긴 제한적 CPU학습을 실행할 준비가
되어 있으나 실행 가능성과 전략 향상은 구분해야 한다.120action preview learning 및
생산 추천 정책 변경은 별도 범위/승인이다.

Infrastructure commit c9bd9da3178029f612f92df592265f2729eabd89는 canonical branch로
push됐다. 결과 commit/최종 local=remote, 원본 master5변경·native pin·잔여 process
및 전체 경과 시간은 Git closure 후 progress journal/최종 응답에 기록한다.

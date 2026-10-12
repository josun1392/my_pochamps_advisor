# Stronger general policy learning V1

**PARTIAL**. 엔지니어링·실제 학습·독립 평가를 완료했다. 더 넓은 M-C 범위와 v4 대비 일부 개선은 확보했지만, 기존 일반 후보·v2/v3·휴리스틱을 일관되게 능가하는 일반 정책은 입증하지 못했다. 기본 추천을 변경하거나 전역 최강 모델로 승격하지 않았다.

## 연구와 실제 재사용

Metamon의 다양한 공개 관측 경험과 advantage 가중 학습, AlphaStar의 고정 역사 상대 다양성을 작은 범위로 적용했다. MaskablePPO/SB3의 actor·value·Adam·마스킹·직렬화를 그대로 재사용했다. 새로운 PPO/Q-learning/전투/RNG 엔진을 구현하지 않았다. MC-AWR는 실제 완결 경험의 `exp((G−V)/temperature)` 가중 likelihood이며, Metamon의 Q-critic 또는 완전한 AWR 재현을 주장하지 않는다. 라이선스·의존성·M-C 차이와 선택 근거는 [연구 기록](strong_policy_research.md)에 있다.

핀된 Showdown Champions `RandomChampionsTeams`와 TeamValidator를 재사용해191학습 기본 종/40이번 학습 제외 종의 다양한 합법 기술·도구 세트를 확보했다.2048학습 팀/256validation 팀/512test 팀/512unseen 팀이다. 원래 native random spread를 유지해 실전 최적 팀·사용률 자료라고 주장하지 않는다. Gen9BSS factory 재사용 POC는100팀 중1팀만 M-C 합법이었다. 금지 도구·IV·Tera Blast·learnset 문제로 전체 도입을 거절했다.

## 학습과 선택

- 기존 action-conditioned v3표현7411차원/35native 행동,142338parameter feedforward policy/value를 유지했다. 새 encoder/model 버전을 만들지 않았다.
- 공개정보 행동 정책7개에서32768고유 경험/3352완결 대전(1644승/1708패)을 수집했다. 실제 실행32800전이 중 미완결32행을 제외했다. Native hidden set/checkpoint/future RNG는 NN 입력이나 최적 행동 label에 포함하지 않았다.
- 독립 seed2393/2477/2591,동일 시작 일반 후보·고정 v2/v3/v4/일반 상대를 사용했다. PPO/혼합 BC+PPO/MC-AWR+PPO를 각각32768PPO 전이로 대응 비교했다. BC/AWR는 같은 데이터8epoch를 학습했다. 행동 종류별 보상은 없다.
- 9파일럿294912PPO 전이 후 validation 근거로 PPO3seed만98304씩 연장했다. 총589824PPO 전이/61327학습 종료 대전,데이터 수집 포함64679완결 대전이다. 총18432파일럿+연장 PPO optimizer updates +12288offline updates =30720updates. 반복 epoch를 새로운 고유 경험으로 계산하지 않는다.
- 학습·checkpoint validation44000·균형 validation53000·final880000을 분리했다. Native/coherent/tactical validation 승률을 같은 가중치로 평균해 선정한2477을 final 전에 동결했다.2393은native65536전이,2477은98304,2591은32768시점의 더 좋은 가중치를 유지했다. 연장했다고 자동 승격하지 않았다.

## 새로운 독립 최종 평가

96새 케이스×6고정 상대,정책별 범위당576전.14정책×4범위32256전과 별도 대응 예산 평가7488전,총39744전이 전부 승패 종료했다(19807승/19937패,무승부·truncation0). Final 확인 후 재학습·재선정하지 않았다.

40종은 이번 v6학습에서 제외됐지만3종(Dragonite/Excadrill/Skarmory)은 과거 사전학습에 등장했다. 따라서 전역 미관측으로 부르지 않는다. 별도의 엄격한17종은 과거 학습55종·기존 평가 미관측 종과 겹치지 않으며,512native 팀의 final-only bank를 사용했다. 해당 contract는 학습/validation 접근을 거절한다.

| 정책 | 새 native | 이번 제외40종 | 엄격한 새17종 | 기존 coherent |
|---|---:|---:|---:|---:|
|선정 PPO2477|300/576 (52.1%)|314/576 (54.5%)|328/576 (56.9%)|327/576 (56.8%)|
|이전 일반 제어군|283/576 (49.1%)|313/576 (54.3%)|320/576 (55.6%)|322/576 (55.9%)|
|v2|279/576 (48.4%)|304/576 (52.8%)|309/576 (53.6%)|317/576 (55.0%)|
|v3|279/576 (48.4%)|315/576 (54.7%)|319/576 (55.4%)|325/576 (56.4%)|
|v4|304/576 (52.8%)|283/576 (49.1%)|318/576 (55.2%)|313/576 (54.3%)|
|혼합 BC 후보|285/576 (49.5%)|329/576 (57.1%)|318/576 (55.2%)|322/576 (55.9%)|
|MC-AWR 후보|289/576 (50.2%)|323/576 (56.1%)|316/576 (54.9%)|319/576 (55.4%)|
|heuristic|282/576 (49.0%)|328/576 (56.9%)|310/576 (53.8%)|320/576 (55.6%)|
|champions_heuristic|292/576 (50.7%)|319/576 (55.4%)|306/576 (53.1%)|336/576 (58.3%)|
|tactical_heuristic|302/576 (52.4%)|329/576 (57.1%)|305/576 (53.0%)|334/576 (58.0%)|
|max_power|141/576 (24.5%)|146/576 (25.3%)|152/576 (26.4%)|156/576 (27.1%)|
|random|67/576 (11.6%)|70/576 (12.2%)|60/576 (10.4%)|82/576 (14.2%)|

선정2477−일반 제어군의 대응 case-cluster bootstrap95% 구간:

| 범위 | 차이 |95%구간 |
|---|---:|---:|
|native_test|+2.95pp|[-2.26,+8.33]|
|native_current_unseen40|+0.17pp|[-4.86,+5.38]|
|fresh17_test|+1.39pp|[-2.43,+5.38]|
|coherent_test|+0.87pp|[-4.69,+6.42]|

이번 제외40종에서 v4대비 +5.38pp [ +1.74,+9.20 ] 개선은 관찰됐지만, 일반 제어군 대비 모든 구간은0을 포함한다. 엄격한17종에서 tactical대비 +3.99pp [−2.95,+11.11],v2대비 +3.30pp [−2.78,+9.90]로 우위를 확정할 수 없다.96케이스 묶음/2000bootstrap이며, pooled Wilson은 설명용이다. 다중 비교 보정 없는 탐색적 결과이며 실제 인간 상대 승률 또는 정확 확률이 아니다.

동일32768PPO 예산의3seed 합산(각 범위864전),seed와case를 함께 재표본한4000bootstrap:

| 방법 | native | 엄격한17종 |
|---|---:|---:|
| PPO |414/864|512/864|
| BC |431/864|509/864|
| MC-AWR |420/864|519/864|

BC−PPO native +1.97pp [−3.12,+7.29],MC-AWR +0.69pp [−6.83,+7.52]. 엄격17종 BC −0.35pp [−4.63,+4.40],MC-AWR +0.81pp [−3.47,+5.44]. 작은3seed의 탐색적 구간이며 어느 offline 방식도 확실한 우위가 없다. BC/AWR가 validation에서 약했지만 final 일부 표본에서는 동등했다. Final을 보고 승격하지 않았다.

## 전술·value 결과와 실패

기존 coherent에서2477의 자발 교대249회/회복 native실패14회,일반 제어군46회/24회,v4 168회/68회였다. 승리는327/322/313이다. 교대 횟수 자체를 목표나 인과적 개선 증거로 삼지 않는다.2393은같은 범위280승으로 크게 퇴보했고, 실패 후보를 보존했다.

별도 validation 조건부 audit32상태×3첫행동=96native branching을 실행했다. 교대 관심11상태에서 선정/교사/max-power8/6/8승,회복 관심6상태3/4/3승이었다. 설정 관심15상태에서 모델은 전부 공격해10승,교사는 설정해7승,max-power는 공격해9승이었다. 이는 설정 능력 향상 증명이 아니라, 일부 교사 설정을 거절한 결과다. 한 완전 가정·복원 RNG·고정 후속 정책의 진단으로, 최적 행동 label·정확 행동 승률이 아니다. 학습 데이터로 사용하지 않았다.

공통 초기96관측의 valueMSE(native/이번40종/새17종/coherent)는2477 .486/.506/.497/.488,제어군 .495/.509/.481/.476이다. Value 개선도 범위별로 혼재한다. 타깃은6고정 상대의 표본 할인 terminal return이며 win probability가 아니다. 방문 궤적 MSE와 공통 초기 상태 지표를 구분했다.

## 결함 수정·호환성과 제한

- 넓어진 native 대전에서 새Mega폼 `Malamar-Mega` 등을 poke-env가 읽지 못하는 오류를 수정했다. Public native species metadata의 private overlay를 사용하고 원래 Gen9data는 변경하지 않았다.
- 과거부터 있던 audit CLI의 hardcoded v4continuation 설명을 실제 선택 modelID로 바로잡았다. 최종 풀의 사전학습 종 중복을 감사하고 엄격한17종 검증을 추가했다.
- Mega Sol은 Showdown이 native 처리하지만 poke-env public-effect enum에는 없다. 현재 heuristic/feature 표현의 한계로 기록했다. 최종 동안 상대를 변경하지 않았으며, 이후 평가 CLI는 첫 경고와 반복 횟수만 요약해 경고 폭주를 줄인다.
- 실제선택 모델을 기존 PokeAdvice 설명 경로에서 로드·추론했다. 원본 snapshot/context,exact ledger,추천 frontier/기본 orchestration이 모두 동일했고,실험 정책/승률 아님 표기가 확인됐다. Opt-in만 제공하고 기본 guaranteed-first는 유지한다.
- 정책은 팀 구성/bring6pick3선택을 배우지 않는다. 고정 팀 bank·native random spreads·단순/역사 상대이며 인간 전문가·실전 ladder 일반화는 검증하지 않았다. 현재feedforward history와 MC credit assignment의 부족은 후속 연구 가설이며 확정 원인으로 과장하지 않는다.

## 자원·검증·롤백

CPU8spawn workers/parent4threads/50%jobCPU/12GiB RAM/hard runtime1200–1800s를 사용했다. GPU 사용0. Dataset collection80.98s(약405행/s),native bank build70.27s였다. 파일럿791.25s+연장488.61s=21분20초(자동checkpoint/validation 포함);각각약373/604PPO전이/s. 학습treeCPU7369.61s,peak committed9.997GB(약9.31GiB). 최종 evaluator는 각CPU12.5%/4GiB,wall901.19/290.14/319.40s로 병렬 실행했다. 공학·검증 작업과 겹치므로 총 경과에서 이 시간을 단순 차감하지 않는다.

537관련 offline 회귀가178.38s에 통과했고,final-only bank 후33관련 테스트도 통과했다. 추가 실제stop/resume:offline epoch4저장→8복원→128nativePPO 완료. 별도 unit에서는 분할 epoch저장·reload와 연속 실행의 parameters가 bit-for-bit 같았다. 외부 네트워크 시도0,모든 소유 실행은 종료됐다. 기존v2/v3/v4/일반 제어군 SHA는 동일하다. 전체L3/전체pytest를 습관적으로 실행하지 않았으며 이전UI layout2실패 경로를 새로운 회귀로 주장하지 않는다.

Best validation checkpoint: `models/showdown_strong_policy_experiment/learner_2477/model.zip`, SHA `c7f120d7ff5f14c127e030affb1887412c55012eea818dd40b6d98e1242df151`. 기존 제어군과v2/v3/v4를 유지하고 모델을 전역 대체하지 않는다. 나머지seed·rejected BC/AWR·frozen plans·raw gzip결과·source metadata는 실험 디렉터리와 외부run에 보존했다.1GiB공개 trajectory dataset은 Git밖에 있다.

재실행 방법은 [독립 학습 사용법](strong_policy_training.md),진행 기록은 [journal](strong_policy_progress.md)이다. 기존별도터미널/시간제한/체크포인트/STOP/재시작을 유지하며 Codex연결 종료 후 프로세스 생존을 보장한다고 주장하지 않는다.

## 다음 권고

현재 결과만으로1M+전이를 무조건 늘릴 근거는 부족하다. 먼저 더 좋은M-C public-information 행동 데이터와 action-value/sequence-memory 접근을 기존 유지 알고리즘으로 소규모 비교하고,엄격한별도validation에서 향상이 나타날 때만 확장하는 편이 타당하다. 이번역량은 연구용으로 유용하지만 production-strength 정책은 아니다. 기본 추천 변경은 별도T1정책 결정이며 이번에는 하지 않았다.

Engineering checkpoint `4ff302b`는 canonical migration branch에 push했다. 최종 evidence commit은 Git log/최종 응답에서 확인할 수 있다. Master와원래5dirty항목은 그대로 보존했다.

## 선정2477의 상대별 최종 성능

각 cell96전의 승리 수. 고정 상대는 모두 policy-visible 정보만 사용한다.

| 상대 |native|이번40종|새17종|coherent|
|---|---:|---:|---:|---:|
|max_power|67/96|70/96|73/96|71/96|
|heuristic|46/96|47/96|50/96|53/96|
|champions_heuristic|45/96|50/96|50/96|49/96|
|tactical_heuristic|40/96|48/96|49/96|46/96|
|frozen_v2|52/96|48/96|52/96|54/96|
|frozen_control|50/96|51/96|54/96|54/96|

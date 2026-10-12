# General M-C strategy quality and training efficiency

상태: **PARTIAL**. 병렬 학습·재현성·실험 보존은 완료했다. 기존 v4보다
미관측 종에서 개선된 일반 후보를 얻었지만, v2/v3 및 강한 휴리스틱을
일관되게 이기는 전략은 입증하지 못했다. V5 모델을 출시하거나 기본
guaranteed-first 추천 정책을 변경하지 않았다.

## 실제 실력과 독립 평가

학습55종, 종이 겹치지 않는 미관측20종의 커리큘럼 v5를 추가했다.
물리/특수/방어 역할을 섞고, 지원·설정 세트에 Choice Scarf를 무작위로
배정하지 않는다. 기존 v1–v4 커리큘럼 의미는 유지한다. 초안에서9종과
Toxic Orb가 고정 M-C validator에 거절되어 제외했다. Goodra/히스이 폼의
Species Clause도 검증했다. 실전 사용률 데이터나 최적 팀이라고 주장하지 않는다.

seed1237/1301의 PPO-only,1423/1559의 추가 교사 데이터 실험을 각각
기존 표현/공개-history 표현으로 짝지었다. 동일 v4 시작 가중치, 양쪽
새 optimizer, 고정 v4/v3 상대 SHA와 max-power/Champions/tactical
휴리스틱을 사용했다. **4개 독립 seed,8개 대응 실험,81,920 PPO 전이,
8,192 유지된 교사 결정,7,297 종료 대전**, truncation0. 교사 실행에서
실제 진행한 결정은8,220이며 마지막 완결 에피소드의 초과28개는 fit에서 제외했다.
실제 optimizer 갱신은 총2,816회다. 기능/성능 smoke 학습은 이 실력 표본과 분리했다.

내부 validation27000에서 체크포인트를 보존하고, 별도 공통
validation32000의32케이스×5상대로 후보를 선택했다. 기존 표현의
warm_control1423은90/160, 공개-history warm_public1423은88/160,
v4는81/160, tactical heuristic은99/160이었다. 이후 후보와 최종 표본을
고정했다. 최종 평가를 보고 재학습하거나 설정을 다시 선택하지 않았다.

새 offset680000, 범위별64케이스×5고정 상대,10정책으로 **9,600전**을
실행했다. 전부 종료했으며 무승부·시간 제한 종료는0이다.

| 정책 | 새 역할 구성 v5 | 미관측20종 v5 | 기존 broad v3 |
|---|---:|---:|---:|
| 일반 후보 |185/320 (57.8%)|183/320 (57.2%)|203/320 (63.4%)|
| 공개-history 후보 |176/320 (55.0%)|164/320 (51.3%)|208/320 (65.0%)|
| 기존 v4 |168/320 (52.5%)|163/320 (50.9%)|212/320 (66.3%)|
| 기존 v3 |188/320 (58.8%)|191/320 (59.7%)|196/320 (61.3%)|
| 기존 v2 |166/320 (51.9%)|194/320 (60.6%)|187/320 (58.4%)|
| 원래 heuristic |175/320 (54.7%)|194/320 (60.6%)|181/320 (56.6%)|
| tactical heuristic |183/320 (57.2%)|200/320 (62.5%)|198/320 (61.9%)|
| max-power |87/320 (27.2%)|105/320 (32.8%)|95/320 (29.7%)|
| random |32/320 (10.0%)|46/320 (14.4%)|40/320 (12.5%)|

일반 후보−v4의 대응 케이스 bootstrap95% 구간은 새 구성
**+5.31pp [-0.31,+11.56]**, 미관측 **+6.25pp [+1.24,+12.19]**,
기존 broad **−2.81pp [-10.31,+5.00]**다. 미관측에서 v2와 비교하면
−3.44pp [-10.00,+2.81], tactical heuristic과는−5.31pp [-14.06,+3.44]다.
공개-history 후보는 미관측에서 heuristic/tactical/v2보다 명목95% 구간상
낮았다. **공개-history 모델의 승격은 거절**하고 반례로 보존했다.

구간은64개 대응 케이스 묶음,2,000 bootstrap 재표본으로 계산했다.
풀링 Wilson 구간은 설명용이다. 다중 비교를 보정하지 않은 탐색적 결과이며,
이 합성 환경에서의 조건부 표본 빈도를 실전 전체 승률이나 정확 확률로
해석하지 않는다. 유일한 전역 best는 없으므로 기존 v4/v2/v3를 유지한다.

## 전술 약점과 시도한 개선

v4의 새 구성 회복739회 중466회가 선택 시점 full HP였고,82회는
네이티브가 실제 `-fail|...|heal`을 기록했다. 미관측에서도593회 중151회
실패했고, 연속 실패가 최대8회였다. full-HP 회복은 상대가 먼저 공격하면
유효할 수 있어 불법으로 만들지 않았다. 일반 후보의 실패는 새 구성0,
미관측28, 기존 broad0으로 감소했다. 미관측 승리도20회 늘었지만,
회복 감소 자체를 좋은 전략이나 인과 증명으로 취급하지 않는다.

일반 후보의 새 구성 교체22/설정0회는 v4의82/40회보다 적었다.
교체 횟수 보너스를 넣지 않았다. 독립 native checkpoint24상태×3분기
72전에서 회복 대신 공격해 패배→승리가 된 사례와, 교체를 공격으로
바꿔 승리→패배가 된 사례가 모두 있었다. 똑같은 복원 RNG와 고정 후속
정책에서의 결과이며 최적 행동 라벨이나 완전 확률 분포는 아니다.
재실행72전의 행동·결과도 일치했다.

교사 데이터에서 자발 교체는약2.1–2.4%, 설정약4.7–5.2%, 방어약0.3–0.4%였다.
학습 fit도 공격88% 수준에 비해 교체8–16%, 설정0–2%였다.
희소 행동의 모방 불균형은 확인됐지만 그 빈도만으로 교사나 정책의
행동을 틀렸다고 단정하지 않는다. PPO KL은약0.001–0.002, value loss는
약0.32–0.45로 유한했으며 발산은 없었다. 안정성과 강한 전략은 별개다.

시험한 관측-v4는354문맥+35×232=8,474차원,152,514 parameter로,
기존 관측-v3의7,411차원/142,338 parameter에서 확장했다. 공개된
동일 명목 우선도 행동 순서, 마지막 실패·피해·회복/설정 반복, Wish/Protect,
현재 HP 공백·상승 스탯·교체 대상·장판의 행동별 상호작용을 추가했다.
실제 속도, 미래 피해, 숨은 능력/아이템, RNG를 추정 사실로 넣지 않는다.
기존 함수 보존 이전을 검증했지만 이 표현의 강도 개선은 확인하지 못했다.
관측 계약만 실험 지원하며 새 전략 모델 세대로 승격하지 않았다.

방문한 자기 정책 궤적의 value MSE는 일반 후보0.753/0.672/0.667,
v4는0.758/0.672/0.630이었다. 서로 다른 방문 궤적이므로 같은 상태의
가치 품질 비교나 보정된 승률이라고 해석하지 않는다. 더 나은 지연 결과
학습과 공개 정보에 기반한 강한 감독 신호는 여전히 필요하다.

## 실행 효율과 trainer 안정성

실제9800X3D8C/16T,5070Ti16GB,64GB RAM에서 측정했다.1024전이씩
native 표본 수집, profiler를 타이밍 밖에 둔 단일 측정:

| worker | Dummy 순차 전이/s | SB3 spawn 전이/s |
|---:|---:|---:|
|1|268|239|
|2|282|387|
|4|259|574|
|8|236|742|

유지된 SB3 `SubprocVecEnv`,`step_async/step_wait`를 재사용했다.
배치 장벽이 있는 on-policy 병렬 실행이며 새 비동기 RL 알고리즘이 아니다.
동일 seed의 Dummy/spawn 관측·마스크·보상·종료가 일치했다.
4worker 실제2048전이 PPO는 CPU4-thread Dummy8.15s,spawn4.03s였다.
동일 benchmark의 CUDA spawn은5.23s였다. CPU가 현재 모델에 유리하다.
단일 측정의 작은 차이에 통계적 속도 개선을 주장하지 않는다.

PyTorch2.8/cu128의 sm120 실제 커널이5070Ti에서 작동했다.
현재 단일 관측 추론은 CPU약0.275ms/CUDA1.334ms였고,
더 큰656k-parameter 모델의 batch128 계산만20회 갱신하면 CPU1.669s/
CUDA0.035s였다. 이 계산 이득은 환경·전송 비용을 포함한 학습 속도나
전략 개선을 뜻하지 않는다. GPU 기본 활성화는 하지 않았다.

두 본 학습의 wall189.12+280.37s, process-tree CPU631.53+873.27s,
최대 committed RAM5.16GiB였다.8worker 기존4worker 체크포인트에서
1024전이/85종료를 이어 학습했고, 메모리8.32GiB였다.
CUDA2worker512전이/128교사 결정 smoke는13.2s,54종료,
Torch GPU peak약92MiB, 전체 Windows committed약6.6GiB였다.
6GiB job cap의 CUDA OOM을 기록했고, 같은15% GPU allocator cap에서
8GiB job으로 정상 실행되어 CPU-side 메모리 headroom을 확인했다.

worker 수 변경은 SB3 `load(env=...)`로 optimizer를 유지하고 rollout
형태를 재구성한다. 프로세스 수 제한을 제거하지 않고 worker-aware로
조정했다. CPU/메모리/VRAM allocator/시간 상한, STOP, 주기 checkpoint,
best 보존, 종료 시 child process 회수와 새 에피소드 resume를 유지했다.

SB3 checkpoint 로딩이 전역 Python/NumPy/Torch RNG를 재설정하는
부작용도 격리했다. 새로운 실험은 가중치 이전 후 seed를 명시적으로
설정한다. seed1871의 두512전이 실행에서 모든 정책 tensor, 종료49전,
승패, validation score, optimizer 갱신18회가 같았다. 본 실력 실험은
이 후속 수정 이전 trainer로 실행됐음을 manifest에 기록했다.
부분 rollout/중단 에피소드의 정확 복구는 주장하지 않는다.

초기에 step info의 private request 누출을 의심했으나 원본 소스 대조로
기존 native step은 이미 스칼라 결과만 반환함을 확인했다. 실제 누출
결함이었다는 설명을 정정한다. 새 info-v2는 반환 필드를 명시적으로
제한하고, reset의 상대 정책 종류를 제거하며 공개 episode/revision/phase
식별만 제공한다. 기존 tensor가 private request를 받았다는 증거는 없다.
문자열 history 복사 최적화는 실제 PPO 속도 차이가 미미해 **채택하지 않았다**.

## 보존·사용·검증

`models/showdown_general_mc_experiment/control/model.zip`은 validation으로
선택한 일반 후보(SHA30bc6c34...),`public/model.zip`은 거절된 실험 비교
체크포인트(SHA55b4050e...)다. 모델/optimizer manifest,8실험 기록,
9600전 전체 결과,조건부 분기,벤치마크와 재현성 증거를 함께 보존했다.
큰 대전·검증 원본은 `.json.gz`로 무손실 보존했고 압축 해제 byte 일치를
검증했다. 읽기 예: `json.loads(gzip.decompress(path.read_bytes()))`.
기존 v1–v4 파일은 기준9a3e1c6과 byte diff가 없다.

```powershell
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/general_interactive_cpu.json --checkout $engine --output $newRun
uv run --extra learning python scripts/train_showdown_autonomous.py --config config/learning/general_dedicated_cpu.json --checkout $engine --output $anotherRun
uv run --extra learning python scripts/benchmark_showdown_learning.py --checkout $engine --output $newBenchmark
uv run --extra learning python scripts/audit_showdown_policy_branches.py --checkout $engine --output $newAudit
```

interactive는4spawn/Torch4/CPU25%/8GiB, dedicated는8spawn/Torch4/CPU50%/
12GiB로30분 상한이다. 새 output을 사용한다. CPU 기본 preset은 v4를
시작점으로 유지한다. 일반 후보를 후속 연구 시작점으로 쓰려면 새 config의
`initial_model`을 위 control 경로로 지정한다. 검증 표본·별도 새 최종
표본을 정하고 seed를 바꾼다. 반복 PPO 연장만으로 강해진다고 가정하지 않는다.
Codex 종료 후 detach 생존 보장은 이전과 동일하게 검증되지 않았으므로,
별도 사용자 PowerShell 전경 세션에서 실행하고 checkpoint로 재개한다.

Showdown 고정 mechanics, poke-env 공개 baseline, SB3-contrib MaskablePPO,
기존 Gym/Qt 인터페이스를 재사용했다. 이전에 실제 점검한
[Metamon](https://github.com/UT-Austin-RPL/metamon)은 MIT지만 OU 규칙과
forked poke-env/Gym 버전이 현재 M-C 환경과 달라 전체 체계를 이식하지 않았다.
[MaskablePPO](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html),
[SB3 vector API](https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html),
[PyTorch Blackwell 지원](https://pytorch.org/blog/pytorch-2-7/)을 따른다.
PPO, RNG engine, Pokémon mechanics를 새로 만들지 않았다.

광범위 offline407 tests 통과, 후속 RNG/모델/기존 UI/optimizer/environment
관련131 tests 통과. 외부 Python 연결 시도0. 기존 두 UI layout 실패는
이번 검증 범위 밖의 알려진 baseline이며 새 회귀로 합산하지 않았다.
Qt/strategy opt-in에서 기본 exact ledger·preferred frontier와 runtime
truth가 보존됐고, 모델이 없거나 disabled이면 기존 경로를 유지했다.
새 모델의 mask/hash/session과 native state 불변도 테스트했다.

다음 단계는 모델 크기·GPU 시간의 무작정 증가보다, 공개 정보로 실행되는
더 강한 상대/교사와 지연된 선택 결과 학습의 작은 대조 실험이다.
현재 simulator/trainer는 그 실험을 지원한다. 풀 규모 학습 자원 확대와
학습 정책의 기본 추천 적용은 아직 권고하지 않는다. 생산 ranking 변경은
별도 T1 결정이며 이번에는 필요하거나 시행되지 않았다.

기준 local/remote9a3e1c6, 작업 branch `codex/showdown-mc-integration-v1`.
구현 커밋c79874b, RNG/info 수정f24a76f, optional test 수집a3b3642.
이 보고서와 실험 아티팩트는 별도 보존 커밋으로 exact-stage한다.
원본 master691d2df와 다섯 pre-existing 변경 경로는 최종 재확인했고
그대로다. 보호 파일·secrets·provider·공개 서버·master merge는 사용하지 않았다.
모든 소유 학습 프로세스는 종료 상태다. 사용자별 전경 trainer를 통해
독립적으로 재개할 수 있지만 대규모 GPU 학습이나 생산 정책 승격을
이번 결과로 권고하지 않는다.

실제 작업 시작2026-10-12 02:12:38 UTC, 최종 기록04:55:39 UTC:
경과2시간43분01초(커밋·원격 최종 확인은 이후). 본 학습 wall7분49.49초,
누적 process-tree CPU25분04.80초이며 벤치마크·smoke·독립 평가는 별도다.
T3 활성 reasoning 시간은 별도 계측하지 않아 경과 시간과 동일하다고
주장하지 않는다.

# 전술 의사결정 개선 결과 — PARTIAL

전술 curriculum에서 유의한 승률 개선을 확인했다. 넓은 로스터와 미학습
종에서는 v2/v3·휴리스틱에 대한 일관된 우위를 입증하지 못했다. 새로운
모델은 실험용이며 guaranteed-first 기본 추천을 변경하지 않았다.

## 원인과 변경

- poke-env0.10의 setup 조건은 Target enum을 문자열 `self`와 비교한다.
  실제 native Scizor/Tyranitar 상태에서 Swords Dance가 가능하고 공개 타입
  prior가1.1이어도 일반 setup gate가 작동하지 않았다. 공격 PP 소진 후
  무작위 fallback에서는 setup이 나올 수 있으므로 절대 불가능하다는 뜻은 아니다.
- 기존 `heuristic`/`champions_heuristic`, v1/v2/v3 및 과거 benchmark는 보존했다.
  새 `tactical_heuristic`만 enum gate와 공개 정보 기반 회복·교체 조건을 사용한다.
  타입 prior는 최적 행동이나 정확한 피해/KO 증거가 아니다.
- V4 curriculum: 절반은40종의 기존 broad pool, 절반은12종류의 대비 전술
  시작 상태다. 부상/방어 상태는 합법적인 native 행동 prefix로 생성하며
  HP·상태·RNG를 수정하지 않는다. 정책 입력·Gym info에 motif/비공개 set을
  제공하지 않는다. unseen은 별도14종을 유지한다. 합성 시작 상태/팀은
  실제 메타 사용률이나 최적 팀을 대표하지 않는다.
- 35-action mask, V3 encoder7411차원,142338개 파라미터의 공유 action
  scorer/context critic, MaskablePPO, gamma0.99, terminal +/-1은 그대로다.
  네트워크/보상 확대 전에 교사와 curriculum 결함을 먼저 검증했다.
- trainer에 teacher 행동별 데이터/정확도와 명시적 `historical_model`을
  추가했다. 미지정 시 기존 순차 league 의미를 유지한다. 고정 상대의
  SHA와 optimizer 복원/ancestor transfer 범위를 manifest에 기록한다.

## 학습과 독립성

첫 실행501/607/709는 같은 v3 출발점이지만 뒤 seed의 historical 상대가
앞 seed의 best로 바뀌는 league였다. 동일 조건의 독립 seed로 보고하지
않고,811/919/1021을 초기·상대 SHA 모두 고정해 재실험했다.
고정 참조는 `fe52cd3b4e288c242176a6574769bdf1cd8fb5dbedad8b015496cb5b5dcfd57d`.
각 seed의 환경/데이터/PPO/미니배치 RNG는 다르며 pretrained 초기 가중치와
optimizer는 공통이다. 이 재실험은 외부 최종 결과를 읽기 전에 시작했다.

| 실행 | 새 PPO | 교사 결정 | 종료 에피소드 | 최고 validation /240 |
|---|---:|---:|---:|---|
| league 501/607/709 |73728|24576|8052|168 /171 /174|
| 고정 상대811/919/1021 |49152|24576|6119|165 /174 /163|

두 본실험 총122880 PPO 전이,49152 교사 결정,14171 완료 에피소드,6912 실제
optimizer 업데이트다. 검증용 임시 테스트 모델의 smoke 업데이트는 여기에
포함하지 않는다. checkpoint reload와 optimizer 복원을 실행 검증했다.
validation48 cases ×5 rivals로만 선택했다.174승 동점은 먼저 보존한709를
유지했다. 최종 평가 후 후보를 재선택·추가 학습하지 않았다.

선택 artifact: `models/showdown_tactical_v4/model.zip`, SHA
`986ea2ba562d0b34df50ec2ca88ae3171e37031f6f358e9aa5813ffe01412641`.
V4는 curriculum 명칭이며 encoder는V3이다. 이 checkpoint의 새 학습은
PPO24576+교사8192이고, metadata total_steps40960은 v3 출발점의 PPO16384를
포함한다. 조상 v2 학습 전체를 새 학습량으로 더하지 않는다.
독립 seed별 validation-best도 별도 `models/showdown_tactical_seed_*`로 보존했다.

## 잠근 새 최종 평가

선택·seed·비교·offset280000을 먼저 고정했다. 각 열은96 독립 case cluster
×5 고정 상대(max-power/원래/Champions/전술 휴리스틱/frozen v3),480경기다.
11개 정책 ×3 범위 =15840 native 경기 모두 종료, 무승부·truncation0.
이전에 읽은 final offsets90000/20000/30000을 재사용하지 않았다.
별도 league-only offset180000 결과는 보조 자료이며 선택/튜닝에 쓰지 않았다.

| 정책 | 전술+broader V4 | 별도 broad V3 | 미학습14종 |
|---|---:|---:|---:|
| 선택709 |324/480 (67.5%)|240/480 (50.0%)|254/480 (52.9%)|
| 기존v2 |287 (59.8%)|230 (47.9%)|254 (52.9%)|
| 기존v3 |294 (61.3%)|249 (51.9%)|243 (50.6%)|
| 원래 휴리스틱 |286 (59.6%)|250 (52.1%)|256 (53.3%)|
| Champions 휴리스틱 |293 (61.0%)|252 (52.5%)|256 (53.3%)|
| 새 전술 휴리스틱 |323 (67.3%)|265 (55.2%)|233 (48.5%)|
| max-power |183 (38.1%)|120 (25.0%)|126 (26.3%)|
| random |78 (16.3%)|63 (13.1%)|31 (6.5%)|
| 독립811 |314 (65.4%)|244 (50.8%)|243 (50.6%)|
| 독립919 |322 (67.1%)|243 (50.6%)|246 (51.3%)|
| 독립1021 |313 (65.2%)|238 (49.6%)|255 (53.1%)|

전술 범위의 선택 모델 paired 차이(96 case cluster bootstrap2000회,
명목95% CI): v3 대비+6.25pp [1.46,11.04], v2 대비+7.71pp [3.75,12.08],
원래 휴리스틱 대비+7.92pp [2.29,13.13]. 새 전술 휴리스틱 대비+0.21pp
[-5.21,5.83]으로 우위는 확인되지 않았다. 독립 seed들도 전술 점수는
개선됐지만, broad/unseen 우위가 반복되지는 않았다.

v3 대비 broad -1.88pp [-8.13,3.34], unseen +2.29pp [-3.13,7.71].
v2 대비 broad +2.08pp [-3.13,7.29], unseen0pp [-5.21,5.00].
이 값은 조건부 표본 결과이며 정확한 확률·실전 메타 전반의 강함이 아니다.
여러 비교의 CI는 다중검정 보정된 전체 우위 증명이 아니다.

## 전술 변화와 실패

전술480경기에서 v3→선택 모델의 자발적 교체62→391, 회복0→1731,
setup0→35였다. 공개 타입 prior가 불리하고 좋은 벤치가 있는 방문 상태의
교체는62/361→268/313. 부상(<65% HP)·회복 가능 상태의 회복0/736→172/374.
방문 상태가 정책마다 달라서 이 비율 자체를 인과적 개선으로 해석하지 않는다.
native first-action branch368경기에서도 교체·회복·setup 각각 성공과
실패가 있었다. 예: 방어 물리 matchup의 회복5/8승 vs 공격2/8승;
steel matchup 교체5/8 vs 공격2/8; 직관적 fire matchup 교체4/8 vs 공격8/8.
고정 후속 휴리스틱의 조건부 실험이지 최적 행동 라벨이 아니다.

회복은 과도해졌다. 별도 validation offset19000,64경기를3개 상대로 순환한
진단에서 선택 모델 회복147회 중 요청 시점 full HP93회, native `-fail ...
heal`26회였다. 상대가 먼저 피해를 주면 full-HP 선제 선택도 성공할 수
있으므로93회를 전부 잘못으로 보지 않는다.26회의 실제 실패는 낭비 증거다.
이 진단에서 후보/v3 모두30승34패였다. teacher-fit 회복/setup 정확도도
제한적이다. 더 오래 PPO만 돌릴 근거는 충분하지 않다.

setup은 broad109회, unseen0회이고 Protect 중심 방어도 일반화되지 않았다.
전술 value-return MSE .433 vs v3 .544, broad .566 vs .653, unseen .769 vs
.741이다. 각 정책의 방문 trajectory에서 측정한 discounted-return 오차라
공통 상태에서의 value 우위나 calibrated win probability로 해석할 수 없다.

다음 개선은 회복 필요량·공개 속도/위협·현재 강화와 move 특징의 상호작용,
공개 이력/후속 행동을 표현하는 좁은 ablation이다. full-HP 회복을 불법
mask로 막거나 교체/회복 자체에 보너스를 주지 않는다. 짧은 독립 실험으로
실패한 회복과 broad 성능을 함께 확인한 뒤 장기간 학습을 결정한다.

## 재사용·검증·사용

[Metamon](https://github.com/UT-Austin-RPL/metamon) MIT source
`0a00a759c9a4382a2877088d828302ec294a05a5` (2026-05-22)를 실제 확인했다.
Gen1–4/9 OU, forked poke-env0.8.3.3/Gym<=0.29.1 대상이며 현재0.10 import를
호환성 guard가 거절했다. 우회하지 않았다. KaizoPlus의 custom damage
equation이나 다중 GPU AMAGO 체계를 새로 복제하지 않았다. 공개 관측·전술
다양성·frozen opponents 접근은 참고했고, 실행은 기존 Showdown pin,
poke-env 공개 baseline, SB3-contrib MaskablePPO, 기존 Gym/Qt를 재사용했다.
paper: [Human-Level Competitive Pokémon](https://arxiv.org/abs/2504.04395).

관련 broad offline403 tests 통과, 뒤 fixed-reference3 tests와 최종 focused
23 tests(네 checkpoint의 hash/mask/optimizer/identity 포함)도 통과했다.
외부 Python 연결 시도0. 이번 checkpoint는 알려진 기존
1280/1366 UI layout2개 실패를 포함하지 않았으며 새 회귀로 주장하지 않는다.
옵션 dependency test의 기존 E402 import 순서 lint는 별도이며 새 코드 lint
통과. v1/v2/v3/tactics 파일은 기준ecfa5c2와 byte diff가 없다.

Qt300-call smoke: p50/p95 1.98/2.22ms, UI1.044s. 모델·native 상태·런타임
관측 ledger 불변과 설정 해제 시 기본 추천 동일을 확인했다. UI smoke12전은
과거 고정 기능 사례이며 새 전략 실력 표본에 더하지 않는다.
학습/주기검증 두 실행 wall659.24+493.21s, tree CPU737.28+551.92s;
최대 committed RAM2.46GiB, native4 workers 약671MiB, Torch1 CPU thread,
각 작업 CPU12.5%/3GiB cap. GPU0. 최종 broad10560전432.04s (24.44전/s),
전술5280전222.41s (23.74전/s), 동시 두 작업 CPU 합계 cap25%.

사용: `config/learning/tactical_cpu.json` + `docs/autonomous_learning.md`의
foreground launcher/STOP/resume. 동일 조건 독립 seed는 historical_model을
같은 frozen source로 둔다. 새 예산은 새 폴더/설정에서 initial_model을
지정한다. 종료된 run의 partial rollout을 정확히 복원했다고 주장하지 않는다.
Codex 종료 후 detach 지속은 보장하지 않으며 이번 모든 실행은 종료했다.

UI의 기존 선택 설정에 model_path/catalog_path/expected_model_id를 지정하면
실험 추론을 사용할 수 있다. 기본 ranking 변경은 별도T1 결정이며 이번
작업은 그것을 요구하지 않는다. v1/v2/v3 및 legacy exact/replay/관측/UI는
그대로 rollback/authority를 맡는다. 지금 구성의 무작정 장기간 확대보다
좁은 행동 표현/이력 개선과 새 독립 검증을 권한다.

주요 코드 커밋861deee/cdd09c9. 최종 artifact/report 커밋은 branch tip에
기록된다. canonical migration branch에만 push하고 master는 merge하지 않는다.
시작2026-10-12 00:59:25 UTC; 종료와 실제 elapsed는 최종 응답/검증에 기록한다.

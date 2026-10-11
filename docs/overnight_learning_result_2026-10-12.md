# 자율 CPU 학습 결과

**COMPLETE: 독립 훈련기와 실제 학습·저장·재시작·평가·실험 UI 연동 완료.**
전략 성능은 기존 v1 대비 개선됐지만 휴리스틱을 넘는 강한 모델로 판단하지 않는다.
기본 guaranteed-first 추천, 관측/reducer/session 권한, 과거 replay 의미는 유지했다.

검증한 시작점은 보고된907d259 이후의 실제 HEAD
de72731e39f2f5e686dfe9c09d0ddae82a00d879였다. canonical remote는
`https://github.com/josun1392/my_pochamps_advisor.git`, 작업 브랜치는
`codex/showdown-mc-integration-v1`이다. master691d2df와 기존 다섯 변경은 보존했다.

## 구현과 재사용

- 기존 M-C native 환경·checkpoint·Gym adapter·실험 UI를 그대로 사용했다.
- 유지되는 알고리즘은 SB3-contrib MaskablePPO2.7.1이다. PPO/RNG/배틀 mechanics를
  다시 구현하지 않았다. 이전에 실행 검증한 CleanRL/poke-env 비교를 반복하지 않았다.
  poke-env0.10.0의 public Battle parser와 SimpleHeuristics/MaxBasePower를 재사용했다.
- v2 입력5221개: 공통 context321,35개의 행동별140-feature 행. 공통 scorer128/64,
  context64, critic128/64,122626 parameters. 공격/교체 순서 변경에 대한 등가성을 검증했다.
- 실제 가시 request·공개 이력·revealed 정보와 native Dex만 입력한다. 숨은 팀/아이템/
  미공개 기술/미래 RNG는 금지한다. 공개 이력 없는 v2 입력은 fail closed한다.
- 기존 additive curriculum의 장기 학습 split 충돌을 확인했고, 기존 v1 의미를 유지하며
  새 v2에 hash namespace를 적용했다. Unknown/known absence 구분은 유지했다.
- 자동 checkpoint/optimizer 저장·원자적 상태 포인터·동시 실행 lock·stop/deadline·resume,
  검증 최상 보존·동점 유지·정체 시 실험 전환·독립 final 평가를 구현했다.
- supervised warm-start와 PPO 학습률을 분리하고 teacher 적합도를 기록한다. 실험별
  historical opponent의 SHA/경로를 고정해 재시작 시 다른 라이벌로 바뀌지 않게 했다.
  그 identity가 없는 구형 중단 run은 해당 경계에서 fail closed하고 새 명시적 run으로 잇는다.
- 외부 Python 네트워크 차단, Windows kill-on-close job, CPU·메모리 제한 및30초 종료
  유예를 적용했다. 초기 연구 환경의 불완전한 의존성 파일은 격리 환경에서 재설치했다.

## 실제 실험

본편 PPO426736 수집 전이 중426496이 완성 rollout 학습에 사용됐다. 중지된240전이는
복원했다고 주장하지 않는다. teacher49152개, 종료/절단 학습 에피소드48930개다.
구형 실행 기록은 학습 truncation breakdown을 남기지 않아 이를 모두 완결 battle이라고
재해석하지 않았다. 새 launcher는 승/패/무/절단을 분리 기록한다. 별도 pilot/deadline
검증은 PPO5083수집/4992학습, teacher256개, 종료/절단385에피소드였다.

실험 A: seeds11/29/47; v1 warm-start, v2 pure PPO, v2 warm-start 및 historical mixture.
PPO311536전이, teacher32768개, 종료/절단33907에피소드. 순수 PPO 검증34/96→60/96;
v1 warm-start56/96→PPO37/96으로 악화돼 승격하지 않았다. A의 최상은 seed47 PPO32768,
66/96이었다. 더 긴98304-step checkpoint는 최상으로 선택되지 않았다.

실험 B: seeds59/73; A최상 유지, 추가 teacher 적합, 새 독립 seed 비교. PPO115200전이,
teacher16384개, 종료/절단15023에피소드. warm-start3e-4/PPO5e-5로 분리했다.
당시 continued seed59 실험의 PPO RNG는 로드된 seed47을 유지했고, 새 native/teacher
seed만59였다. 독립 seed73은 해당하지 않는다. 새 launcher는 새 budget의 seed를
PPO에도 명시 적용하고 기록한다. 구형 실험 결과를 다른 seed의 독립 학습으로 재해석하지 않았다.
최종 seed73 모델은 teacher8192/12epochs/768 updates와 PPO32768/1024 updates를 거쳤고,
teacher-data 적합97.58%, validation71/96으로 선택됐다. 최종 test는 선택에 사용하지 않았다.

## 독립 최종 시험

v2 curriculum test/unseen offset30000, 각각64 case×3 rival(random/max-power/heuristic).
각 정책192전, 무승부/절단0. unseen6종은 학습10종과 겹치지 않는다.

| 정책 | 일반 시험 승/패 | 미학습 종 승/패 |
|---|---:|---:|
| 새 모델 |130/62,67.7%|130/62,67.7%|
| 기존 v1 |102/90,53.1%|96/96,50.0%|
| 실험 A최상 |123/69,64.1%|119/73,62.0%|
| 휴리스틱 |133/59,69.3%|140/52,72.9%|
| random |70/122,36.5%|49/143,25.5%|

v1 대비 paired 차이는+14.6pp(CI+8.3…20.8),+17.7pp(CI+9.4…25.5).
A 대비+3.6pp/+5.7pp의 CI는0을 포함해 추가 우위를 확정하지 않는다.
휴리스틱 대비−1.6pp(CI−4.7…+1.6),−5.2pp(CI−9.9…−0.5)다.
CI는64 case cluster를 유지한2000회 bootstrap이다. pooled Wilson60.8…73.9%는
상관된3 rival strata 때문에 기술적 참고값이며 정확한 확률이 아니다.
value MSE0.530/0.586은 이전 v1의0.854/0.979보다 낮지만 보정된 승률은 아니다.

## 자원·UI·검증

CPU-only, Torch1thread, run당 native4workers(동기 vector stepping), CPU12.5%/commit3GiB
hard cap. 짧은 두 run 중첩 시 최대25%/6GiB;16논리CPU/64GiB 장치다. GPU 학습 없음.
실측 peak job commit A2.12GiB/B1.92GiB, A중단+재개 tree CPU1729.95초,
B638.89초. run wall 합36분54초(병행 구간 포함), 총 tree CPU39분29초.
정체 기준이 더 긴 예산을 중지했다. 성능 개선 없이 단순 연장하지 않았다.

413 native 관측/32배틀에서 최적화 전후 feature bitwise equality를 확인했다.
인코딩 p50/p951.287/1.969→0.653/1.005ms. 최종 모델1000 inference는1.023/1.263ms,
load1.277초. 실제 Qt dispatch85ms, end-to-end845ms, Python peak555MiB/Node139MiB였다.
12 native smoke 배틀10W/2L,136 actions: 공격97, 대기23, 강제교체15, 일반교체1;
Mega9, status6, ability9, item종료5, 날씨30 이벤트. UI root는4개의 숨은 아이템
가정에서 같은 가시 정보로 Flamethrower를 선택했다.99.3%는 정책 선택 분포이며 승률이 아니다.
runtime snapshot/ledger 불변과 opt-in 해제 시 기존 출력의 완전 동일성을 검증했다.

넓은 offline checkpoint7860pass/기존 UI layout2fail,509.42초. 새 Showdown 실패 없음;
parent/4pytest workers 외부 네트워크 시도0. 최종 관련 검사는53pass/30.34초였다.
native masks·forced replacement·pivot/queued choice·checkpoint·Unknown·과거 v1·SHA검증·
truth/ranking isolation·새 budget에서 optimizer 이어 학습·frozen rival binding을 검증했다.
30초 deadline 실행은30.059초에 중지,4571수집/4480학습,321에피소드, worker 종료였다.

## 사용과 남은 범위

자율 훈련 명령·설정·중지·재개는[autonomous_learning.md](autonomous_learning.md)를 따른다.
`models/showdown_action_v2/model.zip` 및 manifest가 최종 opt-in artifact이며 SHA는
`364e30469d8a30106f90c04e0fc59a601b92f541af8b41235d08bd67af06d667`이다.
기존 `models/showdown_initial_v1`은 변경하지 않았다. 학습 checkpoint는 AppData의
`PokeAdvice/training/overnight_2026-10-12/{experiments,warmrate}`에 보존했다.

Codex host의 실제 breakaway probe가 inherited job에 남아 앱 종료 후 지속은 보장하지
않았다. 완료된 모든 실험은 종료했다. 사용자는 별도 PowerShell에서 session을 유지하고
독립 훈련기를 실행/중지/재개할 수 있다. 무제한 background/GPU 작업은 남기지 않았다.

Legacy는 관측/reducer/session/replay/UI/guaranteed exact evidence 및 rollback을 맡는다.
Showdown은 legality·native mechanics·진행/checkpoint·학습 환경을 맡는다. 이번에 legacy
mechanics를 제거하지 않았고 exhaustive exact enumeration은 학습의 전제 조건이 아니다.

현재 결과는 엔지니어링 성공과 실제 학습 성공, v1 대비 전략 개선을 입증한다. 휴리스틱
초과 강도·전체 M-C roster 일반화·팀 preview 학습·recurrent belief·폭넓은 self-play·
보정된 value는 남았다. 다음은 roster/강한 opponent/독립 seeds를 확대한 제한 학습과
평가를 권한다. 대규모 GPU 학습을 바로 늘리기보다 이 일반화 검증을 우선한다.
기본 추천 정책 변경은 별도 T1 결정이며 이번에 변경하지 않았다.

검증된 커밋48318c2/7bfd3ee에 이어 최종 artifact·회귀·작업 기록을 같은 브랜치로
커밋/푸시한다. master merge/force push/보호 파일 변경/provider/public battles는 없었다.
실제 경과시간은 마지막 journal snapshot에 기록한다.

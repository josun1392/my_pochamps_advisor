# Full Regulation M-C legal training domain V1

**COMPLETE — pinned Showdown 지원 영역의 native 합법 학습 기반.** 실게임의
전수 eligibility 인증이나 완성된 전략 AI를 뜻하지 않는다. 기본 추천과 기존
모델을 승격/변경하지 않았다.

권위는 `gen9championsbssregmc`, clean Showdown
`942cda71d14bf0618bd57991708a2e2734b6daba`의 Dex, format rules,
learnsets, TeamValidator와 native battle execution이다. 외부 라이브 게임의
목록/변경 사항과 전수 대조하지 못했다. [공식 뉴스 목록](https://champions.pokemon.com/en-us/news/)
에서 M-C 공지는 확인했지만 상세 페이지가 보안 확인으로 막혔다. 이를 native
권위의 독립 인증으로 취급하지 않는다.

| 항목 | native 검증 범위 |
|---|---:|
| 합법 base species | 231 |
| 시작 가능한 폼/장식 alias | 307 |
| Mega 변신 폼 | 82 |
| 능력에 의한 전투 변신 폼 | 7 |
| 합계 | 396 |
| 선택 가능한 기술 | 510 |
| 초기 세트에서 선택 가능한 능력 | 202 |
| 변신 능력 포함 합집합 | 215 |
| 합법 held item | 166, 별도로 명시적 무도구 허용 |

기존 RandomChampionsTeams source는 231 base/342폼이다. base species 누락은
없지만 폼 54개를 생략했다. 그중 Dex.all()도 생략한 virtual cosmetic alias
14개가 포함된다. 모든 inventory entry는 합법 세트와 **전체 6마리 팀 witness**를
가진다. 기술/능력 목록은 실제 단일 기술 세트 검증이며, 그 목록의 임의 조합이
항상 합법이라는 뜻이 아니다. 생성하는 조합과 전체 팀은 매번 다시 native
검증한다. Cartesian 조합/모든 팀을 열거하지 않았다.

515개 native move-rule 후보 중 Pound, Power Shift, Soft-Boiled, Spore,
Struggle은 지원 종의 초기 선택 세트 witness가 없다. 호출 기술/Struggle 같은
전투 중 실행은 native 엔진이 담당하며 public catalog가 해당 기술을 포함한다.
태그 검사만 통과하던 Cramorant-Gulping/Gorging, Eiscue-Noice,
Minior-Meteor, Ogerpon Tera 4폼은 시작 세트가 실제로 금지돼 제외했다.
Dex 존재/태그 통과를 합법 팀으로 오인하지 않는다.

`models/showdown_mc_domain_v1/inventory.json.gz`는 versioned inventory,
`manifest.json`은 content/source 해시, `public_dex.json`은 별도 공개 metadata,
`catalog.json`은 전체 public alias를 포함한 학습 catalog다. static catalog의
1586개 Dex entry 전체가 M-C 합법이라는 뜻은 아니다. eligibility는 inventory만
사용한다. native source 파일과 생성 도구 해시를 기록했다.

`tools/showdown_bridge/legal-domain.cjs`는 native 검증을 재사용하는 세트/팀
샘플러다. base/form의 임의 작은 ceiling이 없다. 가능한 경우 upstream role
세트를 50% 사용하고, 나머지는 합법 move/ability/item/nature/스탯 포인트를
변화시킨다. 11씩 균형 분배 주변과 32/32/2 집중 분배를 모두 포함한다.
희귀 세트는 form/ability/item/정확한 moves tuple/nature/evs constraint로
요청할 수 있다. `evs`는 Champions native 스탯 포인트이며 mainline EV 변환이
아니다. `item: ""`만 명시적 무도구이고 None/Unknown/불완전 stat 입력은
거절한다. 세트 64회/팀 64회 재시도, 최대 8192팀/호출, subprocess timeout을
적용했다. CLI job은 CPU 12.5%, 2 GiB 또는 검증 시 4 GiB로 제한한다.
native 무작위 팀은 coverage fixture이며 실전 사용률/최적 팀 자료가 아니다.

V7 bank는 train 2048/validation 256/test 256/historical-unseen 256팀이다.
종 단위 partition은 **168/12/12/39**로 폼까지 분리되고, 전체 팀 해시도 서로
중복되지 않는다. 이전 V6 manifest의 실제 종 수는 192/39다. 이전 보고의
191/40 표기는 이번 파일 감사로 정정하며, 과거 bank/평가/기록을 다시 쓰지
않았다. fresh17을 포함한 기존 39종 holdout을 학습에서 유지하고, 새 24종은
V7 hash namespace로 학습 전에 고정했다. 이번 학습/선정은 새 validation만
사용했다. 새 test의 전략 점수는 확인하지 않았다. 전 영역 legality fixture
검사는 모델 선정을 위한 final 성능 label로 사용하지 않는다.

현재 bank의 시작 species/form coverage는 train 236, validation 16, test 12,
historical 43이며 합집합 307이다. train은 485기술/175능력/166도구와 무도구를
포함한다. 전 영역 coverage fixture는 307시작 폼/510기술/202선택 능력/
166도구와 무도구를 포함한다. 학습 study의 예약 종과 전 영역 generation
capability는 별개다.

실행 검증: 4096팀을 같은 seed로 두 번 생성해 byte content 재현성을 확인했다.
4122팀 시도, 31171세트 시도, item collision 6491회, bounded set 재시도
소진으로 팀 재샘플 26회, 최종 승인 팀의 legality 실패 0이다. 별도 1267개
constraint fixture를 실제 native 진행시켰고, Mega 82개를 전부 활성화했다.
Castform 3폼, Aegislash-Blade, Mimikyu-Busted, Morpeko-Hangry,
Palafin-Hero를 실제로 도달시켰다. V1–V4 encoder의 초기/행동 후 총 10136회
유한값/correct catalog 검사, 13개 checkpoint fork/동일 continuation 비교를
통과했다. native whole battle 32/32 종료, truncation 0 (max-power 12승,
tactical heuristic 20승). 이는 전략 품질 비교 연구가 아니라 환경 smoke다.

이번 결함 수정은 temporary formechange를 own-request base details로 덮어쓰던
문제, 14 public alias metadata 누락, Illusion replace의 HP 없는 이벤트와
잘못된 팀원 정보 귀속, V7 restart의 bank 내용 미결합이다. 새
`showdown-policy-state-v2`는 공개 appearance의 identity 불확실성과 확인된
replace를 구분하고, 현재 구간의 공개 사실만 옮기며 이전 팀원의 item/move
기록을 보존한다. 실제 native Illusion 해제와 semantic regression으로 검증했다.
Revival Blessing의 fainted-slot mask, pending opponent action과 fork 연속성도
실제 native 전투로 확인했다. observation/reducer/runtime/replay 원본은 수정하지
않았다. Unknown status duration/item/ability는 추측으로 채우지 않는다.

일부 public Transform/volatile/copy/swap/field event는 fixed feature encoder에
완전히 표현되지 않는다. `projection_coverage`로 명시하고 원래 public_history를
보존한다. 완전한 mechanics state나 perfect-information policy 입력을 주장하지
않는다. 기존 catalog가 생략한 14폼은 기존 inference의 public_catalog_coverage에
명시한다. 새 full catalog는 누락 species를 fail closed한다. 이전 catalog/model
fingerprint를 조용히 바꾸지 않으며, 구 모델의 full-catalog warm-start에는 별도
명시적 compatibility conversion이 필요하다. fresh training은 검증됐다.

bring-6/pick-3, Species/Item Clause, level 50, IV 31, stat-point 66은 native
검증/preview로 유지한다. 모델은 preview 이후의 35 native 행동을 선택한다.
3-of-6 selection 학습은 하지 않았다. 후속 bounded 설계는 별도 preview-action
contract의 ordered 3-of-6 **120개 선택**, own 6개 세트+상대 공개 6종 입력,
native `team XYZ` 제출/phase binding이다. 기존 35칸을 다른 뜻으로 재사용하거나
production 팀 선택 정책을 추가하지 않았다.

기존 autonomous trainer/8 spawn worker/MaskablePPO/optimizer/save/reload/evaluation을
그대로 사용했다. 개선한 V7 fingerprint는 bank/domain/catalog/tool/adapter 해시를
checkpoint와 평가에 묶으며, valid bank 교체도 restart fingerprint가 달라진다.
오래된 미결합 V7 smoke를 정확히 이어받았다고 주장하지 않는다.

readiness는 동일 seed 8059의 수정 단계별 짧은 4회, 총 8192전이/401종료 대전/
256 optimizer update다. 독립 seed 강도 실험이 아니다. 최종 회차는 2048전이/
102종료 대전/64 update, 136067 parameter element 변경을 확인했다. 3회 checkpoint
validation은 각각 2/16승으로 개선되지 않았다. 모델 강도를 주장하거나 승격하지
않았다. 마지막 학습 checkpoint를 reload해 masked inference와 실제 Qt 전략
파이프라인 8 scenario를 확인했고, exact ledger/default frontier/runtime snapshot이
동일했다. 모델 archive는 local Temp readiness output에만 있으며 새 모델 버전을
repo에 등록하지 않았다.

최종 job 측정: inventory+bank build 7.89초, CPU 9.44초, peak 293 MB.
4096×2+1267 coverage generation/재현/집계 13.29초, fixture native 실행+encoder/
baseline 확인 14.08초, 전체 검증 33.82초, peak 1.27 GB. 최종 학습은 startup/
checkpoint/evaluation 포함 15.93초, 128.6전이/초, tree CPU 73.05초,
peak 8.07 GiB, cap CPU 50%/RAM 12 GiB, GPU 0이다. 전체 짧은 학습 wall은
63.46초다. 환경/플랫폼 고정 측정이며 큰 캠페인의 확정 throughput이 아니다.

최종 material shared-state offline checkpoint: **552 passed**, 외부 네트워크
시도 0, 잔여 worker 없음. focused native/identity/restart/parallel/UI 검사를
병행했고 ruff/diff 검사를 통과했다. 알려진 baseline-only UI layout 두 실패는
이번 검사 범위에 포함하지 않았고 새로운 Showdown 회귀로 재분류하지 않았다.
Full L3/전체 pytest를 습관적으로 실행하지 않았다.

원본 master의 5개 변경, protected files, V1–V4와 PPO2477/기존 연구 archive,
작은 과거 curricula, legacy exact/replay/guaranteed-first consumer를 보존했다.
새 default 정책이나 legacy engine 제거는 없다. rollback은 기존 catalog/curriculum
설정과 opt-in inference disabled 경로로 유지된다. live truth mutation은 없다.

재현 가능한 사용은 migration checkout에서 다음과 같다. 결과 디렉터리는 새로
지정하며 기존 artifact를 덮어쓰지 않는다. optional learning 의존성을 설치한
Python/uv 환경과 clean pinned Showdown checkout이 필요하다.

```powershell
python scripts/build_showdown_full_domain.py --checkout <pinned-showdown> --domain-output <new-domain-dir> --bank-output <new-bank-dir>
python scripts/verify_showdown_full_domain.py --checkout <pinned-showdown> --output <new-proof-dir> --sample-teams 4096
python scripts/train_showdown_autonomous.py --config config/learning/full_domain_smoke_cpu.json --checkout <pinned-showdown> --output <new-run-dir>
```

후속 전 영역 학습의 인프라는 준비됐다. 먼저 별도 versioned study/config에서
새 bank/curriculum identity를 고정하고 CPU bounded 파일럿/다중 seed로 경쟁력과
분포 균형을 확인하는 것이 적절하다. 장기 1M+ campaign, neural strength 향상,
production default 승격을 이번 증거만으로 승인했다고 해석하지 않는다.

작업 시작 2026-10-12 07:36:24 UTC, validation closure 09:04:49 UTC로 그 시점의
경과시간은 1시간 28분 25초다. 이후 exact-stage/commit/push/remote 검증까지의
실제 최종 경과시간과 Git SHA는 최종 응답에 기록한다.

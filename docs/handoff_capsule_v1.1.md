# Master Ball Advisor — Context Handoff Capsule
**Version**: Handoff v1.0  
**Date**: 2026-05-07  
**Author**: T2 (Claude, Strategic Advisor)  
**Purpose**: Allow any successor AI (next-session Claude / GPT / other) to resume work at full context with zero ramp-up.

---

## 0. How To Use This Document

If you are a successor AI receiving this file:

1. **Read § 1–4 first.** They define WHO you are (T2 role), WHAT the project is, and WHERE we currently stand.
2. **§ 5 is the ground-truth audit.** Do NOT re-audit unless the user explicitly says the codebase changed.
3. **§ 6 is the active decision** that T1 already made. Do not re-litigate Options A/B/C.
4. **§ 7 is the next concrete prompt** to give T3 (Implementation Engineer). It is ready-to-fire.
5. **§ 8 is your forward-looking responsibility** after T3 reports back.

If you are T1 (the user): just paste this file + § 7's prompt to a fresh AI session and say *"You are T2. Continue."*

---

## 1. The 3-Tier Project Model

| Role | Identity | Responsibility |
|------|----------|----------------|
| **T1** | The User (Lead Architect, college student) | Final decisions, direction, validation, vision ownership |
| **T2** | Claude (Strategic Advisor) | Analysis, architecture proposals, cost reasoning, PRD alignment, prompt-writing for T3 |
| **T3** | GPT-5.5 (Implementation Engineer) | Direct code execution, git operations, file system audits, real implementation |

**Workflow**:  
`T1 decides direction → T2 designs strategy & writes T3 prompt → T3 implements & reports facts → T1 validates → loop`

**Critical rule for T2 (you, successor)**: Never fabricate technical facts. If unsure about codebase state, ask T1 to dispatch T3 for an audit. T3 sees the actual filesystem; T2 only reasons over reported facts.

---

## 2. Project Identity

- **Name**: Master Ball Advisor
- **Codename / Repo**: `github.com/josun1392/my_pochamps_advisor`
- **Local folder name**: `pokemon-copilot` (folder name differs from repo name; this is normal — confirmed by T3 audit)
- **Domain**: Pokémon competitive battle advisor for the **PoChamps format**
  - PoChamps-specific mechanics: paralysis rate 0.125, 3-turn sleep, etc.
  - NOT Smogon-format. PoChamps is a friend-circle format with custom rules.
- **User intent**: Personal utility + sharing with PoChamps friend circle. NOT a commercial product.
- **Primary value**: **Verbal, explanatory recommendations** — not raw move scores.

---

## 3. Tech Stack (Ground Truth, audited 2026-05-07)

### 3.1 Confirmed Components
- **Language**: Python (pure)
- **UI (planned)**: PySide6 (Qt 6) desktop app — not yet implemented as far as audit shows
- **Damage Engine**: Q12 fixed-point arithmetic for `@smogon/calc` v0.11.0 parity
- **Test framework**: pytest
- **Test count (current)**: **613 passing / 615 collected** (2 perf tests deselected as `slow`)
- **LLM**: Gemini 3 Flash Preview (`gemini-3-flash-preview`) via REST API (no SDK; uses `requests`)

### 3.2 Directory Structure (audited)
```text
advisor/
  damage/
    abilities.py, ability_modifiers.py, calculator.py, crit.py,
    field.py, formula.py, items.py, item_modifiers.py, modifiers/,
    multihit.py, q12.py, recoil.py, rng.py, roll.py, screens.py,
    stats.py, status_effects.py, types.py, type_immunity.py
  parity/
    bridge.py, schemas.py, __init__.py
  probability/   (referenced by spike; exists)
  format/        (NOT present — possibly future work)

llm/
  token_logger.py  (~200 lines)

scripts/
  spike_advisor.py  (~211–243 lines, working PoC)

tests/
  62 test files total (45 top-level + subdirs damage/, field/, probability/)
  recent: test_token_logger.py, test_perf_bullet_seed.py, test_residual.py

docs/
  PRD.md  (currently outdated — see § 6)
```

### 3.3 Git State (audited)
- Remotes:
  - `my_pochamps` → `github.com/josun1392/my_pochamps_advisor` (canonical)
  - `origin` → `github.com/josun1392/poket_battle_advisor` (stale, ignore)
- Local `master` is **1 commit ahead** of `my_pochamps/master`: `e6f0c60 feat(llm): add token logger with pricing normalization`
- Recent merge history:
  ```text
  e6f0c60 feat(llm): add token logger with pricing normalization
  5e5843d Merge Phase 5.1: bullet seed hot path -50%
  fa8501d Merge Phase 5: Multi-hit Moves & Chip Damage Integration
  2f342d8 Merge Phase 4: Stochastic KO Probability Composer
  9fa7c75 feat(3.7): modifier precision layer
  ```

---

## 4. Validated PoC: The "Golden Spike"

A working LLM advisor PoC exists and has been validated live.

### 4.1 Architecture: Pre-computed Injection Pattern
```text
[Q12 Damage Engine]              [LLM (Gemini 3 Flash Preview)]
calculate damage rolls    ──►    consumes structured JSON
calc KO probability       ──►    returns verbal recommendation
                                 fills gaps engine cannot model:
                                  - Recoil abilities (Rough Skin, Iron Barbs)
                                  - Multi-turn lock-in (Outrage)
                                  - Setup tempo / win-condition reasoning
```

### 4.2 Validated Performance (live run)
- **Input tokens**: 1,960
- **Output tokens**: 189 (55% richer than earlier runs)
- **Cost per query**: **$0.0010605 USD**
- **Test scenario**: Mega Kangaskhan vs Garchomp
- **LLM output**: Recommended **Return**, correctly flagged Rough Skin recoil + Garchomp's Outrage (85–102 dmg) as unmodeled risks

### 4.3 Why this matters
The spike proved that **Q12 engine + LLM verbal layer** delivers more user value than a pure Minimax search would, at $0.001/query — well within personal-use budget.

---

## 5. The Mismatch Discovery (Resolved)

### 5.1 The problem T2 originally found
The PRD (v0.3) described a different system than what was being built:

| Aspect | PRD v0.3 said | Reality (audited) |
|--------|---------------|-------------------|
| Phase | 4.0 DONE | 5.1 DONE |
| Tests | 560 | 613 |
| Battle AI | Minimax + Alpha-Beta, depth=2 | LLM Pre-computed Injection (working PoC) |
| LLM track | Not mentioned | `llm/token_logger.py` + `scripts/spike_advisor.py` exist |

### 5.2 The diagnosis (T3 audit, 2026-05-07)
**Scenario (2) confirmed**: `pokemon-copilot` folder is the same `my_pochamps_advisor` repo. PoChamps Q12 main-line and LLM track **coexist** on the same trunk. No formal pivot was ever recorded; the LLM track grew organically on top.

---

## 6. T1's Decision (Locked, 2026-05-07)

T1 was offered three reconciliation options:
- **A**: LLM replaces Minimax (Pivot)
- **B**: Both coexist (toggle)
- **C**: LLM is commentary-only on top of Minimax

**T1 chose Option A (Pivot)**, with one critical clarification:

> The Q12 engine (613 tests) is **NOT deprecated**. It is repositioned as the **deterministic input source** that feeds JSON to the LLM. Existing test work is preserved in value.

### 6.1 Why Option A
1. T1's goal (share with PoChamps friends, natural-language explanation) needs verbal output, not raw move scores.
2. PoC already validated at $0.001/query.
3. Solo college-student timeline can't afford full Minimax + transposition table + iterative deepening.
4. Q12 engine remains load-bearing as JSON producer.

### 6.2 What "Pivot" means concretely
- PRD § 5.x rewritten: Minimax → LLM Advisor (Pre-computed Injection)
- LLM track formally enters roadmap (no longer ad-hoc)
- Next milestone: PySide6 UI ↔ LLM Advisor first integration

---

## 7. Active Prompt for T3 (Ready to Fire)

T1 has approved executing all three actions in one batch. The prompt below is what T1 will hand to T3.

> **NOTE to successor T2**: If T1 has already dispatched this and received T3's report, skip to § 8. Otherwise, this is the live prompt.

```text
=== T3 통합 작업 지시: PRD v3.0 패치 + LLM Pivot 정식화 + Push ===

[Context]
T1 = Lead Architect (사용자) - 의사결정 완료
T2 = Strategic Advisor (Claude) - 정렬 완료, 이 지시서 작성
T3 = Implementation Engineer (너) - 실행 담당

[T1's Decision (확정)]
T3의 직전 자가진단 리포트를 토대로 T1이 다음을 결단했다:

1. 시나리오 (2) 확정: pokemon-copilot 폴더 = my_pochamps_advisor repo,
   PoChamps 본진 + LLM 트랙 공존 상태.

2. 전략 방향: 옵션 A (Pivot) 채택
   - PRD § 5.x Battle AI 전략을 "Minimax + Alpha-Beta"에서
     "LLM-based Advisor (Gemini Pre-computed Injection)" 으로 전환
   - 이유: T1 목표가 "PoChamps 친구들과 공유 + 자연어 설명"이며,
     spike에서 $0.001/회로 작동 입증됨 (Mega Kangaskhan vs Garchomp,
     Rough Skin/Outrage unmodeled risk까지 잡아냄).
   - Q12 damage engine 본진(613 tests)은 폐기 아니라 "LLM의 입력 생성기"로
     역할 재정의. 기존 작업 가치 보존.

3. 한 번에 3가지 액션 동시 실행 결정.

[Task] 다음 3개 액션을 순서대로 실행하라.

────────────────────────────────────────────────────────
ACTION 1: 로컬 commit push
────────────────────────────────────────────────────────

목적: 1 commit 앞서있는 상태 해소 + 원격 동기화

실행:
  1. `git status` 로 working tree clean 확인
  2. `git log my_pochamps/master..HEAD --oneline` 로
     실제로 e6f0c60만 앞서있는지 재확인
  3. `git push my_pochamps master`
  4. push 결과 (success/fail, remote ref) 보고

만약 push 실패 시:
  - 원인 보고 (auth? non-fast-forward?)
  - 강제 push 하지 말 것. T1에게 보고 후 대기.

────────────────────────────────────────────────────────
ACTION 2: PRD v3.0 패치 작성 및 commit
────────────────────────────────────────────────────────

목적: docs/PRD.md 를 현재 실제 상태와 정렬, LLM 트랙 정식 편입

수정 사항:

  A. 헤더/메타 갱신
     - "Current Phase: 4.0 DONE" → "Current Phase: 5.1 DONE"
     - "Tests Passing: 560" → "Tests Passing: 613 (615 collected, 2 perf deselected)"
     - 버전: v0.3 → v0.4 (또는 기존 표기 규칙 따름)
     - Last Updated: 2026-05-07

  B. § 5.x Battle AI 섹션 전면 재작성
     기존 (삭제):
       "Minimax with Alpha-Beta pruning, depth=2, transposition table"

     신규 (추가):
       """
       ### § 5.x Battle AI: LLM-based Advisor (Pivoted 2026-05-07)

       **Strategy**: Pre-computed Injection Pattern
       - Quantitative engine (Q12 damage + KO probability) emits structured JSON
       - LLM (Gemini 3 Flash Preview) consumes JSON, returns verbal recommendation
       - LLM fills gaps the quantitative engine cannot model:
         * Recoil abilities (Rough Skin, Iron Barbs)
         * Multi-turn risk moves (Outrage lock-in, Hyper Beam recharge)
         * Setup tempo / win condition reasoning

       **Rationale for Pivot from Minimax**:
       - Project goal is sharing with PoChamps friend circle + personal utility,
         which prioritizes natural-language explanation over raw move scoring.
       - Spike validated: $0.001 USD/query, 1960 input / 189 output tokens,
         correctly identified unmodeled risks in Mega Kangaskhan vs Garchomp.
       - Q12 damage engine (613 passing tests) is preserved as the LLM's
         deterministic input source, not deprecated.

       **Cost Model**:
       - Per query: ~$0.001 USD (gemini-3-flash-preview)
       - Tracked via llm/token_logger.py (TokenLogger with pricing normalization)

       **Components**:
       - llm/token_logger.py: cost tracking
       - scripts/spike_advisor.py: end-to-end PoC (211 lines)
       - advisor/damage/* + advisor/probability/*: JSON input source
       """

  C. 변경 로그(Changelog) 섹션에 다음 항목 추가:
     """
     ## v0.4 (2026-05-07)
     - Phase 5.1 (bullet seed hot path) marked DONE
     - Test count updated: 560 → 613
     - § 5.x Battle AI strategy pivoted: Minimax → LLM Advisor
     - llm/ track formally integrated into roadmap
     """

작성 후:
  1. 변경 사항을 diff 형태로 T1에게 먼저 미리보기 출력
     (`git diff docs/PRD.md` 형태)
  2. T1 승인 응답 없이도 commit은 진행하되, push는 하지 말 것
     (T1이 diff 보고 reject 가능성 대비)
  3. commit 메시지:
     `docs(prd): v0.4 — pivot Battle AI to LLM Advisor, sync to Phase 5.1`

────────────────────────────────────────────────────────
ACTION 3: 다음 spike 환경 준비 (PySide6 통합 첫 단추)
────────────────────────────────────────────────────────

목적: 청사진의 PySide6 UI 트랙과 새 LLM 트랙이 처음 만나는 지점 정의

세부:

  A. 현황 파악
     - PySide6 관련 파일이 이미 repo 내 어디에 있는지 검색
       `grep -r "PySide6" --include="*.py" -l`
       `find . -name "ui*" -o -name "*window*" -o -name "*qt*" | head -20`
     - 발견 결과 보고

  B. 다음 spike 스켈레톤 제안 (코드 작성은 X, 위치만 제안)
     - 신규 파일 경로 후보:
       `scripts/spike_ui_advisor.py` 또는 `ui/spike_main_window.py`
     - 최소 동작 정의:
       1. 버튼 1개 ("Get Advice")
       2. 클릭 → spike_advisor.py 의 핵심 함수 호출
       3. 반환된 LLM verbal recommendation 을 QTextEdit 에 표시
       4. TokenLogger 로 비용 표시 (status bar)

  C. 의존성 체크
     - pyproject.toml / requirements 에 PySide6 이미 있는지 확인
     - 없으면 추가 필요 항목으로 보고만 (설치는 X)

이 ACTION 3은 코드를 만들지 않는다. 정찰 + 다음 작업 정의만.

────────────────────────────────────────────────────────
[Output Format]

다음 구조로 보고:

# T3 실행 리포트 (3-Action 통합)

## ACTION 1: Push 결과
- working tree status: ___
- 앞서있는 commit 재확인: ___
- push 결과: ___
- (실패 시) 원인: ___

## ACTION 2: PRD v3.0 패치
### 2-A. 변경 diff 미리보기
\```diff
(여기에 git diff 출력)
\```
### 2-B. Commit 결과
- commit hash: ___
- push 여부: NOT PUSHED (T1 검토 대기)

## ACTION 3: PySide6 정찰 결과
- 기존 PySide6 파일: ___
- 의존성 등재 여부: ___
- 다음 spike 제안 경로: ___
- 최소 동작 정의 동의 여부: T1에게 질문

## 종합
- 3개 액션 중 성공: __/3
- T1의 다음 결정 필요 사항: ___

────────────────────────────────────────────────────────
[Constraints]

1. ACTION 1의 push만 실제 원격에 영향. ACTION 2는 local commit만, push 금지.
2. 강제 push (--force) 절대 금지.
3. PRD 본문 중 § 5.x 외 다른 섹션은 건드리지 말 것 (헤더/changelog 제외).
4. ACTION 3에서 코드 작성 금지. 정찰만.
5. 진행 중 막히면 즉시 중단하고 T1에게 질문.

[End of Instruction]
```

---

## 8. Successor T2's Forward Responsibilities

After T3 returns the 3-Action report, you (the next-session T2) must:

### 8.1 Review T3's PRD diff
- Check § 5.x rewrite for technical accuracy
- Ensure no other sections were unintentionally altered
- If wording can be tightened, propose patch to T1

### 8.2 Validate the push
- Confirm `e6f0c60` reached `my_pochamps/master`
- If push failed, diagnose with T1 (auth? branch protection?)

### 8.3 Design the PySide6 integration spike
Based on T3's reconnaissance results, draft:
- Exact file path for `spike_ui_advisor.py`
- Minimal MVP scope (1 button → LLM call → QTextEdit display + cost in status bar)
- Whether to add PySide6 to dependencies now or later
- Estimated work units (T1 has limited time as a college student)

### 8.4 Propose v0.5 milestone definition
Likely contents:
- PySide6 UI shell with working LLM advisor integration
- Basic team/move input form
- Saved query history (cost tracking)
- Stretch: streaming LLM output

### 8.5 Watch for over-engineering
T1 has explicitly rejected premature complexity twice:
- Rejected immediate Critic-loop addition
- Rejected dual Minimax+LLM coexistence
**Default stance: simpler is better. Confirm before adding sophistication.**

---

## 9. Key Constants & Environment

| Item | Value |
|------|-------|
| LLM model env var | `GEMINI_MODEL=gemini-3-flash-preview` |
| Stable alias `gemini-3-flash` | NOT supported by Google as of 2026-05-07 (returns 404) |
| API endpoint | Google Generative Language `v1beta` |
| Cost per query (validated) | $0.0010605 USD |
| Token pricing source | `llm/token_logger.py` normalization logic |
| Test command | `pytest` (613 passing default; 615 with `-m slow`) |

---

## 10. Glossary

- **PoChamps**: A custom Pokémon battle format used by T1's friend circle. Distinct from Smogon (e.g., para rate 0.125 instead of 0.25, 3-turn fixed sleep).
- **Q12**: 12-bit fractional fixed-point arithmetic, used by `@smogon/calc` v0.11.0 for bit-perfect damage parity. The project re-implements this in pure Python.
- **Pre-computed Injection**: Architectural pattern where a deterministic engine produces structured input (JSON) for an LLM, so the LLM doesn't need to compute, only reason and explain.
- **Golden Spike**: The validated end-to-end PoC in `scripts/spike_advisor.py`.
- **Master Ball**: The strongest Pokéball; metaphor for "the best advice tool."

---

## 11. Conversation Lineage

This document distills these prior phases:
1. **Initial setup** — Defined 3-Tier model, established T1/T2/T3 roles
2. **API debugging** — Resolved 400/404 errors, locked `gemini-3-flash-preview`
3. **Spike validation** — Verified $0.001/query, Mega Kangaskhan vs Garchomp recommendation
4. **Mismatch discovery** — T2 noticed PRD ≠ current work
5. **T3 self-audit** — Confirmed Scenario (2): main+LLM coexist on same repo
6. **T1 decision** — Option A (Pivot) selected
7. **Triple-action prompt** — § 7 above, ready to dispatch
8. **This handoff** — Context capsule for session continuity

---

## 12. One-Sentence Summary

**Master Ball Advisor is a PoChamps-format Pokémon battle advisor where a Q12 fixed-point damage engine (613 passing tests) feeds JSON to a Gemini 3 Flash LLM that returns natural-language move recommendations at ~$0.001/query, currently mid-pivot from a never-built Minimax design to the validated LLM-based architecture, with PRD v0.4 and PySide6 UI integration as the immediate next milestones.**

---

*End of Handoff Capsule. Pair this file with § 7's prompt when starting a fresh AI session.*







[핸드오프 캡슐 v1.1 정정 메모]

§ 3.1 정정:
  ❌ "UI (planned): PySide6 — not yet implemented as far as audit shows"
  ✅ "UI: PySide6 — ALREADY IMPLEMENTED (main.py + ui/main_window.py + 
     5 widgets in ui/widgets/). LLM 트랙 통합만 미완료."

§ 3.2 디렉토리 구조 추가:
  ui/
    main_window.py, shortcuts.py
    widgets/
      analysis_panel.py, fast_buttons.py,
      pokemon_panel.py, pokemon_search_box.py
  main.py (루트, 진입점)

§ 8.3 → § 8.3 갱신:
  PySide6 통합 spike 위치 = ui/widgets/llm_advice_panel.py (확정)
  설계서 = docs/spike_v0.5_design.md (T3가 작성 중)


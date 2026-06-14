# v6.12 TurnPipeline Prompt / UX Copy Design

## Purpose

v6.12 designs prompt-facing and user-facing copy for future TurnPipeline exposure.

This is a design and documentation step only. It does not implement UI, add a checkbox, connect TurnPipeline to the user-facing advice button, run Gemini, or change production behavior.

## Background

v6.10 executed one controlled actual Gemini smoke with an explicit-on `turn_pipeline` payload fixture. The result was PASS:

- actual Gemini call count: 1
- retry: none
- stop condition: none
- candidate wording was maintained
- Quick Claw was treated as possible / "may", not guaranteed
- Focus Sash was treated as possible survival, not guaranteed consumption or result
- no full turn simulation claim
- no item consumption claim
- no exact post-turn HP claim
- no RNG, speed tie, or exact trigger resolution claim
- damage estimate was treated as a default-assumption estimate, not final battle damage

v6.11 closed that smoke result and kept the current boundary explicit:

- explicit limited `turn_pipeline` generation is possible
- optional top-level payload insertion is possible
- prompt guard presence / absence is verified
- default UI advice flow remains off
- UI checkbox and user-facing automatic TurnPipeline enablement are not implemented
- full Turn Engine, item consumption, HP updates, RNG, speed ties, and exact trigger resolution are not implemented

## Naming Candidates

| Candidate | Audience | Pros | Cons | Recommendation |
|---|---|---|---|---|
| Turn Pipeline | developer / contract docs | Matches existing schema and helper names. | Sounds technical and may imply a complete engine to users. | Use internally. |
| Turn Planning Summary | English user-facing / debug UI | Communicates planning rather than certainty. | Still slightly broad; may need a limitation note. | Good English UI candidate. |
| Limited Turn Context | English user-facing / debug UI | Emphasizes limited scope. | Less specific about events. | Good help text phrase. |
| Candidate Turn Events | English user-facing / debug UI | Clearly frames events as candidates. | Technical, but honest. | Best English label candidate. |
| 턴 이벤트 후보 | Korean user-facing / debug UI | Short and clear that events are candidates. | May still need a tooltip for non-technical users. | Best Korean label candidate. |
| 제한적 턴 판단 보조 | Korean user-facing / help text | Communicates advisory and limited nature. | Too long for a checkbox label. | Good explanatory phrase. |

Recommended naming:

- Developer / schema / documentation: `TurnPipeline`
- Korean user-facing label: `턴 이벤트 후보`
- Korean explanatory phrase: `제한적 턴 판단 보조`
- English user-facing label: `Candidate Turn Events`
- English explanatory phrase: `Limited Turn Context`

## UI Label and Help Text Candidates

### Korean Compact Label

```text
턴 이벤트 후보 포함
```

Tooltip / help text:

```text
확정 턴 시뮬레이션이 아니라, 아이템/속도/생존 가능성 같은 제한적 후보 정보를 조언에 추가합니다.
```

Longer help text for a settings panel:

```text
턴 이벤트 후보는 확정 결과가 아닙니다. RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 계산하지 않고, 현재 정보 기준의 참고 후보로만 사용합니다.
```

### Korean Dev-Flag Label

```text
개발용: 턴 이벤트 후보 포함
```

Tooltip / help text:

```text
TurnPipeline 후보를 payload에 추가해 조언 문구를 점검합니다. 기본 조언 흐름은 변경하지 않으며, full Turn Engine 결과가 아닙니다.
```

### English Compact Label

```text
Include candidate turn events
```

Tooltip / help text:

```text
Adds limited planning context, not a full turn simulation.
```

Longer help text:

```text
Candidate turn events are not resolved outcomes. RNG, item consumption, post-turn HP, speed ties, and exact trigger results are not resolved.
```

## User-Facing Warning Copy

Recommended Korean warning:

```text
이 정보는 확정 턴 시뮬레이션이 아니라 제한적 판단 보조입니다. RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 확정하지 않으며 후보 정보로만 참고하세요.
```

Short Korean warning:

```text
확정 턴 시뮬레이션이 아니며, 발동/소모/턴 종료 HP는 후보 정보로만 참고하세요.
```

Recommended English warning:

```text
This is limited planning context, not a full turn simulation. RNG, item consumption, post-turn HP, speed ties, and exact trigger results are not resolved.
```

## Prompt Guard and UX Copy Alignment

Prompt guard meaning:

- candidate events are not resolved outcomes
- `turn_pipeline` is not full turn simulation
- no RNG, item consumption, post-turn HP, speed tie, or exact trigger result is resolved
- `turn_pipeline` does not replace `damage_estimate`, `ko_context`, or existing item contexts

User-facing copy should mirror the same meaning without schema-heavy wording:

- say "후보" / "candidate"
- say "제한적" / "limited"
- avoid "pipeline proves" or "simulation result"
- keep `damage_estimate` and KO context as the primary calculation references

## Advice Output Copy Rules

Allowed wording:

- "발동할 수 있음"
- "후보로 고려"
- "확정은 아님"
- "현재 정보 기준"
- "제한적 계산 기준"
- "may affect"
- "can be considered"
- "candidate context"
- "not resolved"

Forbidden wording:

- "반드시 발동"
- "소모됨"
- "턴 종료 후 HP는 X"
- "완전한 턴 시뮬레이션 결과"
- "스피드 타이 결과 확정"
- "will activate"
- "will be consumed"
- "post-turn HP will be X"
- "full turn simulation shows"
- "speed tie is resolved"

Recommended style:

- Mention candidate events only when relevant to the recommendation.
- Keep candidate event notes shorter than the move recommendation.
- Tie candidate notes back to known limitations.
- Prefer "may" / "can" / "candidate" over "will" / "confirmed" / "resolved".

## Next Step Options

### Option A: v6.13 UI Exposure Design

Design the future UI location, toggle behavior, disabled state, and rollout plan.

Pros:

- keeps implementation out of scope
- makes UI exposure safer before code changes
- can decide whether this remains dev-only or becomes user-facing later

Cons:

- does not lock prompt copy in tests
- UI implementation still remains a later milestone

### Option B: v6.13 Prompt Copy Test Fixtures

Add fixture tests that lock the prompt / UX copy rules without adding UI implementation.

Pros:

- small and safe implementation step
- protects the wording before UI exposure
- no actual Gemini call required

Cons:

- does not answer final UI placement questions
- may still need later UI design

### Option C: v6.13 UI Dev Flag Implementation

Implement an actual dev flag or checkbox.

Pros:

- enables hands-on UI validation
- can remain default-off

Cons:

- increases user-facing or developer-facing surface area
- requires T1 approval and careful rollback
- still early before copy rules are locked in tests

## Recommendation

Recommended next step:

```text
v6.13 Prompt Copy Test Fixtures
```

Safe alternative:

```text
v6.13 UI Exposure Design
```

Do not proceed directly to UI Dev Flag Implementation unless T1 explicitly approves implementation scope.

## Safety Statement

- No actual Gemini call was executed in v6.12.
- No Vertex AI call was executed.
- No production code was implemented.
- No UI checkbox was implemented.
- No user-facing advice button automatic connection was added.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.
- Secrets, API keys, access tokens, ADC credentials, service-account JSON, billing details, and token-log contents were not printed or recorded.

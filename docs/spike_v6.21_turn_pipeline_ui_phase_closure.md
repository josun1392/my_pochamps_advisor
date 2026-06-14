# v6.21 TurnPipeline UI Phase Closure

## Purpose

v6.21 closes the TurnPipeline UI phase after the controlled UI Gemini smoke passed in v6.20.

This is a closure and stability document. It does not implement production code, run another Gemini call, change UI behavior, or expand TurnPipeline into a full Turn Engine.

## Phase Completion Summary

- v5.3 Item Context -> TurnEvent mapper: added helper-level mapping from existing item/context payloads into `TurnEvent` candidates.
- v5.4 mapper coverage: expanded fixture coverage for unavailable, blocked, malformed, and ordering cases.
- v5.5 TurnPipelineResult fixture/helper: added fixture/debug construction for limited planning output.
- v5.6 debug report: added local TurnPipeline inspection without Gemini or Vertex calls.
- v5.7 payload exposure design: designed optional top-level payload exposure with default-off policy.
- v5.8 optional top-level payload adapter: added explicit-only `turn_pipeline` payload support.
- v5.9 prompt/contract guard: added guardrails so candidate events are not resolved outcomes and do not replace existing contexts.
- v6.0 minimal integration design: kept the next step explicit and default-off.
- v6.1 explicit/default-off generation helper: added `build_optional_turn_pipeline_for_advice_payload(...)`.
- v6.2 explicit payload smoke: verified manual helper plus payload adapter smoke behavior.
- v6.3/v6.5 advice flow design: compared integration points and kept advisor/UI automatic generation out of scope.
- v6.6 advice flow dry-run: added default-off dry-run flag near `run_ui_selected_advice(...)` and verified with mocked Gemini.
- v6.7 closure/stability: documented safety boundaries and timing-sensitive perf instability.
- v6.8 payload snapshot lockdown: locked default/off/on payload shapes with plain pytest assertions.
- v6.9 controlled Gemini smoke design: designed a one-call, no-retry controlled Gemini smoke.
- v6.10 controlled Gemini smoke execution: ran one explicit-on fixture Gemini smoke and classified it PASS.
- v6.11 smoke closure: closed the controlled smoke result and prepared UI exposure design work.
- v6.12 prompt/UX copy design: selected user-facing terminology and warning copy.
- v6.13 prompt copy test fixtures: locked prompt/copy anchors and forbidden wording.
- v6.14 UI exposure design: compared UI exposure options and recommended default-off dev/internal exposure.
- v6.15 offline E2E advice fixture: verified payload -> prompt -> mocked advice flow without external calls.
- v6.16 UI exposure test plan: documented default-off, on/off smoke, no-call, and rollback tests.
- v6.17 controlled UI mock smoke: verified fake UI state off/on paths without implementing UI.
- v6.18 UI dev flag implementation: added the default-off dev-only checkbox.
- v6.19 UI dev flag smoke/manual QA: verified checkbox, tooltip, status, and no-auto-call behavior offscreen.
- v6.20 controlled UI Gemini smoke: ran one UI-enabled Gemini smoke and classified it PASS.

## Current Feature State

- UI dev flag label: `턴 이벤트 후보 포함`.
- The checkbox defaults unchecked.
- No persisted auto-on or saved-setting enablement exists.
- The off path preserves existing advice behavior.
- The on path passes `enable_turn_pipeline=True`.
- Top-level `turn_pipeline` is limited-only in the current implementation path.
- Prompt guard states that TurnPipeline is not full turn simulation and candidate events are not resolved outcomes.
- The UI-enabled Gemini smoke passed once with exactly one actual Gemini call, no retry, no Vertex AI call, and no stop condition.

## Safety Boundary

Currently implemented:

- Add limited turn event candidates to LLM advice when explicitly enabled.
- Provide candidate events, known modifiers, and limited planning/debug context.
- Provide prompt guardrails so Gemini should not present candidate TurnPipeline data as full simulation.
- Preserve `damage_estimate`, `ko_context`, and existing item contexts as the authoritative existing advice primitives.

Still not implemented:

- Full Turn Engine.
- Exact turn order resolution.
- Speed tie resolution.
- RNG resolution.
- Item consumption.
- Post-turn HP update.
- Exact trigger resolution.
- Opponent set inference.

## Controlled UI Gemini Smoke PASS

v6.20 used the UI dev flag path with the checkbox enabled.

- Actual Gemini call count: 1.
- Retry: none.
- Stop condition: none.
- Result classification: PASS.
- Quick Claw used possibility wording.
- Final move order was not modeled.
- Focus Sash was treated as possible survival context.
- There was no full simulation claim.
- There was no item consumption claim.
- There was no exact post-turn HP claim.
- There was no RNG, speed tie, or exact trigger resolution claim.
- Forbidden phrase checks were false.

This result supports exposing the feature only as limited candidate context, not as final turn truth.

## Known Issue: Timing-Sensitive Perf

`test_item_damage_calculation_under_point_12ms_average` has intermittent environment/order-dependent timing-sensitive failures, usually around a small median threshold overrun.

Current policy:

- Do not change the threshold.
- Do not add skip or xfail.
- Do not change damage formula, raw rolls, Q12 multiplier, `ko_context`, or payload filtering to address this closure.
- Use final reruns returning green as the push-readiness signal while recording any observed instability.

## Next Big Direction Options

### Option A: v7.0 Turn Engine Roadmap / Scope Split

Design how a future full Turn Engine would split exact turn order, item consumption, HP update, trigger resolution, RNG, and speed tie handling.

Pros:

- Directly addresses the largest remaining conceptual boundary.
- Keeps implementation from accidentally growing out of limited TurnPipeline context.
- Gives T1/T2 a clean decision point before any full-engine work.

Cons:

- Design-heavy and may not immediately improve user-facing advice quality.
- Requires careful scope discipline to avoid implementing engine behavior too early.

### Option B: v7.0 Battle State / Opponent Move Context Expansion

Expand battle-state and opponent move context before attempting full turn simulation.

Pros:

- Likely improves advice usefulness without requiring exact full-engine resolution.
- Can remain additive to existing `damage_estimate`, `ko_context`, and item contexts.

Cons:

- May need more UI/input decisions.
- Still needs boundaries so inferred opponent context is not overstated.

### Option C: v7.0 UI Polish / User Testing

Use the current default-off dev flag to gather usability feedback and polish copy/layout/status behavior.

Pros:

- Low algorithmic risk.
- Helps validate whether users understand "candidate turn events" as limited context.

Cons:

- Does not expand reasoning capabilities.
- Could distract from needed scope design if treated as the main next phase.

## Recommendation

Recommended next major step:

```text
v7.0 Turn Engine Roadmap / Scope Split
```

Safe alternative:

```text
v7.0 Battle State / Opponent Move Context Expansion
```

Do not start full Turn Engine implementation directly. The next phase should be design and scope separation first.

## Safety Statement

- No production code was implemented in v6.21.
- No actual Gemini call was executed in v6.21.
- No Vertex AI call was executed.
- No UI checkbox behavior was changed.
- No user-facing advice button behavior was changed.
- No full Turn Engine was implemented.
- No item trigger evaluation was implemented.
- No item consumption or HP update was implemented.
- No speed/order simulation was implemented.
- No damage formula, raw damage roll, Q12 multiplier, `ko_context`, or payload filtering behavior was changed.
- `logs/token_usage.jsonl` was not committed or reset.

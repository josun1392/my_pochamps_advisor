# Next Session Prompt v1.9 - Gemini Verification Follow-Up

## v13.16 Closure

Observed direct damage is sourced from the Previous Damage panel dialog and
kept as a defensive per-session snapshot. Its limited-context payload is
normalized, acknowledged exactly, and deterministically consumed only by
Counter, Mirror Coat, and Metal Burst. Counter/Mirror Coat use x2 matching
category, Metal Burst uses floor(3/2), and confirmed opponent HP caps actual
damage/KO. Immunity and unavailable/no-effect paths are explicit; no normal,
fixed, or HP-special fallback is allowed. Keep unsupported timing, indirect,
survival, and ability-override mechanics out of this contract.

## v13.13 Direct Healing

- Implementation commit: `8dcef1d feat: add deterministic direct healing`.
- Direct healing uses `meta.healing`, exact self current/max HP, max-HP floor,
  and a missing-HP cap only. Conditional, weather, delayed, status, and
  target-dependent healing remain unavailable.
- The documentation completion commit and regression baseline must be recorded
  only after validation. The next proposed feature is v13.14 fixed damage.

## v13.14 Fixed Damage

- Keep fixed-damage support on its explicit allowlist. Do not add OHKO,
  Counter-family, ability/status overrides, or normal damage modifiers.

## v13.15 HP-Based Special Damage

- Endeavor and Final Gambit require exact confirmed current HP for both sides;
  Final Gambit's self-faint is not recoil and has no replacement-turn logic.

## v13.11 Multi-Hit

- Generic multi-hit totals use independent rolls only; do not add Skill Link,
  Loaded Dice, per-hit events, hit chance, or drain/recoil integration.

## v13.10 Deterministic Drain And Recoil

- Ordinary move `meta.drain` uses actual capped damage rolls only. Do not add
  Big Root, Liquid Ooze, Rock Head, Life Orb, Shell Bell, hit chance, expected
  values, or between-turn effects.
- Exceptional recoil/crash moves remain unavailable rather than inferred.

## v13.9 Deterministic Hit Chance

- Hit chance is selected move accuracy plus user-confirmed accuracy/evasion
  stages only. Missing metadata remains unavailable; do not infer always-hit
  from a null accuracy field.
- Keep hit chance independent from damage, immunity, KO, expected damage, and
  all ability/item/weather/OHKO/special-rule mechanics.

## v13.8 Priority And Field-Aware Move Order

- The deterministic result is priority/stage-Speed/Tailwind/Trick Room only.
  Never infer opponent priority zero, ability/item modifiers, random tie
  winners, duration, expiry, move success, switching, or a full turn result.
- Explicit UI opponent selection is the only production opponent-move source;
  absent priority stays unavailable. Priority brackets always precede Speed.

## v13.7 Trusted Battle Format And Screens

- Limited-context UI state now supplies only an explicit user-confirmed
  `singles`/`doubles` format to the normalized payload. Do not infer it from
  team size, active slots, or layout; gate-off retains the UI snapshot but
  emits no raw or normalized format context.
- Reflect/Light Screen/Aurora Veil use one defender-side reduction only:
  singles `1/2`, doubles `2/3`. Missing format with an applicable screen is
  unavailable; burn/weather without a screen still calculate normally.
- Structured readback requires the exact battle-format and, when applied,
  screen-modifier lines. Do not add Infiltrator, Brick Break, Psychic Fangs,
  critical bypass, Light Clay, timing, persistence, ability, or item claims.

## v13.4 HP/KO Boundary

- Exact current/max HP is separate from percent and final-stat HP. The v13.4
  result is only independent v13.3 damage rolls against a current snapshot.
- Do not add survival, recovery, chip, accuracy, critical, or turn-transition
mechanics without a separately verified contract.
- A trusted zero current HP means already fainted, not guaranteed future KO;
  retain percentage only and keep KO assessment not applicable.

## v13.3 Base-Damage-Only Boundary

- v13.3 damage ranges use direct final stats plus current stages and selected
  move metadata only; they do not merge with legacy `stat_profiles` damage.
- Follow-up work must not add STAB, types, critical, item, ability, field, or
  KO semantics without an explicit separately verified contract.

## v13.2 Stage-Only Effective Stat Boundary

- `deterministic_calculation_context` is intentionally separate from legacy
  `stat_profiles`, `speed_context`, and all damage/KO calculations.
- Its Speed comparison is stage-only, never final action order. Future work may
  connect verified modifiers only with explicit activation/applicability rules.

## v13.1 Final Battle Stat Boundary

- Direct user-confirmed final stats are stage-unmodified context only and are
  separate from current stages. The adapter exposes both inputs without applying
  a multiplier or calculating outcomes.
- v13.2 should evaluate a safe deterministic calculation integration boundary;
  do not infer EVs, IVs, nature, level, modifiers, damage, or order.

## v12 Phase Closed

- v12 trusted-context integration is closed after the combined offline
  production-path regression. Do not create further v12.xx feature work.
- Existing actual evidence remains v12.71 structured condition/item limited
  sample and v12.77 combined ability stable smoke. Stat-stage and field state
  remain offline-only.
- Next target: v13 **Final Battle Stat Input and Calculation Boundary**. Keep
  deterministic calculation inputs separate from LLM inference and preserve all
  v12 source, gate, acknowledgement, and forbidden-boundary contracts.

## v12.79 Current Field State Context

- Current field state is now a separately validated user-confirmed snapshot:
  weather, terrain, global effects, and side effects. It is gated with the
  existing limited-context switch and rendered through structured trusted
  acknowledgement entries.
- Do not connect it to damage/speed calculations or infer start/end timing,
  duration, a source move/ability/item, resolved mechanics, exact outcomes, or
  final order. The old `field_profiles` calculation path remains separate.
- Offline status: `COMPLETE - CURRENT FIELD STATE END-TO-END GREEN`; no actual
  provider calls were made.

## v12.78 Current Stat Stage Context

- Current stat stages are now user-confirmed limited trusted context only:
  one `(side, stat)` integer -6..+6 entry, no inferred source or resolved
  calculation meaning. The UI, payload, prompt, acknowledgement parser, and
  CLI evaluator are connected behind the existing limited-context gate.
- It is intentionally not connected to damage/speed calculations, ability/item
  inference, or stage-change event resolution. Do not add an actual provider
  call without separate approval.
- Offline status: `COMPLETE - READY FOR OPTIONAL STAT-STAGE ACTUAL SMOKE`.

## v12.77 Ability Structured Smoke

- The fixed `current-condition-ability-item-event` CLI fixture is now covered
  by production-normalization and subprocess contracts. It is allowlisted and
  single-attempt only; it does not accept arbitrary ability input.
- Three independent `gemini-2.5-flash` attempts completed with sanitized
  provider success, available responses, and semantic PASS. Final status:
  `PASS - STABLE` for this fixed fixture.
- Evidence is limited to user-confirmed ability identity attribution and the
  guarded condition/item-event coexistence contract. Do not use it to infer
  abilities from species, activation, suppression, resolved effects, damage,
  or order. New actual calls still require explicit approval.

## v12.76 Ability Smoke Block

- The v12.76 pre-call contracts passed, including full regression:
  `1888 passed, 2 deselected`. No provider call was made.
- Status is `BLOCKED - ABILITY SMOKE FIXTURE UNAVAILABLE`: the sanctioned
  single-attempt CLI only has `current-condition-item-event`, not a fixed
  ability-bearing fixture. Running it would omit the required ability entries
  and cannot establish the v12.76 acknowledgement exact set.
- Do not substitute arbitrary input, modify the CLI during an actual-smoke
  task, or make a credential/provider call. A separately approved offline CLI
  fixture-contract task is the next safe prerequisite.

## v12.75 Known Ability End-to-End Integration

- `ability_context.current_abilities` is now live only behind the existing
  limited-context gate. It carries user-confirmed current identities, not
  species possibilities or observed/resolved ability mechanics.
- Structured advice must acknowledge each entry as `Current ability | side |
  ability`; the deterministic parser exact-compares normalized payload entries
  across condition, ability, and observed item-event categories.
- The CLI semantic evaluator now applies the same ability acknowledgement
  validation and rejects unknown-ability inference plus activation,
  suppression/replacement/copy/restoration, resolved, exact, RNG, and order
  claims. Schema and exit codes remain unchanged.
- Offline matrix and normal UI-response contracts are green. Status:
  `COMPLETE - READY FOR ABILITY ACTUAL SMOKE`. This status is not approval for
  a provider call; require explicit new approval and retain the single-attempt
  CLI discipline.

## v12.74 Known Ability UI/Payload Foundation

- The UI now stores one user-confirmed current ability per self/opponent side,
  with editable validated input, explicit `unknown`, summary count/readback,
  replacement on Apply, and explicit Clear. `none` and candidate-list input are
  rejected; Cancel/invalid input preserve state.
- The limited-context gate controls battle-input and intermediate
  `ability_context.current_abilities` construction. Off preserves session state
  but omits it from battle input; on reuses the existing normalization helper.
- Ability remains prompt-isolated: raw confirmations and `ability_context` are
  removed before prompt serialization. Do not add an ability guard, natural
  language readback, `[Trusted Context]` ability line, CLI evaluator rule, or
  actual provider call without a separate approved integration task.

## v12.73 Known Ability Source Foundation

- Current ability is now a validation-only source boundary. The sole accepted
  source is `user_confirmed_current_ability` with `status=user_confirmed` and a
  normalized self/opponent identity; the helper adds `confidence=known`.
- Species/cache possible abilities, hidden abilities, common sets, selected
  species defaults, interaction inference, future source names, and all
  activation/suppression/replacement/resolved/post-turn claims remain rejected.
- `unknown` is an allowed explicit identity; `none` is rejected because it
  would conflate absence with suppression/removal state.
- No ability UI/session state, payload/prompt mapping, or structured
  acknowledgement line exists. Future integration requires a separate design
  and contract task; no provider call is authorized by this foundation.

## v12.72 Structured Acknowledgement Matrix Status

- Offline matrix coverage now locks condition-plus-item-event, condition-only,
  `none`, `unknown`, item-only, multiple-event, absent, and limited-context-off
  combinations through normalized payload-derived expected entries.
- Exact-set validation rejects missing, extra, duplicate, swapped, category,
  identity, and event-type changes. Normal UI advice preserves the complete
  structured response while CLI JSON remains CLI-only.
- Phase status: `STRUCTURED ACKNOWLEDGEMENT PHASE: READY - LIMITED ACTUAL
  EVIDENCE`. This combines v12.72 offline green with v12.71's 2/2 assessable
  PASS evidence. Do not recover the unavailable attempt or make another
  provider call without new explicit approval.

## v12.71 Structured Trusted-Context Smoke Closure

- The v12.70 structured acknowledgement path was smoke-tested with the fixed
  self-burn, opponent-unknown, and opponent-Focus-Sash fixture.
- Three approved `gemini-2.5-flash` CLI attempts were initiated without retry,
  fallback, second provider, or Vertex AI. Two parseable sanitized results
  passed the payload-derived trusted-context exact-set, advice-presence, and
  forbidden-claim checks.
- One outer execution result was unavailable and must not be reconstructed from
  logs or raw response data. No replacement provider call was made.
- Final classification: `PASS - LIMITED SAMPLE` (2 semantic PASS, 0 semantic
  FAIL, 1 response unavailable). Future provider calls require new explicit
  approval; do not treat this as permission for an automatic follow-up smoke.

This document is a copy-paste-ready prompt for the next T3 session. It preserves the v2.5 Developer API Prepay recovery verification results, the v3.2 item-context verification closure, the v3.4 item context guard registry cleanup, the v4.1-v4.9 TurnSnapshot phase closure, the v5.0 Minimal Turn Engine MVP design, the v5.1 Turn Event contract implementation, the v5.2 item-context-to-TurnEvent mapping design, the v5.3 helper-level mapper implementation, the v5.4 mapper smoke / fixture coverage expansion, the v5.5 TurnPipelineResult fixture smoke, the v5.6 TurnPipeline debug dry-run, the v5.7 TurnPipeline payload exposure design, the v5.8 optional TurnPipeline payload adapter, the v5.9 TurnPipeline prompt/contract guard, the v6.0 Minimal TurnPipeline integration design, the v6.1 explicit TurnPipeline generation adapter, the v6.2 explicit TurnPipeline payload smoke, the v6.3 TurnPipeline UI/advice flow integration design, the v6.4 explicit TurnPipeline advice payload builder smoke, the v6.5 explicit TurnPipeline advice flow integration design, the v6.6 explicit TurnPipeline advice-flow dry-run, the v6.7 TurnPipeline advice-flow closure / stability report, the v6.8 Payload Snapshot Lockdown, the v6.9 Controlled Gemini Smoke Design, the v6.10 Controlled Gemini Smoke Execution, the v6.11 Controlled Gemini Smoke Closure / Next UI Exposure Design, the v6.12 Prompt / UX Copy Design, the v6.13 Prompt Copy Test Fixtures, the v6.14 UI Exposure Design, the v6.15 Offline End-to-End Advice Fixture, the v6.16 UI Exposure Test Plan, the v6.17 Controlled UI Mock Smoke, the v6.18 UI Dev Flag Implementation, the v6.19 UI Dev Flag Smoke / Manual QA, the v6.20 Controlled UI Gemini Smoke, the v6.21 TurnPipeline UI Phase Closure, the v7.0 Turn Engine Roadmap / Scope Split, the v7.1 Deterministic Turn Order Context Design, the v7.2 Turn Order Context Payload Contract, the v7.3 Deterministic Turn Order Context Helper, the v7.4 Turn Order Context Payload Adapter, the v7.5 Turn Order Context Prompt Integration Design, the v7.6 Turn Order Context Prompt Contract Tests, the v7.7 Turn Order Context Prompt Integration, the v7.8 Turn Order Context Offline Advice Fixture, the v7.9 UI / Flag Integration Design, the v7.10 UI Flag Enables Turn Order Context, the v7.11 UI Flag Offline E2E Fixture, the v7.12 Controlled UI Gemini Smoke Design, the v7.13 Controlled UI Gemini Smoke, the v7.14 Smoke Harness Prompt Guard Triage, the v7.15 Controlled UI Gemini Smoke Harness Alignment, the v7.16 Controlled UI Gemini Smoke Retry, the v7.17 Turn Order UI Integration Closure, the v8.0 Battle State / Opponent Move Context Expansion Design, the v8.1 Opponent Move Context Payload Contract, the v8.2 Opponent Move Context Helper, the v8.3 Opponent Move Context Payload Adapter, the v8.4 Opponent Move Prompt Guard, the v8.5 Opponent Move Offline Advice Fixture, the v8.6 Controlled Gemini Smoke Design, the v8.7 Controlled Gemini Smoke, the v8.8 Opponent Move Context Closure, the v9.0 Opponent Move UI / Source Integration Design, the v9.1 Opponent Move UI Source Integration, the v9.2 Opponent Move UI Integration Offline E2E, the v9.3 Opponent Move UI Copy / Tooltip Polish, the v9.4 Opponent Move UI Integration Closure, the v10.0 Battle State Context Design, the v10.1 Battle State Context Payload Contract, the v10.2 Battle State Context Helper, the v10.3 Battle State Context Payload Adapter, the v10.4 Battle State Context Prompt Guard, and the v10.5 Battle State Context Offline Advice Fixture.

Update after v2.5:

- Developer API smoke recovered: `AVAILABLE`.
- Provider used: `gemini_developer_api`.
- Endpoint family used: `generativelanguage.googleapis.com`.
- Vertex AI was not used.
- Focus Band actual Gemini verification: PASS.
- Quick Claw actual Gemini verification: PASS.
- Light Ball actual Gemini verification: PASS after v3.1.1.
- Chilan Berry actual Gemini verification: PASS after v2.7.1.
- v2.6 applied a narrow wording polish for Light Ball and Chilan Berry.
- v2.6.1 ran actual Gemini rechecks for Light Ball and Chilan Berry only.
- v2.7 added a required-mention guard for visible `available=true` item contexts.
- v2.7.1 ran actual Gemini rechecks for Light Ball and Chilan Berry only.
- v2.8 added a narrower Light Ball-specific no-item residue guard.
- v2.8.1 ran a Light Ball-only actual Gemini verification after that guard.
- v3.1 integrated eligible Pikachu + Light Ball into advisor damage estimates.
- v3.1.1 verified Light Ball actual Gemini wording as PASS.
- v3.2 closed the original item-context pending verification queue.
- v3.4 centralized available item context mention labels, item-specific guard text, and forbidden wording metadata in `ADVICE_ITEM_CONTEXT_GUARD_METADATA`.
- v4.1 added `core.turn_state` with `PokemonBattleSlot`, `BattleState`, `TurnInput`, and `TurnSnapshot`.
- v4.3 added optional top-level `turn_snapshot` payload adapter support.
- v4.5 added `llm.advisor_turn_snapshot` and connected UI-selected `battle_input` to optional `TurnSnapshot` payload context with fallback.
- v4.6 verified the TurnSnapshot payload smoke path without actual Gemini calls.
- v4.7 documented the complete TurnSnapshot UI flow and handoff boundaries.
- v4.8 added a local TurnSnapshot dry-run/debug report script and static sample report without actual Gemini calls.
- v4.9 closed the TurnSnapshot phase and prepared v5.0 Minimal Turn Engine MVP Design.
- v5.0 designed a Minimal Turn Engine MVP around `TurnSnapshot` input state, `TurnEvent` candidates, and `TurnPipelineResult` planning output.
- v5.1 added `core.turn_event` with serializable validated `TurnEvent` and `TurnPipelineResult` dataclass contracts.
- v5.2 designed mapping from existing item/context payload surfaces into `TurnEvent` stage/status/certainty candidates without runtime payload integration.
- v5.3 added `llm.advisor_turn_events.build_turn_events_from_advice_payload(...)` for available Light Ball, Quick Claw, Focus Band / Focus Sash, and Chilan Berry context mapping without advisor or LLM payload integration.
- v5.4 expanded mapper fixture coverage for unavailable/blocked/deferred/unknown/malformed contexts, stable ordering, and safe non-overstated event wording.
- v5.5 added `llm.advisor_turn_events.build_turn_pipeline_result_from_advice_payload(...)` as a fixture/debug helper that bundles mapper events into `TurnPipelineResult` without runtime payload integration.
- v5.6 added `scripts/spike_turn_pipeline_debug.py` and `docs/debug_turn_pipeline_sample_v5.6.md` for local TurnPipelineResult inspection without actual Gemini or Vertex AI calls.
- v5.7 designed optional payload exposure for `TurnPipelineResult`, recommending a default-off top-level `turn_pipeline` adapter with strict limitations and no automatic advisor-client generation.
- v5.8 added explicit-only optional top-level `turn_pipeline` payload adapter support while keeping runtime advisor flow from auto-generating `TurnPipelineResult`.
- v5.9 strengthened `turn_pipeline` prompt and contract guardrails so candidate events are not treated as resolved outcomes or replacements for `damage_estimate`, `ko_context`, or existing item contexts.
- v6.0 designed the next integration step as an explicit/default-off generation adapter, not automatic advisor-client generation.
- v6.1 added `build_optional_turn_pipeline_for_advice_payload(...)`, which returns `None` by default and only builds a limited `TurnPipelineResult` when `enable_turn_pipeline=True`.
- v6.2 verified the manual helper-plus-payload-adapter smoke path while keeping advisor-client and UI flow automatic generation disabled.
- v6.3 designed UI/advice-flow integration and recommended keeping v6.4 at explicit payload-builder/helper smoke level, without UI automatic connection.
- v6.4 strengthened explicit payload-builder smoke coverage for disabled/default paths, enabled limited pipeline generation, manual payload insertion, prompt guard behavior, and existing context preservation.
- v6.5 designed explicit advice-flow integration options and recommended v6.6 as a default-off no-actual-Gemini dry-run before any UI checkbox or automatic generation.
- v6.6 added a default-off `enable_turn_pipeline` dry-run flag near `run_ui_selected_advice(...)`, verified default and explicit paths with mocked `call_gemini`, and still did not add UI checkbox or user-facing automatic TurnPipeline enablement.
- v6.7 closed the TurnPipeline advice-flow dry-run phase, documented the current safety boundary, recorded timing-sensitive perf instability as a known issue, and recommended v6.8 Payload Snapshot Lockdown before any controlled Gemini smoke or UI checkbox.
- v6.8 locked default/off/on TurnPipeline payload and prompt shapes with plain pytest dictionary assertions, without external snapshot dependencies or actual Gemini calls.
- v6.9 designed a Controlled Gemini Smoke strategy: explicit-on TurnPipeline fixture only, maximum 1 actual Gemini call, no retry, stop on 429 / `RESOURCE_EXHAUSTED` / API key / billing / routing errors, no Vertex AI, and T1 explicit approval required before execution.
- v6.10 executed exactly 1 controlled actual Gemini smoke on the explicit-on TurnPipeline fixture. Result: PASS. The response kept candidate events non-resolved, did not claim full simulation, item consumption, exact post-turn HP, speed tie/RNG/exact trigger resolution, or damage/KO primitive override.
- v6.11 closed the controlled smoke PASS result, recorded the current safety boundary, and recommended v6.12 Prompt / UX Copy Design or v6.12 UI Exposure Design before any UI checkbox implementation.
- v6.12 designed Prompt / UX copy for future TurnPipeline exposure. Developer docs keep `TurnPipeline`; Korean user-facing copy should prefer `턴 이벤트 후보` / `제한적 턴 판단 보조`; English copy should prefer `Candidate Turn Events` / `Limited Turn Context`. Recommended next is v6.13 Prompt Copy Test Fixtures, with v6.13 UI Exposure Design as the safe alternative.
- v6.13 locked TurnPipeline prompt copy with fixture tests. No-`turn_pipeline` prompts omit guard/copy anchors, explicit `turn_pipeline` prompts include limited/candidate/not-resolved anchors, resolved-outcome phrases stay forbidden, and UI copy labels remain design-only.
- v6.14 designed future UI exposure. A visible `LLMAdvicePanel` checkbox is not recommended as the first step; a settings/developer dev flag or continued internal flag is safer. Default remains off, existing advice button behavior remains unchanged, and UI Dev Flag Implementation requires explicit T1 approval.
- v6.15 added an offline end-to-end advice fixture. `run_ui_selected_advice(...)` is tested with mocked Gemini and in-memory token logging for both default-off and explicit-on paths; explicit-on includes limited `turn_pipeline` and guard wording while preserving existing contexts.
- v6.16 documented the UI exposure test plan before any UI implementation. It defines default-off regression, UI flag off/on smoke, no-call guarantee, copy visibility, rollback/safety switch, and implementation entry criteria. Recommended next is v6.17 Controlled UI Mock Smoke; UI Dev Flag Implementation requires explicit T1 approval.
- v6.17 added a controlled UI mock smoke without implementing UI. A fake UI state verifies omitted/default, flag-off, and flag-on advice paths with mocked Gemini and in-memory logging; flag-on includes limited `turn_pipeline` and enabled status copy while `LLMAdvicePanel` remains unchanged.
- v6.18 added the default-off dev-only UI flag. `LLMAdvicePanel` now has a `턴 이벤트 후보 포함` checkbox with limited-context tooltip and enabled status copy. It starts unchecked, has no persisted auto-enable, toggling alone does not call Gemini, and `MainWindow` passes the checked state into `LLMAdviceWorker` only when the existing advice button is pressed.
- v6.19 verified the UI dev flag with offscreen PySide smoke / QA. The checkbox appears below the advice button, defaults unchecked, has the expected tooltip/status copy, toggle emits no advice request, and existing mocked tests cover off/on advice-flow behavior. No actual Gemini, Vertex AI, or provider call was made.
- v6.20 ran one controlled actual Gemini smoke through the UI dev flag path. Result: PASS. There was exactly 1 call, no retry, no Vertex AI call, no stop condition, and Gemini kept candidate wording without full simulation, item consumption, exact post-turn HP, RNG, speed tie, or exact trigger resolution claims.
- v6.21 closed the TurnPipeline UI phase. The current implementation is a default-off dev UI flag for limited candidate turn-event context, not a full Turn Engine. The recommended next major step is v7.0 Turn Engine Roadmap / Scope Split, with v7.0 Battle State / Opponent Move Context Expansion as the safe alternative.
- v7.0 split the future full Turn Engine roadmap into staged scopes: deterministic turn order context, deterministic damage application preview, item trigger candidate layer, resolved turn simulation prototype, and post-turn state update. No implementation was added. Recommended next is v7.1 Deterministic Turn Order Context Design.
- v7.1 designed deterministic turn order context as limited planning context. It covers priority, Speed relation, unknown handling, tie candidates, candidate modifiers, and unsupported boundaries without implementing resolved order, speed tie/RNG resolution, item consumption, HP update, or opponent set inference. Recommended next is v7.2 Turn Order Context Payload Contract, with v7.2 Deterministic Turn Order Context Helper as the faster alternative.
- v7.2 locked the fixture-level `turn_order_context` payload contract before helper implementation. Tests now cover allowed values, unresolved candidate modifiers, required unsupported boundaries, forbidden resolved-outcome fields, and prompt safety copy anchors. No runtime adapter or helper was added.
- v7.3 added `build_deterministic_turn_order_context(...)` as a standalone helper. It covers base Speed, confirmed final Speed, known priority, unknown handling, and unresolved candidate modifiers without connecting to runtime payload, prompt, UI, Gemini, or full Turn Engine behavior.
- v7.4 added an optional explicit-only `turn_order_context` payload adapter. `build_ui_advice_payload(..., turn_order_context=..., enable_turn_order_context=True)` can add top-level `turn_order_context`; omitted/disabled paths preserve the previous shape. The adapter validates v7.2 contract values, unresolved candidate modifiers, unsupported boundaries, and forbidden resolved-outcome fields. No prompt integration, UI auto-connection, Gemini call, or full Turn Engine behavior was added.
- v7.5 designed `turn_order_context` prompt integration. Recommended placement is the optional-context guard area near `turn_pipeline`; safety wording should say it is limited planning context, not a resolved move order, and must not claim exact final order, speed tie resolution, RNG activation, item consumption, or post-turn HP. Recommended next is v7.6 Turn Order Context Prompt Contract Tests.
- v7.6 locked `turn_order_context` prompt guard/copy tests with `_build_turn_order_context_prompt_guard(payload)`. Default-off guard absence, explicit-on guard wording, forbidden positive phrase anchors, and coexistence with the `turn_pipeline` guard are covered. The helper is not yet wired into `_build_ui_selected_prompt(...)`.
- v7.7 wired the `turn_order_context` guard into `_build_ui_selected_prompt(...)` behind explicit keyword-only inputs. Default/off prompts stay unchanged, explicit-on prompts include the guard and top-level payload JSON context, and `turn_pipeline` coexistence stays covered. No UI auto-connection, Gemini call, or full Turn Engine behavior was added.
- v7.8 added an offline advice fixture for the explicit turn-order context path. It uses mocked `call_gemini` and `_log_advisor_call`, covers default-off, explicit-on, and `turn_pipeline` coexistence prompts, and verifies mocked responses avoid resolved-order wording. No provider call was made.
- v7.9 designed UI / flag integration. Recommended Option C: keep one default-off developer checkbox, clarify its scope in tooltip/status copy, and in the next implementation make the checked state enable both `turn_pipeline` and `turn_order_context` only when valid source contexts exist. No UI behavior was changed and no Gemini call was made.
- v7.10 connected the existing default-off developer checkbox to `turn_order_context`. Checked now maps to both `enable_turn_pipeline=True` and `enable_turn_order_context=True`; unchecked maps both false. Runtime turn-order source extraction is limited to base Speed, user-confirmed final Speed, and unresolved Quick Claw candidate modifier context. No new checkbox, saved auto-enable, Gemini call, or full Turn Engine behavior was added.
- v7.11 verified the UI flag path offline from `LLMAdvicePanel` checkbox state through mocked advice. Unchecked prompts omit both optional contexts and guards; checked prompts include both optional contexts and guards when source context exists. Checkbox toggle emits no advice request and makes no provider call. Mocked responses avoid resolved-order wording.
- v7.12 designed the controlled UI Gemini smoke for the combined `turn_pipeline` + `turn_order_context` checkbox-on path. The design requires pre-call guard checks, maximum 1 actual Gemini call, no retry, stop on provider/auth/billing/quota/routing/timeout errors, PASS/PARTIAL/FAIL/BLOCKED classification, and safe recording without token log or secret contents.
- v7.13 attempted the controlled UI Gemini smoke but classified it as `BLOCKED` before any provider call. Pre-check passed, but the local smoke harness raised on strict prompt equality between the prechecked prompt and provider wrapper prompt. Actual Gemini call count was 0, retry count was 0, and no Vertex AI call was made.
- v7.14 triaged the v7.13 prompt equality guard. Cause: dynamic field difference. The direct pre-check prompt omitted `turn_snapshot`, while `run_ui_selected_advice(...)` automatically built and included it. Safety anchors for `turn_pipeline`, `turn_order_context`, exact order, speed tie, RNG, item consumption, post-turn HP, and full simulation remained present. Recommended next is harness alignment with focused safety anchors before any provider retry.
- v7.15 aligned the controlled UI Gemini smoke harness without provider calls. It added test-only provider-path prompt capture with monkeypatched `call_gemini`, accepts harmless auto-built `turn_snapshot`, keeps offline exact prompt checks intact, and gates future smoke calls on focused safety anchors plus structural optional-context checks. Quick Claw activation certainty remains forbidden.
- v7.16 retried the controlled UI Gemini smoke after T1 approval. Pre-check, focused guard, and structural summary passed. Exactly 1 Gemini call was made, retry count was 0, Vertex AI was not used, and the result was PASS. The response treated optional contexts as limited planning information and did not claim exact final move order, speed tie resolution, Quick Claw activation certainty, item consumption, post-turn HP, or full turn simulation.
- v7.17 closed the Turn Order UI Integration phase. The current feature is a default-off UI checkbox that can include limited `turn_pipeline` and `turn_order_context` context when sources exist, with prompt guards and a controlled UI Gemini smoke PASS. The recommended next major phase is v8.0 Battle State / Opponent Move Context Expansion Design.
- v8.0 designed Battle State / Opponent Move Context Expansion. It recommends adding a fixture-level `opponent_move_context` contract first, with known user-confirmed moves separated from possible/unconfirmed candidate moves, no hidden moveset inference, no opponent set inference, and no full Turn Engine.
- v8.1 locked the fixture-level `opponent_move_context` payload contract. It separates known user-confirmed moves from possible/unconfirmed candidate moves, restricts selected opponent move status to unknown or explicit, rejects hidden inference/resolved fields, and records future prompt safety wording. No runtime helper, adapter, prompt integration, UI change, or Gemini call was added.
- v8.2 added `llm.advisor_opponent_move_context.build_opponent_move_context(...)`, a source-bound helper that normalizes trusted known moves, unconfirmed candidate moves, explicit selected moves, and positive-priority candidates without hidden moveset, selected move, species/common-set, or meta inference. No payload adapter, prompt integration, UI change, or Gemini call was added.
- v8.3 added an explicit/default-off `opponent_move_context` payload adapter. `build_ui_advice_payload(..., opponent_move_context=..., enable_opponent_move_context=True)` inserts valid non-empty context, omits disabled/none/empty contexts, rejects invalid or forbidden fields, and coexists with `turn_pipeline` and `turn_order_context`. No prompt guard, prompt integration, UI/source extraction, or Gemini call was added.
- v8.4 added `_build_opponent_move_context_prompt_guard(payload)` and wired it into `_build_ui_selected_prompt(...)` after the turn-order guard. The guard appears only when top-level `opponent_move_context` is present and tells the LLM not to treat known moves as selected moves unless explicit, not to treat candidate moves as confirmed or selected, and not to infer hidden movesets, opponent sets, selected moves, EV/IV/nature, hidden item, weather, terrain, boosts, RNG, item consumption, or post-turn HP. No UI/source extraction or Gemini call was added.
- v8.5 added a mocked offline advice fixture for `opponent_move_context`. It monkeypatches `call_gemini` and `_log_advisor_call`, verifies default omission, explicit payload + prompt guard inclusion, coexistence with `turn_pipeline` and `turn_order_context`, and mocked response wording that keeps known Thunderbolt non-selected, Quick Attack candidate-only, and avoids hidden moveset/item/EV-IV-nature/RNG/item-consumption/post-turn-HP inference. No actual Gemini, Vertex AI, network, UI/source extraction, or UI checkbox change was added.
- v8.6 designed the controlled Gemini smoke for `opponent_move_context`. The design requires payload + guard pre-checks, known-not-selected and candidate-not-confirmed/selected anchors, maximum 1 actual Gemini call, retry count 0, stop on provider/auth/billing/quota/routing/timeout/exception issues, PASS/PARTIAL/FAIL/BLOCKED classification, and safe recording without raw response, token log, secret, credential, or billing details. No actual Gemini, Vertex AI, network, UI/source extraction, or UI checkbox change was added.
- v8.7 executed the controlled Gemini smoke for `opponent_move_context` after T1 approval. Pre-check passed, exactly 1 Gemini call was made, retry count was 0, Vertex AI was not used, and the result was PASS. The response kept known move data non-selected, candidate move data unconfirmed/unselected, did not infer selected opponent move while unknown, and did not claim hidden moveset, opponent set, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, post-turn HP, or full turn resolution.
- v8.8 closed the Opponent Move Context phase. No code, UI, prompt, payload, or provider behavior changed; the next recommended phase is v9.0 Opponent Move UI/Source Integration Design.
- v9.0 designed opponent move UI/source integration. It recommends reusing the existing default-off limited-context developer checkbox for the first implementation, deriving `opponent_move_context` only from existing explicit/visible `opponent_moves` data, omitting empty context, and keeping checkbox toggles provider-call-free.
- v9.1 connected the existing default-off limited-context UI developer checkbox to `opponent_move_context`. Checked now maps to `enable_turn_pipeline=True`, `enable_turn_order_context=True`, and `enable_opponent_move_context=True`; unchecked maps all three false. Runtime source extraction reads only existing `opponent_moves`, converts UI-visible opponent moves to `visible_ui` candidate moves, keeps candidates unconfirmed/unselected, keeps selected opponent move unknown, and makes no provider call.
- v9.2 verified the existing checkbox path with focused offline E2E tests. The tests cover default unchecked state, toggle no-call behavior, off-path omission of all optional contexts and guards, on-path coexistence of `turn_pipeline`, `turn_order_context`, and `opponent_move_context`, visible UI moves as unconfirmed/unselected `visible_ui` candidates, empty opponent-source omission, and mocked-provider-only advice flow.
- v9.3 polished the existing checkbox copy without behavior changes. The label is `제한 컨텍스트 포함`; tooltip/status copy now explains that the checkbox includes turn event candidates, turn-order helper context, and UI-visible opponent move candidates while staying non-final and non-inferential. Tests lock candidate wording and forbid confirmed-result / selected-move / hidden-inference implications.
- v9.4 closed the v9.0-v9.3 Opponent Move UI Integration phase as documentation only. The closure records current checkbox behavior, UI-visible move handling, candidate/known/selected boundaries, provider no-call coverage, known limitations, and recommends v10.0 Battle State Context Design next without an actual Gemini call.
- v10.0 designed a future `battle_state_context` without implementation. The design proposes source-tagged visible/explicit state fields for active Pokemon and field state, keeps unknown fields unknown, forbids hidden state and damage reverse inference, defines future prompt guard needs, and recommends v10.1 Battle State Context Payload Contract next.
- v10.1 locked the fixture-level `battle_state_context` payload contract with `unknown` / `limited` confidence only, required active/field sections, explicit unknown envelopes, allowed source validation, forbidden source rejection, forbidden hidden/resolved field rejection, and relationship boundaries.
- v10.2 added `llm.advisor_battle_state_context.build_battle_state_context(...)`, a standalone helper that normalizes visible or explicit battle-state facts into the v10.1 shape while keeping forbidden sources unknown/omitted and avoiding adapter, prompt, UI, provider, hidden inference, or full Turn Engine behavior.
- v10.3 added explicit/default-off payload adapter support for caller-provided `battle_state_context`. Valid non-empty context can be inserted as top-level payload context; default, disabled, `None`, `{}`, and unknown-only helper output are omitted. The adapter validates shape/source/forbidden fields, coexists with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`, and still does not add prompt guard, UI/source integration, provider call, hidden-state inference, or full Turn Engine behavior.
- v10.4 added `battle_state_context` prompt guard integration. Prompts without top-level `battle_state_context` omit the guard; prompts with explicit valid context include serialized context and guard wording to keep unknown fields unknown, forbid hidden-state inference and damage/KO reverse inference, and forbid resolved simulation claims such as post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, or full turn outcome.
- v10.5 added an offline mocked advice fixture for explicit `battle_state_context`. It verifies payload preservation, prompt guard preservation, forbidden source/field absence, coexistence with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`, and mocked response safety without actual provider, Vertex AI, or network calls.
- v10.6 inventoried current UI sources for future `battle_state_context` UI integration. Self/opponent species and HP percent are visible UI facts that can be normalized later; user-confirmed item profiles require a v10.7 design decision; status, boosts, weather, terrain, screens, hazards, room, and known conditions have no current explicit UI source and must remain unknown.
- v10.7 designed future `battle_state_context` UI integration. The existing limited-context checkbox should remain default-off, unchecked should omit battle state, checked should enable `enable_battle_state_context=True` with the other limited context flags, and the first source adapter should extract only visible self/opponent species and HP percent. Item mapping is deferred; status, boosts, field state, and known conditions remain unknown.
- v10.8 added `build_battle_state_context_from_ui_selected_state(...)` as a narrow adapter from UI-selected `battle_input` to `battle_state_context`. It extracts only self/opponent species and HP percent as `visible_ui`, leaves status/boosts/item/field/known conditions unknown, and does not connect the checkbox or payload call flow.
- v10.9 connected the existing limited-context checkbox path to `battle_state_context`. Checked now enables `enable_battle_state_context=True` with the other limited contexts and uses the v10.8 adapter; unchecked omits battle state and its guard. No new checkbox, UI copy change, prompt guard wording change, provider call, hidden inference, or full Turn Engine behavior was added.
- v10.10 updated the existing limited-context checkbox copy to mention the current Pokemon/HP snapshot alongside candidate events, turn-order helper information, and opponent move candidates. The label remains `제한 컨텍스트 포함`; behavior, default state, payload flow, source adapter, and prompt guard wording are unchanged.
- v10.11 added an offline UI-selected smoke for the limited-context checkbox path. It verifies off omits `battle_state_context` and guard, on includes `battle_state_context` with visible self/opponent species and HP plus the existing guard, and all provider interaction is monkeypatched.
- v10.12 closed the battle-state context UI phase. The current supported UI path is limited to visible self/opponent species and HP percent through the existing limited-context checkbox; status, boosts, item, field, and known conditions remain unknown or `[]`. Actual Gemini smoke for this UI path has not been run.
- v11.0 designed the controlled Battle State UI Gemini smoke. It was design-only: no actual call, retry, Vertex AI call, or network call. Future execution required explicit T1 approval, exactly one Gemini call, zero retries, pre-call payload/guard checks, and sanitized token/cost reporting only.
- v11.1 executed the controlled Battle State UI Gemini smoke after T1 approval. Exactly one Gemini call was made with `gemini-2.5-flash`, retry count was zero, Vertex AI was not used, payload/prompt boundaries passed, the response scanner found no hidden-state certainty or resolved-outcome claim, and sanitized token/cost summary was recorded without raw token-log output.
- v11.2 closed the Battle State Context actual smoke phase as PASS. It records the v11.1 one-call/no-retry audit, payload/prompt/response boundary PASS, sanitized token/cost summary, local post-call reporting script issue, and the requirement that `logs/token_usage.jsonl` and `config/env.example` remain uncommitted and unreset.
- v11.3 designed the user-confirmed item boundary for future `battle_state_context.item` support. It keeps current runtime behavior unchanged, treats self/opponent item as known only from direct `user_confirmed` or explicitly allowed `explicit_input` sources, keeps opponent item hidden/unknown by default, and treats legality gate plus item contexts as validation/context rather than source of truth.
- v11.4 locked user-confirmed item contract/helper behavior. `battle_state_context.item` known sources are limited to `user_confirmed` and `explicit_input`; `visible_ui`, `calculated_from_visible`, legality-gate, resist-berry, context-derived, hidden, usage/meta/common-set, and damage-reverse item sources stay unknown or are rejected at payload validation. UI item integration remains disconnected.
- v11.5 designed the future user-confirmed item source adapter. Existing UI-selected battle-state extraction remains species/HP-only; future item inclusion should require explicit opt-in, read only trusted `item_profiles` metadata, map direct `status=user_confirmed` user input to `user_confirmed`, reserve `explicit_input` for direct explicit input, and keep missing, ambiguous, legality-derived, resist-berry-derived, damage-derived, or inferred items unknown.
- v11.6 added the explicit opt-in user-confirmed item source adapter. Default adapter calls remain species/HP-only; `include_user_confirmed_items=True` reads only `item_profiles` entries with `status=user_confirmed`, `source=user_input`, and non-empty `item_id`, preserving them as `source=user_confirmed` known items. UI checkbox mapping and payload builder runtime calls remain unchanged.
- v11.7 added a mocked offline prompt fixture for user-confirmed items in `battle_state_context`. It verifies known self/opponent items survive payload and prompt serialization with the existing guard, while field state and `known_conditions` stay unknown/empty and no item consumption, post-turn HP, RNG, speed tie, Quick Claw, selected opponent move, hidden item, or full outcome certainty is introduced.
- v11.8 designed the future UI mapping for user-confirmed items. The recommended implementation is to call `build_battle_state_context_from_ui_selected_state(battle_input, include_user_confirmed_items=enable_battle_state_context)` at the existing `_build_ui_selected_prompt(...)` generation point so checkbox off omits battle state and item payload entirely, while checkbox on can include only valid user-confirmed item metadata.
- v11.9 connected that mapping. The existing limited-context checkbox still gates `battle_state_context`; off omits it entirely, while on passes `include_user_confirmed_items=True` through the source adapter so valid user-confirmed item profiles become known battle-state item context and missing/malformed/forbidden metadata remains unknown.
- v11.10 updated the existing limited-context checkbox tooltip/status copy to mention user-confirmed items while keeping the label, default, behavior, payload builder flow, and prompt guard wording unchanged. Tests guard against hidden/inferred/recommended item wording and item activation, consumption, post-turn HP, RNG, speed tie, Quick Claw, full outcome, or selected opponent move certainty.
- v11.11 added a mocked UI-selected offline smoke for user-confirmed items. It verifies checkbox off omits `battle_state_context` and battle-state known item envelopes, checkbox on includes valid user-confirmed self/opponent items with species/HP `visible_ui`, malformed/forbidden metadata keeps items unknown, existing optional contexts coexist, and mocked responses avoid hidden/resolved item and turn outcome claims.
- v11.12 closed the user-confirmed item phase as PASS for design, contract/helper tests, source adapter, prompt/offline fixture, UI mapping, UI copy, and mocked UI-selected offline smoke. Current runtime behavior is checkbox-gated: off omits `battle_state_context`; on can include only valid user-confirmed item metadata as known item context. No additional actual Gemini item smoke has been run yet.
- v12.0 designed the controlled actual Gemini smoke for the user-confirmed item UI path without executing it. Future v12.1 execution requires explicit T1 approval, exactly one actual Gemini call, retry count 0, no second provider call, payload/prompt boundary prechecks, response safety scan, and sanitized token/cost reporting only.
- v12.1 executed the controlled user-confirmed item Gemini smoke after T1 approval. Exactly one Gemini call was made with `gemini-2.5-flash`, retry count was 0, Vertex AI was not used, no second provider call was made, payload/prompt boundaries passed, the response safety scan found no forbidden item/resolved-outcome claims, and sanitized token/cost summary was recorded without raw token-log or secret output.
- v12.2 closed the user-confirmed item actual smoke as PASS. The closure records T1 approval, one-call/no-retry execution, payload boundary PASS, prompt boundary PASS, response safety scan PASS, sanitized token/cost summary only, unstaged `logs/token_usage.jsonl`, and no raw token-log or secret output.
- v12.3 designed field state sources for `battle_state_context.field`. Current UI path still has no safe weather/terrain/screens/hazards/room source, so field remains unknown. Future field support should start with contract tests and allow only explicit/user-confirmed sources first; visible UI, battle-log observed, and parser-observed sources require later source-specific designs.
- v12.4 locked field state source contract tests. Helper behavior now preserves only `explicit_input`/`user_confirmed` known field sources and normalizes forbidden field sources to unknown; payload validation rejects forbidden field sources. Known field values do not create duration, expiration, post-turn, `damage_estimate`, or `ko_context` changes.
- v12.5 aligned field helper normalization with the field source contract. Helper behavior validates field values by key, preserves only valid `explicit_input`/`user_confirmed` known field values, keeps side-specific screens/hazards inside the existing known envelope, normalizes malformed helper input to unknown, and rejects malformed direct payload known field envelopes. No UI integration, prompt guard wording change, payload builder call-flow change, `damage_estimate`, or `ko_context` behavior change was made.
- v12.6 added a mocked field-state prompt/offline fixture. Known weather, terrain, room, side-specific screens, and side-specific hazards are preserved in payload and serialized prompt with the existing `battle_state_context` guard. Unknown field context stays unknown, existing limited contexts coexist, mocked responses avoid duration/expiration/post-turn/damage precision/full outcome/hidden field claims, and `damage_estimate` plus `ko_context` remain unchanged.
- v12.7 inventoried current UI field-state sources. No current UI widget or `battle_input` key captures weather, terrain, screens, hazards, room, or field conditions. The UI-selected battle-state adapter still reads only species/HP plus optional trusted item profiles. The item profile metadata pattern can be reused for future `field_profiles`, but no field UI or mapping was implemented.
- v12.8 designed the future Field Profile Dialog. The design scopes it to user-confirmed current field context only, proposes weather/terrain/room single-select controls plus side-specific screens/hazards multi-select controls, distinguishes `unknown` from user-confirmed `none`, reuses the `status=user_confirmed` + `source=user_input` metadata pattern, and recommends contract tests before any UI implementation or runtime mapping.
- v12.9 locked Field Profile Dialog contract tests. `build_field_state_from_field_profiles(...)` normalizes future dialog metadata without wiring it into UI mapping. Trusted `status=user_confirmed` + `source=user_input` + valid `value` maps to `user_confirmed` known field envelopes; `unknown` remains unconfirmed/missing/malformed input; `none` is known absence; both-side empty screens/hazards values are accepted as user-confirmed known absence. No Field Profile Dialog UI, field mapping, prompt guard change, payload builder call-flow change, provider call, `damage_estimate`, or `ko_context` change was made.
- v12.10 implemented standalone Field Profile Dialog UI. The dialog exposes weather/terrain/room single-select controls, side-specific screens/hazards controls, explicit `Unknown`/`None`/`Selected` side modes, `Apply`, `Cancel`, and `Reset unknown`, and returns the v12.9 `field_profiles` shape. It is not wired into `battle_input`, `battle_state_context`, the limited-context checkbox, prompt generation, or provider flow.
- v12.11 designed field state UI mapping without implementation. Future `field_profiles` should be session-local `MainWindow` state, gated by the existing limited-context checkbox, and mapped only when `enable_battle_state_context=True` through a future `include_user_confirmed_fields` helper flag. Checkbox off should omit both `battle_state_context` and field-profile data from the provider payload path; checkbox on may map only valid user-confirmed field metadata while preserving `unknown` and trusted `none` semantics.
- v12.12 locked Field State UI Mapping Tests. The UI-selected battle-state adapter now has default-off `include_user_confirmed_fields`; automatic prompt generation enables it only under the existing `enable_battle_state_context` gate. UI-only `field_profiles` are removed from provider prompt payloads and can affect advice only through normalized `battle_state_context.field`. Tests cover checkbox off/on, valid field mapping, `unknown`, trusted `none`, malformed/forbidden metadata, item coexistence, optional-context coexistence, and no duration/expiration/post-turn/damage precision/resolved outcome fields.
- v12.13 implemented Field State UI Mapping under the existing limited-context checkbox gate. Checkbox off omits `battle_state_context` and strips top-level `field_profiles`; checkbox on passes `include_user_confirmed_fields=True` through the UI-selected battle-state adapter so valid `field_profiles` normalize into `battle_state_context.field`. FieldProfileDialog button integration, MainWindow field-profile storage, UI copy changes, prompt guard wording changes, provider calls, `damage_estimate`, and `ko_context` behavior remain unchanged.
- v12.14 designed FieldProfileDialog button integration without implementation. The recommended first entry point is a secondary field-state button inside `LLMAdvicePanel` near the existing limited-context checkbox, while `MainWindow` should own future session-local `field_profiles`. The button may open with the checkbox off, but saved field profiles must not reach the prompt unless the checkbox enables `battle_state_context`. Recommended next is button integration tests before implementation.
- v12.15 locked FieldProfileDialog button integration behavior with seam-level tests before user-facing implementation. The tests cover dialog open/apply/cancel/reset session-state behavior, no provider call from the button path, checkbox off/on payload gating for saved field profiles, unchanged checkbox default, and unchanged `battle_state_context` prompt guard wording. No user-facing button, `MainWindow._field_profiles`, UI copy change, provider call, `damage_estimate`, or `ko_context` behavior was added.
- v12.16 implemented FieldProfileDialog button integration. `LLMAdvicePanel` now has a secondary `Field state` button and `field_profile_requested` signal, while `MainWindow` owns `_field_profiles`, opens `FieldProfileDialog`, stores Apply results, preserves Cancel state, and copies saved profiles into UI-selected battle input. The existing limited-context checkbox still gates provider payload behavior: off omits `battle_state_context` and top-level `field_profiles`, on maps valid saved profiles into `battle_state_context.field`. No new checkbox, prompt guard wording change, actual Gemini call, `damage_estimate`, or `ko_context` behavior was added.
- v12.17 updated limited-context checkbox tooltip/status copy for user-confirmed field state. The copy now states that enabled limited context can include user-confirmed current weather/terrain/room/screens/hazards context, while not confirming turn count, expiration, post-turn result, exact damage, or full turn outcome. Checkbox default, FieldProfileDialog behavior, field mapping behavior, prompt guard wording, provider calls, `damage_estimate`, and `ko_context` behavior remain unchanged.
- v12.18 added a Field State UI End-to-End Offline Smoke. A UI-selected Garchomp/Charizard fixture with saved `field_profiles` and user-confirmed items is run through mocked `run_ui_selected_advice` provider calls. Checkbox off omits `battle_state_context`, top-level `field_profiles`, and serialized field values; checkbox on serializes known weather, terrain, room, screens, and hazards inside `battle_state_context.field` while preserving existing optional contexts. Mocked responses avoid duration, expiration, post-turn state, exact damage, full outcome, damage-inferred field, and hidden-field claims. No actual Gemini call was made.
- v12.19 closed the Field State UI phase for the offline path. The closure records the completed source contract, helper normalization, prompt fixture, UI inventory, FieldProfileDialog, checkbox-gated mapping, button integration, limited-context copy update, and mocked end-to-end offline smoke. Current user flow is `Field state` button -> FieldProfileDialog -> `MainWindow._field_profiles` -> existing limited-context checkbox gate -> `battle_state_context.field` -> prompt serialization. The phase remains bounded to user-confirmed current context only: no duration, expiration, post-turn outcome, exact damage, full turn outcome, hidden-field guessing, full Turn Engine, `damage_estimate`, or `ko_context` behavior change. Recommended next is v12.20 Controlled Field State Gemini Smoke Design; it should be design-only unless T1 explicitly approves a later actual call.
- v12.20 designed the Controlled Field State Gemini Smoke without executing it. The design uses a Garchomp/Charizard fixture with user-confirmed items and user-confirmed field profiles for rain, electric terrain, Trick Room, side-specific screens, and side-specific hazards. Future execution requires clean repo/test preflight, separate T1/T2 approval, exactly one actual Gemini call, retry count 0, no second provider call, no Vertex AI call, no top-level `field_profiles` leakage, unchanged prompt guard wording, response safety checks against duration/expiration/post-turn/exact damage/full outcome/hidden-field claims, and sanitized token/cost summary only. No actual Gemini call was made in v12.20.
- v12.21 diagnosed the field-state actual-smoke preflight environment without installing dependencies or calling providers. Current shell `python` resolves to Anaconda Python 3.13.5 with `pytest 8.3.4` but no PySide6. Python 3.11 exists but lacks both pytest and PySide6. `uv` is not on PATH and no repo-local `.venv` exists. `pyproject.toml` and `uv.lock` already declare/lock PySide6, pytest, and pytest-mock, and README/AGENTS expect `uv run pytest`. The non-UI `tests/test_advisor_battle_state_context.py -q` passes, while PySide6-dependent targeted suites fail during collection. Actual Gemini smoke remains NOT READY in this shell; recommended next is v12.22 Python Environment Setup Guide before any provider execution.
- v12.22 documented the Python Environment Setup Guide. The guide records the Windows setup path for restoring the repo's uv-managed environment: verify/restore `uv`, restart or refresh PATH, run `uv sync --dev` from the repo root after T1 approval, run the field-state targeted preflight set with `uv run pytest`, then run full `uv run pytest -q`. It also documents troubleshooting for missing uv, PySide6, pytest, wrong Python selection, Anaconda PATH priority, missing/broken `.venv`, and PATH refresh issues. No dependency install, sync, provider call, API key validation, production code change, `pyproject.toml` change, or lockfile change was executed in v12.22.
- v12.23 executed the approved environment setup. `uv 0.11.26` was installed/restored, `uv sync --dev` completed with CPython 3.11.9, the repo-local `.venv` now has `pytest 9.0.3` and `PySide6 6.11.0`, targeted field-state preflight tests all pass, and full pytest passes with `1397 passed, 2 deselected`. `pyproject.toml`, `uv.lock`, requirements files, production code, prompt guards, FieldProfileDialog behavior, and field mapping behavior were unchanged. No actual Gemini call, provider credential validation, retry, second provider call, Vertex AI call, `.env` output, API key output, or raw token-log output occurred.
- v12.24 executed the Controlled Field State Gemini Smoke after T1/T2 approval. Targeted preflight tests and full pytest passed, the pre-call prompt payload included gated `battle_state_context.field` values for user-confirmed rain, electric terrain, Trick Room, side-specific screens, and side-specific hazards, and top-level `field_profiles` did not leak. Exactly one actual Gemini call was made with `gemini-2.5-flash`, retry count was 0, second provider call count was 0, and Vertex AI call count was 0. The sanitized response scan found no duration, expiration, post-turn state, exact damage, full outcome, damage-inferred field, hidden field, or hidden item claims. Sanitized token summary: input `11879`, output `172`, cached `0`, estimated cost USD `0.0`. Raw response text and raw token log contents were not printed.
- v12.25 closed the Field State Actual Smoke phase as `CLOSED - PASS` without another provider call. The closure summarizes v12.20-v12.24, records the one-call/no-retry audit trail, payload/prompt PASS, response safety PASS, sanitized token/cost handling, remaining limitations, and recommends v12.26 Item Activation/Consumption Boundary Design next. No production code, dependency file, prompt guard, FieldProfileDialog behavior, field mapping behavior, `damage_estimate`, or `ko_context` behavior changed.
- v12.26 designed the Item Activation/Consumption Boundary without implementation. Known/user-confirmed items remain current context only and do not imply activation, consumption, resolved item effects, post-turn item state, exact damage, resolved order, hidden item inference, or opponent set/item inference. The design defines `unknown_item`, `known_item`, `candidate_activation`, `observed_activation`, `observed_consumption`, and `resolved_item_effect`, documents allowed and forbidden sources, gives Leftovers/Choice Scarf/Focus Sash/Berry/Quick Claw examples, and recommends v12.27 Item Activation/Consumption Contract Tests.
- v12.27 locked Item Activation/Consumption Contract Tests. Known user-confirmed items still serialize only as current context, while malformed battle-state contexts with item-event/resolved fields such as `item_activated`, `item_consumed`, `resolved_item_effect`, `post_turn_item_state`, `quick_claw_activated`, `focus_sash_triggered`, and `berry_consumed` are rejected. Focus Sash, Quick Claw, Berry, Leftovers, and Choice Scarf prompt fixtures verify known items do not serialize activation/consumption fields or positive overclaim phrases. Forbidden inference sources do not upgrade to known items or item events.
- v12.28 added an Item Activation/Consumption Prompt Fixture. The offline fixture uses mocked provider calls only, covers Leftovers, Choice Scarf, Focus Sash, Berry, and Quick Claw, verifies known items serialize only as user-confirmed current context, checks prompt payloads omit activation/consumption/resolved/post-turn item fields, checks safe mocked response wording, and verifies coexistence with `battle_state_context.field`, `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- v12.29 closed the Item Activation/Consumption boundary phase as `CLOSED - PASS`. The closure records v12.26 boundary design, v12.27 contract tests, v12.28 prompt fixture, final known-item current-context boundary, item state model, source boundaries, payload safety PASS, prompt/response safety PASS, coexistence PASS, and recommends v12.30 Item Event Source Inventory.
- v12.30 inventoried item event sources without implementation. The only current source remains `user_confirmed_current_item` -> `known_item` only. Future trusted source candidates are explicit user event confirmation, battle log observation, parser observation, imported replay observation, and future Turn Engine resolution; observed activation, observed consumption, resolved item effects, and post-turn item state remain future-only pending source contracts, payload contracts, tests, and approval.
- v12.31 locked Item Event Source Contract Tests. Future item event fields such as `item_event_context`, `observed_events`, `resolved_effects`, `observed_activation`, `observed_consumption`, `item_event_type`, `event_source`, `event_confidence`, `event_turn`, and `event_provenance` are rejected by current battle-state validation, and future source names do not create trusted observed/resolved events without a separate implementation.
- v12.32 designed Explicit User Item Event Confirmation without implementation. It distinguishes known item, explicit user event confirmation, and resolved item effect; recommends an Item Event Dialog over inline chips; proposes session-local `MainWindow._item_event_confirmations`; and keeps observed event candidates separate from resolved effects, post-turn state, exact HP/damage, RNG, and Speed/order resolution.
- v12.33 locked Explicit User Item Event Contract Tests. Helper-level validation accepts `explicit_user_event_confirmation` candidates only with `status=user_confirmed` and observed event types, rejects invalid source/status/event type/missing fields, rejects resolved/post-turn/exact HP/exact damage/RNG/Speed-order fields, and verifies generated prompt payloads still do not include trusted `item_event_context` before a later mapping implementation.
- v12.34 locked Explicit User Item Event Dialog UI Tests with a test-only fake dialog/controller seam. Apply stores valid observed candidates, Cancel preserves previous session state, Reset clears dialog-local draft and only persists on Apply, invalid events are not saved, opening the future dialog does not request advice or call providers, no real button/dialog/MainWindow wiring is implemented, and `item_event_context` remains unmapped from prompt payloads.
- v12.35 implemented the standalone `ItemEventDialog` widget without button wiring or payload mapping. The dialog has side, item, observed event type, optional turn, and optional note fields; returns `status=user_confirmed` and `source=explicit_user_event_confirmation`; keeps blank turn/note as `None`; validates through the v12.33 helper; implements Apply/Cancel/Reset; and still does not add `item_event_context`, observed prompt mapping, provider calls, parser/replay/Turn Engine behavior, or resolved/post-turn/exact HP/damage/RNG/order calculations.
- v12.36 locked Explicit User Item Event Button Integration Tests with a test-only fake dialog/controller/provider seam. Future button open behavior does not request advice or call providers, Apply stores valid events into a session-local `_item_event_confirmations` candidate, Cancel preserves previous state, Reset persists only on Apply, invalid events are not stored, existing FieldProfileDialog button and limited-context checkbox behavior remain unchanged, and `item_event_context` remains unmapped from prompt payloads.
- v12.37 wired the real LLMAdvicePanel `Item event` button to MainWindow session-local `_item_event_confirmations` state. The button emits `item_event_requested`, not `advice_requested`; MainWindow opens `ItemEventDialog`; Apply saves validated observed candidates; Cancel preserves previous state; Reset + Apply stores an empty list; invalid dialog output does not replace state; existing FieldProfileDialog and limited-context checkbox behavior remain unchanged; and `item_event_context` remains unmapped from prompt payloads.
- v12.38 designed future Item Event Payload Mapping without implementation. The design keeps `_item_event_confirmations` UI-only for now, proposes a future path through `battle_input["item_event_confirmations"]` into `item_event_context.observed_events`, recommends the existing limited context checkbox as the hard gate, limits source/status/event types to explicit user-confirmed observed candidates, and keeps resolved effects, post-turn state, exact HP/damage, RNG, Speed/order, parser/replay/Turn Engine behavior, and provider calls out of scope.
- v12.39 locked Item Event Payload Mapping Tests with a test-only mapper seam. Checkbox off omits the future item event context candidate; checkbox on normalizes only validated explicit user-confirmed observed events with `confidence=observed`; invalid and resolved/post-turn/exact HP/damage/RNG/order inputs are rejected; known item and field state behavior remain unchanged; safe observed-event wording is locked; and current runtime payloads/prompts still omit `item_event_context` pending implementation.
- v12.40 implemented limited-context-gated Item Event Payload Mapping. Checkbox off keeps `_item_event_confirmations` out of battle input and payloads. Checkbox on copies session-local confirmations to battle input, strips the raw UI field before provider payload serialization, and normalizes valid explicit user-confirmed events into `item_event_context.observed_events` with `confidence=observed`. Invalid events are omitted, resolved/post-turn/exact HP/damage/RNG/Speed-order fields remain blocked, known item and field state behavior remain unchanged, and no new natural-language prompt wording or provider call was added.
- v12.41 added an Observed Item Event Prompt Fixture. A minimal prompt guard appears only with `item_event_context` and states that explicit user-confirmed events are observed context only, not resolved mechanics, exact calculations, post-turn state, RNG, or resolved order. Offline fixtures use the production advice path with mocked `call_gemini` and logging, cover all five observed event types, checkbox off/on behavior, optional values, known-item separation, invalid raw event omission, and forbidden claim/field scans without a provider call.
- v12.42 closed the Item Event Payload Mapping phase as `CLOSED - PASS`. The limited-context hard gate, trusted observed-event contract, invalid-event omission, observed-only prompt guard, and unchanged known-item/field-state boundaries are recorded in the closure; no provider call was made.
- v12.43 inventoried the post-closure Item Event follow-ups without implementation. It recommends v12.44 Item Event Actual Gemini Smoke Design, records Battle Log Item Event Source Design as the automation-oriented alternative, and keeps status/condition and damage-calculator design as later, broader options.
- v12.44 designed, but did not execute, a one-call Item Event actual Gemini smoke. The representative fixture separates self known Leftovers from an opponent Focus Sash activation observed through explicit user confirmation. The design fixes observed-only PASS/FAIL criteria, pre-call and manual review checks, sanitized failure handling, and requires separate T1/T2 approval before a future v12.45 execution.
- v12.45 executed the separately approved one-call Item Event Gemini smoke with `gemini-2.5-flash`. Pre-call contracts passed and retry/fallback/second-provider/Vertex AI count was zero. Result: `FAIL - SEMANTIC BOUNDARY`; the response did not clearly distinguish the explicit Focus Sash observation from known-item context, foregrounded unrelated available context, and included a specific HP damage range. No prompt, payload, production code, test, or fixture change was made, and no second call was made.
- v12.46 analyzed the v12.45 failure without another provider call. The likely issue is response salience and fixture ambiguity, not a proven mapper failure: the observed-only guard lacks positive identity/contrast requirements, while the generic advisor path continues with broad damage/KO/item instructions and full payload context. The recommended next step is v12.47 failure reproduction contracts separating narrow event semantics from full-advice prioritization.
- v12.47 added offline failure-reproduction contracts without production changes. Fixture A locks current known Leftovers versus observed opponent Focus Sash separation; Fixture B characterizes the current full-advice guard plus broad-context gap. A test-only evaluator rejects identity mixing, event omission, unsupported resolution, and damage distraction only when event readback is absent.
- v12.48 designed the minimal correction without implementation. It recommends a compact extension of the existing event-present observed-only guard: explicitly contrast known current items with observed events and briefly read back each event's side, item, type, and user-confirmed unresolved status. Damage context remains available but must not replace event acknowledgement.
- v12.49 implemented that compact extension in the existing item-event guard. It is emitted only for non-empty normalized observed events, distinguishes current known items from observed events, requests side/item/event-type user-confirmed readback, preserves non-inference wording, and coexists with trusted damage context. Offline production-path fixtures and reproduction contracts pass without provider calls.
- v12.50 validated the v12.49 correction offline without a provider call. Mocked production-path capture confirms contrast/readback and observed-only anchors for valid events, absence for disabled/known-only/all-invalid paths, and coexistence with trusted damage context. Synthetic contracts reject identity mixing, omission, exact outcomes, RNG/order claims, and damage distraction without event readback. Status: `READY FOR SINGLE ACTUAL RE-SMOKE`, which is readiness only and not approval.
- v12.51 executed the separately approved one-call re-smoke with `gemini-2.5-flash`. Result: `FAIL - SEMANTIC BOUNDARY`. The response now acknowledged an opponent Focus Sash activation observation and kept resolved/exact/post-turn/RNG/order boundaries, but it did not identify self Leftovers as current known-item context or explicitly attribute the event to user confirmation. No prompt/payload/test change or second call was made.
- v12.52 fixed the remaining attribution gap offline. The event-present guard now conditionally requests side/item user-confirmed current-known readback and explicitly prevents known-item promotion into observed event meaning, while retaining observed-event side/item/type readback. Contracts cover both contexts, event-without-known-item, known-only, disabled, and all-invalid paths. Status: `READY FOR FINAL SINGLE ACTUAL RE-SMOKE`; readiness is not approval.
- v12.53 executed the separately approved final one-call re-smoke with `gemini-2.5-flash`. Result: `PASS`. The response read back self Leftovers as user-confirmed current known-item context and opponent Focus Sash activation as a separate observed event, retained uncertainty, kept damage context alongside both readbacks, and made no detected resolved/exact/post-turn/RNG/final-order overclaim. No prompt/payload/test change or second call was made.
- v12.54 closed the v12.26-v12.53 Item Event phase as `CLOSED - PASS`. The closed scope covers known-item and explicit-observed-event contracts, session-local confirmation, limited-context mapping, prompt attribution, and final actual smoke validation. Remaining lifecycle, automated-source, and resolved-calculation work stays separate. Recommended next: v12.55 Item Event Session Lifecycle Design and Contract Tests.
- v12.55 implemented the session-local lifecycle: count/readback, dialog edit/delete, duplicate update identity, stable turn ordering, and an explicit Clear item events reset action. Payload and prompt contracts remain unchanged; checkbox off still preserves state while omitting it from payload.
- v12.56 hardened lifecycle integration offline. Apply/edit/delete/clear now have MainWindow-to-payload-to-prompt contract coverage, duplicate edit collisions keep the edited value once, and delete clears selection to prevent an accidental repeated delete. No provider call or payload/prompt redesign occurred.
- v12.57 added a validation-only status/condition foundation. Only `user_confirmed_current_condition` with known current major-status semantics is accepted; UI-selected runtime mapping and prompt exposure remain intentionally absent. Future event/parser/replay/Turn Engine sources remain unsupported until separately contracted.
- v12.58 added current-condition UI/session state and a limited-context `battle_input` candidate list. It remains filtered before advisor prompt serialization: no `condition_context`, condition guard, or actual provider call was added. Prompt mapping is a separate future task.
- v12.59 maps validated current-condition candidates under the existing limited-context gate. Valid `user_confirmed_current_condition` entries serialize as `condition_context.current_conditions`; disabled, invalid, and all-invalid paths omit it. The compact prompt guard keeps current conditions as self/opponent present-state context only, distinguishes `none` from `unknown`, and forbids application, trigger, exact damage/duration, post-turn, RNG, and final-order inference. Offline mocked production-path fixtures also confirm coexistence with item-event context. No actual Gemini/provider call was made.
- v12.60 strengthens offline response validation. The condition guard now asks for compact side/type user-confirmed present-state readback only when valid context exists. Fixture-specific synthetic tests reject side mixing, unknown inference, event/resolved promotion, exact/post-turn, duration/RNG/order claims, `none` removal-event wording, and omission. Status: `READY FOR SINGLE ACTUAL CONDITION SMOKE`; this is not approval for an actual provider call.
- v12.61 was blocked before any provider call: the approved raw Focus Sash event included `confidence=observed`, while the current raw confirmation validator adds that field only during normalized `item_event_context.observed_events` construction. The item-event context was therefore absent at preflight. Result: `BLOCKED - PRECALL CONTRACT FAILURE`, attempts 0 of 3, with no credential validation, retry, fallback, second provider, or Vertex AI call.
- v12.62 corrected the raw/normalized fixture distinction and passed preflight. Exactly three approved independent `gemini-2.5-flash` calls completed with no retry/fallback/second provider/Vertex AI. The execution channel did not return sanitized evaluator output, so no response text was recovered or stored and individual semantic results cannot be classified. Result: `INCONCLUSIVE - INSUFFICIENT PROVIDER RESULTS`; no fourth call was made.
- v12.63 hardened future smoke capture without an actual call. `run_ui_selected_advice_with_sanitized_smoke_capture(...)` keeps response text only in memory for an evaluator, returns provider/semantic status plus a short sanitized summary, and rejects full raw-response summaries. Sentinel contracts confirm advisor return and worker signal preservation; v12.62 is classified as unusable one-shot runner capture output, not evidence of a provider-empty response. Status: `READY FOR CAPTURED ACTUAL STABILITY SMOKE`; separate approval remains required.
- v12.64 used the approved captured-smoke path with the same raw self-burn, opponent-unknown, and opponent-Focus-Sash fixture for exactly three independent `gemini-2.5-flash` attempt invocations. Offline capture and prompt preflight passed, but this execution channel returned no sanitized attempt objects. No raw response or token-log content was recovered; metadata-only log changes cannot classify every provider result. Result: `INCONCLUSIVE - INSUFFICIENT PROVIDER RESULTS` (semantic PASS 0 assessable, semantic FAIL 0 assessable, response unavailable 3, provider failure 0 observed). Do not rerun or add a provider call without a new explicit approval and a verified result-return channel.
- v12.65 replaced the return-value-only smoke runner boundary with `scripts/run_sanitized_condition_smoke.py`. The fixed one-attempt CLI reuses `run_ui_selected_advice_with_sanitized_smoke_capture(...)` and prints one schema-validated sanitized JSON line to stdout. It has no retry/loop/fallback/provider-selection logic, rejects raw-response and secret-shaped output keys, and distinguishes semantic pass/fail, response unavailable, evaluator failure, provider failure, invalid CLI input, and malformed capture output through fixed exit codes. Fake-provider subprocess contracts pass without exposing the raw sentinel. Status: `READY FOR CLI-CAPTURED ACTUAL STABILITY SMOKE`; a new explicit approval is still required, and each future attempt must invoke the CLI separately.
- v12.66 executed exactly three approved independent CLI attempts with the fixed `current-condition-item-event` fixture and `gemini-2.5-flash`. All attempts returned parseable sanitized JSON, exit 0, empty stderr, provider success, response available, and semantic fail; the sanitized summary consistently reports missing, mixed, or overstated current-condition/observed-item-event attribution. Result: `FAIL - SEMANTIC STABILITY` (PASS 0, FAIL 3, response unavailable 0, evaluator failure 0, provider failure 0, CLI/precall failure 0). The result validates capture transport but does not preserve raw response text or authorize a fourth call or immediate prompt change.
- v12.67 hardened prompt attribution offline after the v12.66 semantic-stability failure. The new payload-driven `Trusted context attribution` block distinguishes each user-confirmed current condition from each explicitly user-confirmed observed item event and requires a compact category/identity acknowledgement without resolved/exact/timing/RNG/order promotion. Condition-only, item-event-only, absent, disabled, invalid, `none`, and `unknown` paths are contract-tested. Synthetic category-collapse and promotion cases fail while natural compact readback variants pass. Status: `READY FOR ATTRIBUTION RE-SMOKE`; this is not actual-call approval.
- v12.68 executed exactly three approved independent CLI re-smoke attempts after v12.67. All three returned parseable sanitized JSON, exit 0, empty stderr, provider success, response available, and semantic fail with the same attribution-boundary summary. Result: `FAIL - SEMANTIC STABILITY` (PASS 0, FAIL 3, response unavailable 0, evaluator failure 0, provider failure 0, CLI/precall failure 0). The prompt block passed offline contracts but did not improve actual fixed-fixture stability; do not perform a fourth call or immediate prompt change from this result.
- v12.69 documented `BLOCKED - CLI CONTRACT CONFLICT`. A structured `[Trusted Context]` acknowledgement with deterministic exact-set validation is the next minimal design, but the actual smoke evaluator is directly owned by the explicitly protected `scripts/run_sanitized_condition_smoke.py`. Adding a parser/prompt outside that CLI would not affect actual semantic results. A future task must explicitly authorize the narrow CLI evaluator integration before parser/prompt implementation or another actual smoke.
- v12.70 resolved that scope conflict after explicit CLI authorization. Prompt generation now requires a dynamic `[Trusted Context]` acknowledgement plus `[Advice]` only when normalized trusted condition/item-event entries exist. `advisor_client` parses and exact-validates category/side/identity/event-type lines, and the actual CLI evaluator derives expected entries from the production normalized prompt payload before applying parser, advice-body, unknown-inference, and forbidden-claim checks. CLI schema/exit codes remain unchanged. Status: `READY FOR STRUCTURED ACKNOWLEDGEMENT ACTUAL SMOKE`; this is not actual-call approval.

Battle State UI Gemini smoke reached actual Gemini PASS in v11.1 and closure in v11.2. Payload preflight PASS still does not imply actual Gemini PASS for future new contexts. Chilan Berry reached actual Gemini PASS after v2.7.1. Light Ball reached actual Gemini PASS after v3.1.1. The original Focus Band / Quick Claw / Light Ball / Chilan Berry pending queue is closed.

## Copy-Paste Prompt

```text
T3, continue after v12.54 Item Event Phase Closure and Next Priority Selection.

Goal:
- Do not add new item contexts.
- Do not run extra Gemini calls unless T1/T2 explicitly approve them.
- Treat `turn_snapshot` as selected/pre-turn known state only, not full Turn Engine output.
- Current recommended next milestone is v12.55 Item Event Session Lifecycle Design and Contract Tests.
- v12.54 closed the Item Event phase as `CLOSED - PASS` after final actual smoke validation.
- The next lifecycle task should design and contract-test summary/readback, edit/delete, duplicate/order policy, and session reset/new-battle boundaries before production UI expansion.
- v12.45 has already consumed its separately approved single actual Gemini call and ended `FAIL - SEMANTIC BOUNDARY`.
- Do not run another item-event provider call without a new explicit T1/T2 approval.
- Analyze response salience and known-item/observed-event separation before proposing any prompt or payload change.
- v12.43 compared item-event smoke, battle-log source, status/condition source, and damage-calculator design work without implementation.
- The recommendation is smoke design only; any actual Gemini execution remains a separately approved future task.
- v12.42 closed the v12.38-v12.41 item event payload-mapping phase as `CLOSED - PASS`.
- The current scope is explicit user-confirmed observed events only; resolved effects, post-turn state, exact HP/damage, RNG, and resolved order remain out of scope.
- v12.43 is an inventory-only comparison of possible follow-up policies; it does not implement new item-event behavior.
- v12.41 added a minimal item-event prompt guard and offline production prompt fixture.
- The guard applies only when `item_event_context` exists and preserves observed-only meaning.
- Offline mocked fixtures cover all five event types, checkbox off/on, known-item separation, and invalid raw event omission.
- No actual provider call or response safety implementation was added.
- v12.40 implemented limited-context-gated runtime item event mapping.
- Checkbox off omits session events from battle input and payloads.
- Checkbox on normalizes only valid explicit user-confirmed observed events into `item_event_context.observed_events` with `confidence=observed`.
- Invalid events are omitted and all-invalid input omits item event context.
- Raw `item_event_confirmations` is removed before provider payload serialization.
- Current prompt has structured context only; no new natural-language observed-event wording was added.
- Historical `unmapped` bullets below describe the pre-v12.40 state and do not override the active mapping boundary above.
- v12.39 locked the future mapping contract with a test-only helper seam.
- Checkbox off omits item event context.
- Checkbox on accepts only validated explicit user-confirmed observed events and adds `confidence=observed`.
- Invalid events and resolved/post-turn/exact HP/damage/RNG/order fields are rejected.
- Known item/current item and field state behavior remain unchanged.
- Current runtime payload and prompt mapping remain unimplemented.
- v12.38 designed future item event payload mapping without implementation.
- Proposed future path is `_item_event_confirmations` -> `battle_input["item_event_confirmations"]` -> limited context gate/helper -> `item_event_context.observed_events` -> prompt serialization.
- Existing limited context checkbox is the recommended hard gate.
- Checkbox off should omit `item_event_context`.
- Checkbox on should include only valid observed events after source/status/event_type validation.
- `item_event_context` remains unmapped in current runtime code.
- Resolved effects, post-turn state, exact HP/damage, RNG, and Speed/order fields remain forbidden.
- v12.37 wired the real LLMAdvicePanel `Item event` button and MainWindow session-local `_item_event_confirmations` storage.
- The button emits `item_event_requested`, not `advice_requested`.
- Button/open action must not request advice or call providers.
- MainWindow opens `ItemEventDialog`.
- Apply stores validated explicit user item event observed candidates in session-local `_item_event_confirmations`.
- Cancel preserves previous session state.
- Reset clears dialog-local draft only; Reset + Cancel preserves previous state and Reset + Apply stores an empty event list.
- Invalid event candidates are rejected and are not saved.
- Existing FieldProfileDialog button behavior and limited-context checkbox gating remain unchanged.
- `item_event_context` remains unmapped from generated prompt payloads.
- v12.36 locked future Item Event button integration behavior with test-only seams.
- Future button/open action must not request advice or call providers.
- Apply stores valid explicit user item events into session-local `_item_event_confirmations`.
- Cancel preserves previous session state.
- Reset clears dialog-local draft only; Reset + Cancel preserves previous state and Reset + Apply stores an empty event list.
- Invalid event candidates are rejected and are not saved.
- Existing FieldProfileDialog button behavior and limited-context checkbox gating remain unchanged.
- Real LLMAdvicePanel Item Event button and MainWindow session wiring exist, but remain UI-only.
- `item_event_context` remains unmapped from generated prompt payloads.
- v12.35 implemented standalone `ItemEventDialog`.
- The dialog fields are side, item, event type, optional turn, and optional note.
- Returned events keep `status=user_confirmed` and `source=explicit_user_event_confirmation`.
- Blank turn and note are retained as `None`.
- Apply validates through the explicit user item event helper and accepts valid observed candidates.
- Cancel rejects without saving a result.
- Reset clears dialog-local draft; Reset + Apply returns an empty event list.
- LLMAdvicePanel button and MainWindow session wiring were added in v12.37.
- `item_event_context` remains unmapped from generated prompt payloads.
- v12.34 locked future Item Event Dialog UI behavior with test-only seams.
- Apply stores valid explicit user item events as session-local observed candidates.
- Cancel preserves previous session state.
- Reset clears dialog-local draft only; Reset + Cancel preserves previous state and Reset + Apply stores an empty event list.
- Invalid event candidates are rejected and are not saved.
- Opening the future item event dialog does not request advice and does not call providers.
- Real Item Event Dialog, real button, and MainWindow session wiring exist as of v12.37.
- `item_event_context` remains unmapped from generated prompt payloads.
- v12.33 locked explicit user item event contract tests.
- Helper-level explicit user event validation accepts observed candidates only.
- Valid explicit user event candidates require `source=explicit_user_event_confirmation`, `status=user_confirmed`, and an allowed observed event type.
- Invalid source, invalid status, invalid event type, and missing required fields are rejected.
- Explicit user event candidates do not create resolved item effects, post-turn item state, exact HP, exact damage, RNG rolls, or Speed/order overrides.
- Generated prompt payloads still do not include trusted `item_event_context` before a later mapping implementation.
- v12.32 designed explicit user item event confirmation without implementation.
- Recommended future UI option is Item Event Dialog, not inline chips.
- Candidate session-local state is `MainWindow._item_event_confirmations`.
- Explicit user event confirmation may create future observed event candidates only, not resolved effects or post-turn state.
- v12.31 locked item event source contract tests.
- Future item event fields are rejected by current battle_state_context validation.
- Future source names alone do not create trusted observed/resolved item events.
- v12.30 inventoried item event sources without implementation.
- Current allowed source is still `user_confirmed_current_item` -> `known_item` only.
- Future trusted source candidates are `explicit_user_event_confirmation`, `battle_log_observed`, `parser_observed`, `imported_replay_observed`, and `future_turn_engine_resolved`.
- Observed activation, observed consumption, resolved item effects, and post-turn item state remain future-only pending source contracts, payload contracts, tests, and approval.
- v12.29 closed the item activation/consumption boundary phase as CLOSED - PASS.
- Future observed activation/consumption still requires separate source inventory, design, tests, and approval.
- v12.28 added an offline mocked prompt/response fixture for item activation/consumption overclaim checks.
- Known items remain user-confirmed/current context in prompt payloads and mocked responses.
- v12.27 locked contract tests for known item versus activation/consumption/resolved item effect boundaries.
- Valid known item context remains unchanged; malformed battle_state_context item-event fields are rejected.
- v12.26 designed the item activation/consumption boundary without implementation.
- Known item means user-confirmed/current item context only; it does not mean activated, consumed, resolved effect, post-turn item state, exact damage, resolved order, hidden item inference, or opponent set/item inference.
- v12.25 closed the field-state actual smoke phase as CLOSED - PASS.
- v12.24 passed the controlled actual Gemini smoke with exactly 1 actual Gemini call, retry count 0, no second provider, and no Vertex AI.
- Do not run another actual Gemini smoke without separate explicit T1/T2 approval for that task.
- Keep `logs/token_usage.jsonl` and `config/env.example` uncommitted and unreset.
- Treat the original item-context verification queue as closed:
  - Focus Band: PASS
  - Quick Claw: PASS
  - Chilan Berry: PASS
  - Light Ball: PASS
- Review v2.5 actual Gemini results:
  - Focus Band: PASS
  - Quick Claw: PASS
  - Light Ball: PARTIAL before v2.6
  - Chilan Berry: PARTIAL
- v2.6 has already applied a narrow wording polish for Light Ball and Chilan Berry.
- v2.6.1 has already run a post-polish actual Gemini recheck:
  - Light Ball: FAIL
  - Chilan Berry: PARTIAL
- v2.7 has already added a prompt guard requiring visible available item contexts to be mentioned at least once when directly relevant.
- v2.7.1 has already run post-guard actual Gemini rechecks:
  - Light Ball: PARTIAL
  - Chilan Berry: PASS
- v2.8 has already added a narrower Light Ball-specific no-item residue guard.
- v2.8.1 has already run a Light Ball-only actual Gemini recheck:
  - Light Ball: FAIL
- v3.1 has already integrated eligible user-confirmed Pikachu + Light Ball into advisor damage estimates:
  - damage_estimate.item_effects.attacker_item.status becomes applied
  - assumptions.item no longer remains none
  - raw rolls intentionally change only for eligible Light Ball
  - ko_context follows the adjusted damage estimate rolls
- v3.1.1 has already run a Light Ball-only actual Gemini verification:
  - Light Ball: PASS
- The original pending item-context actual verification queue is closed.
- Chilan Berry can be treated as full PASS unless later changes regress it.
- Recommended next milestone:
  - v12.55 Item Event Session Lifecycle Design and Contract Tests
  - Reason:
    - v12.54 closes the observed-event phase with final actual smoke PASS.
    - Lifecycle is the most localized user-visible gap before adding automated sources or resolved mechanics.
- Reason:
  - v12.35 implemented the standalone dialog without wiring.
  - Button/session-local storage behavior should be locked test-first before adding LLMAdvicePanel/MainWindow wiring.
  - v12.34 locked Item Event Dialog Apply/Cancel/Reset/session-local behavior before implementation.
  - v12.33 locked the explicit user event source contract at helper level.
  - v12.32 documented the smallest trusted observed source before implementation.
  - v12.31 locked future item event fields and future source names as rejected until trusted source implementation exists.
  - v12.30 documented trusted item event source candidates without implementing parser, replay, resolver, or Turn Engine behavior.
  - v12.29 closed the known-item activation/consumption boundary phase as PASS.
  - v12.24 controlled field-state actual smoke passed.
  - The one-call/no-retry audit trail is complete and should be closed before starting a new feature boundary.
  - v12.23 restored the uv-managed test environment and passed the field-state targeted preflight set plus full pytest.
  - v12.20 already designed the controlled field-state actual smoke policy and safety checks.
  - Any additional actual Gemini call still needs separate explicit approval, retry count 0, no second provider, no Vertex AI, and sanitized token/cost reporting only.
  - v6.10 actual smoke passed with exactly 1 Gemini call and no retry.
  - v6.11 closed that PASS result and kept the current safety boundary explicit.
  - v6.12 designed how to describe the limited TurnPipeline planning summary before any UI checkbox or user-facing exposure implementation.
  - v6.13 locked the prompt / UX copy rules in fixture tests.
  - v6.14 designed UI exposure and recommended not implementing a visible general-user checkbox yet.
  - v6.15 verified an offline end-to-end payload -> prompt -> mocked advice fixture.
  - v6.16 documented the UI exposure test plan, including default-off regression, flag on/off smoke, no-call guarantee, copy visibility, and rollback criteria.
  - v6.17 ran a controlled UI-level mock smoke without implementing UI, using fake UI state for omitted/default, flag-off, and flag-on paths.
  - v6.18 added a default-off dev-only UI flag after T1 approval. The checkbox starts unchecked, has no persisted auto-enable, and toggling alone does not call Gemini.
  - v6.19 manually QA'd the dev flag with offscreen PySide smoke. The checkbox/default/tooltip/status/toggle behavior passed, and no actual Gemini call was made.
  - v6.20 ran one controlled UI Gemini smoke after T1 approval. Result: PASS, with no retry and no Vertex AI call.
  - v6.21 closed the TurnPipeline UI phase and recorded the current feature state, safety boundary, known timing-sensitive perf issue, and next major direction options.
  - v7.0 split future Turn Engine work into stages and recommended deterministic turn order context before any resolved simulation.
  - v7.1 designed deterministic priority/speed/tie candidate context only.
  - v7.2 locked the fixture-level turn order context payload contract and rejected resolved-outcome fields.
  - v7.3 implemented a narrow deterministic helper against that contract.
  - v7.4 added the optional explicit-only payload adapter with validation and `turn_pipeline` coexistence coverage.
  - v7.5 designed prompt placement, safety wording, `turn_pipeline` coexistence, forbidden phrase candidates, and prompt contract test plan.
  - v7.6 locked prompt guard/copy tests with a minimal helper but did not wire it into `_build_ui_selected_prompt(...)`.
  - v7.7 wired the guard into `_build_ui_selected_prompt(...)` for explicit turn-order context prompts and verified it offline.
  - v7.8 verified the full prompt/context path through a mocked advice fixture without Gemini.
  - v7.9 designed how the existing UI/dev flag should expose or combine TurnPipeline and turn-order context before any actual Gemini smoke.
  - v7.10 implemented the default-off UI flag mapping so checked means `enable_turn_pipeline=True` and `enable_turn_order_context=True`, while unchecked means both remain false.
  - v7.11 verified the actual UI checkbox path through a mocked offline advice fixture.
  - v7.12 designed the controlled UI Gemini smoke and locked the pre-check, maximum-one-call, no-retry, stop-condition, classification, and recording policies.
  - v7.13 attempted the smoke but stopped before provider call because the local prompt-alignment harness guard raised. Result: BLOCKED. Actual Gemini call count: 0. Retry count: 0.
  - v7.14 triaged the prompt-alignment issue: direct pre-check prompt omitted the auto-built `turn_snapshot`; the provider path included it. Safety anchors still held.
  - v7.15 aligned the smoke harness around provider-path prompt capture, focused safety anchors, structural optional-context checks, and harmless `turn_snapshot` presence.
  - v7.16 retried the controlled UI Gemini smoke after T1 approval. Result: PASS. Actual Gemini call count: 1. Retry count: 0. No Vertex AI call.
  - v7.17 closed the turn-order UI integration phase and recorded current supported behavior, unsupported boundaries, Quick Claw wording boundaries, smoke PASS, known limitations, and next phase candidates.
  - v8.0 designed battle state / opponent move context expansion and recommended starting with a fixture-level opponent move context payload contract.
  - v8.1 locked the fixture-level `opponent_move_context` contract and rejected hidden inference / selected move inference / resolved outcome fields.
  - v8.2 added a minimal helper that produces the v8.1 shape from explicit known/candidate move data only.
  - v8.3 connected valid helper output to the top-level advice payload through an explicit/default-off adapter.
  - v8.4 locked prompt guard wording before UI/source extraction so candidate moves are not treated as confirmed selected moves.
  - v8.5 verified payload -> prompt -> mocked advice behavior offline before any actual Gemini call or UI/source integration.
  - v8.6 designed the controlled Gemini smoke criteria before any provider call.
  - v8.7 executed exactly one approved Gemini smoke with retry count 0 and PASS.
  - v8.8 closed the phase without code, UI, prompt, payload, or provider-call changes.
  - v9.0 designed source/UI integration without code changes and recommended deriving context from existing explicit/visible `opponent_moves` only.
  - v9.1 implemented the offline UI/source integration through the existing default-off checkbox and kept UI-visible opponent moves as unconfirmed/unselected candidates.
  - v9.2 verified the combined checkbox path offline with mocked provider calls only, including off/on prompts, all three optional contexts coexisting, visible UI moves as candidates, selected opponent move unknown, and empty opponent-source omission.
  - v9.3 polished the existing checkbox label/tooltip/status copy so it accurately describes the combined limited context behavior.
  - v9.4 closed the opponent move UI/source integration phase and recommended v10.0 Battle State Context Design.
  - v10.0 designed a safe `battle_state_context` contract before implementation, focused on known HP/state fields, field state, boosts, weather, terrain, screens, hazards, room effects, and explicit unknown/unsupported boundaries.
  - v10.1 locked the fixture-level payload contract and kept `partial` / `explicit` confidence future-only.
  - v10.2 implemented a standalone helper that normalizes only allowed visible/explicit source data into the contract shape.
  - v10.3 added an explicit/default-off payload adapter for caller-provided `battle_state_context`, with validation, omission for empty contexts, and coexistence with existing optional contexts.
  - v10.4 added prompt guard wording for explicit `battle_state_context` prompts while keeping default/off prompts unchanged.
  - v10.5 verified the offline mocked advice flow for explicit `battle_state_context`, including payload preservation, prompt guard preservation, coexistence with existing optional contexts, and mocked response safety.
  - v10.6 inventoried current UI sources: self/opponent species and HP percent are safe visible UI facts after normalization, user-confirmed item profiles need design before connection, and status/boosts/field/known-condition fields must remain unknown until explicit UI sources exist.
  - v10.7 designed checkbox-based battle-state UI integration: checked should enable battle state with existing limited contexts, but the first implementation should extract only visible species/HP and leave item/status/boosts/field/known conditions unknown.
  - v10.8 implemented the species/HP-only source adapter without checkbox connection, payload-flow change, prompt guard change, provider call, or hidden-state inference.
  - v10.9 connected the existing limited-context checkbox to battle state using the species/HP-only adapter. Checked can now include all four limited contexts; unchecked omits battle state and guard.
  - v10.10 aligned checkbox tooltip/status copy with that behavior, including current Pokemon/HP snapshot wording and forbidden hidden-state/resolved-outcome certainty wording.
  - v10.11 verified the UI-selected checkbox off/on path with mocked provider only. Off omits battle state and guard; on includes all four limited contexts, visible species/HP battle state, unknown non-source fields, and the existing guard.
  - v10.12 closed the battle-state context UI phase for offline/mocked coverage. Current runtime support is species/HP snapshot only; actual Gemini smoke is still pending design and approval.
  - v11.0 designed the one-call controlled Gemini smoke and did not execute it.
  - No actual Gemini call is allowed unless T1 explicitly approves v11.1 one-call execution.
  - No Vertex AI call.
  - Keep `run_ui_selected_advice(...)` default behavior unchanged.
  - Do not make TurnPipeline always-on.
  - Do not make `turn_order_context` always-on.
  - Checkbox toggle must not call Gemini; only the existing advice button may start advice generation.
  - Do not start full Turn Engine implementation yet.
  - v11.1 may execute the controlled Battle State UI Gemini smoke only after explicit T1 approval for one actual call. If approval is absent, choose User-confirmed Item Boundary Design or Field State Source Design instead.
- v3.4 has already centralized item context guard metadata:
  - `ADVICE_ITEM_CONTEXT_GUARD_METADATA` contains mention labels, item-specific guard text, and forbidden wording metadata.
  - `advisor_client.py` still builds the prompt guard from visible `available=true` contexts.
  - payload filtering behavior is unchanged.
  - Choice Scarf remains protected in top-level `speed_context`.
- v4.1-v4.9 TurnSnapshot status:
  - `core/turn_state.py` defines serializable validated snapshot contracts.
  - `build_ui_advice_payload(..., turn_snapshot=None)` preserves old payloads when absent.
  - `llm/advisor_turn_snapshot.py` builds snapshots from UI-selected `battle_input`.
  - `run_ui_selected_advice(...)` attempts snapshot construction and falls back to existing advice when validation fails.
  - Snapshot mapping includes active species, slot index, HP percent, selected move, and known item profile/status only.
  - v4.6 smoke/preflight verified present snapshot, absent/fallback snapshot, prompt limitation, and unchanged damage/ko/item-context payload behavior.
  - v4.7 handoff doc: `docs/handoff_turn_snapshot_flow_v4.7.md`.
  - v4.8 dry-run script: `scripts/spike_turn_snapshot_debug.py`.
  - v4.8 sample report: `docs/debug_turn_snapshot_sample_v4.8.md`.
  - v4.9 closure doc: `docs/handoff_turn_snapshot_phase_closure_v4.9.md`.
  - Full Turn Engine, item trigger evaluation, item consumption, HP update, and speed/order simulation are not implemented.
- v5.0 Minimal Turn Engine MVP Design is complete:
  - `TurnSnapshot` remains selected/pre-turn input state.
  - `damage_estimate` remains the damage primitive.
  - `ko_context` remains limited damage-roll context.
  - existing item contexts remain additive advice surfaces.
  - recommended stages are `pre_turn`, `pre_move`, `damage`, `on_damage_before_ko`, `on_hit_or_damage_dealt`, `post_damage`, and `post_turn`.
  - `TurnEvent` is a candidate/known-modifier/not-simulated event contract, not final battle truth.
  - `TurnPipelineResult` is planning output with `simulated` defaulting to `none`; `limited` and future-compatible `full` are schema values, but v5.1 does not produce full simulation.
- v5.1 Turn Event Contract Implementation is complete:
  - `core.turn_event` defines `TurnEvent` and `TurnPipelineResult`.
  - contracts provide `to_dict()` / `from_dict(...)`.
  - `normalize_turn_event(...)` and `normalize_turn_pipeline_result(...)` are available.
  - stage, status, certainty, side, warnings, limitations, and events are validated/normalized.
  - `TurnPipelineResult.simulated` defaults to `none`.
  - v5.1 does not connect to `advisor_client.py`.
  - v5.1 does not insert turn pipeline output into the LLM payload.
  - v5.1 does not implement item trigger evaluation.
  - v5.1 does not implement item consumption, HP update, speed/order simulation, exact status/volatile resolution, or full Turn Engine behavior.
- v5.2 Item Context to TurnEvent Mapping Design is complete:
  - inventory covers `damage_estimate`, `ko_context`, `speed_context`, `speed_order_context`, `species_stat_item_context`, `type_boost_context`, `survival_context`, `resist_berry_context`, `chilan_berry_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, and `multi_hit_context`.
  - Light Ball maps to `damage` / `known_modifier` / `known`.
  - Quick Claw maps to `pre_move` / `candidate` / `possible`.
  - Focus Band and Focus Sash map to `on_damage_before_ko` / `candidate` / `possible`.
  - Chilan Berry maps to `on_damage_before_ko` / `candidate` / `likely` in the v5.2 design, while the v5.3 first-pass helper uses conservative `possible`.
  - recovery/flinch/critical/accuracy/multi-hit contexts remain later planning targets unless specifically scoped.
- v5.3 Item Context TurnEvent Mapper Implementation is complete:
  - `llm.advisor_turn_events` defines `build_turn_events_from_advice_payload(...)`.
  - input is an already-built move/context dictionary or advice payload fragment.
  - output is `tuple[TurnEvent, ...]`.
  - first mapping targets are Light Ball, Quick Claw, Focus Band / Focus Sash, and Chilan Berry.
  - only `available=true` contexts create events.
  - unavailable, blocked, or deferred contexts create no events.
  - stable order is `species_stat_item_context`, `speed_order_context`, `survival_context`, then `chilan_berry_context`.
  - there is no `advisor_client.py` connection.
  - there is no LLM payload connection.
  - there is no `TurnPipelineResult` creation or connection.
  - there is no full Turn Engine.
  - there is no trigger evaluation, item consumption, HP update, speed/order simulation, exact RNG, or payload filtering change.
- v5.4 TurnEvent Mapper Smoke / Fixture Coverage Expansion is complete:
  - mapper fixture coverage includes available Light Ball, Quick Claw, Focus Band, Focus Sash, and Chilan Berry.
  - negative coverage includes `available=false`, unavailable, blocked, deferred, unknown item ids, and malformed optional context shapes.
  - event ordering remains `species_stat_item_context`, `speed_order_context`, `survival_context`, then `chilan_berry_context`.
  - safety wording avoids claiming item consumption, exact post-turn HP, guaranteed move order, or full turn simulation.
  - there is still no `advisor_client.py` connection.
  - there is still no LLM payload connection.
  - there is still no `TurnPipelineResult` creation or connection.
- v5.5 TurnPipelineResult Fixture Contract Smoke is complete:
  - `build_turn_pipeline_result_from_advice_payload(...)` bundles mapper events into `TurnPipelineResult`.
  - default `simulated` is `limited`, not `full`.
  - `damage_estimate_ref` and `ko_context_ref` are references only.
  - limitations state that the result is not a full turn simulation, item consumption is not simulated, and HP updates/post-turn state are not simulated.
  - there is still no `advisor_client.py` connection.
  - there is still no LLM payload connection.
- v5.6 TurnPipeline Debug Report / Dry-run is complete:
  - `scripts/spike_turn_pipeline_debug.py` prints safe JSON fixture output.
  - `docs/debug_turn_pipeline_sample_v5.6.md` records the static sample report.
  - generated events include Light Ball, Quick Claw, Focus Sash, and Chilan Berry.
  - `simulated` remains `limited`.
  - limitations state that this is not a full turn simulation, item consumption is not simulated, and HP updates/post-turn state are not simulated.
  - there is still no `advisor_client.py` connection.
  - there is still no LLM payload connection.
- v5.7 TurnPipeline Payload Exposure Design is complete:
  - recommended eventual payload location is top-level `turn_pipeline`.
  - recommended exposure policy is default-off / explicit-only.
  - `turn_pipeline` must remain a limited planning/debug summary, not a full turn simulation.
  - `turn_pipeline` must not resolve RNG, item consumption, post-turn HP, speed ties, exact trigger results, or exact status resolution.
  - `damage_estimate` and `ko_context` remain primitives.
  - existing item contexts remain the current user-facing explanation surface.
  - v5.7 does not connect `TurnPipelineResult` to `advisor_client.py`.
  - v5.7 does not insert `turn_pipeline` into the LLM payload.
- v5.8 Optional TurnPipeline Payload Adapter Implementation is complete:
  - `build_ui_advice_payload(..., turn_pipeline=None)` supports explicit optional top-level `turn_pipeline`.
  - `_build_ui_selected_prompt(..., turn_pipeline=None)` can include pipeline limitations when explicitly supplied.
  - absent or `None` `turn_pipeline` preserves existing payload output.
  - supplied `TurnPipelineResult` or mapping values are normalized before insertion.
  - `simulated="full"` is rejected for advice payload exposure.
  - pipeline limitations are required.
  - event wording has narrow validation against resolved-result claims.
  - `run_ui_selected_advice(...)` does not auto-generate `TurnPipelineResult`.
  - `build_turn_pipeline_result_from_advice_payload(...)` remains disconnected from runtime advice flow.
  - v5.8 does not run actual Gemini calls.
- v5.9 TurnPipeline Payload Prompt Guard / Contract Documentation is complete:
  - prompt guard explicitly says candidate events are not resolved outcomes.
  - contract limitations state `turn_pipeline` does not replace `damage_estimate`, `ko_context`, or existing item contexts.
  - contract limitations state candidate events must not be described as consumed items, final HP, guaranteed order, or confirmed triggers.
  - event wording validation rejects narrow resolved-result claims for RNG, item consumption, post-turn HP, speed tie, trigger result, and full simulation wording.
  - absent or `None` `turn_pipeline` still preserves existing payload/prompt behavior.
  - v5.9 does not auto-generate `TurnPipelineResult`.
  - v5.9 does not run actual Gemini calls.
- v6.0 Minimal TurnPipeline Integration Design is complete:
  - compared advisor-client automatic generation, explicit flag generation, debug-only, and fixture-only options.
  - recommended v6.1 explicit/default-off generation adapter.
  - proposed `build_optional_turn_pipeline_for_advice_payload(...)`.
  - input should be an already-built advice payload.
  - output should be `TurnPipelineResult | None`.
  - default should return `None`.
  - explicit true should produce `simulated="limited"` only.
  - helper should not mutate payloads.
  - caller may pass the result to `build_ui_advice_payload(..., turn_pipeline=...)`.
  - `damage_estimate`, `ko_context`, and existing item contexts remain primitives/surfaces.
  - no automatic `run_ui_selected_advice(...)` generation is recommended.
  - no UI hard dependency is recommended.
  - no actual Gemini call, full Turn Engine, item consumption, HP update, speed/order simulation, RNG resolution, or exact trigger resolution is included.
- v6.1 Explicit TurnPipeline Generation Adapter is complete:
  - `llm.advisor_turn_events.build_optional_turn_pipeline_for_advice_payload(...)` exists.
  - `enable_turn_pipeline=False` or omitted returns `None`.
  - `enable_turn_pipeline=True` builds a limited `TurnPipelineResult` through the existing fixture/debug helper.
  - generated output keeps `simulated="limited"` and never produces full simulation.
  - helper does not mutate input payloads.
  - helper can be manually combined with `build_ui_advice_payload(..., turn_pipeline=...)`.
  - there is still no advisor-client automatic generation.
  - there is still no UI-selected advice flow automatic connection.
  - there is still no full Turn Engine, item trigger evaluation, item consumption, HP update, speed/order simulation, or actual Gemini call.
- v6.2 Explicit TurnPipeline Payload Smoke is complete:
  - fixture tests combine `build_optional_turn_pipeline_for_advice_payload(..., enable_turn_pipeline=True)` with `build_ui_advice_payload(..., turn_pipeline=...)`.
  - disabled generation returns `None` and preserves default payload output.
  - enabled generation creates `simulated="limited"` `TurnPipelineResult`.
  - explicit adapter insertion adds top-level `turn_pipeline`.
  - `damage_estimate`, `ko_context`, and existing item contexts remain present and unchanged.
  - prompt guard appears only when `turn_pipeline` is explicitly supplied.
  - there is still no advisor-client automatic generation.
  - there is still no UI-selected advice flow automatic connection.
  - there is still no actual Gemini call, full Turn Engine, item trigger evaluation, item consumption, HP update, speed/order simulation, or payload filtering change.
- v6.3 TurnPipeline UI / Advice Flow Integration Design is complete:
  - inspected the current path from `LLMAdvicePanel.advice_requested` through `MainWindow._start_llm_advice()`, `LLMAdviceWorker.run()`, `run_ui_selected_advice(...)`, `_build_ui_selected_prompt(...)`, and `build_ui_advice_payload(...)`.
  - compared UI checkbox/dev flag, payload-builder optional parameter, debug-only script, and advisor-client automatic generation candidates.
  - recommended v6.4 as explicit payload-builder/helper smoke, not UI runtime integration.
  - default UI-selected advice flow should remain unchanged.
  - `enable_turn_pipeline=True` should remain fixture/dev-only for the next step.
  - `damage_estimate`, `ko_context`, and existing item contexts remain primitives/surfaces.
  - `turn_pipeline` remains a limited timing/planning/debug summary.
  - there is still no production implementation, advisor-client automatic generation, UI-selected advice flow automatic connection, actual Gemini call, or full Turn Engine.
- v6.4 Explicit TurnPipeline Advice Payload Builder Smoke is complete:
  - omitted/default and explicit `enable_turn_pipeline=False` paths return `None`.
  - disabled/default paths preserve payload output and do not add `turn_pipeline`.
  - `enable_turn_pipeline=True` creates a `simulated="limited"` `TurnPipelineResult`.
  - manual `build_ui_advice_payload(..., turn_pipeline=result)` insertion adds top-level `turn_pipeline`.
  - prompt guard is absent without `turn_pipeline` and present with explicit `turn_pipeline`.
  - prompt guard states candidate events are not resolved outcomes and keeps no RNG/item consumption/post-turn HP resolution wording.
  - `damage_estimate`, `ko_context`, and existing item contexts remain present and unchanged.
  - `run_ui_selected_advice(...)` still does not call `build_optional_turn_pipeline_for_advice_payload(...)`.
  - there is still no advisor-client automatic generation, UI-selected advice flow automatic connection, actual Gemini call, full Turn Engine, item trigger evaluation, item consumption, HP update, speed/order simulation, or payload filtering change.
- v6.5 Explicit TurnPipeline Advice Flow Integration Design is complete:
  - compared `run_ui_selected_advice(..., enable_turn_pipeline=False)`, payload-builder-only, UI handler dev flag, UI checkbox, and always-on advisor-client generation candidates.
  - recommended v6.6 as Explicit TurnPipeline Advice Flow Dry-run.
  - default-off remains required.
  - actual Gemini calls must remain disabled in tests.
  - UI checkbox is still deferred.
  - `damage_estimate`, `ko_context`, and existing item contexts remain primitives/surfaces.
  - `turn_pipeline` remains a limited timing/planning/debug summary.
  - there is still no production implementation, advisor-client automatic generation, UI-selected advice flow automatic connection, UI checkbox, actual Gemini call, or full Turn Engine.
- v6.6 Explicit TurnPipeline Advice Flow Dry-run is complete:
  - `run_ui_selected_advice(..., enable_turn_pipeline=False)` now has a default-off dry-run flag.
  - default calls omit `turn_pipeline` and omit the TurnPipeline prompt guard.
  - explicit `enable_turn_pipeline=True` builds a limited TurnPipeline from the already-built advice payload.
  - explicit dry-run passes the result through the existing optional top-level payload adapter.
  - tests mock `call_gemini` and capture the prompt; no actual Gemini or Vertex AI call is made.
  - UI worker and advice panel still do not expose a checkbox or enable the flag.
  - `damage_estimate`, `ko_context`, and existing item contexts remain present.
  - there is still no full Turn Engine, item trigger evaluation, item consumption, HP update, speed/order simulation, or payload filtering change.
- v6.7 TurnPipeline Advice Flow Closure / Stability Report is complete:
  - closes the v5.3-v6.6 TurnPipeline advice-flow dry-run phase.
  - documents that explicit dry-run generation and optional payload insertion are possible, while default UI advice remains off.
  - documents that actual Gemini call, UI checkbox, user-facing advice button automatic enablement, full Turn Engine, item consumption, HP update, RNG/speed tie/exact trigger resolution are still not done.
  - records timing-sensitive perf instability around `test_item_damage_calculation_under_point_12ms_average` as a known issue.
  - recommends v6.8 Payload Snapshot Lockdown before Controlled Gemini Smoke.
- v6.8 Payload Snapshot Lockdown is complete:
  - uses plain pytest dictionary assertions, not an external snapshot plugin.
  - locks default, explicit-off, `turn_pipeline=None`, explicit dataclass, and explicit mapping payload shapes.
  - verifies prompt guard absence/presence with stable substring assertions.
  - verifies `simulated="limited"` and keeps `simulated="full"` rejected.
  - verifies `damage_estimate`, `ko_context`, and item contexts remain present.
  - still does not run actual Gemini or Vertex AI calls.
  - still does not add UI checkbox, user-facing advice button automatic enablement, full Turn Engine, item trigger evaluation, item consumption, HP update, speed/order simulation, or payload filtering changes.
- v6.9 Controlled Gemini Smoke Design is complete:
  - future smoke purpose is to check Gemini does not treat `turn_pipeline` as full simulation or resolved battle truth.
  - recommended fixture is one explicit-on TurnPipeline payload.
  - maximum actual Gemini calls is 1.
  - no retry.
  - stop on 429, `RESOURCE_EXHAUSTED`, API key, auth, billing/prepay, or provider routing errors.
  - PASS requires limited-planning wording, no resolved candidate events, no item consumption, no post-turn HP, no speed tie/RNG/exact trigger resolution, and no conflict with `damage_estimate` / `ko_context`.
  - FAIL includes claims like Quick Claw will activate, Focus Sash will be consumed, exact post-turn HP, full turn simulation proves the result, or `turn_pipeline` overrides damage/KO primitives.
  - v6.9 itself did not execute an actual Gemini or Vertex AI call.
- v6.10 Controlled Gemini Smoke Execution is complete:
  - actual Gemini calls: 1.
  - automatic retries: none.
  - Vertex AI calls: none.
  - result classification: PASS.
  - response treated damage estimate as default-assumption and not final battle damage.
  - response used possible/candidate wording for Quick Claw and Focus Sash.
  - response did not claim item consumption, exact post-turn HP, speed tie/RNG/exact trigger resolution, full turn simulation, or `turn_pipeline` override of damage/KO primitives.
  - synthetic fixture note: Light Ball-on-Charizard wording was awkward but not a TurnPipeline safety failure.
  - `logs/token_usage.jsonl` remains uncommitted and must not be reset.

Repo / branch / remote checks first:
1. Run `git status --short --branch`.
2. Confirm the branch is `master`.
3. Confirm tracking is `my_pochamps/master`.
4. Confirm there are no unexpected ahead commits unless T1/T2 explicitly approved them.
5. `logs/token_usage.jsonl` may be locally modified. Do not commit it and do not reset it.
6. Do not commit `.env`, secrets, API keys, billing information, token-log contents, or `docs/handoff_capsule_v1.1.md`.
7. Do not print API keys, secrets, billing details, or token-log contents.

Current actual Gemini verification status:

1. Focus Band within `survival_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.5: PASS.
   - Actual advice used limited wording: Focus Band may occasionally survive.
   - Forbidden wording observed: none.
   - Context fields:
     - `survival_context.available=true`
     - `survival_effect.type=focus_band`
     - raw damage/rolls unchanged
     - `ko_context` unchanged

2. Quick Claw `speed_order_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.5: PASS.
   - Actual advice used limited wording: Quick Claw may affect move order.
   - Forbidden wording observed: none.
   - Context fields:
     - `speed_order_context.available=true`
     - `speed_order_effect.type=quick_claw`
     - raw damage/rolls unchanged
     - `ko_context` unchanged

3. Light Ball `species_stat_item_context`
   - Implementation: complete after v3.1 damage estimate integration.
   - Payload preflight: PASS.
   - Actual Gemini status after v3.1.1: PASS.
   - Actual advice mentioned Pikachu and user-confirmed Light Ball.
   - Forbidden wording observed: none.
   - v2.5 weakness:
     - Gemini said current damage estimates do not include the stat boost from Pikachu's user-confirmed Light Ball.
     - Preferred wording is limited explanatory context: Light Ball may boost Pikachu's offensive stats in the underlying calculation, is species-specific to Pikachu, and is not a final KO guarantee.
   - v2.6 polish:
     - Prompt/contract now tells Gemini to describe available Light Ball as a Pikachu-specific offensive item context.
     - Prompt/contract now says not to say Light Ball is not included or not modeled when the available context is present.
   - v2.6.1 result:
     - Payload preflight stayed PASS.
     - Gemini still said damage estimates do not include the effect of the user-confirmed Light Ball.
     - Classification: wording guardrail failure / Gemini over-inference from generic default-assumption limitations.
   - v2.7 guard:
     - Prompt now lists visible available item contexts and requires mentioning each directly relevant context at least once.
     - Prompt forbids describing available item effects as unavailable, unmodeled, not included, not reflected, no item is considered, assuming no item, without item effects, or default no-item assumption.
   - v2.7.1 result:
     - Payload preflight stayed PASS.
     - Required mention guard was present and included the Light Ball label.
     - Gemini mentioned Light Ball as a Pikachu-specific offensive item context.
     - Gemini still included generic "no item effects" wording, so this remains PARTIAL.
   - v2.8 implementation:
     - Added a Light Ball-specific guard for `species_stat_item_context.available=true`.
     - The prompt now says not to say or imply that no item effects are included for this move or recommendation.
     - The prompt now forbids generic no-item/default-assumption wording such as no item effects, without item effects, assuming no item, default no-item assumption, item not included, item not modeled, or item not reflected.
     - The prompt now says that when `item_effects` marks the supported modifier as applied, describe the estimate as default assumptions plus the supported Light Ball modifier.
   - v2.8.1 result:
     - Payload preflight stayed PASS.
     - Required mention guard and Light Ball-specific no-item residue guard were present.
     - Gemini generated a response and mentioned Light Ball as a Pikachu-specific offensive item context.
     - Gemini still described the estimate with `no item` default assumptions and said the Light Ball boost was not applied.
     - Classification: FAIL / no-item residue still present.
   - v3.1 implementation:
     - Eligible user-confirmed Pikachu + Light Ball is applied in advisor damage estimates for damaging physical/special moves.
     - `species_stat_item_context` is now a sibling explanation of applied `damage_estimate.item_effects`.
     - Raw rolls and `ko_context` follow adjusted estimate rolls for eligible Light Ball only.
     - Non-Pikachu, unconfirmed, defender-side, and status/unsupported-category Light Ball remain unapplied.
   - v3.1.1 result:
     - Payload preflight stayed PASS.
     - Gemini described Water Pulse as default assumptions plus the supported Light Ball modifier.
     - Gemini said Light Ball is Pikachu-specific and applied for Pikachu in the damage estimate.
     - Forbidden wording: none.
     - Classification: PASS.

4. Chilan Berry `chilan_berry_context`
   - Implementation: complete.
   - Payload preflight: PASS.
   - Actual Gemini status after v2.7.1: PASS.
   - Actual advice mentioned Chilan Berry's potential reduction for Tackle.
   - Forbidden wording observed: none.
   - v2.5 weakness:
     - Gemini did not explicitly say Normal-type.
     - Gemini used weak "not included in the raw damage estimate" wording rather than preferred limited-context phrasing.
   - Preferred wording: Chilan Berry may reduce damage from a Normal-type move; this is limited context and not integrated into final KO odds.
   - v2.6 polish:
     - Prompt/contract now tells Gemini to describe available Chilan Berry as a Normal-type limited context.
     - Prompt/contract now says raw damage rolls and ko_context remain based on the current calculator, and not to say Chilan Berry is not included or not modeled when the available context is present.
   - v2.6.1 result:
     - Payload preflight stayed PASS.
     - Gemini did not use exact forbidden Chilan wording.
     - Gemini still omitted the positive Normal-type limited context and used generic no-item default-assumption wording.
     - Classification: wording guardrail weakness / context omission.
   - v2.7 guard:
     - Prompt now lists visible available item contexts and requires mentioning each directly relevant context at least once.
     - Prompt labels Chilan Berry / chilan_berry_context as Normal-type limited context.
   - v2.7.1 result:
     - Payload preflight stayed PASS.
     - Required mention guard was present and included the Chilan Berry label.
     - Gemini described Chilan Berry as a Normal-type limited context.
     - Gemini preserved that raw damage rolls and ko_context remain based on the current calculator.
     - Forbidden wording: none.
   - Treat as PASS unless later changes regress it.

Global prohibitions:
- No Gemini actual PASS from payload preflight alone.
- No new item implementation.
- No new mechanics.
- No payload filtering behavior change unless explicitly approved.
- No prompt hardening behavior change unless explicitly approved.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No ko_context calculation change.
- No final KO probability.
- No final move order.
- No Turn Engine.
- No item consumption.
- No legal fixture mutation.
- No fixture mutation.
- No UI or sample additions.
- No threshold changes.
- No skip or xfail.
- No logs, `.env`, secrets, API keys, billing details, token-log contents, or `docs/handoff_capsule_v1.1.md` commit.

Suggested tests after any documentation or approved wording work:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- `uv run pytest tests/test_advisor_damage_estimate.py -q`
- `uv run pytest tests/test_damage_perf.py -q`
- `uv run pytest -q`
- If perf is timing-sensitive, rerun isolated/perf-file tests and report medians/thresholds. Do not change thresholds, skip, or xfail.

Documentation expectations:
- Record follow-up decisions in `docs/PROGRESS.md`.
- If status changes, update `docs/handoff_pending_gemini_verification_v1.8.md`, which is now a closed queue / historical handoff document.
- Keep `docs/handoff_capsule_v1.1.md` untouched.
```

## Maintainer Notes

- The old HTTP 429 blocker is no longer the current Developer API state after v2.5.
- Focus Band and Quick Claw reached actual Gemini PASS.
- Light Ball reached actual Gemini PASS after v3.1.1.
- Chilan Berry reached actual Gemini PASS after v2.7.1.
- The original item-context pending verification queue is closed as of v3.2.
- v3.4 centralized item context guard metadata without changing filtering behavior.
- Larger next direction: v6.21 TurnPipeline UI Phase Closure, with v6.21 UI Copy Polish only if wording / layout refinement is requested. Keep additional actual Gemini calls disabled unless T1/T2 explicitly approve a separate one-call smoke.
- v2.7.1 used Developer API only and did not use Vertex AI.
- Use "Pokemon" rather than non-ASCII variants in new handoff text unless a file already requires non-ASCII.
- v13.5 type-aware deterministic results use selected resolved types, ordinary
  STAB, and the base type chart only; do not expand them to ability/item
  overrides, Tera, field modifiers, or final outcomes without a new contract.
- v13.6 deliberately blocks screen resolution pending a trusted battle-format
  source; do not infer singles/doubles from the selected UI state.
- v13.7 screen reduction requires an explicit normalized singles/doubles value.

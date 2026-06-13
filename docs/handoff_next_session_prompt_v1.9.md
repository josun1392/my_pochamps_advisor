# Next Session Prompt v1.9 - Gemini Verification Follow-Up

This document is a copy-paste-ready prompt for the next T3 session. It preserves the v2.5 Developer API Prepay recovery verification results, the v3.2 item-context verification closure, the v3.4 item context guard registry cleanup, the v4.1-v4.9 TurnSnapshot phase closure, the v5.0 Minimal Turn Engine MVP design, the v5.1 Turn Event contract implementation, the v5.2 item-context-to-TurnEvent mapping design, the v5.3 helper-level mapper implementation, the v5.4 mapper smoke / fixture coverage expansion, the v5.5 TurnPipelineResult fixture smoke, the v5.6 TurnPipeline debug dry-run, the v5.7 TurnPipeline payload exposure design, the v5.8 optional TurnPipeline payload adapter, the v5.9 TurnPipeline prompt/contract guard, the v6.0 Minimal TurnPipeline integration design, and the v6.1 explicit TurnPipeline generation adapter.

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

Payload preflight PASS still does not imply actual Gemini PASS. Chilan Berry reached actual Gemini PASS after v2.7.1. Light Ball reached actual Gemini PASS after v3.1.1. The original Focus Band / Quick Claw / Light Ball / Chilan Berry pending queue is closed.

## Copy-Paste Prompt

```text
T3, continue after v6.1 Explicit TurnPipeline Generation Adapter.

Goal:
- Do not add new item contexts.
- Do not run extra Gemini calls unless T1/T2 explicitly approve them.
- Treat `turn_snapshot` as selected/pre-turn known state only, not full Turn Engine output.
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
  - v6.2 Explicit TurnPipeline Adapter Smoke / Integration Preflight
- Reason:
  - v6.1 now provides one explicit/default-off helper that can build `TurnPipelineResult` from an already-built advice payload.
  - The helper returns `None` by default and only builds a limited pipeline when `enable_turn_pipeline=True`.
  - It does not mutate payloads, call Gemini, or change `run_ui_selected_advice(...)` default behavior.
  - The existing optional top-level `turn_pipeline` adapter remains the only payload insertion path, and any v6.2 work should keep this manual/explicit.
  - Keep actual Gemini calls disabled unless T1/T2 explicitly approve them.
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
- Larger next direction: v6.2 explicit TurnPipeline adapter smoke / integration preflight before any automatic pipeline generation or state mutation.
- v2.7.1 used Developer API only and did not use Vertex AI.
- Use "Pokemon" rather than non-ASCII variants in new handoff text unless a file already requires non-ASCII.

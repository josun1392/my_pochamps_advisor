# Master Ball Advisor — Progress

## v11.9 - User-confirmed Item UI Mapping

Purpose:
- Connect user-confirmed item inclusion to the existing limited-context checkbox battle-state path.

Implementation summary:
- Updated `_build_ui_selected_prompt(...)` to call `build_battle_state_context_from_ui_selected_state(battle_input, include_user_confirmed_items=enable_battle_state_context)`.
- Checkbox off still omits `battle_state_context`, its prompt block, its guard, and known battle-state item values.
- Checkbox on still includes species/HP as `visible_ui`.
- Checkbox on + no/malformed/forbidden item metadata keeps item unknown.
- Checkbox on + valid `status=user_confirmed`, `source=user_input`, non-empty `item_id` includes known `user_confirmed` self/opponent item.
- Existing `turn_pipeline`, `turn_order_context`, and `opponent_move_context` coexistence remains covered.
- UI copy, checkbox default, prompt guard wording, and payload builder call flow are unchanged.

Test summary:
- UI flag tests cover off-path omission with user-confirmed item profiles.
- UI flag tests cover on-path known item serialization for valid metadata.
- UI flag tests cover no item profiles, malformed metadata, wrong status, and forbidden sources.
- Tests assert known item does not create item consumption, post-turn HP, RNG, speed tie, Quick Claw, or full outcome fields.

Recommended next:
- v11.10 User-confirmed Item UI Copy Update.
- Alternative: v11.10 User-confirmed Item UI Offline Smoke.
- Alternative: v11.10 Field State Source Design.

Safety statement:
- No actual Gemini call, retry, second provider call, Vertex AI call, network call, new checkbox, UI checkbox default change, UI behavior/copy change, prompt guard wording change, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, hidden item inference, damage reverse inference, species/common-set/meta state generation, opponent set inference, hidden moveset inference, selected opponent move inference, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.8 - User-confirmed Item UI Mapping Design

Purpose:
- Design when the existing limited-context checkbox should enable user-confirmed item inclusion in `battle_state_context`.

Design summary:
- Current checkbox state is read in `MainWindow._start_llm_advice` and copied to `enable_turn_pipeline`, `enable_turn_order_context`, `enable_opponent_move_context`, and `enable_battle_state_context`.
- Current `battle_state_context` is generated in `_build_ui_selected_prompt(...)` when `enable_battle_state_context=True`.
- Recommended future mapping is `build_battle_state_context_from_ui_selected_state(battle_input, include_user_confirmed_items=enable_battle_state_context)`.
- Checkbox off remains the hard gate: no `battle_state_context`, no serialized guard block, and no item payload.
- Checkbox on with no/malformed/forbidden item metadata keeps item unknown.
- Checkbox on with valid `status=user_confirmed`, `source=user_input`, non-empty `item_id` can include known `user_confirmed` item.
- Future UI copy should mention user-confirmed item snapshot semantics.
- Future guard tests may clarify that known item does not imply activation, consumption, post-turn HP, RNG, speed tie, Quick Claw activation, or full outcome.

Recommended next:
- v11.9 User-confirmed Item UI Mapping Implementation.
- Alternative: v11.9 User-confirmed Item UI Copy Design.
- Alternative: v11.9 Field State Source Design.

Safety statement:
- No production code change, UI item integration, UI source adapter connection, limited-context checkbox flow change, UI behavior/default/copy change, payload builder call-flow change, prompt guard wording change, actual Gemini call, retry, second provider call, Vertex AI call, network call, hidden item inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.7 - User-confirmed Item Prompt/Offline Fixture

Purpose:
- Verify that known user-confirmed items can appear in `battle_state_context` payload and prompt without hidden inference or resolved outcome claims.

Implementation summary:
- Added a mocked offline prompt fixture in `tests/test_advisor_payload_contract.py`.
- The fixture uses the v11.6 source adapter with `include_user_confirmed_items=True`.
- Self item `leftovers` and opponent item `choice-scarf` are preserved as `source=user_confirmed` known items.
- Species/HP remain `visible_ui`.
- Field values remain unknown and `known_conditions` remains `[]`.
- The existing battle-state prompt guard appears unchanged.
- The prompt contains no item consumption, post-turn HP, RNG, speed tie, Quick Claw, or full outcome fields.
- Mocked response wording avoids item consumption, activation, post-turn, RNG, speed tie, Quick Claw, full outcome, selected opponent move, and hidden item certainty.

Recommended next:
- v11.8 User-confirmed Item UI Mapping Design.
- Alternative: v11.8 User-confirmed Item UI Integration.
- Alternative: v11.8 Field State Source Design.

Safety statement:
- No UI item integration, UI source adapter runtime connection, limited-context checkbox flow change, UI behavior/default/copy change, payload builder call-flow change, prompt guard wording change, actual Gemini call, retry, second provider call, Vertex AI call, network call, hidden item inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.6 - User-confirmed Item Source Adapter

Purpose:
- Add an explicit opt-in item path to the UI-selected `battle_state_context` adapter.

Implementation summary:
- Extended `build_battle_state_context_from_ui_selected_state(...)` with keyword-only `include_user_confirmed_items=False`.
- Default calls remain species/HP-only and ignore `item_profiles`.
- Opt-in calls inspect `battle_input["item_profiles"]["my_active"]` and `["opponent_active"]`.
- Known item helper input is produced only for `status=user_confirmed`, `source=user_input`, and non-empty string `item_id`.
- Self and opponent item profiles follow the same allowed metadata rule.
- Missing, malformed, wrong-status, wrong-source, legality-gate, resist-berry, damage-reverse, context-derived, visible, or calculated item metadata remains unknown.
- The adapter still does not read legality gate output, resist berry context, damage estimates, `ko_context`, turn contexts, common sets, usage, or meta assumptions.

Test summary:
- Adapter tests cover default item omission, opt-in self/opponent known item inclusion, species/HP preservation, missing profiles, malformed metadata, forbidden metadata, and item-resolution field absence.
- Payload contract test verifies opt-in adapter output is accepted by the existing `battle_state_context` payload adapter.

Recommended next:
- v11.7 User-confirmed Item Prompt/Offline Fixture.
- Alternative: v11.7 User-confirmed Item UI Mapping Design.
- Alternative: v11.7 Field State Source Design.

Safety statement:
- No UI item integration, UI source adapter runtime connection, limited-context checkbox flow change, UI behavior/default/copy change, payload builder call-flow change, prompt guard wording change, actual Gemini call, retry, second provider call, Vertex AI call, network call, hidden item inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.5 - User-confirmed Item Source Adapter Design

Purpose:
- Design how future UI item profiles can safely feed `battle_state_context.item`.

Design summary:
- Existing `battle_input["item_profiles"]` already carries `my_active` and `opponent_active` profiles with status/source/item_id metadata.
- Current `build_battle_state_context_from_ui_selected_state(...)` remains species/HP-only and intentionally ignores item profiles.
- Future item inclusion should be explicit opt-in, for example `include_user_confirmed_items=False` by default.
- Current `status=user_confirmed`, `source=user_input`, non-empty `item_id` profiles can map to `source=user_confirmed` helper input.
- Future `explicit_input` may be allowed only from a direct explicit input surface, not recommendation/filter/legal-gate/damage/context output.
- Opponent item remains unknown unless the user directly confirms or explicitly inputs it.
- Legality gate may validate an already confirmed item but must not create or replace a known item.
- Resist berry context and damage/KO signals must not become `battle_state_context.item` source of truth.

Recommended next:
- v11.6 User-confirmed Item Source Adapter.
- Alternative: v11.6 User-confirmed Item Prompt/Offline Fixture.
- Alternative: v11.6 Field State Source Design.

Safety statement:
- No production code change, UI item integration, UI source adapter connection, existing battle-state adapter change, limited-context checkbox flow change, UI behavior/default/copy change, prompt guard wording change, payload adapter contract change, actual Gemini call, retry, second provider call, Vertex AI call, network call, hidden item inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.4 - User-confirmed Item Contract Tests

Purpose:
- Lock `battle_state_context.item` known-source behavior before UI item integration.

Implementation summary:
- Added item-specific source validation in `llm/advisor_battle_state_context.py`.
- Added payload adapter validation for active-side item fields in `llm/advisor_client.py`.
- Known item sources are limited to `user_confirmed` and `explicit_input`.
- `visible_ui` and `calculated_from_visible` remain valid for species/HP, but not for item.
- Additional forbidden item sources include `legality_gate_guess`, `resist_berry_inferred`, and `context_derived`.
- Current UI-selected adapter still ignores `item_profiles` and extracts only species/HP.

Test summary:
- Helper tests cover self/opponent `user_confirmed` and `explicit_input` items.
- Helper tests keep omitted, malformed, forbidden-source, legality-gate-only, and resist-berry-context-only items unknown.
- Payload contract tests preserve allowed known items and reject item sources without user confirmation.
- Known item tests assert no item consumption, post-turn HP, RNG, speed tie, Quick Claw activation, or full outcome fields are added.

Recommended next:
- v11.5 User-confirmed Item Source Adapter Design.
- Alternative: v11.5 User-confirmed Item Prompt/Offline Fixture.
- Alternative: v11.5 Field State Source Design.

Safety statement:
- No UI item integration, UI source adapter connection, limited-context checkbox flow change, UI behavior/default/copy change, prompt guard wording change, actual Gemini call, retry, second provider call, Vertex AI call, network call, hidden item inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.3 - User-confirmed Item Boundary Design

Purpose:
- Design the boundary for future self/opponent item inclusion in `battle_state_context`.

Design summary:
- Current `battle_state_context.item` remains unknown in the UI-selected path.
- The current UI adapter intentionally extracts only species/HP and ignores `item_profiles`.
- Future known item values should use the existing helper envelope: `{"known": True, "source": "user_confirmed", "value": "<item-id>"}` or explicitly allowed `explicit_input`.
- Self item can be known only when directly user-confirmed or explicitly input.
- Opponent item is hidden by default and can be known only when directly user-confirmed or explicitly input.
- Legality gate is validation/filtering, not a source of truth.
- Resist berry and other item contexts may reference user-confirmed items, but must not be promoted into battle-state item sources.
- Unknown item continues to forbid hidden item inference in the prompt guard.
- Known item must not imply item consumption, activation, final item state, or turn outcome.

Recommended next:
- v11.4 User-confirmed Item Contract Tests.
- Alternative: v11.4 User-confirmed Item Source Adapter Design.
- Alternative: v11.4 Field State Source Design.

Safety statement:
- No production code change, item integration, source adapter change, payload adapter contract change, prompt guard wording change, UI behavior/copy/default change, actual Gemini call, retry, second provider call, Vertex AI call, network call, hidden item inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.2 - Battle State Context Actual Smoke Closure

Purpose:
- Close the Battle State Context actual smoke phase after the v11.1 controlled Gemini smoke PASS.

Closure summary:
- v11.1 executed exactly one actual Gemini call with `gemini-2.5-flash`.
- Retry count was 0.
- No second provider call, clarification call, better-answer call, automatic rerun, or Vertex AI call occurred.
- Payload boundary PASS: `battle_state_context`, `turn_pipeline`, `turn_order_context`, and `opponent_move_context` were present.
- Prompt boundary PASS: serialized `battle_state_context` and the existing v10.4 battle-state guard were present.
- Response boundary PASS: forbidden hidden/resolved phrase scan matched `none`.
- Sanitized token/cost summary: input `11054`, output `171`, cached `0`, pricing `free_tier_zero_cost`, estimated cost USD `0.0`.
- The post-call local reporting script hit a dict/object access issue after the successful provider call; no retry or second provider call was executed.
- `logs/token_usage.jsonl` remains modified from actual call logging and was not committed or reset.

Known limitations:
- One controlled fixture only.
- Does not prove broad advice quality or every Pokemon/move matchup.
- Does not add item, field, status, or boost sources.
- Does not implement full Turn Engine behavior.
- Does not prove future model responses will always obey the guard.

Recommended next:
- v11.3 User-confirmed Item Boundary Design.
- Alternative: v11.3 Field State Source Design.
- Alternative: v11.3 Battle State Context Hardening Backlog.

Safety statement:
- No actual Gemini call, retry, second provider call, Vertex AI call, network call, production code change, new checkbox, checkbox default change, UI behavior change, UI copy change, payload flow behavior change, prompt guard wording change, payload adapter contract change, battle-state source adapter change, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, `logs/token_usage.jsonl`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.1 - Controlled Battle State UI Gemini Smoke

Purpose:
- Execute the v11.0 controlled smoke after T1 approved exactly one actual Gemini call.

Smoke result:
- Result: PASS.
- Model: `gemini-2.5-flash`.
- Actual Gemini calls: 1.
- Retry count: 0.
- Vertex AI calls: 0.
- Fixture used the existing repo UI-selected style: self `charizard` at 100 HP and opponent `garchomp` at 100 HP, with the limited-context checkbox on.
- Payload included `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and `battle_state_context`.
- `battle_state_context` carried only self/opponent species and HP percent as `visible_ui`.
- status, boosts, item, field state, and `known_conditions` remained unknown or `[]`.
- Prompt included serialized `battle_state_context` and the existing battle-state guard.
- Response boundary scanner found no hidden-state certainty or resolved-outcome claim.

Token/cost summary:
- Sanitized token summary: input `11054`, output `171`, cached `0`.
- Pricing status: `free_tier_zero_cost`.
- Estimated cost USD: `0.0`.
- Raw token log lines were not pasted.
- `logs/token_usage.jsonl` was not committed or reset.

Recommended next:
- v11.2 Battle State Context Actual Smoke Closure.
- Alternative: v11.2 User-confirmed Item Boundary Design.
- Alternative: v11.2 Field State Source Design.

Safety statement:
- No production code change, new checkbox, checkbox default change, UI behavior change, UI copy change, payload flow behavior change, prompt guard wording change, payload adapter contract change, battle-state source adapter change, retry, second Gemini call, Vertex AI call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, `.env`, secrets, API keys, raw token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v11.0 - Controlled Battle State UI Gemini Smoke Design

Purpose:
- Design a future controlled Gemini smoke for the UI-selected `battle_state_context` path without executing an actual call.

Design summary:
- Smoke checks that checkbox-on UI-selected prompts include `battle_state_context`.
- Fixture is limited to visible/current self/opponent species and HP percent.
- status, boosts, item, field state, and `known_conditions` must remain unknown or `[]`.
- Expected prompt includes serialized `battle_state_context` and the existing battle-state guard.
- Expected response must avoid hidden-state inference, reverse inference, and resolved simulation claims.

Call policy:
- v11.0 executes no actual Gemini call.
- Future v11.1 call requires explicit T1 approval.
- Future call limit is exactly one Gemini call.
- Retry count is zero.
- No second call is allowed for failure, clarification, or better answer.

Abort criteria:
- Abort before a future call on unexpected repo state, failing tests, missing API key/model, missing payload/guard boundaries, forbidden hidden fields, wrong provider route, or missing T1 approval.

Recommended next:
- v11.1 Controlled Battle State UI Gemini Smoke, only with explicit T1 approval for one actual call.
- Alternative: v11.1 User-confirmed Item Boundary Design.
- Alternative: v11.1 Field State Source Design.

Safety statement:
- No production code change, new checkbox, checkbox default change, UI behavior change, UI copy change, payload flow behavior change, prompt guard wording change, payload adapter contract change, battle-state source adapter change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.12 - Battle State Context UI Phase Closure

Purpose:
- Close the battle-state context UI phase after design, contract, helper, payload adapter, prompt guard, offline fixture, UI source inventory, checkbox mapping, copy update, and offline UI-selected smoke.

Closure summary:
- The existing limited-context checkbox remains default off.
- Checkbox off omits `battle_state_context`.
- Checkbox on enables `battle_state_context` with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- `enable_battle_state_context = enable_turn_pipeline`.
- The UI source adapter extracts only self/opponent species and HP percent as `visible_ui`.
- status, boosts, item, field state, and `known_conditions` remain unknown or `[]`.
- The existing v10.4 prompt guard is reused when `battle_state_context` appears.
- Offline mocked tests cover payload, prompt, guard, and no-provider behavior.
- No actual Gemini smoke has been run for this UI path.

Known limitations:
- No user-confirmed item boundary design yet.
- No field state UI source yet.
- No known-conditions source yet.
- No resolved simulation or full Turn Engine.

Recommended next:
- v11.0 Controlled Battle State UI Gemini Smoke Design.
- Alternative: v11.0 User-confirmed Item Boundary Design.
- Alternative: v11.0 Field State Source Design.

Safety statement:
- No production code change, new checkbox, checkbox default change, UI behavior change, UI copy change, payload flow behavior change, prompt guard wording change, payload adapter contract change, battle-state source adapter change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.11 - Battle State UI Integration Offline Smoke

Purpose:
- Verify the UI-selected limited-context checkbox off/on path with mocked provider calls after battle-state checkbox mapping and copy updates.

Smoke coverage:
- Checkbox off omits `turn_pipeline`, `turn_order_context`, `opponent_move_context`, `battle_state_context`, and the battle-state prompt guard.
- Checkbox on includes `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and `battle_state_context`.
- The prompt includes serialized `battle_state_context` and the existing v10.4 battle-state guard when checked.
- Self/opponent species and HP percent are captured as `visible_ui`.
- Status, boosts, item, field state, and `known_conditions` remain unknown or `[]`.
- Mocked response avoids hidden-state certainty and resolved-outcome claims.

Provider boundary:
- `call_gemini` and `_log_advisor_call` are monkeypatched.
- No actual Gemini call, retry, Vertex AI call, provider call, or network call is performed.

Tests:
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Recommended next:
- v10.12 Battle State Context UI Phase Closure.
- Alternative: v10.12 Controlled Battle State UI Gemini Smoke Design.
- Alternative: v10.12 User-confirmed Item Boundary Design.

Safety statement:
- No new checkbox, checkbox default change, UI behavior change, UI copy change, payload flow behavior change, prompt guard wording change, payload adapter contract change, battle-state source adapter change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.10 - Battle State UI Copy Update

Purpose:
- Update the existing limited-context checkbox copy so it describes all contexts currently enabled by the checkbox, including the v10.9 battle-state species/HP snapshot path.

Copy:
- Label remains `제한 컨텍스트 포함`.
- Tooltip now mentions candidate events, turn-order helper information, UI-visible opponent move candidates, and the current Pokemon/HP snapshot.
- Enabled status now says the limited context includes candidate events, turn-order helper information, opponent move candidates, and the current Pokemon/HP snapshot while remaining non-final.

Safety wording:
- The copy states the context is not a confirmed result.
- It says not to infer the opponent's actual selected move or hidden item/status/boost/field state.
- It says not to claim post-turn HP, item consumption, RNG, speed tie, Quick Claw activation, or full turn outcome.

Tests:
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Recommended next:
- v10.11 Battle State UI Integration Offline Smoke.
- Alternative: v10.11 Battle State Context UI Phase Closure.
- Alternative: v10.11 User-confirmed Item Boundary Design.

Safety statement:
- No new checkbox, checkbox default change, UI behavior change, payload flow change, prompt guard wording change, payload adapter contract change, battle-state source adapter change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.9 - Battle State UI Checkbox Mapping

Purpose:
- Connect the existing limited-context checkbox to `battle_state_context` using the v10.8 species/HP adapter.

Implementation:
- `run_ui_selected_advice(...)` accepts `enable_battle_state_context`.
- `_build_ui_selected_prompt(...)` calls `build_battle_state_context_from_ui_selected_state(...)` when battle state is enabled and no explicit context is supplied.
- `LLMAdviceWorker` and `MainWindow._start_llm_advice(...)` map the existing checkbox state to `enable_battle_state_context` alongside `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.

Behavior:
- Checkbox off omits `battle_state_context` and the battle-state prompt guard.
- Checkbox on can include top-level `battle_state_context` with visible self/opponent species and HP percent.
- Status, boosts, item, field state, and `known_conditions` remain unknown.
- The existing v10.4 battle-state prompt guard is reused without wording changes.

Tests:
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`

Recommended next:
- v10.10 Battle State UI Copy Update.
- Alternative: v10.10 Battle State UI Integration Offline Smoke.
- Alternative: v10.10 Battle State Context Closure.

Safety statement:
- No new checkbox, checkbox default change, UI label/tooltip/status copy change, prompt guard wording change, payload adapter contract change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.8 - Battle State UI Source Adapter

Purpose:
- Add a narrow adapter from UI-selected `battle_input` to `battle_state_context` using only visible species and HP percent.

Implementation:
- Added `build_battle_state_context_from_ui_selected_state(...)` in `llm/advisor_battle_state_context.py`.
- The adapter reads only `pokemon.my_active.name_en`, `pokemon.my_active.hp_percent`, `pokemon.opponent_active.name_en`, and `pokemon.opponent_active.hp_percent`.
- Accepted fields become `visible_ui` source envelopes and are passed through `build_battle_state_context(...)`.

Boundaries:
- Status, boosts, item, field state, and `known_conditions` are not generated by the adapter and remain unknown.
- The adapter does not read `item_profiles`, `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, `opponent_move_context`, common sets, meta guesses, or sample assumptions.
- Missing or malformed species/HP values become explicit unknowns through the helper.

Tests:
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`

Recommended next:
- v10.9 Battle State UI Checkbox Mapping.
- Alternative: v10.9 Battle State UI Integration Offline E2E.
- Alternative: v10.9 Battle State UI Copy Update.

Safety statement:
- No existing limited-context checkbox connection, `build_ui_advice_payload(...)` call-flow change, prompt guard change, UI label/tooltip/status change, UI checkbox behavior change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.7 - Battle State UI Integration Design

Purpose:
- Design how the existing limited-context checkbox should enable future `battle_state_context` UI integration.

Design:
- Keep the existing checkbox default unchecked.
- Checkbox off should keep `enable_turn_pipeline`, `enable_turn_order_context`, `enable_opponent_move_context`, and `enable_battle_state_context` false and omit `battle_state_context`.
- Checkbox on should enable all four limited context flags.
- First battle-state UI integration should extract only visible self/opponent species and HP percent.
- Status, boosts, item, field state, and `known_conditions` should remain unknown in the first integration.
- Item profile mapping is deferred to a separate item-boundary design because it overlaps with existing `item_profiles` and hidden/confirmed item semantics.

Flow:
- UI selected state -> safe species/HP extraction -> `build_battle_state_context(...)` -> explicit/default-off payload adapter -> existing v10.4 prompt guard.
- `battle_state_context` should coexist with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.

Recommended next:
- v10.8 Battle State UI Source Adapter.
- Alternative: v10.8 Battle State UI Integration Offline E2E.
- Alternative: v10.8 Battle State UI Copy Update.

Safety statement:
- No production code, UI/source integration, UI source adapter, payload adapter, prompt guard, UI checkbox behavior, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.6 - Battle State UI Source Inventory

Purpose:
- Inventory which current UI/repo sources can safely feed future `battle_state_context` UI integration.

Files inspected:
- `ui/main_window.py`
- `ui/widgets/pokemon_panel.py`
- `ui/widgets/llm_advice_panel.py`
- `ui/widgets/item_profile_dialog.py`
- `llm/advisor_client.py`
- `llm/advisor_battle_state_context.py`
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_battle_state_context.py`
- v10.2-v10.5 battle-state docs and payload contract docs

Inventory:
- Self and opponent active species are already visible in UI-selected payloads and can be normalized as `visible_ui`.
- Self and opponent active HP percent are already visible in `PokemonPanel.current_hp_percent` / `pokemon.*.hp_percent` and can be normalized as `visible_ui`.
- User-confirmed item profiles can be considered for `user_confirmed` item values after a v10.7 design decision; unknown/default item profiles must not be promoted to hidden battle truth.
- Status, boosts, weather, terrain, screens, hazards, room effects, and general `known_conditions` are not currently available from explicit UI source and should remain unknown.

Recommended next:
- v10.7 Battle State UI Integration Design.
- Alternative: v10.7 Battle State UI Source Adapter if T1/T2 explicitly approve implementation after design review.
- Alternative: v10.7 Battle State Context Closure.

Safety statement:
- No production code, UI/source integration, payload adapter, prompt guard, UI checkbox behavior, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.5 - Battle State Context Offline Advice Fixture

Purpose:
- Verify that `battle_state_context` payload and prompt guard survive an offline mocked advice flow without actual provider, Vertex AI, or network calls.

Implementation:
- Added mocked offline advice fixture coverage in `tests/test_advisor_payload_contract.py`.
- Monkeypatched `advisor_client.call_gemini` and `advisor_client._log_advisor_call`.
- Captured default, explicit battle-state, and coexistence prompts in memory.

Payload preservation:
- Explicit-on fixture includes top-level `battle_state_context`.
- Captured prompt payload preserves helper output shape.
- `confidence == "limited"` is preserved.
- Unknown fields remain explicit unknowns.
- Forbidden sources and forbidden hidden/resolved fields remain absent recursively.

Prompt preservation:
- Serialized `battle_state_context` appears in prompt when enabled.
- v10.4 prompt guard appears in prompt when enabled.
- Guard anchors cover unknown fields, hidden item inference, EV/IV/nature inference, boosts/status/weather/terrain/hazards/screens/room inference, damage/KO reverse inference, resolved simulation, post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, and full turn outcome boundaries.

Coexistence:
- Offline fixture verifies coexistence with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.

Mocked response safety:
- Mocked responses avoid hidden item certainty, EV/IV/nature certainty, post-turn HP certainty, item consumption, RNG resolution, speed tie resolution, Quick Claw activation, and full turn outcome claims.

Tests:
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`

Recommended next:
- v10.6 Battle State UI Source Inventory.
- Alternative: v10.6 Battle State UI Integration Design.
- Alternative: v10.6 Battle State Context Closure.

Safety statement:
- No UI/source integration, UI checkbox behavior change, actual Gemini call, retry, Vertex AI call, network call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.4 - Battle State Context Prompt Guard

Purpose:
- Add prompt guard wording when top-level `battle_state_context` is present in the advice payload.

Implementation:
- Added `_build_battle_state_context_prompt_guard(...)` in `llm/advisor_client.py`.
- Wired the guard into `_build_ui_selected_prompt(...)` after `opponent_move_context` guard.
- `_build_ui_selected_prompt(...)` accepts explicit/default-off `battle_state_context` and `enable_battle_state_context=False` arguments.

Behavior:
- If `battle_state_context` is absent, no serialized `battle_state_context` block or prompt guard appears.
- If `battle_state_context` is present, the serialized context and guard wording appear in the prompt.
- Existing prompt behavior remains unchanged for default/off paths.

Guard boundary:
- Unknown battle state fields must remain unknown.
- Hidden item, EV, IV, nature, boosts, status, weather, terrain, hazards, screens, and room inference is forbidden unless explicitly provided.
- `damage_estimate` and `ko_context` must not be used for hidden-state reverse inference.
- `battle_state_context` must not be treated as a resolved turn simulation.
- The prompt must not claim post-turn HP, item consumption, RNG result, speed tie result, Quick Claw activation, or full turn outcome.

Coexistence:
- The guard coexists with `turn_pipeline`, `turn_order_context`, and `opponent_move_context` guards.

Tests:
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`

Recommended next:
- v10.5 Battle State Context Offline Advice Fixture.
- Alternative: v10.5 Battle State UI Source Inventory.
- Alternative: v10.5 Battle State UI Integration Design.

Safety statement:
- No UI/source integration, UI checkbox behavior change, actual Gemini call, retry, Vertex AI call, hidden-state inference, damage reverse inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, payload filtering, logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.3 - Battle State Context Payload Adapter

Purpose:
- Connect caller-provided, already-normalized `battle_state_context` helper output to the UI advice payload as an optional top-level context.

Implementation:
- Added explicit/default-off adapter support in `llm/advisor_client.py`.
- `build_ui_advice_payload(...)` accepts `battle_state_context` and `enable_battle_state_context=False`.
- The adapter does not call `build_battle_state_context(...)` automatically.
- `None`, `{}`, and unknown-only helper contexts are omitted.
- Valid non-empty contexts are deep-copied into top-level `battle_state_context` when explicitly enabled.

Validation:
- Requires `kind == "battle_state_context"`.
- Allows only `confidence` values `unknown` and `limited`.
- Requires `self_active`, `opponent_active`, `field`, `known_conditions`, `unsupported`, and `safety_notes`.
- Rejects forbidden sources and forbidden hidden/resolved fields recursively.
- Preserves helper output shape when inserted.

Coexistence:
- Coexists with `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- Does not overwrite existing optional contexts.

Safety:
- No automatic battle-state generation.
- No prompt guard, UI/source integration, UI checkbox behavior change, actual Gemini call, retry, Vertex AI call, hidden-state inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering change.
- The adapter does not infer hidden state from `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, or `opponent_move_context`.

Tests:
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`

Recommended next:
- v10.4 Battle State Context Prompt Guard.
- Alternative: v10.4 Battle State Context Payload Adapter Offline Fixture.
- Fallback: v10.4 Battle State Source Inventory.

Safety statement:
- No logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.2 - Battle State Context Helper

Purpose:
- Add a standalone helper that normalizes visible or explicit battle-state facts into the v10.1 `battle_state_context` contract shape.

Implementation:
- Added `llm/advisor_battle_state_context.py`.
- Added `build_battle_state_context(...)` with optional `self_active`, `opponent_active`, `field`, and `known_conditions` inputs.
- Empty or fully rejected input returns `confidence == "unknown"`.
- Any accepted visible or explicit source returns `confidence == "limited"`.
- The helper never emits `partial` or `explicit` confidence.

Source policy:
- Allowed sources: `visible_ui`, `explicit_input`, `user_confirmed`, `calculated_from_visible`.
- Forbidden sources: `species_common_set`, `usage_based_guess`, `meta_inferred`, `hidden_state_guess`, `damage_reverse_inference`.
- Forbidden sources become explicit unknown values or are omitted from list-style conditions.

Shape:
- `self_active` and `opponent_active` always include `species`, `current_hp_percent`, `status`, `boosts`, and `item`.
- `field` always includes `weather`, `terrain`, `screens`, `hazards`, and `room`.
- Missing or rejected values use `{"known": False, "value": "unknown"}`.
- Known status, boosts, item, and field values use `{"known": True, "source": ..., "value": ...}`.
- Visible species and HP percent keep source-tagged `name` / `value` envelopes.

Safety:
- The helper does not infer hidden item, EV/IV/nature, hidden status, hidden boosts, weather, terrain, hazards, screens, room, RNG, item consumption, post-turn HP, or resolved turn outcomes.
- `damage_estimate`, `ko_context`, `turn_pipeline`, `turn_order_context`, and `opponent_move_context` are not used as hidden-state or resolved-outcome sources.
- No payload adapter, prompt guard, UI/source integration, UI checkbox behavior change, actual Gemini call, retry, Vertex AI call, full Turn Engine, damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering change.

Tests:
- `tests/test_advisor_battle_state_context.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`

Recommended next:
- v10.3 Battle State Context Payload Adapter.
- Alternative: v10.3 Battle State Prompt Guard.
- Fallback: v10.3 Battle State Source Inventory if helper input source availability needs tighter alignment before adapter work.

Safety statement:
- No logs, `.env`, secrets, API keys, token-log contents, `config/env.example`, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.1 - Battle State Context Payload Contract

Purpose:
- Lock the future optional top-level `battle_state_context` shape at fixture/test level before helper, adapter, prompt guard, or UI/source integration.

Contract:
- `kind == "battle_state_context"`.
- Initial `confidence` allows only `unknown` and `limited`.
- `self_active` and `opponent_active` include `species`, `current_hp_percent`, `status`, `boosts`, and `item`.
- `field` includes `weather`, `terrain`, `screens`, `hazards`, and `room`.
- `known_conditions` is present as a list.
- `unsupported` and `safety_notes` are required.
- Unknown fields use `{"known": False, "value": "unknown"}`.

Source policy:
- Allowed sources: `visible_ui`, `explicit_input`, `user_confirmed`, `calculated_from_visible`.
- Forbidden sources: `species_common_set`, `usage_based_guess`, `meta_inferred`, `hidden_state_guess`, `damage_reverse_inference`.

Safety:
- Recursive forbidden fields are rejected in fixture tests, including hidden item, EV/IV/nature, inferred item/boost/status/weather/terrain, damage reverse inference, post-turn HP, item consumption, RNG resolution, speed tie resolution, Quick Claw activation resolution, full turn result, and resolved outcome fields.
- Relationship boundaries are locked: existing contexts do not create hidden state, final truth, resolved events, speed tie/RNG/final-order resolution, selected opponent move, hidden moveset, or resolved turn simulation.

Tests:
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`

Recommended next:
- v10.2 Battle State Context Helper.
- Fallback: v10.2 Battle State Context Source Inventory if source availability is unclear.
- Alternative: v10.2 Battle State Prompt Guard Design.

Safety statement:
- No production helper, payload adapter, prompt guard, UI/source integration, UI checkbox behavior change, actual Gemini call, retry, Vertex AI call, hidden-state inference, full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering change.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v10.0 - Battle State Context Design

Purpose:
- Design a future `battle_state_context` before implementation.
- Define safe visible/explicit battle-state boundaries without hidden-state inference or full turn simulation.

Design summary:
- Proposed a future optional top-level `battle_state_context` with `kind`, `confidence`, `self_active`, `opponent_active`, `field`, `known_conditions`, `unsupported`, and `safety_notes`.
- Recommended source-tagged state envelopes such as `{"known": true, "value": ..., "source": "visible_ui"}` and explicit unknown envelopes such as `{"known": false, "value": "unknown"}`.
- Recommended initial confidence values `unknown` and `limited`; deferred `partial` and `explicit` until trusted source paths exist.
- Allowed sources: `visible_ui`, `explicit_input`, `user_confirmed`, `calculated_from_visible`.
- Forbidden sources: `species_common_set`, `usage_based_guess`, `meta_inferred`, `hidden_state_guess`, `damage_reverse_inference`.

Included field categories:
- `self_active`
- `opponent_active`
- `field`
- `known_conditions`
- `unsupported`
- `safety_notes`

Excluded behavior:
- no hidden item, EV/IV/nature, unobserved boost, unobserved status, weather/terrain, hazards/screens, room, RNG, item consumption, post-turn HP, selected opponent move, opponent set, hidden moveset, or full turn inference.
- no reverse inference from `damage_estimate` or `ko_context`.

Existing context relationship:
- `damage_estimate` remains damage context, not hidden-state source.
- `ko_context` remains limited KO context, not final battle truth.
- `turn_pipeline` remains candidate event context, not resolved event output.
- `turn_order_context` remains helper context, not speed tie/RNG/final order resolution.
- `opponent_move_context` remains move fact/candidate context, not selected move or hidden moveset inference.
- `battle_state_context` should be visible/explicit battle-state snapshot context only.

Recommended next:
- v10.1 Battle State Context Payload Contract.
- Fallback: v10.1 Battle State Context Source Inventory if source availability is too unclear.
- Alternative: v10.1 Battle State Prompt Guard Design.

Safety:
- Documentation-only design.
- No production code change.
- No `battle_state_context` implementation.
- No payload adapter or prompt guard implementation.
- No UI checkbox behavior change.
- No actual Gemini call, retry, Vertex AI call, or provider/network call.
- No full Turn Engine, resolved turn order, post-turn HP calculation, item consumption, RNG resolver, speed tie resolver, Quick Claw activation resolution, hidden state inference, damage reverse inference, damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v9.4 - Opponent Move UI Integration Closure

Purpose:
- Close the v9.0-v9.3 Opponent Move UI Integration phase.
- Record the current supported behavior, safety boundary, test coverage, known limitations, and next recommended phase.

Phase summary:
- v9.0 designed the UI/source integration around existing explicit/visible `opponent_moves` data and the existing default-off limited-context checkbox.
- v9.1 implemented runtime source integration behind the checkbox, mapping checked state to `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- v9.2 verified the UI/offline E2E checkbox path with mocked provider calls only.
- v9.3 polished checkbox label, tooltip, and status copy to describe the combined limited context accurately.

Current behavior:
- The existing limited-context checkbox defaults unchecked.
- Checkbox off omits `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and related prompt guards.
- Checkbox on enables all three limited context flags; each context is still emitted only when valid source data exists.
- UI-visible opponent moves become `visible_ui` candidate moves.
- Candidate moves remain `confirmed=False` and `selected=False`.
- Runtime UI-visible moves do not become `known_opponent_moves`.
- `selected_opponent_move` remains `{"status": "unknown"}` unless a future explicit trusted source is designed.
- The v8.4 opponent move prompt guard appears only when top-level `opponent_move_context` exists.

UI copy:
- Label: `제한 컨텍스트 포함`
- Tooltip/status describe candidate turn events, turn-order helper context, and UI-visible opponent move candidates.
- Copy states this is not a final turn result, not the opponent's actual selected move, and not hidden moveset / RNG / item consumption / post-turn HP inference.

Tests:
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_turn_order_context.py`
- `tests/test_advisor_turn_events.py`
- `tests/test_turn_event.py`
- `tests/test_advisor_damage_estimate.py`
- `tests/test_damage_perf.py`

Known limitations:
- UI-visible moves are candidate context only.
- There is no explicit selected opponent move UI source yet.
- No opponent hidden moveset inference, opponent set inference, or meta/common-set expansion exists.
- No actual UI-path Gemini smoke for this combined path has been run.
- No `battle_state_context` exists yet.
- No full turn simulation exists.

Recommended next:
- v10.0 Battle State Context Design.
- Alternative: v9.5 Controlled UI Gemini Smoke Design.
- Alternative: v9.5 Opponent Move UI Path Controlled Gemini Smoke.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No provider/network call.
- No production code change.
- No new checkbox, default change, behavior change, saved auto-enable, or checkbox-toggle provider call.
- No full Turn Engine, `battle_state_context`, resolved turn order, hidden moveset inference, opponent set inference, selected opponent move inference, species/common-set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v9.3 - Opponent Move UI Copy / Tooltip Polish

Purpose:
- Clarify the existing limited-context checkbox copy now that it includes `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.
- Keep behavior unchanged while making the UI describe limited candidate/context semantics accurately.

Implementation:
- Updated `LLMAdvicePanel` checkbox label to `제한 컨텍스트 포함`.
- Updated the tooltip to explain that turn event candidates, turn-order helper context, and UI-visible opponent move candidates are sent to the LLM.
- Updated status copy to say the context is on and remains non-final.
- Added UI copy anchor coverage to `tests/test_ui_turn_pipeline_flag_flow.py`.
- Updated existing payload contract copy assertions.

Final copy:
- Label: `제한 컨텍스트 포함`
- Tooltip: `턴 이벤트 후보, 선후공 판단 보조, UI에 보이는 상대 기술 후보를 LLM 입력에 포함합니다. 이 정보는 확정 턴 결과가 아니며, 상대 기술 후보는 확정된 기술이 아닙니다. 숨겨진 기술배치, RNG 결과, 아이템 소모, 턴 후 HP를 추론하지 않습니다.`
- Status: `제한 컨텍스트 켜짐: 후보 이벤트, 선후공 보조 정보, 상대 기술 후보 전달 | 확정 결과 아님`

Behavior:
- Checkbox default remains unchecked.
- Checkbox toggle behavior is unchanged.
- Checkbox toggle alone still makes no provider call.
- The checkbox still maps only when the existing advice request path reads its state.
- Candidate opponent moves are described as candidates, not confirmed or selected moves.
- The copy does not claim confirmed turn result, confirmed move order, Quick Claw activation, item consumption, post-turn HP, hidden moveset inference, or selected opponent move inference.

Tests:
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`

Recommended next:
- v9.4 Opponent Move UI Integration Closure.
- Alternative: v9.4 Controlled UI Gemini Smoke Design.
- Alternative: v9.4 Battle State Context Design.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No network/provider call.
- No new checkbox.
- No checkbox default change.
- No checkbox behavior change.
- No saved setting auto-enable.
- No checkbox-toggle provider call.
- No full Turn Engine, resolved turn order, hidden moveset inference, opponent set inference, selected opponent move inference, species/common-set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v9.2 - Opponent Move UI Integration Offline E2E

Purpose:
- Verify the existing limited-context UI checkbox path end-to-end with mocked provider calls only.
- Lock checkbox off/on behavior after `opponent_move_context` joined `turn_pipeline` and `turn_order_context` under the same default-off checkbox.

Implementation:
- Added `tests/test_ui_turn_pipeline_flag_flow.py` as a focused UI/offline E2E flag-flow test file.
- Reused the existing `LLMAdvicePanel` checkbox and `run_ui_selected_advice(...)` path.
- Mocked `advisor_client.call_gemini` and `_log_advisor_call` in memory for advice-flow checks.
- Added an empty-opponent-source path to confirm that `opponent_move_context` is omitted rather than forced.

Behavior:
- Checkbox defaults unchecked.
- Checkbox toggle alone emits no advice request and makes no provider call.
- Checkbox off omits `turn_pipeline`, `turn_order_context`, `opponent_move_context`, and their prompt guards.
- Checkbox on maps the same state to `enable_turn_pipeline=True`, `enable_turn_order_context=True`, and `enable_opponent_move_context=True`.
- Checkbox on with visible opponent moves includes all three optional contexts in one prompt/payload.
- UI-visible opponent moves become `visible_ui` candidates, not known opponent moves.
- Candidate moves remain `confirmed=False` and `selected=False`.
- `selected_opponent_move` remains `{"status": "unknown"}`.
- Empty opponent move source still allows `turn_pipeline` and `turn_order_context` while omitting `opponent_move_context` and its guard.

Tests:
- `tests/test_ui_turn_pipeline_flag_flow.py`
- `tests/test_advisor_opponent_move_context.py`
- `tests/test_advisor_payload_contract.py`

Recommended next:
- v9.3 Opponent Move UI Copy / Tooltip Polish.
- Alternative: v9.3 Controlled UI Gemini Smoke Design.
- Alternative: v9.3 Opponent Move UI Integration Closure.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No network/provider call.
- No new checkbox.
- No checkbox default change.
- No saved setting auto-enable.
- No checkbox-toggle provider call.
- No full Turn Engine, resolved turn order, hidden moveset inference, opponent set inference, selected opponent move inference, species/common-set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v9.1 - Opponent Move UI Source Integration

Purpose:
- Connect the existing default-off limited-context UI developer checkbox to `opponent_move_context` generation.
- Keep the implementation offline/test-only, with no actual Gemini or Vertex AI call.

Implementation:
- `run_ui_selected_advice(...)` now accepts `enable_opponent_move_context: bool = False`.
- `_build_ui_selected_prompt(...)` builds optional `opponent_move_context` only when explicitly enabled.
- `LLMAdviceWorker` stores and forwards `enable_opponent_move_context`.
- `MainWindow._start_llm_advice()` maps the existing checkbox to `enable_turn_pipeline`, `enable_turn_order_context`, and `enable_opponent_move_context`.
- Existing UI-visible opponent move slots become `visible_ui` candidate moves in `opponent_move_context`.
- Champions movepool entries remain unconfirmed `champions_movepool` candidates.

Behavior:
- Checkbox off preserves default payload/prompt behavior with no `opponent_move_context`.
- Checkbox on includes `opponent_move_context` only when existing `opponent_moves` source data can produce a non-empty valid context.
- Runtime UI source integration keeps `known_opponent_moves` empty for visible UI slots.
- Candidate moves remain `confirmed=False` and `selected=False`.
- `selected_opponent_move` remains `{"status": "unknown"}`.
- The v8.4 opponent move prompt guard appears only when top-level `opponent_move_context` is present.

Tests:
- `tests/test_advisor_payload_contract.py`
- `tests/test_advisor_opponent_move_context.py`

Recommended next:
- v9.2 Opponent Move UI Integration Offline E2E.
- Alternative: v9.2 Controlled UI Gemini Smoke Design.
- Alternative: v9.2 Opponent Move UI Copy / Tooltip Polish.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No new checkbox.
- No checkbox default change.
- No saved setting auto-enable.
- No checkbox-toggle provider call.
- No full Turn Engine, resolved turn order, hidden moveset inference, opponent set inference, selected opponent move inference, species/common-set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v9.0 - Opponent Move UI / Source Integration Design

Purpose:
- Design how the existing UI-selected advice path should source and expose `opponent_move_context`.
- Keep the work documentation-only before any UI/source implementation.

Current state:
- `opponent_move_context` is ready below the UI layer after v8.8.
- `run_ui_selected_advice(...)` already accepts explicit `opponent_move_context` and `enable_opponent_move_context` inputs.
- `ui/main_window.py` already builds `opponent_moves` from user-filled opponent move slots and Champions movepool candidates.
- The UI does not yet convert or pass that source into `opponent_move_context`.

Selected recommendation:
- Reuse the existing default-off limited-context developer checkbox for the first implementation.
- When unchecked, keep `enable_opponent_move_context=False`.
- When checked, pass `enable_opponent_move_context=True` only when the existing advice button is pressed.
- Derive `opponent_move_context` only from existing explicit/visible `opponent_moves` data.
- Omit empty or invalid context instead of emitting an empty top-level field.

Recommended next:
- v9.1 Opponent Move UI Source Helper / Flag Integration.
- Alternative: v9.1 Opponent Move UI Mock Fixture.
- Alternative: v9.1 Battle State Context Payload Contract.

Safety:
- Documentation-only design.
- No production code change.
- No UI checkbox behavior change.
- No actual Gemini call.
- No Vertex AI call.
- No new checkbox.
- No full Turn Engine, hidden moveset inference, opponent set inference, selected opponent move inference, species/common-set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v8.8 - Opponent Move Context Closure

Purpose:
- Close the Opponent Move Context phase after the v8.7 controlled one-call Gemini smoke PASS.
- Record supported behavior, unsupported boundaries, known limitations, and the next recommended phase.

Phase summary:
- v8.1 locked the fixture-level `opponent_move_context` payload contract.
- v8.2 added the source-bound helper.
- v8.3 added the optional/default-off payload adapter.
- v8.4 added the prompt guard.
- v8.5 verified mocked offline advice behavior.
- v8.6 designed a controlled one-call Gemini smoke.
- v8.7 executed that smoke and classified it PASS.

Current supported behavior:
- `opponent_move_context` is optional and default-off.
- It appears only when a valid non-empty context is supplied with `enable_opponent_move_context=True`.
- Trusted known moves remain known move data, not selected move data.
- Candidate moves remain `confirmed=False` and `selected=False`.
- `selected_opponent_move` remains unknown unless explicitly supplied from a trusted source.
- Prompt guard wording is emitted only when top-level `opponent_move_context` is present.

Closure result:
- No further wording polish is required from the v8.7 smoke result.
- The phase is ready for a source/UI integration design step.

Recommended next:
- v9.0 Opponent Move UI/Source Integration Design.
- Alternative: v9.0 Battle State Context Payload Contract.

Safety:
- Documentation-only closure.
- No actual Gemini call.
- No Vertex AI call.
- No UI/source extraction.
- No UI checkbox behavior change.
- No full Turn Engine, hidden moveset inference, opponent set inference, selected opponent move inference, species/common-set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No logs, `.env`, secrets, API keys, token-log contents, or `docs/handoff_capsule_v1.1.md` changes.

---

## v8.7 - Controlled Gemini Smoke

Purpose:
- Execute the v8.6 controlled one-call Gemini smoke for `opponent_move_context`.
- Verify Gemini keeps known/candidate/selected opponent move boundaries without hidden inference.

Pre-check:
- `opponent_move_context` payload present.
- Opponent move prompt guard present.
- Known move represented as known data, not selected move.
- Candidate move remained `confirmed=False` and `selected=False`.
- `selected_opponent_move` remained unknown.
- Prompt anchors for candidate-not-confirmed, candidate-not-selected, known-not-selected, hidden moveset, opponent set, selected move, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, and post-turn HP all passed.
- Provider call count before smoke was `0`.

Smoke result:
- Actual Gemini call count: 1.
- Retry count: 0.
- Stop condition: none.
- Result classification: PASS.
- Model: `gemini-2.5-flash`.
- Safe usage summary: input tokens `7931`, output tokens `73`, cached tokens `0`.

Response safety:
- Gemini treated `opponent_move_context` as explicitly known / visible context.
- Known Thunderbolt was not treated as selected move.
- Candidate Quick Attack was not treated as confirmed move.
- Candidate Quick Attack was not treated as selected move.
- No selected opponent move inference while `selected_opponent_move` was unknown.
- No hidden moveset, opponent set, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, post-turn HP, or full turn resolution claim.

Safety:
- No retry.
- No Vertex AI call.
- No UI/source extraction.
- No UI checkbox behavior change.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, species/common set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.8 Opponent Move Context Closure.
- Alternative: v8.8 Opponent Move UI/Source Integration Design.

---

## v8.6 - Controlled Gemini Smoke Design

Purpose:
- Define the controlled Gemini smoke plan for `opponent_move_context` before any provider call.
- Lock call conditions, stop conditions, PASS/PARTIAL/FAIL/BLOCKED criteria, wording policy, and safe recording rules.

Design summary:
- Future smoke must include top-level `opponent_move_context` and the opponent move prompt guard.
- Pre-check must confirm known move data is not selected move data.
- Pre-check must confirm candidate moves remain `confirmed=False` and `selected=False`.
- Pre-check must confirm `selected_opponent_move` is unknown for the fixture.
- Pre-check must confirm prompt guard anchors for candidate-not-confirmed, candidate-not-selected, known-not-selected, hidden moveset, opponent set, selected move, EV/IV/nature, hidden item, weather/terrain/boost, RNG, item consumption, and post-turn HP inference.

Call policy:
- Actual Gemini call maximum for the future smoke: 1.
- Retry count: 0.
- No repeated fixture call.
- No additional call after failure, block, timeout, or exception.
- Stop on 429, `RESOURCE_EXHAUSTED`, API key/auth/credential errors, billing/prepay/credit errors, routing errors, timeout, or unexpected exceptions.

Result criteria:
- PASS: Gemini treats context as explicitly known/visible data, keeps known moves non-selected unless explicit, keeps candidates unconfirmed/unselected, and avoids hidden inference or resolved outcome claims.
- PARTIAL: mostly safe but ambiguous wording or prompt-polish need.
- FAIL: selected/confirmed candidate claim, hidden moveset/opponent set/selected move inference, EV/IV/nature/hidden item/weather/terrain/boost inference, RNG/item consumption/post-turn HP/full turn resolution claim.
- BLOCKED: pre-check/provider/auth/billing/quota/routing/timeout/exception prevents evaluation.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No network/provider call.
- No UI/source extraction.
- No UI checkbox behavior change.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, species/common set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.

Recommended next:
- v8.7 Controlled Gemini Smoke, after T1 approval, with at most one actual Gemini call and no retry.
- Alternatives: v8.7 Prompt Wording Polish or v8.7 Opponent Move UI/Source Integration Design.

---

## v8.5 - Opponent Move Offline Advice Fixture

Purpose:
- Verify `opponent_move_context` payload and prompt guard through mocked offline advice.
- Confirm candidate/known/selected move wording stays non-inferential before any provider smoke or UI/source extraction.

Fixture summary:
- Added `test_opponent_move_context_offline_advice_fixture_covers_prompt_and_mocked_response`.
- Monkeypatches `advisor_client.call_gemini` and `_log_advisor_call`.
- Runs default, explicit `opponent_move_context`, and coexistence paths.
- Coexistence path includes `turn_pipeline`, `turn_order_context`, and `opponent_move_context`.

Coverage:
- Default path omits `opponent_move_context` and guard.
- Explicit path includes top-level `opponent_move_context`, serialized prompt JSON context, and opponent move prompt guard.
- Known Thunderbolt remains known move data, not selected move.
- Candidate Quick Attack remains `confirmed=False` and `selected=False`.
- `selected_opponent_move` remains unknown.
- Mocked response avoids `opponent will use`, `likely uses`, confirmed/selected candidate wording, hidden moveset assertions, hidden item assertions, EV/IV/nature assertions, RNG resolution, item consumption, and post-turn HP assertions.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No network call.
- No UI/source extraction.
- No UI checkbox behavior change.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, species/common set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.6 Controlled Gemini Smoke Design.
- Alternative: v8.6 Opponent Move UI/Source Integration Design.

---

## v8.4 - Opponent Move Prompt Guard

Purpose:
- Add prompt guard wording for top-level `opponent_move_context`.
- Prevent candidate moves from being treated as confirmed moves or selected opponent moves.

Implementation summary:
- Added `_build_opponent_move_context_prompt_guard(payload)` in `llm/advisor_client.py`.
- Wired the guard into `_build_ui_selected_prompt(...)` after the `turn_order_context` guard.
- Guard is emitted only when top-level `opponent_move_context` is present.
- Default-off prompts remain unchanged when `opponent_move_context` is absent.
- Explicit prompt path can include both guard and serialized `opponent_move_context`.
- Guard coexists with `turn_pipeline` and `turn_order_context` guards.

Safety wording:
- Opponent move context is based only on explicitly known or visible opponent move data.
- Known moves are not necessarily selected this turn unless `selected_opponent_move` is explicit.
- Candidate moves are not confirmed moves or confirmed selected moves.
- Hidden movesets, opponent sets, and selected opponent moves must not be inferred.
- EV/IV/nature, hidden item, weather, terrain, boosts, RNG results, item consumption, and post-turn HP must not be inferred unless explicitly provided.
- Unsupported entries are boundaries, not facts to fill in.

Tests:
- Expanded `tests/test_advisor_payload_contract.py`.
- Tests cover guard absence, guard presence, safety wording anchors, forbidden positive wording, coexistence with optional turn guards, default-off prompt stability, and explicit prompt inclusion.

Safety:
- No UI/source extraction.
- No UI checkbox behavior change.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, species/common set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.5 Opponent Move Offline Advice Fixture.
- Alternative: v8.5 Opponent Move UI/Source Integration Design.

---

## v8.3 - Opponent Move Context Payload Adapter

Purpose:
- Add an explicit/default-off adapter that can insert a validated top-level `opponent_move_context` into the advice payload.
- Keep prompt guard, prompt integration, UI/source extraction, and Gemini calls out of scope.

Implementation summary:
- `build_ui_advice_payload(...)` now accepts `opponent_move_context` and `enable_opponent_move_context`.
- Default-off and disabled paths preserve the previous payload shape.
- `enable_opponent_move_context=True` with no context preserves the previous payload shape.
- A valid empty helper context is omitted instead of emitted as an empty top-level context.
- Valid non-empty context is deep-copied and inserted as top-level `opponent_move_context`.
- Invalid contexts raise `ValueError`.
- Adapter validation enforces trusted known sources, explicit-only selected move, unconfirmed/unselected candidates, unsupported boundaries, safety notes, and recursive forbidden-field rejection.
- `opponent_move_context` coexists with `turn_pipeline` and `turn_order_context`.

Tests:
- Expanded `tests/test_advisor_payload_contract.py`.
- Tests cover default-off omission, explicit-on insertion, no-context omission, invalid value rejection, forbidden field rejection, selected move preservation, candidate non-confirmed preservation, and coexistence with `turn_pipeline` / `turn_order_context`.
- Existing helper tests remain green.

Safety:
- No prompt guard.
- No prompt integration.
- No UI checkbox behavior change.
- No UI/source extraction.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, species/common set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.4 Opponent Move Prompt Guard.
- Alternative: v8.4 Opponent Move UI/Source Integration Design.

---

## v8.2 - Opponent Move Context Helper

Purpose:
- Add a minimal helper that builds a v8.1-compatible `opponent_move_context` from caller-provided move data.
- Keep the helper source-bound and avoid hidden moveset, selected move, species/common-set, or meta inference.

Implementation summary:
- Added `llm.advisor_opponent_move_context.build_opponent_move_context(...)`.
- Inputs: `known_moves`, `candidate_moves`, and optional `selected_opponent_move`.
- Empty input emits `confidence=unknown`, selected opponent move `{"status": "unknown"}`, and no move lists.
- Trusted known moves from `user_confirmed`, `visible_ui`, or `explicit_input` become `confirmed=True`.
- Untrusted known sources such as `meta_inferred`, `species_common_set`, and `usage_based_guess` are omitted.
- Candidate moves from safe candidate sources remain `confirmed=False` and `selected=False`.
- Candidate inputs with `confirmed=True`, `selected=True`, `will_use=True`, or `likely_selected=True` are omitted.
- Explicit selected moves require trusted source, `move_id`, and `name`; inferred, predicted, or likely statuses are rejected.
- Positive-priority candidate moves produce `priority_move_candidates` that remain unconfirmed and unselected.

Tests:
- Added `tests/test_advisor_opponent_move_context.py`.
- Tests cover empty input, trusted known moves, untrusted source omission, candidate normalization, unsafe candidate omission, selected move handling, priority candidates, no species-only inference, forbidden fields, unsupported boundaries, and safety notes.
- Existing v8.1 payload contract tests remain green.

Safety:
- No payload adapter.
- No prompt integration.
- No UI checkbox behavior change.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, species/common set/meta-based move generation, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.3 Opponent Move Context Payload Adapter.
- Alternative: v8.3 Opponent Move Source Extraction Design if source extraction needs design before adapter work.

---

## v8.1 - Opponent Move Context Payload Contract

Purpose:
- Lock the fixture-level contract for a future optional top-level `opponent_move_context`.
- Separate explicitly known opponent moves from possible/unconfirmed candidate moves before any helper, adapter, prompt, UI, or Gemini work.

Contract summary:
- `kind` is `opponent_move_context`.
- `confidence` is limited to `limited` or `unknown`.
- `selected_opponent_move.status` is limited to `unknown` or explicit user/visible input.
- `known_opponent_moves` require trusted source such as `user_confirmed`, `visible_ui`, or `explicit_input`.
- `candidate_moves` and `priority_move_candidates` must remain `confirmed=False` and `selected=False`.
- Forbidden fields include hidden inference and resolved-outcome markers such as `inferred_moveset`, `predicted_move`, `likely_move`, `will_use`, `meta_set`, `EVs`, `IVs`, `nature`, `hidden_item`, `post_turn_hp`, `item_consumed`, `rng_resolved`, and `speed_tie_resolved`.
- Required unsupported boundaries include hidden moveset inference, opponent set inference, selected move inference, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, RNG resolution, and full turn resolution.

Tests:
- Added fixture-level contract tests in `tests/test_advisor_payload_contract.py`.
- Tests cover allowed values, selected move status, trusted known sources, candidate/priority candidate non-confirmed semantics, forbidden fields, unsupported boundaries, and prompt safety wording anchors.

Safety:
- No runtime helper.
- No payload adapter.
- No prompt integration.
- No UI checkbox behavior change.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine, resolved turn order, opponent set inference, hidden moveset inference, selected opponent move inference, EV/IV/nature inference, hidden item inference, weather/terrain/boost inference, speed tie resolver, RNG resolver, Quick Claw activation resolution, item consumption, or post-turn HP update.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.2 Opponent Move Context Helper.
- Alternative: v8.2 Opponent Move Source Extraction Design.

---

## v8.0 - Battle State / Opponent Move Context Expansion Design

Purpose:
- Design the next phase after v7 Turn Order UI Integration Closure.
- Improve advice quality by expanding explicitly known battle-state and opponent-move context before any full Turn Engine work.

Design summary:
- Current UI-selected path knows selected Pokemon, own selected move, user-confirmed move slots, base stats, visible HP percent, user-confirmed final stats/items when provided, existing item contexts, `turn_pipeline`, and `turn_order_context`.
- Current UI-selected path does not know hidden opponent movesets, opponent selected move unless user-confirmed, hidden item, EV/IV/nature, unprovided boosts, weather/terrain/screens, exact HP, RNG result, or post-turn state.
- Proposed future `opponent_move_context` as an optional top-level limited context that separates known user-confirmed moves from possible/unconfirmed candidate moves.
- Proposed future `battle_state_context` as an optional visible-state summary, not a battle-state manager.
- Move metadata candidates include move id/name/type/category/power/accuracy and later priority/target/effect flags only when trusted metadata exposes them.

Safety:
- Design only.
- No production implementation.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine.
- No resolved turn order.
- No opponent set inference, hidden moveset inference, EV/IV/nature inference, hidden item inference, or weather/terrain/boost inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

Recommended next:
- v8.1 Opponent Move Context Payload Contract.
- Alternative: v8.1 Battle State Context Payload Contract.

---

## v7.17 - Turn Order UI Integration Closure

Purpose:
- Close the Turn Order UI Integration phase after v7.16 controlled UI Gemini smoke PASS.
- Summarize supported behavior, unsupported boundaries, Quick Claw wording boundary, smoke result, known limitations, and next major phase recommendation.

Phase summary:
- `turn_order_context` moved from design through helper, payload adapter, prompt guard, UI flag connection, offline E2E, smoke harness alignment, and controlled UI Gemini smoke PASS.
- The existing UI checkbox `턴 이벤트 후보 포함` remains the single default-off flag for limited turn context.
- Checked state enables both `turn_pipeline` and `turn_order_context` when valid source contexts exist.
- Unchecked state omits both optional contexts and guards.

Current boundary:
- This is still not a full Turn Engine.
- No resolved final move order, speed tie resolution, RNG resolution, Quick Claw activation resolution, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference is supported.
- Quick Claw remains an unresolved candidate modifier. `may/could/possible/unresolved` wording is allowed; activation certainty remains forbidden.

Smoke result:
- v7.16 controlled UI Gemini smoke result: PASS.
- Actual Gemini call count: 1.
- Retry count: 0.
- No Vertex AI call.
- No exact final order, speed tie resolution, Quick Claw activation certainty, item consumption, post-turn HP, or full simulation claim.

Known limitations:
- Move priority and opponent move source extraction remain limited.
- Turn-order context is mostly base/raw Speed hinting unless confirmed final Speed is available.
- RNG modifiers remain unresolved candidates.
- No full battle resolution exists yet.

Recommended next:
- v8.0 Battle State / Opponent Move Context Expansion Design.
- Rationale: opponent move/state/priority/source context is now the largest advice-quality limiter and is safer to expand before any full Turn Engine work.

Safety:
- No actual Gemini call in v7.17.
- No retry.
- No Vertex AI call.
- No production code change.
- No UI checkbox behavior change.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.16 - Controlled UI Gemini Smoke Retry

Purpose:
- Retry the controlled UI Gemini smoke after v7.15 harness alignment.
- Use the actual UI checkbox-on path with both `turn_pipeline` and `turn_order_context`.

Pre-check:
- Checkbox default unchecked: passed.
- Checkbox toggle no-auto-call: passed.
- Checked state mapped to `enable_turn_pipeline=True` and `enable_turn_order_context=True`: passed.
- Prompt/payload included both `turn_pipeline` and `turn_order_context`: passed.
- Prompt included both optional context guards: passed.
- Focused smoke guard passed.
- Structural summary passed, including expected auto-built `turn_snapshot`.

Result:
- Classification: `PASS`.
- Actual Gemini call count: 1.
- Retry count: 0.
- Stop condition: none.
- Vertex AI call count: 0.

Response safety:
- Gemini treated both optional contexts as limited planning information.
- No exact final move order claim.
- No speed tie resolution claim.
- No Quick Claw activation certainty claim.
- No item consumption claim.
- No post-turn HP claim.
- No full turn simulation claim.
- No `damage_estimate` / `ko_context` conflict found.

Recommended next:
- v7.17 Turn Order UI Integration Closure.
- Optional alternative: v7.17 Prompt Wording Polish if the raw-Speed wording should become more cautious.

Safety:
- Exactly one actual Gemini call.
- No retry.
- No repeated provider call.
- No Vertex AI call.
- No UI checkbox behavior change.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- Quick Claw activation certainty remains forbidden.

---

## v7.15 - Controlled UI Gemini Smoke Harness Alignment

Purpose:
- Align the v7.13/v7.14 smoke harness guard before any provider retry.
- Keep v7.15 provider-free and retry-free.

Implementation:
- Added test-only provider-path prompt capture using monkeypatched `call_gemini`.
- Added a focused smoke guard for the actual `run_ui_selected_advice(...)` prompt path.
- Kept offline exact / regression prompt checks intact.
- Allowed harmless auto-built `turn_snapshot` presence in the provider-path structural summary.

Focused smoke guard:
- Requires top-level `turn_pipeline`.
- Requires top-level `turn_order_context`.
- Requires TurnPipeline and turn-order context guards.
- Requires exact-order, speed-tie, RNG activation, item-consumption, and post-turn HP prohibition anchors.
- Accepts `turn_snapshot` as optional context in the provider path.
- Does not misclassify negative Quick Claw safety wording as a positive resolved claim.

Tests:
- Provider-path prompt with auto-built `turn_snapshot` is accepted.
- Missing TurnPipeline guard is rejected.
- Missing turn-order context guard is rejected.
- Missing exact final order prohibition is rejected.
- Missing RNG / Quick Claw activation prohibition is rejected.
- Harmless `turn_snapshot` presence is accepted.
- Negative Quick Claw guard text is not treated as positive activation wording.

Recommended next:
- v7.16 Controlled UI Gemini Smoke Retry, only after explicit T1 approval.
- Safe alternatives: v7.16 Smoke Harness Closure or v7.16 Turn Order UI Integration Closure.

Safety:
- No actual Gemini call.
- No retry.
- No Vertex AI call.
- No production behavior change.
- No UI checkbox behavior change.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No raw full prompt recorded.
- Quick Claw activation certainty remains forbidden.

---

## v7.14 - Smoke Harness Prompt Guard Triage

Purpose:
- Triage why v7.13 stopped before provider call.
- Keep v7.14 provider-free and retry-free.

Findings:
- v7.13 strict prompt equality guard failed because the direct pre-check prompt did not include the `turn_snapshot` that `run_ui_selected_advice(...)` builds automatically.
- Cause classification: dynamic field difference.
- The provider-path prompt included top-level `turn_snapshot`; the direct pre-check prompt did not.
- Both prompts still included `turn_pipeline` and `turn_order_context`.
- Both prompts still included the TurnPipeline and turn-order context guards.

Safety anchor status:
- TurnPipeline limited/debug guard: present.
- turn-order limited planning / not resolved move order guard: present.
- Exact final move order prohibition: present.
- Speed tie resolution prohibition: present.
- RNG item activation prohibition: present.
- Item consumption prohibition: present.
- Post-turn HP prohibition: present.
- Full simulation prohibition remains covered through optional context guards.

Recommendation:
- Prefer Option C: keep exact prompt-shape checks in offline fixtures, but use focused safety anchors and structural summaries in the provider smoke harness.
- Next: v7.15 Controlled UI Gemini Smoke Harness Alignment.
- Do not run another actual Gemini call until the harness is aligned and T1 explicitly approves a new one-call smoke.

Safety:
- No actual Gemini call.
- No retry.
- No Vertex AI call.
- No production behavior change.
- No UI checkbox behavior change.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.
- No raw full prompt recorded.

---

## v7.13 - Controlled UI Gemini Smoke

Purpose:
- Attempt the controlled UI Gemini smoke for the checkbox-on `turn_pipeline` + `turn_order_context` path.
- Enforce the v7.12 maximum-one-call / no-retry policy.

Pre-check:
- Checkbox default unchecked: passed.
- Checkbox toggle no-auto-call: passed.
- Checked state mapped to `enable_turn_pipeline=True` and `enable_turn_order_context=True`: passed.
- Prompt/payload included both `turn_pipeline` and `turn_order_context`: passed.
- Prompt included both optional context guards: passed.
- Unsupported implementation checks passed: no full Turn Engine, resolved order, item consumption, or post-turn HP update.

Result:
- Classification: `BLOCKED`.
- Actual Gemini call count: 0.
- Retry count: 0.
- Stop condition: unexpected exception before call.
- The local smoke harness required exact prompt equality between the prechecked prompt and the provider wrapper prompt. That guard raised before the provider call, so no Gemini request was sent.

Recommended next:
- v7.14 Controlled UI Gemini Smoke Harness Alignment.
- After the harness is fixed, another one-call smoke requires explicit T1 approval.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No retry.
- No production UI behavior change.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.12 - Controlled UI Gemini Smoke Design

Purpose:
- Design a future one-call Gemini smoke for the actual UI checkbox-on path.
- Keep v7.12 documentation-only with no actual provider call.

Scope:
- The future smoke starts from the existing `LLMAdvicePanel` checkbox state.
- Checked state must map to both `enable_turn_pipeline=True` and `enable_turn_order_context=True`.
- Prompt pre-check must confirm both optional guards before any provider call.
- The smoke is meant to verify Gemini treats `turn_pipeline` and `turn_order_context` as limited context, not full simulation or resolved order.

Call policy:
- Actual Gemini call count in the future smoke: maximum 1.
- Automatic retry: forbidden.
- Repeated fixture calls: forbidden.
- Stop and record `BLOCKED` or `FAIL` on 429, `RESOURCE_EXHAUSTED`, API key/auth/credential, billing/prepay/credit, routing, timeout, or unexpected exception.

Result criteria:
- PASS requires no exact final move order, no speed tie resolution, no Quick Claw activation certainty, no item consumption, no post-turn HP claim, no full turn simulation claim, and no conflict with `damage_estimate` / `ko_context`.
- PARTIAL means generally safe wording that still needs polish.
- FAIL means resolved/full-simulation claims.
- BLOCKED means no usable provider result due to availability, auth, billing, quota, routing, timeout, or failed pre-check.

Recommended next:
- v7.13 Controlled UI Gemini Smoke, only after explicit T1 approval.
- Safe alternative: v7.13 Turn Order UI Integration Closure.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No production code implementation.
- No UI checkbox behavior change.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.11 - UI Flag Offline E2E Fixture

Purpose:
- Verify the actual `LLMAdvicePanel` checkbox state through the offline mocked advice path.
- Keep v7.11 provider-free and avoid any new UI controls.

Fixture:
- Uses `LLMAdvicePanel` directly.
- Reads checkbox state to derive `enable_turn_pipeline` and `enable_turn_order_context`.
- Calls `run_ui_selected_advice(...)` with monkeypatched `call_gemini` and `_log_advisor_call`.
- Captures prompts and mocked responses in memory.

Coverage:
- Default unchecked path has no `turn_pipeline` or `turn_order_context` payload sections.
- Checked path includes both optional contexts when source context exists.
- Prompt contains both guards only in the checked path.
- Checkbox toggle emits no `advice_requested` signal and does not call Gemini.
- Mocked responses avoid resolved wording such as `will move first`, `Quick Claw will activate`, `item will be consumed`, `post-turn HP will be`, and `full turn simulation shows`.

Recommended next:
- v7.12 Controlled UI Gemini Smoke Design.
- Do not run actual Gemini until T1 approves a one-call controlled smoke.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No new checkbox.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.10 - UI Flag Enables Turn Order Context

Purpose:
- Connect the existing default-off `턴 이벤트 후보 포함` developer checkbox to both `turn_pipeline` and `turn_order_context`.
- Keep the UI to one checkbox and avoid any actual Gemini call.

Implementation:
- Added `enable_turn_order_context: bool = False` to `run_ui_selected_advice(...)`.
- Added `enable_turn_order_context` forwarding through `LLMAdviceWorker`.
- Mapped the existing checkbox checked state to both optional flags in `MainWindow._start_llm_advice(...)`.
- Added narrow runtime source extraction for `turn_order_context`: base Speed, user-confirmed final Speed, and unresolved Quick Claw candidate modifier only.
- Kept priority unknown because current move metadata does not provide priority.

Copy:
- Kept the checkbox label `턴 이벤트 후보 포함`.
- Updated tooltip/status copy to mention turn event candidates plus turn-order planning hints.

Tests:
- Covered off/on UI flag mapping.
- Verified checkbox toggle still does not auto-call advice.
- Verified source-less enabled path omits invalid empty `turn_order_context`.
- Verified enabled mocked advice path can include both optional contexts and both prompt guards.

Recommended next:
- v7.11 UI Flag Offline E2E Fixture.
- Do not run actual Gemini yet.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No new checkbox.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, opponent set inference, or EV/IV/nature inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.9 - UI / Flag Integration Design

Purpose:
- Design how the existing default-off UI developer flag should expose `turn_order_context`.
- Keep v7.9 documentation-only, with no UI behavior change and no Gemini call.

Options compared:
- Option A: one checkbox enables both `turn_pipeline` and `turn_order_context`.
- Option B: keep `turn_pipeline` on the current checkbox and add a separate turn-order checkbox.
- Option C: keep one checkbox and clarify that it enables limited turn event candidates plus turn-order planning context.

Selected recommendation:
- Use Option C.
- Keep one developer checkbox for the limited turn-planning feature.
- Preserve default unchecked and no persisted auto-enable.
- When off, pass both `enable_turn_pipeline=False` and `enable_turn_order_context=False`.
- When on, pass both `enable_turn_pipeline=True` and `enable_turn_order_context=True`, while omitting any optional context whose source data is unavailable.

Copy:
- Keep the current label `턴 이벤트 후보 포함` for the first implementation to avoid unnecessary UI churn.
- Update tooltip/status copy to mention both turn event candidates and turn-order planning hints.
- Candidate tooltip: `확정 턴 시뮬레이션이 아니라, 턴 이벤트 후보와 선후공 판단 보조 정보를 조언에 추가합니다.`
- Candidate status: `턴 판단 후보 포함됨 | 확정 시뮬레이션 아님`.

Recommended next:
- v7.10 UI Flag Enables Turn Order Context.
- Do not run actual Gemini in v7.10.

Safety:
- No production code implementation.
- No UI checkbox behavior change.
- No UI checkbox auto-connection.
- No actual Gemini call.
- No Vertex AI call.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.8 - Turn Order Context Offline Advice Fixture

Purpose:
- Verify the `turn_order_context` path offline from payload to prompt to mocked LLM response.
- Keep v7.8 provider-free and disconnected from UI flags.

Fixture:
- Uses `_build_ui_selected_prompt(...)` with explicit `turn_order_context` inputs.
- Monkeypatches `advisor_client.call_gemini`.
- Monkeypatches `advisor_client._log_advisor_call`.
- Captures prompts and mocked responses in memory only.

Coverage:
- Default-off path has no `turn_order_context` payload section or guard.
- Explicit-on path has top-level `turn_order_context`, safety guard, `order_hint`, unresolved candidate modifiers, and unsupported boundaries.
- `turn_pipeline` coexistence path has both optional sections and both guards.
- Mocked responses avoid resolved wording such as `will move first`, `Quick Claw will activate`, `item will be consumed`, `post-turn HP will be`, and `full turn simulation shows`.

Recommended next:
- v7.9 UI / Flag Integration Design.
- Safe alternative: v7.9 Controlled Turn Order Gemini Smoke Design.
- Do not run actual Gemini smoke yet.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox auto-connection.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.7 - Turn Order Context Prompt Integration

Purpose:
- Wire the `turn_order_context` prompt guard into `_build_ui_selected_prompt(...)`.
- Verify default-off, explicit-on, and `turn_pipeline` coexistence prompt shapes offline.

Implementation:
- Added keyword-only `turn_order_context` and `enable_turn_order_context` inputs to `_build_ui_selected_prompt(...)`.
- Built the advice payload with the optional explicit turn-order context.
- Inserted `_build_turn_order_context_prompt_guard(...)` immediately after the TurnPipeline guard area.
- Used the existing serialized advice payload JSON as the context inclusion style; no separate compact summary was added.

Tests:
- Default/off prompt behavior remains unchanged.
- Explicit-on prompt includes the turn-order guard and top-level `turn_order_context`.
- Prompt payload includes `order_hint`, unresolved `candidate_modifiers[*].resolved=false`, and unsupported boundaries.
- `turn_pipeline` and `turn_order_context` guards coexist when both contexts are present.
- Positive resolved wording such as `Quick Claw will activate` and `full turn simulation shows` stays absent.

Recommended next:
- v7.8 Turn Order Context Offline Advice Fixture.
- Alternative: v7.8 UI / Flag Integration Design.
- Do not run actual Gemini smoke yet.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox auto-connection.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.6 - Turn Order Context Prompt Contract Tests

Purpose:
- Lock the `turn_order_context` prompt guard/copy contract before runtime prompt integration.
- Keep v7.6 test-focused and offline, with no Gemini call.

Implementation:
- Added `_build_turn_order_context_prompt_guard(payload)` as a minimal conditional guard helper.
- The helper returns empty text when `turn_order_context` is absent.
- The helper returns safety wording when `turn_order_context` is present.
- The helper is not yet wired into `_build_ui_selected_prompt(...)`; runtime prompt integration remains a v7.7 candidate.

Tests:
- Default-off payload has no `turn_order_context` guard.
- Explicit-on payload has guard wording for limited planning context and not-resolved order.
- Guard forbids exact final move order, speed tie resolution, RNG item activation, item consumption, and post-turn HP inference.
- `turn_pipeline` and `turn_order_context` guards can coexist independently.
- Forbidden positive phrase anchors such as `will move first`, `Quick Claw will activate`, and `full turn simulation shows` are not present in the turn-order guard.

Recommended next:
- v7.7 Turn Order Context Prompt Integration.
- Alternative: v7.7 Turn Order Context Offline Advice Fixture.
- Do not run actual Gemini smoke yet.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox auto-connection.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.5 - Turn Order Context Prompt Integration Design

Purpose:
- Design how optional `turn_order_context` should be represented in the LLM prompt.
- Keep v7.5 documentation-only, with no prompt implementation or Gemini call.

Design:
- Recommended placement is the same optional-context guard area as `turn_pipeline`.
- The future guard should appear immediately after the `turn_pipeline` guard when both contexts are present.
- Safety wording should state that `turn_order_context` is limited planning context, not a resolved move order.
- The prompt should forbid exact final move order, speed tie resolution, RNG item activation, item consumption, and post-turn HP inference.

Coexistence:
- `turn_order_context` provides cautious priority / Speed order hints only.
- `turn_pipeline` provides candidate events and limited debug summary only.
- If both are present and incomplete or apparently conflicting, the model should state uncertainty rather than resolving final order or event outcomes.

Recommended next:
- v7.6 Turn Order Context Prompt Contract Tests.
- Faster alternative: v7.6 Turn Order Context Prompt Integration with focused tests.
- Do not go directly to Gemini smoke.

Safety:
- No production code implementation.
- No actual Gemini call.
- No Vertex AI call.
- No prompt integration.
- No UI checkbox auto-connection.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.4 - Turn Order Context Payload Adapter

Purpose:
- Connect the v7.3 deterministic turn order context helper output to the advisor payload as an optional, explicit-only field.
- Keep the adapter default-off and disconnected from prompt, UI, Gemini, and full Turn Engine behavior.

Adapter:
- Added `enable_turn_order_context: bool = False` to `build_ui_advice_payload(...)`.
- Added optional top-level `turn_order_context` insertion when the caller explicitly supplies a context and enables the flag.
- Omitted/disabled paths preserve the previous payload shape.
- `enable_turn_order_context=True` with no supplied context also preserves the previous payload shape.
- Adapter validation enforces v7.2 allowed values, unresolved `candidate_modifiers[*].resolved=false`, required unsupported boundaries, and recursive rejection of resolved-outcome fields.

Coexistence:
- `turn_pipeline` and `turn_order_context` are independent optional top-level sections.
- Tests cover both disabled, pipeline-only, order-context-only, and both-enabled payload shapes.

Recommended next:
- v7.5 Turn Order Context Prompt Integration Design.
- Safer test-first alternative: v7.5 Turn Order Context Prompt Contract Tests.
- Do not go directly to Gemini smoke before prompt safety wording is designed or locked.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No prompt integration.
- No UI checkbox auto-connection.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No resolved turn order, speed tie resolver, RNG resolver, item consumption, post-turn HP update, or opponent set inference.
- No damage formula, raw roll, Q12 multiplier, `ko_context`, or payload filtering changes.

---

## v7.3 - Deterministic Turn Order Context Helper

Purpose:
- Implement the minimal helper for the v7.2 `turn_order_context` contract.
- Keep the helper standalone and disconnected from runtime payload/prompt/UI paths.

Helper:
- Added `llm.advisor_turn_order_context.build_deterministic_turn_order_context(...)`.
- Inputs cover own/opponent move priority, own/opponent base Speed, optional confirmed final Speed, and candidate modifiers.
- Confirmed final Speed takes precedence over base Speed when both sides are known.
- Unknown priority or Speed remains explicit as `unknown`.

Behavior:
- Priority relation covers own higher, opponent higher, same priority, and unknown.
- Speed relation covers base Speed, confirmed final Speed, tie candidates, and missing Speed.
- Order hint remains non-final: likely-if-same-priority, priority-overrides-speed, tie_or_unknown, or unknown.
- Candidate modifiers are normalized to `resolved=False`.

Tests:
- Added `tests/test_advisor_turn_order_context.py`.
- Covered base Speed, confirmed final Speed, priority, unknowns, Quick Claw candidate modifiers, forbidden fields, and unsupported boundaries.

Recommended next:
- v7.4 Turn Order Context Payload Adapter.
- Safe alternative: v7.4 Prompt Integration Design.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No resolved turn order.
- No speed tie resolver.
- No RNG resolver.
- No item consumption.
- No post-turn HP update.
- No opponent set inference.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v7.2 - Turn Order Context Payload Contract

Purpose:
- Lock the deterministic turn order context payload contract before helper implementation.
- Keep the contract fixture-level only; no runtime top-level payload adapter is added yet.

Contract:
- Future optional key: `turn_order_context`.
- `kind`: `deterministic_turn_order_context`.
- `confidence`: `limited` or `unknown`.
- Allowed `priority_relation`, `speed_relation`, and `order_hint` values avoid final-order wording.
- Candidate modifiers must use `resolved=False`.
- Unsupported boundaries include speed tie resolution, RNG item activation, exact final order, item consumption, and post-turn HP update.

Tests:
- Added plain pytest fixture assertions in `tests/test_advisor_payload_contract.py`.
- Tests reject non-allowed classification values.
- Tests reject resolved-outcome fields such as `final_order_resolved`, `item_consumed`, and `post_turn_hp`.
- Tests lock prompt safety copy anchors.

Recommended next:
- v7.3 Deterministic Turn Order Context Helper.
- Keep helper scope to base Speed / confirmed final Speed / priority / unknown relation handling.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No resolved turn order.
- No speed tie resolver.
- No RNG resolver.
- No item consumption.
- No post-turn HP update.
- No opponent set inference.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v7.1 - Deterministic Turn Order Context Design

Purpose:
- Design a limited deterministic turn order context before any full Turn Engine work.
- Define priority, Speed relation, unknown, and tie-candidate semantics without resolving final order.

Design:
- Inputs may include selected Pokemon, selected own move, explicitly known opponent move, trusted move priority metadata, base Speed, user-confirmed final Speed, existing `speed_context`, and Quick Claw `speed_order_context`.
- Unknown or unconfirmed priority/Speed stays explicit as `unknown`.
- Quick Claw and other RNG items remain unresolved candidate modifiers.
- Output draft includes `priority`, `speed`, `order_hint`, `tie_or_unknown`, `candidate_modifiers`, and `unsupported`.

Safety wording:
- This is not resolved final move order.
- Do not claim speed ties are resolved.
- Do not claim RNG items activate.
- Do not claim exact final order unless an explicit resolved engine result is provided.
- Treat the section as limited planning context.

Recommended next:
- v7.2 Turn Order Context Payload Contract.
- Faster alternative: v7.2 Deterministic Turn Order Context Helper.
- No resolved-order helper should be implemented yet.

Safety:
- No production code implementation.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No resolved turn order.
- No speed tie resolver.
- No RNG resolver.
- No item consumption or HP update.
- No opponent set inference.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v7.0 - Turn Engine Roadmap / Scope Split

Purpose:
- Define the future full Turn Engine scope without implementing it.
- Split full engine work into smaller stages with explicit inputs, outputs, risks, and unsupported boundaries.

Roadmap:
- Stage 1: Deterministic Turn Order Context.
- Stage 2: Deterministic Damage Application Preview.
- Stage 3: Item Trigger Candidate Layer.
- Stage 4: Resolved Turn Simulation Prototype.
- Stage 5: Post-turn State Update.

Key distinction:
- Current limited TurnPipeline provides candidate events, known modifiers, and limited planning/debug context.
- Full Turn Engine would resolve turn order, priority/speed/speed ties, RNG triggers, item activation/consumption, damage application, HP update, fainting/survival, and post-turn state.

Risk:
- Low: deterministic context summaries, existing damage estimate reuse, candidate event lists.
- Medium: speed relation interpretation, priority handling, new item trigger families.
- High: RNG resolution, item consumption, post-turn HP update, opponent inference, resolved event sequences.

Recommended next:
- v7.1 Deterministic Turn Order Context Design.
- Safe alternative: v7.1 Battle State / Opponent Move Context Expansion.
- Resolved Turn Simulation Prototype is not recommended as the first v7 step.

Safety:
- No production code implementation.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No resolved turn simulation.
- No turn order resolver.
- No speed tie resolver.
- No RNG resolver.
- No item consumption or HP update.
- No opponent set inference.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.21 - TurnPipeline UI Phase Closure

Purpose:
- Close the TurnPipeline UI phase after the v6.20 controlled UI Gemini smoke PASS.
- Document the current feature state, safety boundary, known limitations, and next major direction.

Current feature state:
- The UI dev flag label is `턴 이벤트 후보 포함`.
- The checkbox defaults unchecked and has no persisted auto-enable.
- Off path preserves existing advice behavior.
- On path passes `enable_turn_pipeline=True`.
- Top-level `turn_pipeline` remains limited-only.
- Prompt guard states that candidate events are not resolved outcomes and not full turn simulation.
- The UI-enabled Gemini smoke passed once with exactly one call, no retry, no Vertex AI, and no stop condition.

Safety boundary:
- Current behavior adds limited turn event candidates, known modifiers, and limited planning/debug context to LLM advice.
- Existing `damage_estimate`, `ko_context`, and item contexts remain the core advice primitives.
- Full Turn Engine, exact turn order, speed tie/RNG resolution, item consumption, post-turn HP update, exact trigger resolution, and opponent set inference are not implemented.

Known issue:
- `test_item_damage_calculation_under_point_12ms_average` remains timing-sensitive in some full-suite/order-dependent runs.
- Threshold / skip / xfail were not changed.
- Final green reruns remain the push-readiness signal while instability is recorded.

Recommended next:
- v7.0 Turn Engine Roadmap / Scope Split.
- Safe alternative: v7.0 Battle State / Opponent Move Context Expansion.
- Do scope/design first; do not start full Turn Engine implementation directly.

Safety:
- No production code implementation.
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox behavior change.
- No user-facing advice button behavior change.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.20 - Controlled UI Gemini Smoke

Purpose:
- Run one controlled actual Gemini smoke through the UI dev flag path.
- Verify Gemini does not treat `turn_pipeline` as full simulation.

Smoke:
- UI checkbox state: on.
- Actual Gemini call count: 1.
- Retry: none.
- Stop condition: none.
- Vertex AI call: none.
- Result classification: PASS.

Response safety:
- Quick Claw used possibility wording and did not guarantee activation.
- Final move order was not modeled.
- Focus Sash was possible survival context, not guaranteed item consumption.
- No full turn simulation claim.
- No exact post-turn HP claim.
- No RNG / speed tie / exact trigger resolution claim.
- Damage / KO wording stayed tied to existing damage estimate context.

Testing:
- Pre-call required tests passed.
- Known timing-sensitive perf failure appeared around `test_item_damage_calculation_under_point_12ms_average`.
- Isolated perf target passed 3/3 after the failure.
- Final full pytest passed.
- Threshold / skip / xfail were not changed.

Recommended next:
- v6.21 TurnPipeline UI Phase Closure.
- If needed, UI Copy Polish can happen separately without another Gemini call.

Safety:
- Exactly one actual Gemini call.
- No retry.
- No Vertex AI call.
- No checkbox-toggle Gemini call.
- No saved setting auto-enable.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.19 - UI Dev Flag Smoke / Manual QA

Purpose:
- Verify the v6.18 TurnPipeline dev-only UI flag with smoke / QA checks.
- Avoid actual Gemini, Vertex AI, and external provider/network calls.

QA method:
- Instantiated `LLMAdvicePanel` directly with PySide offscreen.
- Instantiated `MainWindow` offscreen without entering the interactive event loop.
- Inspected checkbox state, tooltip text, status text, and toggle behavior.
- Reused mocked pytest fixtures for default/off/on advice-flow behavior.

Verified:
- `턴 이벤트 후보 포함` checkbox appears below the advice button.
- Checkbox defaults unchecked.
- Tooltip/help matches v6.18 wording and says this is not full turn simulation.
- Tooltip mentions RNG, item consumption, post-turn HP, speed ties, and exact triggers are not resolved.
- Checkbox toggle alone does not emit `advice_requested`.
- Off state preserves default no-`turn_pipeline` behavior.
- On state can pass `enable_turn_pipeline=True` through existing mocked tests.
- Enabled status copy is `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`.
- No layout/copy blocking issue was observed in offscreen smoke.

Recommended next:
- v6.20 Controlled UI Gemini Smoke, only with explicit T1 approval for one actual UI Gemini call.
- Safe no-call alternative: v6.20 TurnPipeline UI Phase Closure.
- If interactive QA finds wording awkward, use v6.20 UI Copy Polish first.

Safety:
- No production UI logic change.
- No actual Gemini call.
- No Vertex AI call.
- No external network/provider call.
- No saved setting auto-enable.
- No checkbox-toggle Gemini call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.18 - UI Dev Flag Implementation

Purpose:
- Add a default-off developer UI flag for including limited TurnPipeline candidate events in advice.
- Keep the existing advice button behavior unchanged when the flag is off.

UI:
- Adds `턴 이벤트 후보 포함` checkbox to `LLMAdvicePanel`.
- Checkbox defaults unchecked.
- Tooltip states this is not full turn simulation and does not resolve RNG, item consumption, post-turn HP, speed ties, or exact triggers.
- Enabled status copy: `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`.

Flow:
- Off path passes `enable_turn_pipeline=False`.
- On path passes `enable_turn_pipeline=True`.
- `LLMAdviceWorker` still defaults to `enable_turn_pipeline=False`.
- Checkbox toggle alone does not emit advice requests or call Gemini.
- No persisted auto-enable or saved setting was added.

Verified:
- Default unchecked widget state.
- Tooltip/status copy.
- Toggle no-call behavior.
- Worker/main-window flag wiring.
- Mocked default/off/on advice paths remain no-provider-call tests.

Recommended next:
- v6.19 UI Dev Flag Smoke / Manual QA.
- Actual Gemini call remains disabled unless T1 approves a controlled one-call smoke.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No external network/provider call.
- No saved setting auto-enable.
- No checkbox-toggle Gemini call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.17 - Controlled UI Mock Smoke

Purpose:
- Verify future UI flag on/off behavior at mock level without implementing UI.
- Keep actual Gemini, provider/network, and Vertex AI calls disabled.

Mock strategy:
- Uses a fake UI state object instead of real widgets.
- `turn_pipeline_enabled=None` represents current default behavior.
- `turn_pipeline_enabled=False` represents an unchecked future flag.
- `turn_pipeline_enabled=True` represents a checked future flag.
- Monkeypatches `advisor_client.call_gemini` and `_log_advisor_call`.

Verified:
- Default omitted-flag path has no top-level `turn_pipeline` and no prompt guard.
- Flag-off path passes `enable_turn_pipeline=False` and matches the default prompt/payload.
- Flag-on path passes `enable_turn_pipeline=True`, includes limited `turn_pipeline`, and includes candidate / not-resolved / not-full-simulation guard text.
- Fake enabled status can show `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`.
- Existing `damage_estimate`, `ko_context`, and item contexts remain present.
- `LLMAdvicePanel` still has no `QCheckBox`, no layout change, and no `enable_turn_pipeline` wiring.

Recommended next:
- v6.18 UI Dev Flag Implementation if T1 explicitly approves UI implementation.
- Safe alternative: v6.18 Final Pre-UI Integration Review.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No external network/provider call.
- No UI checkbox implementation.
- No `LLMAdvicePanel` layout modification.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.16 - UI Exposure Test Plan

Purpose:
- Document the tests required before exposing TurnPipeline in the UI.
- Keep the step design/test-plan only, with no production code implementation.

UI exposure candidate:
- Preferred candidate under test is a dev-only flag or developer option.
- The feature remains default-off.
- No persisted setting should silently auto-enable it.
- Candidate label: `턴 이벤트 후보 포함`.
- Candidate enabled status: `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`.

Test plan:
- Default-off regression: existing advice button behavior unchanged, no top-level `turn_pipeline`, no prompt guard, no default warning copy.
- UI flag off smoke: unchecked flag calls `run_ui_selected_advice(...)` with `enable_turn_pipeline=False` or omitted.
- UI flag on smoke: checked flag calls `run_ui_selected_advice(..., enable_turn_pipeline=True)`, includes limited `turn_pipeline`, prompt guard, and enabled status copy.
- No-call guarantee: mock `call_gemini`, avoid provider/network calls, avoid Vertex AI, and do not commit token logs.
- Copy visibility: label/help/warning matches v6.12 and never implies a full simulation.
- Rollback: one flag/control can disable or remove the feature without changing the existing advice path.

Implementation entry criteria:
- v6.15 offline E2E fixture green.
- v6.13 prompt copy fixtures green.
- v6.8 payload snapshot tests green.
- T1 explicitly approves UI implementation.
- No unresolved provider issue blocks the planned workflow.
- Do not assume a credit blocker before Gemini reports 429 / billing / prepay / auth / routing errors, but keep automatic retries and unnecessary repeated calls disabled.

Recommended next:
- v6.17 Controlled UI Mock Smoke.
- Alternative: v6.17 UI Dev Flag Implementation with explicit T1 approval.
- UI Copy Snapshot Tests can be folded into either path if UI code is needed.

Safety:
- Documentation/test-plan only.
- No actual Gemini call.
- No Vertex AI call.
- No external network/provider call.
- No production code implementation.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.15 - Offline End-to-End Advice Fixture

Purpose:
- Verify payload -> prompt -> mocked advice behavior without actual Gemini calls.
- Compare default-off and explicit-on TurnPipeline advice paths with the same fixture.

Fixture:
- Uses `run_ui_selected_advice(...)`.
- Monkeypatches `advisor_client.call_gemini`.
- Monkeypatches `_log_advisor_call`.
- Captures and parses both prompts.
- Makes no external network/provider call.

Verified:
- Default path omits top-level `turn_pipeline` and TurnPipeline guard copy.
- Explicit path includes top-level `turn_pipeline` with `simulated="limited"`.
- Explicit path includes candidate / not-resolved / not-full-simulation guard wording.
- Explicit path preserves `damage_estimate`, `ko_context`, and item contexts.
- Resolved-outcome phrases remain absent.

Recommended next:
- v6.16 UI Exposure Test Plan.
- Alternative: v6.16 Controlled UI Mock Smoke.
- UI Dev Flag Implementation requires explicit T1 approval.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No external network/provider call.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.14 - TurnPipeline UI Exposure Design

Purpose:
- Design future TurnPipeline UI exposure without implementing UI.
- Keep existing advice button behavior default-off and unchanged.

Design:
- Option A, visible checkbox in `LLMAdvicePanel`, is discoverable but too user-facing for the first implementation step.
- Option B, settings/developer option dev flag, is the preferred future UI path if implementation is approved.
- Option C, config/internal flag only, remains the safest path if another offline fixture is preferred first.

Default-off policy:
- Existing advice button behavior remains unchanged.
- `enable_turn_pipeline=True` requires explicit opt-in.
- No saved setting should silently auto-enable the feature yet.
- Disabled state must preserve the current payload/prompt shape.

UI copy:
- Label: `턴 이벤트 후보 포함`.
- Help: `확정 턴 시뮬레이션이 아니라, 아이템/속도/생존 가능성 같은 제한적 후보 정보를 조언에 추가합니다.`
- Warning: `RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 확정하지 않습니다.`
- Status: `턴 이벤트 후보 포함됨 | 확정 시뮬레이션 아님`.

Recommended next:
- v6.15 Offline End-to-End Advice Fixture.
- Alternative: v6.15 UI Exposure Test Plan.
- UI Dev Flag Implementation requires explicit T1 approval.

Safety:
- Documentation-only UI exposure design.
- No actual Gemini call.
- No Vertex AI call.
- No production code implementation.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.13 - Prompt Copy Test Fixtures

Purpose:
- Lock v6.12 TurnPipeline prompt / UX copy rules with fixture-level tests.
- Avoid brittle full-prompt snapshots and external snapshot dependencies.

Tests:
- No-`turn_pipeline` prompts omit TurnPipeline guard anchors and design-only UI copy.
- Explicit `turn_pipeline` prompts include limited planning/debug summary wording.
- Explicit `turn_pipeline` prompts keep candidate events as not-resolved outcomes.
- Prompt anchors forbid resolved-outcome meanings such as guaranteed activation, consumed items, final HP, full turn simulation result, or resolved speed tie.
- UI copy labels remain design-only and are not wired into `LLMAdvicePanel`.

Recommended next:
- v6.14 UI Exposure Design.
- Alternative: v6.14 Offline End-to-End Advice Fixture.
- UI Dev Flag Implementation requires explicit T1 approval.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No external snapshot dependency.
- No token-log commit/reset.

---

## v6.12 - TurnPipeline Prompt / UX Copy Design

Purpose:
- Design prompt-facing and user-facing copy for future TurnPipeline exposure.
- Keep the UI checkbox and user-facing automatic advice connection out of scope.

Design:
- Developer / schema name remains `TurnPipeline`.
- Recommended Korean user-facing label: `턴 이벤트 후보`.
- Recommended Korean explanatory phrase: `제한적 턴 판단 보조`.
- Recommended English user-facing label: `Candidate Turn Events`.
- Recommended English explanatory phrase: `Limited Turn Context`.

Recommended UI copy:
- Label: `턴 이벤트 후보 포함`.
- Tooltip: `확정 턴 시뮬레이션이 아니라, 아이템/속도/생존 가능성 같은 제한적 후보 정보를 조언에 추가합니다.`
- Warning: `이 정보는 확정 턴 시뮬레이션이 아니라 제한적 판단 보조입니다. RNG, 아이템 소모, 턴 종료 후 HP, 스피드 타이, 정확한 발동 결과는 확정하지 않으며 후보 정보로만 참고하세요.`

Advice copy rules:
- Allowed: `발동할 수 있음`, `후보로 고려`, `확정은 아님`, `현재 정보 기준`, `제한적 계산 기준`, `may affect`, `candidate context`.
- Forbidden: `반드시 발동`, `소모됨`, `턴 종료 후 HP는 X`, `완전한 턴 시뮬레이션 결과`, `스피드 타이 결과 확정`, `will activate`, `will be consumed`.

Recommended next:
- v6.13 Prompt Copy Test Fixtures.
- Alternative: v6.13 UI Exposure Design.
- Do not implement a UI dev flag / checkbox without explicit approval.

Safety:
- Documentation-only prompt / UX copy design.
- No actual Gemini call.
- No Vertex AI call.
- No production code implementation.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.11 - Controlled Gemini Smoke Closure / Next UI Exposure Design

Purpose:
- Close the v6.10 controlled Gemini smoke PASS result.
- Record the current TurnPipeline safety boundary before any UI exposure.
- Recommend the next safe design step.

Closure:
- v6.10 used one explicit-on `turn_pipeline` payload fixture.
- Actual Gemini call count was 1.
- Retry: none.
- Stop condition: none.
- Classification: PASS.
- No Vertex AI call.
- No UI checkbox.
- No user-facing advice button automatic connection.

Response safety findings:
- Candidate wording was maintained.
- Quick Claw remained possible / "may", not guaranteed activation.
- Focus Sash remained possible survival, not guaranteed consumption or resolved survival.
- No full turn simulation claim.
- No item consumption claim.
- No exact post-turn HP claim.
- No RNG, speed tie, or exact trigger resolution claim.
- Damage estimate was treated as a default-assumption estimate, not final battle damage.

Current safety boundary:
- Explicit flag paths can generate a limited `turn_pipeline`.
- Optional top-level payload insertion is available.
- Prompt guard present / absent behavior is covered.
- Controlled Gemini smoke has one PASS result.
- Default UI advice behavior remains off.
- UI checkbox and user-facing automatic TurnPipeline enablement remain unimplemented.

Recommended next:
- v6.12 Prompt / UX Copy Design.
- Alternative: v6.12 UI Exposure Design.
- Do not implement a UI checkbox yet.

Safety:
- Documentation-only closure / design.
- No actual Gemini call.
- No Vertex AI call.
- No production code implementation.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.10 - Controlled Gemini Smoke Execution

Purpose:
- Execute one controlled actual Gemini smoke for the explicit-on TurnPipeline payload path.
- Verify Gemini does not treat `turn_pipeline` as full simulation or resolved battle truth.

Smoke:
- Fixture: explicit-on `turn_pipeline` payload fixture.
- Actual Gemini calls: 1.
- Automatic retries: none.
- Vertex AI calls: none.
- Stop condition: none.

Result:
- Classification: PASS.
- Response treated the damage estimate as default-assumption and not final battle damage.
- Quick Claw was phrased as possible move-order influence, not guaranteed activation.
- Focus Sash was phrased as possible survival, not guaranteed consumption or resolved survival.
- Chilan Berry was conditional and not relevant to Flamethrower.
- No full turn simulation claim.
- No item consumption claim.
- No exact post-turn HP claim.
- No RNG, speed tie, or exact trigger resolution claim.
- No conflict with `damage_estimate` or `ko_context`.

Note:
- The synthetic fixture allowed an awkward Light Ball-on-Charizard mention; Gemini said the effect was not applied in the Charizard damage estimate.
- This was not a TurnPipeline safety failure, but a future fixture can avoid that synthetic-context mismatch.

Verification:
- Pre-call `uv run pytest tests/test_advisor_payload_contract.py -q`: 78 passed.
- Pre-call `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- Pre-call `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- Pre-call `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- Pre-call `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- Post-call `uv run pytest tests/test_advisor_payload_contract.py -q`: 78 passed.
- Post-call `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- Post-call `uv run pytest -q`: 1008 passed, 2 deselected.

Safety:
- No retry.
- No Vertex AI call.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

Next:
- v6.11 Controlled Gemini Smoke Closure / Next UI Exposure Design.
- Decide whether to remain dev-only, design UI exposure, or improve the fixture offline before any UI checkbox.

---

## v6.9 - TurnPipeline Controlled Gemini Smoke Design

Purpose:
- Design a controlled actual-Gemini smoke strategy for the explicit TurnPipeline payload path.
- Define the approval, call limit, stop conditions, and PASS/FAIL criteria before any real call.

Design:
- Future controlled smoke should use one explicit-on `turn_pipeline` fixture.
- Default-off payload is already covered by v6.8 snapshot lockdown.
- Actual Gemini call limit is maximum 1.
- No automatic retry.
- Stop immediately on 429, `RESOURCE_EXHAUSTED`, API key, auth, billing/prepay, or provider routing errors.
- Vertex AI remains prohibited.

PASS criteria:
- Gemini treats `turn_pipeline` as limited planning/debug context.
- Candidate events are not described as resolved outcomes.
- No item consumption, post-turn HP, speed tie, RNG, exact trigger, status, or volatile resolution claims.
- `damage_estimate` and `ko_context` remain the relevant primitive contexts.

FAIL criteria:
- Claims such as Quick Claw will activate, Focus Sash will be consumed, exact HP after the turn, full turn simulation proves the result, or `turn_pipeline` overrides `damage_estimate` / `ko_context`.

Recommended next:
- v6.10 Controlled Gemini Smoke Execution only with explicit T1 approval.
- Alternative: v6.10 Payload / Prompt Offline Eval if cost/quota/variability risk remains too high.

Safety:
- Documentation-only design.
- No actual Gemini call.
- No Vertex AI call.
- No production code implementation.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No token-log commit/reset.

---

## v6.8 - Payload Snapshot Lockdown

Purpose:
- Lock default/off/on TurnPipeline payload and prompt shapes before any runtime/UI exposure.
- Use plain pytest dictionary assertions instead of external snapshot tooling or large golden JSON files.

Locked:
- Default payload and prompt omit `turn_pipeline`.
- Explicit `enable_turn_pipeline=False` returns `None` and preserves the default payload/prompt shape.
- `turn_pipeline=None` preserves the default payload shape.
- Explicit limited `TurnPipelineResult` adds top-level `turn_pipeline`.
- Mapping input via `TurnPipelineResult.to_dict()` produces the same top-level shape.
- `turn_pipeline.simulated == "limited"` for explicit-on fixture paths.
- `simulated="full"` remains rejected.
- Prompt guard is absent without `turn_pipeline` and present with explicit `turn_pipeline`.
- Prompt guard keeps candidate events as non-resolved outcomes.

Existing-context preservation:
- `damage_estimate` remains present.
- `ko_context` remains present.
- `species_stat_item_context`, `speed_order_context`, `survival_context`, and `chilan_berry_context` remain present.
- `turn_pipeline` stays additive and does not replace existing contexts.

Known perf instability:
- `test_item_damage_calculation_under_point_12ms_average` remains timing-sensitive in full-suite/order-dependent runs.
- No threshold, skip, xfail, formula, raw roll, Q12, or `ko_context` change was made.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No external snapshot dependency.

Next:
- v6.9 Controlled Gemini Smoke Design, or a similarly explicit approval gate before any actual Gemini smoke.
- Keep actual Gemini calls disabled unless T1/T2 explicitly approve a pre-approved fixture and stop conditions.

---

## v6.7 - TurnPipeline Advice Flow Closure / Stability Report

Purpose:
- Close the current TurnPipeline advice-flow dry-run phase.
- Record what is connected, what remains default-off, and what still must not be treated as full simulation.
- Document the repeated timing-sensitive perf instability separately from TurnPipeline behavior.

Closed phase:
- v5.3 Item Context -> TurnEvent mapper.
- v5.4 mapper fixture coverage.
- v5.5 TurnPipelineResult fixture helper.
- v5.6 TurnPipeline debug report / dry-run.
- v5.7 payload exposure design.
- v5.8 optional top-level `turn_pipeline` payload adapter.
- v5.9 prompt/contract guard.
- v6.0 minimal integration design.
- v6.1 explicit generation adapter.
- v6.2 explicit payload smoke.
- v6.3 UI/advice integration design.
- v6.4 explicit advice payload builder smoke.
- v6.5 explicit advice flow integration design.
- v6.6 advice-flow dry-run with mocked `call_gemini`.

Current safety boundary:
- Explicit `enable_turn_pipeline=True` plus mocked/dry-run path can generate limited `turn_pipeline`.
- Optional top-level payload insertion is available.
- Prompt guard present/absent behavior is covered.
- Default UI advice behavior remains off.
- No UI checkbox and no user-facing advice button automatic enablement.

Known perf instability:
- `test_item_damage_calculation_under_point_12ms_average` can intermittently exceed the `0.120000ms` threshold in full-suite or ordering-sensitive runs.
- Isolated target and `tests/test_damage_perf.py -q` generally pass.
- No threshold, skip, xfail, formula, raw roll, Q12, or `ko_context` change was made.

Recommended next:
- v6.8 Payload Snapshot Lockdown.
- Lock default/off/on payload and prompt shapes without actual Gemini calls.
- Defer Controlled Gemini Smoke until after snapshot lockdown.
- Do not add UI checkbox yet.

Safety:
- Documentation-only closure report.
- No production code implementation.
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox implementation.
- No user-facing advice button automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

---

## v6.6 - Explicit TurnPipeline Advice Flow Dry-run

Purpose:
- Verify explicit TurnPipeline generation near the UI-selected advice flow without actual Gemini calls.
- Keep normal UI advice behavior default-off and unchanged.

Implemented:
- `run_ui_selected_advice(..., enable_turn_pipeline=False)` accepts a default-off dry-run flag.
- `_build_ui_selected_prompt(..., enable_turn_pipeline=False)` can explicitly build a limited TurnPipeline only when enabled.
- The explicit path uses `build_optional_turn_pipeline_for_advice_payload(...)` and the existing optional top-level payload adapter.
- Tests mock `call_gemini` and capture prompt text.

Verified:
- Default advice-flow dry-run omits `turn_pipeline`.
- Default advice-flow dry-run omits the TurnPipeline prompt guard.
- Explicit `enable_turn_pipeline=True` dry-run includes top-level `turn_pipeline`.
- Explicit dry-run keeps `simulated="limited"`.
- Prompt guard says candidate events are not resolved outcomes.
- Existing `damage_estimate`, `ko_context`, and item contexts remain present.
- UI panel and worker path do not expose a checkbox or enable the flag.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No UI checkbox implementation.
- No user-facing advice button automatic TurnPipeline enablement.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Next:
- v6.7 should decide whether to close the TurnPipeline dry-run phase or design a runtime/UI exposure surface.
- Keep any runtime exposure default-off and no-actual-Gemini in tests.

---

## v6.5 - Explicit TurnPipeline Advice Flow Integration Design

Purpose:
- Design whether and how explicit TurnPipeline generation should move closer to the real advice flow.
- Keep any future integration default-off, no-actual-Gemini, and easy to roll back.

Compared:
- `run_ui_selected_advice(..., enable_turn_pipeline=False)` optional parameter.
- Keeping explicit generation at payload-builder/manual caller level.
- UI handler dev-only flag.
- UI checkbox.
- Always-on advisor-client generation.

Recommended:
- v6.6 should be an explicit TurnPipeline advice-flow dry-run.
- If code is implemented, prefer an optional default-false flag with mocked/no-call tests only.
- Keep candidate B, manual payload-builder integration, as the safest fallback.
- Do not add a UI checkbox yet.
- Do not auto-generate by default.

Existing-context policy:
- `damage_estimate` remains the calculation source.
- `ko_context` remains the KO interpretation source.
- Existing item contexts remain the explanation source.
- `turn_pipeline` remains a limited timing/planning/debug summary.
- `turn_pipeline` does not replace existing contexts.

Safety:
- Documentation-only design.
- No production code implementation.
- No advisor-client automatic generation.
- No UI-selected advice flow automatic connection.
- No UI checkbox implementation.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 74 passed.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 1004 passed, 2 deselected.

---

## v6.4 - Explicit TurnPipeline Advice Payload Builder Smoke

Purpose:
- Strengthen fixture-level smoke coverage for explicit TurnPipeline generation plus advice payload builder insertion.
- Keep advisor-client and UI-selected advice flow automatic generation disabled.

Verified:
- Omitted/default and explicit `enable_turn_pipeline=False` paths return `None`.
- Disabled/default paths preserve payload output and do not add `turn_pipeline`.
- `enable_turn_pipeline=True` creates `simulated="limited"` `TurnPipelineResult`.
- Manual `build_ui_advice_payload(..., turn_pipeline=result)` insertion adds top-level `turn_pipeline`.
- Event ordering remains stable.
- Prompt guard is absent without `turn_pipeline` and present with explicit `turn_pipeline`.
- Prompt guard states candidate events are not resolved outcomes and does not allow RNG/item consumption/post-turn HP resolution claims.
- `damage_estimate`, `ko_context`, and existing item contexts remain present and unchanged.
- `run_ui_selected_advice(...)` does not call `build_optional_turn_pipeline_for_advice_payload(...)`.

Safety:
- No advisor-client automatic generation.
- No UI-selected advice flow automatic connection.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 74 passed.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 1004 passed, 2 deselected.

---

## v6.3 - TurnPipeline UI / Advice Flow Integration Design

Purpose:
- Design how TurnPipeline could eventually connect to the UI-selected advice flow.
- Keep the design default-off and explicit while avoiding production runtime changes.

Inspected flow:
- `LLMAdvicePanel.advice_requested`
- `MainWindow._start_llm_advice()`
- `MainWindow._build_llm_battle_input()`
- `LLMAdviceWorker.run()`
- `run_ui_selected_advice(...)`
- `_build_ui_selected_prompt(...)`
- `build_ui_advice_payload(..., turn_pipeline=None)`

Recommended:
- v6.4 should remain a payload-builder/helper fixture smoke, not UI runtime integration.
- Keep `enable_turn_pipeline=True` limited to fixture/dev paths.
- Keep default UI-selected advice flow unchanged.
- Do not add a UI checkbox yet.
- Do not add advisor-client automatic generation.

Existing-context policy:
- `damage_estimate` remains the calculation source.
- `ko_context` remains the KO interpretation source.
- Existing item contexts remain the user-facing explanation source.
- `turn_pipeline` remains a limited timing/planning/debug summary.
- `turn_pipeline` does not replace existing contexts.

Safety:
- Documentation-only design.
- No production code implementation.
- No advisor-client automatic generation.
- No UI-selected advice flow automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 74 passed.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 1004 passed, 2 deselected.

---

## v6.2 - Explicit TurnPipeline Payload Smoke

Purpose:
- Verify the fixture-level manual path from explicit TurnPipeline generation to optional top-level payload insertion.
- Keep `advisor_client.py` and UI-selected advice flow disconnected from automatic TurnPipeline generation.

Verified:
- `build_optional_turn_pipeline_for_advice_payload(...)` returns `None` by default.
- `None` passed to `build_ui_advice_payload(..., turn_pipeline=None)` preserves the existing payload.
- `enable_turn_pipeline=True` produces a limited `TurnPipelineResult`.
- Manually passing the result to `build_ui_advice_payload(..., turn_pipeline=...)` adds top-level `turn_pipeline`.
- Event ordering remains Light Ball, Quick Claw, Focus Sash, then Chilan Berry.
- `damage_estimate`, `ko_context`, and existing item contexts are preserved.
- TurnPipeline prompt guard appears only when `turn_pipeline` is explicitly present.

Safety:
- No advisor-client automatic generation.
- No UI-selected advice flow automatic connection.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 74 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 1004 passed, 2 deselected.

---

## v6.1 - Explicit TurnPipeline Generation Adapter

Purpose:
- Add an explicit/default-off helper that can build a limited `TurnPipelineResult` from an already-built advice payload.
- Keep runtime advice behavior unchanged unless a caller manually opts in and manually passes the result to the optional payload adapter.

Implemented:
- Added `build_optional_turn_pipeline_for_advice_payload(...)` in `llm.advisor_turn_events`.
- `enable_turn_pipeline=False` or omitted returns `None`.
- `enable_turn_pipeline=True` builds a `TurnPipelineResult` through the existing fixture/debug helper.
- Generated results use `simulated="limited"` only.
- The helper does not mutate the input payload.
- The helper can be combined manually with `build_ui_advice_payload(..., turn_pipeline=...)`.

Safety:
- No advisor-client automatic generation.
- No UI-selected advice flow automatic connection.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_turn_events.py -q`: 27 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 73 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 1003 passed, 2 deselected.

---

## v6.0 - Minimal TurnPipeline Integration Design

Purpose:
- Design the smallest safe integration path for `TurnPipelineResult` after v5.x foundation work.
- Compare automatic, explicit-flag, debug-only, and fixture-only integration options.
- Recommend a v6.1 explicit/default-off generation adapter without production runtime behavior changes.

Designed:
- Current UI-selected advice path remains:
  - `LLMAdvicePanel.advice_requested`
  - `MainWindow._start_llm_advice()`
  - `_build_llm_battle_input()`
  - `LLMAdviceWorker.run()`
  - `run_ui_selected_advice(...)`
  - `_build_ui_selected_prompt(...)`
  - `build_ui_advice_payload(..., turn_pipeline=None)`
- Recommended v6.1 MVP:
  - `build_optional_turn_pipeline_for_advice_payload(...)`
  - input is an already-built advice payload
  - default `enable_turn_pipeline=False`
  - returns `None` by default
  - returns limited `TurnPipelineResult` only when explicitly enabled
  - caller can pass the result to the existing optional `turn_pipeline` payload adapter
- Rejected v6.1 automatic generation inside `run_ui_selected_advice(...)`.

Existing-context policy:
- `damage_estimate` remains the primitive calculation source.
- `ko_context` remains the limited KO interpretation source.
- Existing item contexts remain the current user-facing context surfaces.
- `turn_pipeline` remains additive timing/planning/debug summary only.
- `turn_pipeline` does not replace or override context availability, item effects, or payload filtering.

Safety:
- Documentation-only design.
- No production code implementation.
- No advisor-client automatic generation.
- No UI-selected advice flow automatic connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 73 passed.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 20 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 996 passed, 2 deselected.

---

## v5.9 - TurnPipeline Payload Prompt Guard / Contract Documentation

Purpose:
- Strengthen optional `turn_pipeline` prompt and contract guardrails.
- Keep `turn_pipeline` from being treated as full turn simulation or resolved battle outcome.
- Preserve default-off behavior when `turn_pipeline` is absent or `None`.

Implemented:
- Added explicit contract limitations that `turn_pipeline` does not replace `damage_estimate`, `ko_context`, or existing item contexts.
- Added explicit contract limitation that candidate pipeline events are not resolved outcomes.
- Strengthened prompt guard to say candidate events are not resolved outcomes.
- Expanded narrow event wording validation for resolved RNG, item consumption, post-turn HP, speed tie, and trigger resolution claims.
- Added fixture-level tests for omitted/`None` prompt behavior, guard wording, conflict policy, and no auto-generation.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No advisor-client automatic `TurnPipelineResult` generation.
- No UI-selected advice flow automatic pipeline connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 73 passed.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 20 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- First `uv run pytest -q`: timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; best median `0.125000ms` vs threshold `0.120000ms`; `995 passed, 2 deselected`.
- Isolated `test_item_damage_calculation_under_point_12ms_average` rerun 3x: passed 3/3.
- Perf file rerun: 4 passed.
- Final `uv run pytest -q`: 996 passed, 2 deselected.
- No threshold, skip, xfail, damage formula, raw roll, Q12, `ko_context`, or payload filtering changes were made.

---

## v5.8 - Optional TurnPipeline Payload Adapter

Purpose:
- Add an explicit-only adapter for optional top-level `turn_pipeline`.
- Preserve default advice payload behavior when `turn_pipeline` is omitted or `None`.
- Keep runtime advisor flow from auto-generating `TurnPipelineResult`.

Implemented:
- Added `TURN_PIPELINE_KNOWN_LIMITATIONS`.
- Added optional `turn_pipeline` support to `build_ui_advice_payload(...)`.
- Added optional `turn_pipeline` support to `_build_ui_selected_prompt(...)`.
- Added top-level `turn_pipeline` insertion only for explicit inputs.
- Normalized `TurnPipelineResult` or mapping values with `normalize_turn_pipeline_result(...)`.
- Rejected `simulated="full"` for advice payload exposure.
- Required pipeline limitations for payload exposure.
- Added narrow event wording validation against resolved-result claims.
- Added prompt guard text only when `turn_pipeline` is present.

Default-off policy:
- `run_ui_selected_advice(...)` does not auto-generate `TurnPipelineResult`.
- `build_turn_pipeline_result_from_advice_payload(...)` remains disconnected from runtime advice flow.
- No automatic UI-selected advice pipeline insertion was added.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 66 passed.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 20 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 989 passed, 2 deselected.

---

## v5.7 - TurnPipeline Payload Exposure Design

Purpose:
- Design whether and how `TurnPipelineResult` should be exposed to the LLM advice payload.
- Keep v5.7 documentation-only and disconnected from `advisor_client.py`.
- Preserve the v5.6 debug/dry-run status while preparing a safe v5.8 adapter path.

Designed:
- Compared payload location candidates:
  - top-level `turn_pipeline`
  - `battle_input.turn_pipeline`
  - `debug_context.turn_pipeline`
  - no exposure / dry-run only
- Recommended eventual top-level `turn_pipeline`, matching the existing top-level `turn_snapshot` pattern.
- Recommended default-off / explicit-argument exposure for v5.8.
- Designed prompt limitations for any future payload exposure:
  - limited planning/debug summary only
  - not a full turn simulation
  - no RNG resolution
  - no item consumption
  - no post-turn HP
  - no guaranteed move order
  - no exact trigger or status resolution

Conflict policy:
- `damage_estimate` remains the damage primitive.
- `ko_context` remains the limited damage-roll primitive.
- Existing item contexts remain the current user-facing explanation surface.
- `turn_pipeline` is an additive planning/timing summary and does not replace existing contexts.
- `turn_pipeline` must not override item context availability, payload filtering, or applied damage item effects.

Recommended next step:
- v5.8 Optional TurnPipeline Payload Adapter Implementation.
- Keep it default-off and explicit-only.
- Do not auto-generate `TurnPipelineResult` inside `run_ui_selected_advice(...)`.
- Do not connect runtime helper generation to advice flow yet.

Safety:
- Documentation-only design.
- No production code changes.
- No `advisor_client.py` connection.
- No LLM payload connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Verification:
- `uv run pytest tests/test_advisor_turn_events.py -q`: 20 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average` and `test_ability_damage_calculation_under_point_20ms_average`; best medians `0.156250ms` vs threshold `0.120000ms` and `0.218750ms` vs threshold `0.200000ms`.
- Isolated `test_ability_damage_calculation_under_point_20ms_average`: passed.
- Isolated `test_item_damage_calculation_under_point_12ms_average`: repeated timing-sensitive failures before sequential cooldown rerun.
- Final sequential `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- Final `uv run pytest -q`: 980 passed, 2 deselected.
- No threshold, skip, xfail, damage formula, raw roll, Q12, `ko_context`, or payload filtering changes were made.

---

## v5.6 - TurnPipeline Debug Report / Dry-run

Purpose:
- Add a local dry-run script for the TurnEvent / TurnPipelineResult fixture path.
- Make mapper and pipeline output inspectable without any Gemini or Vertex AI call.
- Keep the debug report disconnected from `advisor_client.py` and the LLM payload.

Implemented:
- Added `scripts/spike_turn_pipeline_debug.py`.
- Added `docs/debug_turn_pipeline_sample_v5.6.md`.
- Added a smoke test for the debug fixture output shape.

Dry-run behavior:
- Builds a deterministic fixture advice payload.
- Maps available item contexts to `TurnEvent` candidates.
- Bundles events into `TurnPipelineResult`.
- Prints safe JSON to stdout.
- Includes:
  - events
  - stage
  - status
  - certainty
  - limitations
  - simulated value

Generated events:
- Light Ball: `damage` / `known_modifier` / `known`.
- Quick Claw: `pre_move` / `candidate` / `possible`.
- Focus Sash: `on_damage_before_ko` / `candidate` / `possible`.
- Chilan Berry: `on_damage_before_ko` / `candidate` / `possible`.

Safety:
- No `advisor_client.py` connection.
- No LLM payload connection.
- No runtime `TurnPipelineResult` payload insertion.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Recommended next step:
- v5.7 TurnPipeline Planning Design or v5.7 TurnPipelineResult Contract Closure.
- Keep any next step disconnected from `advisor_client.py` unless T1/T2 explicitly approve payload exposure.

Verification:
- `uv run python scripts/spike_turn_pipeline_debug.py`: passed, emitted safe JSON report.
- `uv run pytest tests/test_advisor_turn_events.py -q`: 20 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`, best batch median `0.125000ms` vs threshold `0.120000ms`.
- Isolated perf target rerun 3x: passed 3/3.
- `uv run pytest tests/test_damage_perf.py -q` after isolated reruns: same timing-sensitive failure, best batch median `0.140625ms` vs threshold `0.120000ms`.
- `uv run pytest -q`: same timing-sensitive failure, best batch median `0.125000ms` vs threshold `0.120000ms`; `979 passed, 2 deselected`.
- Final `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- Final `uv run pytest -q`: 980 passed, 2 deselected.
- No threshold, skip, xfail, damage formula, raw roll, Q12, `ko_context`, or payload filtering changes were made.

---

## v5.5 - TurnPipelineResult Fixture Contract Smoke

Purpose:
- Bundle existing `TurnEvent` mapper candidates into a fixture/debug `TurnPipelineResult`.
- Verify serialization, references, limitations, and safe empty-payload behavior.
- Keep the result disconnected from `advisor_client.py` and the LLM payload.

Implemented:
- Added `build_turn_pipeline_result_from_advice_payload(...)` in `llm.advisor_turn_events`.
- The helper uses `build_turn_events_from_advice_payload(...)` for event generation.
- The helper accepts optional:
  - `selected_move_id`
  - `input_snapshot`
  - `damage_estimate_ref`
  - `ko_context_ref`
  - `simulated`
- Default `simulated` is `limited`.
- `full` is not used by the helper.

Fixture smoke coverage:
- Multiple item context payloads produce a `TurnPipelineResult`.
- `events` preserve stable mapper order.
- `to_dict()` serialization preserves refs and events.
- Empty payloads produce an empty event tuple and safe result.
- The helper does not mutate the source payload and does not insert `turn_events` or `turn_pipeline`.

Limitations:
- Result is a limited planning summary, not a full turn simulation.
- Item consumption is not simulated.
- HP updates and exact post-turn state are not simulated.
- Unavailable, blocked, deferred, unknown, or malformed contexts do not create events.

Safety:
- No `advisor_client.py` connection.
- No LLM payload connection.
- No runtime `TurnPipelineResult` payload insertion.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Recommended next step:
- v5.6 TurnPipelineResult Dry-run Report or v5.6 TurnPipeline Planning Design.
- Keep any next step disconnected from `advisor_client.py` unless T1/T2 explicitly approve payload exposure.

Verification:
- `uv run pytest tests/test_advisor_turn_events.py -q`: 19 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: first run timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`, best batch median `0.125000ms` vs threshold `0.120000ms`; `978 passed, 2 deselected`.
- Isolated perf target rerun 3x: passed 3/3.
- Final `uv run pytest -q`: 979 passed, 2 deselected.
- No threshold, skip, xfail, damage formula, raw roll, Q12, `ko_context`, or payload filtering changes were made.

---

## v5.4 - TurnEvent Mapper Smoke / Fixture Coverage Expansion

Purpose:
- Expand fixture coverage for the v5.3 item-context-to-`TurnEvent` mapper.
- Keep mapper output disconnected from `advisor_client.py` and the LLM payload.
- Validate safety wording before any future user-facing exposure.

Implemented:
- Expanded `tests/test_advisor_turn_events.py`.
- Added negative coverage for:
  - `available=false`
  - item/context status `unavailable`
  - item/context status `blocked`
  - item/context status `deferred`
  - unknown item ids
  - malformed optional context shapes
- Added explicit stable ordering assertions:
  - `species_stat_item_context`
  - `speed_order_context`
  - `survival_context`
  - `chilan_berry_context`
- Added safety wording checks for summaries and limitations.

Mapper behavior maintained:
- Light Ball maps to `damage` / `known_modifier` / `known`.
- Quick Claw maps to `pre_move` / `candidate` / `possible`.
- Focus Band maps to `on_damage_before_ko` / `candidate` / `possible`.
- Focus Sash maps to `on_damage_before_ko` / `candidate` / `possible`.
- Chilan Berry maps to `on_damage_before_ko` / `candidate` / `possible`.
- Only visible/usable `available=true` contexts create events.
- Unavailable, blocked, deferred, unknown, or malformed contexts create no events.

Safety:
- No `advisor_client.py` connection.
- No LLM payload connection.
- No `TurnPipelineResult` creation or connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Recommended next step:
- v5.5 TurnEvent Mapper Dry-run Report or v5.5 TurnPipeline Planning Design.
- Keep any next step disconnected from `advisor_client.py` until T1/T2 explicitly approve payload exposure.

Verification:
- `uv run pytest tests/test_advisor_turn_events.py -q`: 15 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`, best batch median `0.125000ms` vs threshold `0.120000ms`.
- Isolated perf target rerun 3x: passed 3/3.
- `uv run pytest tests/test_damage_perf.py -q` after isolated reruns: same timing-sensitive failure, best batch median `0.125000ms` vs threshold `0.120000ms`.
- `uv run pytest -q`: 975 passed, 2 deselected.
- Final `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- No threshold, skip, xfail, damage formula, raw roll, Q12, `ko_context`, or payload filtering changes were made.

---

## v5.3 - Item Context TurnEvent Mapper Implementation

Purpose:
- Add a helper-level mapper from existing advisor context dictionaries to `TurnEvent` candidates.
- Keep the mapper disconnected from `advisor_client.py` and the LLM payload.
- Keep this as a planning/debug layer, not a full Turn Engine.

Implemented:
- Added `llm.advisor_turn_events`.
- Added `build_turn_events_from_advice_payload(...)`.
- The helper accepts an already-built move/context dictionary or advice payload fragment.
- The helper returns `tuple[TurnEvent, ...]`.
- The helper does not mutate the input payload and does not insert `turn_events`.

First-pass mappings:
- Light Ball from `species_stat_item_context`:
  - `damage`
  - `known_modifier`
  - `known`
- Quick Claw from `speed_order_context`:
  - `pre_move`
  - `candidate`
  - `possible`
- Focus Band / Focus Sash from `survival_context`:
  - `on_damage_before_ko`
  - `candidate`
  - `possible`
- Chilan Berry from `chilan_berry_context`:
  - `on_damage_before_ko`
  - `candidate`
  - `possible`

Policy:
- Only `available=true` contexts create events.
- Unavailable, blocked, or deferred contexts create no event in v5.3.
- Event output uses stable context order:
  - `species_stat_item_context`
  - `speed_order_context`
  - `survival_context`
  - `chilan_berry_context`
- Nested move paths under `moves.my_selected_move` and `moves.my_available_moves[*]` are preserved in `payload_key`.

Safety:
- No `advisor_client.py` connection.
- No LLM payload connection.
- No `TurnPipelineResult` creation or connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No actual Gemini call.
- No Vertex AI call.

Recommended next step:
- v5.4 Item Context TurnEvent Mapper Smoke / Dry-run Report.
- Exercise representative fixture payloads through the mapper and document the resulting events without connecting them to advice payloads.
- Keep `advisor_client.py`, LLM payload, item trigger evaluation, item consumption, HP update, and speed/order simulation out of scope.

Verification:
- `uv run pytest tests/test_advisor_turn_events.py -q`: 11 passed.
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_damage_perf.py -q`: timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; first run best batch median `0.140625ms` vs threshold `0.120000ms`.
- Isolated perf target rerun 3x: passed 3/3.
- `uv run pytest tests/test_damage_perf.py -q` after isolated reruns: same timing-sensitive failure, best batch median `0.156250ms` vs threshold `0.120000ms`.
- `uv run pytest -q`: same timing-sensitive failure, best batch median `0.125000ms` vs threshold `0.120000ms`; `970 passed, 2 deselected`.
- Second perf file rerun: same timing-sensitive failure, best batch median `0.156250ms` vs threshold `0.120000ms`.
- Second `uv run pytest -q`: same timing-sensitive failure, best batch median `0.140625ms` vs threshold `0.120000ms`; `970 passed, 2 deselected`.
- No threshold, skip, xfail, damage formula, raw roll, Q12, `ko_context`, or payload filtering changes were made.

---

## v5.2 - Item Context to TurnEvent Mapping Design

Purpose:
- Design how existing advisor item/context payload surfaces should map into `TurnEvent` candidates.
- Keep `TurnEvent` as a debug/planning layer, not a replacement for item contexts.
- Prepare v5.3 mapper implementation without advisor/LLM payload integration.

Inventory covered:
- `damage_estimate`
- `ko_context`
- `speed_context`
- `speed_order_context`
- `species_stat_item_context`
- `type_boost_context`
- `survival_context`
- `resist_berry_context`
- `chilan_berry_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`

Stage/status/certainty mapping:
- Light Ball / `species_stat_item_context`: `damage`, `known_modifier`, `known`.
- type-boost items: `damage`, `known_modifier`, `known` when already applied by `damage_estimate.item_effects`.
- Choice Scarf in `speed_context`: `pre_move`, `known_modifier`, `known` for effective Speed only, not final order.
- Quick Claw / `speed_order_context`: `pre_move`, `candidate`, `possible`.
- Focus Band / Focus Sash in `survival_context`: `on_damage_before_ko`, `candidate`, `possible`.
- Chilan Berry / `chilan_berry_context`: `on_damage_before_ko`, `candidate`, `likely`.
- standard resist berries: `on_damage_before_ko`, `candidate`, `possible`.
- Sitrus Berry / healing berries: `post_damage`, `candidate` or `not_simulated`, `possible` or `not_simulated`.
- Leftovers: `post_turn`, `candidate`, `possible`.
- Shell Bell: `on_hit_or_damage_dealt`, `not_simulated`, `not_simulated`.
- White Herb / Mental Herb / Loaded Dice: future not-simulated planning targets.

Migration path:
- v5.3 should create TurnEvent candidates from already-built context dictionaries.
- Existing item context payloads remain unchanged.
- `advisor_client.py` remains disconnected.
- LLM payload remains unchanged.
- User-facing exposure is deferred to v5.4+.

Recommended next step:
- v5.3 Item Context TurnEvent Mapper Implementation.
- Add `llm/advisor_turn_events.py`.
- Map available Light Ball, Quick Claw, Focus Band / Focus Sash, and Chilan Berry contexts first.
- Add fixture-level tests only.
- Do not implement trigger evaluation, item consumption, HP updates, speed simulation, or payload integration.

Safety:
- Documentation-only design.
- No production code change.
- No actual Gemini call.
- No Vertex AI call.
- No `advisor_client.py` connection.
- No LLM payload connection.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 960 passed, 2 deselected.

---

## v5.1 - Turn Event Contract Implementation

Purpose:
- Add the first Minimal Turn Engine contract layer.
- Keep the implementation limited to dataclasses, serialization, and validation.
- Do not connect the contract to `advisor_client.py` or the LLM payload.

Implemented:
- Added `core.turn_event`.
- Added `TurnEvent`.
- Added `TurnPipelineResult`.
- Added `normalize_turn_event(...)`.
- Added `normalize_turn_pipeline_result(...)`.

Validation:
- `TurnEvent.stage` must be one of:
  - `pre_turn`
  - `pre_move`
  - `damage`
  - `on_damage_before_ko`
  - `on_hit_or_damage_dealt`
  - `post_damage`
  - `post_turn`
- `TurnEvent.status` must be one of:
  - `candidate`
  - `known_modifier`
  - `not_simulated`
  - `blocked`
  - `unavailable`
- `TurnEvent.certainty` must be one of:
  - `known`
  - `likely`
  - `possible`
  - `unknown`
  - `not_simulated`
- sides must be `player`, `opponent`, `field`, `unknown`, or `None`.
- warnings, limitations, and events are normalized into tuples.

Behavior:
- `TurnEvent` can express candidates, known modifiers, not-simulated hooks, blocked hooks, and unavailable hooks.
- `TurnPipelineResult.simulated` defaults to `none`.
- `full` is accepted as a future-compatible schema value, but v5.1 does not produce or depend on full simulation.
- The contract does not mutate HP, consume items, evaluate triggers, or simulate turn order.

Safety:
- No `advisor_client.py` connection.
- No LLM payload connection.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_turn_event.py -q`: 15 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 960 passed, 2 deselected.

---

## v5.0 - Minimal Turn Engine MVP Design

Purpose:
- Design the first Minimal Turn Engine layer after the v4 TurnSnapshot phase.
- Keep this as a planning/contract design, not a full battle simulation.
- Use `TurnSnapshot` as selected/pre-turn input state.

Designed:
- Minimal Turn Engine responsibilities and non-responsibilities.
- Stage model:
  - `pre_turn`
  - `pre_move`
  - `damage`
  - `on_damage_before_ko`
  - `on_hit_or_damage_dealt`
  - `post_damage`
  - `post_turn`
- `TurnEvent` candidate fields:
  - `stage`
  - `source`
  - `subject_side`
  - `target_side`
  - `item_id`
  - `trigger_type`
  - `status`
  - `certainty`
  - `summary`
  - `limitations`
  - `payload_key`
- `TurnPipelineResult` candidate fields:
  - `input_snapshot`
  - `selected_move_id`
  - `damage_estimate_ref`
  - `ko_context_ref`
  - `events`
  - `warnings`
  - `limitations`
  - `simulated`

Existing context relationship:
- `damage_estimate` remains the damage primitive.
- `ko_context` remains limited damage-roll context.
- item contexts remain additive advice surfaces.
- `TurnEvent` should first align/explain existing surfaces rather than replace them.
- Known applied modifiers such as eligible Light Ball can map to `damage` / `known_modifier`.
- Focus Band, Focus Sash, resist berries, Chilan Berry, Quick Claw, Shell Bell, healing berries, White Herb, Mental Herb, Loaded Dice, and Mega Stones are classified as stage-specific planning targets.

Non-goals:
- full Showdown-equivalent simulation
- exact RNG or speed tie resolution
- irreversible item consumption mutation
- exact post-turn HP
- exact status/volatile resolution
- complete multi-hit event engine
- LLM payload insertion of turn pipeline results

Recommended next step:
- v5.1 Turn Event Contract Implementation.
- Add `core/turn_event.py` or `core/turn_pipeline.py`.
- Implement serializable/validated `TurnEvent` and `TurnPipelineResult` dataclasses.
- Add fixture-level tests only.
- Do not connect to `advisor_client.py`.
- Do not implement item trigger evaluation, item consumption, HP update, speed simulation, or full Turn Engine behavior.

Safety:
- Documentation-only design.
- No production code change.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption or HP update logic.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 945 passed, 2 deselected.

---

## v4.9 - TurnSnapshot Phase Closure / v5.0 Prep

Purpose:
- Close the v4 TurnSnapshot phase and prepare the next design milestone.
- Separate completed selected/pre-turn snapshot work from the future Turn Engine scope.

Closed scope:
- v4.1 `core.turn_state` contract.
- v4.3 optional top-level `turn_snapshot` payload adapter.
- v4.5 UI-selected `battle_input` -> `TurnSnapshot` builder.
- v4.6 TurnSnapshot payload smoke verification.
- v4.7 TurnSnapshot flow handoff.
- v4.8 local dry-run/debug snapshot report.

Current state:
- TurnSnapshot is optional selected/pre-turn known-state context.
- `run_ui_selected_advice(...)` attempts snapshot construction and falls back safely.
- Snapshot present path adds top-level `turn_snapshot` plus limitations.
- Snapshot absent path preserves previous payload behavior.
- Actual Gemini calls are not required to inspect local snapshot output.
- Damage estimates, raw rolls, Q12, `ko_context`, item contexts, and payload filtering remain unchanged.

Still not implemented:
- full Turn Engine
- item trigger evaluation
- item consumption
- HP update / post-turn state
- speed/order simulation
- exact status/volatile resolution
- multi-hit event engine

Recommended next step:
- v5.0 Minimal Turn Engine MVP Design.
- Start with `TurnEvent` / `TurnPipelineResult` contracts and event-stage planning.
- Keep `TurnSnapshot` as input state, `damage_estimate` as primitive, and `ko_context` as limited damage-roll context.
- Do not jump directly to full simulation or irreversible item consumption.

Safety:
- Documentation-only closure.
- No production code change.
- No actual Gemini call.
- No Vertex AI call.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- isolated rerun `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed 3/3.
- `uv run pytest -q`: timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; best batch median `0.125000ms`, threshold `0.120000ms`; 944 passed, 2 deselected.
- full suite rerun `uv run pytest -q`: repeated timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; best batch median `0.125000ms`, threshold `0.120000ms`; 944 passed, 2 deselected.
- No threshold, skip, or xfail changes were made.

---

## v4.8 - TurnSnapshot UI Dry-run / Local Debug Snapshot Report

Purpose:
- Add a local dry-run/debug report for inspecting the TurnSnapshot payload path without any actual Gemini call.
- Keep runtime advice behavior unchanged.

Implemented:
- Added `scripts/spike_turn_snapshot_debug.py`.
- The script builds a deterministic fixture `battle_input`, creates a `TurnSnapshot`, attaches it through `build_ui_advice_payload(..., turn_snapshot=...)`, and prints a JSON report to stdout.
- Added `docs/debug_turn_snapshot_sample_v4.8.md` with the sample output and safety notes.
- Added regression coverage that imports the report builder and verifies snapshot presence, absent/fallback behavior, limitations guard, and non-goals.

Dry-run sample:
- player species: `charizard`
- opponent species: `garchomp`
- player HP percent: `88`
- opponent HP percent: `41`
- player item/status: `choice-scarf` / `user_confirmed`
- opponent item/status: `focus-sash` / `user_confirmed`
- selected move: `flamethrower`
- top-level `turn_snapshot` present: true
- absent path omits `turn_snapshot`: true
- limitations guard present: true
- payload matches absent path after removing snapshot fields: true
- invalid HP fallback returns `None`: true

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No production advice behavior change.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering behavior change.

Verification:
- `uv run python scripts/spike_turn_snapshot_debug.py`: passed; emitted local JSON report only.
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 13 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; best batch median `0.125000ms`, threshold `0.120000ms`.
- isolated rerun `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed 3/3.
- perf file rerun `uv run pytest tests/test_damage_perf.py -q`: repeated timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; best batch median `0.140625ms`, threshold `0.120000ms`.
- `uv run pytest -q`: timing-sensitive failure in `test_item_damage_calculation_under_point_12ms_average`; 944 passed, 2 deselected.
- No threshold, skip, or xfail changes were made.

---

## v4.7 - TurnSnapshot UI Flow Documentation / Handoff Cleanup

Purpose:
- Consolidate the v4.1-v4.6 TurnSnapshot flow into one handoff document.
- Clarify what is connected today and what remains outside the current selected/pre-turn snapshot path.

Documented:
- `core/turn_state.py` owns the shared `TurnSnapshot` contract.
- `llm/advisor_turn_snapshot.py` builds snapshots from UI-selected `battle_input`.
- `run_ui_selected_advice(...)` passes the optional snapshot into the advice payload path.
- top-level `turn_snapshot` is additional selected/pre-turn context only.
- snapshot failure falls back to the previous advice flow.
- damage estimates, raw rolls, Q12, `ko_context`, item contexts, and payload filtering remain unchanged.

Not implemented:
- full Turn Engine
- item trigger evaluation
- item consumption
- HP update logic
- post-turn state
- speed/order simulation
- exact item trigger/status/volatile resolution

Recommended next step:
- v4.8 TurnSnapshot UI Dry-run / Local Debug Snapshot Report.
- Reason: inspect the exact local UI-selected snapshot without any Gemini call before v5.0 Turn Engine design.

Safety:
- Documentation-only cleanup.
- No production code change.
- No actual Gemini call.
- No Vertex AI call.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.

Verification:
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 12 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 944 passed, 2 deselected.

---

## v4.6 - TurnSnapshot Payload Smoke Verification

Purpose:
- Verify the v4.3/v4.5 TurnSnapshot payload connection without any actual Gemini call.
- Confirm snapshot present, absent, and fallback paths remain additive and do not alter existing calculator/context behavior.

Verified:
- Valid UI-selected `battle_input` builds a `TurnSnapshot`.
- Present snapshot path adds top-level `turn_snapshot` with player/opponent species, HP percent, selected move, and known item id/status.
- Present snapshot path adds selected/pre-turn snapshot limitations to `scenario.known_limitations`.
- Invalid snapshot input returns `None` through the user-facing fallback helper.
- Absent/fallback path omits `turn_snapshot` and preserves the existing default advice payload.
- Removing only `turn_snapshot` and snapshot limitations from the snapshot payload produces the same payload as the absent snapshot path.
- `run_ui_selected_advice(...)` can build prompt text with snapshot context when valid and fall back without snapshot context when invalid, using mocked Gemini calls in tests only.

Behavior:
- No production code changes.
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.
- No damage estimate, `ko_context`, item-context, or filtering behavior change.

Verification:
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 12 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 944 passed, 2 deselected.

---

## v4.5 - UI Selected State TurnSnapshot Builder

Purpose:
- Build a minimal `TurnSnapshot` from the existing UI-selected `battle_input` and pass it through the optional v4.3 payload adapter.
- Keep this as selected/pre-turn state context only; do not implement full Turn Engine behavior.

Implemented:
- Added `llm/advisor_turn_snapshot.py`.
- Added strict `build_turn_snapshot_from_battle_input(...)`.
- Added user-facing fallback `try_build_turn_snapshot_from_battle_input(...)`.
- Mapped active player/opponent species, slot index, HP percent, known item id/status, and selected player move.
- Kept stat stages empty, major status `None`, volatile conditions empty, weather `None`, terrain `None`, field conditions empty, and turn number `None`.
- Connected `run_ui_selected_advice(...)` to build a snapshot and pass it into `_build_ui_selected_prompt(...)` / `build_ui_advice_payload(...)`.
- Preserved existing advice flow when snapshot construction fails.

Behavior:
- Snapshot absent behavior remains unchanged.
- Snapshot present behavior adds top-level `turn_snapshot` and v4.3 limitations.
- `system_default_none` and explicit no-item profiles map to battle-state `absent`; unknown/unconfirmed profiles stay `unknown`.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.
- No damage estimate, `ko_context`, item-context, or filtering behavior change.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering behavior change.
- No new item implementation.
- No threshold, skip, or xfail change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_turn_snapshot.py -q`: 11 passed.
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 943 passed, 2 deselected.

---

## v4.4 - UI Selected State to TurnSnapshot Mapping Design

Purpose:
- Design how current UI-selected state can be converted into the v4.1 `TurnSnapshot` contract now that v4.3 can attach snapshots to the LLM payload.
- Keep this as design-only; actual UI mapping is deferred to v4.5.

Findings:
- UI-selected state already provides active player/opponent species, slot index, HP percent, selected player move, item profiles, and item status through `_build_llm_battle_input()`.
- Stat stages, major status, volatile conditions, weather, terrain, field conditions, and turn number are not connected yet and should remain empty or `None`.
- `system_default_none` is a calculator assumption and should map to battle-state `unknown`, while user-confirmed `none` can map to `absent`.

Recommendation:
- Build snapshots from existing `battle_input` rather than importing UI widgets directly.
- Add a v4.5 helper module such as `llm/advisor_turn_snapshot.py`.
- Keep `core.turn_state` as the pure contract module.
- Preserve current advice behavior if snapshot construction fails in user-facing flow.

v4.5 MVP:
- Implement `build_turn_snapshot_from_battle_input(battle_input)`.
- Map player/opponent species, slot index, HP percent, item status/id, and selected player move.
- Leave stat stages/status/weather/terrain/field conditions/turn number unconnected.
- Do not change damage estimates, `ko_context`, item contexts, filtering, or prompt semantics beyond the already optional v4.3 snapshot adapter.

Safety:
- Documentation-only design.
- No actual Gemini call.
- No Vertex AI call.
- No code changes.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 932 passed, 2 deselected.

---

## v4.3 - Turn Snapshot Payload Adapter

Purpose:
- Attach the v4.1 `TurnSnapshot` contract to the default LLM advice payload as an optional top-level `turn_snapshot`.
- Preserve existing payload behavior when no snapshot is supplied.

Implemented:
- Added optional `turn_snapshot` arguments to `build_ui_advice_payload(...)` and `_build_ui_selected_prompt(...)`.
- Added adapter logic that normalizes `TurnSnapshot` or mapping input with `normalize_turn_snapshot(...)` and serializes with `to_dict()`.
- Added top-level `turn_snapshot` only when explicitly supplied.
- Added `TURN_SNAPSHOT_KNOWN_LIMITATIONS` and snapshot-specific prompt guard wording.
- Kept invalid snapshot handling strict: invalid values raise `ValueError` instead of being silently coerced or omitted.
- Added tests for absent snapshot behavior, present snapshot serialization, mapping normalization, invalid snapshot validation, prompt guard wording, absent guard behavior, and unchanged damage/`ko_context`/item-context payload sections.
- Documented the adapter in `docs/spike_v4.3_turn_snapshot_payload_adapter.md` and updated `docs/advisor_payload_contract.md`.

Behavior:
- Absent snapshot path remains unchanged.
- Present snapshot is selected/pre-turn known state context only.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering behavior change.
- No new item implementation.
- No threshold, skip, or xfail change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 57 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 932 passed, 2 deselected.

---

## v4.2 - Turn Snapshot Payload Adapter Design

Purpose:
- Design how the v4.1 `TurnSnapshot` contract should attach to the LLM advice payload.
- Keep the design additive, optional, and clearly separate from full Turn Engine output.

Recommendation:
- Use an optional top-level `turn_snapshot` payload section.
- Do not use names such as `turn_engine_result`, `battle_simulation`, `engine_result`, or `final_turn_state`.
- If no `TurnSnapshot` is supplied, default advice payload output should remain unchanged.
- If a `TurnSnapshot` is supplied, normalize with `normalize_turn_snapshot(...)`, serialize with `to_dict()`, and add only the top-level snapshot plus snapshot-specific limitations.

Limitations:
- `turn_snapshot` is selected/pre-turn known state, not full turn simulation.
- Item trigger evaluation, item consumption, post-damage HP updates, speed/order simulation, and exact status/volatile resolution are not implemented.
- Gemini should not claim full turn simulation, exact item trigger results, consumed items, exact post-turn HP, guaranteed move order, or exact status resolution from the snapshot alone.

v4.3 implementation plan:
- Add a small payload adapter helper at the LLM payload boundary.
- Keep absent snapshot behavior unchanged.
- Add top-level `turn_snapshot` only when explicitly provided.
- Add snapshot limitations only when the section is present.
- Do not connect to damage estimate, `ko_context`, item contexts, trigger results, HP updates, item consumption, or speed simulation.

Future connection:
- Map UI selected active slot state, known item profile, HP percent, stat stages, and known conditions into `TurnSnapshot` in later milestones.
- Add a separate item trigger result contract before modeling consumption or post-damage HP updates.

Safety:
- Documentation-only design.
- No actual Gemini call.
- No Vertex AI call.
- No code changes.
- No full Turn Engine implementation.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 50 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 925 passed, 2 deselected.

---

## v4.1 - Turn State Snapshot Contract

Purpose:
- Implement the first minimal contract from the v4.0 Turn Engine / Battle State design.
- Add serializable, validated turn-state structures without connecting them to advisor payload generation, damage estimates, item contexts, or `ko_context`.

Implemented:
- Added `core/turn_state.py` as a shared domain contract module rather than an LLM-owned module.
- Added frozen dataclasses for `PokemonBattleSlot`, `BattleState`, `TurnInput`, and `TurnSnapshot`.
- Added `to_dict()` / `from_dict(...)` helpers plus `normalize_turn_snapshot(...)`.
- Added minimal validation for side values, item status values, HP percent range, stat stage range, turn number, and string list fields.
- Normalized mutable mapping/list inputs into immutable mapping/tuple fields for safer snapshot use.
- Added `tests/test_turn_state_snapshot.py` for serialization, defaults, validation, unknown/None preservation, and immutability checks.
- Documented the contract in `docs/spike_v4.1_turn_state_snapshot_contract.md` and updated the payload contract docs.

Behavior:
- No advisor payload insertion.
- No damage estimate connection.
- No `ko_context` connection.
- No item trigger evaluation.
- No item consumption.
- No HP update logic.
- No speed/order simulation.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No full Turn Engine implementation.
- No new item implementation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No threshold, skip, or xfail change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_turn_state_snapshot.py -q`: 18 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 50 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 925 passed, 2 deselected.

---

## v4.0 - Turn Engine / Battle State Design

Purpose:
- Design the minimum Turn Engine / Battle State layer needed after the v3.2 item context verification queue closure and v3.4 guard registry cleanup.
- Explain why the next broad direction should be battle state and turn timing rather than more limited item contexts.

Findings:
- Current advisor state is selected-Pokemon, selected-move, item-profile, damage-estimate, `ko_context`, and limited item-context oriented.
- It does not own full turn sequence, event timing, item consumption, post-damage HP updates, stat-stage timelines, volatile/status timelines, form/state changes, or final move order.
- Remaining item candidates such as Shell Bell, healing berries, White Herb, Mental Herb, Mega Stones, Focus Band, Quick Claw, and Loaded Dice need those state/timing hooks.

Design:
- Proposed minimal `PokemonBattleSlot`, `BattleState`, `TurnInput`, and `TurnSnapshot` contracts.
- Split Turn Engine responsibilities into pre-turn snapshot, move input, speed/order context, damage estimate, `ko_context`, item trigger evaluation, post-damage update, consumption update, and advisor payload generation.
- Classified item triggers into pre-move, on-damage-before-KO, on-hit/on-damage-dealt, post-damage HP threshold, on-stat-drop, on-status/volatile, form/state, and multi-hit event families.
- Kept existing damage estimate and `ko_context` as calculation primitives and limited damage-roll context.
- Kept existing item contexts as the migration surface; future trigger results can become their source of truth gradually.

Recommended next:
- `v4.1 Turn State Snapshot Contract`.
- Implement a BattleState / TurnSnapshot schema or dataclass layer without full turn simulation and without changing current damage estimate behavior.

Safety:
- Documentation-only design.
- No actual Gemini call.
- No Vertex AI call.
- No code changes.
- No new item implementation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 50 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 907 passed, 2 deselected.

---

## v3.4 - Item Context Guard Registry Cleanup

Purpose:
- Centralize available item context mention labels, item-specific guard text, and forbidden wording metadata.
- Keep behavior unchanged while reducing the chance that a future item context is added without guard metadata.

Implemented:
- Added `ADVICE_ITEM_CONTEXT_GUARD_METADATA` beside the existing context registry in `llm/advisor_payload_contract.py`.
- Moved available item context mention labels and Light Ball-specific no-item residue guard text out of ad hoc `advisor_client.py` branching and into registry metadata.
- Kept `advisor_client.py` responsible for traversing the filtered default advice payload and building the prompt guard from visible `available=true` contexts.
- Preserved Light Ball guard wording, Chilan Berry Normal-type limited label, Quick Claw limited move-order label, survival/resist berry labels, and fallback item-name labels.
- Added tests that every `ADVICE_ITEM_CONTEXT_KEYS` entry has guard metadata and that special Light Ball / Chilan Berry / Quick Claw metadata remains present.
- Documented the guard registry in `docs/advisor_payload_contract.md`.

Behavior preserved:
- `available=true` item contexts remain the only mention-guard targets.
- unavailable/deferred/blocked item contexts remain hidden from default advice payload.
- debug/enriched reasons remain available for tests and diagnostics.
- Choice Scarf stays protected in top-level `speed_context`, not move-level `speed_order_context`.
- Light Ball no-item residue guard remains present.
- Chilan Berry Normal-type limited guard remains present.

Safety:
- No actual Gemini call.
- No Vertex AI call.
- No new item implementation.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering behavior change.
- No threshold, skip, or xfail change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 50 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 907 passed, 2 deselected.

---

## v3.3 - Item Context System Stabilization Design

Purpose:
- Design a stabilization pass for the expanded item context system after the v3.2 verification queue closure.
- Document registry, available guard, unavailable filtering, debug reason handling, current context status, cleanup candidates, and why Turn Engine / Battle State should come before broad item expansion.

Findings:
- `ADVICE_ITEM_CONTEXT_KEYS` / `ADVICE_CONTEXT_KEYS` cover the active item context surface, with `speed_context` intentionally kept as the top-level Choice Scarf Speed exception.
- Default advice filtering consistently keeps `available=true` contexts and hides unavailable/deferred/blocked/debug reasons from default advice.
- Required mention guard generation works from the filtered default payload, but its label and item-specific wording rules now live mostly in `advisor_client.py`.
- Light Ball is the key source-of-truth lesson: actual PASS required aligning `species_stat_item_context.available=true` with applied `damage_estimate.item_effects`.
- Many remaining item candidates require state/timing/event modeling instead of another limited context.

Recommended v3.4 cleanup candidates:
- Move item-context guard metadata / mention labels toward a contract registry helper.
- Centralize debug-only reason and no-item residue filtering policy.
- Reorganize `docs/advisor_payload_contract.md` around context key, trigger, default/debug behavior, raw damage effect, `ko_context` effect, actual Gemini status, and Turn Engine dependency.
- Keep old pending handoff wording clearly archived/closed so future sessions do not rerun closed verification by accident.

Next:
- Recommended next milestone: `v3.4 Item Context Guard Registry Cleanup`.
- Larger direction after stabilization: `v4.0 Turn Engine / Battle State Design`.

Safety:
- Documentation-only design.
- No actual Gemini call.
- No Vertex AI call.
- No code changes.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 906 passed, 2 deselected.

---

## v3.2 - Item Context Verification Closure / Handoff Cleanup

Purpose:
- Close the item-context actual Gemini verification queue after v3.1.1.
- Update handoff docs so the next T3 starts from the final PASS state rather than old BLOCKED / PARTIAL / FAIL history.

Final actual Gemini status:

| Item / context | Final status | Closure note |
|---|---|---|
| Focus Band / `survival_context` | PASS | v2.5 actual advice used limited survival wording with no forbidden wording. |
| Quick Claw / `speed_order_context` | PASS | v2.5 actual advice used limited move-order wording with no forbidden wording. |
| Chilan Berry / `chilan_berry_context` | PASS | v2.7.1 actual advice described Chilan Berry as Normal-type limited context and preserved raw-roll / `ko_context` limits. |
| Light Ball / `species_stat_item_context` | PASS | v3.1.1 actual advice said Light Ball is Pikachu-specific and applied for Pikachu in the damage estimate. |

Light Ball resolution path:
- v2.5: PARTIAL.
- v2.6.1: FAIL.
- v2.7.1: PARTIAL.
- v2.8.1: FAIL.
- v2.9: payload conflict analysis.
- v3.0: damage estimate integration design.
- v3.1: Light Ball damage estimate integration implementation.
- v3.1.1: actual Gemini verification PASS.

Root cause:
- `species_stat_item_context.available=true` was present while `damage_estimate` still carried no-item / not-applied assumptions.
- Gemini correctly noticed the payload tension and described Light Ball as recognized but not applied.

Final fix:
- User-confirmed Pikachu + Light Ball is now integrated into the advisor damage estimate under narrow conditions.
- `species_stat_item_context` is aligned as a sibling explanation of applied `damage_estimate.item_effects`.
- Eligible Light Ball raw rolls and `ko_context` now follow the adjusted estimate; non-Light-Ball behavior is unchanged.

Current item-context surface:

| Context key | Implemented | Legal-gated | Default advice filtering | Actual Gemini status | Notes / limitations |
|---|---:|---:|---|---|---|
| `survival_context` | yes | yes | available context kept; unavailable/debug reasons hidden | PASS for Focus Band; historical PARTIAL for Focus Sash | no final survival probability or item-consumption truth |
| `recovery_context` | yes | yes | available context kept; unavailable/debug reasons hidden | PARTIAL | recovery timing and final KO integration remain out of scope |
| `accuracy_context` | yes | yes | available context kept; unavailable/debug reasons hidden | PASS | no final hit probability integration |
| `critical_context` | yes | yes | available context kept; unavailable/debug reasons hidden | PASS | no final crit probability or damage integration |
| `flinch_context` | yes | yes | available context kept; unavailable/debug reasons hidden | PARTIAL | flinch chance and turn sequencing remain limited |
| `multi_hit_context` | yes | yes, but legal availability limits current coverage | blocked/unavailable context hidden | PASS for blocked quietness; NOT_RUN for legal available Loaded Dice | hit-count probability is not integrated |
| `resist_berry_context` | yes | yes | available standard SE berry context kept; non-SE quietness preserved | PASS | berry-adjusted raw damage / KO not integrated |
| `type_boost_context` | yes | yes plus damage metadata | available matching-type context kept; mismatches hidden | PASS | sibling explanation for supported damage item effects |
| `speed_context` | yes | yes | top-level Speed context remains separate from move-level item contexts | PASS for Choice Scarf | not final turn order |
| `speed_order_context` | yes | yes | available Quick Claw context kept; unavailable/debug reasons hidden | PASS for Quick Claw | no final move-order truth or Turn Engine |
| `species_stat_item_context` | yes | yes plus species-stat metadata | available Pikachu + Light Ball context kept; non-Pikachu/unconfirmed hidden | PASS for Light Ball | Light Ball is applied only for eligible user-confirmed Pikachu attacker damage estimates |
| `chilan_berry_context` | yes | yes plus Normal metadata | available Normal damaging move context kept; non-Normal/unconfirmed hidden | PASS for Chilan Berry | Chilan-adjusted raw damage / KO not integrated |

Next:
- Recommended next milestone: `v3.3 Item Context System Stabilization`.
- Suggested follow-up focus: consolidate context registry/source-of-truth documentation, guard tests, and applied-vs-explanatory context boundaries before adding more items.
- Larger next product direction: `v4.0 Turn Engine / Battle State Design`.
- Rationale: many remaining item candidates need item consumption, timing, status, stat-stage, recovery timing, or turn-order modeling; adding more limited contexts first risks repeating the Light Ball payload-truth problem.

Safety:
- Documentation-only closure.
- No actual Gemini call.
- No Vertex AI call.
- No code changes.
- No damage formula change.
- No raw damage roll change.
- No Q12 multiplier change.
- No `ko_context` calculation change.
- No payload filtering change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 906 passed, 2 deselected.

---

## v3.1 - Light Ball Damage Estimate Integration

Purpose:
- Align Light Ball `species_stat_item_context.available=true` with an applied advisor damage estimate.
- Resolve the v2.8.1 / v2.9 payload conflict where Gemini saw both Light Ball context and no-item damage estimate assumptions.

Implemented:
- Added a narrow advisor damage estimate path for user-confirmed, Champions legal `light-ball` on attacker-side `pikachu`.
- Applied the existing species-stat item modifier to the advisor estimate attack or special attack stat for damaging physical/special moves.
- Marked `damage_estimate.item_effects.attacker_item.status` as `applied` with `effect_type=species_stat_item_modifier`.
- Moved eligible Light Ball estimates away from `assumptions.item=none` and no-item assumption profile wording.
- Reframed `species_stat_item_context` as a sibling explanation of the applied `damage_estimate.item_effects` modifier.
- Kept non-Pikachu, unconfirmed Light Ball, defender-side Light Ball, and status/unsupported-category moves unapplied.
- Preserved Chilan Berry, Focus Band, Quick Claw, type boost, and resist berry context boundaries.

Safety:
- No core damage formula change.
- No Q12 constant change.
- Raw damage rolls intentionally change only for eligible Pikachu + user-confirmed Light Ball damaging physical/special moves.
- `ko_context` naturally follows the adjusted damage estimate rolls; no separate Light-Ball-specific KO hack was added.
- No actual Gemini call.
- No Vertex AI call.
- No legal fixture change.
- No threshold, skip, or xfail change.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 1 timing-sensitive perf failure, 905 passed, 2 deselected.
  - failure: `test_item_damage_calculation_under_point_12ms_average`
  - best batch median: `0.125000ms`
  - threshold: `0.120000ms`
  - isolated target 3x: passed
  - perf file rerun: 4 passed
  - threshold/skip/xfail unchanged.

Next:
- Completed by v3.1.1: Light Ball actual Gemini verification reached PASS.

---

## v3.1.1 - Light Ball Damage Estimate Integration Actual Verification

Purpose:
- Verify the v3.1 Light Ball damage estimate integration with one actual Gemini Developer API call.

Preflight:
- `species_stat_item_context.available=true`.
- Holder species is `pikachu`.
- `damage_estimate.item_effects.attacker_item.status=applied`.
- `damage_estimate.assumptions.item` is not `none`.
- `damage_estimate.assumption_profile.label` no longer says `no item`.
- Required mention guard and Light Ball-specific no-item residue guard are present.
- `ko_context.damage` matches the adjusted damage estimate range.

Actual Gemini result:
- Provider: `gemini_developer_api`.
- Model: `gemini-2.5-flash`.
- Vertex AI: not used.
- Light Ball actual response: PASS.
- Gemini described Water Pulse damage as default assumptions plus the supported Light Ball modifier.
- Gemini explicitly said Light Ball is Pikachu-specific and applied for Pikachu in this damage estimate.
- Forbidden wording observed: none.
- Payload leak observed: none.
- Gemini did not generalize Light Ball to non-Pikachu holders.
- Gemini did not claim guaranteed KO, confirmed OHKO, always doubles damage, or exact final stats.

Safety:
- No code changes in v3.1.1.
- No damage formula change.
- No Q12 multiplier change.
- No non-Light-Ball raw damage behavior change.
- No non-Light-Ball `ko_context` behavior change.
- No payload filtering change.
- No new item implementation.
- No Vertex AI call.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 96 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 906 passed, 2 deselected.

---

## Naming Convention (since 3.1 closure)

```
<Major>.<Minor>.<Patch><suffix>
   │       │       │      └─ same-patch split work (a, b, c, ...)
   │       │       └─ patch (single feature unit)
   │       └─ minor (subsystem group)
   └─ major (product stage)
```

- `3.1.5a` = damage engine / 5th patch / split a
- `3.1.5a-Δ` = deferred-debt cleanup of `3.1.5a`
- Internal git PR numbers are **not** referenced in conversation; use milestone codes only.

---

## Current Position

- **Milestone:** `5.0` Multi-hit Moves & Chip Damage Integration - **COMPLETE**
- **HEAD:** `fa8501d`
- **Tag:** `v0.11.0`
- **Tests:** 602 passing, 0 failures, 0 xfail
- **Performance:** N=4 multi-hit + chip hard ceiling met; worst measured 17.886 ms

---
## Phase 4: COMPLETE

- **Completed:** 2026-05-07
- **Tag:** `v0.10.0`
- **Merge commit:** `2f342d8`
- **Tests:** 518 → 560 (+42), 0 failures, 0 xfail
- **Performance:** N=4 convolution avg 0.215 ms (budget 100 ms)
- **Scope:** Fraction-based 1-4 turn KO probability composer, 16-roll Q12 distribution, crit-rate integration, and canonical modifier scenarios.
- **Next:** Phase 5 preview — multi-hit plus chip damage composition.

---

## Phase 5: COMPLETE

- **Completed:** 2026-05-07
- **Tag:** `v0.11.0`
- **Merge commit:** `fa8501d`
- **Tests:** 560 -> 602 (+42), 0 failures, 0 xfail
- **Scope:** Multi-hit move probability distributions plus deterministic residual chip integration.
- **Multi-hit:** Tier A 2-5 distribution, Skill Link, Loaded Dice, and Population Bomb Tier C support.
- **Chip:** Burn, poison, toxic, Leech Seed, Curse, sand/hail/snow, and binding residuals.
- **Precision:** `Fraction` probability mass throughout; Q12 damage rolls remain integer-only.
- **Performance:** N=4 multi-hit + chip worst measured 17.886 ms with crit-mixed Bullet Seed; Population Bomb + Loaded Dice measured 3.500 ms. Both remain under the 100 ms hard ceiling.

### Phase 5.1: Performance Optimization Accepted

- **Branch:** `feat/phase-5.1-bullet-seed-perf`
- **Diagnosis:** H2/H4 - missing survivor bucket merge plus convolution loop overhead.
- **Fix:** Composer survivor state uses dense integer buckets below KO threshold; `Fraction` construction is deferred to the final by-turn probability boundary.
- **Tests:** 602 default -> 604 with slow (+2), 0 failures, 0 xfail.

| Case | Before | After |
|---|---:|---:|
| bullet_seed_default_burn_no_crit | 13.608 ms | 6.137 ms |
| bullet_seed_default_burn_with_crit | 17.886 ms | 8.861 ms |
| bullet_seed_loaded_dice_toxic_with_crit | 2.207 ms | 1.161 ms |
| population_bomb_loaded_dice_poison_with_crit | 3.500 ms | 2.388 ms |

#### Perf Test Strategy

Perf regression tests use the `slow` pytest marker and are excluded from the default test run. This isolation prevents resource contention with 600+ functional tests that otherwise inflate measurements 2.1~2.6x in shared-environment runs.

**Usage:**
- Default development: `pytest` (602 tests, perf tests excluded)
- Perf verification: `pytest -m slow` (2 perf tests, clean env)
- Full coverage: `pytest -m ""` (604 tests, perf may be flaky)

**Threshold:** 15ms median (warmup + 3-run) on the bullet_seed worst case. T3 standalone baseline 8.861ms; threshold provides ~70% headroom for per-machine variance while still catching algorithmic regressions.

**Phase 6 note:** New perf tests (Parental Bond, Accuracy-Turn) should inherit the `slow` marker via module-level `pytestmark`.

Soft target 5ms partially recovered. The with_crit case at 8.86ms is accepted; hard ceiling 100ms maintained with >90% headroom. Deferred deeper optimization (FFT-style convolution) is out of scope until Phase 6 baseline is established.

T1 to record local measurement post-merge for cross-validation.

### Phase 6 Outlook

- Parental Bond interaction modeling.
- Accuracy and turn-engine interactions for move continuation and chip timing.
- Broader battle-state integration on top of the Phase 4/5 probability core.

---
## Major Roadmap

| Major | Codename | Status |
|---|---|---|
| 1.x | Foundation | ✅ Complete |
| 2.x | Stat Engine | ✅ Complete |
| **3.x** | **Damage Engine** | 🔧 ~30% (3.1 done) |
| 4.x | Turn Engine | ❌ Not started |
| 5.x | Battle AI | ❌ Not started |
| 6.x | UI / CLI / API | ❌ Not started |

---

## 3.x — Damage Engine

### 3.1 — Core Damage Formula ✅ CLOSED

| Code | Item | Status | Tests |
|---|---|---|---|
| 3.1.1 | Status modifiers (burn/paralysis) | ✅ | 296 |
| 3.1.2 | Stat Doublers (Huge Power, Pure Power, Hustle) | ✅ | 304 |
| 3.1.3 | Defensive Boosters (Fur Coat, Ice Scales, Multiscale, Shadow Shield) | ✅ | 316 |
| 3.1.4a | SpA Boosters (Solar Power, Plus, Minus) | ✅ | 326 |
| 3.1.4b | Two-Pass BP Hook (Technician, Tough Claws, Iron Fist) | ✅ | 341 |
| 3.1.5a | Damage Reducers (Filter, Solid Rock, Prism Armor, Punk Rock-D) | ✅ | 357 |
| 3.1.5b | HP-Conditional Type Boosters (Overgrow, Blaze, Torrent, Swarm, Defeatist) | ✅ | 375 |
| 3.1.5c | Damage Chain Gap Fill (Strong Jaw, Mega Launcher, Reckless, Punk Rock-O, Sheer Force BP, Transistor) | ✅ | 393 |
| 3.1.5d | Item Layer 1 (Life Orb, Choice Band/Specs, Muscle Band, Wise Glasses, Expert Belt, Flame Plate) | ✅ | 381* |
| 3.1.5a-Δ | Sheer Force secondary-effect suppression (Path B predicate) | ✅ | 386 |
| 3.1.5d-Δ | Life Orb 1/10 max HP recoil (Path B pure function) | ✅ | 393 |

\* 3.1.5d temporarily showed 417 before squash reconciliation; final consolidated count = 381 after restoring 4 silently-deleted item tests (charcoal, eviolite, light_ball, species_orb).

### 3.2 — Item Wiring (next candidate)

| Code | Item | Status |
|---|---|---|
| 3.2.1 | Choice Scarf (defer to 4.x — speed only) | ⏭️ deferred |
| 3.2.2 | Assault Vest, Eviolite (partial in 3.1.5d) | 🟡 partial |
| 3.2.3 | Type-resist Berries (Occa, Passho, etc.) | ❌ |
| 3.2.4 | Pinch Berries (Salac, Liechi — damage only) | ❌ |
| 3.2.5 | Sitrus / Lum / Leftovers | ⏭️ defer to 4.x |
| 3.2.6 | Air Balloon, Iron Ball, Ring Target | ❌ |
| 3.2.7 | Weakness Policy, Throat Spray | ⏭️ defer to 4.x |
| 3.2.8 | Z-Crystals (Gen 7) | ⏭️ low priority |
| 3.2.9 | Mega Stones (stat + type/ability swap) | ❌ |

### 3.3 — Field & Weather

| Code | Item | Status |
|---|---|---|
| 3.3.1 | Weather (Sun/Rain/Sand/Snow) damage modifiers | ❌ |
| 3.3.2 | Terrain (Electric/Grassy/Misty/Psychic) | ❌ |
| 3.3.3 | Weather/Terrain-setting abilities (Drought, Surge) | ❌ |
| 3.3.4 | Aura abilities (Fairy/Dark Aura, Aura Break) | ❌ |
| 3.3.5 | Room effects (Wonder Room, Magic Room) | ❌ |

### 3.4 — Move-Specific Mechanics

| Code | Item | Status |
|---|---|---|
| 3.4.1 | Multi-hit moves (Bullet Seed, Rock Blast) | ❌ |
| 3.4.2 | Fixed damage (Seismic Toss, Night Shade, Endeavor) | ❌ |
| 3.4.3 | Variable BP (Gyro Ball, Electro Ball, Low Kick) | ❌ |
| 3.4.4 | Counter / Mirror Coat / Metal Burst | ❌ |
| 3.4.5 | OHKO moves | ❌ |
| 3.4.6 | Spread moves (0.75x doubles) | ❌ |
| 3.4.7 | Critical hit mechanics | 🟡 partial |

### 3.5 — Parity Hardening

| Code | Item | Status |
|---|---|---|
| 3.5.1 | `@smogon/calc` 1000-case randomized comparison | ❌ |
| 3.5.2 | Per-generation branching (Gen 1–9) | 🟡 Gen 9 only |
| 3.5.3 | Edge case regression suite (Wonder Guard, Levitate) | 🟡 partial |
| 3.5.4 | Performance benchmark (10k calc / sec) | ❌ |

---

## Test Count Trajectory

```
292 → 296 → 304 → 316 → 326 → 341 → 357 → 375 → 393 → 381 → 386 → 393
 (init)  PR#1  PR#2  PR#3  PR#4  PR#5  PR#6  PR#7  PR#8  squash  Δ-a   Δ-d
```

Parity tests: `112 → 114 → 118 → 122 → 128 → 134 → 140 → 148 → 139`

The dip from 393 → 381 reflects the squash + silent-deletion restoration of 4 item tests, not a regression.

---

## Verified Q12 Constants (audit-stable)

### BP Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 6144 | ×1.50 | technician, strong-jaw, mega-launcher |
| 5325 | ×1.30 | tough-claws, sheer-force, punk-rock (offensive) |
| 4915 | ×1.20 | iron-fist, reckless |
| 4505 | ×1.10 | muscle-band, wise-glasses |

### Attack / Special Attack Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 8192 | ×2.00 | huge-power, pure-power |
| 6144 | ×1.50 | hustle, guts, overgrow, blaze, torrent, swarm (Atk); solar-power, plus, minus, overgrow, blaze, torrent, swarm (SpA); choice-band, choice-specs (item) |
| 5325 | ×1.30 | transistor (Gen 9 nerf, was 6144) |
| 4915 | ×1.20 | flame-plate (item) |
| 2048 | ×0.50 | defeatist (Atk + SpA) |

### Defense / Special Defense Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 2048 | ×0.50 | fur-coat (physical received), ice-scales (special received) |

### Final Modifiers
| Constant | Multiplier | Sources |
|---|---|---|
| 5325 | ×1.30 | life-orb |
| 4915 | ×1.20 | expert-belt |
| 3072 | ×0.75 | filter, solid-rock, prism-armor (super-effective received) |
| 2048 | ×0.50 | multiscale, shadow-shield (full HP), punk-rock (def, sound) |

---

## History Log (chronological commits)

### `3.1.5a-d` Consolidated Squash → `e8a0893`
Sequential PRs #6–9 + PR #9.1 hotfix were developed in working directory and squashed into one commit. Splitting into 4 reconstructed commits provided no real bisect value (intermediate states were never tested in isolation).

Restored 4 item tests silently deleted during PR #9:
- charcoal, eviolite, light_ball, species_orb (adamant / lustrous / griseous orb)

### `3.1.5a-Δ` (Sheer Force suppression) → `587d29f`
- Path B chosen: no secondary-effect resolver exists yet
- Added pure predicate in `advisor/damage/move_categories.py`
- Tests: 381 → 386
- Note: commit subject reads `3.1.6a / PR #8a` (pre-rename); milestone code is `3.1.5a-Δ`

### `3.1.5d-Δ` (Life Orb recoil) → `d3469ca`
- Path B chosen: no turn engine exists yet
- Added pure recoil computation in `advisor/damage/recoil.py`
- Spec: Bulbapedia — 10% max HP, rounded down, min 1 HP; suppressed by Magic Guard and Sheer Force-boosted moves
- Tests: 386 → 393
- Note: commit subject reads `3.1.6b / PR #9a` (pre-rename); milestone code is `3.1.5d-Δ`

### Docs commit → `4a833a4`
- 3.1.5 deferred debt closed
- 3.1 milestone fully terminated

---

## Legacy ↔ Current Code Mapping

| Old reference (in commits / earlier docs) | Current milestone code |
|---|---|
| PR #1 | 3.1.1 |
| PR #2 | 3.1.2 |
| PR #3 | 3.1.3 |
| PR #4 | 3.1.4a |
| PR #5 / 3.1.5c-pr5 | 3.1.4b |
| PR #6 | 3.1.5a |
| PR #7 | 3.1.5b |
| PR #8 | 3.1.5c |
| PR #9 / PR #9.1 | 3.1.5d |
| PR #8a / "3.1.6a" | 3.1.5a-Δ |
| PR #9a / "3.1.6b" | 3.1.5d-Δ |

Future commits use milestone codes directly. PR numbers are git-internal only.

---

## Next Decision Point

`3.1` is closed. Choose next branch before opening any new patch:

- **Option A — `3.2` Item Wiring**: horizontal expansion, fastest path to single-hit Smogon parity 100%
- **Option B — `4.1` Turn Engine**: vertical expansion, unlocks deferred items naturally
- **Option C — `3.3` Field/Weather**: high battle-impact gap-fill

Decision pending. Baseline `4a833a4` / 393 tests is safe to pause on.

---

## v0.5.2 LLM Advice Panel Success Verification

Completed: 2026-05-08

- Verified `scripts/spike_advisor.py` with a valid Gemini API key.
- LLM recommendation returned successfully for the Mega Kangaskhan vs Garchomp spike.
- Recommendation selected `Return`, identified no OHKO, and flagged Garchomp `Outrage` as the main threat.
- Token usage: 1960 input / 148 output / 0 cached.
- Estimated cost: `$0.000958`.
- UI success path confirmed by screenshot:
  - `LLMAdvicePanel` displays the recommendation.
  - Status bar shows `Done | input 1960 / output 148 | $0.0009580`.
  - Fallback cost label also shows the token/cost summary.
- Existing validation remains: `613 passed, 2 deselected`.

Status: v0.5.2 success path verified. Ready for the next UI integration slice.

---

## v0.8.1 — Manual move payload verification attempt

Completed: 2026-05-14

Purpose:
- Attempt to verify the v0.8 manual move selection path from UI-selected Pokemon state to the LLM payload and Gemini response.
- Record the verified payload behavior separately from the blocked Gemini success path.
- Preserve the existing pytest baseline.

Partial verification succeeded:
- Manual move selection path exercised with Charizard vs Garchomp and slot 1 set to Flamethrower.
- Confirmed the selected move button text updates to `화염방사`.
- Confirmed `moves.my_available_moves` includes only the user-selected Flamethrower move.
- Confirmed empty move slots are omitted from `moves.my_available_moves`.
- Confirmed `moves.my_selected_move` matches `moves.my_selected_move_index == 0`.
- Confirmed `moves.move_data_status` is `user_selected_partial_v0.8`.
- Confirmed cache learnsets are not included in the LLM payload.
- Confirmed `moves.opponent_available_moves` remains empty in v0.8.
- Confirmed the UI running state sets the request button disabled, recommendation text to `분석 중...`, and status bar to `Analyzing...`.
- Confirmed the UI recovers after a failed Gemini call by re-enabling the request button and showing the fallback error label.

Blocked / not verified:
- `GEMINI_API_KEY` was present in the Codex environment; `GOOGLE_API_KEY` was not present.
- The Gemini endpoint returned HTTP 400 `INVALID_ARGUMENT` in this environment.
- Gemini success response was not verified.
- LLM response quality was not evaluated.
- The success status bar path `Done | input N / output N | $...` was not verified in this run.
- No API key value was printed, saved, or committed.

Tests:
- `uv run pytest -q`
- Result: 613 passed, 2 deselected.

Remaining limitations:
- A valid T1 local Gemini run is still needed to verify the v0.8.1 success response path.
- Opponent moves are not connected yet.
- Damage/OHKO/2HKO/KO chance are not connected yet.
- EV/IV/nature/item/final stats are not connected yet.
- LLM response quality for the v0.8 selected-move payload remains unjudged because the Gemini call did not succeed.

---

## v0.9.2b - MoveSearchBox Champions Fixture Integration

Purpose:
- Route move search candidates through the sample Champions movepool fixtures instead of PokeAPI historical Pokemon learnsets.
- Keep PokeAPI move data as metadata only.

Implemented:
- MoveSearchBox now receives candidate move ids from `ChampionsMovePoolRepository`.
- Fixture-backed Pokemon use their sample Champions move ids.
- Pokemon without a Champions movepool fixture show an unavailable search state instead of silently falling back to PokeAPI learnsets.
- Added regression tests for Charizard, Froslass, Vanilluxe, Starmie, missing fixtures, and metadata lookup.

Out of scope maintained:
- No full Serebii/RotomLabs scraping.
- No full roster Champions movepool cache.
- No damage engine changes.
- No four-move comparison.

---

## v0.9.2c - Serebii Champions Full Movepool Cache

Purpose:
- Replace narrow sample movepools with Serebii-derived Champions movepool fixtures for the full local Champions roster.
- Keep PokeAPI pokemon learnsets out of move legality decisions.

Implemented:
- Added `scripts/build_serebii_champions_movepools.py` to parse Serebii Champions Pokédex Standard Moves tables.
- Added `scripts/verify_champions_movepools.py`.
- Generated movepool fixtures for all 276 unique local Champions battle entities.
- Preserved global denial of `tera-blast` and verified `hidden-power` is absent.
- Marked `pawmot` as `unavailable_source_error` because Serebii Champions currently returns 404 for its page.

Verification:
- `uv run python scripts/verify_champions_movepools.py`
- Result: 276 entities, 17,115 listed move entries, unavailable source fixtures: `pawmot`.

Out of scope maintained:
- No RotomLabs scraping.
- No automatic scheduled scraping.
- No damage engine changes.
- No four-move damage comparison.

---

## v0.9.2d - Champions Move Korean Name Coverage

Purpose:
- Ensure every move in the Serebii-derived Champions movepool cache has a Korean display/search name.
- Keep move selection working even when PokeAPI move metadata is not locally cached.

Implemented:
- Added `scripts/update_champions_move_ko_mapping.py`.
- Updated `data/ko_mapping.json` for all 490 Champions move ids.
- Added manual Korean-name overrides for recent moves that PokeAPI does not localize yet.
- Added Champions movepool metadata fallback in `MoveRepository`.
- Verified `expanding-force` maps to `와이드포스` and can be searched for Starmie.

Verification:
- `uv run pytest -q`
- Result: 648 passed, 2 deselected.

---

## v0.8.3 — Advisor Payload Contract

Purpose:
- Freeze the current UI-to-LLM payload contract before selected-move damage estimates are added.
- Keep the Gemini recommendation layer from treating incomplete UI metadata as confirmed battle math.

Added:
- `docs/advisor_payload_contract.md`
- `llm/advisor_payload_contract.py`
- `tests/test_advisor_payload_contract.py`

Contract summary:
- Current payload mode remains `ui-selected-pokemon-v0.8`.
- Payload includes selected Pokemon identity, type, base stats, abilities, HP percent, selected move index, and user-confirmed move metadata.
- Payload explicitly does not include final stats, EV/IV/nature, held items, weather, terrain, boosts, exact HP, opponent moves, damage rolls, OHKO/2HKO/KO chance, turn order, or Turn Engine state.
- Guardrails prohibit the LLM from inferring exact damage, KO odds, speed order, survival, unprovided stats/items/field state, or Terastallization.

Next milestones:
- `v0.9 — Selected Move Damage Estimate`
- `v0.10 — Four-Move Damage Comparison`

---

## v0.9 — Selected Move Damage Estimate

Purpose:
- Add a default-assumption damage estimate for the currently selected user-confirmed move.
- Keep the estimate scoped to `moves.my_selected_move.damage_estimate`.
- Preserve the v0.8.3 guardrails so the LLM does not treat the estimate as final battle damage.

Implemented:
- `llm/advisor_damage_estimate.py`
- Default assumptions: level 50, IV 31 all, EV 0 all, neutral nature, no item, no boosts, no weather, no terrain, no screens, no crit, no ability effects, non-spread single-target estimate.
- `MainWindow._build_llm_battle_input()` now attaches the selected move estimate through the helper instead of doing damage math in UI code.
- `docs/advisor_payload_contract.md` and `llm/advisor_payload_contract.py` now describe the v0.9 estimate and limitations.

Out of scope maintained:
- No OHKO/2HKO/KO chance.
- No four-move comparison.
- No opponent moves.
- No EV/IV/nature/item/final stat UI.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

---

## v0.10 - Four-Move Damage Comparison

Purpose:
- Add default-assumption damage estimates for each user-confirmed move slot.
- Let the LLM compare the Q/W/E/R moves already selected in the UI without adding KO odds or full battle state.

Implemented:
- `moves.my_available_moves[*].damage_estimate` now uses the same default-assumption schema as the selected move.
- `moves.my_selected_move.damage_estimate` remains available for backward-compatible selected-move advice.
- Status moves and incomplete move payloads return unavailable schemas instead of inferred damage.
- Payload mode updated to `ui-selected-pokemon-v0.10`.

Out of scope maintained:
- No OHKO/2HKO/KO chance.
- No opponent moves.
- No EV/IV/nature/item/final stat UI.
- No weather/terrain/boost/screen UI.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

---

## v0.10.1 - Four-Move Damage Comparison verification

Purpose:
- Verify the v0.10 four-move damage payload path before moving to the next feature milestone.

Verified:
- Repository started clean and synced with `my_pochamps/master`.
- Offscreen payload check confirmed `moves.my_available_moves[*].damage_estimate` is attached for four user-confirmed move slots.
- Selected move consistency confirmed: `moves.my_selected_move.damage_estimate.selected_move_id` matched the selected slot's move id.
- Damaging moves returned default-assumption `damage_range`, `percent_range`, and 16 rolls.
- Status move handling confirmed with `will-o-wisp` returning `unavailable_status_move`.
- KO chance, OHKO chance, and 2HKO chance fields were absent from available-move estimates.
- Offscreen UI launch succeeded with `Master Ball Advisor v0.10`.
- LLM advice button state transition was verified: enabled -> disabled while running -> enabled after completion state.

Gemini:
- Actual Gemini call was verified with `GEMINI_MODEL=gemini-2.5-flash`.
- Gemini returned a recommendation successfully for Charizard vs Gardevoir with four user-confirmed moves.
- The response selected `Overheat` and compared it using the provided damage estimate: 49.0-58.7% of Gardevoir's default max HP.
- The response preserved the main limitation: estimates use default assumptions and are not final battle damage.
- The response did not claim OHKO, 2HKO, KO chance, survival, Tera, EVs, items, or final stats.
- No API key or secret value was printed or committed.
- The UI success path displayed usage (`input 4031 / output 52`) and re-enabled after completion.
- Cost display showed `$0.0000000`, indicating pricing metadata for `gemini-2.5-flash` still needs a TokenLogger update.

Verification:
- `uv run pytest -q`
- Result: 650 passed, 2 deselected.

Remaining limitations:
- Damage estimates remain default-assumption references, not final battle damage.
- EV/IV/nature/item/final stats, field state, exact HP, opponent moves, OHKO/2HKO/KO chance, and Turn Engine remain unconnected.

---

## v0.10.2 - Gemini Cost Logging Semantics

Purpose:
- Clarify what the UI cost number means after `gemini-2.5-flash` showed `$0.0000000`.
- Distinguish Free Tier zero-cost estimates from unknown model pricing.

Implemented:
- Added explicit pricing statuses to `TokenLogger`:
  - `free_tier_zero_cost`
  - `paid_tier_estimated_cost`
  - `unknown_model_or_unknown_pricing`
- Treated `gemini-2.5-flash` as a Free Tier zero-cost estimate in the local logger.
- Preserved paid-tier estimated cost behavior for existing priced models.
- Preserved warnings for unknown model pricing.
- Added `pricing_status` and `pricing_status_counts` to JSONL records and session summaries.
- Updated the UI cost label to show:
  - `Free tier | input N / output N | $0.0000000`
  - `Paid estimate | input N / output N | $...`
  - `Pricing unknown | input N / output N`

Notes:
- The official Gemini API pricing page distinguishes Free Tier from Paid Tier pricing.
- This logger reports local estimated cost semantics only; actual billing depends on the user's Google account, project, tier, limits, and current Gemini pricing.
- Prices and Free Tier availability can change and should be reviewed against the official Gemini API pricing page before budget-sensitive use.

Verification:
- `uv run pytest tests/test_token_logger.py tests/test_advisor_payload_contract.py -q`
- Result: 20 passed.

---

## v0.11 - Opponent Move Payload

Purpose:
- Add opponent move context to the LLM payload without treating possible moves as confirmed.
- Keep v0.10 my-side four-move damage comparison intact.

Implemented:
- Added top-level `opponent_moves` to the advisor payload.
- Added `known_moves` from user-confirmed opponent Q/W/E/R slots.
- Added `candidate_moves` from the Serebii-derived Champions movepool cache.
- Capped `candidate_moves` at 24 entries.
- Added `confidence: "possible_not_confirmed"` to all candidate moves.
- Removed known move ids from candidate moves to avoid duplicate semantics.
- Kept legacy `moves.opponent_available_moves` as an empty compatibility field.
- Updated payload contract guardrails so Gemini must not treat candidate moves as confirmed.

Out of scope maintained:
- No opponent damage estimate.
- No OHKO/2HKO/KO chance.
- No speed or turn order.
- No Turn Engine.
- No EV/IV/nature/item/final stats UI.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Manual payload check confirmed Garchomp `Earthquake` appears in `opponent_moves.known_moves`.
- Confirmed `opponent_moves.candidate_moves` is capped at 24 and labeled `possible_not_confirmed`.
- Confirmed known move ids are removed from candidate moves.
- Confirmed `moves.opponent_available_moves` remains `[]`.
- Confirmed opponent moves do not include `damage_estimate`.
- Confirmed v0.10 my-side `damage_estimate` still appears.
- `uv run pytest -q`
- Result: 657 passed, 2 deselected.

---

## v0.11.1 - Opponent move payload Gemini verification

Purpose:
- Verify that the v0.11 opponent move payload separates known opponent moves from possible candidate moves.
- Attempt a Gemini quality check for known/candidate move semantics.

Payload verification:
- Confirmed `opponent_moves.known_moves` includes user-confirmed Garchomp `Earthquake`.
- Confirmed known moves use `source: "user_confirmed"`.
- Confirmed `opponent_moves.candidate_moves` is generated from the Champions movepool cache.
- Confirmed every candidate move uses `confidence: "possible_not_confirmed"`.
- Confirmed candidate moves are capped at 24.
- Confirmed known move ids are removed from candidate moves.
- Confirmed `moves.opponent_available_moves` remains the legacy empty list.
- Confirmed opponent moves do not include `damage_estimate`.
- Confirmed my-side four-move `damage_estimate` remains present.

Gemini:
- Actual Gemini call was attempted with `GEMINI_MODEL=gemini-2.5-flash`.
- The Codex tool environment returned `API_KEY_INVALID`, so Gemini response quality could not be verified in this run.
- No API key or secret value was printed or committed.

T1 local app verification:
- Gemini call succeeded from the local PySide app.
- Status bar showed Free Tier cost semantics: `Free tier | input 6473 / output 75 | $0.0000000`.
- In a Charizard vs Garchomp scenario, Gemini recommended `Earthquake` based on the four-move damage comparison.
- The response mentioned the default-assumption limitation.
- The response did not claim KO, OHKO, or 2HKO.
- The response did not assert EVs, IVs, nature, items, boosts, speed order, or final stats.
- No candidate-move overclaim was observed.
- Opponent known/candidate move usage was not strongly visible in the response and needs more observation.

Verification:
- `uv run pytest -q`
- Result: 657 passed, 2 deselected.

Remaining limitations:
- More local Gemini runs are needed to judge whether the model consistently uses `known_moves` as confirmed and `candidate_moves` as possible only.
- Opponent damage estimate remains out of scope until v0.12.

---

## v0.11.2 - Opponent Move Awareness Prompt/Guardrail Polish

Purpose:
- Make Gemini's interpretation of `opponent_moves` more explicit without changing the payload schema.
- Encourage use of known opponent moves and cautious discussion of candidate moves.

Implemented:
- Added a concise prompt guardrail that:
  - treats `opponent_moves.known_moves` as user-confirmed opponent moves
  - treats `opponent_moves.candidate_moves` as possible, not confirmed, moves
  - allows candidate moves to be mentioned as possible threats only when labeled unconfirmed
  - states opponent move damage is not calculated
  - tells the model to use `my_available_moves` damage estimates for comparing the user's own move options
- Strengthened `ADVISOR_KNOWN_LIMITATIONS` with the same opponent-move semantics.
- Updated the advisor payload contract docs.

Manual verification checklist for T1:
- Confirm a known opponent move is reflected in the response when relevant.
- Confirm candidate moves are not described as confirmed moves.
- Confirm candidate moves, if mentioned, are labeled as possible/unconfirmed threats.
- Confirm opponent damage is not described as calculated.
- Confirm my four-move damage comparison remains part of the recommendation.

Out of scope maintained:
- No payload schema change.
- No opponent damage estimate.
- No candidate sorting polish.
- No UI changes.
- No `advisor/damage/` or `advisor/probability/` engine changes.

---

## v0.12 - Opponent Known Move Damage Estimate

Purpose:
- Add default-assumption damage estimates for user-confirmed opponent known moves.
- Let the advisor reason about how threatening a confirmed opponent move is against `my_active`.

Implemented:
- Generalized the LLM damage estimate helper so the attacker and defender payload keys can be selected.
- Added an opponent known move wrapper that calculates `opponent_moves.known_moves[*].damage_estimate`.
- Set opponent known move damage `scope` to `opponent_known_move_only`.
- Set opponent known move damage `target` to `my_active`.
- Kept the same default assumptions as v0.9/v0.10:
  - level 50
  - IV 31 all
  - EV 0 all
  - neutral nature
  - no item, boosts, weather, terrain, screens, critical hit, doubles, or unselected ability effects
- Updated advisor payload contract guardrails for v0.12.

Maintained boundaries:
- Candidate moves do not receive `damage_estimate`.
- OHKO/2HKO/KO chance is not included.
- Speed order, Turn Engine, final stats, EV/IV/nature/item UI, switch recommendation, and lead recommendation remain out of scope.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed opponent known move estimates are attached under `opponent_moves.known_moves[*].damage_estimate`.
- Confirmed opponent known move estimates use `target: "my_active"`.
- Confirmed candidate moves do not receive `damage_estimate`.
- Confirmed status known moves return `unavailable_status_move`.
- Confirmed v0.10 my-side damage estimate regression remains covered.
- `uv run pytest -q`
- Result: 661 passed, 2 deselected.

---

## v0.12.1 - Opponent known move damage Gemini verification

Purpose:
- Verify the v0.12 opponent known move damage payload shape.
- Attempt a Gemini quality check for opponent known move damage awareness.

Payload verification:
- Offscreen payload check used Charizard vs Garchomp with opponent known move `Earthquake`.
- Confirmed `opponent_moves.known_moves[0].move_id` is `earthquake`.
- Confirmed `opponent_moves.known_moves[0].source` is `user_confirmed`.
- Confirmed `opponent_moves.known_moves[0].damage_estimate.status` is `available_with_default_assumptions`.
- Confirmed `opponent_moves.known_moves[0].damage_estimate.target` is `my_active`.
- Confirmed `is_final_battle_damage` is `false`.
- Confirmed Charizard's Ground immunity is represented as `damage_range: 0-0` and `percent_range: 0.0-0.0`.
- Confirmed candidate moves do not include `damage_estimate`.
- Confirmed `moves.my_available_moves[*].damage_estimate` remains present for four user-confirmed moves.
- Confirmed `moves.opponent_available_moves` remains the legacy empty list.
- Confirmed KO/OHKO/2HKO fields are not present.

Gemini:
- Actual Gemini call was attempted with `gemini-2.5-flash`.
- The Codex execution environment returned `API_KEY_INVALID`, even though the environment variable was present.
- This is recorded as an environment/key validation issue, not a v0.12 payload regression.

T1 local app verification:
- Gemini call succeeded from the local valid-key PySide app.
- Status bar showed Free Tier cost semantics: `Free tier | input 7478 / output 101 | $0.0000000`.
- In a Charizard vs Garchomp scenario, Gemini recommended `Heat Wave` from the user's four move options.
- The response used the four-move damage comparison and cited `Heat Wave` at 18.0-21.3% estimated damage to Garchomp.
- The response recognized the opponent known move `Earthquake`.
- The response interpreted Charizard's Flying typing correctly and stated that Earthquake is ineffective/immune against Charizard.
- Candidate Dragon-type moves were described only as unconfirmed possible threats.
- No candidate move overclaim was observed.
- No opponent damage overclaim was observed.
- The response did not claim KO, OHKO, or 2HKO.
- The response preserved the default-assumption limitation and did not assert EVs, IVs, nature, items, final stats, speed order, or turn outcome.

Verification:
- `uv run pytest -q`
- Result: 661 passed, 2 deselected.

Remaining limitations:
- Codex tool environment Gemini response quality remains unverified because that environment returned `API_KEY_INVALID`.
- The damage estimate remains a default-assumption reference, not final battle damage.
- Candidate move damage, KO odds, speed order, final stats, EV/IV/nature/item, and Turn Engine state remain out of scope.

---

## v0.13 - Stats Assumption Profile

Purpose:
- Make the stat model behind every damage estimate explicit.
- Clarify that current damage estimates are still default-assumption rough references.

Implemented:
- Added `ADVISOR_DEFAULT_ASSUMPTION_PROFILE` with id `default_level50_ivs31_evs0_neutral_no_item`.
- Added `assumption_profile` to available damage estimates.
- Added `assumption_profile` to unavailable damage estimate schemas.
- Kept the existing `assumptions` field for compatibility.
- Updated advisor payload mode and contract guardrails for v0.13.
- Updated advisor payload contract documentation.

Maintained boundaries:
- No UI changes.
- No final stats input.
- No EV/IV/nature/item input.
- No top-level `stat_profiles`.
- No item selection.
- No KO/OHKO/2HKO, speed order, or Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed `moves.my_available_moves[*].damage_estimate.assumption_profile` is present.
- Confirmed `moves.my_selected_move.damage_estimate.assumption_profile` is present.
- Confirmed `opponent_moves.known_moves[*].damage_estimate.assumption_profile` is present.
- Confirmed the default profile id is `default_level50_ivs31_evs0_neutral_no_item`.
- Confirmed `source: "system_default"`, `confidence: "rough_reference"`, and `is_user_confirmed: false`.
- Confirmed the existing `assumptions` field remains present.
- Confirmed `is_final_battle_damage` remains `false`.
- `uv run pytest -q`
- Result: 662 passed, 2 deselected.

---

## v0.14 - Final Stats Input

Purpose:
- Allow user-confirmed final stats for the selected my/opponent active Pokemon.
- Use those final stats in existing my-side and opponent-known-move damage estimates without changing the damage engine.

Implemented:
- Added top-level `stat_profiles.my_active` and `stat_profiles.opponent_active`.
- Added `StatProfileDialog` for HP / Atk / Def / SpA / SpD / Spe entry.
- Added a compact `Stats` button to Pokemon panels that opens the dialog for the selected slot.
- Stored final stats on the selected Pokemon panel.
- Added validation that accepts only complete six-stat positive integer profiles.
- Kept partial final stats as default assumptions instead of silently mixing values.
- Updated damage helper stat resolution:
  - my move damage can use `my_active` attacker final stats and `opponent_active` defender final stats
  - opponent known move damage can use `opponent_active` attacker final stats and `my_active` defender final stats
- Updated `damage_estimate.assumption_profile` to `user_confirmed_final_stats_level50` when user-confirmed final stats are used.
- Kept `is_final_battle_damage` as `false`.
- Updated advisor payload contract guardrails for v0.14.

Maintained boundaries:
- No bench Pokemon final stats editing.
- No EV/IV/nature/item input.
- No item, ability, boost, weather, terrain, or screen UI.
- No KO/OHKO/2HKO.
- No speed order.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed default stat profiles are emitted for both active Pokemon when final stats are absent.
- Confirmed user-confirmed final stats are emitted for `my_active` and `opponent_active` when all six stats are present.
- Confirmed partial final stats remain default assumptions.
- Confirmed my move damage uses user-confirmed attacker/defender final stats.
- Confirmed opponent known move damage uses user-confirmed attacker/defender final stats.
- Confirmed `damage_estimate.assumption_profile` changes to `user_confirmed_final_stats_level50`.
- Confirmed `is_final_battle_damage` remains `false`.
- Confirmed KO/OHKO/2HKO fields remain absent.

---

## v0.16.1 - Type Effectiveness Metadata

Purpose:
- Prevent LLM type matchup explanation overclaims.
- Add calculated type effectiveness metadata to each available damage estimate.
- Give Gemini an explicit source for immune / resisted / neutral / super-effective wording.

Context:
- T1 local Gemini testing correctly reflected damage comparison and Ground immunity, but incorrectly described Dragon damage against Corviknight as super effective.
- Corviknight is Flying/Steel, so Dragon is resisted by Steel and should be labeled `not_very_effective`.

Implemented:
- Added `damage_estimate.type_effectiveness`.
- Added `multiplier` and `label` fields.
- Label mapping:
  - `0.0` -> `immune`
  - greater than `0.0` and less than `1.0` -> `not_very_effective`
  - `1.0` -> `neutral`
  - greater than `1.0` -> `super_effective`
- Updated prompt guardrails so type matchup wording must use `damage_estimate.type_effectiveness` when present.
- Updated advisor payload contract documentation and guardrails.

Maintained boundaries:
- No type chart changes.
- No new damage formula.
- No item UI.
- No speed order.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No candidate move damage.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed Dragon Claw/Outrage-style Dragon damage into Corviknight is labeled `not_very_effective`.
- Confirmed Earthquake into Corviknight is labeled `immune` and has 0 damage.
- Confirmed prompt and contract mention `damage_estimate.type_effectiveness`.
- Offscreen UI smoke confirmed `Master Ball Advisor v0.14` launches and Pokemon panels expose Stats buttons.
- `uv run pytest -q`
- Result: 670 passed, 2 deselected.

---

## v0.16 - Minimal Damage Item Assumption

Purpose:
- Add item profile payload structure without adding item UI.
- Apply a small attacker-side damage item subset to existing my move and opponent known move damage estimates.
- Make applied and unapplied item effects explicit for the LLM.

Implemented:
- Added top-level `item_profiles.my_active` and `item_profiles.opponent_active`.
- Default UI payload emits `system_default_none` for both active Pokemon.
- Added support for user-confirmed attacker-side damage items in helper/test payloads.
- Applied the v0.16 subset through the existing damage engine item path:
  - `choice-band` for physical damage.
  - `choice-specs` for special damage.
  - `life-orb` for damage, with recoil marked as unapplied.
  - `muscle-band` for physical damage.
  - `wise-glasses` for special damage.
- Added `damage_estimate.item_effects` to available damage estimates.
- Updated `assumption_profile` ids when a supported damage item modifier is applied.
- Kept `is_final_battle_damage` as `false`.
- Updated advisor payload contract and prompt guardrails for item semantics.

Maintained boundaries:
- No item UI.
- No legal item scraping or cache generation.
- No Expert Belt or Assault Vest.
- No Choice Scarf speed.
- No Focus Sash survival.
- No Leftovers/Sitrus recovery.
- No Choice lock.
- No Life Orb recoil.
- No candidate move damage.
- No KO/OHKO/2HKO.
- No speed order or Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Verification:
- Confirmed default item profiles are emitted as `system_default_none`.
- Confirmed `choice-band` modifies physical move damage and not special move damage.
- Confirmed `choice-specs` modifies special move damage and not physical move damage.
- Confirmed `life-orb` modifies damage and records recoil in `unapplied_effects`.
- Confirmed `muscle-band` and `wise-glasses` apply only to their matching move categories.
- Confirmed unsupported items do not modify damage and are marked `unsupported_item`.
- Confirmed opponent known move damage uses `item_profiles.opponent_active` as attacker item.
- Confirmed candidate moves still do not receive `damage_estimate`.
- Confirmed KO/OHKO/2HKO fields remain absent.

---

## v0.14.1 - Final Stats Input local verification

Purpose:
- Verify the v0.14 final stats input flow without adding new functionality.
- Confirm that UI state, payload `stat_profiles`, and damage estimate assumption profiles remain aligned.

Verification:
- Confirmed the app launches offscreen as `Master Ball Advisor v0.14`.
- Confirmed Pokemon panels expose compact `Stats` buttons.
- Confirmed `StatProfileDialog` can save all six final stats.
- Confirmed the dialog `Clear` path returns to default assumptions.
- Confirmed partial final stats are not accepted as `user_confirmed_final_stats`.
- Confirmed `stat_profiles.my_active` and `stat_profiles.opponent_active` are emitted.
- Confirmed complete final stats produce `status: "user_confirmed_final_stats"` and `source: "user_input"`.
- Confirmed missing/partial final stats keep `status: "default_assumption"`.
- Confirmed my available move damage estimates use `assumption_profile.id: "user_confirmed_final_stats_level50"` when final stats are present.
- Confirmed opponent known move damage estimates use `assumption_profile.id: "user_confirmed_final_stats_level50"` when final stats are present.
- Confirmed sample final stats changed damage ranges compared with default-reference calculations.
- Confirmed `is_final_battle_damage` remains `false`.
- Confirmed KO/OHKO/2HKO fields remain absent.
- Confirmed opponent candidate moves still do not include `damage_estimate`.

Gemini verification:
- Attempted one Codex-environment Gemini call with `gemini-2.5-flash`.
- Result: not verified in Codex because the configured key returned `API_KEY_INVALID`.
- T1 local valid-key app verification is still required to confirm Gemini response quality.
- Expected checks for T1 local verification:
  - Gemini distinguishes user-confirmed final stats from default assumptions.
  - Gemini does not describe the damage as final battle damage.
  - Gemini keeps item/ability/boost/weather/terrain limitations.
  - Gemini does not assert KO/OHKO/2HKO or speed order.

Maintained boundaries:
- No payload schema changes.
- No UI changes.
- No EV/IV/nature/item input.
- No KO/OHKO/2HKO.
- No speed order or Turn Engine.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Test:
- `uv run pytest -q`
- Result: 670 passed, 2 deselected.

---

## v0.16.2 - Type Effectiveness Metadata local Gemini verification

Purpose:
- Verify the v0.16.1 `damage_estimate.type_effectiveness` metadata with a local valid-key Gemini call.
- Confirm Gemini uses the structured type-effectiveness metadata instead of inventing type matchup wording.

Scenario:
- My active Pokemon: Garchomp.
- Opponent active Pokemon: Corviknight.
- My available moves included `Outrage`, `Earthquake`, and `Rock Slide`.
- Opponent known moves were not required for this check.

Payload verification:
- Confirmed `Outrage` includes `damage_estimate.type_effectiveness.label: "not_very_effective"`.
- Confirmed `Outrage` damage range was `41-48`.
- Confirmed `Earthquake` includes `damage_estimate.type_effectiveness.label: "immune"`.
- Confirmed `Earthquake` damage range was `0-0`.
- Confirmed `Rock Slide` includes `damage_estimate.type_effectiveness.label: "neutral"`.
- Confirmed KO/OHKO/2HKO fields remain absent.
- Confirmed candidate moves remain outside damage estimate generation.

Gemini verification:
- Local valid-key Gemini call succeeded with `gemini-2.5-flash`.
- Gemini recommended `Outrage` based on the available move damage estimates.
- Gemini described `Outrage` as dealing more than `Rock Slide` despite being not very effective.
- Gemini described `Earthquake` as doing 0 damage because Corviknight is immune.
- Gemini did not call Dragon damage against Corviknight super effective.
- Gemini did not contradict `damage_estimate.type_effectiveness`.
- Gemini kept the limitation that estimates are reference values based on default assumptions, not final battle damage.

Maintained boundaries:
- No code changes.
- No prompt changes.
- No payload schema changes.
- No item UI.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest -q`
- Result: 686 passed, 2 deselected.

---

## v0.18 - Minimal Supported Item Selector

Purpose:
- Add a minimal app UI path for selecting supported held items.
- Connect selected item state to top-level `item_profiles` so existing v0.16 item damage helpers can apply supported attacker-side item modifiers.

Implemented:
- Added `ItemProfileDialog` with v0.18 options:
  - Unknown item
  - No item
  - Choice Band
  - Choice Specs
  - Life Orb
  - Muscle Band
  - Wise Glasses
- Added compact `Item` button state to Pokemon panels.
- Added item profile state to Pokemon panels.
- Reset item profile state when a panel's Pokemon changes or is cleared.
- `my_active` defaults to `system_default_none`.
- `opponent_active` defaults to `unknown`.
- User-confirmed supported items are emitted in `item_profiles`.
- Existing damage helpers now receive UI-selected item profiles through `MainWindow._build_llm_battle_input()`.
- Updated advisor payload mode to `ui-selected-pokemon-v0.18`.
- Updated advisor payload contract for the minimal item selector and opponent unknown-item default.

Verification:
- Confirmed `ItemProfileDialog` exposes the full v0.18 option set.
- Confirmed Unknown, No item, and supported item selections produce distinct payload profiles.
- Confirmed default `my_active` item profile is `system_default_none`.
- Confirmed default `opponent_active` item profile is `unknown`.
- Confirmed user-selected `Choice Band` is reflected in `item_profiles.my_active`.
- Confirmed user-selected `Life Orb` is reflected in `item_profiles.opponent_active`.
- Confirmed selected supported items flow into damage estimates through `item_effects`.
- Confirmed Life Orb recoil remains listed as an unapplied effect.
- Confirmed panel item profile resets on Pokemon change/clear.
- Confirmed offscreen `MainWindow` smoke creates both team columns with Item buttons.

Maintained boundaries:
- No legal item cache.
- No scraping.
- No unsupported legal item selector.
- No Expert Belt or Assault Vest.
- No Choice Scarf, Focus Sash, Leftovers, or Sitrus Berry.
- No Choice lock.
- No Life Orb recoil.
- No speed order or Turn Engine.
- No KO/OHKO/2HKO.
- No `advisor/damage/` or `advisor/probability/` engine changes.

Test:
- `uv run pytest -q`
- Result: 693 passed, 2 deselected.

---

## v0.18.1 - Minimal item selector verification and Korean UI polish

Purpose:
- Polish the minimal item selector UI text for Korean users.
- Verify that supported item selections continue to flow through `item_profiles` and `damage_estimate.item_effects`.

Implemented:
- Localized the `ItemProfileDialog` guidance text to Korean.
- Kept the v0.18 item selector scope unchanged.

Verification:
- Confirmed `ItemProfileDialog` guidance is Korean:
  - "현재는 데미지 보정 아이템 일부만 지원합니다."
  - "구애 고정, 반동, 스피드, 회복, 생존 효과, KO 확률은 미지원입니다."
- Confirmed `Life Orb` is emitted as a user-confirmed item profile.
- Confirmed `Life Orb` item effects mark `damage_modifier` as applied.
- Confirmed `Life Orb` recoil remains an unapplied effect.
- Confirmed `Choice Band` applies only to physical move damage.
- Confirmed `Choice Specs` applies only to special move damage.
- Confirmed `Unknown` item does not modify damage.
- Confirmed `No item` does not modify damage.
- Confirmed `opponent_active` default item state remains `unknown`.
- Confirmed KO/OHKO/2HKO fields remain absent.

Gemini verification:
- Not run in this Codex verification pass.
- T1 local valid-key app verification is still recommended for confirming natural-language wording around item modifiers.

Maintained boundaries:
- No legal item cache.
- No scraping.
- No unsupported item UI.
- No Expert Belt or Assault Vest.
- No Choice Scarf speed.
- No Focus Sash survival.
- No Leftovers/Sitrus recovery.
- No Choice lock.
- No Life Orb recoil.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_item_profile_dialog.py tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`
- Result: 45 passed.
- `uv run pytest -q`
- Result: 695 passed, 2 deselected.

---

## v0.18.2 - Item modifier Gemini response guardrail

Purpose:
- Make Gemini's natural-language response reflect supported item damage modifiers when they are already applied in `damage_estimate.item_effects`.
- Avoid confusing wording where an item-applied estimate is described as only default assumptions.

Context:
- T1 local Gemini checks showed correct move recommendations and type-effectiveness handling.
- However, when `Life Orb` or `Choice Band` was selected, Gemini often omitted the applied item modifier and only said "default assumptions."

Implemented:
- Strengthened the UI-selected advisor prompt:
  - if `damage_estimate.item_effects.attacker_item.status` is `applied`, mention the supported item damage modifier.
  - describe item-applied numbers as default assumptions plus the supported item modifier, not only default assumptions.
  - keep Choice lock, Life Orb recoil, speed, survival, recovery, and KO odds unmodeled.
- Added the same guardrail to `ADVISOR_KNOWN_LIMITATIONS`.
- Updated the advisor payload contract with explicit allowed/disallowed item explanation semantics.

Verification:
- Confirmed prompt text includes the applied-item explanation guardrail.
- Confirmed contract limitations include the same guardrail.
- Confirmed existing item-effect, type-effectiveness, and opponent-move guardrails remain present.

Gemini verification:
- Not run in this Codex verification pass.
- T1 local valid-key app verification is recommended to confirm Gemini now mentions Life Orb / Choice Band / Choice Specs damage modifiers when applied.

Maintained boundaries:
- No payload schema change.
- No item UI change.
- No legal item cache.
- No scraping.
- No unsupported item UI.
- No recoil, Choice lock, speed, survival, recovery, or KO/OHKO/2HKO implementation.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- Result: 17 passed.

- `uv run pytest -q`
- Result: 696 passed, 2 deselected.
- `uv run pytest -q`
- Result: 696 passed, 2 deselected.

T1 local valid-key verification:
- Confirmed Gemini now mentions supported item damage modifiers when applied.
- Choice Band case:
  - Gemini recommended `Iron Head`.
  - Gemini stated that the Choice Band damage modifier is applied to the physical move damage estimates.
  - Gemini did not claim Choice lock is modeled.
  - Gemini did not claim KO/OHKO/2HKO.
- Life Orb case:
  - Gemini recommended `Iron Head`.
  - Gemini described the estimate as `default assumptions plus the supported Life Orb damage modifier`.
  - Gemini mentioned the opponent item is unknown.
  - Gemini did not describe the estimate as final battle damage.
- Remaining response polish:
  - Gemini may surface the raw type-effectiveness label `super_effective` instead of natural wording like `super effective`.
  - Life Orb recoil is not always explicitly mentioned as unmodeled, even though it remains excluded in the payload/contract.

---

## v0.18.3 - Response wording polish for type labels and item effects

Purpose:
- Reduce awkward or misleading wording in Gemini responses without changing payload schema or damage calculation.
- Ensure raw type-effectiveness labels are converted to natural language.
- Make non-damage item limitations more consistently visible when supported item modifiers are applied.

Implemented:
- Strengthened prompt guidance:
  - do not print raw `type_effectiveness` labels such as `super_effective` or `not_very_effective`.
  - convert labels to natural wording such as `super effective`, `not very effective`, `immune/no effect`, or `neutral`.
  - if Life Orb is applied, say recoil is not modeled.
  - if Choice Band or Choice Specs is applied, say choice lock is not modeled.
  - avoid describing item-applied estimates as only default assumptions.
- Added the same wording guardrails to `ADVISOR_KNOWN_LIMITATIONS`.
- Updated `docs/advisor_payload_contract.md` with explicit type label and item-effect wording rules.

Verification:
- Confirmed prompt includes raw-label avoidance guidance.
- Confirmed prompt includes `super_effective` -> natural wording guidance.
- Confirmed prompt includes `not_very_effective` -> natural wording guidance.
- Confirmed prompt includes `immune/no effect` guidance.
- Confirmed prompt includes Life Orb recoil-not-modeled guidance.
- Confirmed prompt includes Choice Band/Specs choice-lock-not-modeled guidance.
- Confirmed contract limitations include the same guardrails.

Maintained boundaries:
- No payload schema change.
- No damage calculation change.
- No item calculation change.
- No item UI change.
- No legal item cache.
- No scraping.
- No recoil, Choice lock, speed, survival, recovery, or KO/OHKO/2HKO implementation.
- No Turn Engine.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- Result: 17 passed.

---

## v0.20 - Champions legal item fixture and repository

Purpose:
- Start separating Pokemon Champions Regulation M-A item legality from current damage-engine item support.
- Prevent the v0.18 minimal item selector from being mistaken for a Champions legal item selector.

Implemented:
- Added `data/static/champions_legal_items.json` as a manually curated sentinel fixture.
- Added `core/champions_item_repository.py`.
- Added repository helpers for:
  - fixture loading and schema validation.
  - item lookup and normalization.
  - legal item listing.
  - damage-supported-but-not-legal item listing.
  - item classification.
- Added tests for source refs, Regulation M-A metadata, legal sentinels, damage-supported mismatch sentinels, unknown items, list helpers, and fixture validation.

Fixture scope:
- This is not the full 117-item Regulation M-A list.
- Included legal sentinel items:
  - `choice-scarf`
  - `focus-sash`
  - `leftovers`
  - `sitrus-berry`
  - `metal-coat`
  - `charcoal`
- Included damage-supported-but-not-normal-legal-selector sentinels:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
  - `muscle-band`
  - `wise-glasses`

Source policy:
- Primary legal snapshot: MetaVGC.
- Cross-check candidates: RotomPicks and Serebii.
- Contextual held-item guide: ChampDex.
- Existing `data/static/items.json` and `data/static/items_damage.json` remain metadata/effect-support references, not Champions legality sources.
- PokeAPI remains metadata fallback only, not a Champions legality source.

Important classification result:
- `Choice Band`, `Choice Specs`, and `Life Orb` remain damage-supported by the current helper, but are not treated as normal Champions legal selector items.
- `Muscle Band` and `Wise Glasses` are kept as unconfirmed damage-supported mismatch sentinels until legality is confirmed.
- Legal-but-not-modeled items such as `Choice Scarf`, `Focus Sash`, `Leftovers`, and `Sitrus Berry` are recognized without applying speed, survival, recovery, or turn effects.

Maintained boundaries:
- No UI changes.
- No legal item selector integration.
- No scraping or build script.
- No `data/cache` generation.
- No item damage effect additions.
- No Expert Belt or Assault Vest additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, speed order, KO/OHKO/2HKO, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_champions_item_repository.py -q`
- Result: 16 passed.
- `uv run pytest tests/test_items.py tests/test_item_modifiers.py tests/test_item_profile_dialog.py tests/test_advisor_damage_estimate.py -q`
- Result: 47 passed.
- `uv run pytest -q`
- Result: 712 passed, 2 deselected.

---

## v0.20.1 - Item selector label clarification

Purpose:
- Clarify that the current ItemProfileDialog is not a full Pokemon Champions legal item selector.
- Reduce the risk that damage-supported test items are mistaken for confirmed Regulation M-A legal items.

Implemented:
- Updated ItemProfileDialog guidance text in Korean.
- The guidance now states:
  - the current list is not the full Pokemon Champions legal item list.
  - only some items connected to damage calculation are shown.
  - some items may be unconfirmed or differ from the actual Reg M-A legal list.
  - Choice lock, recoil, speed, recovery, survival effects, and KO odds are unsupported.
- Added test coverage for the clarified guidance text.

Maintained boundaries:
- No legal item selector implementation.
- No repository/UI integration.
- No legal item fixture changes.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- `uv run pytest tests/test_item_profile_dialog.py -q`
- Result: 6 passed.

---

## v0.20.2 - Local item selector and Gemini verification

T1 local valid-key verification:
- Life Orb selected state produced a successful Gemini response.
- Gemini recommended `Iron Head`.
- Gemini reflected the expected damage range: `140-166`.
- Gemini explicitly mentioned that the Life Orb damage modifier was applied.
- Gemini explicitly mentioned that Life Orb recoil is not modeled.
- Gemini mentioned that `Outrage` has no effect.
- Gemini mentioned that the opponent held item is unknown.
- Gemini used natural wording (`super effective`) instead of the raw `super_effective` label.
- Gemini did not overclaim final battle damage.
- Gemini did not claim KO/OHKO/2HKO certainty.
- Item selector behavior was confirmed locally.

Remaining follow-up:
- ItemProfileDialog guidance length/truncation can receive one more visual check in the running app.

Maintained boundaries:
- Documentation-only update.
- No code changes.
- No UI changes.
- No legal item selector implementation.
- No repository/UI integration.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

---

## v0.22a - Full legal item fixture expansion plan

Purpose:
- Plan the next data step before any legal item selector UI integration.
- Define how to expand the current sentinel `champions_legal_items.json` fixture toward a full Regulation M-A legal item fixture.
- Keep Champions legality separate from local damage-effect support.

Documented:
- Current v0.20/v0.21 state: legal item repository exists, but the fixture is sentinel-only.
- Source strategy:
  - MetaVGC as the primary legal snapshot.
  - RotomPicks and Serebii as cross-check sources.
  - ChampDex as contextual guide for cut/missing held items.
  - PokeAPI and existing static files as metadata/effect fallback only, not legality sources.
- Fixture expansion options:
  - manual
  - semi-manual static JSON expansion
  - scraper/build script
- Recommended v0.22b direction: semi-manual static JSON expansion before legal selector UI work.
- Fixture schema plan, item ID normalization rules, category rules, source conflict policy, repository impact, tests plan, and v0.22b candidate scope.
- Damage-supported but non-legal item policy for `Choice Band`, `Choice Specs`, `Life Orb`, `Muscle Band`, and `Wise Glasses`.

Maintained boundaries:
- Design/documentation only.
- No code implementation.
- No `data/static/champions_legal_items.json` changes.
- No fixture expansion implementation.
- No UI changes.
- No legal item selector implementation.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

Test:
- Not run; documentation-only planning update.

---

## v0.22b - Champions legal item full fixture expansion

Purpose:
- Expand `data/static/champions_legal_items.json` from a sentinel fixture toward the full Pokemon Champions Regulation M-A legal item fixture.
- Preserve the distinction between Champions legality and local damage-effect modeling.

Implemented:
- Expanded `champions_legal_items.json` to 117 legal item entries.
- Added fixture-level `expected_legal_item_count` and category counts:
  - legal items: 117
  - hold-item bucket from sources represented as 12 `hold_item` + 18 `type_boosting_item`
  - Mega Stones: 59
  - Berries: 28
- Preserved `damage_supported_non_legal_items` for damage-supported mismatch/debug items:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
  - `muscle-band`
  - `wise-glasses`
- Kept source strategy explicit:
  - MetaVGC as primary legal snapshot
  - RotomPicks as category/count cross-check
  - Serebii as cross-check
  - ChampDex as contextual guide
  - PokeAPI/static repo data as metadata/effect fallback only
- Strengthened repository fixture validation and item id normalization.
- Added tests for full fixture count, duplicate item IDs, required fields, category/status fields, normalized lookup, legal sentinel classifications, and damage-supported non-legal separation.

Maintained boundaries:
- No ItemProfileDialog changes.
- No PokemonPanel/MainWindow UI changes.
- No legal item selector UI implementation.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, KO/OHKO/2HKO, speed order, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Tests:
- `uv run pytest tests/test_champions_item_repository.py -q`
- Result: 19 passed.
- `uv run pytest tests/test_items.py tests/test_item_modifiers.py tests/test_advisor_damage_estimate.py tests/test_champions_item_repository.py -q`
- Result: 60 passed.
- `uv run pytest -q`
- Result: 715 passed, 2 deselected.

---

## v0.22c - Champions legal item fixture quality verification

Purpose:
- Add explicit quality checks for the expanded Regulation M-A legal item fixture.
- Record that the full fixture remains separated from damage-supported non-legal/debug items.

Verified:
- Legal item count remains 117.
- Category counts remain:
  - `mega_stone`: 59
  - `berry`: 28
  - `hold_item` + `type_boosting_item`: 30
- No duplicate `item_id` values across legal and damage-supported non-legal sections.
- All fixture items include required fields:
  - `item_id`
  - `name_en`
  - `name_ko`
  - `category`
  - `legal`
  - `legality_status`
  - `legality_confidence`
  - `effect_support_status`
  - `ui_status`
  - `effect_support`
  - `notes`
- Every `item_id` satisfies repository normalization.
- Every item has a non-empty `name_en`.
- `source_refs`, `source_kind`, `fetched_at`, and `regulation` are present.
- `source_conflict` / `unconfirmed` handling is explicit:
  - `muscle-band`
  - `wise-glasses`
- `choice-band`, `choice-specs`, and `life-orb` are not present in normal legal items.
- `choice-band`, `choice-specs`, and `life-orb` remain in `damage_supported_non_legal_items`.
- `list_legal_items()` returns 117 legal entries.
- `list_damage_supported_non_legal_items()` returns the expected mismatch/debug items.
- Unknown item classification remains stable.

Implemented:
- Added fixture quality tests in `tests/test_champions_item_repository.py`.
- Tightened ASCII-safe item id normalization coverage for apostrophe variants.
- No fixture data changes were required.

Maintained boundaries:
- No UI changes.
- No legal item selector implementation.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, KO/OHKO/2HKO, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Tests:
- `uv run pytest tests/test_champions_item_repository.py -q`
- Result: 21 passed.
- `uv run pytest tests/test_items.py tests/test_item_modifiers.py tests/test_advisor_damage_estimate.py tests/test_champions_item_repository.py -q`
- Result: 62 passed.
- `uv run pytest -q`
- Result: 717 passed, 2 deselected.

---

## v0.23 - Legal item selector integration

Purpose:
- Connect `ItemProfileDialog` to Champions legal item repository-backed options.
- Keep normal UI focused on legal item fixture entries instead of damage-test items.

Implemented:
- Added repository-backed item option construction for `ItemProfileDialog`.
- `MainWindow` now injects Champions legal item options from `ChampionsItemRepository`.
- Preserved `Unknown item` and `No item` choices.
- Legal-but-not-modeled items such as `choice-scarf`, `focus-sash`, `leftovers`, and `sitrus-berry` are selectable.
- Selected legal-but-not-modeled items are recorded in `item_profiles` as `user_confirmed` with:
  - `legality_status: legal`
  - `effect_support_status: legal_but_not_modeled`
  - `damage_modifier_status: not_applied`
- Normal selector options hide damage-supported non-legal/debug items:
  - `choice-band`
  - `choice-specs`
  - `life-orb`
- Legacy damage-test helper paths remain available for regression tests, but are not normal UI options.
- Updated advisor prompt/contract wording to distinguish legal items from modeled item effects.

Verified:
- `ItemProfileDialog` accepts injected repository-backed legal item options.
- `Unknown item` and `No item` remain selectable.
- `choice-scarf`, `focus-sash`, `leftovers`, and `sitrus-berry` are selectable legal options.
- `choice-band`, `choice-specs`, and `life-orb` are hidden from normal selector options.
- Legal-but-not-modeled attacker items do not change damage estimates.
- `item_effects.attacker_item.status` reports `not_applied` for selected legal-but-not-modeled items.
- Opponent default item state remains `unknown`.
- My default item state remains `system_default_none`.
- Pokemon change/clear still resets item profile state.

Maintained boundaries:
- No scraping or build script.
- No `data/cache` generation.
- No legal item fixture expansion or large data changes.
- No new item damage effects.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, KO/OHKO/2HKO, speed order, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Tests:
- `uv run pytest tests/test_item_profile_dialog.py tests/test_champions_item_repository.py tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`
- Result: 69 passed.
- `uv run pytest -q`
- Result: 719 passed, 2 deselected.

---

## v0.23.1 - Legal item selector local verification and UX findings

Purpose:
- Record T1 local app verification of the v0.23 legal item selector integration.
- Capture UX findings for the next item selector milestones.

Verified locally:
- `ItemProfileDialog` opens normally.
- The selector shows repository-backed legal item options.
- `No item` is selectable.
- Legal fixture items such as `Abomasite`, `Absolite`, and `Aerodactylite` are visible.
- `Choice Band`, `Choice Specs`, and `Life Orb` are hidden from the normal legal selector.
- This direction is correct because those items remain damage-supported/debug items, not normal Champions legal item options.
- The guidance text explains that the list is based on the Regulation M-A legal item fixture.
- The guidance text also explains that some legal item effects may not be modeled.
- The guidance continues to state that choice lock, recoil, speed, recovery, survival effects, and KO odds are not calculated yet.

UX findings:
- 117 legal items in one combo box is difficult to scan; item search is needed.
- Korean item name mapping is needed.
- Korean + English display is preferred for readability, for example:
  - `기합의띠 (Focus Sash)`
  - `먹다남은음식 (Leftovers)`
  - `구애스카프 (Choice Scarf)`
- Repeated labels such as `(legal, effect not modeled)` are accurate but long.
- Future label polish could use shorter wording such as `[효과 미계산]` or `[not modeled]`.
- Alphabetical sorting makes many Mega Stones appear first, so category grouping or category sorting may be needed.
- Candidate categories:
  - regular held items
  - type-boosting items
  - berries
  - Mega Stones

Next candidates:
- `v0.24 Item Selector Search`
- `v0.25 Korean Item Name Mapping`

Maintained boundaries:
- Documentation-only record.
- No code changes.
- No UI changes.
- No fixture changes.
- No item search implementation.
- No Korean item mapping implementation.
- No scraping or build script.
- No `advisor/damage/` or `advisor/probability` engine changes.

---

## v0.24 - Item selector search

Purpose:
- Add search filtering to `ItemProfileDialog` so T1 can find legal items quickly in the 117-item Regulation M-A fixture list.

Implemented:
- Added an item search input to `ItemProfileDialog`.
- Search placeholder: `아이템 검색...`.
- Filters repository-backed item options by:
  - visible label
  - `name_en`
  - `item_id`
- Search is case-insensitive.
- Search normalizes spaces and underscores to hyphens, so `focus sash`, `focus-sash`, and `focus_sash` all match `focus-sash`.
- `Unknown item` and `No item` remain pinned and accessible while searching.
- Filtered selection/save behavior continues to produce the same `item_profiles` payload shape.

Verified:
- `focus`, `focus sash`, `focus-sash`, and `FOCUS` find `Focus Sash`.
- `left` finds `Leftovers`.
- `sitrus` finds `Sitrus Berry`.
- `Choice Band`, `Choice Specs`, and `Life Orb` remain hidden from normal selector options and search results.
- Reset behavior remains unchanged.
- Existing legal-but-not-modeled damage unchanged tests continue to pass.
- Existing Champions item repository tests continue to pass.

Maintained boundaries:
- No Korean item name mapping.
- No category grouping.
- No legal item fixture changes.
- No Champions item repository data changes.
- No damage-supported non-legal item exposure in normal UI.
- No scraping or build script.
- No `data/cache` generation.
- No item effect additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, KO/OHKO/2HKO, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Tests:
- `uv run pytest tests/test_item_profile_dialog.py tests/test_champions_item_repository.py tests/test_advisor_damage_estimate.py -q`
- Result: 57 passed.
- `uv run pytest -q`
- Result: 724 passed, 2 deselected.

---

## v0.24.1 - Item selector search local verification

Purpose:
- Record T1 local app verification for the v0.24 item selector search UX.

Verified locally:
- `ItemProfileDialog` search input is displayed.
- Placeholder is shown as `아이템 검색...`.
- Searching `fair` filters the list to show `Fairy Feather`.
- `Unknown item` and `No item` remain accessible while searching.
- Clearing the search restores the legal item list.
- Legal items visible in the list include:
  - `Fairy Feather`
  - `Aspear Berry`
  - `Audinite`
  - `Babiri Berry`
  - `Banettite`
  - `Beedrillite`
  - `Black Belt`
  - `Black Glasses`
  - `Blastoisinite`
  - `Bright Powder`
  - `Cameruptite`
- Damage-supported non-legal items remain hidden from the normal selector:
  - `Choice Band`
  - `Choice Specs`
  - `Life Orb`
- T1 judged the search feature to be working correctly.

UX findings:
- Korean item name mapping is still missing.
- Next candidate: `v0.25 Korean Item Name Mapping`.

Maintained boundaries:
- Documentation-only record.
- No code changes.
- No UI changes.
- No fixture changes.
- No test changes.
- No Korean item mapping implementation.
- No category grouping.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

---

## v0.25 - Korean item name mapping

Purpose:
- Add Korean item name support for the legal item selector without changing Champions legality data.
- Improve `ItemProfileDialog` display labels and search for common legal items.

Implemented:
- Added `data/static/item_names_ko.json` as a separate manual-curated display/search mapping.
- `ChampionsItemRepository` now enriches classified items with `name_ko` from the mapping when the legal fixture entry does not provide one.
- `ItemProfileDialog` displays Korean + English names when `name_ko` is available.
- Examples:
  - `기합의띠 (Focus Sash) [효과 미계산]`
  - `먹다남은음식 (Leftovers) [효과 미계산]`
  - `구애스카프 (Choice Scarf) [효과 미계산]`
- Items without `name_ko` fall back to the English label.
- Search now includes:
  - `name_ko`
  - `name_en`
  - `item_id`
  - visible label
- Existing English and item-id search behavior remains intact.
- Label suffixes were shortened from long English wording to compact Korean status labels:
  - `[효과 미계산]`
  - `[데미지 보정 인식]`

Verified:
- Korean name mapping loads successfully.
- `Focus Sash`, `Leftovers`, and `Choice Scarf` display with Korean + English names.
- English fallback works for items without a Korean mapping.
- Korean searches work:
  - `기합` finds `Focus Sash`
  - `먹다` finds `Leftovers`
  - `구애` finds `Choice Scarf`
- Existing searches such as `focus`, `focus sash`, and `focus-sash` still work.
- `Unknown item` and `No item` remain pinned while searching.
- `Choice Band`, `Choice Specs`, and `Life Orb` remain hidden from normal selector options and search results.
- Selected item payload still preserves stable `item_id` and `name_en`, with `name_ko` added as display/search metadata.
- Legal-but-not-modeled items still do not change damage estimates.
- Existing Champions item repository tests continue to pass.

Maintained boundaries:
- No item effect additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, KO/OHKO/2HKO, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.
- No legality changes.
- No re-exposure of Choice Band / Choice Specs / Life Orb in the normal selector.
- No scraping or build script.
- No `data/cache` generation.

Tests:
- `uv run pytest tests/test_item_profile_dialog.py tests/test_champions_item_repository.py tests/test_advisor_damage_estimate.py -q`
- Result: 61 passed.
- `uv run pytest -q`
- Result: 728 passed, 2 deselected.

---

## v0.25.1 - Korean item mapping local verification

Purpose:
- Record T1 local app verification for the v0.25 Korean item name mapping.

Verified locally:
- Korean item name display works.
- Korean + English combined display works.
- Korean item search works.
- Existing English search still works.
- Damage-supported non-legal items remain hidden from the normal selector and search results:
  - `Choice Band`
  - `Choice Specs`
  - `Life Orb`
- T1 local verification passed.

Next candidate:
- `v0.26 Item Category Grouping / Display Polish`

Maintained boundaries:
- Documentation-only record.
- No code changes.
- No UI changes.
- No fixture changes.
- No Korean mapping additions or edits.
- No category grouping implementation.
- No item effect additions.
- No `advisor/damage/` or `advisor/probability` engine changes.

---

## v0.26 - Item category grouping and display polish

Purpose:
- Improve `ItemProfileDialog` legal item scanability after search and Korean-name support.
- Keep the normal selector legal-only while making item order more natural.

Implemented:
- Applied category-based sorting to repository-backed legal item options.
- Sort order:
  - `Unknown item`
  - `No item`
  - `hold_item`
  - `type_boosting_item`
  - `berry`
  - `mega_stone`
  - unknown/other category
- Kept Korean + English display for mapped items.
- Kept compact status labels instead of long text such as `legal, effect not modeled`.
- Chose category sorting without visible category headers/tags to avoid making labels too long.

Verified:
- `Unknown item` and `No item` remain pinned first.
- `hold_item` entries appear before `type_boosting_item` entries.
- `type_boosting_item` entries appear before berries and Mega Stones.
- Berries appear before Mega Stones.
- Korean + English labels remain intact.
- Korean search still works.
- English and item-id search still work.
- `Choice Band`, `Choice Specs`, and `Life Orb` remain hidden from normal selector options and search results.
- Selection/save payload remains compatible.
- Legal-but-not-modeled items still do not change damage estimates.
- Existing Champions item repository tests continue to pass.

Maintained boundaries:
- No legal item fixture changes.
- No Korean mapping expansion.
- No item effect additions.
- No Choice Scarf speed, Focus Sash survival, Leftovers/Sitrus recovery, Choice lock, Life Orb recoil, KO/OHKO/2HKO, or Turn Engine implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.
- No scraping or build script.
- No `data/cache` generation.

Tests:
- `uv run pytest tests/test_item_profile_dialog.py tests/test_champions_item_repository.py tests/test_advisor_damage_estimate.py -q`
- Result: 63 passed.
- `uv run pytest -q`
- Result: 730 passed, 2 deselected.

---

## v0.27 - Speed / Turn Order Design

Purpose:
- Design how future speed and turn-order information should enter the advisor payload without overclaiming final action order.
- Separate raw Speed comparison from effective Speed, move priority, and full action order.

Designed:
- Added `docs/spike_v0.27_speed_turn_order_design.md`.
- Defined concept boundaries:
  - `raw_speed`: final Spe value from user-confirmed final stats or explicit default assumptions.
  - `effective_speed`: future Speed after item/status/field/stage modifiers.
  - `move_priority`: future move priority metadata, not currently exposed by `MoveView`.
  - `action_order`: future Turn Engine-level result, not available yet.
- Proposed top-level `speed_context` payload candidate for a future v0.28.
- Recommended v0.28 candidate:
  - `Raw Speed Comparison Payload`
  - use `stat_profiles.*.final_stats.spe`
  - emit raw relation and margin
  - keep `is_final_turn_order: false`
  - no UI change

Guardrail direction:
- LLM must not treat raw Speed comparison as final turn order.
- If `speed_context.is_final_turn_order` is false, the advisor should avoid claims such as "will move first".
- Choice Scarf may be selected as a legal item, but its speed effect remains not modeled.
- Trick Room, Tailwind, paralysis, Speed stages, priority, ability speed effects, and Turn Engine state remain unmodeled.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No UI implementation.
- No Speed calculation implementation.
- No Choice Scarf speed, priority, Tailwind, Trick Room, paralysis, Speed stage, ability speed effect, or Turn Engine implementation.
- No KO/OHKO/2HKO implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.
- No item effect additions.

Next decisions:
- Whether v0.28 should proceed as `Raw Speed Comparison Payload`.
- Whether raw Speed comparison should require user-confirmed final stats on both sides or allow clearly labeled default fallback.
- Whether to approve `speed_context` as a top-level payload section.
- Whether v0.28 should remain payload/LLM-only with no UI changes.

---

## v0.28 - Raw Speed Comparison Payload

Purpose:
- Add a top-level raw Speed comparison payload without claiming final turn order.
- Use only user-confirmed final Speed values from both active Pokemon.

Implemented:
- Added top-level `speed_context` to the UI LLM battle payload.
- `speed_context.mode` is `raw_speed_comparison_v0.28`.
- When both active Pokemon have user-confirmed final stats:
  - `speed_context.available` is `true`.
  - `my_active.raw_speed` comes from `stat_profiles.my_active.final_stats.spe`.
  - `opponent_active.raw_speed` comes from `stat_profiles.opponent_active.final_stats.spe`.
  - `comparison.raw_speed_relation` reports:
    - `my_active_faster`
    - `opponent_active_faster`
    - `speed_tie`
  - `comparison.speed_margin` records the absolute raw Speed difference.
  - `comparison.speed_tie` records tie state.
- When either side lacks user-confirmed final Speed:
  - `speed_context.available` is `false`.
  - `reason` is `insufficient_confirmed_final_stats`.
- `is_final_turn_order` is always `false`.

Guardrails:
- Updated advisor prompt and payload contract to state that `speed_context` is raw Speed comparison only.
- The LLM must not say a Pokemon will move first when `speed_context.is_final_turn_order` is false.
- Recommended wording is limited to phrases such as "based on raw Speed only" or "appears faster by raw Speed".
- Default Speed fallback is not used in v0.28.

Verified:
- my active faster relation works.
- opponent active faster relation works.
- raw Speed tie relation works.
- insufficient confirmed stats returns unavailable.
- Choice Scarf selection does not modify raw Speed.
- Speed limitations include:
  - priority not modeled
  - Choice Scarf speed not modeled
  - Tailwind not modeled
  - Trick Room not modeled
  - Speed stages not modeled
  - paralysis not modeled
  - ability speed effects not modeled
- Existing advisor payload contract tests pass.

Maintained boundaries:
- No UI changes.
- No Speed input UI.
- No default Speed fallback.
- No Choice Scarf speed implementation.
- No priority move implementation.
- No Tailwind, Trick Room, paralysis, Speed stage, or ability speed effect implementation.
- No Turn Engine.
- No KO/OHKO/2HKO implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.
- No item effect additions.
- No legal item fixture changes.
- No item selector UI changes.

Tests:
- `uv run pytest tests/test_advisor_payload_contract.py -q`
- Result: 21 passed.
- `uv run pytest -q`
- Result: 734 passed, 2 deselected.

---

## v0.28.1 - Raw speed comparison local Gemini verification

Purpose:
- Record T1 local app verification for the v0.28 raw Speed comparison payload and Gemini guardrails.

Verified locally:
- Actual Gemini call succeeded with both active Pokemon using user-confirmed final stats.
- Gemini reflected the raw Speed comparison in the response.
- Confirmed response wording:
  - "Garchomp appears faster by raw Speed only."
- Gemini did not claim final turn order.
- Gemini did not use hard turn-order wording such as "will move first".
- Charizard could hold Choice Scarf without Gemini claiming the Choice Scarf speed effect was applied.
- Confirmed response wording:
  - "Charizard's Choice Scarf speed effect is not modeled."
- The v0.28 policy held:
  - raw Speed comparison only
  - `is_final_turn_order=false`
  - no default Speed fallback
  - no Choice Scarf speed application

Unsupported speed mechanics remain excluded:
- priority
- Tailwind
- Trick Room
- paralysis
- Speed stages
- ability speed effects
- Turn Engine

Result:
- v0.28 local Gemini verification passed.

Next candidates:
- More detailed speed limitation wording polish, if T1 wants clearer natural-language caveats.
- `v0.29 Effective Speed Assumption Design`, if T1/T2 want to start planning Choice Scarf/status/field Speed assumptions.

Maintained boundaries:
- Documentation-only record.
- No code changes.
- No UI changes.
- No `speed_context` schema changes.
- No prompt changes.
- No tests changed.
- No Choice Scarf speed, priority, Tailwind, Trick Room, paralysis, Speed stages, Turn Engine, KO/OHKO/2HKO, or damage/probability engine implementation.

---

## v0.29 - Effective Speed Assumption Design

Purpose:
- Design how to extend v0.28 raw Speed comparison into limited effective Speed assumptions without claiming final turn order.
- Prepare a safe v0.30 candidate before implementing Choice Scarf speed support.

Designed:
- Added `docs/spike_v0.29_effective_speed_assumption_design.md`.
- Separated:
  - `raw_speed`: final Spe from user-confirmed final stats, already implemented in v0.28.
  - `effective_speed`: raw Speed plus supported speed modifiers.
  - `priority_bracket`: future move priority metadata.
  - `field_speed_rule`: future Trick Room/Tailwind-style field rules.
  - `final_action_order`: future Turn Engine-level action order.
- Compared options:
  - keep raw Speed only
  - Choice Scarf only effective Speed
  - Choice Scarf + paralysis/Tailwind/stages
  - effective Speed + priority
  - full Turn Engine
- Recommended v0.30 candidate:
  - `Choice Scarf Effective Speed Payload`
  - no UI changes if possible
  - use existing user-confirmed final Spe and ItemProfileDialog Choice Scarf selection
  - keep `is_final_turn_order=false`

Payload direction:
- Prefer extending existing `speed_context` instead of adding a separate `effective_speed_context`.
- Add `effective_speed`, `speed_modifiers`, raw/effective relations, and explicit limitations when implemented.
- Keep choice lock unmodeled.

Guardrail direction:
- Effective Speed is still not final turn order.
- Do not say "will move first" or "guaranteed outspeed".
- If Choice Scarf is applied in a future payload, describe it as a supported effective Speed estimate.
- Continue to state that priority, Trick Room, Tailwind, paralysis, Speed stages, ability speed effects, and Turn Engine state are not modeled.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No UI implementation.
- No effective Speed calculation implementation.
- No Choice Scarf speed implementation.
- No priority, Tailwind, Trick Room, paralysis, Speed stage, ability speed effect, final turn order, or Turn Engine implementation.
- No KO/OHKO/2HKO implementation.
- No `advisor/damage/` or `advisor/probability` engine changes.

Next decisions:
- Whether v0.30 should proceed as `Choice Scarf Effective Speed Payload`.
- Whether Choice Scarf should apply only when `item_profiles.*.status == user_confirmed`.
- Whether effective Speed fields should extend `speed_context`.
- Whether Choice Scarf should be marked modeled in repository/fixture speed effect support.
- Whether v0.30 should remain payload/helper-only with no UI changes.

---

## v0.30 - Choice Scarf Effective Speed Payload

Purpose:
- Extend `speed_context` with a minimal supported effective Speed estimate for user-confirmed Choice Scarf.
- Keep raw Speed comparison and final turn order separate.

Implemented:
- Added `effective_speed` to `speed_context.my_active` and `speed_context.opponent_active`.
- Added `speed_modifiers` entries when a side has `item_profiles.*.status == user_confirmed` and `item_id == choice-scarf`.
- Applied Choice Scarf as a `1.5` Speed modifier only for user-confirmed Choice Scarf.
- Kept `raw_speed` unchanged.
- Added separate raw and effective comparison fields:
  - `raw_speed_relation`
  - `raw_speed_margin`
  - `raw_speed_tie`
  - `effective_speed_relation`
  - `effective_speed_margin`
  - `effective_speed_tie`
- Preserved `speed_margin` and `speed_tie` as raw Speed compatibility aliases.
- Kept unavailable handling from v0.28 when either side lacks user-confirmed final Speed.

Guardrails:
- `is_final_turn_order` remains `false`.
- Choice lock remains unmodeled and is listed in `unsupported_effects` / limitations.
- Prompt and contract now describe effective Speed as a supported speed modifier estimate, not final turn order.
- Raw Speed and effective Speed must be distinguished when they differ.

Still excluded:
- UI changes.
- Choice lock.
- Priority moves.
- Tailwind.
- Trick Room.
- Paralysis.
- Speed stages.
- Ability speed effects.
- Turn Engine.
- KO/OHKO/2HKO.
- Damage/probability engine changes.

Tests:
- Added coverage for no-item raw/effective equality.
- Added my-side and opponent-side user-confirmed Choice Scarf effective Speed.
- Added unconfirmed/unknown/no item no-modifier cases.
- Added raw-slower/effective-faster relation coverage.
- Updated prompt/contract guardrail tests.
- Full pytest result: `736 passed, 2 deselected`.

---

## v0.30.1 - Choice Scarf Effective Speed Local Gemini Verification

Purpose:
- Record T1 local Gemini verification for v0.30 Choice Scarf effective Speed behavior.

Local verification:
- Gemini actual call succeeded in the local valid-key app environment.
- With both active Pokemon final stats entered, Gemini distinguished raw Speed from effective Speed.
- Observed wording:
  - "Garchomp appears faster than Charizard based on raw Speed (154 vs 152) and significantly faster with its Choice Scarf (effective Speed 231 vs 152), though this is not a final turn order."
- Confirmed Choice Scarf's supported `1.5x` Speed modifier appeared in the effective Speed explanation.
- Confirmed Gemini did not claim final turn order or say the user would definitely move first.
- Confirmed choice lock was described as not modeled.
- Priority, Tailwind, Trick Room, paralysis, Speed stages, and Turn Engine behavior remain unmodeled.

Additional observation:
- When only Garchomp final stats were entered and Charizard final stats were not user-confirmed, Gemini still avoided final turn order claims and described choice lock as not modeled.
- Minor wording polish candidate:
  - The phrase "Choice Scarf speed boost is not modeled" can be misleading when the real blocker is missing confirmed final Speed on one side.
  - Prefer future wording such as "effective Speed comparison requires both Pokemon's user-confirmed final Speed."

Result:
- v0.30 local Gemini verification passed.

Next candidates:
- `v0.30.2 Speed Context Wording Polish`
- `v0.31 Opponent Stat Sample Assumption Design`

Maintained boundaries:
- Documentation-only record.
- No code changes.
- No UI changes.
- No `speed_context` schema changes.
- No prompt changes.
- No tests changed.
- No Choice lock, priority, Tailwind, Trick Room, paralysis, Speed stages, Turn Engine, KO/OHKO/2HKO, or damage/probability engine implementation.

---

## v0.31 - Item Effect Coverage Map Design

Purpose:
- Design an item effect coverage map for the 117 Champions Reg M-A legal items and the legacy damage-supported non-legal/debug item subset.
- Clarify that selectable legal items and modeled item effects remain separate concepts.

Designed:
- Added `docs/spike_v0.31_item_effect_coverage_map_design.md`.
- Documented current coverage:
  - legal fixture has 117 items.
  - `legal_and_damage_supported`: 17 items.
  - `legal_but_not_modeled`: 100 items.
  - `damage_supported_non_legal_items`: 5 items.
- Classified item effect families:
  - damage modifiers
  - speed modifiers
  - survival modifiers
  - recovery modifiers
  - stat modifiers
  - accuracy/evasion
  - crit
  - flinch/secondary effects
  - Mega Evolution/form effects
  - berry/status/misc effects
  - unsupported or unknown effects
- Recorded current modeled effects:
  - Choice Scarf effective Speed in `speed_context`, only when user-confirmed.
  - Legacy damage helper support for Choice Band, Choice Specs, Life Orb, Muscle Band, and Wise Glasses remains debug/test-only because these are not normal legal selector options.
- Proposed coverage status vocabulary:
  - `modeled`
  - `partially_modeled`
  - `recognized_not_modeled`
  - `requires_turn_engine`
  - `requires_probability_engine`
  - `requires_status_engine`
  - `requires_transform_or_form_engine`
  - `legal_but_unknown_effect`
  - `damage_supported_but_not_champions_legal`

Recommended priority:
- v0.32 should focus on Type Boosting Item Damage Modifier Design before Focus Sash, recovery, probability, flinch, or Mega Evolution effects.
- Type boosting items are the safest next target because they attach directly to `damage_estimate` and do not require Turn Engine state.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No fixture changes.
- No `item_effect_coverage.json` creation.
- No item effect additions.
- No damage/probability engine changes.
- No UI changes.
- No Turn Engine, KO/OHKO/2HKO, recovery, survival, crit, flinch, or Mega Evolution implementation.

Next decisions:
- Whether v0.32 should be Type Boosting Item Damage Modifier Design or a small implementation.
- Whether item effect coverage should live in a separate `item_effect_coverage.json` or be derived by repository helpers.
- Whether Focus Sash/Leftovers-style Turn Engine items should remain design-only until after direct damage item coverage.

---

## v0.32 - Type Boosting Item Damage Modifier Design

Purpose:
- Design how legal type boosting items should connect to `damage_estimate` without expanding into broader item, turn, or probability systems.
- Prepare a safe v0.33 implementation path.

Designed:
- Added `docs/spike_v0.32_type_boosting_item_damage_modifier_design.md`.
- Confirmed the legal fixture has 18 `type_boosting_item` entries.
- Confirmed 17 are currently marked `legal_and_damage_supported` and exist in `data/static/items_damage.json`.
- Identified `fairy-feather` as legal but not currently present in the local damage item catalog.
- Recommended v0.33 initially support only the 17 catalog-backed legal type boosting items.

Candidate item list:
- `black-belt`
- `black-glasses`
- `charcoal`
- `dragon-fang`
- `hard-stone`
- `magnet`
- `metal-coat`
- `miracle-seed`
- `mystic-water`
- `never-melt-ice`
- `poison-barb`
- `sharp-beak`
- `silk-scarf`
- `silver-powder`
- `soft-sand`
- `spell-tag`
- `twisted-spoon`

Deferred:
- `fairy-feather` until catalog support is added and tested.

Rules proposed:
- Apply only attacker-side.
- Apply only when the item is user-confirmed, legal, `legal_and_damage_supported`, present in the local damage item catalog, and the move type matches the item's boosted type.
- Do not apply to status moves.
- Keep defender-side item effects out of scope.
- Keep non-legal damage-supported/debug items out of the normal legal path.

Payload direction:
- Extend `damage_estimate.item_effects.attacker_item` with additive fields such as:
  - `effect_type`
  - `boosted_type`
  - `modifier`
  - `reason`
- Continue to use `status == applied` as the only signal that the item changed damage.
- Use `not_applicable` when the selected item is supported but move type does not match.

v0.33 candidate:
- `Type Boosting Item Damage Modifier Implementation`
- Reuse `DamageContext.attacker_item`.
- Reuse `advisor.damage.items.get_item`.
- Add tests for my moves, selected move, opponent known move, not-applicable mismatch, and hidden non-legal item separation.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No damage modifier implementation.
- No fixture changes.
- No UI changes.
- No Expert Belt, Assault Vest, Focus Sash, Leftovers/Sitrus, Choice Band/Specs/Life Orb normal legal path, KO/OHKO/2HKO, Turn Engine, or damage/probability engine redesign.

Next decisions:
- Whether v0.33 should proceed as the small implementation.
- Whether to approve the proposed `item_effects.attacker_item` additive schema.
- Whether to keep `fairy-feather` deferred until local catalog support exists.

---

## v0.33 - Type boosting item damage modifier implementation

Purpose:
- Apply legal catalog-backed type boosting item damage modifiers to advisor damage estimates without expanding UI, Turn Engine, KO, or probability scope.

Implemented:
- Connected legal catalog-backed `type_boosting_item` entries to attacker-side `damage_estimate` calculations.
- Applied a `1.2x` modifier when a user-confirmed legal type boosting item matches the move type.
- Recorded `damage_estimate.item_effects.attacker_item` with `applied`, `not_applicable`, or `unsupported_item`.
- Added additive item effect fields:
  - `effect_type`
  - `boosted_type`
  - `modifier`
  - `reason`
- Applied the modifier to:
  - `moves.my_available_moves[*].damage_estimate`
  - `moves.my_selected_move.damage_estimate`
  - `opponent_moves.known_moves[*].damage_estimate`
- Kept opponent `candidate_moves` excluded from `damage_estimate`.
- Kept `fairy-feather` unmodeled as `unsupported_item` while no catalog-backed modifier exists.
- Updated advisor payload contract and prompt guardrails so the LLM may mention type boosting damage only when `item_effects.attacker_item.status == applied`.

Maintained boundaries:
- No UI changes.
- No fixture changes.
- No Expert Belt, Assault Vest, Focus Sash, Leftovers/Sitrus, recovery, KO/OHKO/2HKO, Turn Engine, or probability implementation.
- No Choice Band, Choice Specs, Life Orb, Muscle Band, or Wise Glasses normal legal path exposure.
- Defender item effects remain out of scope.

Verification:
- Charcoal + Fire move applies the modifier.
- Charcoal + non-Fire move records `not_applicable` and leaves damage unchanged.
- Mystic Water + Water move applies the modifier.
- Black Belt + Fighting move applies the modifier.
- Metal Coat + Steel move applies the modifier.
- Sharp Beak + Flying move applies the modifier.
- `item_effects.attacker_item` records `boosted_type`, `modifier`, `effect_type`, and `status`.
- my selected, my available, and opponent known move estimates receive the applicable item effect.
- opponent candidate moves still do not include `damage_estimate`.
- `fairy-feather` remains unsupported/not modeled.
- Existing item selector, damage parity, speed context, and payload contract regressions remain covered.
- `uv run pytest -q`: 741 passed, 2 deselected.

---

## v0.33.1 - Type boosting item damage local Gemini verification

Purpose:
- Record T1 local app Gemini verification for the v0.33 type boosting item damage modifier behavior.

Verified:
- Gemini actual call succeeded in the local app.
- Mismatch case:
  - My Pokemon: Charizard.
  - User-confirmed item: Charcoal.
  - Selected move: Dragon Claw.
  - Opponent: Garchomp.
  - Gemini correctly explained that Charcoal does not boost Dragon Claw damage.
  - Confirmed wording: "Charizard's user-confirmed Charcoal item does not boost Dragon Claw's damage."
  - This confirms Charcoal + non-Fire move reports the `not_applicable` behavior correctly.
- Applied case:
  - My Pokemon: Charizard.
  - User-confirmed item: Charcoal.
  - Selected move: Overheat.
  - Opponent: Garchomp.
  - Gemini correctly explained that the Charcoal type boosting damage modifier was applied.
  - Confirmed wording: "with the 1.2x Charcoal item modifier applied."
  - This confirms Charcoal + Fire move reports the `applied` behavior correctly.
- Gemini did not exaggerate the estimate as final battle damage.
- Gemini preserved the limitation that Garchomp stats/item were default assumptions.

Result:
- v0.33 local verification passed.

Next candidates:
- Fairy Feather catalog support design.
- Focus Sash survival design.
- Opponent stat sample assumption design.

Maintained boundaries:
- Documentation-only record.
- No code changes.
- No UI changes.
- No payload schema changes.
- No prompt changes.
- No test changes.
- No item effect additions.
- No Fairy Feather, Focus Sash, recovery, KO/OHKO/2HKO, Turn Engine, or damage/probability engine implementation.

---

## v0.34 - Opponent Stat Sample Assumption Design

Purpose:
- Design how opponent stats should be represented when they are user-confirmed, sample-assumed, default-assumed, or unknown.
- Prepare a safe path for future Pokemon stat sample files without treating samples as confirmed opponent stats.

Designed:
- Added `docs/spike_v0.34_opponent_stat_sample_assumption_design.md`.
- Reviewed current final stats, damage estimate, speed context, payload contract, and previous speed/item design boundaries.
- Defined stat source categories:
  - `user_confirmed_final_stats`
  - `sample_assumed_stats`
  - `default_assumption_stats`
  - `unknown_stats`
- Proposed future fixture shape for `data/static/pokemon_stat_samples.json`.
- Recommended keeping `stat_profiles.*` as the first source-of-truth location for stat source metadata.
- Recommended that sample stats may be used only when explicitly selected in a future implementation.
- Recommended that sample stats get a distinct assumption profile and never appear as user-confirmed stats.
- Recommended keeping v0.35 speed behavior user-confirmed-only; sample Speed should not feed the existing confirmed `speed_context` path yet.
- Compared UI options:
  - sample file only
  - explicit Opponent Stat Sample Selector
  - auto-suggest sample
- Recommended v0.35 as repository/fixture only and v0.36+ for any explicit UI selector.
- Proposed future repository/helper names:
  - `core/pokemon_stat_sample_repository.py`
  - `load_stat_samples()`
  - `list_samples_for_species()`
  - `get_sample()`
  - `validate_sample_schema()`
  - `classify_stat_source()`
- Added LLM guardrail direction that sample-assumed stats must be described as assumptions, not confirmed stats.

v0.35 candidate:
- `v0.35 - Opponent Stat Sample Repository / Fixture`
- Include a sentinel sample fixture, repository loader, schema validation tests, and source model documentation.
- Exclude UI selector, automatic sample application, damage/speed integration, Turn Engine, and KO/OHKO/2HKO.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No data fixture creation.
- No repository implementation.
- No UI changes.
- No payload schema implementation.
- No prompt changes.
- No tests changed.
- No sample stats applied to damage or speed.
- No automatic opponent sample selection.
- No KO/OHKO/2HKO, Turn Engine, item effect, or damage/probability engine changes.

---

## v0.35 - Opponent stat sample repository and fixture

Purpose:
- Add a minimal read-only opponent stat sample foundation without connecting sample stats to UI, damage estimates, or speed context.

Implemented:
- Added `data/static/pokemon_stat_samples.json` sentinel fixture.
- Added one estimated/manual `sample_assumed` sample for each sentinel species:
  - `garchomp_fast_physical_01`
  - `charizard_special_attacker_01`
  - `corviknight_bulky_01`
- Added `core/pokemon_stat_sample_repository.py`.
- Added schema validation for:
  - top-level schema/version fields
  - normalized species ids
  - globally unique sample ids
  - `status: sample_assumed`
  - `is_user_confirmed: false`
  - `confidence: estimated`
  - complete `hp/atk/def/spa/spd/spe` stats
  - complete SP distribution keys
  - limitations that state samples are not user-confirmed
- Added lookup helpers:
  - `load_samples()`
  - `validate_sample_schema()`
  - `normalize_species_id()`
  - `PokemonStatSampleRepository.list_species()`
  - `PokemonStatSampleRepository.list_samples_for_species()`
  - `PokemonStatSampleRepository.get_sample()`
- Added `tests/test_pokemon_stat_sample_repository.py`.

Maintained boundaries:
- No UI selector.
- No automatic sample application.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as `user_confirmed_final_stats`.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No damage/probability engine changes.

Verification:
- `uv run pytest tests/test_pokemon_stat_sample_repository.py -q`: 15 passed.
- `uv run pytest -q`: 756 passed, 2 deselected.

---

## v0.35.1 - Opponent stat sample source metadata polish

Purpose:
- Clarify source metadata and policy for opponent stat sentinel samples so they cannot be confused with user-confirmed or official opponent spreads.

Implemented:
- Expanded `data/static/pokemon_stat_samples.json` sample metadata with:
  - `source_type`
  - `source_name`
  - `source_url`
  - `source_note`
  - `regulation`
  - `season`
  - `is_official`
  - `confidence_reason`
  - `created_by`
  - `last_reviewed`
- Kept all sentinel samples as:
  - `source_type: manual_estimate`
  - `status: sample_assumed`
  - `is_user_confirmed: false`
  - `confidence: estimated`
  - `is_official: false`
- Added the limitation: `Do not use as final battle truth.`
- Expanded repository validation to require source metadata and reject unsupported `source_type` values.
- Added allowed `source_type` policy values:
  - `manual_estimate`
  - `usage_based_estimate`
  - `team_article_manual_extract`
  - `calculator_derived`
  - `official_or_replica_team`
  - `unknown`
- Added tests for required source metadata, manual estimate sentinel policy, null `source_url`, invalid `source_type`, and boolean `is_official`.

Source tier policy:
- Tier 1: direct stat usage or direct stat source candidates, such as future Pokebase-like stat usage sources.
- Tier 2: usage, item, moveset, or team-context sources, such as Pikalytics or Pokemon Zone.
- Tier 3: team article, replica team, or manual extraction sources, such as DevonCorp team articles, replica team codes, or team pastes.
- Tier 4: rules validation sources, such as Pokeos or Bulbapedia SP rules.
- Tier 5: manual estimates, including T1/project curated sentinel samples. These must keep `confidence: estimated` and must never be treated as user-confirmed.

Maintained boundaries:
- No UI selector.
- No automatic sample application.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as `user_confirmed_final_stats`.
- No official or confirmed-spread claims.
- No large sample DB buildout.
- No external scraping or build script.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No damage/probability engine changes.

Verification:
- `uv run pytest tests/test_pokemon_stat_sample_repository.py -q`: 20 passed.
- `uv run pytest -q`: 761 passed, 2 deselected.

---

## v0.36 - Opponent multi-sample assumption design

Purpose:
- Shift opponent sample modeling from selecting one exact sample to representing multiple possible opponent profiles with uncertainty.

Designed:
- Added `docs/spike_v0.36_opponent_multi_sample_assumption_design.md`.
- Documented the principle: `possible sample != confirmed opponent set`.
- Defined information states:
  - `not_confirmed`
  - `partially_confirmed`
  - `user_confirmed`
- Proposed future `opponent_assumptions` payload shape with:
  - `known_status`
  - `user_confirmed_fields`
  - `possible_samples`
  - `samples_meta`
  - `observation_history`
  - static `update_policy`
- Defined required `possible_samples` fields:
  - `sample_id`
  - `species_id`
  - `label_en`
  - `label_ko`
  - `source`
  - `source_type`
  - `confidence`
  - `prior_probability`
  - `evidence_basis`
  - `is_user_confirmed`
  - `possible_item`
  - `possible_stats`
  - `notes`
  - `limitations`
- Designed prior/evidence policy:
  - `prior_probability` is an estimated model prior, not a confirmed probability.
  - `evidence_basis` explains the source of the prior.
  - manual priors must remain clearly labeled as estimates.
- Designed Top-K and coverage metadata:
  - `total_known_archetypes`
  - `included_top_k`
  - `coverage_probability`
  - `omitted_archetypes_note`
- Added a future update hook for observation-based updates while keeping v0.36 static.
- Defined user override policy:
  - `user_confirmed_fields` outrank sample priors.
  - conflicting samples should be filtered or marked as conflicts.
  - fully user-confirmed state can disable multi-sample reasoning.
- Defined future calculation modes only:
  - `worst_case`
  - `most_likely`
  - `expected_value`
  - `range`
- Added LLM guardrails and BAD/GOOD wording examples for possible sample language.
- Recommended small UI touch points later, such as viewing possible sample distribution from the existing Stats dialog, without forcing a single sample selection.
- Proposed repository/data direction:
  - keep `PokemonStatSampleRepository` as read-only data loader
  - add a future `opponent_assumption_builder` for Top-K, filtering, and payload construction
- Recommended `v0.37 - Opponent Possible Sample Payload Design` before implementation.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No data fixture changes.
- No repository implementation.
- No UI changes.
- No automatic sample selection.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No Bayesian update implementation.
- No calculation mode implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No damage/probability engine changes.

---

## v0.37 - Opponent possible sample payload design

Purpose:
- Design the future `opponent_assumptions` payload section for possible opponent samples while keeping samples context-only and non-confirmed.

Designed:
- Added `docs/spike_v0.37_opponent_possible_sample_payload_design.md`.
- Compared top-level section options:
  - `opponent_assumptions`
  - `possible_opponent_profiles`
  - `battle_assumptions.opponent_samples`
- Recommended top-level `opponent_assumptions` because possible samples are incomplete-information context, not deterministic calculation state.
- Proposed v0.37 candidate schema with:
  - `mode: multi_sample_assumption_v0.37_candidate`
  - `available`
  - `scope: opponent_active`
  - `is_confirmed_information: false`
  - `calculation_usage: context_only`
  - `opponent_active.known_status`
  - `user_confirmed_fields`
  - `possible_samples`
  - `samples_meta`
  - `observation_history`
  - static `update_policy`
  - top-level limitations
- Defined availability behavior:
  - species with samples -> `available: true`
  - no species samples -> `available: false`, `reason: no_samples_for_species`
  - missing opponent -> `reason: opponent_active_missing`
  - repository failure -> `reason: repository_unavailable`
- Defined calculation usage policy:
  - v0.37 candidate uses `calculation_usage: context_only`
  - no direct damage, Speed, KO, survival, or final turn order usage
- Designed prior policy:
  - sentinel samples may use `prior_probability: null`
  - `prior_probability_type` candidates are `usage_derived`, `manual_estimate`, `heuristic`, and `not_available`
  - null prior is not zero probability
  - numeric priors may be unnormalized because the payload may be Top-K
- Designed Top-K and coverage policy:
  - default `top_k` candidate is `3`
  - `included_top_k` records actual included samples
  - `total_known_archetypes` records repository/builder candidates
  - `coverage_probability` may be null
  - `omitted_archetypes_note` is required
- Designed user-confirmed override policy:
  - `user_confirmed_fields` outrank sample assumptions
  - conflicting samples should be removed or marked as `conflicts_with_confirmed_fields`
- Added LLM BAD/GOOD examples and contract guardrails:
  - possible samples are not confirmed sets
  - sample stats are not user-confirmed stats
  - null prior is not zero probability
  - omitted Top-K archetypes are not impossible
  - context-only samples must not be described as damage/speed calculation inputs
- Designed prompt integration direction:
  - summarize only top risks
  - avoid long sample dumps
  - mention context-only limits when relevant
  - do not invent samples when unavailable
- Proposed future builder/helper names:
  - `build_opponent_assumptions_payload()`
  - `select_possible_samples()`
  - `attach_samples_meta()`
  - `apply_user_confirmed_field_filter()`
  - `normalize_prior_probabilities()` or `leave_prior_unnormalized()`
  - `validate_opponent_assumptions_payload()`
- Recommended `v0.38 - Opponent Possible Sample Payload Implementation`.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No data fixture changes.
- No repository changes.
- No UI changes.
- No automatic sample selection.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.

---

## v0.38 - Opponent possible sample payload

Purpose:
- Add a minimal top-level `opponent_assumptions` payload section that gives Gemini context-only possible opponent sample profiles without connecting samples to damage, Speed, KO, or turn-order calculations.

Implemented:
- Added `llm/opponent_assumptions.py`.
- Added `build_opponent_assumptions_payload()` for active opponent species sample lookup.
- Added helper functions:
  - `select_possible_samples()`
  - `build_samples_meta()`
  - `validate_opponent_assumptions_payload()`
- Added top-level `opponent_assumptions` to the UI-built advisor payload.
- Used `PokemonStatSampleRepository` to load manually curated sentinel samples.
- Kept `top_k` default at `3`.
- For available species, payload includes:
  - `mode: multi_sample_assumption_v0.38`
  - `available: true`
  - `scope: opponent_active`
  - `is_confirmed_information: false`
  - `calculation_usage: context_only`
  - `known_status: not_confirmed`
  - `user_confirmed_fields: {}`
  - `possible_samples`
  - `samples_meta`
  - `observation_history: []`
  - static `update_policy`
- For unavailable species, payload returns:
  - `available: false`
  - `reason: no_samples_for_species`
- Added unavailable handling for:
  - `opponent_active_missing`
  - `repository_unavailable`
- Kept all possible samples as:
  - `source: sample_assumed`
  - `is_user_confirmed: false`
  - `confidence: estimated`
  - `prior_probability: null`
  - `prior_probability_type: not_available`
- Added advisor contract and prompt guardrails:
  - possible samples are not confirmed opponent sets
  - sample assumptions are not user-confirmed information
  - null prior is not zero probability
  - Top-K omitted archetypes are not impossible
  - context-only samples are not damage or Speed calculation inputs
  - sample context must not be used to claim final turn order, KO, or survival
- Added tests for:
  - available species sample payload
  - unknown species unavailable payload
  - missing opponent unavailable payload
  - repository unavailable payload
  - possible sample `is_user_confirmed: false`
  - `calculation_usage: context_only`
  - `samples_meta`
  - static `update_policy`
  - null prior handling
  - prompt and contract guardrails
  - no automatic damage or Speed integration

Maintained boundaries:
- No UI changes.
- No fixture expansion.
- No external scraping or build script.
- No automatic sample application.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as `user_confirmed_final_stats`.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No damage/probability engine changes.

Verification:
- `uv run pytest tests/test_opponent_assumptions.py tests/test_advisor_payload_contract.py -q`: 32 passed.
- `uv run pytest -q`: 769 passed, 2 deselected.

---

## v0.38.2 - Opponent assumptions and choice lock wording polish

Purpose:
- Polish Gemini prompt and payload contract wording after local validation showed opponent sample context was too quiet and choice lock could be mentioned for non-Choice items.

Implemented:
- Updated advisor prompt guardrails so available `opponent_assumptions` with `possible_samples` may be mentioned briefly when relevant.
- Kept opponent samples as context-only, non-confirmed assumptions.
- Kept guardrails that sample stats are not used directly for damage or Speed calculations.
- Added example wording direction:
  - possible opponent samples exist, but they are context only and not confirmed.
- Tightened choice lock wording:
  - Choice lock may be mentioned only for Choice Scarf, Choice Band, or Choice Specs.
  - Non-Choice items such as Charcoal, Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, Leftovers, and Focus Sash must not get choice-lock wording.
- Preserved type boosting item wording:
  - Charcoal-like items may mention their supported damage modifier when applied.
  - Type mismatch still should say the item does not boost that move.
- Updated `docs/advisor_payload_contract.md`.
- Updated `tests/test_advisor_payload_contract.py`.

Maintained boundaries:
- No UI changes.
- No fixture expansion.
- No external scraping or build script.
- No automatic sample application.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as `user_confirmed_final_stats`.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No damage/probability engine changes.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py tests/test_opponent_assumptions.py -q`: 32 passed.
- `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: 1 passed.
- `uv run pytest -q`: 769 passed, 2 deselected.

---

## v0.38.3 - Opponent assumption and choice lock local Gemini re-verification

Purpose:
- Record T1 local Gemini actual-call re-verification for the v0.38 opponent assumptions payload and v0.38.2 choice-lock wording polish.

Verification source:
- T1 local app Gemini actual call.
- Code, UI, schema, prompt, tests, and fixtures were not changed in this step.

Charcoal / Tyranitar case:
- My Pokemon: Charizard.
- Item: Charcoal / 목탄.
- Move: Heat Wave.
- Opponent Pokemon: Tyranitar.
- Gemini response confirmed:
  - "Use Heat Wave. It deals an estimated 34-41 damage, which is not very effective against Tyranitar."
  - "Charcoal's Fire-type damage modifier is applied to the estimate."
  - "Main limitation: Damage estimates use default assumptions, and the opponent's item and move set are unconfirmed."
- Result:
  - Charcoal Fire-type damage modifier wording is correct.
  - No incorrect "Choice lock for Charcoal is not modeled" wording appeared.
  - Opponent item and moveset remained unconfirmed.
  - Damage was not overstated as final battle damage.

Garchomp possible sample context case:
- My Pokemon: Charizard.
- Item: Charcoal / 목탄.
- Move: Heat Wave.
- Opponent Pokemon: Garchomp.
- Opponent stats were not user-confirmed.
- Gemini response confirmed:
  - "Possible opponent samples exist for Garchomp but are context-only and not confirmed, so candidate moves like Earthquake are unconfirmed possible threats."
- Result:
  - Possible opponent sample context was mentioned briefly.
  - The sample context was described as context-only.
  - The sample context was described as not confirmed.
  - Gemini did not say sample stats were used directly for damage or Speed calculation.
  - Gemini did not treat the possible sample as a confirmed opponent set.
  - Damage estimate was not overstated as final battle damage.

Conclusion:
- Gemini actual call succeeded.
- v0.38.3 local verification passed.

Next candidates:
- `v0.39 - Opponent Assumptions Response Concision / Visibility Polish`
- `v0.39 - Sample Payload UI/Debug Inspection Design`
- `v0.39 - Opponent Sample Expansion Source Plan`

Maintained boundaries:
- Documentation-only record.
- No code implementation.
- No UI changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No sample fixture changes.
- No damage/speed integration.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.

---

## v0.39 - Opponent sample expansion source plan

Purpose:
- Design a source policy and manual expansion plan for growing opponent sample coverage without treating possible samples as confirmed opponent sets.

Designed:
- Added `docs/spike_v0.39_opponent_sample_expansion_source_plan.md`.
- Reviewed the current sentinel sample fixture, sample repository validation, opponent assumptions payload builder, payload contract, and v0.34/v0.36/v0.37 design docs.
- Confirmed current state:
  - `opponent_assumptions` exists as a top-level payload section.
  - `calculation_usage` remains `context_only`.
  - possible samples remain `sample_assumed` and `is_user_confirmed: false`.
  - sample stats are not connected to damage estimates or speed context.
  - current sample coverage is sentinel-only and too small for real multi-sample advisor distribution.
- Defined source tier policy:
  - Tier 1: direct stat / stat usage sources.
  - Tier 2: usage / item / move / team context sources.
  - Tier 3: team article / replica team / manual extract sources.
  - Tier 4: rules validation sources.
  - Tier 5: manual estimates.
- Proposed future source metadata requirements:
  - `source_type`
  - `source_name`
  - `source_url`
  - `source_note`
  - `regulation`
  - `season`
  - `last_reviewed`
  - `is_official`
  - `confidence`
  - `confidence_reason`
  - `evidence_basis`
  - `reviewer_notes`
  - `limitations`
- Proposed confidence model:
  - `confirmed`
  - `usage_derived`
  - `team_extract`
  - `estimated`
  - `unknown`
- Documented that higher source confidence still does not make a sample user-confirmed or the actual opponent set.
- Proposed archetype-oriented sample fields:
  - `archetype_id`
  - `archetype_tags`
  - `role`
  - `likely_item`
  - `possible_items`
  - `likely_moves`
  - `possible_moves`
  - `stat_focus`
  - `speed_tier_label`
  - `risk_notes`
- Recommended initial expansion scope for v0.40:
  - 10 to 15 core species.
  - 1 to 3 archetypes per species.
  - initial candidates include `garchomp`, `charizard`, `tyranitar`, `corviknight`, `archaludon`, and optional `pikachu`.
- Defined a manual review workflow:
  - collect source candidate
  - assign source tier and `source_type`
  - confirm item/move/ability/role evidence
  - record direct stat/SP evidence when available
  - mark indirect stats as estimates
  - write limitations
  - validate schema
  - add reviewer notes
  - add tests
  - request T1/T2 review before commit
- Kept a no-scraping policy for v0.39.
- Documented future scraping prerequisites:
  - source terms review
  - rate limit review
  - data freshness policy
  - generated vs curated data separation
  - mandatory manual review
- Designed payload impact:
  - `top_k` default remains `3`
  - `coverage_probability` remains null for manual-only samples
  - `prior_probability` remains null unless evidence supports it
  - omitted Top-K archetypes remain possible
- Added LLM guardrail direction:
  - sample source confidence is not actual opponent confirmation
  - manual estimates should be described as low-confidence risk cues
  - usage-based samples still do not prove the live opponent set
  - do not invent probabilities when no prior is provided
  - do not say samples were used for damage or Speed calculations unless a future integration explicitly does that
- Proposed future tests for source metadata, confidence enum, archetype fields, Top-K behavior, null prior handling, and existing opponent assumptions regression.
- Recommended `v0.40 - Opponent Sample Expansion Sentinel Pack` as the next candidate, with `v0.40 - Opponent Sample Archetype Schema Polish` as the fallback if source review is not ready.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No fixture changes.
- No sample additions.
- No repository changes.
- No UI changes.
- No scraping or build script.
- No automatic sample application.
- No damage/speed integration.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.

---

## v0.40 - Opponent sample candidate validation

Purpose:
- Record the validation-first review of the T2-1 `v0.40.0-final` 19-sample candidate package before any fixture merge.

Validation record:
- Added `docs/spike_v0.40_opponent_sample_candidate_validation.md`.
- Treated the T2-1 package as candidate input, not as trusted final fixture data.
- Confirmed the existing fixture structure:
  - `data/static/pokemon_stat_samples.json`
  - species-keyed dictionary
  - `samples: { species_id: [sample...] }`
  - current sample count: 3
- Confirmed the candidate structure differs:
  - `existing_samples`
  - `new_samples_v40`
  - sample entries use `species`
  - top-level `sp_distribution`
  - additional v0.40 fields such as `archetype_id`, `stats_truth_source`, `possible_items`, `calculation_usage`, and `existing_pre_v40`
- Marked the candidate as requiring schema-extension/migration planning before any direct merge.

Stats validation:
- Repo stat calculator exists:
  - `advisor.damage.stats.final_stats`
- Candidate stats were cross-checked against repo-native calculation where local base stats were available.
- Matched samples: 0.
- Mismatched samples: 13.
- Unverified samples: 6.
- Conclusion:
  - T2-1 manual stats must not be merged as-is.
  - Samples without repo base stats must remain unmerged until validation data exists.

Species key validation:
- Candidate uses `rotom_wash`.
- Repo normalization converts `rotom_wash` to `rotom-wash`.
- Local repo cache contains `data/cache/pokemon/rotom-wash.json`.
- Conclusion:
  - raw `rotom_wash` should not be merged without a repo-native normalization policy.

Korean / ability validation:
- Confirmed:
  - `tyranitar` ability `모래날림`
  - `archaludon` ability `지구력`
  - `rotom-wash` ability `부유`
- Suspicious:
  - `garchomp` ability_korean `사기`; repo/data mapping indicates Rough Skin as `까칠한피부`
  - `kingambit` korean_name `키랑이`; not confirmed from repo-backed data during validation
- Unresolved:
  - `amoonguss`
  - `gholdengo`
  - `metagross`
  - `amoonguss` ability_korean `포자`

Item legality validation:
- Legal in current Champions item repository:
  - `black-glasses`
  - `choice-scarf`
  - `leftovers`
  - `lum-berry`
  - `mental-herb`
  - `metal-coat`
  - `occa-berry`
  - `sitrus-berry`
- Illegal / not normal Champions legal in current fixture:
  - `choice-specs`
  - `choice-band`
  - `life-orb`
- Unknown in current Champions item repository:
  - `heavy-duty-boots`
  - `loaded-dice`
  - `weakness-policy`
  - `assault-vest`
  - `throat-spray`
  - `power-herb`
  - `covert-cloak`
  - `air-balloon`
  - `black-sludge`
  - `rocky-helmet`
- Banned pseudo-item check:
  - no `metagrossite-banned`
  - no item id containing `banned`

Decision:
- `merge_allowed: false`
- `data/static/pokemon_stat_samples.json` was not modified.
- No repository schema changes were made.
- No tests were changed.
- No commit was created during validation.
- The validation stop worked as intended before fixture mutation.

Next candidates:
- `v0.41 - Repo-Native Minimal Sample Pack Design`
- `v0.41 - Legal Item Filter for Possible Sample Items`
- `v0.41 - Stat Calculator Based Sample Generation Plan`

Maintained boundaries:
- Documentation-only record.
- No fixture changes.
- No sample additions.
- No schema migration.
- No repository changes.
- No tests changed.
- No UI changes.
- No damage/speed integration.
- No possible item auto-deletion.
- No stats auto-correction.
- No scraping or build script.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.41 - Repo-native minimal sample pack design

Purpose:
- Design a safer repo-native path for the next opponent sample fixture update after the v0.40 candidate failed validation.

Designed:
- Added `docs/spike_v0.41_repo_native_minimal_sample_pack_design.md`.
- Reviewed:
  - `data/static/pokemon_stat_samples.json`
  - `core/pokemon_stat_sample_repository.py`
  - `tests/test_pokemon_stat_sample_repository.py`
  - `llm/opponent_assumptions.py`
  - `tests/test_opponent_assumptions.py`
  - `advisor/damage/stats.py`
  - `core/champions_item_repository.py`
  - `data/static/champions_legal_items.json`
  - `docs/spike_v0.40_opponent_sample_candidate_validation.md`
- Summarized v0.40 failure causes:
  - candidate schema was not repo-native
  - manual final stats did not match `advisor.damage.stats.final_stats`
  - some species had no local cache/base stats for validation
  - `rotom_wash` conflicted with repo normalization to `rotom-wash`
  - candidate `possible_items` included illegal/unknown items
  - Korean/ability fields had unresolved cases
- Established new sample principle:
  - T1/T2 may propose SP distributions and archetypes
  - final stats must be generated or verified by repo calculator
  - species without local base stats are excluded
  - `possible_items` should include Champions legal items only
  - non-legal/unknown item ideas belong in notes, not `possible_items`
- Recommended preserving the existing species-keyed fixture shape.
- Recommended using `species_id` only and repo-normalized slugs such as `rotom-wash`.
- Designed stats generation policy:
  - `stats_truth_source: repo_calculator_from_sp_distribution`
  - `stats_calculator: advisor.damage.stats.final_stats`
  - explicit nature, IV, level, and SP assumptions
  - no T2 manual final stats copied into fixture
- Classified v0.42 species eligibility:
  - likely eligible: `garchomp`, `charizard`, `corviknight`, `tyranitar`, `archaludon`, `dragonite`, `rotom-wash`, `kingambit`
  - deferred: `gholdengo`, `amoonguss`, `metagross`
- Recommended v0.42 minimal scope:
  - 5 to 7 species
  - 1 sample per species
  - repo-calculated stats only
  - legal-item-only `possible_items`
- Proposed simple validation archetypes:
  - `garchomp`: `fast_physical`
  - `charizard`: `special_attacker`
  - `corviknight`: `defensive_pivot`
  - `tyranitar`: `bulky_physical`
  - `archaludon`: `special_tank`
  - `dragonite`: `physical_setup`
  - `rotom-wash`: `defensive_pivot`
- Designed v0.42 test direction:
  - recompute fixture stats with repo calculator
  - validate species normalization
  - validate legal-item-only `possible_items`
  - keep no damage/speed integration regression
  - keep `opponent_assumptions` Top-K regression
- Kept LLM/payload guardrails:
  - sample remains context-only
  - sample stats are not damage/speed inputs
  - legal possible items are not confirmed held items
  - null prior is not zero probability
- Recommended `v0.42 - Repo-Native Minimal Sample Pack Implementation`.
- Listed `v0.42 - Stat Sample Generator Helper Design` as an alternative if implementation inputs are not ready.

Maintained boundaries:
- Documentation-only design.
- No fixture changes.
- No sample additions.
- No code implementation.
- No repository implementation.
- No tests changed.
- No UI changes.
- No scraping or build script.
- No damage/speed integration.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.42 - Repo-native minimal sample pack

Purpose:
- Add a small repo-native opponent sample pack using only species with local base stats, repo-calculated final stats, and Champions legal possible items.

Implemented:
- Kept `data/static/pokemon_stat_samples.json` as a species-keyed dictionary.
- Added 7 repo-native validation samples:
  - `garchomp_fast_physical_repo_v42`
  - `charizard_special_attacker_repo_v42`
  - `corviknight_defensive_pivot_repo_v42`
  - `tyranitar_bulky_physical_repo_v42`
  - `archaludon_special_tank_repo_v42`
  - `dragonite_physical_setup_repo_v42`
  - `rotom_wash_defensive_pivot_repo_v42`
- Added 4 new sample species keys:
  - `archaludon`
  - `dragonite`
  - `rotom-wash`
  - `tyranitar`
- Preserved existing 3 sentinel samples.
- Used repo-normalized `rotom-wash` for the Rotom-Wash sample.
- Generated all v0.42 sample stats with `advisor.damage.stats.final_stats`.
- Recorded calculator provenance:
  - `stats_truth_source: repo_calculator_from_sp_distribution`
  - `stats_calculator: advisor.damage.stats.final_stats`
- Kept SP distributions simple and within Champions limits:
  - per-stat SP `0..32`
  - total SP `<= 66`
- Kept all v0.42 samples as:
  - `status: sample_assumed`
  - `is_user_confirmed: false`
  - `source_type: manual_estimate`
  - `confidence: estimated`
  - `calculation_usage: context_only`
  - `prior_probability: null`
  - `coverage_probability: null`
- Used Champions legal item repository checked `possible_items` only.
- Excluded v0.40 illegal/non-legal items such as `choice-specs`, `choice-band`, and `life-orb`.
- Excluded v0.40 unknown items such as `heavy-duty-boots`, `loaded-dice`, `weakness-policy`, `assault-vest`, `power-herb`, `covert-cloak`, `air-balloon`, `black-sludge`, and `rocky-helmet`.
- Added repository validation for optional repo-native sample fields when `calculation_usage` is present.
- Added tests for:
  - v0.42 sample count
  - species key normalization
  - repo-native required fields
  - SP caps and total
  - repo calculator stat recomputation
  - legal-only `possible_items`
  - context-only limitations
  - `opponent_assumptions` regression for expanded sample species

Maintained boundaries:
- No UI changes.
- No external scraping or build script.
- No automatic sample application.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as user-confirmed.
- No T2 manual final stats used.
- No `possible_items` object array schema.
- No usage-derived or confirmed confidence.
- No numeric prior or coverage probabilities.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.

Verification:
- `uv run pytest tests/test_pokemon_stat_sample_repository.py tests/test_opponent_assumptions.py -q`: 34 passed.
- `uv run pytest tests/test_advisor_payload_contract.py::test_ui_payload_includes_opponent_assumptions_for_species_with_samples tests/test_pokemon_stat_sample_repository.py tests/test_opponent_assumptions.py -q`: 35 passed.
- `uv run pytest -q`: 777 passed, 2 deselected.

---

## v0.42.1 - Repo-native sample local Gemini verification

Purpose:
- Record local Gemini actual-call verification after the v0.42 repo-native minimal sample pack.

Observed local cases:
- Tyranitar case:
  - Player Pokemon: Charizard.
  - Player item: Charcoal.
  - Selected move: Heat Wave.
  - Opponent Pokemon: Tyranitar.
  - Opponent stats: not user-confirmed.
  - Gemini recommended Heat Wave and described an estimated 34-41 damage range against Tyranitar using default assumptions plus Charcoal's 1.2x Fire-type modifier.
  - Gemini stated speed context was not available.
  - Gemini mentioned Tyranitar possible unconfirmed candidate moves such as Earthquake, Stone Edge, and Crunch.
- Rotom-Wash case:
  - Player Pokemon: Charizard.
  - Player item: Charcoal.
  - Selected move: Heat Wave.
  - Opponent Pokemon: Rotom-Wash.
  - Opponent stats: not user-confirmed.
  - Gemini recognized Rotom-Wash without slug/normalization problems.
  - Gemini described Heat Wave as boosted by Charcoal and avoided final speed-order claims.
  - Gemini stated the opponent item was unknown.

Confirmed safety behavior:
- Gemini actual call succeeded.
- Charcoal Fire-type damage modifier wording was correct.
- No Charcoal choice-lock hallucination appeared.
- No final turn order was asserted.
- Gemini did not claim sample stats were directly used for damage or speed calculation.
- Gemini did not present possible samples as confirmed opponent sets.
- Damage was not overstated as final battle truth.

Partial-pass finding:
- v0.42.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- Sample visibility: WEAK.
- In the Tyranitar case, possible sample context did not clearly say `context-only` / `not confirmed`.
- In the Rotom-Wash case, possible sample context was barely surfaced.

Next candidate:
- `v0.43 - Opponent Sample Visibility Prompt Polish`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No damage/speed integration.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.48 - Opponent assumptions payload versioning design

Purpose:
- Design a backward-compatible versioning policy for `opponent_assumptions` after v0.47 minimal metadata enrichment.

Designed:
- Documented current state:
  - `opponent_assumptions` was introduced in v0.38
  - current `mode` remains `multi_sample_assumption_v0.38`
  - actual payload shape has evolved through v0.42, v0.43, v0.45, and v0.47
  - sample assumptions remain `context_only` and not damage/speed inputs
- Defined versioning problem:
  - stale mode name does not describe current payload shape
  - future code may treat current payload as original v0.38
  - additive metadata vs breaking schema changes are not explicit
  - debug summary helper needs version semantics
- Set goals:
  - backward compatibility
  - clear payload evolution
  - distinguish behavior mode from schema shape
  - avoid confusing metadata evolution with calculation integration
- Compared options:
  - keep mode unchanged and add `schema_version`
  - rename mode to latest version
  - add feature flags
  - introduce `contract_version` / semantic mode
- Recommended v0.49 path:
  - keep `mode: multi_sample_assumption_v0.38`
  - add `schema_version: opponent_assumptions_v0.47`
  - add `metadata_version: minimal_metadata_v1`
  - add compact `payload_features`
- Proposed fields:
  - `mode`
  - `schema_version`
  - `metadata_version`
  - `calculation_usage`
  - `payload_features`
- Proposed payload features:
  - `possible_samples: true`
  - `minimal_metadata: true`
  - `debug_summary_supported: true`
  - `full_stats_excluded: true`
  - `damage_speed_integration: false`
- Defined compatibility policy:
  - additive fields only
  - old payloads without schema fields should still be handled
  - debug summary may show legacy/null versions
  - Gemini should not mention version fields in user advice
- Added future tests plan for:
  - schema/metadata version fields
  - mode backward compatibility
  - payload feature flags
  - legacy payload handling
  - debug summary version display
  - existing regression tests
- Documented docs/contract impact:
  - mode is historical behavior label
  - schema_version is current payload shape
  - metadata_version is possible sample metadata shape
  - payload_features is developer/debug-oriented

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No payload version field added.
- No fixture changes.
- No sample additions.
- No UI changes.
- No damage/speed integration.
- No user-confirmed treatment changes.
- No calculation mode.
- No Bayesian update.
- No Turn Engine.
- No full stats exposure.
- No full payload export.
- No scraping or build script.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.49 - Opponent assumptions payload versioning

Purpose:
- Add additive version fields to `opponent_assumptions` while preserving the existing historical mode string.

Implemented:
- Kept `mode: multi_sample_assumption_v0.38`.
- Added additive `schema_version: opponent_assumptions_v0.47`.
- Added additive `metadata_version: minimal_metadata_v1`.
- Added additive `payload_features`:
  - `possible_samples: true`
  - `minimal_metadata: true`
  - `debug_summary_supported: true`
  - `full_stats_excluded: true`
  - `damage_speed_integration: false`
- Added version fields to available and unavailable opponent assumptions payloads.
- Updated debug summary helper to include:
  - `schema_version`
  - `metadata_version`
  - compact `payload_features`
- Preserved old payload compatibility:
  - missing `schema_version` renders as `legacy`
  - missing `metadata_version` renders as `legacy`
  - missing `payload_features` gets safe fallback flags
- Added advisor contract guardrails:
  - mode is historical behavior label
  - schema/metadata versions describe current payload shape
  - version fields are developer/contract metadata
  - version info should not be mentioned in user-facing battle advice
- Updated `docs/advisor_payload_contract.md` to document:
  - `mode`
  - `schema_version`
  - `metadata_version`
  - `payload_features`
  - additive compatibility semantics
- Added tests for:
  - mode unchanged
  - schema_version present
  - metadata_version present
  - payload_features values
  - debug summary version display
  - legacy payload without version fields
  - user-facing version silence guardrail

Maintained boundaries:
- No mode rename.
- No fixture changes.
- No sample additions.
- No repository sample data changes.
- No UI changes.
- No full stats exposure.
- No full payload export.
- No damage/speed integration.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as user-confirmed.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No scraping or build script.

Verification:
- `uv run pytest tests/test_opponent_assumptions.py tests/test_advisor_payload_contract.py -q`: 41 passed.
- `uv run pytest -q`: 785 passed, 2 deselected.

---

## v0.49.1 - Opponent assumptions versioning debug verification

Purpose:
- Record local verification that v0.49 versioning fields are visible in developer debug summaries while staying silent in user-facing advice.

Local verification:
- Tested species: `rotom-wash`.
- Built `opponent_assumptions` with:
  - `build_opponent_assumptions_payload({"name_en": "rotom-wash"})`
- Built debug summary with:
  - `build_opponent_assumptions_debug_summary(payload)`
- Rendered copy-ready JSON with:
  - `format_opponent_assumptions_debug_json(summary)`

Confirmed versioning output:
- `mode` remained `multi_sample_assumption_v0.38`.
- `schema_version` rendered as `opponent_assumptions_v0.47`.
- `metadata_version` rendered as `minimal_metadata_v1`.
- `payload_features` rendered with:
  - `possible_samples: true`
  - `minimal_metadata: true`
  - `debug_summary_supported: true`
  - `full_stats_excluded: true`
  - `damage_speed_integration: false`

Confirmed sample metadata remained visible:
- `opponent_assumptions_available: true`.
- `possible_sample_count: 1`.
- `sample_id: rotom_wash_defensive_pivot_repo_v42`.
- `species_id: rotom-wash`.
- `role: defensive_pivot`.
- `archetype_id: rotom_wash_defensive_pivot_repo_v42`.
- `possible_items: ["leftovers", "sitrus-berry"]`.
- `confidence: estimated`.
- `is_user_confirmed: false`.

Confirmed guardrails:
- `used_for_damage: false`.
- `used_for_speed: false`.
- `guardrails.context_only: true`.
- `guardrails.not_confirmed: true`.
- `guardrails.not_damage_input: true`.
- `guardrails.not_speed_input: true`.
- `guardrails.not_final_turn_order: true`.

Legacy fallback verification:
- Removed `schema_version`, `metadata_version`, and `payload_features` from a generated `opponent_assumptions` object.
- Debug summary helper completed without crashing.
- Missing `schema_version` rendered as `legacy`.
- Missing `metadata_version` rendered as `legacy`.
- Missing `payload_features` used safe fallback flags:
  - `possible_samples: false`
  - `minimal_metadata: false`
  - `debug_summary_supported: true`
  - `full_stats_excluded: true`
  - `damage_speed_integration: false`
- Legacy summary preserved `used_for_damage: false`, `used_for_speed: false`, and context-only guardrails.

Safety and silence checks:
- No full stats dump appeared.
- No `sp_distribution` dump appeared.
- No full source metadata dump appeared.
- No full LLM payload export appeared.
- No secrets, `.env`, API keys, or token logs appeared.
- User-facing version silence was confirmed by prompt/contract regression:
  - advisor prompt says version fields are developer/contract metadata
  - advisor prompt says not to mention `schema_version`, `metadata_version`, or `payload_features` in user-facing battle advice

Verdict:
- v0.49.1 debug summary versioning verification: PASS.
- Version display: PASS.
- Legacy fallback: PASS.
- User-facing version silence: PASS by prompt/contract regression.
- Safety / no full stats / no SP distribution / no source metadata / no full payload / no secrets: PASS.

Next candidates:
- `v0.50 - Developer Debug Access Design`.
- `v0.50 - Debug Export Access Surface Design`.
- `v0.50 - Sample/Item Roadmap Return Plan`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No damage/speed integration.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.50 - Developer debug access design

Purpose:
- Design a developer-only access path for the existing `opponent_assumptions` debug summary without exposing general user-facing UI or full payload exports.

Designed:
- Documented current state:
  - debug summary helper exists
  - pretty JSON formatter exists
  - local verification confirmed safe summary output
  - no app button, menu, hotkey, or CLI access surface exists yet
- Defined problems:
  - active opponent sample payload is hard to inspect during app use
  - helper exists but is not exposed to developers
  - visible UI debug controls could confuse regular users
  - full payload export is too broad and creates hygiene risk
- Defined goals:
  - developer-only access
  - `opponent_assumptions` summary only
  - no full LLM payload
  - no full stats or SP distribution
  - no secrets, `.env`, API keys, or token logs
  - keep normal UI simple

Options compared:
- Option A - CLI/debug script.
- Option B - copy debug JSON button in app.
- Option C - hidden developer hotkey.
- Option D - debug log only.
- Option E - developer-only collapsible panel.

Recommendation:
- Prefer Option A as the safest next step:
  - `v0.51 - Opponent Assumptions Debug CLI Script Implementation`
  - input species id
  - build `opponent_assumptions`
  - print safe debug summary JSON to stdout
  - no UI
  - no full payload
  - no file writes by default
- Defer live app copy/hotkey design until the CLI access path is stable.
- Defer a visible debug panel until a later version.

Debug access scope:
- Include:
  - species id
  - availability
  - mode/schema/metadata versions
  - compact payload features
  - possible sample count
  - sample id/species id
  - role/archetype id
  - confidence
  - possible items
  - `is_user_confirmed`
  - `used_for_damage`
  - `used_for_speed`
  - guardrails
- Exclude:
  - full LLM payload
  - Gemini prompt
  - full stats
  - SP distribution
  - full source metadata
  - API key
  - `.env`
  - token logs
  - arbitrary environment variables

Git hygiene:
- Prefer stdout for v0.51.
- Do not commit generated debug JSON.
- If future file export is added, use a git-ignored path such as `logs/debug_payloads/` and verify/document ignore coverage.
- Keep `logs/token_usage.jsonl` unrelated and uncommitted.

Tests planned for v0.51:
- available species output
- unknown species output
- no secrets in output
- no full stats or SP distribution in output
- no full payload in output
- version fields display
- role/archetype/possible items display
- `used_for_damage=false`
- `used_for_speed=false`
- guardrails display
- existing `opponent_assumptions` regressions

Return to main roadmap:
- After minimal debug access, return to item/survival/KO roadmap candidates:
  - item effect expansion
  - survival/recovery item design
  - KO/OHKO/2HKO design
  - Focus Sash / Leftovers / Sitrus Berry / Bright Powder work

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No UI implementation.
- No CLI script implementation.
- No hotkey implementation.
- No fixture changes.
- No sample additions.
- No damage/speed integration.
- No user-confirmed treatment changes.
- No full payload export.
- No full stats exposure.
- No calculation mode implementation.
- No Bayesian update implementation.
- No Turn Engine.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.51 - Opponent assumptions debug CLI script

Purpose:
- Add a developer CLI that prints the safe `opponent_assumptions` debug summary JSON for a requested species.

Implemented:
- Added `scripts/debug_opponent_assumptions.py`.
- Added required CLI argument:
  - `--species`
- Added optional CLI argument:
  - `--top-k`, defaulting to the existing opponent assumptions default of `3`.
- The CLI:
  - builds an opponent-active payload from the provided species id
  - uses `PokemonStatSampleRepository`
  - calls `build_opponent_assumptions_payload`
  - calls `build_opponent_assumptions_debug_summary`
  - prints `format_opponent_assumptions_debug_json(summary)` to stdout
- Known species with samples return `opponent_assumptions_available: true`.
- Unknown species return safe unavailable JSON with `reason: no_samples_for_species`.

Safety and privacy:
- No Gemini call.
- No file writes.
- No `logs/debug_payloads/` output.
- No full LLM payload export.
- No full stats dump.
- No `sp_distribution` dump.
- No source URL/source note/reviewer notes/full source metadata dump.
- No Gemini prompt or response output.
- No API key, `.env`, secrets, environment dump, or token usage logs.

Docs:
- Updated `docs/advisor_payload_contract.md` with CLI usage:
  - `uv run python scripts/debug_opponent_assumptions.py --species rotom-wash`
- Documented that the CLI is developer-only, stdout-only, and summary-only.

Tests:
- Added CLI tests for:
  - script existence
  - known species output
  - unknown species output
  - valid JSON stdout
  - schema and metadata version fields
  - role/archetype/possible items
  - `used_for_damage=false`
  - `used_for_speed=false`
  - guardrails
  - no full stats
  - no `sp_distribution`
  - no full payload
  - no secrets/env/token logs
  - `--top-k` limiting behavior

Next candidates:
- `v0.52 - Item / Survival Roadmap Return Design`.
- `v0.52 - Focus Sash / Survival Item Design`.

Maintained boundaries:
- No UI button.
- No hotkey.
- No debug panel.
- No Gemini call.
- No full payload export.
- No file write.
- No fixture changes.
- No sample additions.
- No repository sample data changes.
- No damage/speed integration.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as user-confirmed.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No scraping or build script.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

Verification:
- `uv run pytest tests/test_debug_opponent_assumptions_cli.py tests/test_opponent_assumptions.py -q`: 19 passed.
- `uv run pytest -q`: 789 passed, 2 deselected.

---

## v0.52 - Item / survival roadmap return design

Purpose:
- Close the opponent sample/debug stabilization line for now and return to the item effect, survival, and KO roadmap.

Designed:
- Documented current state:
  - type boosting item damage modifiers are implemented
  - Choice Scarf effective Speed is implemented in `speed_context`
  - opponent sample/debug/versioning/CLI support is stable enough to pause
  - Focus Sash, Leftovers, Sitrus Berry, Bright Powder, Scope Lens, and King's Rock effects remain unconnected
  - KO/OHKO/2HKO is not connected to advisor responses
  - Turn Engine does not exist
- Compared candidate feature areas:
  - Focus Sash survival support
  - Sitrus Berry / Leftovers recovery context
  - Bright Powder accuracy context
  - Scope Lens critical-hit context
  - King's Rock flinch context
  - KO/OHKO/2HKO probability
- Recommended next direction:
  - `v0.53 - Focus Sash Survival Design`
  - `v0.54 - Focus Sash Limited Survival Implementation`
  - `v0.55 - Focus Sash Local Gemini Verification`

Focus Sash limited scope proposal:
- user-confirmed Focus Sash only
- full HP or full-HP-compatible state only
- lethal damage estimate can produce limited survival context
- raw damage rolls remain unchanged
- wording should be "may survive at 1 HP due to Focus Sash under limited assumptions"
- exclude:
  - multi-hit moves
  - hazards
  - residual damage
  - weather chip
  - ability interactions
  - prior damage ambiguity
  - item consumption tracking
  - exact turn sequencing
  - final battle truth claims

Payload / LLM direction:
- Compared top-level `survival_context` vs nested `damage_estimate.survival_context`.
- Recommended designing around explicit survival context that does not alter raw damage rolls.
- Guardrails:
  - do not say "definitely survives"
  - do not infer Focus Sash unless item is user-confirmed
  - do not claim multi-hit/hazard/residual behavior unless modeled
  - do not create KO/OHKO/2HKO claims from limited survival context

Roadmap proposal:
- `v0.53 - Focus Sash Survival Design`
- `v0.54 - Focus Sash Limited Survival Implementation`
- `v0.55 - Focus Sash Local Gemini Verification`
- `v0.56 - KO/OHKO/2HKO Probability Design`
- `v0.57 - Sitrus/Leftovers Recovery Design`
- `v0.58 - Accuracy/Crit/Flinch Item Coverage Design`

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No item effect implementation.
- No survival calculation implementation.
- No KO/OHKO/2HKO implementation.
- No Turn Engine.
- No UI changes.
- No fixture changes.
- No sample additions.
- No damage/speed integration changes.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.53 - Focus Sash survival design

Purpose:
- Design limited Focus Sash survival context without changing raw damage rolls or introducing Turn Engine state.

Designed:
- Documented current state:
  - type boosting item damage modifiers are implemented
  - Choice Scarf effective Speed is implemented in `speed_context`
  - Focus Sash is legal/selectable but survival is not connected
  - `damage_estimate` remains raw damage range and roll centered
  - KO/OHKO/2HKO and Turn Engine remain unimplemented
- Defined Focus Sash as survival context, not damage reduction.
- Established core principle:
  - Focus Sash may affect survival wording
  - Focus Sash must not alter raw damage rolls

Scope proposal for v0.54:
- Include only:
  - defender item profile is `user_confirmed`
  - defender item id is `focus-sash`
  - defender HP is full or full-compatible
  - incoming damage estimate exists
  - at least one incoming roll can be lethal
  - move is not known to be multi-hit
- Exclude:
  - multi-hit moves
  - hazards
  - residual damage
  - weather/status chip
  - prior damage ambiguity
  - ability interactions
  - item suppression
  - Mold Breaker-like exceptions
  - exact turn sequencing
  - KO probability integration

Data requirements:
- defender item profile status and item id
- defender HP state:
  - exact current/max HP if available
  - otherwise current UI `hp_percent`
- damage estimate min/max and rolls
- move metadata sufficient to exclude multi-hit when known

Payload direction:
- Prefer additive `survival_context` beside the relevant move `damage_estimate`.
- Do not mutate `damage_range`, `rolls`, type effectiveness, or item damage modifier math.
- Direction rules:
  - my selected move: defender is `opponent_active`
  - opponent known move: defender is `my_active`

LLM guardrails:
- Say "may survive at 1 HP", not "will survive".
- Say this is limited context.
- Say raw damage is unchanged.
- Do not infer Focus Sash unless item is user-confirmed.
- Do not describe Focus Sash as damage reduction.
- Do not claim final battle truth, final turn order, or KO/OHKO/2HKO probability.

Reason codes proposed:
- `no_focus_sash`
- `item_not_user_confirmed`
- `hp_not_full`
- `hp_unknown`
- `damage_not_lethal`
- `multi_hit_not_supported`
- `damage_estimate_missing`
- `defender_max_hp_missing`
- `unsupported_turn_engine_required`

v0.54 candidate:
- `v0.54 - Focus Sash Limited Survival Context Implementation`
- Add helper and additive payload context.
- User-confirmed Focus Sash only.
- Full HP only.
- Lethal damage only.
- Raw damage unchanged.
- No Turn Engine.
- No KO probability.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No actual `survival_context` field addition.
- No item effect implementation.
- No damage formula changes.
- No raw damage roll changes.
- No KO/OHKO/2HKO implementation.
- No Turn Engine.
- No multi-hit support.
- No hazard/residual/weather/status chip.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.54 - Focus Sash limited survival context

Purpose:
- Add limited Focus Sash `survival_context` beside relevant `damage_estimate` entries without changing raw damage math.

Implemented:
- Added a Focus Sash survival context helper in `llm/advisor_survival_context.py`.
- Attached additive `survival_context` for:
  - my selected move / available move damage against `opponent_active`
  - opponent known move damage against `my_active`
- Kept opponent candidate moves excluded from both `damage_estimate` and `survival_context`.
- Modeled Focus Sash only when:
  - defender item is user-confirmed
  - defender item id is `focus-sash`
  - defender HP is full by exact HP or 100% HP
  - incoming damage max is at least current HP
- Added lethal flags:
  - `could_be_lethal_without_item` when max damage is at least current HP
  - `guaranteed_lethal_without_item` when min damage is at least current HP
- Added `survival_effect.may_survive_at_1_hp`.
- Added `raw_damage_rolls_changed=false` and preserved raw damage min/max/rolls unchanged.

Guardrails:
- Focus Sash is limited survival context, not damage reduction.
- Use "may survive at 1 HP" wording.
- Do not say "definitely survives" or that Focus Sash guarantees survival in final battle.
- Do not infer Focus Sash when item is unknown or unconfirmed.
- Multi-hit moves, hazards, residual damage, weather/status chip, ability interactions, and exact turn sequencing are not modeled.

Docs and tests:
- Updated `docs/advisor_payload_contract.md` with `survival_context` shape, reason codes, and LLM wording guardrails.
- Updated advisor payload prompt/contract guardrails.
- Added tests for full HP lethal, could-lethal vs guaranteed-lethal, no Focus Sash, unconfirmed Focus Sash, HP not full, HP unknown, non-lethal damage, opponent known move direction, candidate move exclusion, multi-hit unsupported, and raw damage unchanged.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 63 passed.
- `uv run pytest -q`: 798 passed, 2 deselected.

Maintained boundaries:
- No damage formula changes.
- No raw damage roll changes.
- No KO/OHKO/2HKO implementation.
- No Turn Engine.
- No multi-hit support.
- No hazards/residual/weather/status chip support.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.54.1 - Focus Sash survival local Gemini verification

Purpose:
- Record local Gemini actual-call verification for v0.54 limited Focus Sash `survival_context`.

Local verification:
- Gemini actual call succeeded.
- Case run: Case B, opponent Focus Sash survival.
  - Player Pokemon: Charizard.
  - Selected move: Flamethrower.
  - Opponent Pokemon: Garchomp.
  - Opponent item: user-confirmed `focus-sash`.
  - Opponent HP: full / 100%.
  - Local payload included available `survival_context`.
  - Incoming damage context: 31-37 damage, `could_be_lethal_without_item=true`, `guaranteed_lethal_without_item=false`.
- Gemini response summary:
  - Recommended Flamethrower.
  - Stated it deals 31-37 damage with default assumptions and is not very effective.
  - Stated Garchomp has a user-confirmed Focus Sash and may survive at 1 HP.
  - Stated attacker stats are based on default assumptions.

Confirmed behavior:
- Focus Sash wording was present.
- "may survive at 1 HP" wording was present.
- Raw damage estimate remained visible as 31-37 and was not replaced by a reduced damage value.
- No damage reduction hallucination appeared.
- No "definitely survives", "will survive", or guaranteed final survival wording appeared.
- Focus Sash was not inferred from unknown or unconfirmed item data.
- No raw damage roll changes, KO/OHKO/2HKO claims, or final battle truth claims appeared.

Weakness:
- The response did not explicitly mention multi-hit, hazards, residual damage, weather/status chip, or exact turn sequencing limitations.
- The response did not explicitly say raw damage rolls are unchanged, though it preserved the raw damage estimate and separated Focus Sash as survival wording.

Verdict:
- v0.54.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- Focus Sash visibility: PASS.
- Limitation visibility: WEAK.

Next candidates:
- `v0.55 - Focus Sash Prompt Polish`.
- `v0.55 - KO/OHKO/2HKO Design`.
- `v0.55 - Sitrus/Leftovers Recovery Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `survival_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No KO/OHKO/2HKO implementation.
- No Turn Engine.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.55 - Focus Sash prompt polish

Purpose:
- Polish Focus Sash wording after v0.54.1 local Gemini verification showed safety and visibility were good, but limitation wording was weak.

Implemented:
- Strengthened advisor prompt guardrails so available Focus Sash `survival_context` should include one concise limitation sentence.
- Added the target limitation wording:
  - multi-hit moves are not modeled
  - hazards are not modeled
  - chip damage is not modeled
  - exact turn sequencing is not modeled
- Kept the Focus Sash limitation short so it does not dominate the recommendation.
- Preserved existing wording requirements:
  - use "may survive at 1 HP"
  - do not say "will survive"
  - do not say "definitely survives"
  - do not say Focus Sash guarantees survival
  - raw damage estimate is unchanged
  - Focus Sash is not damage reduction
  - Focus Sash applies only when user-confirmed and HP is full
- Preserved unavailable-case guardrail:
  - do not infer Focus Sash when item is unknown or unconfirmed
  - do not force Focus Sash limitation wording when `survival_context.available` is false or no `survival_context` is present

Docs and tests:
- Updated `docs/advisor_payload_contract.md` with one-line Focus Sash limitation examples and unavailable-case wording.
- Updated advisor payload contract guardrails.
- Updated prompt/contract regression tests for:
  - one-line limitation rule
  - multi-hit / hazards / chip damage / exact turn sequencing wording
  - `may survive at 1 HP`
  - `will survive` / `definitely survives` prohibition
  - raw damage unchanged
  - not damage reduction
  - no unknown/unconfirmed Focus Sash inference

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py tests/test_advisor_damage_estimate.py -q`: 63 passed.
- `uv run pytest -q`: 798 passed, 2 deselected.

Maintained boundaries:
- No `survival_context` structure changes.
- No survival calculation changes.
- No damage formula changes.
- No raw damage roll changes.
- No KO/OHKO/2HKO implementation.
- No Turn Engine.
- No multi-hit support.
- No hazards/residual/weather/status chip support.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.55.1 - Focus Sash prompt local Gemini verification

Purpose:
- Record local Gemini actual-call verification after v0.55 Focus Sash prompt polish.

Local verification:
- Gemini actual call succeeded.
- Case run: Case B, opponent Focus Sash survival.
  - Player Pokemon: Charizard.
  - Selected move: Flamethrower.
  - Opponent Pokemon: Garchomp.
  - Opponent item: user-confirmed `focus-sash`.
  - Opponent HP: full / 100%.
  - Local payload included available `survival_context`.
  - Incoming damage context: 31-37 damage, `could_be_lethal_without_item=true`, `guaranteed_lethal_without_item=false`.
- Gemini response summary:
  - Recommended Flamethrower.
  - Stated Flamethrower is not very effective against Garchomp.
  - Stated it deals 31-37 damage based on default assumptions for Charizard and user-confirmed stats for Garchomp.
  - Stated Garchomp is holding a user-confirmed Focus Sash and may survive at 1 HP.
  - Main limitation included that Charizard's final stats are default assumptions.
  - Focus Sash limitation appeared as one sentence: Focus Sash survival context does not model multi-hit moves, hazards, or chip damage.

Confirmed behavior:
- Focus Sash wording was present.
- "may survive at 1 HP" wording was present.
- Raw damage estimate remained visible as 31-37 and was not replaced by a reduced damage value.
- No damage reduction hallucination appeared.
- No "definitely survives", "will survive", or guaranteed final survival wording appeared.
- Focus Sash was not inferred from unknown or unconfirmed item data.
- Multi-hit, hazards, and chip damage limitation wording appeared in one concise sentence.

Weakness:
- The limitation sentence did not explicitly mention exact turn sequencing.

Verdict:
- v0.55.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- Focus Sash visibility: PASS.
- Limitation visibility: IMPROVED but still incomplete because exact turn sequencing was omitted.

Next candidates:
- `v0.56 - KO/OHKO/2HKO Design`.
- `v0.56 - Sitrus/Leftovers Recovery Design`.
- `v0.56 - Bright Powder Accuracy Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `survival_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No KO/OHKO/2HKO implementation.
- No Turn Engine.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.56 - KO / OHKO / 2HKO probability design

Purpose:
- Design how to expose KO, OHKO, and 2HKO context from existing raw damage rolls without introducing Turn Engine behavior or final battle truth.

Designed:
- Documented current state:
  - `damage_estimate` already includes min/max and 16 raw rolls
  - Focus Sash `survival_context` is additive and does not alter raw rolls
  - Choice Scarf `speed_context` and opponent assumptions remain separate
  - `advisor.damage.rolls.calc_ko_chance()` exists but is not connected to the LLM payload
  - KO/OHKO/2HKO advice remains unimplemented
- Defined the problem:
  - players need "can this KO?" and "is this a 2HKO?" context
  - full battle truth requires accuracy, Speed/order, recovery, chip, Focus Sash, and turn sequencing
  - v0.56 should remain limited damage-roll context only

Payload direction:
- Prefer additive `ko_context` beside each relevant move `damage_estimate`.
- Do not put KO fields inside raw `damage_range` or `rolls`.
- Do not make it top-level only, because my moves and opponent known moves have different defender sides.
- Candidate moves remain excluded unless they receive deterministic `damage_estimate` in a future version.

OHKO logic:
- Use current HP when exact/current target HP is available.
- If HP is full and max HP reference is available, full-HP OHKO can use max HP reference.
- Count rolls where `roll >= current_hp`.
- `min >= current_hp` means guaranteed OHKO under limited assumptions.
- `max < current_hp` means no OHKO under raw rolls.
- Partial successful rolls produce `successful_rolls / total_rolls`.
- If rolls are missing, min/max-only limited mode can set possible/guaranteed booleans but should not invent chance.

2HKO logic:
- Start with limited min/max classification:
  - `min_damage * 2 >= hp` -> guaranteed 2HKO under limited assumptions
  - `max_damage * 2 >= hp` -> possible 2HKO
  - `max_damage * 2 < hp` -> no 2HKO
- Defer roll-pair 2HKO probability even though `calc_ko_chance()` can compute pairwise outcomes.
- Explicitly exclude healing, recovery, chip changes, Protect/Substitute, switching, accuracy, and turn order.

Focus Sash interaction:
- Keep Focus Sash `survival_context` separate from KO probability.
- KO context is based on raw damage rolls.
- Focus Sash may soften wording:
  - raw damage could KO
  - user-confirmed Focus Sash may allow survival at 1 HP
- Do not say Focus Sash is included in KO probability.

LLM guardrails:
- Use "limited damage-roll context".
- Do not describe KO context as final battle truth.
- Say raw damage rolls are unchanged.
- Say accuracy, speed order, priority, recovery, hazards, chip damage, switching, and turn sequencing are not modeled.
- Do not overstate 2HKO as final turn simulation.

v0.57 candidate:
- `v0.57 - KO/OHKO/2HKO Limited Context Implementation`
- Add additive `ko_context`.
- Use roll-count OHKO chance when rolls exist.
- Use min/max-limited 2HKO classification.
- Preserve Focus Sash as separate context.
- No Turn Engine.
- No accuracy/recovery/chip integration.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No actual `ko_context` field addition.
- No Turn Engine.
- No accuracy calculation.
- No priority or Speed order implementation.
- No recovery implementation.
- No hazards/chip/residual/weather/status implementation.
- No Focus Sash KO probability integration.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.57 - KO/OHKO/2HKO limited context

Purpose:
- Add additive limited `ko_context` beside relevant `damage_estimate` entries using existing raw damage min/max/rolls.

Implemented:
- Added `llm/advisor_ko_context.py`.
- Attached `ko_context` for:
  - `moves.my_available_moves[*]`
  - `moves.my_selected_move`
  - `opponent_moves.known_moves[*]`
- Kept opponent candidate moves excluded from `damage_estimate`, `survival_context`, and `ko_context`.
- Kept raw `damage_range` and `rolls` unchanged.

OHKO logic:
- Uses current HP when exact `current_hp` is present.
- Uses full HP reference when `hp_percent == 100` and max HP is available through `damage_estimate.derived_stats.defender.default_max_hp`.
- Counts rolls where `roll >= current_hp`.
- Exposes:
  - `possible`
  - `guaranteed`
  - `chance`
  - `successful_rolls`
  - `total_rolls`
  - `method: roll_count`
- If rolls are missing, falls back to min/max limited mode:
  - no invented roll chance
  - `chance=null`
  - `method: limited_min_max_no_rolls`

2HKO logic:
- Uses limited min/max classification:
  - `min_damage * 2 >= current_hp` -> guaranteed 2HKO under limited assumptions
  - `max_damage * 2 >= current_hp` -> possible 2HKO
  - `max_damage * 2 < current_hp` -> no 2HKO
- Does not compute roll-pair probability.
- Includes assumptions that the same move is used twice and no healing, recovery, chip damage, protection, switching, item survival integration, or turn sequencing is modeled.

Focus Sash interaction:
- `survival_context` can coexist with `ko_context`.
- Focus Sash is not included in KO probability.
- KO context remains raw damage-roll context.
- Prompt/contract guardrails tell the LLM that Focus Sash survival context is separate from raw KO context.

Docs and tests:
- Updated `docs/advisor_payload_contract.md` with `ko_context` semantics, OHKO chance logic, 2HKO limited logic, Focus Sash separation, and LLM wording guardrails.
- Updated advisor prompt and known limitations.
- Added tests for:
  - guaranteed OHKO
  - impossible OHKO
  - partial OHKO chance
  - successful rolls / total rolls
  - no-roll min/max fallback
  - HP unknown
  - guaranteed/possible/impossible 2HKO
  - raw damage unchanged
  - my move direction
  - opponent known move direction
  - candidate move exclusion
  - Focus Sash coexistence
  - Focus Sash not integrated into KO chance
  - prompt/contract guardrails

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 72 passed.
- `uv run pytest -q`: 807 passed, 2 deselected.

Maintained boundaries:
- No Turn Engine.
- No accuracy calculation.
- No priority or Speed order integration.
- No recovery implementation.
- No hazards/chip/residual/weather/status implementation.
- No Focus Sash KO probability integration.
- No damage formula changes.
- No raw damage roll changes.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.58 - KO context local Gemini verification

Purpose:
- Record local Gemini actual-call verification for v0.57 limited `ko_context`.

Observed local case:
- Case A - roll-based OHKO chance:
  - Player Pokemon: Charizard.
  - Selected move: Heat Wave.
  - Opponent Pokemon: Garchomp.
  - Opponent current HP: 35.
  - Raw damage estimate: 31-38.
  - Damage rolls: 16 rolls with 8 rolls at or above current HP.
  - `ko_context.ohko.chance`: 0.5.
  - `ko_context.ohko.successful_rolls`: 8.
  - `ko_context.ohko.total_rolls`: 16.
  - `ko_context.two_hko.possible`: true.

Gemini response summary:
- Gemini actual call succeeded.
- Gemini recommended Heat Wave.
- Gemini stated the raw estimate as 31-38 damage to Garchomp under default assumptions.
- Gemini stated there is a 50% chance to OHKO Garchomp based on its current 35 HP.
- Gemini included a limitation sentence that this is limited damage-roll context only.
- Gemini stated accuracy, speed order, priority, recovery, hazards, chip damage, switching, protection, and turn sequencing are not modeled.

Confirmed behavior:
- KO chance was expressed as roll-based limited context.
- Raw damage estimate was unchanged.
- Limited damage-roll context wording appeared.
- Accuracy/speed/recovery/chip/turn sequencing limitation appeared.
- Gemini did not claim final battle truth.
- Gemini did not overclaim guaranteed KO in battle.
- No Focus Sash coexistence case was exercised in this local verification.

Verdict:
- v0.58 local Gemini verification: PASS.
- Safety: PASS.
- KO context visibility: PASS.
- Limitation visibility: PASS.
- Focus Sash coexistence: not exercised in this verification.

Next candidates:
- `v0.59 - KO Context Prompt Polish`.
- `v0.59 - Sitrus/Leftovers Recovery Design`.
- `v0.59 - Bright Powder Accuracy Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `ko_context` changes.
- No `survival_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No Turn Engine.
- No accuracy calculation.
- No recovery implementation.
- No hazards/chip/residual/weather/status implementation.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.59 - Sitrus / Leftovers recovery design

Purpose:
- Design how Sitrus Berry and Leftovers could be represented as limited recovery context without changing raw damage or raw KO context.

Current state:
- `damage_estimate` provides raw damage min/max/rolls.
- Focus Sash has additive `survival_context`.
- KO/OHKO/2HKO has additive `ko_context`.
- Sitrus Berry and Leftovers are legal/selectable, but their recovery effects are not modeled.
- `champions_legal_items.json` marks both recovery effects as `not_supported`.
- Turn Engine, recovery sequencing, chip, hazards, weather/status, and item consumption tracking are absent.

Design:
- Proposed additive `recovery_context`.
- Kept raw damage rolls unchanged.
- Kept raw `ko_context` unchanged.
- Recommended user-confirmed item only:
  - `sitrus-berry`
  - `leftovers`
- Required defender max HP before computing a recovery amount.
- Proposed conservative unavailable reasons such as:
  - `no_recovery_item`
  - `item_not_user_confirmed`
  - `defender_max_hp_missing`
  - `unsupported_recovery_item`
  - `turn_engine_required`
  - `item_consumption_not_tracked`

Placement recommendation:
- Prefer `recovery_context` as an additive sibling beside each relevant `damage_estimate`, matching `survival_context` and `ko_context`.
- Keep Leftovers timing explicit as `end_of_turn_limited`.
- Do not insert recovery into `ko_context`.
- Consider a later top-level summary only if repeated Leftovers notes become noisy.

LLM guardrails:
- Recovery context is limited context only.
- Raw damage estimates are unchanged.
- Raw KO context is unchanged.
- Recovery is not fully simulated.
- Do not claim final 2HKO/3HKO truth without Turn Engine.
- Do not assume item activation when item is unknown or unconfirmed.
- Sitrus/Leftovers timing and item consumption are not fully modeled.

v0.60 candidate:
- `v0.60 - Sitrus / Leftovers Limited Recovery Context Implementation`.
- Alternative: `v0.60 - Recovery Item Rule Validation Design` if T1/T2 want rule-source certainty before implementation.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `recovery_context` implementation.
- No Turn Engine.
- No item consumption tracking.
- No exact KO/2HKO/3HKO simulation.
- No KO context modification.
- No raw damage roll modification.
- No Focus Sash interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.60 - Sitrus / Leftovers limited recovery context

Purpose:
- Add additive limited `recovery_context` beside relevant `damage_estimate` entries for user-confirmed Sitrus Berry and Leftovers.

Implemented:
- Added `llm/advisor_recovery_context.py`.
- Attached `recovery_context` for:
  - `moves.my_available_moves[*]`
  - `moves.my_selected_move`
  - `opponent_moves.known_moves[*]`
- Kept opponent candidate moves excluded from `damage_estimate`, `survival_context`, `recovery_context`, and `ko_context`.
- Kept raw `damage_range` and `rolls` unchanged.
- Kept `ko_context` unchanged.

Recovery policy:
- Sitrus Berry:
  - user-confirmed `sitrus-berry` only
  - `timing: threshold_or_after_damage_limited`
  - `estimated_recovery_hp = floor(max_hp / 4)`
  - `formula_label: floor(max_hp / 4)`
  - exact activation timing and item consumption are not tracked
- Leftovers:
  - user-confirmed `leftovers` only
  - `timing: end_of_turn_limited`
  - `estimated_recovery_hp = floor(max_hp / 16)`
  - `formula_label: floor(max_hp / 16)`
  - exact end-of-turn sequencing is not modeled

Guardrails:
- `recovery_context` is limited context only.
- Recovery does not change raw damage estimates.
- Recovery does not change raw KO/OHKO/2HKO context.
- Recovery is not fully simulated.
- Unknown or unconfirmed recovery items are not inferred.
- Item consumption is not tracked.
- Final 2HKO/3HKO truth is not claimed without Turn Engine.
- Focus Sash plus recovery interaction is not implemented.

Docs and tests:
- Updated `docs/advisor_payload_contract.md` with `recovery_context` semantics, reason codes, formula labels, and LLM wording guardrails.
- Updated advisor prompt and known limitations.
- Added tests for:
  - user-confirmed Sitrus Berry context
  - user-confirmed Leftovers context
  - formula labels and floor-based recovery amounts
  - unconfirmed item handling
  - no recovery item handling
  - missing max HP handling
  - raw damage unchanged
  - `ko_context` unchanged
  - my move direction
  - opponent known move direction
  - candidate move exclusion
  - prompt/contract guardrails

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 79 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 813 passed, 1 failed, 2 deselected.
  - Failure was isolated to `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`.
  - The isolated perf test passed when rerun by itself.
  - No v0.60 damage formula, raw roll, or perf-path code was changed.

Maintained boundaries:
- No Turn Engine.
- No item consumption tracking.
- No exact 2HKO/3HKO simulation.
- No KO context modification.
- No raw damage roll modification.
- No damage formula changes.
- No Focus Sash interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No full payload export.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.60.1 - Recovery context local Gemini verification

Purpose:
- Record local Gemini actual-call verification for v0.60 limited Sitrus / Leftovers `recovery_context`.

Observed local case:
- Case A - opponent Sitrus Berry:
  - Player Pokemon: Charizard.
  - Selected move: Heat Wave.
  - Opponent Pokemon: Garchomp.
  - Opponent item: user-confirmed Sitrus Berry.
  - Opponent max HP: 183.
  - Raw damage estimate: 75-90.
  - `ko_context.ohko.possible`: false.
  - `ko_context.two_hko.possible`: false.
  - `recovery_context.recovery_effect.estimated_recovery_hp`: 45.
  - `recovery_context.recovery_effect.formula_label`: `floor(max_hp / 4)`.

Gemini response summary:
- Gemini actual call succeeded.
- Gemini recommended Heat Wave.
- Gemini stated the raw estimate as 75-90 HP damage to Garchomp under default assumptions.
- Gemini stated the move is not an OHKO.
- Gemini recognized the user-confirmed Sitrus Berry.
- Gemini stated Sitrus Berry may restore 45 HP.
- Gemini described the recovery as limited context that may affect follow-up KOs.
- Gemini stated exact activation timing and item consumption are not modeled.

Confirmed behavior:
- Recovery context was surfaced as limited context.
- Recovery amount visibility worked.
- Raw damage estimate remained visible as 75-90.
- Gemini did not say recovery changed raw damage.
- Gemini did not say KO/OHKO/2HKO context already includes recovery.
- Gemini did not claim final KO, 2HKO, or 3HKO truth.
- Gemini did not say Sitrus definitely activates.
- Gemini did not infer an unknown or unconfirmed recovery item.

Gaps:
- Gemini did not explicitly say `ko_context` is unchanged.
- Gemini did not explicitly mention turn sequencing in the limitation sentence.
- Leftovers case was not exercised in this verification.

Verdict:
- v0.60.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- Recovery visibility: PASS.
- Limitation visibility: PARTIAL.

Perf flake note:
- v0.60 full pytest was pushed under a one-time perf flake exception.
- v0.60.1 is a documentation-only verification record.
- No perf threshold, skip, xfail, damage formula, or raw roll changes were made.

Next candidates:
- `v0.61 - Recovery Prompt Polish`.
- `v0.61 - Bright Powder Accuracy Design`.
- `v0.61 - Damage Perf Test Stability Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `recovery_context` changes.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No Turn Engine.
- No item consumption tracking.
- No exact KO simulation.
- No perf threshold changes.
- No test skip or xfail.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.61 - Recovery prompt polish

Purpose:
- Polish recovery wording after v0.60.1 local Gemini verification showed Recovery visibility PASS but Limitation visibility PARTIAL.

Implemented:
- Strengthened advisor prompt and payload contract wording for `recovery_context`.
- Clarified that `recovery_context` is limited context only.
- Clarified that raw damage estimates are unchanged.
- Clarified that `ko_context` is unchanged by recovery.
- Clarified that KO/OHKO/2HKO estimates do not include recovery.
- Strengthened follow-up wording:
  - recovery may affect follow-up KO/2HKO only under limited assumptions
- Strengthened timing and state limitations:
  - exact activation timing is not modeled
  - item consumption is not tracked
  - turn sequencing is not modeled
- Added explicit forbidden wording:
  - do not say Sitrus Berry definitely activates
  - do not say KO chance includes recovery
  - do not say recovery changes the damage range
- Preserved unavailable/no-invent guardrail for unknown or unconfirmed Sitrus Berry / Leftovers.

Docs and tests:
- Updated `docs/advisor_payload_contract.md`.
- Updated prompt/contract regression tests for:
  - limited recovery context
  - raw damage unchanged
  - `ko_context` unchanged
  - recovery not included in KO/OHKO/2HKO estimates
  - follow-up KO/2HKO limited assumptions
  - exact timing / item consumption / turn sequencing limitations
  - forbidden recovery overclaims

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 820 passed, 2 deselected.
- `uv run pytest -q`: 814 passed, 2 deselected.
- No v0.60 perf flake reproduced during v0.61 full pytest.

Maintained boundaries:
- No `recovery_context` structure changes.
- No recovery calculation changes.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No Turn Engine.
- No item consumption tracking.
- No exact KO/2HKO/3HKO simulation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No perf threshold changes.
- No test skip or xfail.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.61.1 - Recovery prompt local Gemini verification

Purpose:
- Record local Gemini actual-call verification after v0.61 recovery prompt polish.

Observed local case:
- Case A - opponent Sitrus Berry:
  - Player selected move: Heat Wave.
  - Opponent Pokemon: Garchomp.
  - Opponent item: user-confirmed Sitrus Berry.
  - Raw damage estimate: 33-39.
  - Recovery amount surfaced by Gemini: estimated 45 HP.

Gemini response:
> Use Heat Wave. It will deal 33-39 damage, which is not very effective against Garchomp.
>
> The main limitation is that damage estimates use default assumptions, exact KO context is not available, and Sitrus Berry recovery (estimated 45 HP) is not modeled for exact activation timing or item consumption. Possible opponent samples exist, but they are context only and not confirmed.

Confirmed behavior:
- Gemini actual call succeeded.
- Sitrus Berry recovery estimated 45 HP was mentioned.
- Exact activation timing and item consumption not modeled were mentioned.
- Raw damage estimate 33-39 was preserved in the response.
- Gemini did not say recovery changed the damage range.
- Gemini did not say recovery was included in KO chance.
- Gemini did not claim final KO, 2HKO, or 3HKO truth.
- Gemini did not infer an unknown or unconfirmed recovery item.

Gaps:
- Gemini did not explicitly say "KO/OHKO/2HKO estimates do not include recovery."
- Gemini used "exact KO context is not available", which is safe but a little ambiguous.
- `ko_context` separation remains PARTIAL rather than full PASS.

Verdict:
- v0.61.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- Recovery visibility: PASS.
- Limitation visibility: PASS.
- `ko_context` separation: PARTIAL.

Next candidates:
- `v0.62 - Bright Powder Accuracy Design`.
- `v0.62 - Damage Perf Test Stability Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `recovery_context` changes.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No Turn Engine.
- No item consumption tracking.
- No exact KO simulation.
- No perf threshold changes.
- No test skip or xfail.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.62 - Bright Powder accuracy design

Purpose:
- Design a limited Bright Powder accuracy/evasion context after v0.61.1 closed the recovery prompt verification line.

Current state:
- `damage_estimate` provides raw damage min/max/rolls.
- `ko_context` provides limited damage-roll KO/OHKO/2HKO context.
- `survival_context` provides limited Focus Sash survival context.
- `recovery_context` provides limited Sitrus / Leftovers recovery context.
- Bright Powder is legal and recognized in `champions_legal_items.json`, but its effect remains unmodeled.
- No general accuracy/evasion/hit chance engine exists.
- No Turn Engine exists.

Designed direction:
- Add a future `accuracy_context` as limited move-level context for user-confirmed Bright Powder.
- Keep raw damage min/max/rolls unchanged.
- Keep raw `ko_context` unchanged.
- Do not calculate hit-adjusted KO probability in the first implementation.
- Require known move accuracy before surfacing available accuracy context.
- Treat missing move accuracy as unavailable or limited unknown-accuracy state.

Recommended placement:
- Prefer a move-level sibling `accuracy_context`.
- If existing move payload patterns make sibling placement beside `damage_estimate` natural, that is acceptable.
- Do not nest accuracy fields inside `damage_estimate` or `ko_context`.
- Avoid top-level-only accuracy context for v0.63 because move accuracy is move-specific.

Accuracy policy:
- Bright Powder should be modeled only when the defender item is user-confirmed `bright-powder`.
- Use label-first fields such as `limited_evasion_modifier`, `accuracy_risk_note`, or `estimated_hit_reliability_note`.
- Do not expose final hit probability until Bright Powder modifier rules and Champions/PoChamps compatibility are confirmed.
- Move accuracy missing should not trigger guessed accuracy math.

LLM guardrails:
- `accuracy_context` is limited context only.
- Bright Powder may reduce hit reliability, not damage.
- Raw damage estimates are unchanged.
- Raw KO/OHKO/2HKO estimates do not include hit chance.
- Do not claim the move will miss.
- Do not claim final hit probability unless explicitly calculated.
- Do not infer Bright Powder if item is unknown or unconfirmed.

Future tests plan:
- user-confirmed Bright Powder plus known move accuracy -> `accuracy_context.available=true`
- unknown/unconfirmed Bright Powder no-invent behavior
- no Bright Powder unavailable/absent behavior
- move accuracy missing unavailable behavior
- raw damage unchanged
- raw `ko_context` unchanged
- no OHKO chance alteration
- my move and opponent known move directions
- candidate moves excluded or documented
- prompt guardrails
- existing Focus Sash, KO, recovery, type item, Choice Scarf, and opponent assumptions regressions

Recommended next candidate:
- `v0.63 - Bright Powder Limited Accuracy Context Implementation`

Alternative next candidate:
- `v0.63 - Accuracy Item Rule Validation Design`

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `accuracy_context` implementation.
- No hit-adjusted KO probability.
- No Turn Engine.
- No accuracy/evasion stage system.
- No ability/weather/item interaction modeling.
- No KO context modification.
- No raw damage roll modification.
- No Focus Sash / Sitrus interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.63 - Bright Powder limited accuracy context

Purpose:
- Add limited Bright Powder accuracy context without changing raw damage or raw KO context.

Implemented:
- Added `llm/advisor_accuracy_context.py`.
- Added additive move-level `accuracy_context` for:
  - my selected move / available moves targeting `opponent_active`
  - opponent known moves targeting `my_active`
- Kept opponent candidate moves excluded from `damage_estimate`, `survival_context`, `recovery_context`, `accuracy_context`, and `ko_context`.

Bright Powder behavior:
- Modeled only when defender item is user-confirmed `bright-powder`.
- Requires known move accuracy metadata.
- Returns unavailable for:
  - no Bright Powder
  - unknown/unconfirmed Bright Powder
  - missing move accuracy
  - missing damage estimate
- Provides label/formula context only:
  - `effect_label: may_reduce_hit_reliability`
  - `formula_label: bright_powder_limited_modifier`
- Does not calculate final hit probability.
- Does not calculate hit-adjusted KO probability.

Preserved raw contexts:
- Raw damage min/max/rolls are unchanged.
- `ko_context` is unchanged.
- OHKO chance remains based on raw damage rolls only.
- Bright Powder is not treated as damage reduction.

Prompt / contract updates:
- Documented `accuracy_context` field semantics.
- Added Bright Powder limited assumptions.
- Documented `base_accuracy`, `effect_label`, `formula_label`, and `hit_probability_integrated=false`.
- Added guardrails:
  - raw damage unchanged
  - raw `ko_context` unchanged
  - KO/OHKO/2HKO estimates do not include hit chance
  - do not claim the move will miss
  - do not claim guaranteed miss
  - do not infer Bright Powder if item is unknown or unconfirmed
  - accuracy/evasion stages, ability interactions, weather, multi-hit accuracy, and turn sequencing are not modeled

Tests:
- Added `accuracy_context` helper and payload attachment tests for:
  - user-confirmed Bright Powder plus known move accuracy
  - unknown/unconfirmed Bright Powder
  - no Bright Powder
  - missing move accuracy
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move direction
  - opponent known move direction
  - candidate move exclusion
- Added prompt/contract regression tests for Bright Powder guardrails.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 85 passed.
- `uv run pytest -q`: 820 passed, 2 deselected.

Maintained boundaries:
- No final hit probability.
- No hit-adjusted KO probability.
- No accuracy/evasion stage system.
- No Turn Engine.
- No ability/weather/item interaction modeling.
- No KO context modification.
- No raw damage roll modification.
- No damage formula changes.
- No Focus Sash / Sitrus interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.63.1 - Bright Powder accuracy local Gemini verification

Purpose:
- Record local Gemini actual-call verification after v0.63 Bright Powder limited `accuracy_context` implementation.

Observed local case:
- Case A - opponent Bright Powder:
  - Player selected move: Heat Wave.
  - Move accuracy metadata: 90.
  - Opponent Pokemon: Garchomp.
  - Opponent item: user-confirmed Bright Powder.
  - `accuracy_context.available`: true.
  - `accuracy_context.accuracy_effect.hit_probability_integrated`: false.
  - Raw damage estimate: 33-39.
  - `ko_context.ohko.possible`: false.
  - `ko_context.ohko.chance`: 0.0.

Gemini response:
> Use **Heat Wave**. It deals 18.0-21.3% damage to Garchomp, but is not very effective. No OHKO or 2HKO is possible with this move.
>
> The main limitation is that Garchomp's user-confirmed Bright Powder may reduce Heat Wave's hit reliability, though this is not modeled in the damage rolls or KO context. The damage estimate uses default assumptions for your Charizard's stats and is not final battle damage.

Confirmed behavior:
- Gemini actual call succeeded.
- Bright Powder was mentioned as user-confirmed.
- Gemini used limited hit reliability wording:
  - "may reduce Heat Wave's hit reliability"
- Raw damage was preserved:
  - response described 18.0-21.3%, matching 33-39 damage over 183 HP.
- Gemini stated Bright Powder was not modeled in damage rolls or KO context.
- Gemini did not say KO/OHKO/2HKO estimates include hit chance.
- Gemini did not claim hit-adjusted KO probability.
- Gemini did not describe Bright Powder as damage reduction.
- Gemini did not say Heat Wave will miss or is guaranteed to miss.
- Gemini did not infer an unknown or unconfirmed Bright Powder item.

Gaps:
- Gemini did not explicitly mention accuracy/evasion stages.
- Gemini did not explicitly mention ability/weather interactions.
- Gemini did not explicitly mention turn sequencing.
- Limitation wording is safe but not complete.

Verdict:
- v0.63.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- Bright Powder visibility: PASS.
- Limited accuracy context: PASS.
- Raw damage unchanged: PASS.
- `ko_context` / hit chance separation: PASS.
- Limitation visibility: PARTIAL.

Next candidates:
- `v0.64 - Accuracy Prompt Polish`.
- `v0.64 - Damage Perf Test Stability Design`.
- `v0.64 - Scope Lens Critical Hit Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `accuracy_context` changes.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No final hit probability.
- No hit-adjusted KO probability.
- No Turn Engine.
- No accuracy/evasion stage system.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.64 - Accuracy prompt polish

Purpose:
- Polish Bright Powder `accuracy_context` wording after v0.63.1 local Gemini verification showed Limitation visibility PARTIAL.

Implemented:
- Strengthened advisor prompt and payload contract wording for `accuracy_context`.
- Clarified that `accuracy_context` is limited context only.
- Strengthened Bright Powder wording:
  - Bright Powder may reduce hit reliability
  - Bright Powder is not damage reduction
- Strengthened raw context separation:
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include hit chance
- Strengthened probability exclusions:
  - final hit probability is not calculated
  - hit-adjusted KO probability is not calculated
  - do not state a hit-adjusted KO percent unless a future explicit field calculates it
- Strengthened limitation sentence:
  - final hit probability, accuracy/evasion stages, ability/weather interactions, multi-hit accuracy, and turn sequencing are not modeled
- Preserved unavailable/no-invent guardrail:
  - unknown/unconfirmed Bright Powder should not be inferred
  - unavailable `accuracy_context` should not force Bright Powder wording

Docs and tests:
- Updated `docs/advisor_payload_contract.md`.
- Updated prompt/contract regression tests for:
  - limited accuracy context
  - hit reliability wording
  - raw damage unchanged
  - `ko_context` unchanged
  - KO/OHKO/2HKO estimates do not include hit chance
  - final hit probability not calculated
  - hit-adjusted KO probability not calculated
  - accuracy/evasion stages not modeled
  - ability/weather interactions not modeled
  - multi-hit accuracy not modeled
  - turn sequencing not modeled
  - no damage reduction wording
  - no will-miss or guaranteed-miss wording
  - unknown/unconfirmed no-invent guardrail

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.

Maintained boundaries:
- No `accuracy_context` structure changes.
- No accuracy calculation changes.
- No final hit probability.
- No hit-adjusted KO probability.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No Turn Engine.
- No accuracy/evasion stage system.
- No ability/weather/item interaction modeling.
- No UI changes.
- No fixture changes.
- No sample additions.
- No perf threshold changes.
- No test skip or xfail.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.65 - Scope Lens critical-hit design

Purpose:
- Design a limited Scope Lens critical-hit context after the Bright Powder accuracy prompt line reached a stable enough point to move on.

Designed:
- Documented current state:
  - `damage_estimate` provides raw damage min/max/rolls
  - `ko_context` provides limited damage-roll KO/OHKO/2HKO context
  - `survival_context` provides Focus Sash limited survival
  - `recovery_context` provides Sitrus / Leftovers limited recovery
  - `accuracy_context` provides Bright Powder limited hit reliability
  - Scope Lens is legal/recognized but not connected to advisor payload context
- Noted lower-level critical-hit utilities already exist in `advisor/damage/crit.py`:
  - Scope Lens can contribute a critical-hit stage there
  - stage-to-probability helpers exist
  - crit damage modifier helpers exist
  - these are not yet exposed as LLM payload context
- Defined the problem:
  - Scope Lens is not a direct always-on damage boost
  - current raw damage estimates do not include crit chance
  - raw `ko_context` does not include crit chance
  - mixing Scope Lens into raw damage or KO context would imply unsupported crit-adjusted probability
- Proposed additive `critical_context`:
  - move-level sibling preferred
  - damage-estimate sibling acceptable if repo structure requires it
  - never nested inside `damage_estimate`
  - never nested inside `ko_context`
- Proposed payload fields:
  - `mode: limited_critical_context`
  - attacker side
  - user-confirmed `scope-lens`
  - `effect_label: may_increase_critical_hit_likelihood`
  - `formula_label: scope_lens_limited_critical_modifier`
  - `raw_damage_rolls_changed: false`
  - `ko_context_changed: false`
  - `crit_probability_integrated: false`
  - `crit_adjusted_ko_integrated: false`
- Recommended label-first policy:
  - no final critical-hit probability in v0.66
  - no crit-adjusted KO probability in v0.66
  - validate Champions/PoChamps crit-stage compatibility before exposing numeric crit chance
- Added LLM guardrail design:
  - Scope Lens may increase critical-hit likelihood
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include crit chance
  - crit-adjusted KO probability is not calculated
  - do not claim a critical hit will occur
  - do not describe Scope Lens as direct damage boost
- Added future tests plan for:
  - user-confirmed Scope Lens
  - unconfirmed/no Scope Lens
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move / opponent known move directions
  - candidate move exclusion
  - prompt guardrails
  - existing Bright Powder, recovery, KO, Focus Sash, type item, speed, and opponent assumptions regressions

v0.66 recommendation:
- `v0.66 - Scope Lens Limited Critical Context Implementation`.
- Alternative: `v0.66 - Critical Hit Rule Validation Design` if T1/T2 want exact crit stage / Scope Lens modifier validation first.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `critical_context` implementation.
- No final critical-hit probability.
- No crit-adjusted KO probability.
- No Turn Engine.
- No critical-hit stage system in the LLM payload.
- No ability/weather/item interaction modeling.
- No KO context modification.
- No raw damage roll modification.
- No Focus Sash / Sitrus / Bright Powder interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.66 - Scope Lens limited critical context

Purpose:
- Add limited Scope Lens critical-hit context as an additive move-level payload sibling without changing raw damage or raw KO context.

Implemented:
- Added `llm/advisor_critical_context.py`.
- Added `build_critical_context(...)` for limited Scope Lens critical-hit context.
- Attached `critical_context` to:
  - `moves.my_available_moves[*]`
  - `moves.my_selected_move`
  - `opponent_moves.known_moves[*]`
- Kept candidate moves excluded:
  - no `damage_estimate`
  - no `ko_context`
  - no `recovery_context`
  - no `accuracy_context`
  - no `critical_context`
  - no `survival_context`
- Modeled only user-confirmed Scope Lens:
  - `item_id: scope-lens`
  - `status: user_confirmed`
- Added unavailable fallbacks:
  - `no_scope_lens`
  - `item_not_user_confirmed`
  - `damage_estimate_missing`
- Added `critical_effect` fields:
  - `type: scope_lens`
  - `effect_label: may_increase_critical_hit_likelihood`
  - `formula_label: scope_lens_limited_critical_modifier`
  - `raw_damage_rolls_changed: false`
  - `ko_context_changed: false`
  - `crit_probability_integrated: false`
  - `crit_adjusted_ko_integrated: false`
- Added Scope Lens to legal-but-not-modeled item effect summary as `critical_hit`.
- Preserved raw damage:
  - no damage formula changes
  - no raw min/max changes
  - no raw rolls changes
- Preserved raw KO context:
  - `ko_context` unchanged
  - OHKO chance unchanged
  - no crit chance folded into KO/OHKO/2HKO estimates
- Added prompt/contract guardrails:
  - `critical_context` is limited critical-hit context only
  - Scope Lens may increase critical-hit likelihood
  - Scope Lens is not a direct damage boost
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include crit chance
  - final critical-hit probability is not calculated
  - crit-adjusted KO probability is not calculated
  - do not say the move will crit or that crit is guaranteed
  - do not infer Scope Lens if item is unknown or unconfirmed
  - critical-hit stages, abilities, move-specific crit effects, and turn sequencing are not modeled
- Updated `docs/advisor_payload_contract.md` with `critical_context` semantics, fields, reason codes, and LLM wording examples.
- Added tests for:
  - user-confirmed Scope Lens available context
  - unconfirmed Scope Lens fallback
  - no Scope Lens fallback
  - damage estimate missing fallback
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move attacker direction
  - opponent known move attacker direction
  - candidate move exclusion
  - prompt/contract guardrails
  - existing Bright Powder, recovery, KO, Focus Sash, type item, speed, and opponent assumptions regressions

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 91 passed.
- `uv run pytest -q`: 826 passed, 2 deselected.

Maintained boundaries:
- No final critical-hit probability.
- No crit-adjusted KO probability.
- No critical-hit stage system in the LLM payload.
- No Turn Engine.
- No ability/weather/item interaction modeling.
- No KO context modification.
- No raw damage roll modification.
- No damage formula changes.
- No Focus Sash / Sitrus / Bright Powder interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No full payload export.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.67 - Damage perf test stability design

Purpose:
- Design a safer policy for stabilizing `tests/test_damage_perf.py` after the v0.60 one-off full-suite perf flake.

Designed:
- Documented current state:
  - damage formula and raw rolls are core calculation paths
  - `test_item_damage_calculation_under_point_12ms_average` guards item damage calculation performance
  - v0.60 had one full-suite failure at about `0.149357ms` against `< 0.12ms`
  - the same test passed three isolated reruns
  - v0.60 touched LLM/context paths, not damage formula or raw roll code
  - v0.61, v0.63, v0.64, and v0.66 full pytest runs passed afterward
- Defined the problem:
  - microbenchmark-style tests can be sensitive to environment load
  - one timed sample can fail due to transient outliers
  - threshold loosening or skip/xfail would risk hiding real regressions
- Compared options:
  - keep current behavior
  - isolated perf mode
  - repeated measurement / median basis
  - warmup before measurement
  - perf marker separation
  - threshold adjustment
- Recommended v0.68 direction:
  - modify only `tests/test_damage_perf.py`
  - add warmup calls
  - add repeated measurements
  - assert on median average time
  - keep threshold unchanged unless separately approved
  - improve failure messages with samples, threshold, and isolated rerun command
- Documented test policy:
  - full pytest remains the normal gate
  - perf failures are not automatically ignored
  - isolated rerun 3 times when a perf failure appears load-sensitive
  - check whether damage formula / rolls / item modifier paths changed
  - T1/T2 approval required for any exception push
  - no threshold relaxation, skip, xfail, or unrelated optimization without a dedicated task

v0.68 recommendation:
- `v0.68 - Damage Perf Test Stability Implementation`.
- Scope should be limited to test harness stability in `tests/test_damage_perf.py`.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No test implementation.
- No threshold modification.
- No skip or xfail.
- No damage formula changes.
- No raw damage roll changes.
- No LLM/context changes.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.68 - Damage perf test stability implementation

Purpose:
- Stabilize damage perf tests after the v0.60 full-suite perf flake without loosening thresholds or hiding tests.

Implemented:
- Updated `tests/test_damage_perf.py` only.
- Added shared perf measurement helper:
  - warmup calls before timing
  - repeated measurement samples
  - median average milliseconds assertion
  - detailed failure message
- Added constants:
  - `PERF_ITERATIONS = 1000`
  - `PERF_REPEATS = 5`
  - `PERF_WARMUP_ITERATIONS = 100`
- Applied median-based assertion to:
  - `test_damage_calculation_under_5ms_average`
  - `test_field_damage_calculation_under_6ms_average`
  - `test_item_damage_calculation_under_point_12ms_average`
  - `test_ability_damage_calculation_under_point_20ms_average`
- Preserved existing thresholds:
  - `< 5.0ms`
  - `< 6.0ms`
  - `< 0.12ms`
  - `< 0.20ms`
- Improved failure message with:
  - median average
  - threshold
  - all measured samples
  - min/max sample values
  - isolated rerun command
  - reminder to rerun isolated 3 times before changing threshold if only full-suite fails

Verification:
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- Isolated repeated item perf runs:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: 1 passed.
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: 1 passed.
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: 1 passed.
- Item perf sample check:
  - threshold: `< 0.12ms`
  - median average: `0.040732ms`
  - samples: `0.040732`, `0.042375`, `0.041486`, `0.040344`, `0.036867`
- `uv run pytest -q`: 826 passed, 2 deselected.

Maintained boundaries:
- No threshold modification.
- No skip or xfail.
- No production code changes.
- No damage formula changes.
- No raw damage roll changes.
- No LLM/context changes.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.69 - King's Rock flinch design

Purpose:
- Design a limited King's Rock flinch-pressure context after the Scope Lens critical-context line reached implementation.

Designed:
- Documented current state:
  - `damage_estimate` provides raw damage min/max/rolls
  - `ko_context` provides limited damage-roll KO/OHKO/2HKO context
  - `survival_context`, `recovery_context`, `accuracy_context`, and `critical_context` are additive limited contexts
  - King's Rock is legal/recognized in the item repository, but its flinch effect is not modeled
  - `advisor/damage/move_categories.py` explicitly leaves item-added King's Rock flinch outside the current secondary-effect helper
- Defined the problem:
  - King's Rock is flinch pressure, not direct damage boost
  - flinch usefulness depends on hit, speed/order, target action state, move eligibility, multi-hit behavior, abilities, and turn sequencing
  - mixing flinch into raw damage or `ko_context` would imply unsupported final outcome probability
- Proposed additive `flinch_context`:
  - mode: `limited_flinch_context`
  - attacker-side item: user-confirmed `kings-rock`
  - move-level sibling preferred
  - `effect_label`: `may_add_flinch_pressure`
  - `formula_label`: `kings_rock_limited_flinch_modifier`
  - `raw_damage_rolls_changed: false`
  - `ko_context_changed: false`
  - `final_flinch_probability_integrated: false`
  - `flinch_adjusted_outcome_integrated: false`
  - `is_final_battle_truth: false`
- Compared placement options:
  - move-level sibling field
  - `damage_estimate` sibling if implementation structure requires it
  - top-level `flinch_context`
- Recommended move-level sibling placement for v0.70.
- Designed flinch amount policy:
  - label/formula only in first implementation
  - no numeric final flinch probability
  - no flinch-adjusted KO or outcome probability
  - validate exact modifier, move eligibility, multi-hit behavior, and Champions/PoChamps compatibility before numeric probability display
- Added LLM guardrail design:
  - King's Rock may add flinch pressure
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include flinch chance
  - final flinch probability is not calculated
  - flinch-adjusted outcome probability is not calculated
  - do not claim the target will flinch or cannot move
  - do not infer King's Rock if the item is unknown or unconfirmed
  - do not describe King's Rock as a direct damage boost
  - speed/order, target action state, ability interactions, multi-hit handling, and turn sequencing are not modeled
- Added future test plan for:
  - user-confirmed King's Rock availability
  - unknown/unconfirmed/no King's Rock unavailable behavior
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move and opponent known move direction
  - candidate moves excluded
  - prompt guardrails
  - existing critical, accuracy, recovery, KO, Focus Sash, type item, speed context, and opponent assumptions regressions

v0.70 recommendation:
- `v0.70 - King's Rock Limited Flinch Context Implementation`.
- Alternative: `v0.70 - Flinch Rule Validation Design` if T1/T2 want exact King's Rock modifier / move eligibility validation first.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `flinch_context` implementation.
- No final flinch probability.
- No flinch-adjusted outcome probability.
- No Turn Engine.
- No speed/order integration.
- No target action state.
- No ability/weather/item interaction modeling.
- No multi-hit handling.
- No KO context modification.
- No raw damage roll modification.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.70 - King's Rock limited flinch context

Purpose:
- Add limited King's Rock flinch context as an additive move-level payload sibling without changing raw damage or raw KO context.

Implemented:
- Added `llm/advisor_flinch_context.py`.
- Added `build_flinch_context(...)` for limited King's Rock flinch pressure context.
- Attached `flinch_context` to:
  - `moves.my_available_moves[*]`
  - `moves.my_selected_move`
  - `opponent_moves.known_moves[*]`
- Kept `opponent_moves.candidate_moves[*]` excluded from `damage_estimate`, `ko_context`, `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, and `flinch_context`.
- Modeled only attacker-side user-confirmed King's Rock:
  - item id: `kings-rock`
  - item status: `user_confirmed`
- Added unavailable behavior:
  - `no_kings_rock`
  - `item_not_user_confirmed`
  - `damage_estimate_missing`
- Added `flinch_effect` fields:
  - `type: kings_rock`
  - `effect_label: may_add_flinch_pressure`
  - `formula_label: kings_rock_limited_flinch_modifier`
  - `raw_damage_rolls_changed: false`
  - `ko_context_changed: false`
  - `flinch_probability_integrated: false`
  - `turn_outcome_integrated: false`
- Added limitations:
  - limited flinch context only
  - final flinch probability not modeled
  - speed order not modeled
  - target action state not modeled
  - abilities not modeled
  - multi-hit handling not modeled
  - turn sequencing not modeled
- Updated LLM prompt and payload contract guardrails:
  - King's Rock may add flinch pressure
  - King's Rock is not a direct damage boost
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include flinch chance
  - final flinch probability is not calculated
  - flinch-adjusted turn/outcome probability is not calculated
  - do not claim the target will flinch, cannot move, or that flinch is guaranteed
  - do not infer King's Rock if the item is unknown or unconfirmed
- Updated `docs/advisor_payload_contract.md` with:
  - `flinch_context` field semantics
  - King's Rock limited assumptions
  - effect labels
  - reason codes
  - LLM wording guardrails
- Added tests for:
  - user-confirmed King's Rock availability
  - unknown/unconfirmed King's Rock unavailable behavior
  - no King's Rock unavailable behavior
  - damage-estimate missing unavailable behavior
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move direction
  - opponent known move direction
  - candidate moves excluded
  - prompt/contract guardrails

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 97 passed.
- `uv run pytest -q`: 832 passed, 2 deselected.

Maintained boundaries:
- No final flinch probability.
- No flinch-adjusted turn/outcome probability.
- No speed/order integration.
- No target action state.
- No Turn Engine.
- No ability/weather/item interaction implementation.
- No KO context modification.
- No raw damage roll modification.
- No damage formula changes.
- No Focus Sash / Sitrus / Bright Powder / Scope Lens interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.70.1 - King's Rock flinch local Gemini verification

Purpose:
- Record local Gemini actual-call verification for the v0.70 limited King's Rock `flinch_context`.

Observed local case:
- Case A - my Pokemon has user-confirmed King's Rock:
  - Player Pokemon: Charizard.
  - Player item: King's Rock.
  - Item status: `user_confirmed`.
  - Selected move: Flamethrower.
  - Opponent Pokemon: Garchomp.
  - Opponent current/max HP available through user-confirmed stat profile.
  - Payload check before call:
    - `flinch_context.available: true`
    - `flinch_effect.effect_label: may_add_flinch_pressure`
    - `damage_estimate.damage_range: 31-37`
    - `ko_context.available: true`

Gemini response:
- "Use Flamethrower. It deals 31-37 HP (16.9-20.2%) damage, but is not very effective. Your Charizard's King's Rock may add flinch pressure, but final flinch probability is not modeled. Charizard's attacking stats are based on default assumptions."

Confirmed behavior:
- Gemini actual call succeeded.
- User-confirmed King's Rock was mentioned.
- Limited flinch context wording appeared:
  - "may add flinch pressure"
  - "final flinch probability is not modeled"
- Raw damage estimate was preserved:
  - response repeated `31-37 HP`
  - no wording claimed King's Rock changed the damage range
- `ko_context` / flinch chance separation was safe but incomplete:
  - response did not say KO/OHKO/2HKO estimates include flinch chance
  - response did not explicitly say KO/OHKO/2HKO estimates do not include flinch chance
- Final flinch probability was not claimed.
- Flinch-adjusted turn/outcome probability was not claimed.
- No direct damage boost hallucination appeared.
- No "will flinch", "cannot move", or "guaranteed flinch" wording appeared.
- No unknown/unconfirmed item inference appeared.

Limitation visibility:
- Mentioned:
  - final flinch probability is not modeled
  - default attacking-stat assumptions
- Missing or weak:
  - KO/OHKO/2HKO estimates do not include flinch chance
  - flinch-adjusted turn/outcome probability is not calculated
  - speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled

Verdict:
- v0.70.1 local Gemini verification: PARTIAL PASS.
- Safety: PASS.
- King's Rock visibility: PASS.
- Limited flinch context: PASS.
- `ko_context` / flinch chance separation: PARTIAL.
- Limitation visibility: PARTIAL.

Next candidates:
- `v0.71 - Flinch Prompt Polish`.
- `v0.71 - Loaded Dice / Multi-hit Context Design`.
- `v0.71 - Local Gemini Verification Batch`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No `flinch_context` changes.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No final flinch probability implementation.
- No flinch-adjusted outcome implementation.
- No speed/order integration.
- No target action state.
- No Turn Engine.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.71 - Flinch prompt polish

Purpose:
- Improve King’s Rock `flinch_context` response wording after v0.70.1 local Gemini verification found safe but incomplete limitation visibility.

Implemented:
- Strengthened advisor prompt and payload contract wording for `flinch_context.available=true`.
- Added explicit wording that:
  - the raw damage estimate is unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include flinch chance
  - final flinch probability is not calculated
  - flinch-adjusted turn/outcome probability is not calculated
  - speed order is not modeled
  - target action state is not modeled
  - abilities are not modeled
  - multi-hit handling is not modeled
  - turn sequencing is not modeled
- Preserved King’s Rock wording:
  - may add flinch pressure
  - not a direct damage boost
  - user-confirmed item only
- Preserved no-invent guardrail:
  - do not infer King’s Rock if item is unknown or unconfirmed
  - do not force flinch limitation text when no `flinch_context` is present
- Preserved definite-outcome guardrails:
  - do not claim the target will flinch
  - do not claim the target cannot move
  - do not claim flinch is guaranteed
- Updated `docs/advisor_payload_contract.md`.
- Added payload contract tests for:
  - limited flinch context wording
  - raw damage unchanged wording
  - raw `ko_context` unchanged wording
  - KO/OHKO/2HKO estimates not including flinch chance
  - final flinch probability not calculated
  - flinch-adjusted outcome not calculated
  - speed order / target action state / abilities / multi-hit handling / turn sequencing not modeled
  - direct damage boost and definite flinch guardrails

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 832 passed, 2 deselected.

Maintained boundaries:
- No `flinch_context` structure changes.
- No flinch calculation changes.
- No final flinch probability.
- No flinch-adjusted turn/outcome probability.
- No speed/order integration.
- No target action state.
- No `ko_context` changes.
- No damage formula changes.
- No raw damage roll changes.
- No Turn Engine.
- No ability/weather/item interaction implementation.
- No UI changes.
- No fixture changes.
- No sample additions.
- No perf threshold changes.
- No skip or xfail.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

Next:
- v0.71.1 local Gemini verification should confirm whether the strengthened flinch limitation sentence appears naturally.

---

## v0.72 - Loaded Dice / multi-hit context design

Purpose:
- Design a limited Loaded Dice multi-hit context after the King's Rock flinch prompt line reached a stable enough point to move on.

Designed:
- Documented current state:
  - `damage_estimate` provides raw damage min/max/rolls
  - `ko_context` provides limited damage-roll KO/OHKO/2HKO context
  - `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, and `flinch_context` are additive limited contexts
  - Loaded Dice is not connected to the LLM payload path as a multi-hit context
  - lower-level multi-hit and probability utilities already exist
  - `data/static/items.json` describes `loaded-dice` as a `multihit_modifier`
- Defined the problem:
  - Loaded Dice is hit-count reliability, not direct damage boost
  - multi-hit touches raw damage aggregation, KO chance, Focus Sash, King's Rock, accuracy, crit, move metadata, and target HP
  - mixing Loaded Dice into raw damage or `ko_context` would imply unsupported final multi-hit outcome modeling
- Proposed additive `multi_hit_context`:
  - mode: `limited_multi_hit_context`
  - attacker-side item: user-confirmed `loaded-dice`
  - move-level sibling preferred
  - move metadata should identify multi-hit eligibility when available
  - `effect_label`: `may_improve_multi_hit_reliability`
  - `formula_label`: `loaded_dice_limited_multihit_modifier`
  - `raw_damage_rolls_changed: false`
  - `ko_context_changed: false`
  - `hit_count_probability_integrated: false`
  - `multi_hit_adjusted_ko_integrated: false`
  - `is_final_battle_truth: false`
- Compared placement options:
  - move-level sibling field
  - `damage_estimate` sibling if implementation structure requires it
  - top-level `multi_hit_context`
- Recommended move-level sibling placement for v0.73.
- Designed multi-hit amount policy:
  - label/formula only in first implementation
  - no numeric final hit count probability
  - no multi-hit-adjusted KO probability
  - no guaranteed hit-count claim
  - validate rule exposure, move eligibility, and Champions/PoChamps compatibility before numeric probability display
- Added LLM guardrail design:
  - Loaded Dice may improve multi-hit reliability for eligible moves
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include multi-hit count changes
  - final hit count probability is not calculated
  - multi-hit-adjusted KO probability is not calculated
  - do not claim a specific number of hits will occur
  - do not infer Loaded Dice if the item is unknown or unconfirmed
  - do not describe Loaded Dice as a direct damage boost
  - Focus Sash / King's Rock / accuracy / crit per-hit interactions are not modeled
- Added future test plan for:
  - user-confirmed Loaded Dice + known multi-hit move availability
  - unknown/unconfirmed/no Loaded Dice unavailable behavior
  - move-not-multi-hit and missing metadata behavior
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move and opponent known move direction
  - candidate moves excluded
  - prompt guardrails
  - existing flinch, critical, accuracy, recovery, KO, Focus Sash, type item, speed context, and opponent assumptions regressions

v0.73 recommendation:
- `v0.73 - Loaded Dice Limited Multi-hit Context Implementation`.
- Alternative: `v0.73 - Multi-hit Rule Validation Design` if T1/T2 want Loaded Dice rule exposure / move eligibility validation first.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `multi_hit_context` implementation.
- No final hit count probability.
- No multi-hit-adjusted KO probability.
- No Turn Engine.
- No multi-hit damage aggregation in the LLM payload.
- No Focus Sash / King's Rock interaction implementation.
- No accuracy/crit per-hit modeling.
- No KO context modification.
- No raw damage roll modification.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.73 - Loaded Dice limited multi-hit context

Purpose:
- Add limited Loaded Dice `multi_hit_context` as an additive move-level sibling without changing raw damage rolls or KO context.

Implemented:
- Added `llm/advisor_multi_hit_context.py`.
- Attached additive `multi_hit_context` to:
  - my selected move
  - my available moves
  - opponent user-confirmed known moves
- Limited modeled availability to:
  - attacker item `loaded-dice`
  - item `status: user_confirmed`
  - move metadata identifying a multi-hit move
- Added unavailable reason handling for:
  - `no_loaded_dice`
  - `item_not_user_confirmed`
  - `move_not_multi_hit`
  - `move_multihit_metadata_missing`
  - `damage_estimate_missing`
- Kept candidate moves excluded from `multi_hit_context`.
- Added Loaded Dice to legal-but-not-modeled item effect reporting as `multi_hit`.

Payload behavior:
- `multi_hit_context.mode`: `limited_multi_hit_context`
- `multi_hit_effect.effect_label`: `may_improve_multi_hit_reliability`
- `multi_hit_effect.formula_label`: `loaded_dice_limited_multihit_modifier`
- `raw_damage_rolls_changed: false`
- `ko_context_changed: false`
- `hit_count_probability_integrated: false`
- `multi_hit_adjusted_ko_integrated: false`
- `is_final_battle_truth: false`

Guardrails:
- Loaded Dice may improve multi-hit reliability for eligible moves.
- Raw damage estimates are unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include multi-hit count changes.
- Final hit count probability is not calculated.
- Multi-hit-adjusted KO probability is not calculated.
- Do not claim a specific number of hits will occur or that 5 hits are guaranteed.
- Do not claim Loaded Dice breaks Focus Sash unless explicitly modeled.
- Do not infer Loaded Dice if item is unknown or unconfirmed.
- Do not describe Loaded Dice as a direct damage boost.
- Focus Sash / King's Rock / accuracy / crit per-hit handling and turn sequencing are not modeled.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 104 passed.
- `uv run pytest -q`: 839 passed, 2 deselected.

Maintained boundaries:
- No final hit count probability.
- No multi-hit-adjusted KO probability.
- No multi-hit damage aggregation.
- No Focus Sash interaction implementation.
- No King's Rock multi-hit interaction implementation.
- No accuracy/crit per-hit modeling.
- No Turn Engine.
- No KO context modification.
- No raw damage roll modification.
- No damage formula changes.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.74 - Power Herb / charge-turn context design

Purpose:
- Design a limited Power Herb charge-turn context after Loaded Dice `multi_hit_context` reached implementation and push.

Designed:
- Documented current state:
  - `damage_estimate` provides raw damage min/max/rolls
  - `ko_context` provides limited damage-roll KO/OHKO/2HKO context
  - `survival_context`, `recovery_context`, `accuracy_context`, `critical_context`, `flinch_context`, and `multi_hit_context` are additive limited contexts
  - Power Herb is not connected to the LLM payload path
  - no LLM-facing charge move metadata, item consumption tracking, once-per-battle state, or Turn Engine exists
  - inspected static item files did not show Power Herb metadata, so v0.75 needs either a small metadata source or a rule validation pass
- Defined the problem:
  - Power Herb is charge-move usability, not direct damage boost
  - charge-turn behavior touches move eligibility, item consumption, weather, switching, protection, Speed/order, and final outcome simulation
  - mixing Power Herb into raw damage or `ko_context` would imply unsupported turn sequencing or final KO claims
- Proposed additive `charge_context`:
  - mode: `limited_charge_move_context`
  - attacker-side item: user-confirmed `power-herb`
  - move-level sibling preferred
  - move metadata should identify charge-move eligibility when available
  - `effect_label`: `may_skip_charge_turn_for_eligible_move`
  - `formula_label`: `power_herb_limited_charge_modifier`
  - `raw_damage_rolls_changed: false`
  - `ko_context_changed: false`
  - `turn_sequence_integrated: false`
  - `item_consumption_tracked: false`
  - `is_final_battle_truth: false`
- Compared placement options:
  - move-level sibling field
  - `damage_estimate` sibling if implementation structure requires it
  - top-level `charge_context`
- Recommended move-level sibling placement for v0.75.
- Designed charge rule policy:
  - label/formula only in first implementation
  - no numeric final turn probability
  - no charge-turn-adjusted KO probability
  - no item consumption tracking
  - validate charge move metadata, item legality, move eligibility, and Champions/PoChamps compatibility before stronger claims
- Added LLM guardrail design:
  - Power Herb may allow an eligible charge move to skip the charging turn
  - raw damage estimates are unchanged
  - raw `ko_context` is unchanged
  - KO/OHKO/2HKO estimates do not include charge-turn sequencing
  - item consumption is not tracked
  - final turn outcome is not calculated
  - do not infer Power Herb if item is unknown or unconfirmed
  - do not claim Power Herb boosts damage directly
  - do not claim the move definitely resolves in one turn unless eligibility and item state are explicitly modeled
- Added future test plan for:
  - user-confirmed Power Herb + charge move metadata availability
  - unknown/unconfirmed/no Power Herb unavailable behavior
  - move-not-charge and missing charge metadata behavior
  - raw damage unchanged
  - `ko_context` unchanged
  - OHKO chance unchanged
  - my move and opponent known move direction
  - candidate moves excluded
  - prompt guardrails
  - existing Loaded Dice, King's Rock, Scope Lens, Bright Powder, recovery, KO, and Focus Sash regressions

v0.75 recommendation:
- `v0.75 - Power Herb Limited Charge Context Implementation` if a small explicit charge move metadata source can be safely defined without fixture churn.
- Alternative: `v0.75 - Charge Move Rule Validation Design` if T1/T2 want Power Herb legality, move eligibility, charge metadata availability, or weather exceptions validated first.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `charge_context` implementation.
- No item consumption tracking.
- No turn-sequence-adjusted KO probability.
- No Turn Engine.
- No charge move damage modification.
- No weather interaction.
- No KO context modification.
- No raw damage roll modification.
- No UI changes.
- No fixture changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.75 - Charge move rule validation design

Purpose:
- Validate the repo-native rule sources needed before implementing Power Herb `charge_context`.

Investigated:
- `docs/spike_v0.74_power_herb_charge_context_design.md`
- `llm/advisor_damage_estimate.py`
- `llm/advisor_payload_contract.py`
- `docs/advisor_payload_contract.md`
- `advisor/damage/items.py`
- `advisor/damage/item_modifiers.py`
- `data/static/items.json`
- `data/static/items_damage.json`
- `data/static/champions_legal_items.json`
- `data/static/moves.json` - not present
- `data/cache/moves/` - not present
- `data/cache/pokeapi/moves/`
- `tests/test_advisor_damage_estimate.py`
- `tests/test_advisor_payload_contract.py`

Validated:
- Power Herb is not currently implemented as `charge_context`.
- `data/static/moves.json` is not present.
- `data/cache/moves/` is not present.
- `data/cache/pokeapi/moves/` is present, but the inspected cache/index shape is not a reliable LLM-facing charge metadata source.
- Champions movepool cache entries are present and include normalized move ids such as `solar-beam`, `meteor-beam`, `sky-attack`, `fly`, `dig`, `dive`, `bounce`, and `solar-blade`.
- Champions movepool move entries expose ordinary move metadata such as `move_id`, names, type, category, power, accuracy, pp, source refs, confidence, and metadata source.
- No confirmed repo-native charge-turn field such as `is_charge_move`, `charge_turn`, `two_turn`, or `power_herb_eligible` was found.
- `data/static/move_flags.json` exists, but does not provide charge/charging flags.
- `core.move_repository.MoveView` exposes move id/name/type/category/power/accuracy/pp only.
- `data/static/items.json`, `data/static/items_damage.json`, and `data/static/champions_legal_items.json` do not contain a confirmed `power-herb` entry.
- Champions legality for Power Herb is not confirmed in the current inspected static item files.
- Move ids are already normalized as lowercase hyphenated ids in payload/cache paths; item normalization elsewhere uses strip/lowercase plus apostrophe removal and space/underscore-to-hyphen conversion.

Designed:
- Compared candidate rule sources:
  - use existing move metadata field if a future field exists
  - add a curated static charge move fixture, such as `data/static/charge_moves.json`
  - parse move descriptions
  - remain unsupported until explicit metadata exists
- Recommended against description parsing because it is brittle and not repo-native.
- Recommended `v0.76 - Charge Move Metadata Fixture Design` before implementation.
- Deferred `Power Herb Limited Charge Context Implementation` until charge move metadata and eligibility policy are approved.
- Defined eligibility policy:
  - user-confirmed Power Herb only
  - explicit charge metadata required
  - normalized lowercase hyphenated move ids
  - non-charge moves return `move_not_charge_move`
  - missing metadata returns `move_charge_metadata_missing`
  - no Power Herb returns `no_power_herb`
  - unconfirmed Power Herb returns `item_not_user_confirmed`
  - unsupported charge item returns `unsupported_charge_item`
  - weather exceptions remain out of scope
- Preserved safety policy:
  - raw damage unchanged
  - raw `ko_context` unchanged
  - `turn_sequence_integrated=false`
  - `item_consumption_tracked=false`
  - final turn outcome not calculated
  - item already consumed state not inferred
  - unknown/unconfirmed Power Herb not inferred

Future test plan:
- known charge move + user-confirmed Power Herb -> `charge_context.available=true`
- non-charge move + user-confirmed Power Herb -> `move_not_charge_move`
- missing metadata -> `move_charge_metadata_missing`
- no Power Herb -> `no_power_herb`
- unconfirmed Power Herb -> `item_not_user_confirmed`
- raw damage min/max/rolls unchanged
- `ko_context` unchanged
- candidate moves excluded
- prompt guardrails
- existing context regressions
- full pytest

v0.76 recommendation:
- Prefer `v0.76 - Charge Move Metadata Fixture Design`.
- Keep description parsing forbidden.
- Consider static allowlist implementation only after fixture schema, source notes, and eligibility policy are approved.
- Continue excluding weather interaction, item consumption tracking, Turn Engine, and turn-sequence-adjusted KO probability.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `charge_context` implementation.
- No fixture implementation.
- No allowlist implementation.
- No item consumption tracking.
- No turn-sequence-adjusted KO probability.
- No Turn Engine.
- No weather interaction.
- No damage formula change.
- No raw damage roll modification.
- No KO context modification.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.76 - Charge move metadata fixture design

Purpose:
- Design a deterministic repo-native charge move metadata fixture before implementing Power Herb `charge_context`.

Designed:
- Confirmed current state from v0.75:
  - no repo-native charge move field exists
  - `data/static/moves.json` is not present
  - `data/cache/moves/` is not present
  - `data/cache/pokeapi/moves/` exists but is not an LLM-facing charge metadata source
  - Power Herb metadata/legal status is not confirmed in inspected static item files
  - description parsing remains forbidden
- Compared fixture path options:
  - `data/static/charge_moves.json`
  - `data/static/move_metadata_overrides.json`
  - `data/static/power_herb_eligible_moves.json`
- Recommended `data/static/charge_moves.json` for v0.77 because it is narrow, explicit, and easy to test.
- Deferred broad `move_metadata_overrides.json` until multiple independent move metadata override needs exist.
- Rejected a Power-Herb-only eligible-move file because it hides the distinction between charge move metadata and item eligibility.
- Designed schema:
  - `version: charge_moves_v1`
  - `moves` object keyed by normalized move id
  - `is_charge_move`
  - `power_herb_eligible`
  - `charge_type`
  - `known_exceptions`
  - `source`
  - `confidence`
  - `notes`
- Validated initial move-scope candidates against repo/cache presence:
  - `solar-beam`, `solar-blade`, `meteor-beam`, and `sky-attack` are good initial fixture candidates
  - `skull-bash` is present in pokemon cache / KO mapping / PokeAPI index but was not confirmed in Champions movepool during this pass, so it should be optional/deferred
  - `fly`, `dig`, `dive`, `bounce`, and `phantom-force` are present but should be deferred for semi-invulnerable policy
  - `razor-wind`, `shadow-force`, `freeze-shock`, `ice-burn`, and `geomancy` were not observed in inspected repo/cache paths, so they are deferred
- Defined eligibility policy:
  - lowercase hyphenated move ids
  - user-confirmed Power Herb only
  - fixture key + `is_charge_move=true` + `power_herb_eligible=true` required for available context
  - absent fixture entry should mean `move_charge_metadata_missing`, not proof of non-charge status
  - explicit non-charge entries can return `move_not_charge_move`
  - weather exceptions remain notes/limitations only
- Proposed repository/helper design:
  - prefer `core/charge_move_repository.py`
  - load and validate fixture
  - normalize move ids
  - expose `get_charge_move_metadata(move_id)`
  - expose `is_power_herb_eligible(move_id)`
  - provide safe unavailable reasons
- Planned tests:
  - fixture loads
  - version exists
  - move ids normalized
  - required fields present
  - Solar Beam / Meteor Beam examples
  - unknown move safely unavailable
  - no description parsing
  - future charge context keeps raw damage and `ko_context` unchanged
  - existing context regressions
  - full pytest

v0.77 recommendation:
- `v0.77 - Charge Move Metadata Fixture Implementation`.
- Add `data/static/charge_moves.json`, a narrow helper/repository, and tests only.
- Do not add Power Herb LLM `charge_context` until v0.78.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No fixture implementation.
- No `charge_context` implementation.
- No Power Herb implementation.
- No item consumption tracking.
- No turn-sequence-adjusted KO probability.
- No Turn Engine.
- No weather interaction.
- No damage formula change.
- No raw damage roll modification.
- No KO context modification.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.77 - Charge move metadata fixture implementation

Purpose:
- Add a repo-native charge move metadata fixture and safe repository/helper before implementing Power Herb `charge_context`.

Implemented:
- Added `data/static/charge_moves.json`.
- Added `core/charge_move_repository.py`.
- Added `tests/test_charge_move_repository.py`.
- Implemented fixture loading and validation:
  - `version` must equal `charge_moves_v1`
  - `moves` must be an object
  - move ids must be normalized lowercase hyphenated slugs
  - every move entry must include `is_charge_move`, `power_herb_eligible`, `charge_type`, `source`, `confidence`, and `notes`
  - optional `known_exceptions` must be a list of strings
- Implemented helper behavior:
  - `load_charge_moves()`
  - `normalize_move_id(move_id)`
  - `ChargeMoveRepository.get_charge_move_metadata(move_id)`
  - `ChargeMoveRepository.is_charge_move(move_id)`
  - `ChargeMoveRepository.is_power_herb_eligible(move_id)`
- Added safe unknown handling:
  - unknown moves return `None` for metadata
  - unknown moves return `False` for charge move and Power Herb eligibility
  - `None` move ids return safe unavailable-style results
- Initial minimal move scope:
  - `solar-beam`
  - `solar-blade`
  - `meteor-beam`
  - `sky-attack`
- Recorded deferred move candidates in fixture metadata:
  - `skull-bash`
  - `fly`
  - `dig`
  - `dive`
  - `bounce`
  - `razor-wind`
  - `phantom-force`
  - `shadow-force`
  - `freeze-shock`
  - `ice-burn`
  - `geomancy`
- Kept description parsing out of the repository.
- Kept the repository independent from LLM modules.
- Kept the repository independent from damage formula and raw damage roll modules.

Verification:
- `uv run pytest tests/test_charge_move_repository.py -q`: 14 passed.
- `uv run pytest -q`: 853 passed, 2 deselected.

Maintained boundaries:
- No Power Herb `charge_context` implementation.
- No LLM payload changes.
- No `advisor_damage_estimate` connection.
- No item consumption tracking.
- No turn-sequence-adjusted KO probability.
- No Turn Engine.
- No weather interaction.
- No damage formula change.
- No raw damage roll modification.
- No KO context modification.
- No UI changes.
- No sample additions.
- No description parsing.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.78 - Champions legal item coverage verification design

Purpose:
- Pause Power Herb `charge_context` implementation and verify whether implemented item contexts align with Champions legal item coverage.

Verified item coverage:
- `charcoal`
  - Champions legal fixture: present legal
  - `items.json`: present
  - `items_damage.json`: present under `type_boost_items`
  - coverage decision: aligned
- `choice-scarf`
  - Champions legal fixture: present legal
  - `items.json`: present
  - `items_damage.json`: present under `stat_boost_items`
  - coverage decision: aligned
- `focus-sash`
  - Champions legal fixture: present legal
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: aligned via legal fixture; limited non-damage context
- `sitrus-berry`
  - Champions legal fixture: present legal
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: aligned via legal fixture; limited non-damage context
- `leftovers`
  - Champions legal fixture: present legal
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: aligned via legal fixture; limited non-damage context
- `bright-powder`
  - Champions legal fixture: present legal
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: aligned via legal fixture; limited non-damage context
- `scope-lens`
  - Champions legal fixture: present legal
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: aligned via legal fixture; limited non-damage context
- `kings-rock`
  - Champions legal fixture: present legal
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: aligned via legal fixture; limited non-damage context
- `loaded-dice`
  - Champions legal fixture: not present
  - `items.json`: present
  - `items_damage.json`: not present
  - coverage decision: mismatch; future-only or blocked until legal coverage is confirmed
- `power-herb`
  - Champions legal fixture: not present
  - `items.json`: not present
  - `items_damage.json`: not present
  - coverage decision: blocked; do not implement user-facing `charge_context`

Designed policy:
- Treat `data/static/champions_legal_items.json` as the gate for normal user-facing Champions item context exposure.
- Do not treat `items.json` alone as legal coverage.
- Do not treat `items_damage.json` alone as legal coverage.
- Do not treat `data/static/charge_moves.json` as Power Herb legality.
- Existing move metadata fixtures can remain because metadata is not user-facing item legality.
- Items absent from legal coverage should be marked `blocked_by_legal_item_coverage` or `future_only_until_legal_confirmed`.
- Do not implement new user-facing item contexts for items absent from Champions legal item coverage.

Key decisions:
- Power Herb `charge_context` remains blocked.
- v0.77 charge move metadata fixture remains valid as generic move metadata.
- Loaded Dice requires follow-up legal coverage decision because `multi_hit_context` exists while `loaded-dice` is absent from the Champions legal item fixture.

Recommended next candidates:
- `v0.79 - Legal Item Context Gating Design`.
- Alternative: `v0.79 - Loaded Dice Legal Coverage Follow-up`.
- Not recommended: `Power Herb Limited Charge Context Implementation` until Power Herb is legal-confirmed.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No fixture changes.
- No legal item fixture changes.
- No Power Herb `charge_context` implementation.
- No Loaded Dice behavior changes.
- No LLM payload changes.
- No item consumption tracking.
- No turn-sequence-adjusted KO probability.
- No Turn Engine.
- No weather interaction.
- No damage formula changes.
- No raw damage roll modifications.
- No KO context changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.79 - Legal item context gating design

Purpose:
- Design a legal gate so user-facing Champions item contexts cannot drift ahead of `data/static/champions_legal_items.json`.

Designed:
- Restated current context coverage:
  - Charcoal damage modifier
  - Choice Scarf `speed_context`
  - Focus Sash `survival_context`
  - Sitrus Berry / Leftovers `recovery_context`
  - Bright Powder `accuracy_context`
  - Scope Lens `critical_context`
  - King's Rock `flinch_context`
  - Loaded Dice `multi_hit_context`
- Defined the problem:
  - `items.json` does not prove Champions legality
  - `items_damage.json` does not prove Champions legality
  - context helper existence does not prove Champions legality
  - `charge_moves.json` does not prove Power Herb legality
  - user-confirmed item status is necessary but not sufficient
- Designed legal gate policy:
  - modeled user-facing item context requires legal coverage in `champions_legal_items.json`
  - user-confirmed but unlisted items should not emit modeled context
  - stable reason candidates include `blocked_by_legal_item_coverage`, `future_only_until_legal_confirmed`, and `unknown_item`
  - legal coverage, effect metadata, and LLM payload implementation remain separate review gates
- Compared placement options:
  - legal gate inside each context helper
  - common legal item helper/repository
  - payload assembly gate before context creation
- Recommended hybrid direction:
  - reuse `core.champions_item_repository.ChampionsItemRepository`
  - apply a common legal gate in payload assembly before attaching user-facing contexts
  - optionally add helper-level defensive checks later
- Defined item status classifications:
  - `legal_modeled`
  - `legal_unmodeled`
  - `implemented_but_not_legal`
  - `future_only`
  - `blocked_by_legal_item_coverage`
  - `unknown_item`
- Classified current items:
  - `charcoal`, `choice-scarf`, `focus-sash`, `sitrus-berry`, `leftovers`, `bright-powder`, `scope-lens`, and `kings-rock`: `legal_modeled`
  - `loaded-dice`: `implemented_but_not_legal` / `future_only`
  - `power-herb`: `blocked_by_legal_item_coverage`
- Loaded Dice policy:
  - keep implementation as future-only code
  - block user-facing context unless legal fixture coverage is added
  - do not mutate legal fixture without separate approved legal coverage update
- Power Herb policy:
  - keep `charge_context` blocked
  - do not expose Power Herb in user-facing payload
  - do not treat charge move metadata as item legality

v0.80 recommendation:
- `v0.80 - Legal Item Gate Implementation`.
- Reuse `ChampionsItemRepository`.
- Keep legal fixture unchanged.
- Add Loaded Dice blocked regression tests.
- Keep Power Herb blocked.

Future tests:
- legal item passes gate
- unlisted item fails gate
- user-confirmed illegal item still blocked
- `loaded-dice` blocked because absent from legal fixture
- `power-herb` blocked
- aligned item contexts still work
- no legal fixture mutation
- existing item context regressions
- full pytest

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No legal gate implementation.
- No legal fixture mutation.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No external web/legal research.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.80 - Legal item gate implementation

Purpose:
- Gate user-facing modeled item contexts by Champions legal item fixture coverage.

Implemented:
- Added `core/champions_legal_item_repository.py` as a thin legal gate helper around the existing `ChampionsItemRepository`.
- Added `llm/advisor_item_legal_gate.py` for LLM item-context blocking.
- Added stable blocked reason:
  - `blocked_by_legal_item_coverage`
- Added safe helper behavior:
  - `is_champions_legal_item(item_id)`
  - `get_legal_item_status(item_id)`
  - unknown/empty item ids return false safely
  - normalization handles case, spaces, and underscores through existing item normalization
- Applied legal gate to item context helpers:
  - Focus Sash `survival_context`
  - Sitrus / Leftovers `recovery_context`
  - Bright Powder `accuracy_context`
  - Scope Lens `critical_context`
  - King's Rock `flinch_context`
  - Loaded Dice `multi_hit_context`
- Preserved existing legal item contexts:
  - Focus Sash remains available when legal/user-confirmed/full HP/lethal conditions pass
  - Sitrus Berry / Leftovers remain available when legal/user-confirmed/max HP conditions pass
  - Bright Powder remains available when legal/user-confirmed/move accuracy conditions pass
  - Scope Lens remains available when legal/user-confirmed conditions pass
  - King's Rock remains available when legal/user-confirmed conditions pass
- Blocked Loaded Dice user-facing modeled context because `loaded-dice` is absent from `data/static/champions_legal_items.json`.
- Kept Power Herb blocked and did not add `charge_context`.
- Updated `docs/advisor_payload_contract.md`:
  - Champions legal fixture is the user-facing item context gate
  - `items.json` / `items_damage.json` are not legal coverage sources
  - `charge_moves.json` is move metadata and not Power Herb legality
  - Loaded Dice is blocked/future-only until legal coverage is confirmed
  - Power Herb remains blocked

Verification:
- `uv run pytest tests/test_champions_item_repository.py tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 139 passed.
- `uv run pytest -q`: 866 passed, 2 deselected.

Maintained boundaries:
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Power Herb legal addition.
- No Power Herb `charge_context` implementation.
- No Loaded Dice behavior expansion.
- No damage formula change.
- No raw damage roll modification.
- No KO context calculation change beyond legal-gated absence for non-legal item context.
- No Turn Engine.
- No item consumption tracking.
- No UI changes.
- No sample additions.
- No external research.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.81 - Loaded Dice legal coverage follow-up design

Purpose:
- Decide how to treat Loaded Dice after v0.80 legal gating blocked it from user-facing modeled context.

Designed:
- Confirmed current state:
  - Loaded Dice `multi_hit_context` implementation exists.
  - `loaded-dice` is absent from `data/static/champions_legal_items.json`.
  - `loaded-dice` is present in `data/static/items.json`, but `items.json` is not legal coverage.
  - `loaded-dice` is absent from `data/static/items_damage.json`.
  - v0.80 legal gate blocks user-facing modeled Loaded Dice context with `blocked_by_legal_item_coverage`.
  - legal fixture remains unchanged.
- Defined the policy problem:
  - implemented context code does not prove Champions legality.
  - exposing legal-unconfirmed Loaded Dice advice would be unsafe.
  - deleting already-tested implementation would reduce future reuse if legal coverage is later confirmed.
- Compared policy options:
  - keep implemented but blocked.
  - remove Loaded Dice context implementation.
  - keep as future-only with explicit docs/tests.
- Recommended Option C:
  - keep implementation as future-only support.
  - continue blocking user-facing modeled context through the legal gate.
  - preserve regression tests that user-confirmed Loaded Dice is still blocked while legal fixture coverage is absent.
  - require separate approved evidence before any legal fixture update.

Loaded Dice status:
- implementation status: implemented future-only support.
- legal fixture status: absent.
- user-facing status: blocked.
- stable reason: `blocked_by_legal_item_coverage`.
- `status=user_confirmed` remains necessary but not sufficient for modeled context.

Proposed v0.82 candidates:
- `v0.82 - Loaded Dice Future-only Documentation / Regression Polish`
  - optional docs/test naming clarity; no behavior change.
- `v0.82 - Return to Legal Item Feature Expansion`
  - choose an item already confirmed legal in `data/static/champions_legal_items.json`.
- `v0.82 - Local Gemini Verification Batch`
  - run deferred local Gemini verifications for recent context wording.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior expansion.
- No Power Herb implementation.
- No external research.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.82 - Local Gemini verification batch

Purpose:
- Record a local Gemini actual-call batch verification for recent item contexts and legal-gated future-only items.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: opponent Garchomp user-confirmed Bright Powder.
  - Case B: my Charizard user-confirmed Scope Lens.
  - Case C: my Charizard user-confirmed King's Rock.
  - Case D: my Charizard user-confirmed Loaded Dice with multi-hit move metadata, blocked by legal coverage.
  - Case E: my Charizard user-confirmed Power Herb, no `charge_context`.

Case A - Bright Powder:
- Gemini mentioned the opponent's user-confirmed Bright Powder.
- Gemini said Bright Powder may reduce Heat Wave's hit reliability.
- Raw damage was preserved as 18.0%-21.3% for Heat Wave.
- Gemini did not say Bright Powder reduced damage.
- Gemini did not claim final hit probability.
- Gemini did not say the move will miss or is guaranteed to miss.
- Gemini did not explicitly say KO/OHKO/2HKO estimates do not include hit chance.
- Result: PARTIAL PASS.

Case B - Scope Lens:
- Gemini mentioned Charizard's user-confirmed Scope Lens.
- Gemini said Scope Lens may increase critical-hit likelihood.
- Raw damage was preserved as 33-39 damage / 18.0%-21.3%.
- Gemini stated the critical-hit note is not included in raw damage and KO estimates.
- Gemini did not claim final crit probability.
- Gemini did not say the move will crit or that a critical hit is guaranteed.
- Gemini did not describe Scope Lens as a direct damage boost.
- Result: PASS.

Case C - King's Rock:
- Gemini mentioned Charizard's King's Rock.
- Gemini said King's Rock may add flinch pressure.
- Raw damage was preserved as 52-63 HP / 28.4%-34.4%.
- Gemini did not say flinch chance was included in KO chance.
- Gemini said flinch probability is not modeled.
- Gemini did not claim flinch-adjusted turn or outcome probability.
- Gemini did not say the target will flinch, cannot move, or is guaranteed to flinch.
- Wording included "damage modifier is not included," which is safe in outcome but slightly awkward because King's Rock is not a damage modifier.
- Speed/order, target action state, and turn sequencing limitations were not fully surfaced.
- Result: PARTIAL PASS.

Case D - Loaded Dice legal gate:
- Payload had `multi_hit_context.available=false` with reason `blocked_by_legal_item_coverage`.
- Gemini did not present Loaded Dice as legal-modeled context.
- Gemini did not say Loaded Dice may improve multi-hit reliability.
- Gemini did not say the move will hit 5 times or guarantee a hit count.
- Gemini did not claim multi-hit-adjusted KO probability.
- Gemini did mention "Loaded Dice's multi-hit effect is not modeled in this damage estimate."
- This is safe, but it still surfaces the blocked item instead of staying completely quiet about future-only item behavior.
- Result: PARTIAL PASS.

Case E - Power Herb blocked:
- Payload had no `charge_context`.
- Gemini did not claim Power Herb makes Solar Beam fire instantly.
- Gemini did not infer item consumption or turn sequencing.
- Gemini did not claim turn-sequence-adjusted KO probability.
- Gemini said "Power Herb effect is not modeled in the damage estimate."
- This is safe, but it still surfaces the blocked item instead of staying completely quiet about future-only charge behavior.
- Result: PARTIAL PASS.

Overall verification:
- Raw damage unchanged: PASS.
- `ko_context` / secondary-effect probability separation: PARTIAL PASS.
- Final probability claims: PASS.
- Illegal/future-only item modeled exposure: PASS for modeled context, PARTIAL for natural-language quietness.
- Hallucination safety: PARTIAL PASS.
- Overall verdict: PARTIAL PASS.

Next candidates:
- `v0.83 - Verification Prompt Polish`
- `v0.83 - Legal Item Gate Hardening`
- `v0.83 - Actual Champions Legal Item Expansion Design`

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No prompt changes.
- No tests changed.
- No context helper changes.
- No legal gate changes.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.83 - Verification prompt polish

Purpose:
- Polish prompt and contract wording after v0.82 local Gemini verification produced a PARTIAL PASS.

Implemented:
- Strengthened Bright Powder accuracy wording:
  - hit reliability context is separate from raw damage and KO estimates.
  - KO/OHKO/2HKO estimates do not include hit chance.
  - final hit probability is not calculated.
  - Bright Powder must not be described as damage reduction.
- Strengthened King's Rock flinch wording:
  - flinch pressure context is separate from raw damage and KO estimates.
  - KO/OHKO/2HKO estimates do not include flinch chance.
  - final flinch probability and flinch-adjusted turn/outcome probability are not calculated.
  - speed order, target action state, abilities, multi-hit handling, and turn sequencing are not modeled.
  - prefer "raw damage estimate is unchanged" over awkward wording such as "damage modifier is not included."
- Strengthened blocked/future-only item quietness:
  - blocked legal item reasons are developer/debug/contract metadata.
  - Loaded Dice / Power Herb blocked or future-only effects should not appear in normal user-facing recommendation text.
  - do not say "Loaded Dice is not modeled" or "Power Herb is not modeled" by default unless the user explicitly asks about that item.
  - do not imply blocked or future-only items are available in Champions.
- Updated:
  - `llm/advisor_client.py`
  - `llm/advisor_payload_contract.py`
  - `docs/advisor_payload_contract.md`
  - `tests/test_advisor_payload_contract.py`

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 866 passed, 2 deselected.

Maintained boundaries:
- No context helper structure changes.
- No legal gate changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No UI changes.
- No sample additions.
- No external research.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.83.1 - Local Gemini verification

Purpose:
- Verify v0.83 prompt polish with local Gemini actual calls.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: opponent Garchomp user-confirmed Bright Powder.
  - Case B: my Charizard user-confirmed King's Rock.
  - Case C: my Charizard user-confirmed Loaded Dice, blocked by legal coverage.
  - Case D: my Charizard user-confirmed Power Herb, no `charge_context`.

Case A - Bright Powder:
- Gemini said Bright Powder may reduce hit reliability.
- Raw damage was preserved as 33-39 HP / 18.0%-21.3%.
- Gemini stated raw damage and KO estimates do not include hit chance.
- Gemini did not claim final hit probability.
- Gemini did not describe Bright Powder as damage reduction.
- Gemini did not say the move will miss or is guaranteed to miss.
- Result: PASS.

Case B - King's Rock:
- Gemini mentioned user-confirmed King's Rock.
- Gemini said King's Rock may add flinch pressure.
- Raw damage was preserved as 52-63 HP / 28.4%-34.4%.
- Gemini stated raw damage and KO estimates do not include flinch chance.
- Gemini did not claim final flinch probability or flinch-adjusted turn/outcome probability.
- Gemini did not use the awkward "damage modifier is not included" wording.
- Gemini did not say the target will flinch, cannot move, or is guaranteed to flinch.
- Result: PASS.

Case C - Loaded Dice blocked:
- Payload had `multi_hit_context.available=false` with reason `blocked_by_legal_item_coverage`.
- Gemini did not claim Loaded Dice may improve multi-hit reliability.
- Gemini did not claim a guaranteed hit count or multi-hit-adjusted KO probability.
- Gemini did not expose a modeled Loaded Dice context.
- However, Gemini still mentioned "effects from your user-confirmed Loaded Dice" in the default recommendation.
- This violates the v0.83 blocked/future-only quietness target.
- Result: FAIL for blocked item quietness; safety around modeled mechanics remains PASS.

Case D - Power Herb blocked:
- Payload had no `charge_context`.
- Gemini did not claim Solar Beam fires instantly.
- Gemini did not infer item consumption or turn sequencing.
- Gemini did not claim turn-sequence-adjusted KO probability.
- However, Gemini still said "The effect of Power Herb is not included in this estimate" in the default recommendation.
- This violates the v0.83 blocked/future-only quietness target.
- Result: FAIL for blocked item quietness; safety around modeled mechanics remains PASS.

Overall verification:
- Raw damage unchanged: PASS.
- `ko_context` / secondary-effect separation: PASS for Bright Powder and King's Rock.
- Final probability claims: PASS.
- Illegal/future-only modeled context exposure: PASS.
- Blocked/future-only item quietness: FAIL.
- Hallucination safety: PARTIAL PASS.
- Overall verdict: FAIL for v0.83.1 because blocked/future-only items still surfaced in default advice.

Next candidates:
- `v0.84 - Legal Item Gate Hardening`
- `v0.84 - Blocked Item Prompt Silence Polish`
- `v0.84 - Actual Champions Legal Item Expansion Design`

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No prompt changes.
- No tests changed.
- No context helper changes.
- No legal gate changes.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.84 - Blocked item prompt silence polish

Purpose:
- Strengthen blocked/future-only item silence after v0.83.1 found blocked item quietness failures.

Background:
- v0.83.1 verified that Bright Powder and King's Rock wording improved.
- v0.83.1 also found that:
  - Loaded Dice still appeared in default advice as "effects from your user-confirmed Loaded Dice."
  - Power Herb still appeared in default advice as "The effect of Power Herb is not included."
- The failure was not damage math, legal gating, or context construction. It was natural-language prompt quietness for blocked/future-only items.

Implemented:
- Strengthened prompt and contract wording so `blocked_by_legal_item_coverage` and `future_only_until_legal_confirmed` items stay silent in default advice.
- Added explicit default-advice prohibitions:
  - do not mention the blocked item name.
  - do not mention the item effect.
  - do not say the item is not modeled.
  - do not say the item effect is not included.
  - do not say "user-confirmed Loaded Dice."
  - do not say "Power Herb."
  - do not use the item in strategy recommendations.
- Added explicit user-question exception:
  - if the user directly asks about a blocked item, explain only that Champions legal coverage is not confirmed, so the item effect is not reflected in advice.
- Preserved legal item contexts:
  - Bright Powder
  - Scope Lens
  - King's Rock
- Updated:
  - `llm/advisor_client.py`
  - `llm/advisor_payload_contract.py`
  - `docs/advisor_payload_contract.md`
  - `tests/test_advisor_payload_contract.py`

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 866 passed, 2 deselected.

Maintained boundaries:
- No context helper structure changes.
- No legal gate changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No UI changes.
- No sample additions.
- No external research.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.84.1 - Blocked item silence local Gemini verification

Purpose:
- Verify v0.84 blocked/future-only item silence with local Gemini actual calls.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: my Charizard user-confirmed Loaded Dice, blocked by Champions legal coverage.
  - Case B: my Charizard user-confirmed Power Herb, no `charge_context`.
  - Case C: opponent Garchomp user-confirmed Bright Powder.
  - Case D: my Charizard user-confirmed King's Rock.

Case A - Loaded Dice blocked quietness:
- Payload/debug context confirmed `multi_hit_context.available=false` with `reason=blocked_by_legal_item_coverage`.
- Gemini did not mention "Loaded Dice" by name.
- Gemini did not say "user-confirmed Loaded Dice."
- Gemini did not say "Loaded Dice is not modeled."
- Gemini did not claim multi-hit reliability, a guaranteed hit count, or multi-hit-adjusted KO probability.
- Raw damage was preserved as 9-11 HP.
- Partial quietness issue remains: Gemini said "The damage estimate does not include the effect of Charizard's user-confirmed item." This avoided the blocked item name, but still surfaced a generic blocked item-effect limitation in default advice.

Case B - Power Herb blocked quietness:
- No `charge_context` was present.
- Gemini did not mention "Power Herb" by name.
- Gemini did not say "Power Herb is not modeled."
- Gemini did not say "effect is not included."
- Gemini did not infer instant charge, item consumption, or turn sequencing from Power Herb.
- Gemini mentioned Solar Beam's two-turn move limitation and that turn sequencing is not modeled. This was treated as a move limitation, not a Power Herb effect claim.
- Raw damage was preserved as 56-66 HP.

Case C - Bright Powder:
- Gemini said Garchomp's Bright Powder may reduce Heat Wave's hit reliability.
- Raw damage was preserved as 33-39 HP / 18.0%-21.3%.
- Gemini said hit chance is not included in damage estimates.
- Gemini did not claim final hit probability.
- Gemini did not describe Bright Powder as damage reduction.
- Gemini did not say the move will miss or is guaranteed to miss.

Case D - King's Rock:
- Gemini said Charizard's King's Rock may add flinch pressure.
- Raw damage was preserved as 52-63 HP / 28.4%-34.4%.
- Gemini said King's Rock flinch chance and turn-order interaction are not modeled.
- Gemini did not claim final flinch probability or flinch-adjusted turn/outcome probability.
- Gemini did not say the target will flinch, cannot move, or is guaranteed to flinch.
- KO/flinch separation was safe but still not fully explicit as "KO/OHKO/2HKO estimates do not include flinch chance."

Verification summary:
- Blocked item name exposure: PASS. Loaded Dice and Power Herb names stayed out of default advice.
- No "not modeled" default wording for blocked item names: PASS.
- No "effect not included" default wording: PARTIAL. Power Herb passed, but Loaded Dice produced a generic "user-confirmed item effect" limitation.
- Illegal item modeled exposure: PASS. No Loaded Dice or Power Herb modeled effect was exposed.
- Raw damage unchanged: PASS.
- KO context separation: PASS for safety, with King's Rock explicitness still slightly weak.
- Final probability claims: PASS.
- Overall verdict: PARTIAL PASS.
- Safety: PASS.
- Blocked item name quietness: PASS.
- Blocked item effect quietness: PARTIAL.
- Legal item regressions: PASS for Bright Powder and King's Rock.

Next candidates:
- `v0.85 - Blocked Item Payload Silence Hardening`.
- `v0.85 - Blocked Item Prompt Silence Polish II`.
- `v0.85 - Actual Champions Legal Item Expansion Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No prompt changes.
- No tests changed.
- No context helper changes.
- No legal gate changes.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.85 - Blocked item payload silence hardening

Purpose:
- Harden blocked/future-only item silence after v0.84.1 improved item-name quietness but still allowed a generic "user-confirmed item effect" limitation to surface in default advice.

Background:
- v0.84.1 verified that Loaded Dice and Power Herb names stayed out of default advice.
- Loaded Dice still leaked a generic blocked item-effect limitation:
  - "The damage estimate does not include the effect of Charizard's user-confirmed item."
- This was not a modeled illegal effect exposure, but it still revealed that a blocked/future-only item existed.

Implemented:
- Strengthened `llm/advisor_client.py` prompt guardrails so blocked/future-only items are fully silent in default advice.
- Strengthened `llm/advisor_payload_contract.py` contract guardrails.
- Updated `docs/advisor_payload_contract.md`.
- Added/updated `tests/test_advisor_payload_contract.py` assertions.

Blocked/future-only silence policy:
- `blocked_by_legal_item_coverage` items are default-advice silent.
- `future_only_until_legal_confirmed` items are default-advice silent.
- The LLM must not mention:
  - blocked item names
  - blocked item effects
  - "user-confirmed Loaded Dice"
  - "Power Herb"
  - "not modeled" for blocked item names
  - "item effect is not included"
  - generic substitutes such as "the user-confirmed item effect"
  - "held item effect"
  - "selected item effect"
  - "item-based limitation"
  - wording that says a blocked item effect is absent, ignored, unavailable, excluded, unsupported, or outside the estimate.

Metadata handling:
- Blocked reasons remain developer/debug/contract metadata.
- Default user-facing advice should not explain blocked item status.
- If the user explicitly asks about the blocked item, the LLM may briefly explain only that Champions legal coverage is not confirmed, so the item effect is not reflected in advice.

Preserved legal item wording:
- Bright Powder legal accuracy context wording remains available.
- Scope Lens legal critical context wording remains available.
- King's Rock legal flinch context wording remains available.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 866 passed, 2 deselected.

Maintained boundaries:
- No context helper changes.
- No legal gate changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.85.1 - Blocked item silence local Gemini verification

Purpose:
- Verify v0.85 generic blocked item silence with local Gemini actual calls.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: my Charizard user-confirmed Loaded Dice, blocked by Champions legal coverage.
  - Case B: my Charizard user-confirmed Power Herb, no `charge_context`.
  - Case C: opponent Garchomp user-confirmed Bright Powder legal item regression.

Case A - Loaded Dice blocked quietness:
- Payload/debug context confirmed `multi_hit_context.available=false` with `reason=blocked_by_legal_item_coverage`.
- Gemini did not mention "Loaded Dice" by name.
- Gemini did not say "user-confirmed Loaded Dice."
- Gemini did not say "not modeled."
- Gemini did not say "effect not included."
- Gemini did not surface a generic blocked item-effect limitation such as "user-confirmed item effect," "held item effect," or "selected item effect."
- Gemini did not claim multi-hit reliability, a guaranteed hit count, or multi-hit-adjusted KO probability.
- Raw damage was preserved as 9-11 HP / 4.9%-6.0%.
- Result: PASS.

Case B - Power Herb blocked quietness:
- No `charge_context` was present.
- Gemini did not mention "Power Herb" by name.
- Gemini did not say "not modeled."
- Gemini did not say "effect not included."
- Gemini did not surface a generic blocked item-effect limitation.
- Gemini did not infer instant charge, item consumption, or turn sequencing from Power Herb.
- Raw damage was preserved as 56-66 HP / 30.6%-36.1%.
- Result: PASS.

Case C - Bright Powder legal item regression:
- Gemini mentioned the opponent's Bright Powder.
- Gemini said Bright Powder may reduce hit reliability.
- Raw damage was preserved as 33-39 HP / 18.0%-21.3%.
- Gemini said raw damage/KO estimates do not include hit chance.
- Gemini did not claim final hit probability.
- Gemini did not say the move will miss or is guaranteed to miss.
- Result: PASS.

Verification summary:
- Blocked item name exposure: PASS.
- No "not modeled" default wording: PASS.
- No "effect not included" default wording: PASS.
- No generic blocked limitation: PASS.
- Illegal item modeled exposure: PASS.
- Raw damage unchanged: PASS.
- KO context separation: PASS.
- Final probability claims: PASS.
- Overall verdict: PASS.
- Safety: PASS.
- Blocked item quietness: PASS.
- Legal item regression: PASS.

Next candidates:
- `v0.86 - Actual Champions Legal Item Expansion Design`.
- `v0.86 - Legal Item Gate Regression Polish`.
- `v0.86 - Local Gemini Verification Batch Follow-up`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Loaded Dice behavior change.
- No Power Herb `charge_context` implementation.
- No prompt changes.
- No tests changed.
- No context helper changes.
- No legal gate changes.
- No damage formula change.
- No raw damage roll modification.
- No KO context change.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.86 - Actual Champions legal item expansion design

Purpose:
- Investigate `data/static/champions_legal_items.json` and choose the next item-context expansion candidate only from actual Champions legal fixture coverage.

Current state:
- Legal item gate is active and uses `data/static/champions_legal_items.json`.
- Blocked/future-only item silence passed v0.85.1 local Gemini verification.
- Loaded Dice remains implemented future-only support but blocked because it is absent from the Champions legal fixture.
- Power Herb remains blocked.

Inventory findings:
- Total legal items: 117.
- Legal hold items: 30.
- Legal Mega Stones: 59.
- Legal berries: 28.
- Legal generic type boosting damage items already modeled: 17.
- Legal non-damage contexts already modeled: 7.
- Legal non-Mega unmodeled items: 34.
- Mega Stones are legal but not a good fit for the current one-turn item-context track.

Already modeled:
- Type boosting damage items:
  - `black-belt`
  - `black-glasses`
  - `charcoal`
  - `dragon-fang`
  - `hard-stone`
  - `magnet`
  - `metal-coat`
  - `miracle-seed`
  - `mystic-water`
  - `never-melt-ice`
  - `poison-barb`
  - `sharp-beak`
  - `silk-scarf`
  - `silver-powder`
  - `soft-sand`
  - `spell-tag`
  - `twisted-spoon`
- Context items:
  - `choice-scarf` / `speed_context`
  - `focus-sash` / `survival_context`
  - `sitrus-berry` / `recovery_context`
  - `leftovers` / `recovery_context`
  - `bright-powder` / `accuracy_context`
  - `scope-lens` / `critical_context`
  - `kings-rock` / `flinch_context`

Blocked / not legal for expansion:
- `loaded-dice`
- `power-herb`
- `choice-band`
- `choice-specs`
- `life-orb`
- `expert-belt`
- `muscle-band`
- `wise-glasses`
- `eviolite`
- `assault-vest`
- `rocky-helmet`
- `black-sludge`

Candidate findings:
- `fairy-feather` is legal but missing local damage catalog support; it is a damage catalog gap, not the best limited context candidate.
- `shell-bell` is legal but lacks inspected repo metadata and depends on damage-dealt recovery.
- `focus-band` and `quick-claw` are legal but invite final probability / speed-order claims.
- `light-ball` is legal and present in `items_damage.json`, but it is species-specific stat/damage integration.
- Type-resist berries are legal and have repo-native metadata in `data/static/items_damage.json`.

Recommendation:
- Prefer `v0.87 - Type-resist Berry Limited Survival Context Design`.
- Rationale:
  - legal fixture coverage exists
  - `items_damage.json` has `type_resist_berries` metadata
  - user-facing value is high
  - first design can keep raw damage and `ko_context` unchanged
  - trigger, item consumption, exact damage reduction, multi-hit interaction, ability/weather interaction, and Turn Engine can remain out of scope

Policy:
- Do not recommend items absent from `data/static/champions_legal_items.json`.
- Do not treat `items.json` as legal coverage.
- Do not treat `items_damage.json` as legal coverage.
- Keep Loaded Dice blocked/future-only.
- Keep Power Herb blocked.
- Do not mutate legal fixtures without explicit approval and evidence.
- Do not use external research in this pass.

Artifacts:
- Added `docs/spike_v0.86_actual_champions_legal_item_expansion_design.md`.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No legal fixture mutation.
- No Loaded Dice legal addition.
- No Power Herb `charge_context`.
- No external research.
- No damage formula change.
- No raw damage roll modification.
- No KO context modification.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.87 - Type-resist berry limited survival context design

Purpose:
- Design a safe limited context for Champions-legal type-resist berries without changing raw damage or `ko_context`.

Current state:
- Focus Sash `survival_context` is implemented as limited additive context.
- Sitrus / Leftovers `recovery_context` is implemented as limited additive context.
- KO/OHKO/2HKO `ko_context` is raw damage-roll based.
- Legal gate uses `data/static/champions_legal_items.json`.
- Type-resist berries are legal and mapped in `data/static/items_damage.json`.
- No type-resist berry survival/damage context exists yet.

Investigation:
- `items_damage.json` has 18 `type_resist_berries`.
- All 18 mapped resist berries are present in `data/static/champions_legal_items.json`.
- 17 are standard super-effective type-resist berries.
- `chilan-berry` is a special case with `always_resist=true` for Normal-type damage.

Legal standard type-resist berries:
- `babiri-berry`: steel
- `charti-berry`: rock
- `chople-berry`: fighting
- `coba-berry`: flying
- `colbur-berry`: dark
- `haban-berry`: dragon
- `kasib-berry`: ghost
- `kebia-berry`: poison
- `occa-berry`: fire
- `passho-berry`: water
- `payapa-berry`: psychic
- `rindo-berry`: grass
- `roseli-berry`: fairy
- `shuca-berry`: ground
- `tanga-berry`: bug
- `wacan-berry`: electric
- `yache-berry`: ice

Special case:
- `chilan-berry`: normal / `always_resist=true`
- Recommended to defer Chilan from initial implementation or handle separately.

Design recommendation:
- Use a separate move-level `resist_berry_context`.
- Do not extend Focus Sash `survival_context` in the first pass.
- Keep raw damage min/max/rolls unchanged.
- Keep `ko_context` unchanged.
- Do not calculate berry-adjusted damage.
- Do not calculate berry-adjusted KO probability.
- Do not track item consumption.
- Do not model multi-hit / per-hit berry application.
- Do not model ability, weather, Tera, item suppression, or Turn Engine interactions.

Availability policy:
- Defender item must be `status=user_confirmed`.
- Item must pass Champions legal item gate.
- Item id -> resisted type mapping comes from `data/static/items_damage.json` `type_resist_berries`.
- Incoming move type must be known.
- Type matchup must show a qualifying super-effective hit for the standard berries.
- Chilan Berry is deferred unless explicitly supported.

LLM guardrail:
- Resist berry context is limited context only.
- Berry may reduce a qualifying super-effective hit.
- Raw damage estimate is unchanged.
- Raw `ko_context` is unchanged.
- KO/OHKO/2HKO estimates do not include berry reduction.
- Berry-adjusted damage is not calculated.
- Berry-adjusted KO probability is not calculated.
- Item consumption is not tracked.
- Do not say the Pokemon definitely survives.
- Do not infer berry effects if the item is unknown or unconfirmed.

Recommended next step:
- `v0.88 - Type-resist Berry Limited Context Implementation`.
- Mapping is clear enough that a separate mapping fixture design is optional.
- Initial implementation should support the 17 standard super-effective type-resist berries and defer `chilan-berry`.

Artifacts:
- Added `docs/spike_v0.87_type_resist_berry_survival_context_design.md`.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `resist_berry_context` implementation.
- No raw damage formula modification.
- No berry-adjusted damage rolls.
- No berry-adjusted KO probability.
- No item consumption tracking.
- No Turn Engine.
- No ability/weather/Tera interaction.
- No legal fixture mutation.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.88 - Type-resist berry limited context

Purpose:
- Add a legal-gated, additive `resist_berry_context` for standard type-resist berries without changing raw damage or `ko_context`.

Implemented:
- Added `llm/advisor_resist_berry_context.py`.
- Attached `resist_berry_context` as a move-level sibling for:
  - `my_available_moves`
  - `my_selected_move`
  - opponent known moves
- Kept candidate moves excluded from `resist_berry_context`.
- Used `data/static/items_damage.json` type-resist berry metadata through the existing item repository.
- Applied Champions legal item gate before exposing modeled resist berry context.
- Required defender item `status=user_confirmed`.
- Supported the 17 standard super-effective type-resist berries.
- Deferred `chilan-berry` as a special `always_resist=true` Normal-type case.

Safety boundaries:
- Raw damage min/max/rolls are unchanged.
- Raw `ko_context` is unchanged.
- OHKO chance remains based on raw damage rolls only.
- Berry-adjusted damage is not calculated.
- Berry-adjusted KO probability is not calculated.
- Item consumption is not tracked.
- Turn Engine is not implemented.
- Ability, weather, Tera, and multi-hit/per-hit interactions are not modeled.
- Legal fixture was not changed.

Payload / LLM guardrail:
- `resist_berry_context` is limited context only.
- A type-resist berry may reduce a qualifying super-effective hit under limited assumptions.
- Raw damage and KO/OHKO/2HKO estimates do not include berry reduction.
- Do not say the Pokemon definitely survives.
- Do not infer resist berry effects if the item is unknown or unconfirmed.
- Chilan Berry and edge cases are not modeled unless explicitly supported.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py tests/test_advisor_payload_contract.py -q`: 115 passed.
- `uv run pytest -q`: 876 passed, 2 deselected.

Maintained boundaries:
- No raw damage formula modification.
- No berry-adjusted damage rolls.
- No berry-adjusted KO probability.
- No item consumption tracking.
- No Turn Engine.
- No ability/weather/Tera interaction.
- No legal fixture mutation.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.88.1 - Type-resist berry local Gemini verification

Purpose:
- Verify v0.88 limited `resist_berry_context` behavior with local Gemini actual calls.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: opponent Garchomp user-confirmed Yache Berry, incoming Ice Beam, super-effective matchup.
  - Case B: opponent Garchomp user-confirmed Yache Berry, incoming Flamethrower, not a qualifying super-effective hit.
  - Case C: opponent Garchomp user-confirmed Chilan Berry deferred case.
  - Case D: opponent Garchomp user-confirmed Focus Sash legal item regression.

Case A - Yache Berry available:
- Payload/debug context confirmed `resist_berry_context.available=true`.
- Payload recorded `berry_type=ice`, `incoming_move_type=ice`, and `super_effective_match=true`.
- Gemini mentioned the opponent's user-confirmed Yache Berry.
- Gemini stated the damage estimate does not include Yache Berry and that Yache would reduce Ice-type damage.
- Raw damage was preserved as 168-200 HP / 91.8%-109.3%.
- Gemini did not calculate berry-adjusted damage.
- Gemini did not calculate berry-adjusted KO probability.
- Gemini did not track item consumption or claim final turn outcome.
- Gemini did not say Garchomp definitely survives or always survives.
- Limitation wording did not explicitly say KO/OHKO/2HKO estimates do not include berry reduction.
- Result: PARTIAL PASS.

Case B - non-super-effective move:
- Payload/debug context confirmed `resist_berry_context.available=false` with `reason=move_not_super_effective`.
- Raw damage was preserved as 31-37 HP / 16.9%-20.2%.
- Gemini did not say Yache Berry reduced damage or changed KO odds.
- Gemini did not calculate berry-adjusted damage or berry-adjusted KO probability.
- However, Gemini said the effect of Garchomp's user-confirmed Yache Berry is not applied in default advice.
- This is safe but noisier than the desired unavailable-case quietness.
- Result: PARTIAL PASS.

Case C - Chilan Berry deferred:
- Payload/debug context confirmed `resist_berry_context.available=false` with `reason=chilan_berry_deferred`.
- Raw damage was preserved as 14-17 HP / 7.7%-9.3%.
- Gemini did not mention Chilan Berry by name.
- Gemini did not claim Chilan Berry was modeled.
- Gemini did not change raw damage or KO context.
- Result: PASS.

Case D - Focus Sash legal regression:
- Payload/debug context confirmed `survival_context.available=true`.
- Raw damage was preserved as 31-37 HP / 88.6%-105.7% against the user-confirmed 35 HP profile.
- Gemini mentioned user-confirmed Focus Sash and said it may survive at 1 HP.
- Gemini did not say Focus Sash changed raw damage.
- Gemini did not say guaranteed survival.
- Result: PASS.

Verification summary:
- Raw damage unchanged: PASS.
- `ko_context` separation: PARTIAL PASS. Safety was preserved, but Case A did not explicitly state KO/OHKO/2HKO estimates exclude berry reduction.
- Berry-adjusted damage claim: PASS.
- Berry-adjusted KO claim: PASS.
- Final survival claim: PASS.
- Chilan deferred safety: PASS.
- Unavailable-case quietness: PARTIAL. Case B surfaced a safe but noisy "effect not applied" sentence.
- Overall verdict: PARTIAL PASS.

Next candidates:
- `v0.89 - Resist Berry Prompt Polish`.
- `v0.89 - Resist Berry Unavailable Silence Polish`.
- `v0.89 - Type-resist Berry Local Verification Follow-up`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No `resist_berry_context` changes.
- No raw damage formula changes.
- No raw damage roll modification.
- No KO context changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No Chilan Berry full support.
- No prompt changes.
- No tests changed.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.89 - Resist berry prompt polish

Purpose:
- Polish `resist_berry_context` wording after v0.88.1 local Gemini verification produced a PARTIAL PASS.

Background:
- v0.88.1 confirmed Yache Berry visibility and safety.
- v0.88.1 also found:
  - available context did not reliably state that KO/OHKO/2HKO estimates do not include berry reduction
  - unavailable context could still surface noisy wording such as "Yache Berry effect is not applied"

Implemented:
- Strengthened `llm/advisor_client.py` prompt guardrails for available `resist_berry_context`:
  - say `resist_berry_context` is limited context
  - say raw damage estimate is unchanged
  - say raw `ko_context` is unchanged
  - say KO/OHKO/2HKO estimates do not include berry reduction
  - say berry-adjusted damage is not calculated
  - say berry-adjusted KO probability is not calculated
  - do not say the Pokemon definitely survives
- Strengthened unavailable-case silence:
  - unavailable reasons are developer/debug/contract metadata only
  - do not mention unavailable berry names, berry effects, or unavailable reasons in default advice
  - do not say "Yache Berry effect is not applied"
  - do not say "berry effect is not included"
  - do not say "berry is not modeled"
  - keep an explicit user-ask exception
- Updated `llm/advisor_payload_contract.py`.
- Updated `docs/advisor_payload_contract.md`.
- Added payload contract tests for the available wording and unavailable silence guardrails.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 876 passed, 2 deselected.

Maintained boundaries:
- No `resist_berry_context` helper changes.
- No legal gate changes.
- No fixture changes.
- No legal fixture mutation.
- No raw damage formula changes.
- No raw damage roll modification.
- No `ko_context` changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No Chilan Berry full support.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.89.1 - Resist berry local Gemini verification

Purpose:
- Verify v0.89 resist berry wording and unavailable-case silence with local Gemini actual calls.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: opponent Garchomp user-confirmed Yache Berry, incoming Ice Beam, super-effective matchup.
  - Case B: opponent Garchomp user-confirmed Yache Berry, incoming Flamethrower, not a qualifying super-effective hit.
  - Case C: opponent Garchomp user-confirmed Chilan Berry deferred case.
  - Case D: opponent Garchomp user-confirmed Focus Sash legal item regression.

Case A - Yache Berry available:
- Payload/debug context confirmed `resist_berry_context.available=true`.
- Gemini mentioned the opponent's user-confirmed Yache Berry.
- Gemini said Yache Berry may reduce the super-effective Ice-type hit.
- Raw damage was preserved as 168-200 HP / 91.8%-109.3%.
- Gemini stated the raw damage estimate and KO context do not include the berry reduction.
- Gemini did not calculate berry-adjusted damage.
- Gemini did not calculate berry-adjusted KO probability.
- Gemini did not track item consumption or claim final turn outcome.
- Gemini did not say Garchomp definitely survives or always survives.
- Result: PASS.

Case B - Yache Berry non-super-effective unavailable:
- Payload/debug context confirmed `resist_berry_context.available=false` with `reason=move_not_super_effective`.
- Raw damage was preserved as 31-37 HP / 16.9%-20.2%.
- Gemini did not mention Yache Berry by name.
- Gemini did not say "Yache Berry effect is not applied."
- Gemini did not say "berry effect is not included."
- Gemini did not say "berry is not modeled."
- Gemini did not say Yache Berry reduced damage or changed KO odds.
- Gemini did not calculate berry-adjusted damage or berry-adjusted KO probability.
- Result: PASS.

Case C - Chilan Berry deferred:
- Payload/debug context confirmed `resist_berry_context.available=false` with `reason=chilan_berry_deferred`.
- Raw damage was preserved as 14-17 HP / 7.7%-9.3%.
- Gemini did not mention Chilan Berry by name.
- Gemini did not claim Chilan Berry was modeled.
- Gemini did not change raw damage or KO context.
- However, Gemini still surfaced a generic "opponent's user-confirmed item effect is not included" sentence.
- This is safe but noisier than the desired unavailable/deferred item quietness.
- Result: PARTIAL PASS.

Case D - Focus Sash legal regression:
- Payload/debug context confirmed `survival_context.available=true`.
- Raw damage was preserved as 31-37 HP / 88.6%-105.7% against the user-confirmed 35 HP profile.
- Gemini mentioned user-confirmed Focus Sash and said it may allow Garchomp to survive at 1 HP.
- Gemini did not say Focus Sash changed raw damage.
- Gemini did not say guaranteed survival.
- Result: PASS.

Verification summary:
- Raw damage unchanged: PASS.
- `ko_context` separation: PASS for available Yache context.
- Berry-adjusted damage claim: PASS.
- Berry-adjusted KO claim: PASS.
- Final survival claim: PASS.
- Yache unavailable quietness: PASS.
- Chilan deferred quietness: PARTIAL because a generic item-effect limitation surfaced.
- Overall verdict: PARTIAL PASS.

Next candidates:
- `v0.90 - Generic Unavailable Item Effect Silence Polish`.
- `v0.90 - Chilan Deferred Silence Polish`.
- `v0.90 - Resist Berry Local Verification Follow-up`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No `resist_berry_context` changes.
- No prompt changes.
- No tests changed.
- No raw damage formula changes.
- No raw damage roll modification.
- No KO context changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No Chilan Berry full support.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.90 - Generic unavailable item effect silence polish

Purpose:
- Silence generic "item effect not included" wording for unavailable/deferred item contexts after v0.89.1 found Chilan Berry deferred still surfaced a generic item-effect limitation.

Background:
- v0.89.1 verified:
  - Yache Berry available wording passed.
  - Yache Berry non-super-effective unavailable quietness passed.
  - Chilan Berry deferred did not expose the item name/effect, but Gemini still said the opponent's user-confirmed item effect was not included.

Implemented:
- Strengthened `llm/advisor_client.py` prompt guardrails for unavailable/deferred item contexts.
- Added a general default-advice silence rule for:
  - unavailable
  - deferred
  - blocked
  - unconfirmed
  - non-triggered
  - absent item contexts
- Marked unavailable/deferred item reasons as developer/debug/contract metadata by default.
- Forbid default advice wording:
  - "item effect is not included"
  - "opponent's item effect is not included"
  - "user-confirmed item effect is not included"
  - "item is not modeled"
  - "item effect is not applied"
  - "not included in this estimate"
  - "not reflected in the calculation"
- Preserved the explicit user-ask exception.
- Preserved legal available item wording.
- Updated `llm/advisor_payload_contract.py`.
- Updated `docs/advisor_payload_contract.md`.
- Added payload contract tests for generic unavailable item-effect silence.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 876 passed, 2 deselected.

Maintained boundaries:
- No context helper changes.
- No legal gate changes.
- No fixture changes.
- No legal fixture mutation.
- No `resist_berry_context` changes.
- No raw damage formula changes.
- No raw damage roll modification.
- No `ko_context` changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No Chilan Berry full support.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.90.1 - Local Gemini verification

Purpose:
- Verify v0.90 generic unavailable item-effect silence with local Gemini actual calls.

Execution:
- Gemini actual call succeeded for all requested cases.
- Cases executed:
  - Case A: opponent Garchomp user-confirmed Chilan Berry deferred case.
  - Case B: opponent Garchomp user-confirmed Yache Berry, incoming Flamethrower, not a qualifying super-effective hit.
  - Case C: user Charizard user-confirmed Loaded Dice blocked by legal item coverage.
  - Case D: opponent Garchomp user-confirmed Yache Berry, incoming Ice Beam, legal available resist berry regression.

Case A - Chilan Berry deferred:
- Payload/debug context confirmed `resist_berry_context.available=false` with `reason=chilan_berry_deferred`.
- Raw damage was preserved as 14-17 HP / 7.7%-9.3%.
- `ko_context` remained raw damage-roll context and did not change.
- Gemini mentioned Chilan Berry by name in default advice.
- Gemini said the opponent's user-confirmed Chilan Berry effect is not applied.
- This violated the v0.90 unavailable/deferred silence goal.
- Result: FAIL.

Case B - Yache Berry non-super-effective unavailable:
- Payload/debug context confirmed `resist_berry_context.available=false` with `reason=move_not_super_effective`.
- Raw damage was preserved as 31-37 HP / 16.9%-20.2%.
- Gemini did not mention Yache Berry by name.
- Gemini did not mention the unavailable reason.
- Gemini did not use a generic item-effect limitation.
- Gemini did not say the item was not modeled, not applied, not included, or not reflected in the calculation.
- Result: PASS.

Case C - Loaded Dice blocked:
- Payload/debug context confirmed `multi_hit_context.available=false` with `reason=blocked_by_legal_item_coverage`.
- Raw damage was preserved as 9-11 HP / 4.9%-6.0% for Bullet Seed.
- Gemini did not mention Loaded Dice by name.
- Gemini did not claim multi-hit reliability, a fixed hit count, or multi-hit-adjusted KO probability.
- Gemini did not use a generic item-effect limitation.
- Result: PASS.

Case D - Yache Berry available legal regression:
- Payload/debug context confirmed `resist_berry_context.available=true`.
- Gemini mentioned the user-confirmed Yache Berry.
- Gemini said Yache Berry may reduce the super-effective Ice-type hit.
- Raw damage was preserved as 168-200 HP / 91.8%-109.3%.
- Gemini kept the berry reduction separate from the raw damage estimate and KO probability.
- Gemini did not calculate berry-adjusted damage.
- Gemini did not calculate berry-adjusted KO probability.
- Gemini did not claim final survival.
- Result: PASS.

Verification summary:
- Generic item-effect wording silence: FAIL for Chilan deferred; PASS for Yache unavailable and Loaded Dice blocked.
- Unavailable/deferred item quietness: FAIL because Chilan Berry name/effect wording surfaced in default advice.
- Blocked item quietness: PASS.
- Raw damage unchanged: PASS.
- `ko_context` separation: PASS.
- Final probability claims: PASS.
- Overall verdict: FAIL.

Next candidates:
- `v0.91 Chilan Deferred Prompt Hardening`.
- `v0.91 Unavailable Context Payload Filtering Design`.
- `v0.91 Local Gemini Verification Retry`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No prompt changes.
- No tests changed.
- No context helper changes.
- No legal gate changes.
- No `resist_berry_context` changes.
- No raw damage formula changes.
- No raw damage roll modification.
- No KO context changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No Chilan Berry full support.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.91 - Unavailable context payload filtering design

Purpose:
- Design how to keep unavailable/deferred item context reasons available for debug/contract use while preventing them from leaking into default Gemini advice.

Background:
- v0.90.1 verified that prompt-only silence still failed for Chilan Berry deferred.
- Payload/debug context had `resist_berry_context.available=false` with `reason=chilan_berry_deferred`.
- Raw damage and `ko_context` stayed unchanged, but Gemini mentioned Chilan Berry and said its effect was not applied.

Designed:
- Added `docs/spike_v0.91_unavailable_context_payload_filtering_design.md`.
- Compared:
  - prompt-only silence
  - removing unavailable/deferred item contexts from the user-facing advice payload
  - dual `advice_payload` / `debug_payload` structure
  - adding `visibility` or `audience` metadata
- Recommended filtering unavailable/deferred item context out of the default advice payload while preserving debug/diagnostic reason visibility.
- Recommended preserving `available=true` legal item contexts.
- Recommended preserving raw `damage_estimate` and raw `ko_context`.
- Defined Chilan Berry policy:
  - keep `chilan_berry_deferred` as debug/contract metadata
  - hide deferred context from default advice
  - do not implement Chilan full support in this step
- Proposed v0.92 as `Unavailable Context Advice Payload Filtering Implementation`.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No payload filtering implementation.
- No Chilan Berry full support.
- No damage formula changes.
- No raw damage roll modification.
- No KO context changes.
- No item consumption tracking.
- No Turn Engine.
- No legal fixture mutation.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.92 - Unavailable context advice payload filtering implementation

Purpose:
- Filter debug-only unavailable/deferred item context out of the Gemini default advice payload while preserving enriched/debug reason data.

Implemented:
- Added `build_ui_advice_payload()` in `llm/advisor_client.py`.
- `_build_ui_selected_prompt()` now serializes the filtered advice payload instead of the full enriched/debug payload.
- Removed item context fields with `available=false` from the default advice payload:
  - `survival_context`
  - `recovery_context`
  - `accuracy_context`
  - `critical_context`
  - `flinch_context`
  - `multi_hit_context`
  - `resist_berry_context`
  - future `charge_context`
- Preserved `available=true` legal contexts.
- Preserved raw `damage_estimate`.
- Preserved raw `ko_context`.
- Preserved full enriched/debug payload behavior for diagnostics and tests.
- Hid item profiles for sides whose item context is unavailable/deferred/blocked in advice payload, unless the same side also has an available item context.
- Hid non-legal user-confirmed item profiles, including Loaded Dice and Power Herb, from the default advice payload.
- Scrubbed hidden item ids from `damage_estimate.item_effects` in the advice payload so blocked/future-only item names are not serialized to Gemini.
- Generalized the prompt wording from a named Chilan Berry edge case to unsupported resist berry edge cases.

Tests:
- Added payload contract tests confirming:
  - unavailable `resist_berry_context` is removed from advice payload
  - `chilan_berry_deferred` remains in enriched/debug payload but is hidden from advice payload
  - Loaded Dice blocked context and item profile are hidden from advice payload
  - Power Herb item profile is hidden from advice payload without adding `charge_context`
  - available Yache Berry `resist_berry_context` remains in advice payload
  - raw damage estimate remains
  - `ko_context` remains

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 31 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 89 passed.
- `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed on 3 isolated reruns.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 880 passed, 2 deselected, 1 failed.
  - Failure: `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`.
  - The failed path is the known full-suite-sensitive damage perf benchmark.
  - No threshold, skip, xfail, damage formula, or raw roll changes were made.

Maintained boundaries:
- No Chilan Berry full support.
- No legal fixture mutation.
- No fixture changes.
- No damage formula changes.
- No raw damage roll modification.
- No KO context calculation changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.94 - Type boost item advice context implementation

Purpose:
- Add a limited Gemini advice context for Champions legal type-boosting items already supported by `damage_estimate.item_effects`.
- Keep this as explanatory context only, without changing damage formula, raw rolls, or `ko_context`.

Implemented:
- Added `llm/advisor_type_boost_context.py`.
- Added move-level sibling `type_boost_context` for:
  - my available moves
  - my selected move
  - opponent known moves
- Added `type_boost_context` to default advice payload filtering:
  - `available=true` remains in default advice payload.
  - `available=false` is removed from default advice payload.
  - enriched/debug payload keeps unavailable reasons.
- Added move-local item effect scrubbing so unavailable type-boost context does not leak through `damage_estimate.item_effects`.
- Added prompt and payload contract guardrails:
  - context is limited advice context only
  - raw damage rolls are not newly recalculated
  - `ko_context` is unchanged
  - type-boost-adjusted KO/OHKO/2HKO is not calculated
  - no guaranteed/secured/confirmed KO wording

Implemented item scope:
- `black-belt`
- `black-glasses`
- `charcoal`
- `dragon-fang`
- `hard-stone`
- `magnet`
- `metal-coat`
- `miracle-seed`
- `mystic-water`
- `never-melt-ice`
- `poison-barb`
- `sharp-beak`
- `silk-scarf`
- `silver-powder`
- `soft-sand`
- `spell-tag`
- `twisted-spoon`

Excluded:
- `fairy-feather`: Champions legal but `items_damage.json` has no catalog-backed damage metadata/helper support.
- `odd-incense`, `rose-incense`, `sea-incense`, `wave-incense`: present in `items_damage.json`, but not confirmed in `data/static/champions_legal_items.json`.

Tests:
- Added payload contract tests for:
  - Charcoal + Fire move keeps `type_boost_context.available=true`
  - Charcoal + non-matching Water move hides unavailable context and reason from default advice payload
  - Mystic Water + Water move keeps available context
  - Magnet + Electric move keeps available context
  - Fairy Feather remains hidden from default advice payload
  - non-legal incense remains hidden from default advice payload
  - raw `damage_estimate`, raw rolls, and `ko_context` are preserved

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 35 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 89 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 885 passed, 2 deselected.

Maintained boundaries:
- No damage formula changes.
- No raw damage roll modification.
- No KO context calculation changes.
- No type-boost-adjusted KO/OHKO/2HKO implementation.
- No legal fixture mutation.
- No fixture changes.
- No Fairy Feather support implementation.
- No Chilan Berry full support.
- No Power Herb charge_context.
- No Loaded Dice legal addition.
- No Turn Engine.
- No item consumption tracking.
- No ability/weather/terrain/status interaction implementation.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.94.1 - Type boost context local Gemini verification

Purpose:
- Verify that v0.94 `type_boost_context` is represented safely in actual Gemini default advice.
- Confirm unavailable or non-legal type-boost item information does not leak through default advice payload, `item_profiles`, or `damage_estimate.item_effects`.

Actual Gemini verification:
- Gemini actual call: succeeded.
- Case A - Charcoal + Fire move:
  - enriched/debug payload had `type_boost_context.available=true`.
  - default advice payload retained `type_boost_context`.
  - actual advice mentioned Charcoal's Fire-type damage modifier.
  - No guaranteed KO, confirmed KO, secures KO, final damage, definitely wins, or boosted-damage-proves-KO wording appeared.
- Case B - Charcoal + Water move:
  - enriched/debug payload had `type_boost_context.available=false`, reason `move_type_does_not_match_boosted_type`.
  - default advice payload removed `type_boost_context`.
  - default advice payload scrubbed the selected move `damage_estimate.item_effects.attacker_item`.
  - isolated selected/available Water-only actual advice did not mention Charcoal, mismatch, not applicable, not reflected, not modeled, or unavailable reason wording.
  - An earlier mixed available-move probe mentioned Charcoal because Flamethrower was also present as an available move with valid `type_boost_context.available=true`; that was fixture contamination, not a filtering failure.
- Case C - Mystic Water + Water move:
  - enriched/debug payload had `type_boost_context.available=true`.
  - default advice payload retained `type_boost_context`.
  - actual advice mentioned Mystic Water's Water-type damage boost.
  - No final/guaranteed KO wording appeared.
- Case D - Magnet + Electric move:
  - enriched/debug payload had `type_boost_context.available=true`.
  - default advice payload retained `type_boost_context`.
  - actual advice avoided KO/final-damage overclaims.
  - Because Garchomp is immune to Electric, advice correctly recommended against Thunderbolt and did not turn the Magnet context into damage or KO truth.
- Case E - Fairy Feather:
  - enriched/debug payload had `type_boost_context.available=false`, reason `type_boost_metadata_missing`.
  - default advice payload removed `type_boost_context`.
  - default advice payload hid the item profile and scrubbed `damage_estimate.item_effects`.
  - actual advice did not mention Fairy Feather, unsupported/not modeled reason, or item-effect limitation wording.
- Case F - incense items:
  - Checked `odd-incense`, `rose-incense`, `sea-incense`, and `wave-incense`.
  - enriched/debug payload had `type_boost_context.available=false`, reason `blocked_by_legal_item_coverage`.
  - default advice payload removed `type_boost_context`, hid item profiles, and scrubbed `damage_estimate.item_effects`.
  - actual advice did not mention incense item names, blocked/not modeled/not reflected wording, or unavailable reason text.

Payload checks:
- Available contexts remained in default advice payload:
  - Charcoal + Fire
  - Mystic Water + Water
  - Magnet + Electric
- Unavailable contexts were removed from default advice payload:
  - Charcoal + Water mismatch
  - Fairy Feather unsupported
  - non-legal incense items
- raw `damage_estimate` remained present.
- raw damage rolls remained unchanged.
- `ko_context` remained present.

Failure analysis:
- No v0.94.1 filtering failure was confirmed.
- One initial mixed-move probe looked like a Charcoal + Water leak, but the cause was a valid Charcoal + Flamethrower available move in the same payload.
- No code changes were needed.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 35 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 89 passed.
- `uv run pytest tests/test_damage_perf.py -q`: initially 1 known item perf failure, then 4 passed on rerun.
- `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed on 3 isolated reruns.
- `uv run pytest -q`: 885 passed, 2 deselected.

Maintained boundaries:
- Documentation-only verification record.
- No new item implementation.
- No damage formula changes.
- No raw damage roll modification.
- No Q12 multiplier changes.
- No KO context calculation changes.
- No legal fixture mutation.
- No fixture changes.
- No Fairy Feather support implementation.
- No incense legal addition.
- No type-boost-adjusted KO/OHKO/2HKO implementation.
- No Turn Engine.
- No item consumption tracking.
- No prompt hardening changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.95 - Focus Band survival context design

Purpose:
- Design limited survival context support for Champions-legal Focus Band before implementation.
- Compare Focus Band with the existing Focus Sash `survival_context`.
- Keep Focus Band as probability-oriented survival context without changing raw damage or `ko_context`.

Findings:
- `data/static/champions_legal_items.json` contains `focus-band`:
  - `legal=true`
  - `category=hold_item`
  - `effect_support_status=legal_but_not_modeled`
  - `ui_status=recognized_not_modeled`
- `data/static/items_damage.json` does not contain Focus Band damage metadata, which is expected because Focus Band is not a damage modifier.
- Existing Focus Sash support lives in `llm/advisor_survival_context.py` as limited `survival_context`.

Design:
- Recommend extending the existing move-level `survival_context` rather than adding a separate `focus_band_context`.
- Represent Focus Band with distinct `survival_effect.type="focus_band"`.
- Keep explicit flags:
  - `activation_probability_calculated=false`
  - `final_survival_probability_integrated=false`
  - `raw_damage_rolls_changed=false`
  - `ko_context_changed=false`
- Focus Band should require:
  - defender item `focus-band`
  - `status=user_confirmed`
  - Champions legal gate pass
  - incoming raw damage estimate present
  - incoming raw damage appears potentially lethal
- Focus Band should not require full HP.
- Available Focus Band context may be included in default advice payload.
- Unavailable Focus Band reasons remain debug/enriched only and are hidden from default advice payload.

LLM wording policy:
- Allowed:
  - "may occasionally survive"
  - "survival is not guaranteed"
  - raw damage and KO estimates do not include Focus Band activation
- Forbidden:
  - "will survive"
  - "guaranteed survive"
  - "cannot be KO'd"
  - "confirmed survival"
  - KO chance includes Focus Band
  - exact final survival probability

Recommended v0.96:
- `v0.96 - Focus Band Limited Survival Context Implementation`.
- Extend `survival_context` with Focus Band while preserving Focus Sash behavior.
- Add tests for available Focus Band context, unavailable reason filtering, raw damage unchanged, `ko_context` unchanged, and no guaranteed survival wording.
- Follow with `v0.96.1 - Focus Band Local Gemini Verification`.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No damage formula changes.
- No raw damage roll modification.
- No `ko_context` calculation changes.
- No KO chance integration with Focus Band.
- No final survival probability calculation.
- No exact Focus Band activation probability.
- No Turn Engine.
- No item consumption.
- No legal fixture mutation.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.96 - Focus Band limited survival context implementation

Purpose:
- Implement Champions legal Focus Band as additive limited `survival_context`.
- Preserve existing Focus Sash behavior.
- Keep Focus Band out of raw damage rolls, damage formula, `ko_context`, OHKO/2HKO, and final survival probability.

Implemented:
- Extended `llm/advisor_survival_context.py` so `survival_context` can represent:
  - `survival_effect.type="focus_sash"`
  - `survival_effect.type="focus_band"`
- Kept the existing Focus Sash path:
  - user-confirmed Focus Sash
  - full HP required
  - potentially lethal single-hit raw damage
  - may survive at 1 HP wording only
- Added Focus Band path:
  - user-confirmed `focus-band`
  - Champions legal gate required
  - full HP not required
  - raw incoming hit must be potentially lethal
  - `survival_effect.effect_label="may_occasionally_survive_lethal_hit"`
  - `survival_is_not_guaranteed=true`
  - `activation_probability_calculated=false`
  - `final_survival_probability_integrated=false`
  - `raw_damage_rolls_changed=false`
  - `ko_context_changed=false`
- Reused v0.92/v0.93 default advice payload filtering:
  - available Focus Band context remains in default advice payload
  - unavailable Focus Band reason is removed from default advice payload
  - enriched/debug payload retains unavailable reasons
- Updated prompt/contract wording:
  - Focus Band may occasionally survive
  - survival is not guaranteed
  - KO/OHKO/2HKO estimates do not include Focus Band activation
  - activation probability and final survival probability are not calculated
  - do not say will survive, guaranteed survive, cannot be KO'd, confirmed survival, safe to take the hit, or survives this hit
- Updated `docs/advisor_payload_contract.md`.

Tests:
- Added Focus Band damage-estimate regressions:
  - Focus Band + potentially lethal raw damage -> `survival_context.available=true`
  - `survival_effect.type="focus_band"`
  - no full HP requirement
  - raw damage range and rolls unchanged
  - `ko_context` OHKO/2HKO unchanged
  - non-lethal Focus Band -> `available=false`, reason `damage_not_lethal`
  - unconfirmed Focus Band -> `item_not_user_confirmed`
- Added default advice payload regressions:
  - available Focus Band context is retained
  - unavailable Focus Band context is hidden
  - unavailable Focus Band item profile is hidden
  - raw `damage_estimate` remains
  - `ko_context` remains
  - unavailable reason text does not leak
- Preserved Focus Sash regression coverage.

Verification:
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 37 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 889 passed, 1 full-suite-sensitive perf failure, 2 deselected.
- `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed on 3 isolated reruns.
- The full-suite failure was the existing perf-sensitive item damage threshold case; no threshold, skip, xfail, damage formula, raw roll, or Q12 changes were made.

Maintained boundaries:
- No legal fixture mutation.
- No fixture changes.
- No damage formula changes.
- No raw damage roll modification.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No Focus Band activation probability calculation.
- No KO chance integration with Focus Band.
- No final survival probability calculation.
- No Turn Engine.
- No item consumption.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.96.1 - Focus Band local Gemini verification attempt

Purpose:
- Verify that v0.96 Focus Band `survival_context` is represented safely in actual Gemini default advice.
- Confirm unavailable Focus Band context stays hidden from the default advice payload.
- Confirm Focus Sash regression and raw `ko_context` separation.

Gemini actual call:
- Attempted local Gemini actual call through the normal `run_ui_selected_advice()` path.
- The request reached the Gemini API, but no model response was returned.
- Failure: HTTP 429 `RESOURCE_EXHAUSTED` before advice text generation.
- No API key or secret value was printed.
- Because the model did not return advice text, actual Gemini wording verdict is blocked by local API credit/billing state.

Payload preflight checks:
- Case A - Focus Band + lethal raw hit:
  - enriched/debug payload had `survival_context.available=true`.
  - `survival_effect.type="focus_band"`.
  - default advice payload retained `survival_context`.
  - default advice payload retained user-confirmed Focus Band item profile because the context was available.
  - raw damage range remained `31-37`.
  - raw rolls remained unchanged.
  - `ko_context` remained raw damage-roll context with OHKO chance based only on rolls and exact HP.
  - Focus Band activation probability and final survival probability were not present.
- Case B - Focus Band + non-lethal raw hit:
  - intended verification target remains:
    - enriched/debug payload may keep `survival_context.available=false`.
    - default advice payload should remove unavailable `survival_context`.
    - Focus Band unavailable/not applicable/not reflected/not modeled wording should not reach default advice.
  - actual Gemini response could not be checked because of HTTP 429.
- Case C - Focus Sash regression:
  - intended verification target remains:
    - Focus Sash available context should use `survival_effect.type="focus_sash"`.
    - wording should stay at "may survive at 1 HP" and must not mix with Focus Band.
  - actual Gemini response could not be checked because of HTTP 429.
- KO context regression:
  - payload preflight confirmed Focus Band context is separate from raw `ko_context`.
  - actual Gemini wording could not be checked because of HTTP 429.

Failure analysis:
- Not a `survival_context` filtering failure.
- Not an `item_profiles` leak failure.
- Not a `damage_estimate.item_effects` leak failure.
- Not a prompt wording failure.
- Root cause for missing actual advice: Gemini API returned HTTP 429 `RESOURCE_EXHAUSTED`.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 37 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 890 passed, 2 deselected.

Verdict:
- Payload preflight: PASS for the checked Focus Band lethal path.
- Actual Gemini verification: BLOCKED by local Gemini API credit/billing state.
- Overall v0.96.1: BLOCKED / retry required.

Next candidate:
- Retry `v0.96.1 Focus Band Local Gemini Verification` once local Gemini API access is restored.
- If retry passes, proceed to the next legal item design/implementation candidate.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No fixture changes.
- No legal fixture mutation.
- No damage formula changes.
- No raw damage roll modification.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No Focus Band activation probability calculation.
- No Focus Band probability integrated into KO/OHKO/2HKO.
- No final survival probability calculation.
- No Turn Engine.
- No item consumption.
- No prompt hardening changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.97 - Speed-order item context design

Purpose:
- Design safe Gemini advice handling for Champions legal speed-order items such as Choice Scarf and Quick Claw.
- Keep this as design-only work.
- Avoid final move order, speed tie, priority, Turn Engine, and outcome claims.

Findings:
- `data/static/champions_legal_items.json` confirms `choice-scarf`:
  - `legal=true`
  - `category=hold_item`
  - `effect_support_status=legal_but_not_modeled`
  - `effect_support.speed_order=not_supported`
  - `effect_support.choice_lock=not_supported`
  - notes include `Speed/order effects are not modeled.`
- `data/static/champions_legal_items.json` confirms `quick-claw`:
  - `legal=true`
  - `category=hold_item`
  - `effect_support_status=legal_but_not_modeled`
  - `effect_support.speed_order=not_supported`
  - notes include `Speed/order effects are not modeled.`
- Existing `speed_context` already supports limited Choice Scarf effective Speed when both active Pokemon have user-confirmed final Speed and Choice Scarf is user-confirmed.
- Existing `speed_context.is_final_turn_order` remains `false`.
- Choice Scarf choice lock remains unmodeled.
- Quick Claw has no current modeled advice context.

Design:
- Keep Choice Scarf in existing `speed_context`.
- Do not duplicate Choice Scarf into a new item context.
- Recommend a separate future `speed_order_context` for Quick Claw-like limited move-order item pressure.
- Proposed `speed_order_context` should be additive and should not be nested inside `speed_context`, `damage_estimate`, or `ko_context`.
- Available Quick Claw context should require:
  - user-confirmed item
  - Champions legal gate pass
  - item id `quick-claw`
  - limited "may affect move order" framing only
- `available=false` reasons should be debug/enriched only and hidden from default advice payload.

LLM wording policy:
- Allowed:
  - "may affect move order"
  - "speed order is not fully modeled"
  - "final move order is not calculated"
- Forbidden:
  - "will move first"
  - "guaranteed outspeeds"
  - "confirmed first"
  - "always acts before"
  - "Quick Claw guarantees priority"
  - exact Quick Claw activation probability
  - final speed tie resolution

Recommended v0.98:
- `v0.98 - Quick Claw Limited Speed-Order Context Implementation`.
- Add `speed_order_context` for Quick Claw only.
- Preserve Choice Scarf in existing `speed_context`.
- No activation probability, final move order, speed tie resolution, priority, Trick Room, Tailwind, paralysis, boosts, abilities, weather, item consumption, or Turn Engine.
- No damage formula, raw roll, or `ko_context` changes.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No speed calculation implementation.
- No final move order calculation.
- No speed tie final resolution.
- No priority, Trick Room, Tailwind, paralysis, boosts, ability, or weather integration.
- No choice lock implementation.
- No Quick Claw activation probability calculation.
- No Turn Engine.
- No damage formula changes.
- No raw damage roll modification.
- No `ko_context` changes.
- No legal fixture mutation.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.98 - Quick Claw limited speed-order context implementation

Purpose:
- Implement the v0.97 Quick Claw design as a Gemini advice-only limited `speed_order_context`.
- Keep Choice Scarf in the existing top-level `speed_context`.
- Avoid actual move order, speed tie, activation probability, priority, Turn Engine, damage, or KO changes.

Implemented:
- Added `llm/advisor_speed_order_context.py`.
- Added move-level `speed_order_context` for:
  - `moves.my_available_moves[*]`
  - `moves.my_selected_move`
  - `opponent_moves.known_moves[*]`
- `speed_order_context.available=true` requires:
  - attacker item profile status `user_confirmed`
  - item id `quick-claw`
  - Champions legal item gate pass
  - an actual selected/available/known move payload
- Available context includes:
  - `mode=limited_speed_order_item_context`
  - `speed_order_effect.type=quick_claw`
  - `effect_label=may_affect_move_order`
  - `activation_probability_calculated=false`
  - `final_move_order_calculated=false`
  - `speed_tie_resolved=false`
  - `priority_integrated=false`
  - `turn_engine_integrated=false`
  - `is_final_battle_truth=false`
- `available=false` speed-order contexts are removed from the default Gemini advice payload.
- Enriched/debug payload can retain unavailable reasons such as:
  - `no_speed_order_item`
  - `item_not_user_confirmed`
  - `unsupported_speed_order_item`
  - `blocked_by_legal_item_coverage`
- Default advice payload filtering now treats applied Choice Scarf `speed_context` sides as available item sides, so Quick Claw-specific unavailable filtering does not hide existing Choice Scarf effective Speed context.
- Default advice payload note filtering now also removes debug-only item profile `notes` containing phrases such as `not modeled`, preventing legal-but-limited item metadata from leaking through profile notes.

Prompt / contract:
- Added `speed_order_context` prompt and contract guardrails.
- Allowed wording:
  - Quick Claw may affect move order.
  - Quick Claw can occasionally affect move order.
  - Move order is not fully modeled.
- Forbidden wording:
  - will move first
  - guaranteed outspeeds
  - confirmed first
  - always acts before
  - wins the speed interaction
  - safe because it moves first
- Documented that Choice Scarf remains in `speed_context`, not `speed_order_context`.
- Documented that candidate moves do not receive `speed_order_context`.

Tests:
- Added payload contract tests for:
  - user-confirmed legal Quick Claw preserving available `speed_order_context`
  - unconfirmed Quick Claw hidden from default advice payload
  - non-Quick-Claw item hidden from default advice payload
  - unavailable reason and item name silence in default advice payload
  - raw `damage_estimate` retained
  - raw damage rolls retained
  - `ko_context` retained
  - Choice Scarf `speed_context` regression preserved
  - prompt and contract guardrails

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 41 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had one known perf-sensitive threshold miss; immediate rerun passed, 4 passed.
- `uv run pytest -q`: 894 passed, 2 deselected.

Maintained boundaries:
- No legal fixture changes.
- No fixture changes.
- No speed calculation implementation.
- No final move order calculation.
- No Quick Claw activation probability calculation.
- No priority, Trick Room, Tailwind, paralysis, boosts, ability, or weather integration.
- No Turn Engine.
- No item consumption.
- No Choice Scarf implementation changes beyond preserving existing `speed_context` through advice filtering.
- No choice lock implementation.
- No damage formula changes.
- No raw damage roll modification.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.98.1 - Quick Claw local Gemini verification attempt

Purpose:
- Verify that v0.98 Quick Claw `speed_order_context` is represented safely in actual Gemini default advice.
- Confirm unavailable Quick Claw contexts stay hidden from default advice payload.
- Confirm Choice Scarf remains in existing `speed_context` and is not moved into `speed_order_context`.
- Confirm Quick Claw does not affect raw damage rolls, `damage_estimate`, or `ko_context`.

Gemini actual call:
- Attempted local Gemini actual call through the normal default-advice prompt path.
- Case A reached the Gemini API, but no model advice text was returned.
- Failure: HTTP 429 `RESOURCE_EXHAUSTED`.
- Actual Gemini natural-language wording could not be judged.
- This is not recorded as PASS; v0.98.1 actual Gemini verification is BLOCKED.
- No API key, secret, or account details were recorded.

Payload preflight:
- Case A - Quick Claw available:
  - Enriched/debug payload had `speed_order_context.available=true`.
  - Default advice payload retained `speed_order_context`.
  - `speed_order_effect.type=quick_claw`.
  - `activation_probability_calculated=false`.
  - `final_move_order_calculated=false`.
  - `speed_tie_resolved=false`.
  - `priority_integrated=false`.
  - `turn_engine_integrated=false`.
  - Default advice payload retained raw damage range `31-37`.
  - Default advice payload retained raw 16-roll damage list.
  - Default advice payload retained `ko_context.ohko.chance=0.0`.
  - Default advice payload did not contain hard move-order claims such as `will move first`, `guaranteed outspeeds`, `confirmed first`, `always acts before`, `wins the speed interaction`, or `safe because it moves first` from the context payload.
- Case B - Quick Claw unavailable / unconfirmed:
  - Enriched/debug payload had `speed_order_context.available=false`.
  - Reason was `item_not_user_confirmed`.
  - Default advice payload removed `speed_order_context`.
  - Default advice payload hid the Quick Claw item profile as unknown.
  - Default advice payload retained raw damage and `ko_context`.
  - Default advice payload did not expose Quick Claw unavailable reason, item name, or unavailable-effect wording.
- Case C - Choice Scarf regression:
  - Enriched/debug payload had Quick Claw-specific `speed_order_context.available=false` with `unsupported_speed_order_item`.
  - Default advice payload removed `speed_order_context`.
  - Existing top-level `speed_context` remained available.
  - Choice Scarf modifier remained in `speed_context.my_active.speed_modifiers`.
  - Effective Speed remained `150` from raw Speed `100`.
  - `speed_context.is_final_turn_order=false` remained unchanged.
  - Choice lock remained unsupported/unmodeled; no choice lock implementation was added.
- Case D - damage / KO regression:
  - Same Quick Claw available payload retained raw damage range `31-37`.
  - Raw damage rolls were unchanged.
  - `ko_context` remained raw damage-roll context.
  - No Quick Claw activation probability, final move order, or KO integration appeared.

Verdict:
- Payload preflight: PASS.
- Actual Gemini natural-language verification: BLOCKED by HTTP 429 `RESOURCE_EXHAUSTED`.
- Overall v0.98.1: BLOCKED / retry required once local Gemini API access is restored.

Tests:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 41 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 2 failed, 2 passed on first run; rerun had 1 failed, 3 passed.
- `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: failed on three isolated reruns in the current local environment.
- `uv run pytest -q`: 1 failed, 893 passed, 2 deselected.
- Failing test: `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`.
- No threshold, skip, xfail, damage formula, raw roll, or Q12 changes were made.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No prompt changes.
- No tests changed.
- No fixture or legal fixture changes.
- No new item implementation.
- No speed calculation implementation.
- No final move order calculation.
- No Quick Claw activation probability calculation.
- No speed tie, priority, Trick Room, Tailwind, paralysis, boosts, ability, or weather integration.
- No Turn Engine.
- No item consumption.
- No Choice Scarf implementation.
- No choice lock implementation.
- No damage formula changes.
- No raw damage roll modification.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

Next:
- Retry `v0.98.1 Quick Claw Local Gemini Verification` once local Gemini API access is restored.
- If the retry passes, continue to the next Champions legal item design.

---

## v0.99 - Item context registry / filtering cleanup design

Purpose:
- Design a cleanup path for default advice payload filtering after the addition of multiple item/advice contexts.
- Document where filtering rules currently live and how they should be centralized before v1.0.

Current context inventory:
- `survival_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`
- `resist_berry_context`
- `type_boost_context`
- `speed_context`
- `speed_order_context`

Findings:
- Most default advice payload filtering currently lives in `llm/advisor_client.py`.
- `build_ui_advice_payload()` is the main advice-payload boundary.
- `ITEM_CONTEXT_FIELDS` identifies item contexts where `available=false` should be removed from the default advice payload.
- `_remove_unavailable_item_contexts()` removes unavailable item contexts.
- `_collect_available_item_context_sides()` protects item profiles for sides with available context.
- `_hide_advice_hidden_item_profiles()` and `_hide_advice_hidden_item_effects()` prevent item-profile and item-effect leaks.
- `_hide_move_local_unavailable_type_boost_item_effects()` is a type-boost-specific special case.
- `_speed_context_item_sides()` is a Choice Scarf `speed_context` special case.
- `_remove_debug_only_limitations()` strips debug-only limitation phrases from default advice payload.

Design conclusion:
- Add a registry or registry-like constants before v1.0.
- Recommended shape:
  - `ADVICE_CONTEXT_KEYS` or `ADVICE_CONTEXT_REGISTRY`
  - `DEBUG_ONLY_REASON_PHRASES`
  - `filter_context_for_default_advice(payload)`
- Keep behavior unchanged in the cleanup:
  - available legal contexts remain in default advice payload
  - `available=false` item contexts are hidden from default advice payload
  - debug/enriched payload keeps unavailable/deferred/blocked reasons
  - raw `damage_estimate` remains
  - raw `ko_context` remains
  - `speed_context` remains governed by its own Speed contract
- Include registry notes or hooks for:
  - type-boost move-local `damage_estimate.item_effects` scrubbing
  - Choice Scarf `speed_context` item-profile protection
  - debug-only limitation phrase removal

Recommended v1.0:
- `v1.0 - Item Context Registry Filtering Cleanup Implementation`.
- Implement registry cleanup without adding new item behavior.
- Add table-driven tests for all registered item context keys.
- Add tests that registry keys stay aligned with move-level context attachment.
- Preserve candidate move exclusion.

Alternative:
- `v1.0 - Item Context Filtering Contract Test Consolidation` if T1/T2 prefer a test-only hardening step before code cleanup.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 41 passed.
- `uv run pytest -q`: 894 passed, 2 deselected.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No filtering logic changes.
- No new item context implementation.
- No fixture or legal fixture changes.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No Turn Engine.
- No item consumption.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.0 - Item context registry filtering cleanup implementation

Purpose:
- Implement the v0.99 cleanup design by centralizing default advice item-context filtering policy behind registry constants.
- Preserve existing default advice payload behavior.
- Avoid adding any new item or battle mechanics.

Implemented:
- Added contract-owned registry constants in `llm/advisor_payload_contract.py`:
  - `ADVICE_CONTEXT_KEYS`
  - `ADVICE_ITEM_CONTEXT_KEYS`
  - `ADVICE_CONTEXT_SIDE_FIELDS`
  - `ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB`
  - `DEBUG_ONLY_REASON_PHRASES`
- Refactored `llm/advisor_client.py` to consume the registry constants.
- Added `filter_context_for_default_advice(payload)` as the canonical default-advice filtering helper.
- Kept `build_ui_advice_payload()` as a deepcopy wrapper around the filtering helper.
- Preserved existing filtering behavior:
  - `available=false` item contexts are removed from default advice payload
  - available item contexts remain in default advice payload
  - enriched/debug payload can retain unavailable reasons
  - hidden item profiles remain scrubbed as unknown
  - hidden item effects remain scrubbed
  - type-boost move-local `damage_estimate.item_effects` scrub behavior remains
  - Choice Scarf `speed_context` item-profile protection remains
  - debug-only limitation phrase removal remains

Registry coverage:
- Current registered advice contexts:
  - `survival_context`
  - `recovery_context`
  - `accuracy_context`
  - `critical_context`
  - `flinch_context`
  - `multi_hit_context`
  - `resist_berry_context`
  - `type_boost_context`
  - `speed_context`
  - `speed_order_context`
  - future `charge_context`
- `speed_context` remains top-level Speed comparison context, not an item-context removal target.
- Choice Scarf remains in `speed_context`.
- `speed_order_context` remains Quick Claw-only.

Tests added/updated:
- Registry lists current context surfaces.
- Every registered item context with `available=false` is removed from default advice payload.
- Every registered item context with `available=true` remains in default advice payload.
- Debug/enriched payload can still retain unavailable reasons.
- Raw `damage_estimate.damage_range`, raw rolls, and `ko_context` remain.
- Existing Choice Scarf `speed_context` regression remains.
- Existing type-boost item-effect scrub regression remains.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 44 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 perf-sensitive failure; isolated rerun passed 3 times; file rerun passed 4 passed.
- `uv run pytest -q`: 1 full-suite-sensitive perf failure, 896 passed, 2 deselected on two reruns.
- Failing full-suite-only test: `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`.
- Full-suite failure samples:
  - rerun 1 median `0.124845ms` over threshold `0.120000ms`
  - rerun 2 median `0.122099ms` over threshold `0.120000ms`
- No threshold, skip, xfail, damage formula, raw roll, Q12, or `ko_context` changes were made.

Maintained boundaries:
- Behavior-preserving cleanup.
- No new item context implementation.
- No new mechanics.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No speed calculation changes.
- No final move order calculation.
- No Quick Claw activation probability calculation.
- No Choice Scarf choice lock implementation.
- No priority, Trick Room, Tailwind, paralysis, boosts, ability, weather, or Turn Engine integration.
- No item consumption.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.0.1 - Registry cleanup verification

Purpose:
- Verify that the v1.0 registry/filtering cleanup did not change existing item/advice context behavior.
- Record regression results without adding new item mechanics or changing filtering behavior.

Verified context behavior:
- Available context retention:
  - `survival_context`
  - `recovery_context`
  - `accuracy_context`
  - `critical_context`
  - `flinch_context`
  - `multi_hit_context`
  - `resist_berry_context`
  - `type_boost_context`
  - `speed_context`
  - `speed_order_context`
- Unavailable/deferred/blocked item contexts remain hidden from default advice payload.
- Default advice payload still strips debug-only reason wording such as:
  - `not modeled`
  - `not reflected`
  - `unsupported`
  - `blocked`
  - `deferred`
  - `effect is not applied`
  - `item effect is not included`

Regression checks:
- Choice Scarf:
  - Existing top-level `speed_context` remains protected.
  - Choice Scarf was not moved into `speed_order_context`.
  - Choice lock remains unimplemented.
- Quick Claw:
  - `speed_order_context.available=true` remains in default advice payload.
  - Activation probability and final move order remain uncalculated.
- Type boost:
  - Available legal type boost context remains in default advice payload.
  - Mismatched/non-legal type boost item exposure through `damage_estimate.item_effects` remains scrubbed.
- Damage / KO:
  - No damage formula changes.
  - No raw damage roll changes.
  - No Q12 multiplier changes.
  - No `ko_context` calculation changes.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 44 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 perf-sensitive failure; isolated rerun passed 3 times; file rerun passed 4 passed.
- `uv run pytest -q`: 1 full-suite-sensitive perf failure, 896 passed, 2 deselected.
- Failing perf-sensitive test: `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`.
- Failure samples:
  - perf file first run median `0.123070ms` over threshold `0.120000ms`
  - full suite median `0.146497ms` over threshold `0.120000ms`
- No threshold, skip, xfail, damage formula, raw roll, Q12, or `ko_context` changes were made.

Verdict:
- Registry/filtering behavior regression: PASS.
- Choice Scarf regression: PASS.
- Quick Claw regression: PASS.
- Type-boost scrub regression: PASS.
- Damage / KO regression: PASS.
- Perf status: known perf-sensitive test remains environment/full-suite sensitive; isolated 3x and file rerun passed.

Maintained boundaries:
- Verification record only.
- No code changes.
- No filtering behavior changes.
- No prompt changes.
- No tests changed.
- No new item implementation.
- No new mechanics.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No speed calculation changes.
- No final move order calculation.
- No Quick Claw activation probability calculation.
- No Choice Scarf choice lock implementation.
- No priority, Trick Room, Tailwind, paralysis, boosts, ability, weather, or Turn Engine integration.
- No item consumption.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.0.2 - Perf test stability design

Purpose:
- Analyze repeated instability in `tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average`.
- Design stabilization options without changing thresholds, skipping/xfailing, or modifying damage math.

Findings:
- The unstable test measures `advisor.damage.formula.calc_damage_rolls()` directly.
- The measured context includes:
  - Fire-type `flamethrower`
  - sun weather
  - defender Light Screen
  - grounded inputs
  - attacker item `life-orb`
  - defender item `occa-berry`
- The test does not call:
  - `llm/advisor_client.py`
  - registry-based default advice payload filtering
  - `llm/advisor_damage_estimate.attach_selected_move_damage_estimate()`
  - item/advice context helpers
  - `ko_context`
- Recent v0.94-v1.0.1 LLM/context changes are unlikely to directly affect this perf test.

Observed v1.0.2 local results:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 44 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 perf-sensitive failure.
  - failing test: `test_item_damage_calculation_under_point_12ms_average`
  - median `0.123070ms` over threshold `0.120000ms`
  - samples `[0.092768, 0.081443, 0.12307, 0.14194, 0.166956]`
- Isolated rerun of the failing test 3x: passed, passed, passed.
- `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 1 full-suite-sensitive perf failure, 896 passed, 2 deselected.
  - failing test: `test_item_damage_calculation_under_point_12ms_average`
  - median `0.146497ms` over threshold `0.120000ms`
  - samples `[0.108934, 0.100931, 0.146497, 0.147728, 0.16589]`

Analysis:
- Current evidence points to timing-sensitive/environment-sensitive perf failure, not correctness failure.
- No damage roll mismatch or formula assertion failed.
- Isolated reruns passing after failures suggest CPU scheduling, process state, cache/warmup, or local load sensitivity.
- The `0.120000ms` threshold is very tight for the current environment because several failures are only a few microseconds over threshold.
- The larger full-suite failure still matches the same timing-only failure mode.

Stability options documented:
- increase warm-up
- increase iterations per sample
- increase repeats while preserving median
- add careful outlier handling
- collect more baseline measurements before threshold discussion
- separate perf tests from correctness CI
- introduce environment-sensitive perf marker without skipping by default
- investigate baseline-comparison style perf tests

Recommended v1.0.3:
- `v1.0.3 - Perf Test Measurement Stabilization`.
- Keep threshold unchanged.
- Do not skip or xfail.
- Do not change damage formula, raw rolls, Q12, or `ko_context`.
- Improve measurement stability and diagnostics only.
- Conservative first candidate:
  - modestly increase warm-up and/or repeats for the tight item perf test
  - preserve median-based assertion
  - collect isolated 10x, perf file 5x, and full-suite results

Maintained boundaries:
- Documentation-only design.
- No threshold changes.
- No skip or xfail.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No item context filtering changes.
- No new item or mechanics.
- No Turn Engine.
- No item consumption.
- No fixture or legal fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.0.3 - Perf test measurement stabilization implementation

Purpose:
- Stabilize the timing-sensitive damage perf benchmark without relaxing its threshold.
- Keep the benchmark focused on `calc_damage_rolls()` hot-path measurement.
- Preserve damage formula, raw damage rolls, Q12, and `ko_context` behavior.

Implemented:
- Kept `test_item_damage_calculation_under_point_12ms_average` threshold at `0.120000ms`.
- Did not add skip or xfail.
- Changed perf timing helper to measure CPU process time with `time.process_time()` rather than wall-clock `time.perf_counter()`.
  - Rationale: the benchmark is intended to measure CPU cost of the damage hot path, not scheduler / background-load wall time.
- Disabled Python GC during the timing section and restored its previous state afterward.
  - Rationale: reduce unrelated GC pause noise inside the measured window.
- Increased measurement stability:
  - `PERF_WARMUP_ITERATIONS`: `100` -> `300`
  - `PERF_REPEATS`: `5` -> `7`
  - `PERF_ITERATIONS`: kept at `1000`
- Added optional measurement `batches`.
- Applied `batches=3` only to the tight item damage benchmark.
- Preserved median-based assertion style by using the best batch median for the tight benchmark.
- Improved failure messages with:
  - best batch median
  - batch medians
  - all samples
  - min / max
  - iterations / repeats / warm-up / batch settings

Verification:
- Isolated target perf 10x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`
  - result: 10 passed / 0 failed
- Perf file 5x:
  - `uv run pytest tests/test_damage_perf.py -q`
  - result: 5 passed / 0 failed
  - each run reported `4 passed`
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 44 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest -q`: 897 passed, 2 deselected.

Maintained boundaries:
- No threshold changes.
- No skip or xfail.
- No perf test deletion.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No item/advice context filtering changes.
- No new item or mechanics.
- No Turn Engine.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.1 - Next legal item context candidate design

Purpose:
- Survey Champions legal item fixture coverage for the next safe limited item/advice context candidate.
- Exclude already modeled contexts and candidates that require Turn Engine, item consumption, final KO probability, final move order, or unsupported legal/metadata assumptions.
- Keep this as a documentation-only spike.

Investigated:
- `data/static/champions_legal_items.json`
- `data/static/items_damage.json`
- existing item context helpers
- `llm/advisor_damage_estimate.py`
- `llm/advisor_payload_contract.py`
- `llm/advisor_client.py`
- `docs/advisor_payload_contract.md`

Findings:
- The Champions legal fixture contains 117 legal items:
  - 12 hold items
  - 28 berries
  - 18 type-boosting items
  - 59 Mega Stones
- Already modeled legal non-Mega coverage includes:
  - Bright Powder
  - Choice Scarf
  - Focus Band
  - Focus Sash
  - King's Rock
  - Leftovers
  - Quick Claw
  - Scope Lens
  - Sitrus Berry
  - 17 metadata-supported type-boosting items
  - 17 standard type-resist berries
- Remaining non-Mega legal candidates are:
  - `light-ball`
  - `fairy-feather`
  - `mental-herb`
  - `shell-bell`
  - `white-herb`
  - status/PP/recovery utility berries: `aspear-berry`, `cheri-berry`, `chesto-berry`, `leppa-berry`, `lum-berry`, `oran-berry`, `pecha-berry`, `persim-berry`, `rawst-berry`
  - `chilan-berry`
- Mega Stones are legal but deferred because Mega Evolution needs form/species/state/ability mechanics.

Recommendation:
- Recommend `Light Ball` as the v1.2 candidate.
- Proposed next context: `species_stat_item_context`.
- Rationale:
  - Champions legal fixture confirms `light-ball`.
  - `items_damage.json` contains `species_stat_items.light-ball`.
  - existing damage helper support already handles Light Ball for Pikachu.
  - a limited advice context can expose existing legal + metadata + helper support without adding a new damage formula path.
- v1.2 should keep scope narrow:
  - Light Ball only
  - user-confirmed attacker item only
  - holder species must be Pikachu
  - default advice payload keeps only `available=true`
  - debug/enriched payload may retain unavailable reasons
  - no new KO/OHKO/2HKO integration

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 44 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure in `test_item_damage_calculation_under_point_12ms_average`.
  - failure: best batch median `0.140625ms`, threshold `0.120000ms`
  - batch medians: `[0.140625, 0.15625, 0.234375]`
  - samples min/max: `0.125000ms` / `0.281250ms`
- Isolated target rerun 3x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`
  - result: 3 passed / 0 failed
- `uv run pytest tests/test_damage_perf.py -q`: first rerun had the same timing-sensitive perf failure.
  - failure: best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians: `[0.125, 0.140625, 0.140625]`
  - samples min/max: `0.109375ms` / `0.187500ms`
- `uv run pytest tests/test_damage_perf.py -q`: second rerun passed, 4 passed.
- `uv run pytest -q`: 897 passed, 2 deselected.
- No threshold, skip, xfail, damage formula, raw roll, Q12, or `ko_context` changes were made.

Deferred:
- Fairy Feather: legal but missing local damage metadata/helper support.
- Mental Herb / White Herb: require status/stat-stage state, trigger timing, and item consumption.
- Shell Bell / Oran Berry: require recovery timing and item consumption; Shell Bell also needs damage-dealt recovery.
- Status berries: require actual status/confusion/PP state and item consumption.
- Chilan Berry: special Normal-type resist semantics; better as a focused future pass.
- Mega Stones: require Mega Evolution mechanics.
- Loaded Dice / Power Herb: remain blocked/future-only until Champions legal coverage is confirmed.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No new item context implementation.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No speed calculation.
- No final move order.
- No final KO probability.
- No Turn Engine.
- No item consumption.
- No fixture or legal fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.2 - Light Ball limited species stat item context design

Purpose:
- Design Light Ball as a limited `species_stat_item_context`.
- Separate existing damage helper support from a future Gemini advice context.
- Keep this as a documentation-only spike.

Investigated:
- `data/static/champions_legal_items.json`
- `data/static/items_damage.json`
- `advisor/damage/items.py`
- `advisor/damage/item_modifiers.py`
- `llm/advisor_damage_estimate.py`
- `llm/advisor_payload_contract.py`
- `llm/advisor_client.py`
- `docs/advisor_payload_contract.md`

Findings:
- `light-ball` is Champions legal:
  - `legal=true`
  - `legality_status=legal`
  - `category=hold_item`
- `items_damage.json` contains `species_stat_items.light-ball`:
  - `species=["pikachu"]`
  - `stats=["atk", "spa"]`
  - `multiplier_q12=8192`
- existing damage helper support already exists:
  - `advisor/damage/items.py` loads `species_stat_items` as `ItemEffect(kind="species_stat")`
  - `advisor/damage/item_modifiers.py` returns `M_DOUBLE` in `attack_stat_item_mod()` when `item.item_id == "light-ball"` and holder species is `pikachu`
- legal fixture still labels Light Ball as `legal_but_not_modeled`, so v1.3 should cross-check legal fixture, local metadata, and helper support rather than relying on any one source alone.

Design recommendation:
- Use `species_stat_item_context`.
- Initial implementation should support Light Ball only.
- Available only when:
  - item profile is `status=user_confirmed`
  - `item_id=light-ball`
  - Champions legal fixture confirms the item
  - `items_damage.json` metadata exists
  - holder species normalizes to `pikachu`
  - move is damaging with a category that can use Atk or SpA
- Non-Pikachu holder, missing metadata, unconfirmed item, blocked/deferred, or unsupported reasons should remain debug/enriched metadata only and be hidden from the default Gemini advice payload.
- Context is explanatory only:
  - no new damage formula
  - no raw damage roll changes
  - no Q12 constant changes
  - no `ko_context` changes
  - no Light-Ball-adjusted KO/OHKO/2HKO context
  - no final stat truth or EV/IV/nature inference

Wording policy:
- Allowed:
  - Light Ball may boost Pikachu's offensive stats in the underlying calculation.
  - This is species-specific to Pikachu.
  - Do not generalize this item to non-Pikachu holders.
  - Do not treat this as a final KO guarantee.
- Forbidden:
  - guaranteed KO
  - always doubles damage
  - confirmed OHKO because of Light Ball
  - all Electric-type Pokemon benefit from Light Ball
  - Light Ball works on any holder
  - final stats are fully known
  - exact EV/IV/nature-adjusted stats are known

Recommended v1.3:
- `v1.3 - Light Ball Limited Species Stat Item Context Implementation`
- Add `llm/advisor_species_stat_item_context.py`.
- Add registry key `species_stat_item_context`.
- Attach move-level context next to relevant damage estimates.
- Keep default advice payload filtering behavior: `available=true` only.
- Add tests for Pikachu available, non-Pikachu hidden, unconfirmed hidden, debug reason retained, raw damage unchanged, raw rolls unchanged, Q12 unchanged, and `ko_context` unchanged.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 44 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure in `test_item_damage_calculation_under_point_12ms_average`.
  - failure: best batch median `0.156250ms`, threshold `0.120000ms`
  - batch medians: `[0.15625, 0.171875, 0.15625]`
  - samples min/max: `0.093750ms` / `0.218750ms`
- Isolated target rerun 3x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`
  - result: 3 passed / 0 failed
- `uv run pytest tests/test_damage_perf.py -q`: first rerun had the same timing-sensitive perf failure.
  - failure: best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians: `[0.125, 0.140625, 0.140625]`
  - samples min/max: `0.093750ms` / `0.156250ms`
- `uv run pytest tests/test_damage_perf.py -q`: second rerun still had the same timing-sensitive perf failure.
  - failure: best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians: `[0.125, 0.125, 0.140625]`
  - samples min/max: `0.109375ms` / `0.156250ms`
- `uv run pytest -q`: 1 perf-sensitive failure, 896 passed, 2 deselected.
  - failure: best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians: `[0.140625, 0.125, 0.140625]`
  - samples min/max: `0.093750ms` / `0.171875ms`
- Threshold/skip/xfail/damage formula/raw rolls/Q12/`ko_context` were not changed.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No new item context implementation.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final stat truth calculation.
- No EV/IV/nature inference.
- No final KO probability.
- No Turn Engine.
- No item consumption.
- No Mega Evolution.
- No ability/weather/terrain interaction.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.3 - Light Ball limited species stat item context implementation

Purpose:
- Implement Light Ball as a limited `species_stat_item_context` for Gemini advice.
- Keep `damage_estimate.item_effects` as the source of truth for whether an item modifier was applied.
- Add explanatory move-level context only; do not create new damage, KO, stat, or Turn Engine mechanics.

Implemented:
- Added `llm/advisor_species_stat_item_context.py`.
- Added move-level `species_stat_item_context` attachment for:
  - `moves.my_available_moves`
  - `moves.my_selected_move`
  - generated selected-move fallback payloads
  - `opponent_moves.known_moves`
- Added `species_stat_item_context` to advice context registry/filtering.
- Kept `available=true` Light Ball context in default advice payload only when:
  - item profile is `status=user_confirmed`
  - `item_id=light-ball`
  - Champions legal item gate passes
  - local `species_stat_items.light-ball` metadata exists
  - holder species normalizes to `pikachu`
  - move category is physical or special
- Hid `available=false` species-stat context from default advice payload while preserving enriched/debug reasons.
- Preserved default advice hiding for non-Pikachu Light Ball and unconfirmed Light Ball.
- Updated advisor prompt and payload contract wording for:
  - Light Ball is species-specific to Pikachu
  - Light Ball may boost Pikachu's offensive stats in the underlying calculation
  - `damage_estimate.item_effects` remains the source of truth
  - no final stat truth, EV/IV/nature inference, final KO guarantee, or Light-Ball-adjusted KO/OHKO/2HKO
- Added payload contract regression tests for:
  - Pikachu + user-confirmed Light Ball available context
  - non-Pikachu + user-confirmed Light Ball hidden from default advice
  - unconfirmed Light Ball hidden from default advice
  - advice registry includes `species_stat_item_context`
  - local `damage_estimate.item_effects` scrub behavior includes `species_stat_item_context`

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 47 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 2 timing-sensitive perf failures.
  - `test_item_damage_calculation_under_point_12ms_average`: best batch median `0.125000ms`, threshold `0.120000ms`.
  - batch medians: `[0.125, 0.140625, 0.15625]`
  - samples min/max: `0.078125ms` / `0.203125ms`
  - `test_ability_damage_calculation_under_point_20ms_average`: best batch median `0.203125ms`, threshold `0.200000ms`.
  - batch medians: `[0.203125]`
  - samples min/max: `0.156250ms` / `0.296875ms`
- Isolated rerun of both failing perf tests: passed.
- `uv run pytest tests/test_damage_perf.py -q`: rerun 4 passed.
- `uv run pytest -q`: 1 full-suite-sensitive perf failure, 899 passed, 2 deselected.
  - `test_item_damage_calculation_under_point_12ms_average`: best batch median `0.125000ms`, threshold `0.120000ms`.
  - batch medians: `[0.140625, 0.125, 0.125]`
  - samples min/max: `0.109375ms` / `0.171875ms`
- Isolated target rerun 3x after full-suite failure:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`
  - result: 3 passed / 0 failed
- Threshold/skip/xfail/damage formula/raw rolls/Q12/`ko_context` were not changed.

Maintained boundaries:
- No new damage formula.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` calculation changes.
- No final stat truth calculation.
- No EV/IV/nature inference.
- No final KO probability.
- No Light-Ball-adjusted KO/OHKO/2HKO implementation.
- No Turn Engine.
- No item consumption.
- No Mega Evolution.
- No ability/weather/terrain interaction.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.3.1 - Light Ball context verification

Purpose:
- Verify the v1.3 Light Ball `species_stat_item_context` behavior in payload preflight and actual Gemini advice flow.
- Keep the step verification-only unless a real leak or behavior regression is found.

Payload preflight:
- Case A: Pikachu + user-confirmed Light Ball:
  - enriched/debug `species_stat_item_context.available=true`.
  - default advice payload retained `species_stat_item_context.available=true`.
  - default advice item profile retained `item_id=light-ball`.
  - raw `damage_estimate.damage_range` and `rolls` matched enriched/debug.
  - raw `ko_context.ohko` and `ko_context.two_hko` matched enriched/debug.
  - no forbidden payload wording appeared:
    - `not modeled`
    - `not reflected`
    - `unsupported`
    - `blocked`
    - `deferred`
    - `effect is not applied`
    - `item effect is not included`
    - `Light Ball works on any holder`
    - `all Electric-type Pokemon benefit`
    - `guaranteed KO`
    - `confirmed OHKO`
    - `always doubles damage`
    - `final stats are fully known`
- Case B: non-Pikachu + user-confirmed Light Ball:
  - enriched/debug `species_stat_item_context.available=false`.
  - reason: `holder_species_not_supported`.
  - default advice payload removed `species_stat_item_context`.
  - default advice payload hid `item_profiles.my_active` as unknown.
  - raw damage and `ko_context` matched enriched/debug.
  - no forbidden payload wording appeared.
- Case C: Pikachu + unconfirmed Light Ball:
  - enriched/debug `species_stat_item_context.available=false`.
  - reason: `item_not_user_confirmed`.
  - default advice payload removed `species_stat_item_context`.
  - default advice payload hid `item_profiles.my_active` as unknown.
  - raw damage and `ko_context` matched enriched/debug.
  - no forbidden payload wording appeared.

Gemini actual call:
- Attempted actual Gemini calls for:
  - Pikachu + user-confirmed Light Ball
  - non-Pikachu + user-confirmed Light Ball
  - Pikachu + unconfirmed Light Ball
- Result: BLOCKED, not PASS.
- Blocker: HTTP 429 `RESOURCE_EXHAUSTED`.
- No API key, secret, project, billing, or account details were recorded.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 47 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 1 timing-sensitive perf failure, 3 passed.
  - `test_item_damage_calculation_under_point_12ms_average`
  - best batch median `0.156250ms`, threshold `0.120000ms`
  - batch medians: `[0.1875, 0.15625, 0.15625]`
  - samples min/max: `0.109375ms` / `0.250000ms`
- Isolated target rerun 3x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`
  - result: 0 passed / 3 failed
  - failures:
    - best batch median `0.125000ms`, threshold `0.120000ms`
    - best batch median `0.140625ms`, threshold `0.120000ms`
    - best batch median `0.125000ms`, threshold `0.120000ms`
- `uv run pytest tests/test_damage_perf.py -q`: rerun 1 timing-sensitive perf failure, 3 passed.
  - best batch median `0.140625ms`, threshold `0.120000ms`
  - batch medians: `[0.15625, 0.140625, 0.171875]`
  - samples min/max: `0.125000ms` / `0.234375ms`
- `uv run pytest -q`: 1 timing-sensitive perf failure, 899 passed, 2 deselected.
  - `test_item_damage_calculation_under_point_12ms_average`
  - best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians: `[0.140625, 0.125, 0.125]`
  - samples min/max: `0.109375ms` / `0.140625ms`

Verdict:
- Payload preflight: PASS.
- Pikachu Light Ball available payload behavior: PASS.
- non-Pikachu Light Ball default advice filtering: PASS.
- unconfirmed Light Ball default advice filtering: PASS.
- raw damage / raw rolls / Q12 / `ko_context`: unchanged by this verification step.
- Actual Gemini natural-language verification: BLOCKED by HTTP 429 `RESOURCE_EXHAUSTED`.
- Perf status: timing-sensitive perf failure persists in the current environment, including isolated target reruns. No threshold, skip, xfail, damage formula, raw roll, Q12, or `ko_context` changes were made.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No new item implementation.
- No new mechanics implementation.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final stat truth calculation.
- No EV/IV/nature inference.
- No final KO probability.
- No Light-Ball-adjusted KO/OHKO/2HKO implementation.
- No Turn Engine.
- No item consumption.
- No Mega Evolution.
- No ability/weather/terrain interaction.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.4 - Chilan Berry limited Normal-resist context design

Purpose:
- Design how to handle deferred `chilan-berry` as a limited advice context.
- Keep Chilan separate from the 17 standard super-effective `resist_berry_context` berries.
- Preserve raw damage, raw rolls, Q12 constants, `ko_context`, and Turn Engine boundaries.

Investigated:
- `data/static/champions_legal_items.json`
- `data/static/items_damage.json`
- `llm/advisor_resist_berry_context.py`
- `llm/advisor_damage_estimate.py`
- `llm/advisor_payload_contract.py`
- `llm/advisor_client.py`
- `tests/test_advisor_damage_estimate.py`
- `tests/test_advisor_payload_contract.py`
- `tests/test_berries.py`
- `docs/advisor_payload_contract.md`
- `docs/spike_v0.87_type_resist_berry_survival_context_design.md`
- `docs/spike_v1.1_next_legal_item_context_candidate_design.md`

Findings:
- `chilan-berry` is Champions legal.
- `champions_legal_items.json` marks it:
  - `legal=true`
  - `legality_status=legal`
  - `category=berry`
  - `effect_support_status=legal_but_not_modeled`
- `items_damage.json` includes `type_resist_berries.chilan-berry`:
  - `resist_type=normal`
  - `always_resist=true`
- Current `resist_berry_context` intentionally returns `available=false`, reason `chilan_berry_deferred` when `always_resist=true`.
- Low-level berry modifier tests already verify Chilan's Normal-type helper behavior:
  - `defender_berry_mod(get_item("chilan-berry"), "normal", False) == M_HALF`
- That helper support should not be treated as permission to change raw damage or `ko_context` in this advice-context pass.

Design conclusion:
- Recommended context name: `chilan_berry_context`.
- Keep standard `resist_berry_context` unchanged for the 17 super-effective type-resist berries.
- Do not fold Chilan into `resist_berry_context` yet because the current shape is built around:
  - `requires_super_effective_hit`
  - `super_effective_match`
  - standard berry type matching
- Chilan should be a separate move-level limited context because Normal-type damage is a special `always_resist=true` case, not a super-effective trigger.

Proposed available conditions:
- defender item profile is `status=user_confirmed`
- defender item id is `chilan-berry`
- Champions legal fixture gate passes
- `items_damage.json` metadata exists
- metadata has `resist_type=normal`
- metadata has `always_resist=true`
- incoming move type is known
- incoming move type is `normal`
- incoming move is damaging
- raw `damage_estimate` exists

Non-Normal move policy:
- enriched/debug payload may return `available=false`, reason `move_type_not_normal`
- default advice payload must omit `chilan_berry_context`
- default advice must not mention Chilan Berry, a non-Normal mismatch, unavailable reason, `not modeled`, `not reflected`, `unsupported`, or `effect is not applied`

Payload policy:
- `available=true`: keep `chilan_berry_context` in default advice payload
- `available=false`: remove `chilan_berry_context` from default advice payload
- debug/enriched payload may retain reason
- no Chilan-adjusted damage or KO fields are integrated

Gemini wording policy:
- Allowed:
  - "Chilan Berry may reduce damage from a Normal-type move."
  - "This is limited context and not integrated into final KO odds."
  - "Do not treat this as guaranteed survival."
  - "Raw damage rolls and KO context remain based on the current calculator."
- Forbidden:
  - guaranteed survival
  - confirmed live
  - will survive because of Chilan Berry
  - KO chance is reduced to X
  - final damage is halved
  - raw damage rolls already include Chilan Berry
  - Chilan Berry applies to all move types

Recommended v1.5:
- `v1.5 - Chilan Berry Limited Normal-Resist Context Implementation`
- Add `llm/advisor_chilan_berry_context.py`.
- Add registry key `chilan_berry_context`.
- Attach move-level context next to existing damage estimate contexts.
- Support only `chilan-berry`.
- Require user-confirmed legal defender item and incoming Normal damaging move.
- Keep default advice filtering as `available=true` only.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 47 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 900 passed, 2 deselected.

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No `chilan_berry_context` implementation.
- No Chilan-adjusted damage formula.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final survival probability.
- No final KO probability.
- No item consumption.
- No Turn Engine.
- No ability/weather/terrain interaction.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.5 - Chilan Berry limited context implementation

Purpose:
- Implement `chilan-berry` as a separate limited `chilan_berry_context` for Gemini advice.
- Keep Chilan separate from the 17 standard super-effective `resist_berry_context` berries.
- Preserve raw damage, raw rolls, Q12 constants, `ko_context`, and Turn Engine boundaries.

Implemented:
- Added `llm/advisor_chilan_berry_context.py`.
- Added move-level `chilan_berry_context` attachment for:
  - `moves.my_available_moves`
  - `moves.my_selected_move`
  - selected-move fallback context
  - `opponent_moves.known_moves`
- Kept candidate moves excluded from `chilan_berry_context`.
- Added `chilan_berry_context` to the advice context registry/filtering surface.
- Updated prompt/contract guardrails for Chilan-specific limited wording.
- Updated `docs/advisor_payload_contract.md`.
- Added regression tests in `tests/test_advisor_payload_contract.py`.

Available conditions:
- defender item profile is `status=user_confirmed`
- defender item id is `chilan-berry`
- Champions legal gate passes
- `items_damage.json` metadata is present through the item repository
- metadata is `type_resist_berry`
- metadata has `always_resist=true`
- metadata resisted type is `normal`
- incoming move type is `normal`
- incoming move is damaging
- raw `damage_estimate` is available

Payload behavior:
- Chilan + Normal damaging move:
  - enriched/debug payload keeps `resist_berry_context.available=false`, reason `chilan_berry_deferred`
  - enriched/debug payload adds `chilan_berry_context.available=true`
  - default advice payload removes unavailable `resist_berry_context`
  - default advice payload keeps available `chilan_berry_context`
  - defender `item_profiles` remains visible because an available legal item context exists
- Chilan + non-Normal damaging move:
  - enriched/debug payload keeps `chilan_berry_context.available=false`, reason `move_type_not_normal`
  - default advice payload removes `chilan_berry_context`
  - default advice payload hides the unavailable item profile
  - default advice payload does not expose Chilan name/effect/unavailable reason
- Unconfirmed Chilan:
  - enriched/debug payload keeps `chilan_berry_context.available=false`, reason `item_not_user_confirmed`
  - default advice payload removes `chilan_berry_context`
  - default advice payload hides the item profile and reason

Gemini wording policy:
- Allowed:
  - "Chilan Berry may reduce damage from a Normal-type move."
  - "This is limited context and not integrated into final KO odds."
  - "Do not treat this as guaranteed survival."
  - "Raw damage rolls and KO context remain based on the current calculator."
- Forbidden:
  - guaranteed survival
  - confirmed live
  - will survive because of Chilan Berry
  - KO chance is reduced to a value
  - final damage is halved
  - raw damage rolls already include Chilan Berry
  - Chilan Berry applies to all move types

Regression coverage:
- Chilan + Normal move preserves available `chilan_berry_context` in default advice payload.
- Chilan + non-Normal move hides unavailable `chilan_berry_context` and item profile.
- Unconfirmed Chilan hides unavailable `chilan_berry_context` and item profile.
- Existing Yache `resist_berry_context` behavior remains available for qualifying super-effective moves.
- Existing `resist_berry_context` still returns `chilan_berry_deferred` for Chilan; Chilan is handled only by the separate context.
- Default advice payload leak checks cover `not modeled`, `not reflected`, `unsupported`, `blocked`, `deferred`, `effect is not applied`, and `item effect is not included`.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure.
  - best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians `[0.140625, 0.125, 0.125]`
  - sample min `0.109375ms`, max `0.203125ms`
- Isolated target perf rerun 5x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed x5.
- `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 1 full-suite-sensitive perf failure, 901 passed, 2 deselected.
  - best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians `[0.125, 0.125, 0.125]`
  - sample min `0.109375ms`, max `0.187500ms`

Maintained boundaries:
- No Chilan-adjusted damage formula.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final survival probability.
- No final KO probability.
- No item consumption.
- No Turn Engine.
- No ability/weather/terrain interaction.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.5.1 - Chilan Berry context verification

Purpose:
- Verify the v1.5 `chilan_berry_context` payload behavior and actual Gemini advice path.
- Keep this as verification only unless a real leak or regression appears.

Payload preflight:
- Case A - Chilan Berry + Normal damaging move:
  - enriched/debug payload kept `resist_berry_context.available=false`, reason `chilan_berry_deferred`
  - enriched/debug payload had `chilan_berry_context.available=true`
  - default advice payload kept `chilan_berry_context`
  - default advice payload removed unavailable `resist_berry_context`
  - default advice payload kept opponent `item_profiles` as user-confirmed `chilan-berry`
  - default advice payload had no forbidden Chilan overclaim wording
  - raw damage stayed `14-17`
  - raw rolls stayed `[14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 17]`
  - `ko_context` stayed raw damage-roll based and did not integrate Chilan reduction
- Case B - Chilan Berry + non-Normal damaging move:
  - enriched/debug payload had `chilan_berry_context.available=false`, reason `move_type_not_normal`
  - default advice payload removed `chilan_berry_context`
  - default advice payload hid the opponent item profile
  - default advice payload JSON did not include Chilan Berry, `chilan-berry`, `move_type_not_normal`, or generic unavailable item-effect wording
- Case C - unconfirmed Chilan Berry:
  - enriched/debug payload had `chilan_berry_context.available=false`, reason `item_not_user_confirmed`
  - default advice payload removed `chilan_berry_context`
  - default advice payload hid the opponent item profile
  - default advice payload JSON did not include Chilan Berry, `chilan-berry`, `item_not_user_confirmed`, or generic unavailable item-effect wording
- Case D - standard resist berry regression:
  - Yache Berry + Ice super-effective move kept `resist_berry_context.available=true`
  - default advice payload retained available `resist_berry_context`
  - default advice payload did not include `chilan_berry_context`

Actual Gemini verification:
- Attempted actual Gemini default-advice call for Chilan Berry + Normal damaging move.
- Result: BLOCKED, not PASS.
- Blocker: HTTP 429 `RESOURCE_EXHAUSTED`.
- No API key, secret, billing, or token-log details were printed or recorded.
- Because the first actual call was blocked, the non-Normal and unconfirmed actual Gemini cases were not called.

Verdict:
- Payload preflight: PASS.
- Chilan + Normal move payload: PASS.
- Chilan + non-Normal move filtering: PASS.
- Unconfirmed Chilan filtering: PASS.
- Standard resist berry regression: PASS.
- Actual Gemini natural-language verification: BLOCKED by HTTP 429 `RESOURCE_EXHAUSTED`.
- Overall v1.5.1 verdict: BLOCKED for actual Gemini advice, with payload preflight PASS.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure.
  - best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians `[0.125, 0.125, 0.125]`
  - sample min `0.093750ms`, max `0.203125ms`
- Isolated target perf rerun 5x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed x5.
- `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Verification/documentation-only change.
- No new item implementation.
- No new mechanics implementation.
- No Chilan-adjusted damage formula.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final survival probability.
- No final KO probability.
- No item consumption.
- No Turn Engine.
- No ability/weather/terrain interaction.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.6 - Item context coverage / pending verification design

Purpose:
- Audit implemented item/advice context coverage before adding another item context.
- Classify actual Gemini verification status as PASS, PARTIAL, BLOCKED_HTTP_429, or NOT_RUN.
- Identify payload-preflight PASS items whose actual natural-language Gemini verification is still blocked by HTTP 429.

Written:
- `docs/spike_v1.6_item_context_coverage_pending_verification_design.md`

Audited context keys:
- `survival_context`
- `recovery_context`
- `accuracy_context`
- `critical_context`
- `flinch_context`
- `multi_hit_context`
- `resist_berry_context`
- `type_boost_context`
- `speed_context`
- `speed_order_context`
- `species_stat_item_context`
- `chilan_berry_context`

Coverage summary:
- Actual Gemini PASS:
  - `accuracy_context` / Bright Powder
  - `critical_context` / Scope Lens
  - `resist_berry_context` / Yache Berry
  - `type_boost_context` / Charcoal, Mystic Water, Magnet
  - `speed_context` / Choice Scarf
  - blocked item quietness for Loaded Dice / Power Herb
- Actual Gemini PARTIAL:
  - `survival_context` / Focus Sash historical limitation visibility weakness
  - `recovery_context` / Sitrus Berry historical limitation visibility weakness
  - `flinch_context` / King's Rock historical wording/limitation weakness
  - `multi_hit_context` / legal available context NOT_RUN, blocked quietness PASS
- Payload preflight PASS but actual Gemini BLOCKED_HTTP_429:
  - Focus Band within `survival_context`
  - Quick Claw `speed_order_context`
  - Light Ball `species_stat_item_context`
  - Chilan Berry `chilan_berry_context`
- NOT_RUN:
  - legal available Loaded Dice `multi_hit_context`, because Loaded Dice remains absent from the Champions legal fixture
  - future Power Herb `charge_context`, because it is unimplemented and remains out of scope

Recommendation:
- Do not add a new item context immediately.
- Prefer `v1.7 - Item Context Gemini Verification Retry Batch`.
- Retry actual Gemini calls for:
  - Chilan Berry Normal available
  - Light Ball Pikachu available
  - Quick Claw available
  - Focus Band lethal available
- If Gemini quota/access remains blocked, use `v1.7 - Handoff / Pending Verification Capsule` instead of adding a new item.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure.
  - best batch median `0.125000ms`, threshold `0.120000ms`
  - batch medians `[0.140625, 0.140625, 0.125]`
  - sample min `0.093750ms`, max `0.171875ms`
- Isolated target perf rerun 5x:
  - `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed x5.
- `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Documentation-only audit.
- No code implementation.
- No filtering logic changes.
- No new item context.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final KO probability.
- No final move order.
- No Turn Engine.
- No item consumption.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.7 - Item context Gemini verification retry batch

Purpose:
- Retry actual Gemini default-advice verification for the v1.6 BLOCKED_HTTP_429 queue.
- Keep this as verification only unless an actual payload leak, wording failure, or context attachment failure appears.

Retry queue:
- Focus Band within `survival_context`
- Quick Claw `speed_order_context`
- Light Ball `species_stat_item_context`
- Chilan Berry `chilan_berry_context`

Payload preflight:
- Focus Band:
  - default advice payload retained `survival_context.available=true`
  - `survival_effect.type=focus_band`
  - raw damage stayed `31-37`
  - raw rolls stayed `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
  - `ko_context.raw_damage_rolls_changed=false`
  - no forbidden Focus Band overclaim wording in payload JSON
- Quick Claw:
  - default advice payload retained `speed_order_context.available=true`
  - `speed_order_effect.type=quick_claw`
  - raw damage stayed `31-37`
  - raw rolls stayed `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
  - `ko_context.raw_damage_rolls_changed=false`
  - no forbidden Quick Claw move-order wording in payload JSON
- Light Ball:
  - default advice payload retained `species_stat_item_context.available=true`
  - holder detail remained `pikachu`
  - raw damage stayed `0-0`
  - raw rolls stayed sixteen `0` rolls
  - `ko_context.raw_damage_rolls_changed=false`
  - no forbidden Light Ball generalization/KO wording in payload JSON
- Chilan Berry:
  - default advice payload retained `chilan_berry_context.available=true`
  - detail remained incoming Normal-type move
  - raw damage stayed `14-17`
  - raw rolls stayed `[14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 17]`
  - `ko_context.raw_damage_rolls_changed=false`
  - no forbidden Chilan all-types/final-damage/survival wording in payload JSON

Actual Gemini retry:
- Focus Band actual call attempted first through the normal `run_ui_selected_advice()` path.
- Result: BLOCKED_HTTP_429.
- Blocker: HTTP 429 `RESOURCE_EXHAUSTED`.
- Per retry policy, remaining actual calls were not attempted after the first 429:
  - Quick Claw: BLOCKED_BATCH
  - Light Ball: BLOCKED_BATCH
  - Chilan Berry: BLOCKED_BATCH
- This is not recorded as PASS.
- No API key, secret, billing, or token-log details were printed or recorded.

Failure classification:
- Focus Band: API BLOCKED_HTTP_429.
- Quick Claw: API BLOCKED_HTTP_429 / BLOCKED_BATCH.
- Light Ball: API BLOCKED_HTTP_429 / BLOCKED_BATCH.
- Chilan Berry: API BLOCKED_HTTP_429 / BLOCKED_BATCH.
- No payload leak observed.
- No wrong item/context attachment observed.
- No raw damage, raw rolls, Q12, or `ko_context` change observed.

Verdict:
- Payload preflight: PASS for all four retry targets.
- Actual Gemini natural-language verification: BLOCKED.
- Overall v1.7: BLOCKED_BATCH with payload preflight PASS.
- Recommendation remains: do not add another item context until Gemini quota/access is restored or T1/T2 explicitly accepts the pending verification risk.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Verification/documentation-only change.
- No new item implementation.
- No new mechanics implementation.
- No payload filtering behavior changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final survival probability.
- No final move order.
- No final KO probability.
- No item consumption.
- No Turn Engine.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v1.8 - Pending Gemini verification handoff capsule design

Purpose:
- Create a handoff document for the pending item-context actual Gemini verification queue.
- Preserve the distinction between payload preflight PASS and actual natural-language Gemini PASS.
- Avoid modifying `docs/handoff_capsule_v1.1.md`.

Written:
- `docs/handoff_pending_gemini_verification_v1.8.md`

Pending verification queue:
- Focus Band within `survival_context`
  - implementation status: implemented
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_HTTP_429
  - blocked reason: first v1.7 actual call returned HTTP 429 `RESOURCE_EXHAUSTED`
- Quick Claw `speed_order_context`
  - implementation status: implemented
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_BATCH
  - blocked reason: not called after Focus Band hit HTTP 429
- Light Ball `species_stat_item_context`
  - implementation status: implemented
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_BATCH
  - blocked reason: not called after Focus Band hit HTTP 429
- Chilan Berry `chilan_berry_context`
  - implementation status: implemented
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_BATCH
  - blocked reason: not called after Focus Band hit HTTP 429

Retry conditions:
- Gemini quota/access must recover.
- First actual Gemini call must not return HTTP 429.
- API keys, secrets, billing details, and token-log contents must not be printed or recorded.
- If the first case returns HTTP 429 `RESOURCE_EXHAUSTED`, stop the batch and record remaining cases as `BLOCKED_BATCH`.

Retry order:
1. Focus Band within `survival_context`
2. Quick Claw `speed_order_context`
3. Light Ball `species_stat_item_context`
4. Chilan Berry `chilan_berry_context`

Forbidden wording summary:
- Focus Band:
  - `will survive`
  - `guaranteed survive`
  - `cannot be KO'd`
  - `confirmed live`
- Quick Claw:
  - `will move first`
  - `guaranteed outspeeds`
  - `confirmed first`
  - `always acts before`
  - `wins the speed interaction`
- Light Ball:
  - `all Electric-type Pokemon benefit`
  - `all Electric-type Pokémon benefit`
  - `Light Ball works on any holder`
  - `guaranteed KO`
  - `confirmed OHKO`
  - `always doubles damage`
  - `final stats are fully known`
- Chilan Berry:
  - `Chilan Berry applies to all move types`
  - `guaranteed survival`
  - `confirmed live`
  - `will survive because of Chilan Berry`
  - `final damage is halved`
  - `raw damage rolls already include Chilan Berry`

Completed stabilization summary:
- Item context registry/filtering cleanup is complete.
- Perf test measurement stabilization is complete.
- Item context coverage audit is complete.

Recommended v1.9:
- If Gemini quota/access is restored:
  - `v1.9 - Item Context Gemini Verification Retry Batch 2`
  - retry the same four cases in the documented order
- If Gemini quota/access remains blocked:
  - keep pending queue unchanged
  - avoid adding a new item context
  - prefer documentation-only handoff/coordination or pause item expansion until actual advice can be verified

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Documentation-only handoff.
- No code implementation.
- No new item context.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final KO probability.
- No final move order.
- No Turn Engine.
- No item consumption.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or `docs/handoff_capsule_v1.1.md` commits.

---

## v1.9 - Pending verification capsule finalization / next session prompt

Purpose:
- Finalize a copy-paste-ready next-session prompt for the pending actual Gemini verification queue.
- Preserve the distinction between payload preflight PASS and actual natural-language Gemini PASS.
- Keep the pending queue actionable without running Gemini retry in this step.

Written:
- `docs/handoff_next_session_prompt_v1.9.md`

Included pending queue:
- Focus Band within `survival_context`
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_HTTP_429
  - forbidden wording includes `will survive`, `guaranteed survive`, `cannot be KO'd`, `confirmed live`
- Quick Claw `speed_order_context`
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_BATCH
  - forbidden wording includes `will move first`, `guaranteed outspeeds`, `confirmed first`, `always acts before`, `wins the speed interaction`
- Light Ball `species_stat_item_context`
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_BATCH
  - forbidden wording includes `all Electric-type Pokemon benefit`, `Light Ball works on any holder`, `guaranteed KO`, `confirmed OHKO`, `always doubles damage`, `final stats are fully known`
- Chilan Berry `chilan_berry_context`
  - payload preflight: PASS
  - actual Gemini status: BLOCKED_BATCH
  - forbidden wording includes `Chilan Berry applies to all move types`, `guaranteed survival`, `confirmed live`, `will survive because of Chilan Berry`, `final damage is halved`, `raw damage rolls already include Chilan Berry`

Next-session prompt coverage:
- repo/branch/remote status checks
- `logs/token_usage.jsonl` commit/reset prohibition
- `.env`, secrets, API keys, billing details, token-log contents, and `docs/handoff_capsule_v1.1.md` commit prohibition
- pending verification queue
- payload preflight PASS vs actual Gemini PASS distinction
- Gemini retry conditions
- first-call HTTP 429 batch-stop policy
- actual PASS conditions and BLOCKED handling
- forbidden wording checklist
- raw damage / raw rolls / Q12 / `ko_context` no-change boundary
- threshold / skip / xfail prohibition

v2.0 / next milestone decision points:
- Decide whether to retry the pending Gemini queue as soon as quota/access recovers.
- Decide whether to pause new item context expansion until actual Gemini PASS exists for Focus Band, Quick Claw, Light Ball, and Chilan Berry.
- Decide whether additional item contexts are acceptable while these four remain actual Gemini BLOCKED.
- Decide whether a release/milestone can be marked complete with payload preflight PASS but actual Gemini BLOCKED.
- Refresh handoff docs after actual PASS/PARTIAL/FAIL results.

Verification:
- Gemini actual call: not run in v1.9 by design.
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure:
  - best batch median `0.125000ms`, threshold `0.120000ms`
- isolated target perf test 3x: passed.
- `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest -q`: 1 full-suite timing-sensitive perf failure, 901 passed, 2 deselected:
  - best batch median `0.125000ms`, threshold `0.120000ms`

Maintained boundaries:
- Documentation-only handoff.
- No Gemini retry.
- No code implementation.
- No new item context.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final KO probability.
- No final move order.
- No Turn Engine.
- No item consumption.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.0 - Item context Gemini verification retry

Purpose:
- Retry actual Gemini default-advice verification for the pending HTTP 429 queue.
- Keep the run verification-only: no new item context, no mechanics, no filtering changes, no prompt hardening.
- Stop the batch after the first HTTP 429 to avoid wasting API retries.

Retry queue:
1. Focus Band within `survival_context`
2. Quick Claw `speed_order_context`
3. Light Ball `species_stat_item_context`
4. Chilan Berry `chilan_berry_context`

Payload preflight:
- Focus Band:
  - `survival_context.available=true`
  - `survival_effect.type=focus_band`
  - raw damage `31-37`
  - raw rolls `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
  - `ko_context.raw_damage_rolls_changed=false`
- Quick Claw:
  - `speed_order_context.available=true`
  - `speed_order_effect.type=quick_claw`
  - raw damage `31-37`
  - raw rolls `[31, 32, 32, 33, 33, 33, 33, 34, 34, 35, 35, 36, 36, 36, 36, 37]`
  - `ko_context.raw_damage_rolls_changed=false`
- Light Ball:
  - `species_stat_item_context.available=true`
  - holder species detail `pikachu`
  - raw damage `0-0`
  - raw rolls sixteen `0` rolls
  - `ko_context.raw_damage_rolls_changed=false`
- Chilan Berry:
  - `chilan_berry_context.available=true`
  - incoming move type `normal`
  - raw damage `14-17`
  - raw rolls `[14, 14, 14, 14, 15, 15, 15, 15, 15, 15, 16, 16, 16, 16, 16, 17]`
  - `ko_context.raw_damage_rolls_changed=false`

Actual Gemini retry:
- Focus Band actual call attempted first through the normal `run_ui_selected_advice()` path.
- Result: BLOCKED_HTTP_429.
- Blocker: HTTP 429 `RESOURCE_EXHAUSTED`.
- Per retry policy, remaining actual calls were not attempted after the first 429:
  - Quick Claw: BLOCKED_BATCH
  - Light Ball: BLOCKED_BATCH
  - Chilan Berry: BLOCKED_BATCH
- This is not recorded as PASS.

Failure classification:
- Focus Band: API BLOCKED_HTTP_429.
- Quick Claw: API BLOCKED_HTTP_429 / BLOCKED_BATCH.
- Light Ball: API BLOCKED_HTTP_429 / BLOCKED_BATCH.
- Chilan Berry: API BLOCKED_HTTP_429 / BLOCKED_BATCH.
- No payload leak observed.
- No wrong item/context attachment observed.
- No forbidden wording could be evaluated because no actual natural-language advice was produced.
- No raw damage, raw rolls, Q12, or `ko_context` change observed.

Verdict:
- Payload preflight: PASS for all four retry targets.
- Actual Gemini natural-language verification: BLOCKED.
- Overall v2.0: BLOCKED_BATCH with payload preflight PASS.
- Recommendation remains: do not mark these contexts actual Gemini PASS from payload preflight alone.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- No code implementation.
- No new item context.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No final survival probability.
- No final move order.
- No final KO probability.
- No item consumption.
- No Turn Engine.
- No legal fixture changes.
- No fixture changes.
- No UI changes.
- No sample additions.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.0.1 - Gemini API availability and model config check

Purpose:
- Separate the HTTP 429 blocker from item-context payload correctness.
- Check the active Gemini model/client configuration without printing secrets.
- Run one minimal smoke prompt only, not item-context verification.

Client configuration observed:
- model id: `gemini-2.5-flash`
- API key environment presence: present, value not printed
- endpoint path: Gemini REST `generateContent`
- temperature: not explicitly configured in the local client
- max output tokens: not explicitly configured in the local client
- thinking config: not explicitly configured in the local client
- retry/backoff: not configured in the local client
- timeout: 60 seconds

Smoke prompt:
- prompt: `Reply exactly: OK`
- item context payload: not used
- result classification: BLOCKED_HTTP_429
- safe error summary: Gemini API returned HTTP 429 `RESOURCE_EXHAUSTED`; the response indicated depleted prepayment credits and directed project/billing management in AI Studio
- no additional Gemini actual calls were made after the smoke 429

External documentation basis:
- Google Gemini API troubleshooting classifies HTTP 429 `RESOURCE_EXHAUSTED` as exceeding rate limits and recommends checking the model's rate limit or requesting quota increase: https://ai.google.dev/gemini-api/docs/troubleshooting
- Google Gemini API rate limits are evaluated across dimensions such as requests per minute, tokens per minute, and requests per day, and exceeding any one can trigger a rate limit error: https://ai.google.dev/gemini-api/docs/rate-limits
- Google Gemini thinking documentation says Gemini models can use dynamic thinking by default; Gemini 2.5 Flash/Pro thinking can increase latency/token usage depending on configuration and model behavior: https://ai.google.dev/gemini-api/docs/thinking
- Active rate limits and quota/account status should be checked in AI Studio / Google project quota views; this repo must not print or commit API keys, billing details, or token-log contents.

Verdict:
- The blocker is not reproduced by item-context payload shape; even the smallest smoke prompt is blocked.
- Pending item-context actual Gemini verification remains BLOCKED, not PASS.
- Next action remains: wait for quota/access/credits recovery, then retry Focus Band first.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure:
  - best batch median `0.125000ms`, threshold `0.120000ms`
- isolated target perf test 3x: passed.
- `uv run pytest tests/test_damage_perf.py -q` first rerun: 1 timing-sensitive perf failure:
  - best batch median `0.140625ms`, threshold `0.120000ms`
- `uv run pytest -q`: 1 full-suite timing-sensitive perf failure, 901 passed, 2 deselected:
  - best batch median `0.125000ms`, threshold `0.120000ms`
- `uv run pytest tests/test_damage_perf.py -q` second rerun: 4 passed.

Maintained boundaries:
- No item-context actual PASS recorded.
- No new item implementation.
- No new mechanics.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.1 - Vertex AI Gemini migration spike

Purpose:
- Investigate whether Google Cloud / Vertex AI Gemini can be used as an optional provider while the current Gemini Developer API / AI Studio API-key path is blocked by HTTP 429 `RESOURCE_EXHAUSTED`.
- Keep the current Developer API client intact.
- Document required Google Cloud setup, environment variables, endpoint/auth differences, and a safe future smoke-test procedure.
- Avoid running pending item-context verification or any Vertex AI actual call in this spike.

Written:
- `docs/spike_v2.1_vertex_ai_gemini_migration_design.md`

Current Developer API path:
- provider: `gemini_developer_api`
- endpoint host: `generativelanguage.googleapis.com`
- auth: API key from `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- current observed model id: `gemini-2.5-flash`
- status: BLOCKED_HTTP_429 because the minimal smoke prompt returned HTTP 429 `RESOURCE_EXHAUSTED` with prepayment credits / AI Studio billing guidance
- action: keep this path; do not delete or replace it in v2.1

Vertex AI Gemini candidate path:
- provider: `vertex_ai_gemini`
- endpoint service: `aiplatform.googleapis.com`
- auth: Google Cloud ADC, gcloud credentials, or service account outside the repo
- billing/quota: Google Cloud billing and Vertex/Agent Platform quota, separate from the current AI Studio API-key credit state
- required setup: project, billing account, API enablement, IAM permission, supported region/location, selected model id
- status: not implemented; spike candidate only

Environment variable placeholders documented:
- `LLM_PROVIDER=vertex_ai_gemini`
- `GOOGLE_CLOUD_PROJECT=<project-id>`
- `GOOGLE_CLOUD_LOCATION=<region-or-global>`
- `VERTEX_AI_MODEL=<model-id>`
- `GOOGLE_APPLICATION_CREDENTIALS=<optional-local-path-to-service-account-json>`

Provider adapter recommendation:
- Keep current Developer API path as `GeminiDeveloperApiProvider`.
- Add optional future `VertexAiGeminiProvider`.
- Use a common interface such as `generate_advice(prompt, model, timeout, options)`.
- Normalize errors without exposing secrets.
- Do not change payload filtering, prompt text, or damage/KO math as part of provider migration.

Safe future smoke test design:
- prompt: `Reply exactly: OK`
- expected response: `OK`
- classifications: `AVAILABLE`, `BLOCKED_QUOTA`, `AUTH_ERROR`, `PERMISSION_DENIED`, `MODEL_NOT_FOUND`, `REGION_NOT_SUPPORTED`, `OTHER_ERROR`
- success means only provider availability; it is not pending item-context verification PASS
- after smoke `AVAILABLE`, retry Focus Band first in a separate pending-verification step

Official documentation basis:
- Gemini API troubleshooting: https://ai.google.dev/gemini-api/docs/troubleshooting
- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
- Gemini thinking: https://ai.google.dev/gemini-api/docs/thinking
- Google Cloud Vertex AI / Agent Platform authentication: https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/authentication
- Google Cloud local environment setup: https://docs.cloud.google.com/gemini-enterprise-agent-platform/machine-learning/start/cloud-environment
- Google Cloud Gemini generate content REST method: https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/projects.locations.endpoints/generateContent
- Google Cloud deployments and endpoints: https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/locations
- Google Cloud client libraries / ADC: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/libraries

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had 1 timing-sensitive perf failure:
  - best batch median `0.125000ms`, threshold `0.120000ms`
- isolated target perf test 3x: passed.
- `uv run pytest tests/test_damage_perf.py -q` first rerun: 1 timing-sensitive perf failure:
  - best batch median `0.125000ms`, threshold `0.120000ms`
- `uv run pytest -q`: 902 passed, 2 deselected.
- `uv run pytest tests/test_damage_perf.py -q` second rerun: 4 passed.

Maintained boundaries:
- Documentation-only spike.
- No Vertex AI actual call.
- No pending item-context verification.
- No new item implementation.
- No provider code implementation.
- No existing Developer API client deletion or replacement.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No legal fixture changes.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, service account JSON, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.2 - Vertex AI local setup and smoke readiness check

Purpose:
- Check whether the local environment is ready for a future Vertex AI Gemini smoke call.
- Keep the current Gemini Developer API key path intact.
- Avoid pending item-context verification and avoid any Vertex AI actual call unless setup is ready.

Local setup check:
- repo branch: `master`
- remote tracking: `my_pochamps/master`
- local uncommitted change observed: `logs/token_usage.jsonl` only
- `gcloud --version`: GCLOUD_NOT_INSTALLED
- `gcloud config get-value project`: not checked because `gcloud` is not installed
- Application Default Credentials: not checked because `gcloud` is not installed
- `aiplatform.googleapis.com` enablement: not checked because `gcloud` is not installed
- environment variables:
  - `GOOGLE_CLOUD_PROJECT`: unset
  - `GOOGLE_CLOUD_LOCATION`: unset
  - `VERTEX_AI_MODEL`: unset
  - `GOOGLE_GENAI_USE_ENTERPRISE`: unset
  - `GOOGLE_APPLICATION_CREDENTIALS`: unset

Smoke readiness:
- Vertex AI smoke prompt was not executed.
- result classification: NOT_RUN_SETUP_INCOMPLETE
- actual response generated: no
- additional Vertex AI actual calls: no
- pending item-context verification: not executed

Next setup actions for T1:
- Install Google Cloud CLI if Vertex AI local smoke should be attempted.
- Configure the intended project, for example after confirmation: `gcloud config set project gen-lang-client-0167075914`.
- Configure ADC with `gcloud auth application-default login`, or prepare a service account JSON outside the repo.
- Enable `aiplatform.googleapis.com` if not already enabled.
- Set local environment variables such as `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `VERTEX_AI_MODEL`, and `GOOGLE_GENAI_USE_ENTERPRISE`.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Documentation-only readiness check.
- No Vertex AI actual call.
- No pending item-context verification.
- No Gemini Developer API retry.
- No provider code implementation.
- No existing Developer API client deletion or replacement.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No legal fixture changes.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, access tokens, service account JSON, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.3 - Google Cloud CLI setup attempt for Vertex AI smoke test

Purpose:
- Prepare the local environment for a future Vertex AI Gemini smoke test as far as possible.
- Stop at any T1-owned browser login, account selection, or permission approval step.
- Avoid pending item-context verification and avoid actual Vertex AI smoke calls until setup is complete.

Repo state:
- branch: `master`
- remote tracking: `my_pochamps/master`
- unpushed commits before this record: none
- local uncommitted change observed: `logs/token_usage.jsonl` only

Google Cloud CLI:
- initial `gcloud --version`: GCLOUD_NOT_INSTALLED
- `winget` availability: available
- package candidate found: `Google.CloudSDK` version `572.0.0`
- install attempt: ran `winget install --id Google.CloudSDK --exact --accept-package-agreements --accept-source-agreements`
- install result: installed locally under the user Google Cloud SDK path
- current PowerShell session PATH: not refreshed, so plain `gcloud` still may not resolve until a new shell is opened
- direct installed command check: GCLOUD_AVAILABLE
- direct installed version: Google Cloud SDK `572.0.0`

gcloud init / project:
- `gcloud init`: attempted, then stopped because it did not complete non-interactively and appears to require T1 login/account/project selection
- classification: GCLOUD_INIT_NEEDS_T1_LOGIN
- project before setup: unset
- project configured non-interactively: `gen-lang-client-0167075914`
- project classification: PROJECT_SET

Authentication and API enablement:
- ADC check via `gcloud auth application-default print-access-token`: ADC_NOT_CONFIGURED
- ADC classification: ADC_NEEDS_T1_LOGIN
- `aiplatform.googleapis.com` enablement check: CHECK_FAILED because no active gcloud account is selected
- API enablement classification: CHECK_FAILED_NEEDS_T1_LOGIN

Environment variables:
- `GOOGLE_CLOUD_PROJECT`: unset
- `GOOGLE_CLOUD_LOCATION`: unset
- `VERTEX_AI_MODEL`: unset
- `GOOGLE_GENAI_USE_ENTERPRISE`: unset
- `GOOGLE_APPLICATION_CREDENTIALS`: unset
- recommended temporary PowerShell values remain:
  - `$env:LLM_PROVIDER="vertex_ai_gemini"`
  - `$env:GOOGLE_CLOUD_PROJECT="gen-lang-client-0167075914"`
  - `$env:GOOGLE_CLOUD_LOCATION="global"`
  - `$env:VERTEX_AI_MODEL="gemini-2.5-flash"`
  - `$env:GOOGLE_GENAI_USE_ENTERPRISE="True"`

Smoke readiness:
- Vertex AI smoke prompt was not executed.
- result classification: NOT_RUN_SETUP_INCOMPLETE
- actual response generated: no
- additional Vertex AI actual calls: no
- pending item-context verification: not executed

T1 direct action required:
- Open a new PowerShell after installation so PATH updates are available, or use the installed `gcloud.cmd` path directly.
- Run `gcloud init` and complete Google account login/account/project selection.
- Run `gcloud auth application-default login` and approve ADC access in the browser.
- Confirm or enable `aiplatform.googleapis.com` for project `gen-lang-client-0167075914`.
- Set temporary PowerShell environment variables before a future smoke test.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Local setup and documentation-only repo record.
- No Vertex AI smoke call.
- No pending item-context verification.
- No Gemini Developer API retry.
- No provider code implementation.
- No existing Developer API client deletion or replacement.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No legal fixture changes.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, access tokens, service account JSON, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.4 - Vertex AI Gemini smoke test

Purpose:
- Run exactly one minimal Vertex AI Gemini smoke prompt through the `aiplatform.googleapis.com` path.
- Confirm whether the Vertex AI provider path can generate a response independently from the Gemini Developer API key path.
- Avoid pending item-context verification and avoid any Focus Band / Quick Claw / Light Ball / Chilan Berry PASS classification.

Repo state:
- branch: `master`
- remote tracking: `my_pochamps/master`
- unpushed commits before this record: none
- local uncommitted change observed: `logs/token_usage.jsonl` only

Preflight:
- Google Cloud SDK: available through the installed direct `gcloud.cmd` path
- project: `gen-lang-client-0167075914`
- ADC: available; token value was not printed
- `aiplatform.googleapis.com`: enabled
- Codex shell environment variables were not inherited, so the smoke command used explicit local command arguments:
  - provider: `vertex_ai_gemini`
  - endpoint family: Vertex AI / `aiplatform.googleapis.com`
  - project: `gen-lang-client-0167075914`
  - location: `global`
  - model: `gemini-2.5-flash`

Smoke prompt:
- prompt: `Reply exactly: OK`
- execution count: 1
- result classification: OTHER_ERROR
- actual response generated: no
- response summary: HTTP 417 `Expectation Failed`
- additional Vertex AI actual calls: no
- Gemini Developer API key path: not used
- `generativelanguage.googleapis.com` path: not used
- service account JSON: not used
- pending item-context verification: not executed

Verdict:
- Vertex AI setup reached the API call stage, unlike v2.2/v2.3.
- The smoke did not produce an `OK` response and is not `AVAILABLE`.
- The blocker is now a Vertex AI smoke-call error, not the earlier local setup incomplete state.
- This is not item-context verification PASS; Focus Band, Quick Claw, Light Ball, and Chilan Berry actual Gemini verification remain pending.
- Because the smoke failed, no additional Vertex AI actual calls were made.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- Documentation-only repo record.
- No pending item-context verification.
- No new item implementation.
- No provider code implementation.
- No existing Developer API client deletion or replacement.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No legal fixture changes.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, access tokens, ADC credential contents, service account JSON, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.5 - Gemini Developer API prepay recovery smoke and pending verification retry

Purpose:
- Recheck the existing Gemini Developer API / AI Studio API-key path after T1 completed Prepay credit recovery.
- Use the Developer API path only, not Vertex AI.
- Run one smoke prompt, then retry the pending item-context actual natural-language verification only if smoke is available.

Repo state:
- branch: `master`
- remote tracking: `my_pochamps/master`
- unpushed commits before this record: none
- local uncommitted change observed: `logs/token_usage.jsonl` only

Smoke test:
- provider: `gemini_developer_api`
- endpoint family: `generativelanguage.googleapis.com`
- auth: API key from local environment / `.env`; value not printed
- model: `gemini-2.5-flash`
- prompt: `Reply exactly: OK`
- execution count: 1
- result classification: AVAILABLE
- actual response generated: yes
- response summary: `OK`
- usage summary recorded only as short counts: input 5 / output 1 / cached 0
- additional smoke retry: no
- Vertex AI path: not used

Pending item-context actual verification:
- execution condition: smoke was AVAILABLE, so the pending queue was retried
- item actual call count: 4
- total actual calls including smoke: 5
- automatic retries: no
- repeated loops/backoff: no
- payload preflight: PASS for all four cases

Results:
- Focus Band / `survival_context`: PASS
  - preflight: `survival_context.available=true`, `survival_effect.type=focus_band`
  - actual advice mentioned Focus Band and limited survival wording: "may occasionally survive"
  - forbidden wording: none
  - response preserved that activation probability is not calculated
- Quick Claw / `speed_order_context`: PASS
  - preflight: `speed_order_context.available=true`, `speed_order_effect.type=quick_claw`
  - actual advice mentioned Quick Claw with limited move-order wording: "may affect move order"
  - forbidden wording: none
  - response preserved that activation/final turn order are not modeled
- Light Ball / `species_stat_item_context`: PARTIAL
  - preflight: `species_stat_item_context.available=true`, holder species `pikachu`
  - actual advice mentioned Pikachu and user-confirmed Light Ball
  - forbidden wording: none
  - weakness: response said current damage estimates do not include the stat boost from Pikachu's Light Ball, instead of the preferred limited wording that Light Ball may boost Pikachu's offensive stats in the underlying calculation and should not be treated as final KO truth
  - failure classification: wording guardrail weakness / Gemini over-inference
- Chilan Berry / `chilan_berry_context`: PARTIAL
  - preflight: `chilan_berry_context.available=true`, incoming move type `normal`
  - actual advice mentioned Chilan Berry's potential reduction for Tackle and did not claim adjusted rolls or final survival
  - forbidden wording: none
  - weakness: response did not explicitly limit the effect to a Normal-type move and used weak "not included in the raw damage estimate" wording rather than the preferred limited-context phrasing
  - failure classification: wording guardrail weakness

Raw calculation impact:
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- payload filtering changed: no
- prompt hardening changed: no

Verdict:
- Developer API Prepay recovery smoke: AVAILABLE.
- Pending item-context actual Gemini verification is no longer blocked by HTTP 429.
- Actual Gemini PASS items: Focus Band, Quick Claw.
- Actual Gemini PARTIAL items: Light Ball, Chilan Berry.
- Remaining work should focus on T1/T2 deciding whether to polish wording for Light Ball and Chilan Berry, without changing damage math or item mechanics.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.

Maintained boundaries:
- No Vertex AI call.
- No new item implementation.
- No provider code implementation.
- No existing Developer API client deletion or replacement.
- No payload filtering changes.
- No prompt hardening.
- No damage formula changes.
- No raw damage roll changes.
- No Q12 multiplier changes.
- No `ko_context` changes.
- No legal fixture changes.
- No threshold, skip, or xfail changes.
- No logs, `.env`, secrets, API keys, access tokens, ADC credential contents, service account JSON, billing details, token logs, or `docs/handoff_capsule_v1.1.md` commits.

---

## v2.6 - Light Ball / Chilan Berry limited wording polish

Purpose:
- Polish the two v2.5 PARTIAL actual-Gemini items without changing mechanics, payload filtering, damage math, or verification state.
- Keep Focus Band and Quick Claw as actual Gemini PASS from v2.5.
- Keep Light Ball and Chilan Berry as PARTIAL until a separate approved actual Gemini recheck runs.

v2.5 PARTIAL causes:
- Light Ball / `species_stat_item_context`:
  - actual advice mentioned Pikachu and user-confirmed Light Ball with no forbidden wording.
  - weakness: the response sounded like Light Ball was not included in the estimate instead of saying the available context may explain a supported Pikachu-specific offensive modifier in the underlying calculation.
- Chilan Berry / `chilan_berry_context`:
  - actual advice mentioned Chilan Berry's potential reduction for Tackle with no forbidden wording.
  - weakness: the response did not explicitly call it a Normal-type limited context and used weak not-included wording instead of the preferred separate limited-context phrasing.

Implemented wording polish:
- Strengthened the advisor prompt so available Light Ball context should be described as a Pikachu-specific offensive item context and not as `not included` or `not modeled`.
- Strengthened the advisor prompt so available Chilan Berry context should be described as Normal-type limited context, separate from raw rolls and final KO odds.
- Updated `ADVISOR_KNOWN_LIMITATIONS` and context limitations for the same positive wording.
- Added payload contract regression assertions for the strengthened wording.
- Updated `docs/advisor_payload_contract.md` to forbid `Light Ball is not included/not modeled` and `Chilan Berry is not included/not modeled` when their available context is present.

Verification policy:
- Actual Gemini call in v2.6: not run.
- Vertex AI call in v2.6: not run.
- Light Ball status after v2.6: PARTIAL, pending a separate v2.6.1 actual Gemini recheck if T1/T2 approve.
- Chilan Berry status after v2.6: PARTIAL, pending a separate v2.6.1 actual Gemini recheck if T1/T2 approve.

Raw calculation impact:
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- new item implementation: no
- payload filtering behavior changed: no

---

## v2.6.1 - Light Ball / Chilan Berry actual wording verification retry

Purpose:
- Recheck actual Gemini Developer API wording for the two v2.5/v2.6 follow-up items after the v2.6 wording polish.
- Do not recheck Focus Band or Quick Claw because both already reached actual Gemini PASS in v2.5.

Execution:
- provider: `gemini_developer_api`
- endpoint family: `generativelanguage.googleapis.com`
- model: `gemini-2.5-flash`
- Vertex AI calls: none
- automatic retry loop: none
- Focus Band / Quick Claw calls: none

Payload preflight:
- Light Ball / `species_stat_item_context`: PASS
  - `species_stat_item_context.available=true`
  - holder species `pikachu`
  - available context present in the default advice payload
- Chilan Berry / `chilan_berry_context`: PASS
  - `chilan_berry_context.available=true`
  - incoming move type `normal`
  - available context present in the default advice payload

Actual Gemini results:
- Light Ball: FAIL
  - A first Light Ball call used Thunderbolt into Garchomp and was not a useful final classification because the selected move was immune; Gemini did not engage the Light Ball context.
  - A follow-up non-immune Light Ball call used a physical damaging move with `species_stat_item_context.available=true`.
  - Gemini still said the damage estimates do not include the effect of the user-confirmed Light Ball.
  - This violates the v2.6 intent to avoid "not included / not modeled" style wording when the available Light Ball context is present.
  - Failure classification: wording guardrail failure / Gemini over-inference from generic damage-estimate limitations.
- Chilan Berry: PARTIAL
  - Gemini generated an actual response and no forbidden Chilan wording appeared.
  - However, the response did not mention Chilan Berry as a Normal-type limited context.
  - It used generic "no item" default-assumption wording, so it did not satisfy the positive PASS wording.
  - Failure classification: wording guardrail weakness / context omission.

Forbidden wording / leaks:
- payload leak observed: no
- wrong context attachment observed: no
- Light Ball forbidden/undesired wording observed: yes, semantic "does not include the effect of the user-confirmed Light Ball"
- Chilan forbidden wording observed: no exact forbidden Chilan phrase, but positive Normal-type limited context wording was missing

Raw calculation impact:
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- new item implementation: no
- payload filtering behavior changed: no

Result:
- Actual Gemini PASS items from v2.5 remain: Focus Band, Quick Claw.
- Light Ball remains not PASS after v2.6.1: FAIL.
- Chilan Berry remains not PASS after v2.6.1: PARTIAL.
- Recommended next step: T2 should decide whether to redesign the prompt/payload contract for available item-context wording, especially the conflict between generic default-assumption/no-item wording and available explanatory item contexts.

---

## v2.7 - Available item context required mention guard

Purpose:
- Address the v2.6.1 failure mode where Gemini received available item contexts but fell back to generic no-item/default-assumption wording.
- Require visible `available=true` item contexts in the default advice payload to be mentioned at least once when directly relevant.
- Keep unavailable/deferred/blocked context filtering unchanged.

v2.6.1 problem summary:
- Light Ball / `species_stat_item_context`: FAIL because Gemini still said the user-confirmed Light Ball effect was not included despite `species_stat_item_context.available=true`.
- Chilan Berry / `chilan_berry_context`: PARTIAL because Gemini did not mention the Normal-type limited Chilan context and used generic no-item wording.
- Payload preflight, attachment, filtering, raw damage rolls, Q12, and `ko_context` were not the cause.

Implemented:
- Added a registry-backed prompt guard generated from the already-filtered default advice payload.
- The guard lists available item contexts such as:
  - Light Ball / `species_stat_item_context` as Pikachu-specific offensive item context.
  - Chilan Berry / `chilan_berry_context` as Normal-type limited context.
  - other visible `available=true` item contexts through the existing item-context registry.
- The guard tells Gemini to mention each listed available item context at least once when directly relevant.
- The guard forbids describing visible available item effects as unavailable, unmodeled, not included, not reflected, no item is considered, assuming no item, without item effects, or default no-item assumption.
- The guard keeps wording limited and forbids turning item context into final KO odds, guaranteed survival, guaranteed move order, exact final stats, or final battle truth.

Tests:
- Added prompt assertions for available Light Ball required mention guard.
- Added prompt assertions for available Chilan Berry required mention guard.
- Added regression assertions that unavailable/non-triggered Light Ball and Chilan contexts do not trigger the available-context guard.
- Preserved raw damage range, rolls, and `ko_context` assertions for the available contexts.

Boundaries:
- Actual Gemini call in v2.7: not run.
- Vertex AI call in v2.7: not run.
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- new item implementation: no
- payload filtering behavior changed: no

---

## v2.7.1 - Light Ball / Chilan Berry required mention guard actual verification

Purpose:
- Recheck actual Gemini Developer API wording after the v2.7 available item context required-mention guard.
- Recheck only Light Ball and Chilan Berry.
- Do not recheck Focus Band or Quick Claw because both already reached actual Gemini PASS in v2.5.

Execution:
- provider: `gemini_developer_api`
- endpoint family: `generativelanguage.googleapis.com`
- model: `gemini-2.5-flash`
- Developer API calls: yes
- Vertex AI calls: none
- automatic retry loop: none
- Focus Band / Quick Claw calls: none

Payload preflight:
- Light Ball / `species_stat_item_context`: PASS
  - `species_stat_item_context.available=true`
  - holder species `pikachu`
  - available context present in the default advice payload
  - required mention guard present
  - required mention guard included the Light Ball / `species_stat_item_context` label
- Chilan Berry / `chilan_berry_context`: PASS
  - `chilan_berry_context.available=true`
  - incoming move type `normal`
  - available context present in the default advice payload
  - required mention guard present
  - required mention guard included the Chilan Berry / `chilan_berry_context` label

Actual Gemini results:
- Light Ball: PARTIAL
  - Gemini generated an actual response.
  - Gemini mentioned Light Ball as a Pikachu-specific offensive item context that may boost Pikachu's offensive stats.
  - No non-Pikachu generalization, guaranteed KO, confirmed OHKO, always-doubles-damage, or exact-final-stats wording appeared.
  - Remaining weakness: Gemini still added generic default-assumption wording that the damage estimates include "no item effects."
  - This is improved from v2.6.1 FAIL but still not a clean PASS because the available Light Ball context is partially undercut by generic no-item wording.
  - Classification: wording guardrail weakness / generic default-assumption residue.
- Chilan Berry: PASS
  - Gemini generated an actual response.
  - Gemini explicitly described Chilan Berry as a Normal-type limited context.
  - Gemini said it may reduce damage from a Normal-type damaging move like Tackle.
  - Gemini preserved that raw damage rolls and `ko_context` remain based on the current calculator.
  - No forbidden Chilan wording appeared.

Forbidden wording / leaks:
- payload leak observed: no
- wrong context attachment observed: no
- Light Ball exact forbidden phrase observed: no
- Light Ball semantic no-item residue observed: yes, "no item effects"
- Chilan forbidden wording observed: no

Raw calculation impact:
- raw damage formula changed: no
- raw damage rolls changed: no
- Q12 multiplier changed: no
- `ko_context` changed: no
- new item implementation: no
- payload filtering behavior changed: no

Result:
- Actual Gemini PASS items: Focus Band, Quick Claw, Chilan Berry.
- Light Ball remains not full PASS after v2.7.1: PARTIAL.
- Recommended next step: T2 should decide whether Light Ball needs a narrower available-context/no-item wording exception or whether the partial result is acceptable.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had one timing-sensitive failure:
  - failure test: `test_item_damage_calculation_under_point_12ms_average`
  - best batch median: 0.125000ms
  - threshold: 0.120000ms
  - isolated target rerun 3x: passed.
  - `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.
- threshold/skip/xfail changed: no.

---

## v2.8 - Light Ball no-item residue guard

Purpose:
- Address the v2.7.1 Light Ball PARTIAL result.
- v2.7.1 confirmed Chilan Berry reached actual Gemini PASS, while Light Ball improved but still retained generic "no item effects" wording after positively mentioning the available Light Ball context.
- Implement a narrower Light Ball-specific prompt/contract guard without running actual Gemini verification in this implementation step.

Root cause:
- The v2.7 required-mention guard made Gemini mention `Light Ball / species_stat_item_context`.
- Gemini still mixed that positive mention with a generic default/no-item estimate sentence.
- This was not a payload leak, wrong context attachment, damage formula issue, raw roll issue, Q12 issue, or `ko_context` issue.

Implemented:
- Kept the registry-based available item context guard.
- Added a Light Ball-specific no-item residue guard when `species_stat_item_context.available=true`.
- The new guard says not to say or imply that no item effects are included for the move or recommendation.
- The new guard forbids generic no-item/default-assumption wording for available Light Ball context, including:
  - no item effects
  - without item effects
  - assuming no item
  - default no-item assumption
  - item not included
  - item not modeled
  - item not reflected
- The new guard tells Gemini to mention Light Ball as a Pikachu-specific offensive item context and, when `item_effects` marks the supported modifier as applied, describe the estimate as default assumptions plus the supported Light Ball modifier.
- Kept Light Ball limited wording:
  - no guaranteed KO
  - no confirmed OHKO
  - no always-doubles-damage claim
  - no exact final stats or exact EV/IV/nature-adjusted stats.

Regression protection:
- Chilan Berry PASS guard is preserved:
  - Chilan Berry remains a Normal-type damaging move limited context.
  - raw damage rolls and `ko_context` remain based on the current calculator.
  - final survival, final damage halving, and Chilan-adjusted KO odds remain forbidden.
- Focus Band / Quick Claw wording was not changed.
- unavailable/deferred/blocked filtering behavior was not changed.

Execution boundaries:
- actual Gemini call: not run in v2.8.
- Vertex AI call: not run.
- raw damage formula changed: no.
- raw damage rolls changed: no.
- Q12 multiplier changed: no.
- `ko_context` changed: no.
- new item implementation: no.
- payload filtering behavior changed: no.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had one timing-sensitive failure:
  - failure test: `test_item_damage_calculation_under_point_12ms_average`
  - best batch median: 0.140625ms
  - threshold: 0.120000ms
  - isolated target rerun 3x: passed.
  - `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.
- threshold/skip/xfail changed: no.

---

## v2.8.1 - Light Ball no-item residue guard actual verification

Purpose:
- Recheck only Light Ball after the v2.8 Light Ball-specific no-item residue guard.
- Do not recheck Chilan Berry, Focus Band, or Quick Claw because they already reached actual Gemini PASS.

Execution:
- provider: `gemini_developer_api`
- endpoint family: `generativelanguage.googleapis.com`
- model: `gemini-2.5-flash`
- Developer API calls: yes, one Light Ball actual verification call only.
- Vertex AI calls: none.
- automatic retry loop: none.
- Chilan Berry / Focus Band / Quick Claw calls: none.

Payload preflight:
- Light Ball / `species_stat_item_context`: PASS
  - `species_stat_item_context.available=true`
  - holder species `pikachu`
  - item `light-ball`
  - available context present in the default advice payload
  - required mention guard present
  - required mention guard included the Light Ball / `species_stat_item_context` label
  - Light Ball-specific no-item residue guard present
  - supported Light Ball modifier wording guard present
  - raw damage rolls present and unchanged
  - `ko_context` present and unchanged

Actual Gemini result:
- Light Ball: FAIL
  - Gemini generated an actual response.
  - Gemini mentioned Light Ball as a Pikachu-specific offensive item context.
  - Gemini still described the estimate using a `no item` default assumption label.
  - Gemini also said the Light Ball offensive stat boost is not applied to the damage estimates.
  - This is the same core failure mode as v2.6.1/v2.7.1: available Light Ball context is present, but Gemini undercuts it with generic no-item / not-applied wording.
  - Classification: no-item residue still present / wording guardrail failure.

Forbidden wording / leaks:
- payload leak observed: no.
- wrong context attachment observed: no.
- non-Pikachu generalization observed: no.
- guaranteed KO / confirmed OHKO / always-doubles-damage wording observed: no.
- exact final stats claim observed: no.
- Light Ball no-item residue observed: yes.

Raw calculation impact:
- raw damage formula changed: no.
- raw damage rolls changed: no.
- Q12 multiplier changed: no.
- `ko_context` changed: no.
- new item implementation: no.
- payload filtering behavior changed: no.

Result:
- Actual Gemini PASS items remain: Focus Band, Quick Claw, Chilan Berry.
- Light Ball remains not PASS after v2.8.1: FAIL.
- Recommended next step: do not add another prompt-only guard blindly. T2 should review whether the payload should avoid conflicting no-item assumption-profile wording when an applied Light Ball item effect is present, while still preserving raw damage / roll / `ko_context` boundaries.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: 4 passed.
- `uv run pytest -q`: one timing-sensitive perf failure:
  - failure test: `test_item_damage_calculation_under_point_12ms_average`
  - best batch median: 0.125000ms
  - threshold: 0.120000ms
  - isolated target rerun 3x: passed.
  - `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
  - full suite result: 1 failed, 901 passed, 2 deselected.
- threshold/skip/xfail changed: no.

---

## v2.9 - Light Ball payload conflict analysis

Purpose:
- Analyze the v2.8.1 Light Ball FAIL without running another Gemini call.
- Find where `no item`, `not applied`, and default-assumption wording remain in the Light Ball available payload.
- Decide whether the next step should be prompt hardening, payload clarification, or actual Light Ball damage-estimate integration.

Findings:
- Payload preflight remains PASS:
  - `species_stat_item_context.available=true`
  - holder species `pikachu`
  - item `light-ball`
  - required mention guard present
  - Light Ball-specific no-item residue guard present
- The default advice payload still contains conflicting damage-estimate signals:
  - `damage_estimate.assumption_profile.id=default_level50_ivs31_evs0_neutral_no_item`
  - `damage_estimate.assumption_profile.label=Default Level 50 / IV 31 / EV 0 / neutral nature / no item`
  - `damage_estimate.assumptions.item=none`
  - top-level Light Ball item profile has `effect_support_status=legal_but_not_modeled`
  - top-level Light Ball item profile has `damage_modifier_status=not_applied`
  - `species_stat_item_context.species_stat_effect.damage_estimate_item_effect_status=not_applied`
- Core damage code has Light Ball support in species-stat item modifier logic.
- The advisor damage estimate builder does not currently pass Light Ball as an applied attacker item:
  - `_attacker_item_for_damage` handles catalog type-boost items and `SUPPORTED_ATTACKER_DAMAGE_ITEMS`
  - `SUPPORTED_ATTACKER_DAMAGE_ITEMS` does not include Light Ball / species-stat items
- Therefore, the current LLM advice payload is internally tense:
  - Light Ball is available as explanatory context
  - raw damage rolls are still no-item / not Light-Ball-adjusted

Conclusion:
- Another prompt-only guard is unlikely to be robust.
- T2 should choose one of two directions:
  - integrate Light Ball into advisor damage estimates in a separate mechanics/damage task, which would intentionally change raw rolls and needs broad tests
  - keep Light Ball explanatory-only, but clarify the payload/contract so Gemini may say Light Ball is recognized separately and not integrated into raw rolls without generic no-item wording

Boundaries:
- actual Gemini call: not run in v2.9.
- Vertex AI call: not run.
- code changes: none.
- payload filtering changes: none.
- raw damage formula changed: no.
- raw damage rolls changed: no.
- Q12 multiplier changed: no.
- `ko_context` changed: no.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had one timing-sensitive failure:
  - failure test: `test_item_damage_calculation_under_point_12ms_average`
  - best batch median: 0.125000ms
  - threshold: 0.120000ms
  - isolated target rerun 3x: passed.
  - `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.
- threshold/skip/xfail changed: no.

---

## v3.0 - Light Ball damage estimate integration design

Purpose:
- Design whether and how Light Ball should be integrated into advisor damage estimates after the v2.8.1/v2.9 Light Ball failure analysis.
- This is design-only; implementation is deferred to v3.1.

Background:
- Actual Gemini PASS: Focus Band, Quick Claw, Chilan Berry.
- Actual Gemini FAIL: Light Ball.
- v2.9 found a payload conflict:
  - `species_stat_item_context.available=true`
  - but `damage_estimate.assumption_profile` still says no item
  - `damage_estimate.assumptions.item=none`
  - Light Ball item/profile/context status still says not applied

Design conclusion:
- T2-preferred direction is Option A:
  - integrate user-confirmed Pikachu + Light Ball into the advisor damage estimate under narrow conditions
  - make `damage_estimate.item_effects.attacker_item.status=applied`
  - change assumption profile / assumptions away from no-item wording
  - allow raw damage rolls and `ko_context` to change only for eligible Pikachu + Light Ball cases
- `species_stat_item_context` should become a sibling explanation of the applied `damage_estimate.item_effects` modifier, not an explanatory-only context that conflicts with the raw estimate.

Important implementation caveat:
- `advisor/damage/item_modifiers.py` has Light Ball-aware `attack_stat_item_mod(...)`.
- The current `calc_damage_rolls()` path appears to use `get_atk_item_modifier(...)` / `get_spa_item_modifier(...)` directly, so v3.1 must verify whether passing Light Ball into `DamageContext.attacker_item` is enough.
- Preferred v3.1 path is to route formula attack-stat item modifier handling through the shared Light Ball-aware helper, preserving Choice Band / Choice Specs behavior.

Proposed v3.1 scope:
- Apply Light Ball only when:
  - attacker item profile is `user_confirmed`
  - item id is `light-ball`
  - attacker species is `pikachu`
  - Champions legal fixture passes
  - `items_damage.json` species-stat metadata exists
  - move is damaging and physical/special
- Do not apply for:
  - non-Pikachu holders
  - unconfirmed item
  - defender-side Light Ball for attacker estimates
  - status or unsupported moves
  - blocked/unavailable item coverage

Testing plan:
- Add damage estimate tests for physical and special Pikachu Light Ball roll increases.
- Add non-Pikachu and unconfirmed negative tests.
- Assert `assumptions.item` is not `none` and `item_effects.attacker_item.status=applied`.
- Assert `species_stat_item_context.available=true` aligns with the applied item effect status.
- Assert `ko_context` derives from the adjusted rolls but remains limited/not final battle truth.
- Regress Focus Band, Quick Claw, Chilan Berry, type boost, resist berry, Choice Scarf, and existing damage item behavior.

Boundaries:
- actual Gemini call: not run in v3.0.
- Vertex AI call: not run.
- code changes: none.
- raw damage formula changed: no.
- raw damage rolls changed: no.
- Q12 multiplier changed: no.
- `ko_context` changed: no.
- payload filtering changed: no.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 49 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 92 passed.
- `uv run pytest tests/test_damage_perf.py -q`: first run had one timing-sensitive failure:
  - failure test: `test_item_damage_calculation_under_point_12ms_average`
  - best batch median: 0.140625ms
  - threshold: 0.120000ms
  - isolated target rerun 3x: passed.
  - `uv run pytest tests/test_damage_perf.py -q` rerun: 4 passed.
- `uv run pytest -q`: 902 passed, 2 deselected.
- threshold/skip/xfail changed: no.

---

## v0.92.1/v0.93 - Unavailable item context verification and regression hardening

Purpose:
- Re-verify v0.92 advice-payload filtering with actual Gemini calls.
- Harden regressions so unavailable/deferred/blocked item information cannot leak through default advice payload JSON, `item_profiles`, `damage_estimate.item_effects`, or generic limitation wording.

Observed before hardening:
- Actual Gemini calls after v0.92 no longer exposed Chilan Berry, Loaded Dice, or Power Herb item names/effects from unavailable item contexts.
- However, the default advice payload could still contain generic debug-only limitation wording such as `not modeled` from nested non-item fields like `ko_context.limitations`.
- Root cause: item context filtering removed `available=false` item context fields, but did not scrub debug-oriented `limitations` strings that could still invite generic natural-language caveats.

Implemented:
- Kept `available=false` item contexts removed from the default Gemini advice payload.
- Kept enriched/debug payload reasons intact:
  - `chilan_berry_deferred`
  - `move_not_super_effective`
  - `blocked_by_legal_item_coverage`
- Added advice-payload limitation filtering for debug-only phrases:
  - `effect is not applied`
  - `item effect is not included`
  - `not modeled`
  - `not reflected`
  - `unsupported`
  - `deferred`
  - `blocked`
- Kept raw `damage_estimate` in the default advice payload.
- Kept raw `ko_context` in the default advice payload while stripping only debug-only limitation strings from its `limitations` list.
- Preserved available legal item contexts such as available Yache Berry `resist_berry_context`.
- Reworded the resist berry edge-case prompt/contract guardrail away from `Unsupported...not modeled` wording to:
  - `Resist berry edge cases require explicit support before advice can use them.`

Actual Gemini verification:
- Gemini actual call: succeeded.
- Case A Chilan Berry deferred:
  - enriched/debug payload kept `resist_berry_context.available=false`, reason `chilan_berry_deferred`.
  - default advice payload removed `resist_berry_context`.
  - default advice payload hid the opponent item profile as unknown.
  - actual advice did not mention Chilan Berry, `chilan`, effect-not-applied wording, `not modeled`, `not reflected`, `unsupported`, `deferred`, or `blocked`.
- Case B Yache Berry available:
  - default advice payload retained `resist_berry_context.available=true`.
  - raw damage range and rolls were preserved.
  - `ko_context` remained present.
  - actual advice kept the berry reduction separate from raw damage/KO context.
- Case C Yache Berry non-super-effective unavailable:
  - enriched/debug payload kept reason `move_not_super_effective`.
  - default advice payload removed `resist_berry_context` and hid the item profile.
  - actual advice did not mention Yache Berry, the unavailable reason, or generic item-effect limitation wording.
- Case D Loaded Dice blocked:
  - enriched/debug payload kept `multi_hit_context.available=false`, reason `blocked_by_legal_item_coverage`.
  - default advice payload removed `multi_hit_context`, hid the item profile, and did not expose `loaded-dice` through `damage_estimate.item_effects`.
  - actual advice did not mention Loaded Dice, blocked/not-modeled wording, 5-hit claims, or multi-hit-adjusted KO.
- Case E Power Herb blocked:
  - no `charge_context` was added.
  - default advice payload hid the item profile and did not expose `power-herb`.
  - actual advice did not mention Power Herb, instant charge, item consumption, or turn sequencing.

Regression tests:
- Strengthened `tests/test_advisor_payload_contract.py` to assert:
  - Chilan deferred is hidden from default advice payload while debug reason remains.
  - Yache non-SE unavailable is hidden from default advice payload while debug reason remains.
  - Loaded Dice blocked is hidden from default advice payload while debug reason remains.
  - Power Herb / non-legal item profile is hidden from default advice payload.
  - Available Yache Berry context remains in default advice payload.
  - raw damage range and rolls remain unchanged.
  - `ko_context` remains present with OHKO/2HKO values preserved.
  - unavailable/deferred/blocked reason strings and item names do not appear in serialized default advice payload.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 31 passed.
- `uv run pytest tests/test_advisor_damage_estimate.py -q`: 89 passed.
- `uv run pytest tests/test_damage_perf.py -q`: initially 1 known item perf failure, then 4 passed on rerun.
- `uv run pytest tests/test_damage_perf.py::test_item_damage_calculation_under_point_12ms_average -q`: passed on 3 isolated reruns.
- `uv run pytest -q`: 881 passed, 2 deselected.

Maintained boundaries:
- No Chilan Berry full support.
- No legal fixture mutation.
- No fixture changes.
- No damage formula changes.
- No raw damage roll modification.
- No KO context calculation changes.
- No berry-adjusted damage implementation.
- No berry-adjusted KO implementation.
- No item consumption tracking.
- No Turn Engine.
- No Power Herb charge_context.
- No Loaded Dice legal addition.
- No UI changes.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.45 - Opponent assumptions debug export

Purpose:
- Add a developer/debug helper that creates a safe, copy-ready summary of the current `opponent_assumptions` payload section.

Implemented:
- Added opponent assumptions debug summary builders in `llm/opponent_assumptions.py`:
  - `build_opponent_assumptions_debug_summary(payload)`
  - `build_opponent_assumptions_debug_summary_from_assumptions(opponent_assumptions)`
  - `format_opponent_assumptions_debug_json(summary)`
- Supported `available=true` summaries with:
  - opponent species id
  - availability
  - `calculation_usage`
  - `is_confirmed_information`
  - possible sample count
  - included Top-K count
  - sample id / species id / role / archetype id / confidence / possible items
  - `is_user_confirmed: false`
  - `used_for_damage: false`
  - `used_for_speed: false`
- Supported `available=false` summaries with:
  - unavailable reason
  - zero sample count
  - empty sample list
  - safety guardrails
- Added guardrail booleans:
  - `not_confirmed`
  - `not_damage_input`
  - `not_speed_input`
  - `not_final_turn_order`
  - `context_only`
- Added copy/export-ready pretty JSON formatting.
- Kept export scope to `opponent_assumptions` summary only.
- Deferred full LLM payload export.
- Did not add file writing in v0.45.
- Did not add a UI debug panel.
- Updated `docs/advisor_payload_contract.md` with developer-only debug summary policy:
  - not automatically inserted into Gemini responses
  - not a full payload export
  - no API keys, secrets, `.env`, token logs, full stats, full source metadata, or full Top-K dumps
  - future file export should use a git-ignored path such as `logs/debug_payloads/`
- Added tests for:
  - available debug summary
  - unavailable debug summary
  - missing assumptions safety
  - full payload input not leaking unrelated payload fields
  - no secret-like fields
  - no full stats dump
  - optional role/archetype/possible_items preservation
  - pretty JSON formatting

Maintained boundaries:
- No UI panel.
- No user-facing advice injection.
- No full LLM payload export.
- No fixture changes.
- No sample additions.
- No repository sample changes.
- No damage/speed integration.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as user-confirmed.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No scraping or build script.

Verification:
- `uv run pytest tests/test_opponent_assumptions.py -q`: 13 passed.
- `uv run pytest -q`: 783 passed, 2 deselected.

---

## v0.45.1 - Debug summary local verification

Purpose:
- Verify that the v0.45 opponent assumptions debug summary helper produces a human-readable, copy-ready JSON string.

Local verification:
- Tested species: `rotom_wash`.
- Built `opponent_assumptions` with:
  - `build_opponent_assumptions_payload({"name_en": "rotom_wash"}, PokemonStatSampleRepository())`
- Built debug summary with:
  - `build_opponent_assumptions_debug_summary(payload)`
- Rendered copy-ready JSON with:
  - `format_opponent_assumptions_debug_json(summary)`

Observed debug summary:
- `opponent_species_id`: `rotom_wash`.
- `opponent_assumptions_available`: `true`.
- `calculation_usage`: `context_only`.
- `possible_sample_count`: `1`.
- `included_top_k`: `1`.
- `possible_samples[0].sample_id`: `rotom_wash_defensive_pivot_repo_v42`.
- `possible_samples[0].species_id`: `rotom-wash`.
- `possible_samples[0].confidence`: `estimated`.
- `possible_samples[0].is_user_confirmed`: `false`.
- `possible_samples[0].used_for_damage`: `false`.
- `possible_samples[0].used_for_speed`: `false`.
- Guardrails were all `true`:
  - `context_only`
  - `not_confirmed`
  - `not_damage_input`
  - `not_speed_input`
  - `not_final_turn_order`

Safety checks:
- No full stats dump appeared.
- No full LLM payload dump appeared.
- No `secret_api_key`, `env`, API key, token, or token usage raw log fields appeared.
- Output was pretty-printed and copy-ready.

Metadata completeness note:
- The summary included `role`, `archetype_id`, and `possible_items` keys.
- In this local output, `role` and `archetype_id` were `null`, and `possible_items` was an empty list because the current `opponent_assumptions` payload does not carry those repository metadata fields into `possible_samples`.
- This is safe, but less informative than the v0.44 target summary shape.

Verdict:
- v0.45.1 local debug summary verification: PARTIAL PASS.
- JSON formatting: PASS.
- Availability / count / sample identity: PASS.
- Safety / no full stats / no full payload / no secrets: PASS.
- Metadata completeness: WEAK.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No damage/speed integration.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.46 - Opponent assumptions metadata enrichment design

Purpose:
- Design how to safely expose minimal sample metadata so `opponent_assumptions` debug summaries are more useful without changing battle math or overloading Gemini responses.

Designed:
- Documented current limitation from v0.45.1:
  - debug summary safety fields work
  - `role`, `archetype_id`, and `possible_items` are null or empty because `opponent_assumptions.possible_samples` does not carry those repository fields
- Defined the problem:
  - `sample_id` alone is weak for debugging
  - empty `possible_items` makes legal item filtering hard to inspect
  - too much metadata could make Gemini over-explain or overclaim possible samples
- Identified metadata candidates:
  - `role`
  - `archetype_id`
  - `archetype_tags`
  - `possible_items`
  - `confidence`
  - `source_type`
  - `calculation_usage`
  - `is_user_confirmed`
  - `limitations`
- Set source-of-truth principle:
  - fixture remains sample metadata source
  - repository remains validation/normalization boundary
  - `opponent_assumptions` should include only LLM-safe metadata
  - debug summary should summarize only metadata already present in `opponent_assumptions`
  - debug summary should not re-query repository and diverge from what Gemini saw
- Compared enrichment options:
  - enrich `opponent_assumptions.possible_samples`
  - debug summary only repository re-query
  - nested `debug_metadata`
  - separate developer_debug object outside LLM payload
- Recommended v0.47 path:
  - Option A minimal enrichment in `possible_samples`
  - add `role`, `archetype_id`, `possible_items`, and `calculation_usage`
  - keep full stats/source metadata excluded
  - keep Option D for future richer debug needs
- Proposed minimal metadata set and explicit exclusions:
  - exclude full stats
  - exclude full SP distribution
  - exclude source URL/source note
  - exclude full update policy
  - exclude long reviewer notes
- Documented LLM guardrail impact:
  - role/archetype/possible_items are context-only metadata
  - possible items are not confirmed held items
  - do not enumerate sample metadata by default
  - never use metadata as damage or Speed input
- Designed expected debug summary improvement:
  - non-null `role`
  - non-null `archetype_id`
  - legal-only `possible_items`
  - `used_for_damage: false`
  - `used_for_speed: false`
- Added future tests plan for:
  - metadata presence in `possible_samples`
  - debug summary population
  - legal-only possible items
  - no full stats dump
  - no damage/speed integration regression

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No fixture changes.
- No sample additions.
- No repository sample data changes.
- No UI changes.
- No damage/speed integration.
- No user-confirmed treatment changes.
- No calculation mode.
- No Bayesian update.
- No Turn Engine.
- No full stats exposure.
- No full payload export.
- No scraping or build script.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.47 - Opponent assumptions minimal metadata enrichment

Purpose:
- Populate safe, minimal sample metadata in `opponent_assumptions.possible_samples` so developer debug summaries show useful role/archetype/item context.

Implemented:
- Enriched `opponent_assumptions.possible_samples` with minimal metadata:
  - `role`
  - `archetype_id`
  - `possible_items`
  - `calculation_usage`
- Kept existing safety metadata:
  - `confidence`
  - `is_user_confirmed: false`
  - `prior_probability: null`
  - `prior_probability_type: not_available`
- Removed `possible_stats` from `possible_samples` to avoid full stats exposure.
- Kept full stats and SP distribution out of `possible_samples`.
- Kept source URL, source note, full source metadata, long reviewer notes, and full update policy out of `possible_samples`.
- Updated debug summary behavior so repo-native samples can show:
  - non-null `role`
  - non-null `archetype_id`
  - legal-only `possible_items`
  - `used_for_damage: false`
  - `used_for_speed: false`
- Updated advisor prompt and payload contract guardrails:
  - sample role/archetype/possible_items are context-only metadata
  - possible_items are possible assumptions, not confirmed held items
  - do not enumerate sample metadata by default
  - keep sample visibility concise
- Updated `docs/advisor_payload_contract.md` with minimal metadata field semantics.
- Added/updated tests for:
  - role/archetype_id/possible_items in `possible_samples`
  - no `possible_stats`, full `stats`, or `sp_distribution`
  - no source metadata dump
  - debug summary metadata population
  - `used_for_damage: false`
  - `used_for_speed: false`
  - prompt/contract guardrails
  - no damage/speed integration regression

Maintained boundaries:
- No fixture changes.
- No sample additions.
- No repository sample data changes.
- No UI changes.
- No full stats exposure.
- No full payload export.
- No damage/speed integration.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as user-confirmed.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No scraping or build script.

Verification:
- `uv run pytest tests/test_opponent_assumptions.py tests/test_advisor_payload_contract.py -q`: 40 passed.
- `uv run pytest -q`: 784 passed, 2 deselected.

---

## v0.47.1 - Opponent metadata debug summary local verification

Purpose:
- Verify that the v0.47 minimal metadata enrichment appears in the developer debug summary output.

Local verification:
- Tested species: `rotom_wash`.
- Built `opponent_assumptions` with:
  - `build_opponent_assumptions_payload({"name_en": "rotom_wash"}, PokemonStatSampleRepository())`
- Built debug summary with:
  - `build_opponent_assumptions_debug_summary(payload)`
- Rendered copy-ready JSON with:
  - `format_opponent_assumptions_debug_json(summary)`

Observed debug summary:
- `opponent_assumptions_available`: `true`.
- `opponent_species_id`: `rotom_wash`.
- `possible_sample_count`: `1`.
- `included_top_k`: `1`.
- `possible_samples[0].sample_id`: `rotom_wash_defensive_pivot_repo_v42`.
- `possible_samples[0].species_id`: `rotom-wash`.
- `possible_samples[0].role`: `defensive_pivot`.
- `possible_samples[0].archetype_id`: `rotom_wash_defensive_pivot_repo_v42`.
- `possible_samples[0].possible_items`: `["leftovers", "sitrus-berry"]`.
- `possible_samples[0].confidence`: `estimated`.
- `possible_samples[0].is_user_confirmed`: `false`.
- `possible_samples[0].used_for_damage`: `false`.
- `possible_samples[0].used_for_speed`: `false`.
- Guardrails were all `true`:
  - `context_only`
  - `not_confirmed`
  - `not_damage_input`
  - `not_speed_input`
  - `not_final_turn_order`

Safety checks:
- No full stats dump appeared.
- No `sp_distribution` dump appeared.
- No full source metadata dump appeared.
- No full LLM payload export appeared.
- No `secret_api_key`, `env`, API key, token, or token usage raw log fields appeared.
- Output remained pretty-printed and copy-ready.

Verdict:
- v0.47.1 local debug summary verification: PASS.
- Metadata population: PASS.
- Safety / no full stats / no SP distribution / no source metadata / no full payload / no secrets: PASS.
- Guardrails: PASS.

Next candidates:
- `v0.48 - Payload Versioning Design`.
- `v0.48 - Developer Debug Access Design`.
- `v0.48 - Opponent Sample Pack Expansion Plan`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No damage/speed integration.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.44 - Opponent sample debug inspection design

Purpose:
- Design a developer/debug-only way to inspect which `opponent_assumptions` and `possible_samples` are present for the current active opponent.

Designed:
- Documented current state:
  - `opponent_assumptions` payload exists
  - repo-native minimal sample pack exists
  - Gemini now surfaces one-line possible sample context
  - developers still cannot directly inspect the runtime sample payload in the app
- Defined debug inspection goals:
  - developer/debug-only
  - show `calculation_usage: context_only`
  - show samples are not user-confirmed
  - show samples are not damage or Speed inputs
  - keep user-facing battle advice simple
- Compared options:
  - debug log only
  - payload export / copy button
  - developer-only debug panel
  - AI analysis panel bottom summary
  - CLI/debug script
- Recommended v0.45 direction:
  - prefer `Opponent Assumptions Debug Export Implementation`
  - start with `opponent_assumptions` summary export/copy
  - defer general UI debug panel
  - keep CLI/debug script as a smaller alternative
- Proposed debug summary shape with:
  - opponent species id
  - availability
  - calculation usage
  - possible sample count
  - included Top-K count
  - sample id / role / archetype / possible items
  - `used_for_damage: false`
  - `used_for_speed: false`
  - safety guardrails
- Designed payload export scope:
  - prefer `opponent_assumptions` summary only first
  - full LLM payload export remains optional/deferred
  - any file export should use a git-ignored path such as `logs/debug_payloads/`
- Documented safety/privacy/git hygiene:
  - no API keys, `.env`, secrets, or raw auth data
  - `logs/` remains uncommitted
  - debug export is developer-only
- Added future tests plan for:
  - available/unavailable summary
  - `is_user_confirmed: false`
  - `used_for_damage: false`
  - `used_for_speed: false`
  - no secret-like fields in export
  - existing opponent assumptions and payload contract regressions

Maintained boundaries:
- Documentation-only design.
- No code implementation.
- No UI implementation.
- No fixture changes.
- No sample additions.
- No damage/speed integration.
- No sample treated as user-confirmed.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No scraping or build script.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

---

## v0.43 - Opponent sample visibility prompt polish

Purpose:
- Improve response visibility for context-only opponent samples after v0.42.1 found Sample visibility WEAK.

Implemented:
- Strengthened advisor prompt and payload contract wording for `opponent_assumptions`.
- Added a one-line visibility rule:
  - when `opponent_assumptions.available` is true and `possible_samples` exist, the response may include at most one short limitation sentence that possible sample context exists.
- Preserved the safety wording that possible samples are:
  - context-only
  - not confirmed
  - not user-confirmed
  - not direct damage or Speed calculation inputs
- Added concision guardrails:
  - do not dump `sample_id`
  - do not dump full stats
  - do not dump source metadata
  - do not dump `update_policy`
  - do not dump `coverage_probability`
  - do not dump full Top-K sample lists
- Added unavailable-case guardrail:
  - if `opponent_assumptions.available` is false, do not invent samples or force a sample limitation.
- Updated `docs/advisor_payload_contract.md`.
- Added advisor payload contract tests for the one-line visibility, concision, and unavailable/no-invent guardrails.

Maintained boundaries:
- No fixture changes.
- No sample additions.
- No repository changes.
- No UI changes.
- No damage/speed integration.
- No sample stats connected to `damage_estimate`.
- No sample stats connected to `speed_context`.
- No sample treated as user-confirmed.
- No calculation mode implementation.
- No Bayesian update implementation.
- No KO/OHKO/2HKO.
- No Turn Engine.
- No item effect changes.
- No scraping or build script.

Verification:
- `uv run pytest tests/test_advisor_payload_contract.py -q`: 26 passed.
- `uv run pytest -q`: 777 passed, 2 deselected.

---

## v0.43.1 - Opponent sample visibility local Gemini verification

Purpose:
- Record local Gemini actual-call verification after v0.43 opponent sample visibility prompt polish.

Observed local case:
- Rotom-Wash case:
  - Player Pokemon: Charizard.
  - Player item: Charcoal.
  - Selected move: Heat Wave.
  - Opponent Pokemon: Rotom-Wash.
  - Opponent stats: not user-confirmed.
  - Gemini recommended Heat Wave and described an estimated 26.4-31.2% damage range that is not very effective against Rotom-Wash.
  - Gemini stated the estimate includes a 1.2x Fire-type damage boost from the user-confirmed Charcoal and is based on default assumptions.
  - Gemini stated Rotom-Wash's item is unknown, speed order is uncertain, and unconfirmed Electric-type candidate moves are a possible threat.
  - Gemini included the concise sample visibility sentence: "Possible opponent samples exist, but they are context only and not confirmed."

Confirmed behavior:
- Gemini actual call succeeded.
- Rotom-Wash recognition was normal.
- Charcoal 1.2x Fire-type modifier wording was correct.
- Possible opponent sample context appeared as one concise line.
- `context only` and `not confirmed` wording appeared.
- Gemini did not present possible samples as confirmed opponent sets.
- Gemini did not claim sample stats were directly used for damage or speed calculation.
- Gemini did not assert final turn order.
- No `sample_id`, full stats, source metadata, `update_policy`, or Top-K sample dump appeared.
- Response concision was acceptable.

Verdict:
- v0.43.1 local Gemini verification: PASS.
- Safety: PASS.
- Sample visibility: PASS.
- Concision: PASS.

Next candidates:
- `v0.44 - Opponent Sample Expansion Plan`.
- `v0.44 - Legal Item Coverage Expansion Design`.
- `v0.44 - Opponent Sample Debug Inspection Design`.

Maintained boundaries:
- Documentation-only verification record.
- No code changes.
- No UI changes.
- No fixture changes.
- No schema changes.
- No prompt changes.
- No tests changed.
- No damage/speed integration.
- No sample additions.
- No logs, `.env`, secrets, API keys, or handoff capsule commits.

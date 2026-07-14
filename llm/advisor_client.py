"""Thin LLM advisor client used by UI spikes.

This module keeps PySide UI code from importing the script module directly.
The underlying quantitative scenario still lives in ``scripts.spike_advisor``
for the v0.5 spike.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from core.turn_event import TurnPipelineResult, normalize_turn_pipeline_result
from core.turn_state import TurnSnapshot, normalize_turn_snapshot
from core.champions_legal_item_repository import get_legal_item_status
from llm.advisor_battle_state_context import (
    BATTLE_STATE_CONTEXT_ACTIVE_FIELDS,
    BATTLE_STATE_CONTEXT_ALLOWED_SOURCES,
    BATTLE_STATE_CONTEXT_FIELD_FIELDS,
    BATTLE_STATE_CONTEXT_FIELD_ALLOWED_SOURCES,
    BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS,
    BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES,
    BATTLE_STATE_CONTEXT_ITEM_ALLOWED_SOURCES,
    BATTLE_STATE_CONTEXT_SAFETY_NOTES,
    BATTLE_STATE_CONTEXT_UNKNOWN_FIELD,
    BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES,
    build_battle_state_context_from_ui_selected_state,
    build_item_event_context_from_confirmations,
    validate_explicit_user_item_event_confirmation,
)
from llm.advisor_opponent_move_context import (
    OPPONENT_MOVE_CONTEXT_ALLOWED_MOVE_FIELDS,
    OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES,
    OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS,
    OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES,
    OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES,
    build_opponent_move_context,
)
from llm.advisor_turn_order_context import (
    TURN_ORDER_CONTEXT_CONFIDENCE_VALUES,
    TURN_ORDER_CONTEXT_FORBIDDEN_FIELDS,
    TURN_ORDER_CONTEXT_ORDER_HINT_VALUES,
    TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES,
    TURN_ORDER_CONTEXT_REQUIRED_UNSUPPORTED,
    TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES,
    build_deterministic_turn_order_context,
)
from llm.advisor_payload_contract import (
    ADVICE_CONTEXT_SIDE_FIELDS,
    ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB,
    ADVICE_ITEM_CONTEXT_GUARD_METADATA,
    ADVICE_ITEM_CONTEXT_KEYS,
    DEBUG_ONLY_REASON_PHRASES,
    TURN_PIPELINE_KNOWN_LIMITATIONS,
    TURN_SNAPSHOT_KNOWN_LIMITATIONS,
)
from llm.advisor_turn_snapshot import try_build_turn_snapshot_from_battle_input
from llm.advisor_turn_events import build_optional_turn_pipeline_for_advice_payload
from llm.token_logger import UNKNOWN_MODEL_OR_UNKNOWN_PRICING, TokenLogger
from scripts.spike_advisor import (
    DEFAULT_MODEL,
    build_prompt,
    call_gemini,
    collect_battle_data,
)


def run_spike_advice(model: str | None = None) -> tuple[str, dict[str, int], dict[str, Any]]:
    """Run the hardcoded v0.5 advisor spike and return recommendation + usage.

    Returns:
        ``(recommendation_text, usage, session_summary)``.
    """
    selected_model = model or DEFAULT_MODEL
    data = collect_battle_data()
    prompt = build_prompt(data)
    recommendation, usage = call_gemini(prompt, selected_model)

    logger = TokenLogger()
    try:
        logger.log_call(
            model=selected_model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
            tool_name="damage_calculator",
            turn_number=1,
            game_id="spike_mega_kangaskhan_vs_garchomp",
        )
        summary = logger.get_session_summary()
    except Exception as exc:  # pragma: no cover - defensive UI resilience path
        summary = {
            "total_calls": 0,
            "total_input_tokens": usage.get("input_tokens", 0),
            "total_output_tokens": usage.get("output_tokens", 0),
            "total_cached_tokens": usage.get("cached_tokens", 0),
            "estimated_cost_usd": 0.0,
            "pricing_status": UNKNOWN_MODEL_OR_UNKNOWN_PRICING,
            "pricing_status_counts": {UNKNOWN_MODEL_OR_UNKNOWN_PRICING: 1},
            "by_tool": {},
            "token_logging_error": str(exc),
        }

    return recommendation, usage, summary


def build_ui_advice_payload(
    battle_input: dict[str, Any],
    turn_snapshot: TurnSnapshot | dict[str, Any] | None = None,
    turn_pipeline: TurnPipelineResult | dict[str, Any] | None = None,
    turn_order_context: dict[str, Any] | None = None,
    opponent_move_context: dict[str, Any] | None = None,
    battle_state_context: dict[str, Any] | None = None,
    item_event_context: dict[str, Any] | None = None,
    *,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
    enable_item_event_context: bool = False,
) -> dict[str, Any]:
    """Return the Gemini default-advice payload without debug-only item context."""
    payload = deepcopy(battle_input)
    filtered_payload = filter_context_for_default_advice(payload)
    _add_turn_snapshot_to_advice_payload(filtered_payload, turn_snapshot)
    _add_turn_pipeline_to_advice_payload(filtered_payload, turn_pipeline)
    _add_turn_order_context_to_advice_payload(
        filtered_payload,
        turn_order_context,
        enable_turn_order_context=enable_turn_order_context,
    )
    _add_opponent_move_context_to_advice_payload(
        filtered_payload,
        opponent_move_context,
        enable_opponent_move_context=enable_opponent_move_context,
    )
    _add_battle_state_context_to_advice_payload(
        filtered_payload,
        battle_state_context,
        enable_battle_state_context=enable_battle_state_context,
    )
    _add_item_event_context_to_advice_payload(
        filtered_payload,
        item_event_context,
        enable_item_event_context=enable_item_event_context,
    )
    return filtered_payload


def filter_context_for_default_advice(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove debug-only item context from the Gemini default-advice payload."""
    _remove_ui_only_field_profiles(payload)
    available_item_sides = _collect_available_item_context_sides(payload)
    _hide_move_local_unavailable_type_boost_item_effects(payload)
    hidden_item_sides = _remove_unavailable_item_contexts(payload)
    hidden_item_sides -= available_item_sides
    hidden_item_ids = _hide_advice_hidden_item_profiles(payload, hidden_item_sides)
    _hide_advice_hidden_item_effects(payload, hidden_item_ids)
    _remove_debug_only_limitations(payload)
    return payload


def _remove_ui_only_field_profiles(payload: dict[str, Any]) -> None:
    payload.pop("field_profiles", None)
    payload.pop("item_event_confirmations", None)
    payload.pop("current_condition_confirmations", None)


def run_ui_selected_advice(
    battle_input: dict[str, Any],
    model: str | None = None,
    *,
    enable_turn_pipeline: bool = False,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
) -> tuple[str, dict[str, int], dict[str, Any]]:
    """Run the v0.6 UI-selected Pokemon advisor flow.

    The caller passes plain dictionaries collected from UI state. This function
    owns prompt construction, Gemini invocation, and token logging.
    """
    selected_model = model or DEFAULT_MODEL
    turn_snapshot = try_build_turn_snapshot_from_battle_input(battle_input)
    prompt = _build_ui_selected_prompt(
        battle_input,
        turn_snapshot=turn_snapshot,
        enable_turn_pipeline=enable_turn_pipeline,
        enable_turn_order_context=enable_turn_order_context,
        enable_opponent_move_context=enable_opponent_move_context,
        enable_battle_state_context=enable_battle_state_context,
    )
    recommendation, usage = call_gemini(prompt, selected_model)
    summary = _log_advisor_call(
        model=selected_model,
        usage=usage,
        game_id="ui_selected_pokemon_v0_6",
    )
    return recommendation, usage, summary


def _build_ui_selected_prompt(
    battle_input: dict[str, Any],
    turn_snapshot: TurnSnapshot | dict[str, Any] | None = None,
    turn_pipeline: TurnPipelineResult | dict[str, Any] | None = None,
    turn_order_context: dict[str, Any] | None = None,
    opponent_move_context: dict[str, Any] | None = None,
    battle_state_context: dict[str, Any] | None = None,
    item_event_context: dict[str, Any] | None = None,
    *,
    enable_turn_pipeline: bool = False,
    enable_turn_order_context: bool = False,
    enable_opponent_move_context: bool = False,
    enable_battle_state_context: bool = False,
) -> str:
    if turn_pipeline is None and enable_turn_pipeline:
        base_payload = build_ui_advice_payload(
            battle_input,
            turn_snapshot=turn_snapshot,
        )
        selected_move = _selected_move_payload_from_advice_payload(base_payload)
        turn_pipeline = build_optional_turn_pipeline_for_advice_payload(
            base_payload,
            enable_turn_pipeline=True,
            selected_move_id=_string_field(selected_move, "move_id"),
            damage_estimate_ref=_move_payload_ref(selected_move, "damage_estimate"),
            ko_context_ref=_move_payload_ref(selected_move, "ko_context"),
        )

    if turn_order_context is None and enable_turn_order_context:
        base_payload = build_ui_advice_payload(
            battle_input,
            turn_snapshot=turn_snapshot,
        )
        turn_order_context = _build_optional_turn_order_context_for_advice_payload(base_payload)

    if opponent_move_context is None and enable_opponent_move_context:
        base_payload = build_ui_advice_payload(
            battle_input,
            turn_snapshot=turn_snapshot,
        )
        opponent_move_context = _build_optional_opponent_move_context_for_advice_payload(base_payload)

    if battle_state_context is None and enable_battle_state_context:
        battle_state_context = build_battle_state_context_from_ui_selected_state(
            battle_input,
            include_user_confirmed_items=enable_battle_state_context,
            include_user_confirmed_fields=enable_battle_state_context,
        )

    if item_event_context is None and enable_battle_state_context:
        item_event_context = build_item_event_context_from_confirmations(
            battle_input.get("item_event_confirmations")
        )

    advice_payload = build_ui_advice_payload(
        battle_input,
        turn_snapshot=turn_snapshot,
        turn_pipeline=turn_pipeline,
        turn_order_context=turn_order_context,
        opponent_move_context=opponent_move_context,
        battle_state_context=battle_state_context,
        item_event_context=item_event_context,
        enable_turn_order_context=enable_turn_order_context,
        enable_opponent_move_context=enable_opponent_move_context,
        enable_battle_state_context=enable_battle_state_context,
        enable_item_event_context=enable_battle_state_context,
    )
    available_item_context_guard = _build_available_item_context_required_mention_guard(advice_payload)
    turn_snapshot_guard = _build_turn_snapshot_prompt_guard(advice_payload)
    turn_pipeline_guard = _build_turn_pipeline_prompt_guard(advice_payload)
    turn_order_context_guard = _build_turn_order_context_prompt_guard(advice_payload)
    opponent_move_context_guard = _build_opponent_move_context_prompt_guard(advice_payload)
    battle_state_context_guard = _build_battle_state_context_prompt_guard(advice_payload)
    item_event_context_guard = _build_item_event_context_prompt_guard(advice_payload)
    return (
        "You are Master Ball Advisor. Recommend the best one-turn action using "
        "only the selected Pokemon identity and UI state below. Be concise, "
        "name the recommended direction, and mention the main limitation in the "
        "data. "
        f"{turn_snapshot_guard}"
        f"{turn_pipeline_guard}"
        f"{turn_order_context_guard}"
        f"{opponent_move_context_guard}"
        f"{battle_state_context_guard}"
        f"{item_event_context_guard}"
        "If a damage_estimate is present, use it only under its stated "
        "assumption_profile and never describe it as final battle damage. Do "
        "not claim OHKO, 2HKO, KO chance, survival, or speed order unless those "
        "fields are explicitly provided. If ko_context is present, treat it as "
        "limited damage-roll context only, not final battle truth. ko_context "
        "does not change raw damage_range or rolls; OHKO chance is based on "
        "damage rolls only, and 2HKO context is a limited min/max estimate, "
        "not final turn simulation. ko_context does not model accuracy, speed "
        "order, priority, recovery, hazards, chip damage, switching, protection, "
        "or turn sequencing. survival_context is separate from raw "
        "ko_context and is not included in KO probability. If opponent_moves is present, treat "
        "known_moves as user-confirmed and candidate_moves only as possible, "
        "not confirmed, opponent moves. You may mention candidate moves as "
        "possible threats, but label them as unconfirmed. Opponent known move "
        "damage estimates, when present, are rough default-assumption threat "
        "references against my_active. User-confirmed final stats may be used "
        f"{available_item_context_guard}"
        "when stat_profiles provides them, but do not infer EVs, IVs, nature, "
        "items, or speed order from final stats. If speed_context is present, "
        "treat it as raw/effective Speed comparison only, not final turn order. If "
        "speed_context.is_final_turn_order is false, do not say a Pokemon will "
        "move first or that turn order is guaranteed. Use wording such as "
        "based on raw Speed only or appears faster by raw Speed. Default Speed "
        "fallback is not used in v0.30; raw/effective Speed comparison requires "
        "user-confirmed final Speed for both active Pokemon. If effective_speed "
        "is present, treat it as a supported speed modifier estimate, not final "
        "turn order. Choice Scarf speed may be included only when speed_context "
        "marks it applied from a user-confirmed item; for Choice Scarf, choice "
        "lock is still not modeled. If raw Speed and effective Speed disagree, explain the "
        "difference without saying turn order is guaranteed. Do not apply "
        "priority, Tailwind, Trick Room, paralysis, Speed stages, or ability "
        "speed effects unless explicit calculated fields say they are modeled. "
        "Quick Claw speed-order context may appear only as limited "
        "speed_order_context. speed_order_context applies only when Quick "
        "Claw is user-confirmed and Champions legal. It may say Quick Claw "
        "may affect move order or can occasionally affect move order, but "
        "move order is not fully modeled and this is not guaranteed priority. "
        "Final move order, activation probability, speed ties, priority, "
        "Trick Room, Tailwind, paralysis, boosts, abilities, weather, item "
        "consumption, and turn sequencing are not modeled. Do not say will "
        "move first, guaranteed outspeeds, confirmed first, always acts "
        "before, wins the speed interaction, or safe because it moves first "
        "from speed_order_context. If speed_order_context is unavailable, "
        "treat the reason as developer/debug/contract metadata only and do "
        "not mention the item name, effect, or unavailable reason in default "
        "advice unless the user explicitly asks. Choice Scarf is not modeled "
        "through speed_order_context; keep Choice Scarf in speed_context. "
        "If item_profiles is present, "
        "distinguish unknown, none, system_default_none, and user_confirmed "
        "items. Only item effects marked as applied in "
        "damage_estimate.item_effects are included in damage numbers. Legal "
        "items and modeled item effects are separate concepts: a "
        "legal_but_not_modeled selected item may be user-confirmed, but its "
        "effect is not included unless item_effects marks it applied. "
        "For type boosting items, say the damage modifier is included only "
        "when damage_estimate.item_effects.attacker_item.status is applied; "
        "do not say a type boosting item boosted damage when the move type "
        "does not match or the item is unsupported. Legal item selection does "
        "not imply the selected item has a modeled effect. Fairy Feather is "
        "legal but not damage-modeled until a catalog-backed modifier exists. "
        "Type-boost item context may appear only as limited type_boost_context. "
        "type_boost_context is an advice context for user-confirmed, Champions "
        "legal, damage-supported type-boosting items when the move type matches "
        "the boosted type. It does not change raw damage_range or rolls beyond "
        "the existing damage_estimate.item_effects calculation, and ko_context "
        "is unchanged by type_boost_context. Type-boost-adjusted KO/OHKO/2HKO "
        "context is not calculated. Do not say boosted damage guarantees KO, "
        "secures the KO, proves the KO, or is final battle damage. If "
        "type_boost_context is unavailable, treat the reason as developer/"
        "debug/contract metadata only and do not mention the item name, effect, "
        "or unavailable reason in default advice unless the user explicitly asks. "
        "Light Ball species-stat item context may appear only as limited "
        "species_stat_item_context. species_stat_item_context applies only "
        "when Light Ball is user-confirmed, Champions legal, holder species "
        "is Pikachu, and local species-stat metadata exists. It is a sibling "
        "explanation of an applied Light Ball modifier in "
        "damage_estimate.item_effects. Eligible Pikachu Light Ball damage "
        "estimates use default stat assumptions plus the supported Light Ball "
        "species-stat modifier, and raw damage rolls plus ko_context are based "
        "on those adjusted estimate rolls. "
        "damage_estimate.item_effects remains the source of truth for whether "
        "a supported item modifier was applied to a specific estimate. When "
        "species_stat_item_context is available, say Light Ball is a "
        "Pikachu-specific offensive item context applied in the damage estimate "
        "when damage_estimate.item_effects marks the supported modifier as "
        "applied. "
        "Do not say Light Ball is not included or Light Ball is not modeled "
        "when species_stat_item_context is available. Say this is not final "
        "stat truth and not a final KO guarantee. Do not generalize Light "
        "Ball to non-Pikachu holders. Do not say guaranteed KO, always doubles "
        "damage, confirmed OHKO because of Light Ball, all Electric-type "
        "Pokemon benefit from Light Ball, Light Ball works on any holder, "
        "final stats are fully known, or exact EV/IV/nature-adjusted stats "
        "are known. If species_stat_item_context is unavailable, treat the "
        "reason as developer/debug/contract metadata only and do not mention "
        "Light Ball, non-Pikachu mismatch, unsupported reason, missing "
        "metadata, or not modeled wording in default advice unless the user "
        "explicitly asks. "
        "Damage-supported non-legal/debug items are not normal legal selector "
        "options. If a user-confirmed item is blocked by legal item coverage "
        "or marked future-only, treat the block reason as developer/debug/"
        "contract metadata and do not include that item effect in normal "
        "user-facing recommendation text. In default advice, do not mention "
        "the blocked item name, do not say user-confirmed Loaded Dice, do not "
        "say Power Herb, do not say the item is not modeled, and do not say "
        "the item effect is not included. Do not use generic substitutes such "
        "as the user-confirmed item effect, held item effect, selected item "
        "effect, or item-based limitation for blocked or future-only items. "
        "Do not mention that a blocked item exists by saying its effect is "
        "absent, ignored, unavailable, excluded, unsupported, or outside the "
        "estimate. Do not say Loaded Dice is not "
        "modeled or Power Herb is not modeled unless the user explicitly asks "
        "about that item. If the user explicitly asks about a blocked item, "
        "explain only that Champions legal coverage is not confirmed, so the "
        "item effect is not reflected in advice. Do not imply blocked or "
        "future-only items are available in Champions. For unavailable, "
        "deferred, blocked, unconfirmed, non-triggered, or absent item "
        "contexts, treat the reason as developer/debug/contract metadata by "
        "default. Do not say item effect is not included, opponent's item "
        "effect is not included, user-confirmed item effect is not included, "
        "item is not modeled, item effect is not applied, not included in "
        "this estimate, or not reflected in the calculation in default "
        "advice. Do not mention unavailable or deferred item names or effects "
        "unless the user explicitly asks about that item. If an "
        "attacker item effect is applied, mention the supported item damage "
        "modifier and do not describe the estimate as only default "
        "assumptions; describe it as default assumptions plus the supported "
        "item modifier. If Life Orb is applied, say recoil is not modeled. If "
        "Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled. "
        "Do not mention choice lock for non-Choice items such as Charcoal, "
        "Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, "
        "Leftovers, Focus Sash, or Focus Band. Life Orb recoil is not connected. "
        "Sitrus Berry and Leftovers recovery may appear only as limited "
        "recovery_context; it does not change raw damage_range or rolls. "
        "ko_context is unchanged by recovery_context, and KO/OHKO/2HKO "
        "estimates do not include recovery. recovery_context applies only "
        "when Sitrus Berry or "
        "Leftovers is user-confirmed and defender max HP is available. Sitrus "
        "Berry recovery_context is threshold recovery limited context; exact "
        "activation timing and item consumption are not tracked. Leftovers "
        "recovery_context is end-of-turn limited context; exact turn "
        "sequencing is not modeled. When recovery_context is available, keep "
        "recovery wording concise and say exact activation timing, item "
        "consumption, and turn sequencing are not modeled. Say recovery may "
        "affect follow-up KO/2HKO only under limited assumptions; do not claim "
        "final 2HKO or 3HKO truth without Turn Engine, and do not infer "
        "recovery if the item is unknown or unconfirmed. Do not say Sitrus "
        "Berry definitely activates, KO chance includes recovery, or recovery "
        "changes the damage range. Do not combine Focus Sash and recovery into final "
        "outcome claims. Bright Powder accuracy may appear only as limited "
        "accuracy_context. accuracy_context does not change raw damage_range "
        "or rolls, and ko_context is unchanged by accuracy_context. "
        "KO/OHKO/2HKO estimates do not include hit chance. Bright Powder may "
        "reduce hit reliability, but it is not damage reduction. "
        "accuracy_context applies only when Bright Powder is user-confirmed "
        "and move accuracy metadata is available. When accuracy_context is "
        "available, keep accuracy wording concise and mention that raw damage "
        "and KO/OHKO/2HKO estimates do not include hit chance. Include one "
        "concise limitation sentence that final hit probability, "
        "accuracy/evasion stages, ability/weather interactions, multi-hit "
        "accuracy, and turn sequencing are not modeled. Hit-adjusted KO "
        "probability is not calculated. Final hit probability is not "
        "calculated. Do not claim the move will miss or that a miss is "
        "guaranteed, and do not say the hit-adjusted KO chance is a percent "
        "unless an explicit future field calculates it. Do not infer Bright "
        "Powder if the item is unknown or unconfirmed. Scope Lens critical-hit "
        "context may appear only as limited critical_context. critical_context "
        "does not change raw damage_range or rolls, and ko_context is "
        "unchanged by critical_context. KO/OHKO/2HKO estimates do not include "
        "crit chance. Scope Lens may increase critical-hit likelihood, but it "
        "is not a direct damage boost. critical_context applies only when "
        "Scope Lens is user-confirmed. When critical_context is available, "
        "keep critical-hit wording concise and mention that raw damage and "
        "KO/OHKO/2HKO estimates do not include crit chance. Final "
        "critical-hit probability is not calculated. Crit-adjusted KO "
        "probability is not calculated. Do not claim the move will crit or "
        "that a critical hit is guaranteed. Do not infer Scope Lens if "
        "the item is unknown or unconfirmed. Critical-hit stages, abilities, "
        "move-specific crit effects, and turn sequencing are not modeled. "
        "King's Rock flinch context may appear only as limited "
        "flinch_context. flinch_context does not change raw damage_range or "
        "rolls, and ko_context is unchanged by flinch_context. "
        "KO/OHKO/2HKO estimates do not include flinch chance. King's Rock "
        "may add flinch pressure, but it is not a direct damage boost. "
        "flinch_context applies only when King's Rock is user-confirmed. "
        "When flinch_context is available, say the raw damage estimate is "
        "unchanged and raw ko_context is unchanged. "
        "Do not describe King's Rock with awkward wording such as damage "
        "modifier is not included; say raw damage estimate is unchanged "
        "instead. "
        "When flinch_context is available, keep flinch wording concise and "
        "mention that raw damage and KO/OHKO/2HKO estimates do not include "
        "flinch chance. Include one concise limitation sentence that speed "
        "order, target action state, abilities, multi-hit handling, and turn "
        "sequencing are not modeled. Final flinch probability is not calculated. "
        "Flinch-adjusted turn or outcome probability is not calculated. Do "
        "not claim the target will flinch, cannot move, or that flinch is "
        "guaranteed. Do not infer King's Rock if the item is unknown or "
        "unconfirmed. Speed order, target action state, abilities, multi-hit "
        "handling, and turn sequencing are not modeled. Loaded Dice multi-hit "
        "context may appear only as limited multi_hit_context. "
        "multi_hit_context does not change raw damage_range or rolls, and "
        "ko_context is unchanged by multi_hit_context. KO/OHKO/2HKO estimates "
        "do not include multi-hit count changes. Loaded Dice may improve "
        "multi-hit reliability for eligible moves, but it is not a direct "
        "damage boost. multi_hit_context applies only when Loaded Dice is "
        "user-confirmed, Champions legal coverage is confirmed, and move "
        "multi-hit metadata is available. When "
        "multi_hit_context is available, keep multi-hit wording concise and "
        "mention that raw damage and KO/OHKO/2HKO estimates do not include "
        "multi-hit count changes. Final hit count probability is not "
        "calculated. Multi-hit-adjusted KO probability is not calculated. Do "
        "not claim a specific number of hits will occur or that 5 hits are "
        "guaranteed. Do not claim Loaded Dice breaks Focus Sash unless that "
        "interaction is explicitly modeled. Do not infer Loaded Dice if the "
        "item is unknown or unconfirmed. Focus Sash, King's Rock, accuracy, "
        "crit per-hit handling, and turn sequencing are not modeled. "
        "Type-resist berry context may appear only as limited "
        "resist_berry_context. resist_berry_context does not change raw "
        "damage_range or rolls, and ko_context is unchanged by "
        "resist_berry_context. KO/OHKO/2HKO estimates do not include berry "
        "reduction; when resist_berry_context is available, explicitly say "
        "the raw damage estimate is unchanged and raw ko_context is "
        "unchanged. "
        "If resist_berry_context is unavailable, treat the unavailable reason "
        "as developer/debug/contract metadata only and do not mention the "
        "berry name, berry effect, or unavailable reason in default advice. "
        "Do not say Yache Berry effect is not applied, do not say the berry "
        "effect is not included, and do not say the berry is not modeled in "
        "default advice unless the user explicitly asks about that berry. "
        "A standard type-resist berry may reduce a qualifying "
        "super-effective hit, but berry-adjusted damage is not calculated. "
        "Berry-adjusted KO probability is not calculated. Item consumption "
        "is not tracked. Do not say the Pokemon definitely survives. Do not "
        "infer a resist berry if the item is unknown or unconfirmed. "
        "Resist berry edge cases require explicit support before advice can "
        "use them. Chilan Berry context may appear only as limited "
        "chilan_berry_context. chilan_berry_context applies only when Chilan "
        "Berry is user-confirmed, Champions legal coverage is confirmed, "
        "local metadata marks always_resist true for Normal, incoming move "
        "type is Normal, and the move is damaging. It does not change raw "
        "damage_range or rolls, and ko_context is unchanged. KO/OHKO/2HKO "
        "estimates do not include Chilan Berry reduction. Chilan-adjusted "
        "damage and Chilan-adjusted KO probability are not calculated. Item "
        "consumption is not tracked. When chilan_berry_context is available, "
        "say Chilan Berry is a Normal-type limited context and may reduce "
        "damage from a Normal-type damaging move. Say this limited context is "
        "separate from raw damage rolls and not integrated into final KO odds; "
        "raw damage rolls and ko_context remain based on the current "
        "calculator. Do not say Chilan Berry is not included or Chilan Berry "
        "is not modeled when chilan_berry_context is available. Do not say "
        "guaranteed survival, confirmed live, will survive because of Chilan "
        "Berry, KO chance is reduced to a value, final damage is halved, raw "
        "damage rolls already include Chilan Berry, or Chilan Berry applies "
        "to all move types. If chilan_berry_context is unavailable, treat "
        "the unavailable reason as developer/debug/contract metadata only "
        "and do not mention Chilan Berry, its effect, or unavailable reason "
        "in default advice unless the user explicitly asks. "
        "Focus Sash and Focus Band survival may appear only as limited "
        "survival_context, not as damage reduction; survival_context does "
        "not change raw damage_range or rolls and ko_context is unchanged. "
        "Focus Sash survival_context applies only when Focus Sash is "
        "user-confirmed and HP is full. When Focus Sash survival_context is "
        "available, say may survive at 1 HP; do not say will survive, "
        "definitely survives, or guarantees survival. Focus Band "
        "survival_context applies only when Focus Band is user-confirmed, "
        "Champions legal, and the raw incoming hit is potentially lethal. "
        "When Focus Band survival_context is available, say may occasionally "
        "survive and survival is not guaranteed; do not say will survive, "
        "guaranteed survive, cannot be KO'd, confirmed survival, safe to "
        "take the hit, or survives this hit. Focus Band activation "
        "probability and final survival probability are not calculated, "
        "and KO/OHKO/2HKO estimates do not include Focus Band activation. "
        "When survival_context is available, include one concise limitation "
        "sentence: multi-hit moves, hazards, chip damage, item consumption, "
        "activation probability, and exact turn sequencing are not modeled. "
        "Multi-hit moves, hazards, residual damage, weather/status chip, "
        "ability interactions, and exact turn sequencing are not modeled "
        "for survival_context. Do not infer Focus Sash or Focus Band if "
        "the item is unknown or unconfirmed. When discussing type matchups, "
        "use damage_estimate.type_effectiveness if present and do not call a "
        "move super effective, resisted, or immune unless that field supports "
        "it. Do not print raw type_effectiveness labels such as super_effective "
        "or not_very_effective; convert them to natural wording: super effective, "
        "not very effective, immune/no effect, or neutral. Opponent candidate move damage is not "
        "calculated in v0.18. Use my_available_moves damage_estimates to "
        "compare the user's own move options. If opponent_assumptions is "
        "present, treat possible_samples only as context-only risk profiles, "
        "not confirmed opponent sets. Do not describe sample_assumed data as "
        "user-confirmed information. Opponent assumptions version fields are "
        "developer/contract metadata; do not mention schema_version, "
        "metadata_version, or payload_features in user-facing battle advice. "
        "If calculation_usage is context_only, do "
        "not say those samples changed damage_estimate or speed_context. Do "
        "not interpret null prior_probability as zero probability, and do not "
        "claim Top-K omitted archetypes are impossible. Do not infer final "
        "turn order, KO, survival, or exact stats from possible samples. When "
        "opponent_assumptions.available is true and possible_samples exist, "
        "include at most one short limitation sentence that possible sample "
        "context exists, for example: possible opponent samples exist, but "
        "they are context only and not confirmed. Do not dump sample_id, full "
        "stats, source metadata, update_policy, coverage_probability, or full "
        "Top-K sample lists into the response. If opponent_assumptions is "
        "unavailable, do not invent samples or force a sample limitation. "
        "Opponent sample role, archetype_id, and possible_items are context-only "
        "metadata, not confirmed opponent information. Possible_items are "
        "possible assumptions, not confirmed held items. Do not enumerate "
        "opponent sample metadata by default; keep sample visibility concise.\n\n"
        f"{json.dumps(advice_payload, ensure_ascii=False, indent=2)}"
    )


def _selected_move_payload_from_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    moves = payload.get("moves")
    if not isinstance(moves, dict):
        return None
    selected_move = moves.get("my_selected_move")
    if not isinstance(selected_move, dict):
        return None
    return selected_move


def _build_optional_turn_order_context_for_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    own_base_speed = _active_base_speed(payload, "my_active")
    opponent_base_speed = _active_base_speed(payload, "opponent_active")
    own_final_speed = _confirmed_final_speed(payload, "my_active")
    opponent_final_speed = _confirmed_final_speed(payload, "opponent_active")
    candidate_modifiers = _turn_order_candidate_modifiers(payload)

    has_speed_source = (own_base_speed is not None and opponent_base_speed is not None) or (
        own_final_speed is not None and opponent_final_speed is not None
    )
    if not has_speed_source and not candidate_modifiers:
        return None

    return build_deterministic_turn_order_context(
        own_move_priority=None,
        opponent_move_priority=None,
        own_base_speed=own_base_speed,
        opponent_base_speed=opponent_base_speed,
        own_confirmed_final_speed=own_final_speed,
        opponent_confirmed_final_speed=opponent_final_speed,
        candidate_modifiers=candidate_modifiers,
    )


def _build_optional_opponent_move_context_for_advice_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    opponent_moves = payload.get("opponent_moves")
    if not isinstance(opponent_moves, dict):
        return None

    candidate_moves: list[dict[str, Any]] = []
    for move in _mapping_list(opponent_moves.get("known_moves")):
        visible_move = _opponent_context_move_from_payload(move, source="visible_ui")
        if visible_move is not None:
            candidate_moves.append(visible_move)
    for move in _mapping_list(opponent_moves.get("candidate_moves")):
        source = move.get("source")
        candidate_source = source if source in OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES else "visible_or_cache_candidate"
        candidate_move = _opponent_context_move_from_payload(move, source=str(candidate_source))
        if candidate_move is not None:
            candidate_moves.append(candidate_move)

    if not candidate_moves:
        return None

    return build_opponent_move_context(
        candidate_moves=candidate_moves,
        selected_opponent_move={"status": "unknown"},
    )


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _opponent_context_move_from_payload(move: dict[str, Any], *, source: str) -> dict[str, Any] | None:
    move_id = move.get("move_id")
    if not isinstance(move_id, str) or not move_id:
        return None

    normalized: dict[str, Any] = {
        "move_id": move_id,
        "source": source,
    }
    name = move.get("name") or move.get("name_en") or move.get("name_ko")
    if isinstance(name, str) and name:
        normalized["name"] = name
    for key in ("type", "category", "power", "accuracy", "priority", "target", "effect_flags"):
        value = move.get(key)
        if value is not None:
            normalized[key] = value
    return normalized


def _active_base_speed(payload: dict[str, Any], side: str) -> int | None:
    pokemon = payload.get("pokemon")
    if not isinstance(pokemon, dict):
        return None
    active = pokemon.get(side)
    if not isinstance(active, dict):
        return None
    base_stats = active.get("base_stats")
    if not isinstance(base_stats, dict):
        return None
    speed = base_stats.get("speed")
    return speed if isinstance(speed, int) else None


def _confirmed_final_speed(payload: dict[str, Any], side: str) -> int | None:
    stat_profiles = payload.get("stat_profiles")
    if not isinstance(stat_profiles, dict):
        return None
    profile = stat_profiles.get(side)
    if not isinstance(profile, dict) or profile.get("status") != "user_confirmed_final_stats":
        return None
    final_stats = profile.get("final_stats")
    if not isinstance(final_stats, dict):
        return None
    speed = final_stats.get("spe")
    return speed if isinstance(speed, int) else None


def _turn_order_candidate_modifiers(payload: dict[str, Any]) -> list[dict[str, str]]:
    selected_move = _selected_move_payload_from_advice_payload(payload)
    if selected_move is None:
        return []
    speed_order_context = selected_move.get("speed_order_context")
    if not isinstance(speed_order_context, dict) or speed_order_context.get("available") is not True:
        return []
    item = speed_order_context.get("item")
    item_id = item.get("item_id") if isinstance(item, dict) else None
    if item_id != "quick-claw":
        return []
    return [
        {
            "source": "Quick Claw",
            "effect": "may alter move order",
        }
    ]


def _string_field(payload: dict[str, Any] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _move_payload_ref(payload: dict[str, Any] | None, key: str) -> str | None:
    if payload is None or key not in payload:
        return None
    return f"moves.my_selected_move.{key}"


def _add_turn_snapshot_to_advice_payload(
    payload: dict[str, Any],
    turn_snapshot: TurnSnapshot | dict[str, Any] | None,
) -> None:
    if turn_snapshot is None:
        return

    normalized_snapshot = normalize_turn_snapshot(turn_snapshot)
    payload["turn_snapshot"] = normalized_snapshot.to_dict()

    scenario = payload.setdefault("scenario", {})
    limitations = list(scenario.get("known_limitations") or ())
    for limitation in TURN_SNAPSHOT_KNOWN_LIMITATIONS:
        if limitation not in limitations:
            limitations.append(limitation)
    scenario["known_limitations"] = limitations


def _add_turn_pipeline_to_advice_payload(
    payload: dict[str, Any],
    turn_pipeline: TurnPipelineResult | dict[str, Any] | None,
) -> None:
    if turn_pipeline is None:
        return

    normalized_pipeline = normalize_turn_pipeline_result(turn_pipeline)
    if normalized_pipeline.simulated == "full":
        raise ValueError("turn_pipeline simulated='full' is not allowed in advice payload")
    if not normalized_pipeline.limitations:
        raise ValueError("turn_pipeline limitations are required")

    for event in normalized_pipeline.events:
        _validate_turn_pipeline_event_wording(event.to_dict())

    payload["turn_pipeline"] = normalized_pipeline.to_dict()

    scenario = payload.setdefault("scenario", {})
    limitations = list(scenario.get("known_limitations") or ())
    for limitation in TURN_PIPELINE_KNOWN_LIMITATIONS:
        if limitation not in limitations:
            limitations.append(limitation)
    scenario["known_limitations"] = limitations


def _add_turn_order_context_to_advice_payload(
    payload: dict[str, Any],
    turn_order_context: dict[str, Any] | None,
    *,
    enable_turn_order_context: bool,
) -> None:
    if not enable_turn_order_context:
        return
    if turn_order_context is None:
        return

    context = deepcopy(turn_order_context)
    _validate_turn_order_context_payload(context)
    payload["turn_order_context"] = context


def _add_opponent_move_context_to_advice_payload(
    payload: dict[str, Any],
    opponent_move_context: dict[str, Any] | None,
    *,
    enable_opponent_move_context: bool,
) -> None:
    if not enable_opponent_move_context:
        return
    if opponent_move_context is None:
        return

    context = deepcopy(opponent_move_context)
    _validate_opponent_move_context_payload(context)
    if _is_empty_opponent_move_context(context):
        return
    payload["opponent_move_context"] = context


def _add_battle_state_context_to_advice_payload(
    payload: dict[str, Any],
    battle_state_context: dict[str, Any] | None,
    *,
    enable_battle_state_context: bool,
) -> None:
    if not enable_battle_state_context:
        return
    if battle_state_context is None:
        return
    if not battle_state_context:
        return

    context = deepcopy(battle_state_context)
    _validate_battle_state_context_payload(context)
    if _is_empty_battle_state_context(context):
        return
    payload["battle_state_context"] = context


def _add_item_event_context_to_advice_payload(
    payload: dict[str, Any],
    item_event_context: dict[str, Any] | None,
    *,
    enable_item_event_context: bool,
) -> None:
    if not enable_item_event_context or item_event_context is None:
        return

    context = deepcopy(item_event_context)
    if not isinstance(context, dict) or set(context) != {"observed_events"}:
        raise ValueError("item_event_context must contain observed_events only")
    observed_events = context.get("observed_events")
    if not isinstance(observed_events, list):
        raise ValueError("item_event_context observed_events must be a list")

    normalized_events: list[dict[str, Any]] = []
    for event in observed_events:
        if not isinstance(event, dict):
            raise ValueError("item_event_context observed_events must contain mappings")
        confidence = event.get("confidence")
        candidate = {key: value for key, value in event.items() if key != "confidence"}
        normalized = validate_explicit_user_item_event_confirmation(candidate)
        if confidence != "observed":
            raise ValueError("item_event_context observed event confidence must be observed")
        normalized_events.append({**normalized, "confidence": "observed"})

    if normalized_events:
        payload["item_event_context"] = {"observed_events": normalized_events}


def _validate_battle_state_context_payload(context: dict[str, Any]) -> None:
    if not isinstance(context, dict):
        raise ValueError("battle_state_context must be a mapping")
    if context.get("kind") != "battle_state_context":
        raise ValueError("battle_state_context kind must be battle_state_context")
    if context.get("confidence") not in {"limited", "unknown"}:
        raise ValueError("battle_state_context confidence is not allowed")
    if set(context) != {
        "kind",
        "confidence",
        "self_active",
        "opponent_active",
        "field",
        "known_conditions",
        "unsupported",
        "safety_notes",
    }:
        raise ValueError("battle_state_context top-level shape is not allowed")

    _validate_battle_state_active_side(context.get("self_active"), "self_active")
    _validate_battle_state_active_side(context.get("opponent_active"), "opponent_active")
    _validate_battle_state_field(context.get("field"))

    known_conditions = context.get("known_conditions")
    if not isinstance(known_conditions, list):
        raise ValueError("battle_state_context known_conditions must be a list")
    for condition in known_conditions:
        if not isinstance(condition, dict):
            raise ValueError("battle_state_context known_conditions must contain mappings")

    unsupported = context.get("unsupported")
    required_unsupported = set(BATTLE_STATE_CONTEXT_UNSUPPORTED_BOUNDARIES)
    if not isinstance(unsupported, list) or not required_unsupported.issubset(set(unsupported)):
        raise ValueError("battle_state_context unsupported boundaries are required")

    safety_notes = context.get("safety_notes")
    required_safety_notes = set(BATTLE_STATE_CONTEXT_SAFETY_NOTES)
    if not isinstance(safety_notes, list) or not required_safety_notes.issubset(set(safety_notes)):
        raise ValueError("battle_state_context safety notes are required")

    _validate_battle_state_context_sources(context)
    _validate_no_battle_state_context_forbidden_fields(context)


def _validate_battle_state_active_side(active_side: Any, side_name: str) -> None:
    if not isinstance(active_side, dict):
        raise ValueError(f"battle_state_context {side_name} must be a mapping")
    if set(active_side) != set(BATTLE_STATE_CONTEXT_ACTIVE_FIELDS):
        raise ValueError(f"battle_state_context {side_name} shape is not allowed")

    _validate_battle_state_name_or_unknown(active_side["species"], f"{side_name}.species")
    _validate_battle_state_value_or_unknown(active_side["current_hp_percent"], f"{side_name}.current_hp_percent")
    for field_name in ("status", "boosts"):
        _validate_battle_state_known_value_or_unknown(active_side[field_name], f"{side_name}.{field_name}")
    _validate_battle_state_item_or_unknown(active_side["item"], f"{side_name}.item")


def _validate_battle_state_field(field: Any) -> None:
    if not isinstance(field, dict):
        raise ValueError("battle_state_context field must be a mapping")
    if set(field) != set(BATTLE_STATE_CONTEXT_FIELD_FIELDS):
        raise ValueError("battle_state_context field shape is not allowed")
    for field_name in BATTLE_STATE_CONTEXT_FIELD_FIELDS:
        _validate_battle_state_known_field_value_or_unknown(field[field_name], f"field.{field_name}")


def _validate_battle_state_name_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    if not value.get("name"):
        raise ValueError(f"battle_state_context {field_name} requires name")


def _validate_battle_state_value_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")


def _validate_battle_state_known_value_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("known") is not True:
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")


def _validate_battle_state_item_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("known") is not True:
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")
    if value.get("source") not in BATTLE_STATE_CONTEXT_ITEM_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")


def _validate_battle_state_known_field_value_or_unknown(value: Any, field_name: str) -> None:
    if value == BATTLE_STATE_CONTEXT_UNKNOWN_FIELD:
        return
    if not isinstance(value, dict):
        raise ValueError(f"battle_state_context {field_name} must be a mapping")
    if value.get("known") is not True:
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")
    if value.get("source") not in BATTLE_STATE_CONTEXT_FIELD_ALLOWED_SOURCES:
        raise ValueError(f"battle_state_context {field_name} source is not allowed")
    known_value = value.get("value")
    if known_value is None or known_value == "unknown":
        raise ValueError(f"battle_state_context {field_name} requires known value")
    field_key = field_name.rsplit(".", maxsplit=1)[-1]
    if not _battle_state_field_value_is_allowed(field_key, known_value):
        raise ValueError(f"battle_state_context {field_name} known value is not allowed")


def _battle_state_field_value_is_allowed(field_name: str, value: Any) -> bool:
    if field_name in {"screens", "hazards"}:
        return _battle_state_side_specific_field_value_is_allowed(value)
    if field_name in {"weather", "terrain"}:
        return isinstance(value, str) and bool(value.strip())
    if field_name == "room":
        return _battle_state_simple_field_value_is_allowed(value)
    return False


def _battle_state_simple_field_value_is_allowed(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return bool(value) and all(isinstance(key, str) and key.strip() for key in value)
    return False


def _battle_state_side_specific_field_value_is_allowed(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    if not set(value).issubset({"self", "opponent"}):
        return False
    if not all(_battle_state_side_condition_list_is_allowed(side_value) for side_value in value.values()):
        return False
    if any(_battle_state_side_condition_list_has_known_value(side_value) for side_value in value.values()):
        return True
    return set(value) == {"self", "opponent"} and all(isinstance(side_value, list) for side_value in value.values())


def _battle_state_side_condition_list_is_allowed(value: Any) -> bool:
    if value == "unknown":
        return True
    if isinstance(value, list):
        return all(isinstance(entry, str) and bool(entry.strip()) for entry in value)
    return False


def _battle_state_side_condition_list_has_known_value(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _validate_battle_state_context_sources(value: Any) -> None:
    if isinstance(value, dict):
        source = value.get("source")
        if source is not None:
            if source in BATTLE_STATE_CONTEXT_FORBIDDEN_SOURCES:
                raise ValueError("battle_state_context source is forbidden")
            if source not in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
                raise ValueError("battle_state_context source is not allowed")
        for child_value in value.values():
            _validate_battle_state_context_sources(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_battle_state_context_sources(child_value)


def _validate_no_battle_state_context_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in BATTLE_STATE_CONTEXT_FORBIDDEN_FIELDS:
                raise ValueError(f"battle_state_context must not include {key!r}")
            _validate_no_battle_state_context_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_no_battle_state_context_forbidden_fields(child_value)


def _is_empty_battle_state_context(context: dict[str, Any]) -> bool:
    return not _battle_state_context_has_known_source(context)


def _battle_state_context_has_known_source(value: Any) -> bool:
    if isinstance(value, dict):
        source = value.get("source")
        if source in BATTLE_STATE_CONTEXT_ALLOWED_SOURCES:
            return True
        return any(_battle_state_context_has_known_source(child_value) for child_value in value.values())
    if isinstance(value, list):
        return any(_battle_state_context_has_known_source(child_value) for child_value in value)
    return False


def _validate_opponent_move_context_payload(context: dict[str, Any]) -> None:
    if context.get("kind") != "opponent_move_context":
        raise ValueError("opponent_move_context kind must be opponent_move_context")
    if context.get("confidence") not in {"limited", "unknown"}:
        raise ValueError("opponent_move_context confidence is not allowed")

    selected = context.get("selected_opponent_move")
    if not isinstance(selected, dict):
        raise ValueError("opponent_move_context selected_opponent_move must be a mapping")
    if selected.get("status") not in {"unknown", "explicit"}:
        raise ValueError("opponent_move_context selected_opponent_move status is not allowed")
    if selected.get("status") == "explicit":
        if selected.get("source") not in OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES:
            raise ValueError("opponent_move_context explicit selected move requires trusted source")
        if not selected.get("move_id") or not selected.get("name"):
            raise ValueError("opponent_move_context explicit selected move requires move_id and name")

    known_moves = context.get("known_opponent_moves")
    if not isinstance(known_moves, list):
        raise ValueError("opponent_move_context known_opponent_moves must be a list")
    for move in known_moves:
        if not isinstance(move, dict):
            raise ValueError("opponent_move_context known moves must be mappings")
        _validate_opponent_move_metadata_fields(move)
        if move.get("source") not in OPPONENT_MOVE_CONTEXT_TRUSTED_KNOWN_SOURCES:
            raise ValueError("opponent_move_context known move source is not trusted")
        if move.get("confirmed") is not True:
            raise ValueError("opponent_move_context known moves must be confirmed")

    candidate_moves = context.get("candidate_moves")
    if not isinstance(candidate_moves, list):
        raise ValueError("opponent_move_context candidate_moves must be a list")
    for move in candidate_moves:
        _validate_opponent_move_candidate(move)

    priority_candidates = context.get("priority_move_candidates")
    if not isinstance(priority_candidates, list):
        raise ValueError("opponent_move_context priority_move_candidates must be a list")
    for move in priority_candidates:
        _validate_opponent_move_candidate(move)

    unsupported = context.get("unsupported")
    required_unsupported = set(OPPONENT_MOVE_CONTEXT_UNSUPPORTED_BOUNDARIES)
    if not isinstance(unsupported, list) or not required_unsupported.issubset(set(unsupported)):
        raise ValueError("opponent_move_context unsupported boundaries are required")

    safety_notes = context.get("safety_notes")
    if not isinstance(safety_notes, list) or "Candidate moves are not confirmed selected moves." not in safety_notes:
        raise ValueError("opponent_move_context candidate safety note is required")

    _validate_no_opponent_move_context_forbidden_fields(context)


def _validate_opponent_move_candidate(move: Any) -> None:
    if not isinstance(move, dict):
        raise ValueError("opponent_move_context candidate moves must be mappings")
    _validate_opponent_move_metadata_fields(move)
    if move.get("source") not in OPPONENT_MOVE_CONTEXT_CANDIDATE_SOURCES:
        raise ValueError("opponent_move_context candidate source is not allowed")
    if move.get("confirmed") is not False:
        raise ValueError("opponent_move_context candidate moves must be unconfirmed")
    if move.get("selected") is not False:
        raise ValueError("opponent_move_context candidate moves must be unselected")


def _validate_opponent_move_metadata_fields(move: dict[str, Any]) -> None:
    if not set(move).issubset(OPPONENT_MOVE_CONTEXT_ALLOWED_MOVE_FIELDS):
        raise ValueError("opponent_move_context move metadata field is not allowed")


def _validate_no_opponent_move_context_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in OPPONENT_MOVE_CONTEXT_FORBIDDEN_FIELDS:
                raise ValueError(f"opponent_move_context must not include {key!r}")
            _validate_no_opponent_move_context_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_no_opponent_move_context_forbidden_fields(child_value)


def _is_empty_opponent_move_context(context: dict[str, Any]) -> bool:
    return (
        context.get("selected_opponent_move") == {"status": "unknown"}
        and not context.get("known_opponent_moves")
        and not context.get("candidate_moves")
        and not context.get("priority_move_candidates")
    )


def _validate_turn_order_context_payload(context: dict[str, Any]) -> None:
    if context.get("kind") != "deterministic_turn_order_context":
        raise ValueError("turn_order_context kind must be deterministic_turn_order_context")
    if context.get("confidence") not in TURN_ORDER_CONTEXT_CONFIDENCE_VALUES:
        raise ValueError("turn_order_context confidence is not allowed")

    priority = context.get("priority")
    if not isinstance(priority, dict):
        raise ValueError("turn_order_context priority must be a mapping")
    if priority.get("priority_relation") not in TURN_ORDER_CONTEXT_PRIORITY_RELATION_VALUES:
        raise ValueError("turn_order_context priority_relation is not allowed")

    speed = context.get("speed")
    if not isinstance(speed, dict):
        raise ValueError("turn_order_context speed must be a mapping")
    if speed.get("speed_relation") not in TURN_ORDER_CONTEXT_SPEED_RELATION_VALUES:
        raise ValueError("turn_order_context speed_relation is not allowed")

    if context.get("order_hint") not in TURN_ORDER_CONTEXT_ORDER_HINT_VALUES:
        raise ValueError("turn_order_context order_hint is not allowed")

    unsupported = context.get("unsupported")
    if not isinstance(unsupported, list) or not TURN_ORDER_CONTEXT_REQUIRED_UNSUPPORTED.issubset(set(unsupported)):
        raise ValueError("turn_order_context unsupported boundaries are required")

    modifiers = context.get("candidate_modifiers")
    if not isinstance(modifiers, list):
        raise ValueError("turn_order_context candidate_modifiers must be a list")
    for modifier in modifiers:
        if not isinstance(modifier, dict) or modifier.get("resolved") is not False:
            raise ValueError("turn_order_context candidate modifiers must be unresolved")

    _validate_no_turn_order_context_forbidden_fields(context)


def _validate_no_turn_order_context_forbidden_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            if key in TURN_ORDER_CONTEXT_FORBIDDEN_FIELDS:
                raise ValueError(f"turn_order_context must not include {key!r}")
            _validate_no_turn_order_context_forbidden_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _validate_no_turn_order_context_forbidden_fields(child_value)


def _validate_turn_pipeline_event_wording(event: dict[str, Any]) -> None:
    rendered_parts = []
    for key in ("summary", "limitations"):
        value = event.get(key)
        if isinstance(value, str):
            rendered_parts.append(value)
        elif isinstance(value, list):
            rendered_parts.extend(item for item in value if isinstance(item, str))
    rendered = " ".join(rendered_parts).lower()
    forbidden_phrases = (
        "item was consumed",
        "item has been consumed",
        "item consumption resolved",
        "exact trigger result",
        "trigger result is resolved",
        "exact post-turn hp",
        "post-turn hp is",
        "guaranteed move order",
        "speed tie resolved",
        "rng resolved",
        "full turn simulation completed",
    )
    for phrase in forbidden_phrases:
        if phrase in rendered:
            raise ValueError(f"turn_pipeline event wording must not claim {phrase!r}")


def _build_turn_snapshot_prompt_guard(payload: dict[str, Any]) -> str:
    if "turn_snapshot" not in payload:
        return ""
    return (
        "If turn_snapshot is present, treat it as selected/pre-turn known state "
        "context only, not full turn simulation. Do not claim full turn "
        "simulation, exact item trigger result, item was consumed, exact "
        "post-turn HP, guaranteed move order, or exact status resolution from "
        "turn_snapshot alone. Item trigger evaluation, item consumption, "
        "post-damage HP updates, speed/order simulation, and exact status "
        "resolution are not implemented. Use turn_snapshot only as known state "
        "context. "
    )


def _build_turn_pipeline_prompt_guard(payload: dict[str, Any]) -> str:
    if "turn_pipeline" not in payload:
        return ""
    return (
        "If turn_pipeline is present, treat it as a limited planning/debug "
        "summary only, not full turn simulation. Do not claim RNG resolution, "
        "item consumption, exact post-turn HP, guaranteed move order, exact "
        "item trigger result, speed tie resolution, or exact status resolution "
        "from turn_pipeline. Use turn_pipeline events only as candidate or "
        "known-modifier context; candidate events are not resolved outcomes. "
        "Do not treat turn_pipeline as final battle truth or as a replacement "
        "for damage_estimate, ko_context, or existing item contexts. "
    )


def _build_turn_order_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "turn_order_context" not in payload:
        return ""
    return (
        "If turn_order_context is present, treat it as limited planning context, "
        "not a resolved move order. Use it only as a cautious hint when priority "
        "and Speed data are available. Do not claim exact final move order. Do "
        "not claim speed ties are resolved. Do not claim RNG items activate. Do "
        "not infer item consumption. Do not infer post-turn HP from "
        "turn_order_context. "
    )


def _build_opponent_move_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "opponent_move_context" not in payload:
        return ""
    return (
        "If opponent_move_context is present, treat it as based only on "
        "explicitly known or visible opponent move data. Known opponent moves "
        "are not necessarily the opponent's selected move this turn unless "
        "selected_opponent_move is explicit. Candidate moves are not confirmed "
        "moves. Candidate moves are not confirmed selected moves. Do not infer "
        "hidden movesets. Do not infer opponent sets. Do not infer the "
        "opponent's selected move unless explicitly provided. Do not infer "
        "EVs, IVs, nature, hidden item, weather, terrain, boosts, RNG results, "
        "item consumption, or post-turn HP unless explicitly provided. Treat "
        "unsupported entries as boundaries, not facts to fill in. "
    )


def _build_battle_state_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "battle_state_context" not in payload:
        return ""
    return (
        "If battle_state_context is present, treat it only as a visible or "
        "explicit battle-state snapshot, not a resolved turn simulation. "
        "Unknown battle state fields must remain unknown. Do not infer hidden "
        "items. Do not infer EVs, IVs, or nature. Do not infer boosts, status, "
        "weather, terrain, hazards, screens, or room unless explicitly "
        "provided. Do not reverse-engineer hidden state from damage estimates "
        "or KO context. Do not claim post-turn HP, item consumption, RNG "
        "result, speed tie result, Quick Claw activation, or full turn outcome "
        "from battle_state_context. Treat unsupported entries as boundaries, "
        "not facts to fill in. "
    )


def _build_item_event_context_prompt_guard(payload: dict[str, Any]) -> str:
    if "item_event_context" not in payload:
        return ""
    return (
        "If item_event_context is present, treat it only as an explicitly "
        "user-confirmed observed item event. Distinguish current known items "
        "from explicitly observed item events. Where current known item "
        "context is present, briefly acknowledge each known item by side and "
        "item as user-confirmed current context only, not an observed "
        "activation, consumption, or resolved effect. Keep those current "
        "known items separate from explicitly observed item events. Briefly "
        "acknowledge each "
        "observed event by side, item, and event type as user-confirmed "
        "observation only. It is observed context only, not "
        "a resolved mechanic result, exact calculation, post-turn state, RNG "
        "result, or resolved turn order. Do not infer exact HP, exact damage, "
        "item consumption, item effect application, Quick Claw RNG outcome, "
        "Focus Sash HP result, or Berry recovery amount from it. "
    )


def _build_available_item_context_required_mention_guard(payload: dict[str, Any]) -> str:
    labels = _collect_available_item_context_labels(payload)
    if not labels:
        return ""
    context_keys = _collect_available_item_context_keys(payload)
    contexts = "; ".join(labels)
    guard = (
        "Available item contexts are present in the advice payload: "
        f"{contexts}. Mention each listed available item context at least once "
        "when it is directly relevant to the recommendation. Do not describe "
        "these available item effects as unavailable, unmodeled, not included, "
        "not reflected, no item is considered, assuming no item, without item "
        "effects, or default no-item assumption. If a damage estimate also uses "
        "default assumptions, keep that separate from the available limited item "
        "context: say the raw damage/ko_context limitations remain, but do not "
        "erase the available item context. Keep the wording limited. Do not "
        "convert the context into final KO odds, guaranteed survival, guaranteed "
        "move order, exact final stats, or final battle truth. "
    )
    for context_key in context_keys:
        metadata = ADVICE_ITEM_CONTEXT_GUARD_METADATA.get(context_key, {})
        specific_guard = metadata.get("specific_guard")
        if isinstance(specific_guard, str) and specific_guard:
            guard += specific_guard
    return guard


def _collect_available_item_context_labels(value: Any) -> list[str]:
    labels: list[str] = []
    _collect_available_item_context_labels_into(value, labels)
    return labels


def _collect_available_item_context_keys(value: Any) -> list[str]:
    keys: list[str] = []
    _collect_available_item_context_keys_into(value, keys)
    return keys


def _collect_available_item_context_labels_into(value: Any, labels: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ADVICE_ITEM_CONTEXT_KEYS and isinstance(child, dict) and child.get("available") is True:
                labels.append(_available_item_context_label(key, child))
            _collect_available_item_context_labels_into(child, labels)
    elif isinstance(value, list):
        for item in value:
            _collect_available_item_context_labels_into(item, labels)


def _collect_available_item_context_keys_into(value: Any, keys: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                key in ADVICE_ITEM_CONTEXT_KEYS
                and isinstance(child, dict)
                and child.get("available") is True
                and key not in keys
            ):
                keys.append(key)
            _collect_available_item_context_keys_into(child, keys)
    elif isinstance(value, list):
        for item in value:
            _collect_available_item_context_keys_into(item, keys)


def _available_item_context_label(context_key: str, context: dict[str, Any]) -> str:
    item = context.get("item")
    item_name = ""
    if isinstance(item, dict):
        raw_item = item.get("name_en") or item.get("item_id")
        if isinstance(raw_item, str) and raw_item:
            item_name = raw_item
    metadata = ADVICE_ITEM_CONTEXT_GUARD_METADATA.get(context_key, {})
    raw_template = metadata.get("mention_label")
    if isinstance(raw_template, str) and raw_template:
        fallback_item_name = metadata.get("fallback_item_name")
        if not isinstance(fallback_item_name, str) or not fallback_item_name:
            fallback_item_name = context_key
        return raw_template.format(item_name=item_name or fallback_item_name)
    if item_name:
        return f"{item_name} / {context_key}"
    return context_key


def _remove_unavailable_item_contexts(value: Any) -> set[str]:
    hidden_item_sides: set[str] = set()
    if isinstance(value, dict):
        for key in list(value.keys()):
            child = value[key]
            if key in ADVICE_ITEM_CONTEXT_KEYS and isinstance(child, dict) and child.get("available") is False:
                hidden_item_sides.update(_context_item_sides(child))
                del value[key]
                continue
            hidden_item_sides.update(_remove_unavailable_item_contexts(child))
    elif isinstance(value, list):
        for item in value:
            hidden_item_sides.update(_remove_unavailable_item_contexts(item))
    return hidden_item_sides


def _collect_available_item_context_sides(value: Any) -> set[str]:
    available_item_sides: set[str] = set()
    if isinstance(value, dict):
        speed_context = value.get("speed_context")
        if isinstance(speed_context, dict):
            available_item_sides.update(_speed_context_item_sides(speed_context))
        for key, child in value.items():
            if key in ADVICE_ITEM_CONTEXT_KEYS and isinstance(child, dict) and child.get("available") is True:
                available_item_sides.update(_context_item_sides(child))
            available_item_sides.update(_collect_available_item_context_sides(child))
    elif isinstance(value, list):
        for item in value:
            available_item_sides.update(_collect_available_item_context_sides(item))
    return available_item_sides


def _speed_context_item_sides(speed_context: dict[str, Any]) -> set[str]:
    if speed_context.get("available") is not True:
        return set()
    sides: set[str] = set()
    for side in ("my_active", "opponent_active"):
        side_context = speed_context.get(side)
        if not isinstance(side_context, dict):
            continue
        modifiers = side_context.get("speed_modifiers")
        if not isinstance(modifiers, list):
            continue
        if any(_is_applied_choice_scarf_modifier(modifier) for modifier in modifiers):
            sides.add(side)
    return sides


def _is_applied_choice_scarf_modifier(modifier: Any) -> bool:
    return (
        isinstance(modifier, dict)
        and modifier.get("item_id") == "choice-scarf"
        and modifier.get("applied") is True
    )


def _context_item_sides(context: dict[str, Any]) -> set[str]:
    sides = set()
    for key in ADVICE_CONTEXT_SIDE_FIELDS:
        value = context.get(key)
        if isinstance(value, str) and value:
            sides.add(value)
    return sides


def _hide_advice_hidden_item_profiles(payload: dict[str, Any], hidden_item_sides: set[str]) -> set[str]:
    item_profiles = payload.get("item_profiles")
    if not isinstance(item_profiles, dict):
        return set()

    hidden_item_ids: set[str] = set()
    for side, profile in list(item_profiles.items()):
        if not isinstance(profile, dict):
            continue
        item_id = profile.get("item_id")
        legal_status = get_legal_item_status(item_id)
        should_hide = side in hidden_item_sides or (
            profile.get("status") == "user_confirmed"
            and legal_status.get("legal") is not True
        )
        if not should_hide:
            continue
        if isinstance(item_id, str) and item_id:
            hidden_item_ids.add(item_id)
        item_profiles[side] = {
            "status": "unknown",
            "source": "advice_payload_filter",
            "item_id": None,
            "name_en": None,
            "name_ko": None,
            "effects_scope": [],
            "damage_modifier_status": "not_applicable",
        }
    return hidden_item_ids


def _hide_advice_hidden_item_effects(value: Any, hidden_item_ids: set[str]) -> None:
    if not hidden_item_ids:
        return
    if isinstance(value, dict):
        item_id = value.get("item_id")
        if isinstance(item_id, str) and item_id in hidden_item_ids:
            _scrub_advice_hidden_item_effect(value)
        for child in value.values():
            _hide_advice_hidden_item_effects(child, hidden_item_ids)
    elif isinstance(value, list):
        for item in value:
            _hide_advice_hidden_item_effects(item, hidden_item_ids)


def _hide_move_local_unavailable_type_boost_item_effects(value: Any) -> None:
    if isinstance(value, dict):
        available_item_sides = {
            side
            for key, child in value.items()
            if key in ADVICE_ITEM_CONTEXT_KEYS
            and isinstance(child, dict)
            and child.get("available") is True
            for side in _context_item_sides(child)
        }
        for context_key in ADVICE_CONTEXTS_REQUIRING_MOVE_LOCAL_ITEM_EFFECT_SCRUB:
            context = value.get(context_key)
            if isinstance(context, dict) and context.get("available") is False:
                if _context_item_sides(context) & available_item_sides:
                    continue
                damage_estimate = value.get("damage_estimate")
                if isinstance(damage_estimate, dict):
                    item_effects = damage_estimate.get("item_effects")
                    attacker_item = item_effects.get("attacker_item") if isinstance(item_effects, dict) else None
                    if isinstance(attacker_item, dict):
                        _scrub_advice_hidden_item_effect(attacker_item)
        for child in value.values():
            _hide_move_local_unavailable_type_boost_item_effects(child)
    elif isinstance(value, list):
        for item in value:
            _hide_move_local_unavailable_type_boost_item_effects(item)


def _scrub_advice_hidden_item_effect(value: dict[str, Any]) -> None:
    value["item_id"] = None
    value["name_en"] = None
    value["name_ko"] = None
    value["status"] = "advice_payload_hidden"
    value["applied_effects"] = []
    value["unapplied_effects"] = []
    value.pop("effect_type", None)
    value.pop("boosted_type", None)
    value.pop("modifier", None)
    value.pop("reason", None)


def _remove_debug_only_limitations(value: Any) -> None:
    if isinstance(value, dict):
        for key in ("limitations", "notes"):
            values = value.get(key)
            if isinstance(values, list):
                value[key] = [
                    item
                    for item in values
                    if not _contains_debug_limitation_phrase(item)
                ]
        for child in value.values():
            _remove_debug_only_limitations(child)
    elif isinstance(value, list):
        for item in value:
            _remove_debug_only_limitations(item)


def _contains_debug_limitation_phrase(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.lower()
    return any(phrase in lowered for phrase in DEBUG_ONLY_REASON_PHRASES)


def _log_advisor_call(
    *,
    model: str,
    usage: dict[str, int],
    game_id: str,
) -> dict[str, Any]:
    logger = TokenLogger()
    try:
        logger.log_call(
            model=model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cached_tokens=usage["cached_tokens"],
            tool_name="damage_calculator",
            turn_number=1,
            game_id=game_id,
        )
        return logger.get_session_summary()
    except Exception as exc:  # pragma: no cover - defensive UI resilience path
        return {
            "total_calls": 0,
            "total_input_tokens": usage.get("input_tokens", 0),
            "total_output_tokens": usage.get("output_tokens", 0),
            "total_cached_tokens": usage.get("cached_tokens", 0),
            "estimated_cost_usd": 0.0,
            "pricing_status": UNKNOWN_MODEL_OR_UNKNOWN_PRICING,
            "pricing_status_counts": {UNKNOWN_MODEL_OR_UNKNOWN_PRICING: 1},
            "by_tool": {},
            "token_logging_error": str(exc),
        }

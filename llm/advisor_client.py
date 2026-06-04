"""Thin LLM advisor client used by UI spikes.

This module keeps PySide UI code from importing the script module directly.
The underlying quantitative scenario still lives in ``scripts.spike_advisor``
for the v0.5 spike.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from core.champions_legal_item_repository import get_legal_item_status
from llm.token_logger import UNKNOWN_MODEL_OR_UNKNOWN_PRICING, TokenLogger
from scripts.spike_advisor import (
    DEFAULT_MODEL,
    build_prompt,
    call_gemini,
    collect_battle_data,
)


ITEM_CONTEXT_FIELDS = frozenset(
    {
        "survival_context",
        "recovery_context",
        "accuracy_context",
        "critical_context",
        "flinch_context",
        "multi_hit_context",
        "resist_berry_context",
        "charge_context",
    }
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


def build_ui_advice_payload(battle_input: dict[str, Any]) -> dict[str, Any]:
    """Return the Gemini default-advice payload without debug-only item context."""
    payload = deepcopy(battle_input)
    available_item_sides = _collect_available_item_context_sides(payload)
    hidden_item_sides = _remove_unavailable_item_contexts(payload)
    hidden_item_sides -= available_item_sides
    hidden_item_ids = _hide_advice_hidden_item_profiles(payload, hidden_item_sides)
    _hide_advice_hidden_item_effects(payload, hidden_item_ids)
    return payload


def run_ui_selected_advice(
    battle_input: dict[str, Any],
    model: str | None = None,
) -> tuple[str, dict[str, int], dict[str, Any]]:
    """Run the v0.6 UI-selected Pokemon advisor flow.

    The caller passes plain dictionaries collected from UI state. This function
    owns prompt construction, Gemini invocation, and token logging.
    """
    selected_model = model or DEFAULT_MODEL
    prompt = _build_ui_selected_prompt(battle_input)
    recommendation, usage = call_gemini(prompt, selected_model)
    summary = _log_advisor_call(
        model=selected_model,
        usage=usage,
        game_id="ui_selected_pokemon_v0_6",
    )
    return recommendation, usage, summary


def _build_ui_selected_prompt(battle_input: dict[str, Any]) -> str:
    advice_payload = build_ui_advice_payload(battle_input)
    return (
        "You are Master Ball Advisor. Recommend the best one-turn action using "
        "only the selected Pokemon identity and UI state below. Be concise, "
        "name the recommended direction, and mention the main limitation in the "
        "data. If a damage_estimate is present, use it only under its stated "
        "assumption_profile and never describe it as final battle damage. Do "
        "not claim OHKO, 2HKO, KO chance, survival, or speed order unless those "
        "fields are explicitly provided. If ko_context is present, treat it as "
        "limited damage-roll context only, not final battle truth. ko_context "
        "does not change raw damage_range or rolls; OHKO chance is based on "
        "damage rolls only, and 2HKO context is a limited min/max estimate, "
        "not final turn simulation. ko_context does not model accuracy, speed "
        "order, priority, recovery, hazards, chip damage, switching, protection, "
        "or turn sequencing. Focus Sash survival_context is separate from raw "
        "ko_context and is not included in KO probability. If opponent_moves is present, treat "
        "known_moves as user-confirmed and candidate_moves only as possible, "
        "not confirmed, opponent moves. You may mention candidate moves as "
        "possible threats, but label them as unconfirmed. Opponent known move "
        "damage estimates, when present, are rough default-assumption threat "
        "references against my_active. User-confirmed final stats may be used "
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
        "Leftovers, or Focus Sash. Life Orb recoil is not connected. "
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
        "Unsupported resist berry edge cases are not modeled unless explicitly "
        "supported. "
        "Focus Sash survival may appear only as limited "
        "survival_context, not as damage reduction; it does not change raw "
        "damage_range or rolls. Focus Sash survival_context applies only "
        "when Focus Sash is user-confirmed and HP is full. When it is "
        "available, say may survive at 1 HP; do not say will survive, "
        "definitely survives, or guarantees survival. When Focus Sash survival_context is available, "
        "include one concise limitation sentence: multi-hit moves, hazards, "
        "chip damage, and exact turn sequencing are not modeled. Multi-hit "
        "moves, hazards, residual damage, weather/status chip, ability "
        "interactions, and exact turn sequencing are not modeled for Focus "
        "Sash survival_context. Do not infer Focus "
        "Sash if the item is unknown or unconfirmed. When discussing type matchups, "
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


def _remove_unavailable_item_contexts(value: Any) -> set[str]:
    hidden_item_sides: set[str] = set()
    if isinstance(value, dict):
        for key in list(value.keys()):
            child = value[key]
            if key in ITEM_CONTEXT_FIELDS and isinstance(child, dict) and child.get("available") is False:
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
        for key, child in value.items():
            if key in ITEM_CONTEXT_FIELDS and isinstance(child, dict) and child.get("available") is True:
                available_item_sides.update(_context_item_sides(child))
            available_item_sides.update(_collect_available_item_context_sides(child))
    elif isinstance(value, list):
        for item in value:
            available_item_sides.update(_collect_available_item_context_sides(item))
    return available_item_sides


def _context_item_sides(context: dict[str, Any]) -> set[str]:
    sides = set()
    for key in ("attacker_side", "defender_side"):
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
        if profile.get("status") != "user_confirmed":
            continue
        item_id = profile.get("item_id")
        legal_status = get_legal_item_status(item_id)
        should_hide = side in hidden_item_sides or legal_status.get("legal") is not True
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
            value["item_id"] = None
            value["status"] = "advice_payload_hidden"
            value["applied_effects"] = []
            value["unapplied_effects"] = []
        for child in value.values():
            _hide_advice_hidden_item_effects(child, hidden_item_ids)
    elif isinstance(value, list):
        for item in value:
            _hide_advice_hidden_item_effects(item, hidden_item_ids)


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

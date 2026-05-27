"""Thin LLM advisor client used by UI spikes.

This module keeps PySide UI code from importing the script module directly.
The underlying quantitative scenario still lives in ``scripts.spike_advisor``
for the v0.5 spike.
"""

from __future__ import annotations

import json
from typing import Any

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
    return (
        "You are Master Ball Advisor. Recommend the best one-turn action using "
        "only the selected Pokemon identity and UI state below. Be concise, "
        "name the recommended direction, and mention the main limitation in the "
        "data. If a damage_estimate is present, use it only under its stated "
        "assumption_profile and never describe it as final battle damage. Do "
        "not claim OHKO, 2HKO, KO chance, survival, or speed order unless those "
        "fields are explicitly provided. If opponent_moves is present, treat "
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
        "options. If an "
        "attacker item effect is applied, mention the supported item damage "
        "modifier and do not describe the estimate as only default "
        "assumptions; describe it as default assumptions plus the supported "
        "item modifier. If Life Orb is applied, say recoil is not modeled. If "
        "Choice Scarf, Choice Band, or Choice Specs is applied, say choice lock is not modeled. "
        "Do not mention choice lock for non-Choice items such as Charcoal, "
        "Mystic Water, Black Belt, Metal Coat, Sharp Beak, Fairy Feather, "
        "Leftovers, or Focus Sash. Life Orb recoil, Focus Sash survival, "
        "and Leftovers recovery are not connected. When discussing type matchups, "
        "use damage_estimate.type_effectiveness if present and do not call a "
        "move super effective, resisted, or immune unless that field supports "
        "it. Do not print raw type_effectiveness labels such as super_effective "
        "or not_very_effective; convert them to natural wording: super effective, "
        "not very effective, immune/no effect, or neutral. Opponent candidate move damage is not "
        "calculated in v0.18. Use my_available_moves damage_estimates to "
        "compare the user's own move options. If opponent_assumptions is "
        "present, treat possible_samples only as context-only risk profiles, "
        "not confirmed opponent sets. Do not describe sample_assumed data as "
        "user-confirmed information. If calculation_usage is context_only, do "
        "not say those samples changed damage_estimate or speed_context. Do "
        "not interpret null prior_probability as zero probability, and do not "
        "claim Top-K omitted archetypes are impossible. Do not infer final "
        "turn order, KO, survival, or exact stats from possible samples. When "
        "opponent_assumptions.available is true and possible_samples exist, "
        "briefly mention when relevant that possible sample context exists, "
        "for example: possible opponent samples exist, but they are context "
        "only and not confirmed.\n\n"
        f"{json.dumps(battle_input, ensure_ascii=False, indent=2)}"
    )


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

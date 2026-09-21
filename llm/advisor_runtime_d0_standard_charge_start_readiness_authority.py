"""Strict current-D0 readiness for ordinary charge-move charge-start semantics."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from advisor.canonical_charge_move_lifecycle import resolve_canonical_charge_move_lifecycle
from core.champions_item_repository import normalize_item_id
from llm.advisor_reducer_state_model import is_unknown_battle_fact
from llm.advisor_runtime_d0_held_item_effect_applicability_authority import (
    resolve_runtime_d0_held_item_effect_applicability_authority,
)
from llm.advisor_runtime_strategy_d0 import (
    resolve_runtime_d0_selectable_move_metadata_authority,
    runtime_strategy_d0_freshness,
)
from llm.advisor_runtime_d0_solar_charge_weather_authority import (
    freeze_runtime_d0_solar_charge_weather_decision_authority,
)


SCHEMA_VERSION = "runtime-d0-standard-charge-start-readiness-authority-v1"
_SUPPORTED_FAMILIES = frozenset({"ordinary_charge_then_damage", "weather_sensitive_charge_then_damage", "charge_turn_self_effect_then_damage"})
_SUPPORTED_MOVES = frozenset({"sky-attack", "razor-wind", "freeze-shock", "ice-burn", "solar-beam", "solar-blade", "meteor-beam", "skull-bash"})
_SOLAR_MOVES = frozenset({"solar-beam", "solar-blade"})
_SELF_EFFECT_MOVES = frozenset({"meteor-beam", "skull-bash"})
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_TRUSTED_ITEM_EVENTS = frozenset({
    "current_item_observed", "item_consumption_observed", "item_removed_observed",
})


def freeze_runtime_d0_standard_charge_start_readiness_authority(
    *,
    strategy_d0: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    action: Mapping[str, Any],
    actor: Mapping[str, Any],
    target: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze readiness for the ordinary charge-start branch only.

    This authority never claims that the selected action executed.  It answers
    only whether, if the action reaches its move execution boundary, ordinary
    charging is the supported next semantic phase or a known instant-skip
    branch may apply.
    """
    base = _base(strategy_d0, action, actor, target)
    if base is None:
        return _result("rejected", "standard_charge_identity_or_d0_invalid", {})
    fresh = runtime_strategy_d0_freshness(
        strategy_d0=strategy_d0, runtime_snapshot=runtime_snapshot,
    )
    if fresh.get("status") != "current":
        return _result("rejected", fresh.get("reason", "stale_runtime_d0"), base)

    metadata_authority = resolve_runtime_d0_selectable_move_metadata_authority(
        strategy_d0=strategy_d0, action=action,
    )
    common = {**base, "move_metadata_authority": deepcopy(metadata_authority)}
    if metadata_authority.get("status") != "resolved":
        status = metadata_authority.get("status")
        return _result(
            "rejected" if status == "rejected" else "incomplete",
            metadata_authority.get("reason", "standard_charge_move_metadata_unavailable"),
            common,
        )
    metadata = metadata_authority.get("metadata")
    if not isinstance(metadata, Mapping) or metadata.get("move_id") != base["move_id"]:
        return _result("rejected", "standard_charge_move_metadata_identity_mismatch", common)

    canonical = resolve_canonical_charge_move_lifecycle(base["move_id"])
    common["canonical_charge_lifecycle_authority"] = deepcopy(canonical)
    if canonical.get("status") == "rejected":
        return _result(
            "rejected",
            canonical.get("reason", "canonical_charge_lifecycle_rejected"),
            common,
        )
    if canonical.get("status") != "resolved":
        return _result(
            "unsupported",
            canonical.get("reason", "standard_charge_lifecycle_not_supported"),
            common,
        )
    if canonical.get("move_id") not in _SUPPORTED_MOVES:
        return _result(
            "unsupported", "standard_charge_lifecycle_family_not_supported", common,
        )
    canonical_error = _canonical_error(canonical, base["move_id"])
    if canonical_error is not None:
        return _result("rejected", canonical_error, common)

    state = runtime_snapshot.get("state") if isinstance(runtime_snapshot, Mapping) else None
    raw_actor = _pokemon(state, actor)
    raw_target = _pokemon(state, target)
    if raw_actor is None or raw_target is None:
        return _result("rejected", "standard_charge_runtime_identity_mismatch", common)

    item = _current_item_authority(raw_actor, actor, base)
    common["current_item_authority"] = deepcopy(item)
    if item["status"] == "rejected":
        return _result("rejected", item["reason"], common)
    if item["status"] == "unknown":
        return _result("incomplete", "standard_charge_current_item_unknown", common)

    power_state: dict[str, Any]
    if item["status"] == "known_absent":
        power_state = {
            "status": "not_required",
            "reason": "current_item_known_absent",
        }
    elif item.get("item_id") != "power-herb":
        power_state = {
            "status": "not_required",
            "reason": "current_item_not_power_herb",
            "item_id": item.get("item_id"),
        }
    else:
        applicability = resolve_runtime_d0_held_item_effect_applicability_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            holder=actor,
        )
        common["power_herb_applicability_authority"] = deepcopy(applicability)
        applicability_error = _power_herb_applicability_error(applicability, base, item)
        if applicability_error is not None:
            status, reason = applicability_error
            return _result(status, reason, common)
        if applicability.get("item_effects_active") is True:
            power_state = {
                "status": "active",
                "outcome": applicability.get("outcome"),
                "reason": applicability.get("reason"),
            }
        elif applicability.get("item_effects_active") is False:
            power_state = {
                "status": "suppressed",
                "outcome": applicability.get("outcome"),
                "reason": applicability.get("reason"),
            }
        else:
            return _result("rejected", "power_herb_applicability_result_invalid", common)

    if base["move_id"] in _SOLAR_MOVES:
        weather = freeze_runtime_d0_solar_charge_weather_decision_authority(
            strategy_d0=strategy_d0,
            runtime_snapshot=runtime_snapshot,
            action=action,
            actor=actor,
            target=target,
        )
        common["solar_weather_decision_authority"] = deepcopy(weather)
        if weather.get("status") != "resolved":
            return _result(
                "rejected" if weather.get("status") == "rejected" else "incomplete",
                weather.get("reason", "solar_weather_decision_unavailable"),
                common,
            )
        if weather.get("outcome") == "sunny_skip":
            return _weather_skip_ready(
                common,
                power_herb_applicability_state=power_state,
                solar_weather_decision_authority=weather,
            )
        if power_state.get("status") == "active":
            return _power_herb_skip_ready(
                common,
                power_herb_applicability_state=power_state,
                solar_weather_decision_authority=weather,
            )
        return _ready(
            common,
            power_herb_applicability_state=power_state,
            solar_weather_decision_authority=weather,
        )

    if power_state.get("status") == "active":
        return _power_herb_skip_ready(
            common,
            power_herb_applicability_state=power_state,
        )
    return _ready(
        common,
        power_herb_applicability_state=power_state,
    )


def _base(
    d0: Any,
    action: Any,
    actor: Any,
    target: Any,
) -> dict[str, Any] | None:
    if (
        not isinstance(d0, Mapping)
        or d0.get("status") != "resolved"
        or d0.get("schema_version") != "deterministic-runtime-strategy-d0-v1"
        or not _owner(actor)
        or not _owner(target)
        or not isinstance(action, Mapping)
    ):
        return None
    active = d0.get("active_owners")
    if not isinstance(active, Mapping) or actor != d0.get("decision_owner"):
        return None
    if active.get(actor["side"]) != dict(actor) or actor["side"] == target["side"]:
        return None
    target_side = "opponent" if actor["side"] == "self" else "self"
    if target["side"] != target_side or active.get(target_side) != dict(target):
        return None
    action_id, move_id = action.get("action_id"), action.get("identity")
    if (
        action.get("action_type") != "attack"
        or not isinstance(action_id, str) or not action_id
        or not isinstance(move_id, str) or not move_id
    ):
        return None
    explicit_target = action.get("target_owner")
    if explicit_target is not None and explicit_target != dict(target):
        return None
    required = (
        "session_id", "source_runtime_fingerprint",
        "strategy_preview_fingerprint", "decision_owner",
    )
    if any(not d0.get(key) for key in required):
        return None
    return {
        "session_id": d0["session_id"],
        "source_runtime_fingerprint": d0["source_runtime_fingerprint"],
        "source_branch_fingerprint": d0["strategy_preview_fingerprint"],
        "decision_owner": deepcopy(dict(d0["decision_owner"])),
        "actor": deepcopy(dict(actor)),
        "source_target_owner": deepcopy(dict(target)),
        "continuation_target_locator": {
            "session_id": target["session_id"],
            "side": target["side"],
            "slot_index": target["slot_index"],
        },
        "action_id": action_id,
        "move_id": move_id,
    }


def _canonical_error(canonical: Mapping[str, Any], move_id: str) -> str | None:
    expected_family = (
        "weather_sensitive_charge_then_damage" if move_id in _SOLAR_MOVES
        else "charge_turn_self_effect_then_damage" if move_id in _SELF_EFFECT_MOVES
        else "ordinary_charge_then_damage"
    )
    expected = {
        "move_id": move_id,
        "is_charge_move": True,
        "charge_flag_confirmed": True,
        "lifecycle_family": expected_family,
        "execution_model": "charge_then_execute",
        "charge_move_event_participation": True,
        "twoturnmove_state_usage": True,
        "existing_move_volatile_continuation": True,
        "terminal_effect_class": "damaging_move",
        "power_herb_charge_skip_possible": True,
        "canonical_recognition_grants_immediate_execution": False,
        "source": "pinned_showdown_charge_move_lifecycle_v1",
        "confidence": "authenticated_pinned_source",
    }
    if any(canonical.get(key) != value for key, value in expected.items()):
        return "standard_charge_canonical_lifecycle_mismatch"
    if canonical.get("power_herb_behavior") != "descriptive_skip_mechanism_only":
        return "standard_charge_power_herb_metadata_invalid"
    return None


def _current_item_authority(
    raw: Mapping[str, Any],
    owner: Mapping[str, Any],
    base: Mapping[str, Any],
) -> dict[str, Any]:
    value = raw.get("known_item")
    provenance = raw.get("known_item_provenance")
    common = {
        "owner": deepcopy(dict(owner)),
        "session_id": base["session_id"],
        "source_runtime_fingerprint": base["source_runtime_fingerprint"],
        "source_branch_fingerprint": base["source_branch_fingerprint"],
    }

    if isinstance(value, str) and value and not is_unknown_battle_fact(value):
        if _trusted_item_provenance(provenance, require_status="known"):
            return {
                "status": "known",
                "item_id": normalize_item_id(value),
                "source_provenance": deepcopy(dict(provenance)),
                **common,
            }
        return {
            "status": "unknown",
            "item_id": None,
            "reason": "current_item_present_without_trusted_provenance",
            **common,
        }

    if value is None:
        if provenance is None:
            return {"status": "unknown", "item_id": None, **common}
        if not isinstance(provenance, Mapping):
            return {
                "status": "rejected",
                "item_id": None,
                "reason": "standard_charge_current_item_provenance_malformed",
                **common,
            }
        event = provenance.get("event_kind")
        if event == "current_item_observed":
            if _trusted_item_provenance(provenance, require_status="known_absent"):
                return {
                    "status": "known_absent",
                    "item_id": None,
                    "source_provenance": deepcopy(dict(provenance)),
                    **common,
                }
            return {
                "status": "rejected",
                "item_id": None,
                "reason": "standard_charge_known_absent_item_provenance_invalid",
                **common,
            }
        if event in {"item_consumption_observed", "item_removed_observed"}:
            if _trusted_item_provenance(provenance, require_status=None):
                return {
                    "status": "known_absent",
                    "item_id": None,
                    "source_provenance": deepcopy(dict(provenance)),
                    **common,
                }
            return {
                "status": "rejected",
                "item_id": None,
                "reason": "standard_charge_known_absent_item_provenance_invalid",
                **common,
            }
        if is_unknown_battle_fact(value):
            return {"status": "unknown", "item_id": None, **common}
        return {
            "status": "unknown",
            "item_id": None,
            "reason": "current_item_absence_not_authenticated",
            **common,
        }

    if is_unknown_battle_fact(value):
        return {"status": "unknown", "item_id": None, **common}
    return {
        "status": "rejected",
        "item_id": None,
        "reason": "standard_charge_current_item_state_malformed",
        **common,
    }


def _trusted_item_provenance(
    provenance: Any,
    *,
    require_status: str | None,
) -> bool:
    if not isinstance(provenance, Mapping):
        return False
    event = provenance.get("event_kind")
    if event not in _TRUSTED_ITEM_EVENTS:
        return False
    if event == "current_item_observed" and provenance.get("trust") != "user_confirmed_observation":
        return False
    turn = provenance.get("turn_number")
    if not isinstance(turn, int) or isinstance(turn, bool) or turn < 1:
        return False
    if require_status is not None and provenance.get("status") != require_status:
        return False
    return True


def _power_herb_applicability_error(
    value: Any,
    base: Mapping[str, Any],
    item: Mapping[str, Any],
) -> tuple[str, str] | None:
    if not isinstance(value, Mapping):
        return "rejected", "power_herb_applicability_authority_malformed"
    if value.get("schema_version") != "runtime-d0-held-item-effect-applicability-authority-v1":
        return "rejected", "power_herb_applicability_authority_schema_mismatch"
    if value.get("status") != "resolved":
        status = value.get("status")
        return (
            "rejected" if status == "rejected" else "incomplete",
            value.get("reason", "power_herb_applicability_authority_unavailable"),
        )
    for key in (
        "session_id", "source_runtime_fingerprint",
        "source_branch_fingerprint", "decision_owner",
    ):
        if value.get(key) != base.get(key):
            return "rejected", "power_herb_applicability_authority_binding_mismatch"
    if value.get("holder") != base.get("actor"):
        return "rejected", "power_herb_applicability_holder_mismatch"
    current = value.get("current_item_authority")
    if (
        not isinstance(current, Mapping)
        or current.get("status") != "known"
        or current.get("item_id") != "power-herb"
    ):
        return "rejected", "power_herb_applicability_item_identity_mismatch"
    if item.get("status") != "known" or item.get("item_id") != "power-herb":
        return "rejected", "power_herb_current_item_identity_mismatch"
    if value.get("item_effects_active") not in {True, False}:
        return "rejected", "power_herb_applicability_result_invalid"
    return None


def _ready(
    base: Mapping[str, Any],
    *,
    power_herb_applicability_state: Mapping[str, Any],
    solar_weather_decision_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "outcome": "charge_start_ready",
        "next_semantic_phase": "charge_turn_start",
        "power_herb_applicability_state": deepcopy(dict(power_herb_applicability_state)),
        **({"solar_weather_decision_authority": deepcopy(dict(solar_weather_decision_authority)), "skip_reason": "ordinary_charge"} if isinstance(solar_weather_decision_authority, Mapping) else {}),
        "action_execution_confirmed": False,
        "immediate_damage_execution_grant": False,
        "charge_turn_state_materialized": False,
        "pp_consumed": False,
        "provenance": "strict_runtime_d0_standard_charge_start_readiness_v1",
    }


def _power_herb_skip_ready(
    base: Mapping[str, Any],
    *,
    power_herb_applicability_state: Mapping[str, Any],
    solar_weather_decision_authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "outcome": "power_herb_charge_skip_ready",
        "next_semantic_phase": "current_turn_charge_skip_terminal_execution",
        "power_herb_applicability_state": deepcopy(dict(power_herb_applicability_state)),
        **({"solar_weather_decision_authority": deepcopy(dict(solar_weather_decision_authority)), "skip_reason": "power_herb_skip"} if isinstance(solar_weather_decision_authority, Mapping) else {}),
        "action_execution_confirmed": False,
        "immediate_damage_execution_grant": False,
        "charge_turn_state_materialized": False,
        "pp_consumed": False,
        "provenance": "strict_runtime_d0_standard_charge_power_herb_skip_readiness_v1",
    }


def _weather_skip_ready(
    base: Mapping[str, Any],
    *,
    power_herb_applicability_state: Mapping[str, Any],
    solar_weather_decision_authority: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": "resolved",
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "outcome": "weather_charge_skip_ready",
        "next_semantic_phase": "current_turn_charge_skip_terminal_execution",
        "skip_reason": "weather_skip",
        "power_herb_applicability_state": deepcopy(dict(power_herb_applicability_state)),
        "solar_weather_decision_authority": deepcopy(dict(solar_weather_decision_authority)),
        "action_execution_confirmed": False,
        "immediate_damage_execution_grant": False,
        "charge_turn_state_materialized": False,
        "pp_consumed": False,
        "provenance": "strict_runtime_d0_solar_weather_skip_readiness_v1",
    }


def _pokemon(state: Any, owner: Mapping[str, Any]) -> Mapping[str, Any] | None:
    side = state.get(f"{owner['side']}_side") if isinstance(state, Mapping) else None
    roster = side.get("pokemon") if isinstance(side, Mapping) else None
    value = roster.get(owner["slot_index"]) if isinstance(roster, Mapping) else None
    return (
        value
        if isinstance(value, Mapping) and value.get("pokemon_id") == owner["pokemon_id"]
        else None
    )


def _owner(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == set(_OWNER_KEYS)
        and isinstance(value.get("session_id"), str) and bool(value["session_id"])
        and value.get("side") in {"self", "opponent"}
        and isinstance(value.get("slot_index"), int)
        and not isinstance(value.get("slot_index"), bool)
        and value["slot_index"] >= 0
        and isinstance(value.get("pokemon_id"), str)
        and bool(value["pokemon_id"])
    )


def _result(
    status: str,
    reason: str,
    base: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "status": status,
        "schema_version": SCHEMA_VERSION,
        **deepcopy(dict(base)),
        "reason": reason,
        "action_execution_confirmed": False,
        "immediate_damage_execution_grant": False,
    }

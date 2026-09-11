"""Strict detached branch projection from one exact EOT residual ledger."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_end_of_turn_residual_phase import validate_end_of_turn_residual_phase_ledger
from llm.advisor_post_eot_replacement_transition import post_eot_source_binding
from llm.advisor_transition_preview import fingerprint_transition_preview_state


SCHEMA_VERSION = "detached-end-of-turn-post-action-branch-authority-v1"
_SIDES = ("self", "opponent")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")


def materialize_detached_end_of_turn_post_action_branch_authority(
    *, eot_ledger: Mapping[str, Any], source_eot_fingerprint: str,
) -> dict[str, Any]:
    """Project one validated EOT ledger into the existing post-EOT branch seam.

    This owner transports resolved EOT state only.  It does not select an
    incoming Pokemon, execute entry mechanics, or infer omitted state.
    """
    if not isinstance(eot_ledger, Mapping) or not isinstance(source_eot_fingerprint, str):
        return _result("rejected", "end_of_turn_ledger_or_fingerprint_invalid")
    if fingerprint_transition_preview_state(eot_ledger) != source_eot_fingerprint:
        return _result("rejected", "stale_or_foreign_end_of_turn_ledger")
    ledger = validate_end_of_turn_residual_phase_ledger(ledger=eot_ledger)
    if ledger.get("status") != "evaluable":
        return _result(ledger.get("status", "rejected"), ledger.get("reason", "invalid_end_of_turn_residual_ledger"))
    try:
        state = _post_action_state(ledger)
    except _Incomplete as error:
        return _result("incomplete", error.reason)
    except _Rejected as error:
        return _result("rejected", error.reason)
    state_fingerprint = fingerprint_transition_preview_state(state)
    if state_fingerprint is None:
        return _result("rejected", "post_eot_branch_state_unserializable")
    return {
        "status": "known",
        "schema_version": SCHEMA_VERSION,
        "source_binding": post_eot_source_binding(ledger),
        "source_eot_fingerprint": source_eot_fingerprint,
        "state": state,
        "state_fingerprint": state_fingerprint,
        "provenance": "strict_detached_exact_eot_to_post_action_branch_v1",
    }


def _post_action_state(ledger: Mapping[str, Any]) -> dict[str, Any]:
    phase = ledger.get("phase_input")
    final = ledger.get("post_end_of_turn_active_states")
    if not isinstance(phase, Mapping) or not isinstance(final, Mapping):
        raise _Rejected("end_of_turn_post_action_source_missing")
    session = ledger.get("session_id")
    if not isinstance(session, str) or not session:
        raise _Rejected("end_of_turn_post_action_session_invalid")

    active: dict[str, dict[str, Any]] = {}
    hp_rows, condition_rows = [], []
    conditions, items, toxic = {}, {}, {}
    for side in _SIDES:
        source = phase.get("active_states", {}).get(side) if isinstance(phase.get("active_states"), Mapping) else None
        resolved = final.get(side)
        row = _active_row(source, resolved, session=session, side=side)
        active[side] = row["active"]
        hp_rows.append(row["hp"])
        condition_rows.append(row["condition"])
        conditions[side] = row["condition_authority"]
        items[side] = row["item"]
        toxic[side] = {"owner": deepcopy(row["owner"]), "authority": row["toxic_progression"]}

    weather = phase.get("weather_authority")
    field = _field(weather, ledger)
    hazards = _switch_hazard_authorities(phase, ledger)
    return {
        "schema_version": "deterministic-transition-preview-v1",
        "active": active,
        "current_state": {
            "current_state_session_id": session,
            "current_hp_context": {"current_hp": hp_rows},
            "condition_context": {"current_conditions": condition_rows},
            "field_state_context": {"current_field": field},
        },
        # These retain the ledger's exact item and toxic authorities without
        # inventing a committed runtime observation or a generic item state.
        "post_eot_active_condition_authorities": conditions,
        "post_eot_active_item_authorities": items,
        "post_eot_toxic_progression": toxic,
        **({"post_eot_hazard_authorities": hazards} if hazards is not None else {}),
    }


def _switch_hazard_authorities(phase: Mapping[str, Any], ledger: Mapping[str, Any]) -> dict[str, Any] | None:
    """Project canonical hazard contexts only from validated exact phase input."""
    values = phase.get("switch_hazard_authorities")
    if values is None:
        return None
    if not isinstance(values, Mapping) or set(values) != set(_SIDES):
        raise _Rejected("end_of_turn_post_action_switch_hazard_authority_invalid")
    result: dict[str, Any] = {}
    for side in _SIDES:
        row = values[side]
        if not isinstance(row, Mapping) or row.get("status") == "unknown":
            raise _Incomplete("end_of_turn_post_action_switch_hazard_unknown")
        if row.get("status") != "resolved" or row.get("path_outcome") not in {"no_hazard_change", "path_local_hazard_result"}:
            raise _Rejected("end_of_turn_post_action_switch_hazard_authority_invalid")
        expected = {"session_id": ledger.get("session_id"), "pair_id": ledger.get("pair_id"), "source_runtime_fingerprint": ledger.get("source_runtime_fingerprint"), "source_branch_fingerprint": ledger.get("source_branch_fingerprint"), "decision_owner": ledger.get("decision_owner"), "terminal_leaf_id": ledger.get("terminal_leaf_id"), "affected_side": side}
        if row.get("source_binding") != expected:
            raise _Rejected("end_of_turn_post_action_switch_hazard_binding_invalid")
        hazards = row.get("hazards")
        if not _canonical_hazards(hazards, session=ledger.get("session_id"), side=side):
            raise _Rejected("end_of_turn_post_action_switch_hazard_context_invalid")
        result[side] = deepcopy(dict(hazards))
    return result


def _canonical_hazards(value: Any, *, session: Any, side: str) -> bool:
    return isinstance(value, Mapping) and set(value) == {"schema_version", "session_id", "affected_side", "stealth_rock", "spikes_layers", "toxic_spikes_layers", "sticky_web"} and value.get("schema_version") == "switch-hazard-context-v2" and value.get("session_id") == session and value.get("affected_side") == side and value.get("stealth_rock") in {"present", "absent"} and value.get("sticky_web") in {"present", "absent"} and value.get("spikes_layers") in {0, 1, 2, 3} and not isinstance(value.get("spikes_layers"), bool) and value.get("toxic_spikes_layers") in {0, 1, 2} and not isinstance(value.get("toxic_spikes_layers"), bool)


def _active_row(source: Any, resolved: Any, *, session: str, side: str) -> dict[str, Any]:
    if not isinstance(source, Mapping) or not isinstance(resolved, Mapping):
        raise _Rejected("end_of_turn_post_action_active_state_missing")
    owner = source.get("owner")
    if not _owner(owner, session=session, side=side) or resolved.get("owner") != owner:
        raise _Rejected("end_of_turn_post_action_owner_mismatch")
    hp, fainted = resolved.get("current_hp"), resolved.get("fainted")
    maximum = resolved.get("maximum_hp")
    if not _integer(hp) or not _integer(maximum) or maximum <= 0 or not 0 <= hp <= maximum or fainted is not (hp == 0):
        raise _Rejected("end_of_turn_post_action_hp_faint_continuity_invalid")
    source_hp = source.get("hp")
    if not isinstance(source_hp, Mapping) or source_hp.get("maximum_hp") != maximum:
        raise _Rejected("end_of_turn_post_action_max_hp_mismatch")
    condition_authority = _condition_authority(source.get("condition"), owner)
    condition = _condition_row(condition_authority, owner)
    item = _item(source.get("item"), owner)
    toxic = resolved.get("toxic_progression")
    if not isinstance(toxic, Mapping):
        raise _Rejected("end_of_turn_post_action_toxic_authority_missing")
    return {
        "owner": deepcopy(dict(owner)),
        "active": {**deepcopy(dict(owner)), "current_hp": hp, "max_hp": maximum, "fainted": fainted},
        "hp": {"side": side, "current_hp": hp, "maximum_hp": maximum, "status": "predicted", "source": "detached_exact_end_of_turn_post_action_branch"},
        "condition": condition,
        "condition_authority": condition_authority,
        "item": item,
        "toxic_progression": deepcopy(dict(toxic)),
    }


def _condition_authority(value: Any, owner: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("status") not in {"known_none", "known_present"}:
        raise _Incomplete("end_of_turn_post_action_condition_unknown")
    if value.get("status") == "known_present" and (not isinstance(value.get("condition"), str) or not value["condition"]):
        raise _Rejected("end_of_turn_post_action_condition_invalid")
    return {"owner": deepcopy(dict(owner)), "authority": deepcopy(dict(value))}


def _condition_row(value: Mapping[str, Any], owner: Mapping[str, Any]) -> dict[str, Any]:
    authority = value["authority"]
    kind = "none" if authority["status"] == "known_none" else authority["condition"]
    return {"side": owner["side"], "condition_type": kind, "status": "predicted", "source": "detached_exact_end_of_turn_post_action_branch"}


def _item(value: Any, owner: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "known_absent"}:
        raise _Incomplete("end_of_turn_post_action_item_unknown")
    if value["status"] == "known" and (not isinstance(value.get("value"), str) or not value["value"]):
        raise _Rejected("end_of_turn_post_action_item_invalid")
    return {"owner": deepcopy(dict(owner)), "authority": deepcopy(dict(value))}


def _field(value: Any, ledger: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("status") not in {"known", "unknown"}:
        raise _Rejected("end_of_turn_post_action_weather_authority_invalid")
    if value["status"] == "unknown":
        return {}
    expected = {
        "session_id": ledger.get("session_id"),
        "source_runtime_fingerprint": ledger.get("source_runtime_fingerprint"),
        "source_branch_fingerprint": ledger.get("source_branch_fingerprint"),
    }
    if value.get("source_binding") != expected or not isinstance(value.get("weather"), str):
        raise _Rejected("end_of_turn_post_action_weather_binding_invalid")
    return {"weather": value["weather"]}


def _owner(value: Any, *, session: str, side: str) -> bool:
    return isinstance(value, Mapping) and set(value) == set(_OWNER_KEYS) and value.get("session_id") == session and value.get("side") == side and _integer(value.get("slot_index")) and value["slot_index"] >= 0 and isinstance(value.get("pokemon_id"), str) and bool(value["pokemon_id"])


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _result(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}


class _Incomplete(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class _Rejected(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason

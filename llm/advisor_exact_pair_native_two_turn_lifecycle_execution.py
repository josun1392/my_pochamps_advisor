"""Strict two-turn execution over real exact immediate-pair terminal ledgers."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from llm.advisor_exact_eot_post_action_lifecycle_coordinator import coordinate_exact_eot_post_action_lifecycle
from llm.advisor_post_eot_replacement_transition import validate_post_eot_transition
from llm.advisor_transition_preview import fingerprint_transition_preview_state as fingerprint


SCHEMA_VERSION = "exact-pair-native-two-turn-lifecycle-execution-v1"
_SIDES = ("self", "opponent")
_OWNER_KEYS = ("session_id", "side", "slot_index", "pokemon_id")
_TURN_KEYS = ("terminal_ledger", "terminal_leaf_id", "terminal_active_authorities", "team_authorities", "weather_authority", "leech_seed_transfers", "switch_hazard_authorities")


def execute_exact_pair_native_two_turn_lifecycle(*, turn_one: Mapping[str, Any], turn_two: Mapping[str, Any] | None, completed_replacement_transition: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Advance exactly two pair terminals without a legacy EOT fallback."""
    first = _coordinate_turn(turn_one)
    if first.get("status") not in {"next_decision_ready", "replacement_required", "battle_terminal"}:
        return _halt(first, "turn_one_exact_lifecycle", turn_one_lifecycle=first)
    if first["status"] == "battle_terminal":
        return _result("battle_terminal", turn_one_lifecycle=first, final_status="battle_terminal")
    boundary = _next_boundary(first, completed_replacement_transition)
    if boundary.get("status") == "battle_terminal":
        return _result("battle_terminal", turn_one_lifecycle=first, next_turn_boundary=boundary, final_status="battle_terminal")
    if boundary.get("status") != "resolved":
        return _halt(boundary, "turn_one_next_decision_boundary", turn_one_lifecycle=first)
    if not isinstance(turn_two, Mapping):
        return _halt(_error("incomplete", "turn_two_exact_pair_required"), "turn_two_exact_pair", turn_one_lifecycle=first, next_turn_boundary=boundary)
    reason = _validate_turn_two_source(turn_two, boundary)
    if reason is not None:
        return _halt(_error("rejected", reason), "turn_two_source_binding", turn_one_lifecycle=first, next_turn_boundary=boundary)
    second = _coordinate_turn(turn_two)
    if second.get("status") not in {"next_decision_ready", "replacement_required", "battle_terminal"}:
        return _halt(second, "turn_two_exact_lifecycle", turn_one_lifecycle=first, next_turn_boundary=boundary, turn_two_lifecycle=second)
    return _result(second["status"], turn_one_lifecycle=first, next_turn_boundary=boundary, turn_two_lifecycle=second, final_status=second["status"])


def _coordinate_turn(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or any(key not in value for key in _TURN_KEYS):
        return _error("rejected", "exact_turn_input_malformed")
    if not isinstance(value.get("leech_seed_transfers"), tuple) or not isinstance(value.get("switch_hazard_authorities"), Mapping):
        return _error("rejected", "exact_turn_terminal_authority_malformed")
    return coordinate_exact_eot_post_action_lifecycle(
        terminal_ledger=value["terminal_ledger"], terminal_leaf_id=value["terminal_leaf_id"],
        terminal_active_authorities=value["terminal_active_authorities"], team_authorities=value["team_authorities"],
        weather_authority=value["weather_authority"], leech_seed_transfers=value["leech_seed_transfers"],
        switch_hazard_authorities=value["switch_hazard_authorities"],
    )


def _next_boundary(first: Mapping[str, Any], completed: Mapping[str, Any] | None) -> dict[str, Any]:
    initial = first.get("post_eot_transition")
    if not isinstance(initial, Mapping) or validate_post_eot_transition(transition=initial).get("status") != "valid":
        return _error("rejected", "turn_one_post_eot_transition_invalid")
    if first.get("status") == "next_decision_ready":
        return _resolved_boundary(initial, None)
    if not isinstance(completed, Mapping):
        return _error("incomplete", "replacement_completion_required")
    if validate_post_eot_transition(transition=completed).get("status") != "valid":
        return _error("rejected", "replacement_completion_invalid")
    if completed.get("source") != initial.get("source"):
        return _error("rejected", "replacement_completion_source_invalid")
    if completed.get("status") == "battle_terminal":
        return _error("battle_terminal", "replacement_completion_battle_terminal")
    if completed.get("status") != "next_decision_ready":
        return _error("incomplete", "replacement_completion_not_ready")
    return _resolved_boundary(completed, completed)


def _resolved_boundary(transition: Mapping[str, Any], replacement: Mapping[str, Any] | None) -> dict[str, Any]:
    state, next_fingerprint = transition.get("detached_next_decision_state"), transition.get("next_decision_fingerprint")
    owners = _owners(state)
    if not isinstance(state, Mapping) or not isinstance(next_fingerprint, str) or fingerprint(state) != next_fingerprint or owners is None:
        return _error("rejected", "next_decision_state_invalid")
    return {"status": "resolved", "detached_next_decision_state": deepcopy(dict(state)), "next_decision_fingerprint": next_fingerprint, "active_owners": owners, "post_eot_transition": deepcopy(dict(transition)), **({"completed_replacement_transition": deepcopy(dict(replacement))} if replacement is not None else {})}


def _validate_turn_two_source(turn: Mapping[str, Any], boundary: Mapping[str, Any]) -> str | None:
    state, expected_fingerprint = turn.get("next_decision_state"), turn.get("next_decision_fingerprint")
    if not isinstance(state, Mapping) or not isinstance(expected_fingerprint, str) or fingerprint(state) != expected_fingerprint:
        return "turn_two_next_decision_authority_invalid"
    if state != boundary["detached_next_decision_state"] or expected_fingerprint != boundary["next_decision_fingerprint"]:
        return "turn_two_next_decision_binding_invalid"
    ledger, owners = turn.get("terminal_ledger"), boundary["active_owners"]
    if not isinstance(ledger, Mapping) or ledger.get("source_branch_fingerprint") != expected_fingerprint:
        return "turn_two_pair_branch_binding_invalid"
    if ledger.get("session_id") != owners["self"]["session_id"] or ledger.get("own_actor") != owners["self"] or ledger.get("opponent_actor") != owners["opponent"] or ledger.get("decision_owner") != owners["self"]:
        return "turn_two_pair_owner_binding_invalid"
    return None


def _owners(state: Any) -> dict[str, dict[str, Any]] | None:
    active = state.get("active") if isinstance(state, Mapping) else None
    if not isinstance(active, Mapping): return None
    owners: dict[str, dict[str, Any]] = {}
    for side in _SIDES:
        row = active.get(side)
        owner = {key: row.get(key) for key in _OWNER_KEYS} if isinstance(row, Mapping) else None
        if not isinstance(owner, Mapping) or owner["side"] != side or not isinstance(owner["session_id"], str) or not owner["session_id"] or not isinstance(owner["slot_index"], int) or isinstance(owner["slot_index"], bool) or not isinstance(owner["pokemon_id"], str) or not owner["pokemon_id"]:
            return None
        owners[side] = owner
    return owners if owners["self"]["session_id"] == owners["opponent"]["session_id"] else None


def _result(status: str, **values: Any) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, **{key: deepcopy(value) for key, value in values.items()}, "provenance": "strict_exact_pair_native_two_turn_lifecycle_v1"}


def _error(status: str, reason: str) -> dict[str, Any]:
    return {"status": status, "schema_version": SCHEMA_VERSION, "reason": reason}


def _halt(result: Mapping[str, Any], stage: str, **values: Any) -> dict[str, Any]:
    return _result(result.get("status", "rejected"), reason=result.get("reason", stage), failed_stage=stage, **values)

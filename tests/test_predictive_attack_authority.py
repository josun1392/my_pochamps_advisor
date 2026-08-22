from copy import deepcopy

from llm.advisor_predictive_attack_authority import build_predictive_fixed_damage_attack_authority
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _owner, _state


def _input(state, *, move="seismic-toss", types=("water",), level=50):
    owner, target = _owner(state, "self"), _owner(state, "opponent")
    return {"schema_version": "current-predictive-fixed-damage-input-v1", "provenance": "trusted_current_predictive_fixed_damage_input_v1", "session_id": owner["session_id"], "source_branch_fingerprint": fingerprint_transition_preview_state(state), "decision_owner": owner, "attacker": owner, "target": target, "move_id": move, "attacker_level_authority": {"status": "known", "value": level}, "target_type_authority": {"status": "known", "value": list(types)}}


def _tracked_substitute(state, *, status="known_inactive", hp=None):
    owners = [_owner(state, side) for side in ("self", "opponent")]
    state["substitute_state_context"] = {"schema_version": "detached-substitute-state-v1", "states": [{"owner": owners[0], "state": "known_inactive", "substitute_hp": None}, {"owner": owners[1], "state": status, "substitute_hp": hp}]}


def test_seismic_toss_is_exact_current_authority_not_an_observed_result():
    state, _ = _state(); _tracked_substitute(state)
    result = build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=_owner(state, "self"), target_owner=_owner(state, "opponent"), move_id="seismic-toss", predictive_input=_input(state))
    assert result["schema_version"] == "deterministic-predictive-attack-authority-v1"
    assert result["completeness"] == "exact_complete" and result["predicted_result"] == {"damage": 50, "damage_route": "target", "target_hp_before": 100, "target_hp_after": 50, "target_fainted": False}
    assert "observed" not in result["provenance"] and state["active"]["opponent"]["current_hp"] == 100


def test_predictive_authority_rejects_stale_foreign_and_historical_inputs():
    state, _ = _state(); _tracked_substitute(state); owner, target = _owner(state, "self"), _owner(state, "opponent")
    stale = _input(state); stale["source_branch_fingerprint"] = "stale"
    assert build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=stale)["status"] == "rejected"
    foreign = _input(state); foreign["attacker"] = target
    assert build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=foreign)["status"] == "rejected"
    historical = {"schema_version": "observed-direct-damage-result-v1", "source_branch_fingerprint": fingerprint_transition_preview_state(state)}
    assert build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=historical)["status"] == "rejected"


def test_missing_current_inputs_and_unknown_substitute_remain_incomplete():
    state, _ = _state(); owner, target = _owner(state, "self"), _owner(state, "opponent")
    assert build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=_input(state))["reason"] == "substitute_state_unknown"
    _tracked_substitute(state); broken = _input(state); broken["attacker_level_authority"] = {"status": "unknown"}
    assert build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=broken)["status"] == "rejected"


def test_type_immunity_and_known_substitute_route_are_exact_and_detached():
    state, _ = _state(); owner, target = _owner(state, "self"), _owner(state, "opponent"); _tracked_substitute(state, status="known_active", hp=40)
    result = build_predictive_fixed_damage_attack_authority(branch_state=state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=_input(state))
    assert result["predicted_result"]["damage_route"] == "substitute" and result["predicted_result"]["substitute_hp_after"] == 0
    immune_state = deepcopy(state); _tracked_substitute(immune_state)
    immune = build_predictive_fixed_damage_attack_authority(branch_state=immune_state, decision_owner=owner, target_owner=target, move_id="seismic-toss", predictive_input=_input(immune_state, types=("ghost",)))
    assert immune["predicted_result"]["damage"] == 0 and immune["predicted_result"]["target_fainted"] is False

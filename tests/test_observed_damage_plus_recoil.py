"""Brave Bird trusted damage-plus-recoil stays a bounded F0→F1→F2 composition."""
from copy import deepcopy

from llm.advisor_observed_damage_plus_recoil import materialize_observed_brave_bird_recoil
from llm.advisor_transition_preview import fingerprint_transition_preview_state
from tests.test_forced_switch_execution import _owner, _state


def _result(state, *, user_side="self", target_side="opponent", damage=20, recoil=10, recoil_result="applied", **changes):
    user, target = _owner(state, user_side), _owner(state, target_side)
    value = {"schema_version": "observed-damage-plus-recoil-result-v1", "session_id": user["session_id"], "source_branch_fingerprint": fingerprint_transition_preview_state(state), "user": user, "target_owner": target, "move_id": "brave-bird", "damage_amount": damage, "damaging_hit_result": "applied", "recoil_result": recoil_result, "recoil_amount": recoil if recoil_result == "applied" else None, "provenance": "trusted_observed_damage_plus_recoil_result_v1"}
    value.update(changes); return value


def _materialize(state, result=None):
    return materialize_observed_brave_bird_recoil(branch_state=state, source_branch_fingerprint=fingerprint_transition_preview_state(state), observed_result=_result(state) if result is None else result)


def test_brave_bird_side_neutral_f0_f1_f2_is_pure_and_exact():
    state, _ = _state(); before = deepcopy(state)
    first, repeated = _materialize(state), _materialize(state)
    assert first == repeated and state == before
    assert first["f1_branch_fingerprint"] != first["resulting_branch_fingerprint"]
    assert first["next_state"]["active"]["opponent"]["current_hp"] == 80
    assert first["next_state"]["active"]["self"]["current_hp"] == 80
    opposite = _materialize(state, _result(state, user_side="opponent", target_side="self"))
    assert opposite["next_state"]["active"]["self"]["current_hp"] == 70 and opposite["next_state"]["active"]["opponent"]["current_hp"] == 90


def test_brave_bird_target_ko_recoil_ko_and_double_ko_are_represented():
    state, _ = _state()
    target_ko = _materialize(state, _result(state, damage=100, recoil=10))
    assert target_ko["next_state"]["active"]["opponent"]["fainted"] is True and target_ko["next_state"]["active"]["self"]["fainted"] is False
    recoil_ko_state, _ = _state(); recoil_ko_state["active"]["self"]["current_hp"] = 10
    recoil_ko = _materialize(recoil_ko_state)
    assert recoil_ko["next_state"]["active"]["self"]["fainted"] is True and recoil_ko["next_state"]["active"]["opponent"]["fainted"] is False
    double_state, _ = _state(); double_state["active"]["self"]["current_hp"] = 10
    double_ko = _materialize(double_state, _result(double_state, damage=100, recoil=10))
    assert all(double_ko["next_state"]["active"][side]["fainted"] for side in ("self", "opponent"))


def test_brave_bird_replay_and_invalid_authority_fail_closed_without_partial_f2():
    state, _ = _state(); observation = _result(state); result = _materialize(state, observation)
    assert materialize_observed_brave_bird_recoil(branch_state=result["next_state"], source_branch_fingerprint=result["resulting_branch_fingerprint"], observed_result=observation)["status"] == "rejected"
    cases = [{**observation, "move_id": "double-edge"}, {**observation, "damaging_hit_result": "failed"}, {**observation, "recoil_result": "unknown"}, {**observation, "recoil_amount": 0}, {**observation, "source_branch_fingerprint": "stale"}, {**observation, "provenance": "ui_text"}, {**observation, "user": _owner(state, "opponent")}]
    for case in cases: assert _materialize(state, case)["status"] == "rejected"
    malformed, _ = _state(); malformed["active"]["self"]["current_hp"] = None
    assert _materialize(malformed) == {"status": "rejected", "reason": "invalid_observed_recoil_authority"}
    target_bad, _ = _state(); target_bad["active"]["opponent"]["current_hp"] = None
    assert _materialize(target_bad)["status"] == "rejected"


def test_exact_not_applied_recoil_stops_coherently_at_f1():
    state, _ = _state(); result = _materialize(state, _result(state, recoil_result="not_applied"))
    assert result["status"] == "resolved" and result["recoil"] == "not_applied"
    assert result["next_state"]["active"]["opponent"]["current_hp"] == 80 and result["next_state"]["active"]["self"]["current_hp"] == 90

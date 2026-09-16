from copy import deepcopy

from llm.advisor_champions_sleep_application import materialize_champions_rest
from llm.advisor_detached_drain_consequence import apply_detached_drain_consequence
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_direct_heal_execution_authority import freeze_runtime_d0_direct_heal_execution_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from tests.test_detached_opponent_response_profile import _owner, _snapshot, _state


def _metadata(d0, actor, action_id, metadata):
    return {"status":"resolved", "move_id":metadata["move_id"], "metadata":metadata, "candidate_id":action_id,
            "active_attacker":actor, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"],
            "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"]}


def _order(d0, own, opponent):
    return {"status":"resolved", "schema_version":"runtime-d0-action-order-authority-v1", "order":"own_first", "order_engine":{"status":"own_faster"}, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "own_action_id":own["action_id"], "opponent_action_id":opponent["action_id"], "own_actor":d0["active_owners"]["self"], "opponent_actor":d0["active_owners"]["opponent"]}


def _pair(second_move):
    state = _state()
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=200, max_hp=301, fainted=False)
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state, "self"))
    actor, target = d0["active_owners"]["self"], d0["active_owners"]["opponent"]
    psychic = {"move_id":"psychic-noise", "category":"special", "power":75, "type":"psychic", "accuracy":90, "priority":0, "target":"selected-pokemon"}
    recovery = {"move_id":second_move, "category":"status", "target":"self", "priority":0, "accuracy":None, "power":None}
    own = {"action_id":"attack:psychic-noise", "action_type":"attack", "identity":"psychic-noise"}
    own["move_metadata_authority"] = _metadata(d0, actor, own["action_id"], psychic)
    opponent = {"status":"resolved", "action_id":f"opponent_attack:{second_move}", "action_type":"attack", "move_id":second_move, "identity":second_move, "session_id":d0["session_id"], "source_runtime_fingerprint":d0["source_runtime_fingerprint"], "source_branch_fingerprint":d0["strategy_preview_fingerprint"], "decision_owner":d0["decision_owner"], "usability":{"status":"known_usable"}, "selectability":"selectable"}
    opponent["metadata_authority"] = _metadata(d0, target, opponent["action_id"], recovery)
    direct = {} if second_move == "rest" else {opponent["action_id"]: freeze_runtime_d0_direct_heal_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=opponent, actor=target)}
    rest = {} if second_move != "rest" else {opponent["action_id"]: materialize_champions_rest(strategy_d0=d0, runtime_snapshot=snapshot, actor=target, action=opponent)}
    return snapshot, d0, own, opponent, materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own, opponent_action=opponent, action_order_authority=_order(d0, own, opponent), direct_heal_execution_authorities=direct, rest_execution_authorities=rest)


def test_psychic_noise_terminal_hit_prevents_recover_in_the_same_pair():
    snapshot, _d0, _own, _opponent, pair = _pair("recover")
    assert pair["status"] == "evaluable", pair
    hit = [row for row in pair["terminal_branches"] if row["first_action_leaf"]["hit_state"] == "hit"]
    assert hit and all(row["second_action"]["leaf"]["consequences"]["direct_heal"]["actual_heal"] == 0 for row in hit)
    miss = [row for row in pair["terminal_branches"] if row["first_action_leaf"]["hit_state"] != "hit"]
    assert miss and all(row["second_action"]["leaf"]["consequences"]["direct_heal"]["actual_heal"] > 0 for row in miss)
    assert snapshot["state"]["opponent_side"]["pokemon"][0]["healing_prevented_status"] != "active"


def test_psychic_noise_terminal_hit_prevents_rest_in_the_same_pair():
    _snapshot_value, _d0, _own, _opponent, pair = _pair("rest")
    assert pair["status"] == "evaluable", pair
    hit = [row for row in pair["terminal_branches"] if row["first_action_leaf"]["hit_state"] == "hit"]
    assert hit and all(row["second_action"]["leaf"]["consequences"]["rest_application"]["outcome"] == "healing_prevented" for row in hit)


def test_drain_consumes_exact_path_local_active_prevention_without_losing_damage():
    state = _state(); state["self_side"]["pokemon"][0].update(current_hp=100, max_hp=200, fainted=False, healing_prevented_status="active", healing_prevented_status_provenance={"event_kind":"current_healing_prevented_observed", "trust":"user_confirmed_observation", "status":"active", "turn_number":1, "source_observation_id":"detached:leaf:psychic-noise", "source_sequence":1})
    snapshot = {"status":"runtime_snapshot_ready", "session_id":state["session_id"], "state":state, "state_fingerprint":state_fingerprint(state)}
    leaf = {"hit_state":"hit", "consequences":{"own_final_hp":100, "source_hit_context":{"target_routing":"target", "target_pre_hp":100, "target_post_hp":80, "actual_damage":20}}}
    result = apply_detached_drain_consequence(runtime_snapshot=snapshot, attacker=_owner(state,"self"), target=_owner(state,"opponent"), move_metadata={"move_id":"giga-drain", "category":"special"}, leaf=leaf)
    assert result["status"] == "resolved"
    assert result["leaf"]["consequences"]["own_final_hp"] == 100
    assert result["leaf"]["consequences"]["drain"]["actual_target_hp_loss"] == 20
    assert result["leaf"]["consequences"]["drain"]["healing_prevented"] is True


def test_drain_unknown_is_not_rewritten_as_active_and_invalid_active_fails_closed():
    state = _state(); state["self_side"]["pokemon"][0].update(current_hp=100, max_hp=200, fainted=False)
    snapshot = {"status":"runtime_snapshot_ready", "session_id":state["session_id"], "state":state, "state_fingerprint":state_fingerprint(state)}
    leaf = {"hit_state":"hit", "consequences":{"own_final_hp":100, "source_hit_context":{"target_routing":"target", "target_pre_hp":100, "target_post_hp":80, "actual_damage":20}}}
    normal = apply_detached_drain_consequence(runtime_snapshot=snapshot, attacker=_owner(state,"self"), target=_owner(state,"opponent"), move_metadata={"move_id":"giga-drain", "category":"special"}, leaf=leaf)
    assert normal["status"] == "resolved" and normal["leaf"]["consequences"]["own_final_hp"] > 100
    invalid = deepcopy(snapshot); invalid["state"]["self_side"]["pokemon"][0]["healing_prevented_status"] = "active"; invalid["state"]["self_side"]["pokemon"][0]["healing_prevented_status_provenance"] = {"event_kind":"foreign"}
    assert apply_detached_drain_consequence(runtime_snapshot=invalid, attacker=_owner(state,"self"), target=_owner(state,"opponent"), move_metadata={"move_id":"giga-drain", "category":"special"}, leaf=leaf)["status"] == "incomplete"

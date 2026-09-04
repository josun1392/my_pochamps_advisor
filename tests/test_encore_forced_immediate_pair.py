from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_exact_immediate_action_pair_outcome_ledger import normalize_exact_immediate_action_pair_outcome_ledger
from copy import deepcopy
from tests.test_taunt_action_restriction import _taunt_inputs


def test_faster_encore_replaces_only_pending_selected_action_with_locked_priority(monkeypatch):
    snapshot, d0, own, foe, own_action, opponent, order, _, pure = _taunt_inputs(category="physical")
    own_action = {**own_action, "action_id": "attack:encore", "identity": "encore", "move_metadata_authority": {**own_action["move_metadata_authority"], "candidate_id": "attack:encore", "move_id": "encore", "metadata": {"move_id": "encore", "category": "status", "type": "normal", "accuracy": 100, "priority": 0}}}
    order = {**order, "own_action_id": "attack:encore"}
    application = {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "actor": own, "target": foe, "action_id": "attack:encore", "move_id": "encore", "outcome": "applicable", "locked_move_id": "quick-attack", "locked_move_metadata": {"move_id": "quick-attack", "category": "physical", "priority": 1}, "last_used_execution_id": "used-b"}
    def ledger(**kwargs):
        action = kwargs.get("action") or {}; move = action.get("identity", kwargs["metadata_authority"].get("metadata", {}).get("move_id"))
        leaf = {"leaf_id": f"{move}:hit", "candidate_id": action.get("action_id", move), "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit", "critical_state": "non_critical", "damage_roll": {"damage": 10}, "consequences": {"damage": 10, "own_final_hp": 100, "target_final_hp": 90, "target_ko": False, "self_fainted": False, "secondary": None, "contact": "not_applicable"}, "provenance": {"attacker": kwargs["actor"], "target": kwargs["target"], "move_id": move}}
        return {"status": "evaluable", "terminal_leaves": (leaf,)}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", ledger)
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent, action_order_authority=order, encore_application_authorities={"attack:encore": application}, pure_status_execution_authorities=pure)
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    forced = pair["terminal_branches"][0]["second_action"]["forced_execution_action"]
    assert forced["selected_move_id"] == "tackle" and forced["execution_move_id"] == "quick-attack" and forced["execution_priority"] == 1
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=pair)["status"] == "evaluable"
    forged = deepcopy(pair); forged["terminal_branches"] = tuple({**branch, "second_action": {**branch["second_action"], "forced_execution_action": {**branch["second_action"]["forced_execution_action"], "selected_action_id": "forged"}}} for branch in pair["terminal_branches"])
    assert normalize_exact_immediate_action_pair_outcome_ledger(pair=forged)["status"] == "rejected"


def test_slower_encore_does_not_retroactively_replace_executed_action(monkeypatch):
    snapshot, d0, own, foe, own_action, opponent, order, _, pure = _taunt_inputs(order="opponent_first", category="physical")
    own_action = {**own_action, "action_id": "attack:encore", "identity": "encore", "move_metadata_authority": {**own_action["move_metadata_authority"], "candidate_id": "attack:encore", "move_id": "encore", "metadata": {"move_id": "encore", "category": "status", "type": "normal", "accuracy": 100, "priority": 0}}}
    order = {**order, "own_action_id": "attack:encore"}
    app = {"status": "resolved", "session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"], "actor": own, "target": foe, "action_id": "attack:encore", "move_id": "encore", "outcome": "applicable", "locked_move_id": "quick-attack", "locked_move_metadata": {"move_id": "quick-attack", "category": "physical", "priority": 1}, "last_used_execution_id": "used-b"}
    monkeypatch.setattr("llm.advisor_immediate_move_vs_move_action_pair._attack_ledger", lambda **kwargs: {"status": "evaluable", "terminal_leaves": ({"leaf_id": "tackle:hit", "candidate_id": "opponent_attack:tackle", "probability": {"numerator": 1, "denominator": 1}, "hit_state": "hit", "critical_state": "non_critical", "damage_roll": {"damage": 10}, "consequences": {"damage": 10, "own_final_hp": 100, "target_final_hp": 90, "target_ko": False, "self_fainted": False, "secondary": None, "contact": "not_applicable"}, "provenance": {"attacker": kwargs["actor"], "target": kwargs["target"], "move_id": "tackle"}},)})
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent, action_order_authority=order, encore_application_authorities={"attack:encore": app}, pure_status_execution_authorities=pure)
    assert pair["status"] == "evaluable" and pair["terminal_branches"][0]["first_action_leaf"]["candidate_id"] == "opponent_attack:tackle"

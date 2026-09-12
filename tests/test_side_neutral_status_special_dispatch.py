from copy import deepcopy

import pytest

from llm.advisor_detached_taunt_action_restriction import materialize_detached_taunt_application
from llm.advisor_immediate_move_vs_move_action_pair import materialize_immediate_move_vs_move_action_pair
from llm.advisor_runtime_d0_pure_status_action_execution_authority import freeze_runtime_d0_pure_status_action_execution_authority
from tests.test_taunt_action_restriction import _taunt_inputs


def _opponent_special(move_id: str, own_action, foe, own, bindings):
    types = {"taunt": "dark", "encore": "normal", "disable": "normal", "trick": "psychic", "switcheroo": "dark"}
    metadata = {"move_id": move_id, "category": "status", "type": types[move_id], "accuracy": 100, "priority": 0, "target": "selected-pokemon", "contact": False}
    return {"status": "resolved", "action_id": f"opponent_attack:{move_id}", "action_type": "attack", "move_id": move_id, "identity": move_id, "opponent_actor": foe, "target_owner": own, **bindings, "metadata_authority": {"status": "resolved", "move_id": move_id, "metadata": metadata}, "usability": {"status": "known_usable"}, "selectability": "selectable"}


def _mirror_inputs(move_id: str, order: str = "opponent_first"):
    snapshot, d0, own, foe, _, tail, _, _, _ = _taunt_inputs(category="status")
    bindings = {"session_id": d0["session_id"], "source_runtime_fingerprint": d0["source_runtime_fingerprint"], "source_branch_fingerprint": d0["strategy_preview_fingerprint"], "decision_owner": d0["decision_owner"]}
    own_metadata = {**tail["metadata_authority"], "candidate_id": tail["action_id"], "active_attacker": own, **bindings}
    own_action = {"action_id": tail["action_id"], "action_type": "attack", "identity": "tail-whip", "move_metadata_authority": own_metadata}
    opponent = _opponent_special(move_id, own_action, foe, own, bindings)
    order_auth = {"status": "resolved", "schema_version": "runtime-d0-action-order-authority-v1", "order": order, **bindings, "own_action_id": own_action["action_id"], "opponent_action_id": opponent["action_id"], "own_actor": own, "opponent_actor": foe}
    accuracy = {"status": "resolved", **bindings, "actor": own, "target": foe, "action_id": own_action["action_id"], "move_id": "tail-whip", "outcome": "hit"}
    pure = freeze_runtime_d0_pure_status_action_execution_authority(strategy_d0=d0, runtime_snapshot=snapshot, action=own_action, actor=own, target=foe, status_accuracy_authority=accuracy)
    return snapshot, d0, own, foe, own_action, opponent, order_auth, pure, bindings


def test_opponent_taunt_first_mirrors_own_taunt_and_blocks_pending_status():
    snapshot, d0, own, foe, own_action, opponent, order, pure, bindings = _mirror_inputs("taunt")
    base = {**bindings, "actor": foe, "target": own, "action_id": opponent["action_id"], "move_id": "taunt"}
    known = lambda **extra: {"status": "resolved", **base, **extra}
    app = materialize_detached_taunt_application(strategy_d0=d0, action=opponent, actor=foe, target=own, accuracy_authority=known(outcome="hit"), target_ability_authority=known(ability="pressure"), target_side_ability_authority=known(ability="pressure"), reflection_authority=known(outcome="not_applicable"))
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent, action_order_authority=order, pure_status_execution_authorities={own_action["action_id"]: pure}, taunt_application_authorities={opponent["action_id"]: app})
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}
    assert pair["terminal_branches"][0]["second_action"]["leaf"]["consequences"]["execution_failure"] == "taunt_action_restriction"


@pytest.mark.parametrize("move_id,field,outcome", [("encore", "encore_application_authorities", "failed"), ("disable", "disable_application_authorities", "applicable")])
def test_opponent_restriction_special_dispatches_from_the_opponent_action(move_id, field, outcome):
    snapshot, d0, own, foe, own_action, opponent, order, pure, bindings = _mirror_inputs(move_id)
    app = {"status": "resolved", **bindings, "actor": foe, "target": own, "action_id": opponent["action_id"], "move_id": move_id, "outcome": outcome}
    if move_id == "encore": app.update(locked_move_id="tackle", locked_move_metadata={"move_id": "tackle", "category": "physical", "priority": 0}, last_used_execution_id="used")
    else: app.update(disabled_move_id="tail-whip", last_used_execution_id="used")
    pair = materialize_immediate_move_vs_move_action_pair(strategy_d0=d0, runtime_snapshot=snapshot, own_action=own_action, opponent_action=opponent, action_order_authority=order, pure_status_execution_authorities={own_action["action_id"]: pure}, **{field: {opponent["action_id"]: app}})
    assert pair["status"] == "evaluable" and pair["terminal_probability_mass"] == {"numerator": 1, "denominator": 1}

from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_runtime_d0_pivot_replacement_authority import freeze_runtime_d0_pivot_replacement_authority


def _runtime(bench=1):
    state = create_unknown_bootstrap_battle_state("pivot-live", "self", "foe") ["state"]
    state["self_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    for slot in range(1, bench + 1):
        state["opponent_side"]["pokemon"][slot] = {**deepcopy(state["opponent_side"]["pokemon"][0]), "pokemon_id": f"foe-{slot}"}
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": state, "state_fingerprint": state_fingerprint(state)}


def _request(snapshot):
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": "pivot-live", "side": "self", "slot_index": 0, "pokemon_id": "self"})
    foe = d0["active_owners"]["opponent"]
    action = {"action_id": "opponent_attack:u-turn"}
    return d0, foe, action


def test_unique_opponent_pivot_replacement_is_actor_neutral_and_multiple_is_policy_incomplete():
    snapshot = _runtime(); d0, foe, action = _request(snapshot)
    resolved = freeze_runtime_d0_pivot_replacement_authority(strategy_d0=d0, runtime_snapshot=snapshot, pivot_actor=foe, pivot_action=action, move_metadata={"move_id": "u-turn"})
    assert resolved["status"] == "resolved"
    assert resolved["owner"]["side"] == "opponent"
    assert resolved["decision_owner"] == foe
    assert resolved["entry_authority"]["hazards"]["affected_side"] == "opponent"
    multi_snapshot = _runtime(bench=2); multi_d0, multi_foe, action = _request(multi_snapshot)
    multiple = freeze_runtime_d0_pivot_replacement_authority(strategy_d0=multi_d0, runtime_snapshot=multi_snapshot, pivot_actor=multi_foe, pivot_action=action, move_metadata={"move_id": "u-turn"})
    assert multiple["status"] == "incomplete"
    assert multiple["reason"] == "opponent_pivot_replacement_choice_policy_required"


def test_no_opponent_pivot_replacement_is_exact_no_pivot():
    snapshot = _runtime(bench=0); d0, foe, action = _request(snapshot)
    result = freeze_runtime_d0_pivot_replacement_authority(strategy_d0=d0, runtime_snapshot=snapshot, pivot_actor=foe, pivot_action={"action_id": "opponent_attack:volt-switch"}, move_metadata={"move_id": "volt-switch"})
    assert result["status"] == "known_none"

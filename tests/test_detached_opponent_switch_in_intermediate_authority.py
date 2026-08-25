from copy import deepcopy

from llm.advisor_current_opponent_switch_response_set_observation import admit_current_opponent_switch_response_set_observation
from llm.advisor_detached_opponent_switch_in_intermediate_authority import materialize_detached_opponent_switch_in_intermediate_authority
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_opponent_switch_response_authority import freeze_runtime_d0_opponent_switch_response_authority
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from llm.advisor_switch_hazard_authority import build_switch_hazard_context


def _manager(*, known_hp=True):
    state = create_unknown_bootstrap_battle_state("s", "self", "opponent")["state"]
    bench = deepcopy(state["opponent_side"]["pokemon"][0]); bench["pokemon_id"] = "bench"
    if known_hp:
        bench.update({"current_hp": 80, "max_hp": 100, "fainted": False})
    state["opponent_side"]["pokemon"][1] = bench
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="s", affected_side="opponent", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _inputs(manager):
    assert admit_current_opponent_switch_response_set_observation(runtime_session_manager=manager, captured_session_id="s", permission="permitted", targets=[{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}], turn_number=1)["status"] == "resolved"
    state = manager.read_state()["state"]
    snapshot = {"status": "runtime_snapshot_ready", "session_id": "s", "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner={"session_id": "s", "side": "self", "slot_index": 0, "pokemon_id": "self"})
    switch = freeze_runtime_d0_opponent_switch_response_authority(strategy_d0=d0, runtime_snapshot=snapshot)
    return d0, snapshot, switch


def test_selectable_opponent_target_materializes_detached_switch_in_with_exact_known_facts():
    manager = _manager(); d0, snapshot, switch = _inputs(manager)
    before = deepcopy(manager.read_state()["state"])
    result = materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="opponent_switch:s:1:bench")

    assert result["status"] == "resolved"
    hypothetical = result["hypothetical_switch_in_state"]
    assert hypothetical["hypothetical"] is True
    assert hypothetical["active_owner"]["pokemon_id"] == "bench"
    assert hypothetical["replaced_active_owner"]["pokemon_id"] == "opponent"
    assert hypothetical["hp_authority"]["current_hp"] == 80
    assert hypothetical["condition_authority"] == {"status": "unknown"}
    assert hypothetical["stage_authority"] == {"status": "unknown"}
    assert hypothetical["entry_consequence"] == {"status": "resolved", "damage": 0, "post_hp": 80, "hazard_ko": False, "effect": "known_absent_entry_hazards"}
    assert manager.read_state()["state"] == before


def test_unknown_target_hp_or_hazards_fail_closed_without_defaulting():
    manager = _manager(known_hp=False); d0, snapshot, switch = _inputs(manager)
    hp_unknown = materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="opponent_switch:s:1:bench")
    assert hp_unknown["status"] == "incomplete"

    manager = _manager(); d0, snapshot, switch = _inputs(manager)
    snapshot["state"].pop("switch_hazard_context")
    snapshot["state_fingerprint"] = state_fingerprint(snapshot["state"])
    # The original D0 cannot be paired with a changed snapshot.
    assert materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="opponent_switch:s:1:bench")["status"] == "rejected"


def test_unselectable_or_mismatched_response_never_materializes():
    manager = _manager(); d0, snapshot, switch = _inputs(manager)
    assert materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switch, selected_response_action_id="unknown")["status"] == "rejected"
    foreign = deepcopy(switch); foreign["source_branch_fingerprint"] = "foreign"
    assert materialize_detached_opponent_switch_in_intermediate_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=foreign, selected_response_action_id="opponent_switch:s:1:bench")["status"] == "rejected"

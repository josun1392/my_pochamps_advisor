from copy import deepcopy
from inspect import getsource

from llm.advisor_current_combined_opponent_response_universe_observation import (
    admit_current_combined_opponent_response_universe_observation,
)
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_d0_combined_opponent_response_universe_authority import (
    freeze_runtime_d0_combined_opponent_response_universe_authority,
)
from llm.advisor_runtime_d0_complete_opponent_response_set_authority import (
    freeze_runtime_d0_complete_opponent_response_set_authority,
)
from llm.advisor_runtime_d0_opponent_action_authority import (
    METADATA_SCHEMA_VERSION,
    freeze_runtime_d0_opponent_known_move_action_authority,
)
from llm.advisor_runtime_d0_opponent_switch_response_authority import (
    freeze_runtime_d0_opponent_switch_response_authority,
)
from llm.advisor_runtime_d0_opponent_switch_target_combat_authority import (
    freeze_runtime_d0_opponent_switch_target_combat_authority,
)
from llm.advisor_runtime_strategy_d0 import freeze_runtime_strategy_d0
from ui.main_window import MainWindow


MOVES = ["tackle", "scratch", "growl", "tail-whip"]
TARGET_FACTS = {"slot_index": 1, "pokemon_id": "bench", "current_hp": 100, "max_hp": 100, "fainted": False, "types": ["normal"], "final_stats": {"attack": 100, "defense": 100, "special-attack": 100, "special-defense": 100, "speed": 100}, "stages": {"attack": 0, "defense": 0, "special-attack": 0, "special-defense": 0, "speed": 0, "accuracy": 0, "evasion": 0}, "condition": "none", "item": {"status": "known_absent"}, "ability": "pressure"}
HAZARDS = {"stealth_rock": "absent", "spikes_layers": 0, "toxic_spikes_layers": 0, "sticky_web": "absent"}


def _manager():
    state = create_unknown_bootstrap_battle_state("combined-ui", "self", "opponent")["state"]
    bench = deepcopy(state["opponent_side"]["pokemon"][0]); bench["pokemon_id"] = "bench"
    state["opponent_side"]["pokemon"][1] = bench
    created = BattleObservationRuntimeSessionManager.create("combined-ui", state)
    assert created["status"] == "session_ready"
    return created["manager"]


def _usability(value="usable"):
    return {move: {"status": value} for move in MOVES}


def _combined_authority(manager):
    state = manager.read_state()["state"]
    snapshot = {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}
    owner = {"session_id": state["session_id"], "side": "self", "slot_index": 0, "pokemon_id": "self"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    metadata = {move: {"status": "resolved", "schema_version": METADATA_SCHEMA_VERSION, "move_id": move, "metadata": {"move_id": move, "category": "physical", "power": 40, "type": "normal", "accuracy": 100, "priority": 0}, "provenance": "repository_normalized_move_metadata_v1"} for move in MOVES}
    known = freeze_runtime_d0_opponent_known_move_action_authority(strategy_d0=d0, runtime_snapshot=snapshot, canonical_move_metadata_authorities=metadata)
    moves = freeze_runtime_d0_complete_opponent_response_set_authority(strategy_d0=d0, runtime_snapshot=snapshot, opponent_known_move_authority=known)
    switches = freeze_runtime_d0_opponent_switch_response_authority(strategy_d0=d0, runtime_snapshot=snapshot)
    return freeze_runtime_d0_combined_opponent_response_universe_authority(strategy_d0=d0, runtime_snapshot=snapshot, move_response_authority=moves, switch_response_authority=switches), moves, switches


def test_one_production_batch_makes_both_current_and_combined_universe_resolved():
    manager = _manager()
    result = admit_current_combined_opponent_response_universe_observation(runtime_session_manager=manager, captured_session_id="combined-ui", move_ids=MOVES, move_usability=_usability(), permission="permitted", targets=[{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}], turn_number=1)
    assert result["status"] == "resolved"
    assert result["move_observation"]["observation_sequence"] == result["switch_observation"]["observation_sequence"] == result["shared_observation_sequence"]
    universe, moves, switches = _combined_authority(manager)
    assert moves["status"] == switches["status"] == universe["status"] == "resolved"
    assert universe["universe_state"] == "complete_with_selectable_responses"
    assert universe["selectable_response_action_ids"][-1] == "opponent_switch:combined-ui:1:bench"


def test_invalid_second_dimension_leaves_no_partial_current_authority_and_stale_rejects():
    manager = _manager()
    invalid = admit_current_combined_opponent_response_universe_observation(runtime_session_manager=manager, captured_session_id="combined-ui", move_ids=MOVES, move_usability=_usability(), permission="permitted", targets=[], turn_number=1)
    assert invalid["status"] == "incomplete"
    state = manager.read_state()["state"]
    assert "current_opponent_response_set" not in state["opponent_side"]["pokemon"][0]
    assert "current_opponent_switch_response_set" not in state["opponent_side"]
    assert admit_current_combined_opponent_response_universe_observation(runtime_session_manager=manager, captured_session_id="other", move_ids=MOVES, move_usability=_usability(), permission="blocked", targets=[{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}], turn_number=1)["status"] == "rejected"


def test_window_uses_one_atomic_combined_production_admission():
    source = getsource(MainWindow._open_current_combined_opponent_response_universe_confirmation)
    assert "admit_current_combined_opponent_response_universe_observation" in source


def test_atomic_target_combat_observation_is_d0_bound_and_resolves_switch_in_authority():
    manager = _manager()
    admitted = admit_current_combined_opponent_response_universe_observation(runtime_session_manager=manager, captured_session_id="combined-ui", move_ids=MOVES, move_usability=_usability(), permission="permitted", targets=[{"slot_index": 1, "pokemon_id": "bench", "availability": "alive"}], target_combat_facts=[TARGET_FACTS], switch_hazard_context=HAZARDS, turn_number=1)
    assert admitted["status"] == "resolved"
    state = manager.read_state()["state"]
    target = state["opponent_side"]["pokemon"][1]
    assert target["current_hp"] == 100 and target["current_type"] == ["normal"]
    universe, _, switches = _combined_authority(manager)
    snapshot = manager.capture_runtime_state_snapshot("combined-ui")
    owner = {"session_id": "combined-ui", "side": "self", "slot_index": 0, "pokemon_id": "self"}
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=owner)
    combat = freeze_runtime_d0_opponent_switch_target_combat_authority(strategy_d0=d0, runtime_snapshot=snapshot, switch_response_authority=switches, selected_response_action_id=universe["selectable_response_action_ids"][-1])
    assert combat["status"] == "resolved" and combat["combat_fields"]["max_hp"] == 100
    assert admitted["target_combat_observations"][0]["observation_sequence"] == admitted["shared_observation_sequence"]

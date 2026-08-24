"""Final combat stats are runtime observations, never reconstructed defaults."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import FINAL_COMBAT_STAT_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_reducer_state_model import state_fingerprint
from llm.advisor_runtime_strategy_d0 import (
    freeze_runtime_final_combat_stat_authority,
    freeze_runtime_strategy_d0,
    freeze_runtime_water_gun_predictive_input,
)


def _state(session: str = "runtime-final-stat") -> dict:
    state = create_unknown_bootstrap_battle_state(session, "attacker", "target")["state"]
    for side in ("self", "opponent"):
        state[f"{side}_side"]["pokemon"][0].update(current_hp=100, max_hp=100, fainted=False)
    return state


def _owner(state: dict, side: str = "self") -> dict:
    return {"session_id": state["session_id"], "side": side, "slot_index": 0, "pokemon_id": state[f"{side}_side"]["pokemon"][0]["pokemon_id"]}


def _snapshot(state: dict) -> dict:
    return {"status": "runtime_snapshot_ready", "session_id": state["session_id"], "state": deepcopy(state), "state_fingerprint": state_fingerprint(state)}


def _capture(manager, boundary, *, side: str, pokemon_id: str, stat: str, value: int) -> None:
    confirmation = boundary.confirm(
        event_kind="current_final_combat_stat_observed", payload={"stat": stat, "value": value},
        session_id="runtime-final-stat", source=FINAL_COMBAT_STAT_SOURCE, trust=USER_TRUST,
        confirmed=True, side=side, slot_index=0, pokemon_id=pokemon_id, turn_number=1,
    )
    assert manager.admit_confirmation("runtime-final-stat", confirmation)["status"] == "added"
    assert manager.apply("runtime-final-stat", manager.read_collection_snapshot())["status"] == "applied"


def test_runtime_final_stats_are_identity_bound_stage_unmodified_and_propagate_to_d0() -> None:
    state = _state()
    manager = BattleObservationRuntimeSessionManager.create("runtime-final-stat", state)["manager"]
    boundary = LifecycleConfirmationBoundary("runtime-final-stat", {"self": {"slot_index": 0, "pokemon_id": "attacker"}, "opponent": {"slot_index": 0, "pokemon_id": "target"}})
    _capture(manager, boundary, side="self", pokemon_id="attacker", stat="special-attack", value=123)
    _capture(manager, boundary, side="opponent", pokemon_id="target", stat="special-defense", value=111)
    snapshot = manager.capture_runtime_state_snapshot("runtime-final-stat")
    d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(snapshot["state"]))

    attack = freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(snapshot["state"]), stat="special-attack")
    defense = freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(snapshot["state"], "opponent"), stat="special-defense")

    assert d0["strategy_state"]["active"]["self"]["current_final_stats"]["special-attack"]["value"] == 123
    assert attack["status"] == defense["status"] == "resolved"
    assert attack["final_stat_authority"]["value"] == 123
    assert defense["final_stat_authority"]["value"] == 111
    assert attack["stage_authority"] == {"status": "unknown", "reason": "runtime_stat_stage_unknown"}


def test_final_stat_authority_rejects_stale_and_wrong_identity_and_water_gun_uses_known_stats() -> None:
    state = _state()
    for side, stat, value in (("self", "special-attack", 123), ("opponent", "special-defense", 111)):
        pokemon = state[f"{side}_side"]["pokemon"][0]
        pokemon["current_final_stats"][stat] = {"value": value, "provenance": {"event_kind": "current_final_combat_stat_observed", "trust": "user_confirmed_observation", "turn_number": 1}}
    state["self_side"]["pokemon"][0]["stat_stages"] = {"special-attack": 2}
    snapshot = _snapshot(state); d0 = freeze_runtime_strategy_d0(runtime_snapshot=snapshot, decision_owner=_owner(state))
    advanced = deepcopy(state); advanced["last_applied_observation_sequence"] = 1

    assert freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=_snapshot(advanced), owner=_owner(state), stat="special-attack")["status"] == "rejected"
    assert freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state, "opponent"), stat="special-attack")["status"] == "incomplete"
    staged = freeze_runtime_final_combat_stat_authority(strategy_d0=d0, runtime_snapshot=snapshot, owner=_owner(state), stat="special-attack")
    assert staged["final_stat_authority"]["value"] == 123
    assert staged["stage_authority"]["value"] == 2
    water = freeze_runtime_water_gun_predictive_input(strategy_d0=d0, runtime_snapshot=snapshot, attacker=_owner(state), target=_owner(state, "opponent"), move_id="water-gun")
    assert water["authority_fields"]["attacker_final_special_attack"]["value"] == 123
    assert water["authority_fields"]["target_final_special_defense"]["value"] == 111
    assert "runtime_stat_provenance_unavailable" in water["missing_authority"]

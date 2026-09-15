from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_production_forced_switch_integration import admit_forced_switch_phazing
from llm.advisor_reducer_state_model import project_atomic_transition
from llm.advisor_switch_hazard_authority import build_switch_hazard_context


def _manager():
    state = create_unknown_bootstrap_battle_state("production-phaze", "self-a", "opponent-a")["state"]
    for side in ("self", "opponent"):
        active = state[f"{side}_side"]["pokemon"][0]
        active.update(current_hp=80, max_hp=100, fainted=False, known_item=None)
        bench = deepcopy(active); bench["pokemon_id"] = f"{side}-b"
        state[f"{side}_side"]["pokemon"][1] = bench
    state["switch_hazard_context"] = build_switch_hazard_context(session_id="production-phaze", affected_side="self", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
    return BattleObservationRuntimeSessionManager.create("production-phaze", state)["manager"]


def _known_persistent_state(manager, side="self", persistent_state="inactive"):
    state = manager.read_state()["state"]
    pokemon_id = state[f"{side}_side"]["pokemon"][0]["pokemon_id"]
    plan = {"session_id": state["session_id"], "status": "planned", "conflicts": [], "ordered_steps": [{
        "observation_id": f"ingrain-{side}", "observation_sequence": 1,
        "planned_effect": "set_current_ingrain_state", "side": side, "slot_index": 0,
        "pokemon_id": pokemon_id, "persistent_state": persistent_state,
        "trust": "user_confirmed_observation", "turn_number": 1,
    }]}
    projected = project_atomic_transition(state, plan, state["session_id"])["projected_state"]
    return BattleObservationRuntimeSessionManager.create(state["session_id"], projected)["manager"]


def _known_inactive(manager, side="self"):
    return _known_persistent_state(manager, side)


def _neutral_hazards(manager, side):
    state = manager.read_state()["state"]
    state["switch_hazard_context"] = build_switch_hazard_context(
        session_id="production-phaze", affected_side=side, stealth_rock="absent",
        spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent",
    )
    return BattleObservationRuntimeSessionManager.create("production-phaze", state)["manager"]


def _admit(manager, **kwargs):
    return admit_forced_switch_phazing(runtime_session_manager=manager, captured_session_id="production-phaze", target_side="self", move_id="roar", incoming_pokemon_id="self-b", turn_number=1, **kwargs)


def test_roar_neutral_entry_commits_exactly_one_authoritative_switch():
    manager = _known_inactive(_manager())
    result = _admit(manager)
    assert result["status"] == "resolved", result
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 1


def test_ingrain_unknown_fails_closed_without_runtime_mutation():
    manager = _manager(); before = manager.read_state()
    # No persistent observation is present, so Ingrain remains unknown.
    result = _admit(manager)
    assert result["status"] == "incomplete" and manager.read_state() == before


def test_active_ingrain_cancels_without_authoritative_writeback():
    manager = _known_persistent_state(_manager(), persistent_state="active")
    before = manager.read_state()
    result = _admit(manager)
    assert result["status"] == "resolved" and result["reason"] == "cancelled"
    assert result["observation_transaction"] == [] and manager.read_state() == before


def test_whirlwind_is_side_neutral_for_an_opponent_target():
    manager = _neutral_hazards(_known_inactive(_manager(), "opponent"), "opponent")
    result = admit_forced_switch_phazing(
        runtime_session_manager=manager, captured_session_id="production-phaze",
        target_side="opponent", move_id="whirlwind", incoming_pokemon_id="opponent-b",
        turn_number=1,
    )
    assert result["status"] == "resolved", result
    assert manager.read_state()["state"]["opponent_side"]["active_slot_index"] == 1


@pytest.mark.parametrize("incoming", ["self-a", "opponent-b", "missing"])
def test_invalid_replacement_fails_closed_without_partial_writeback(incoming):
    manager = _known_inactive(_manager())
    before = manager.read_state()
    result = admit_forced_switch_phazing(
        runtime_session_manager=manager, captured_session_id="production-phaze",
        target_side="self", move_id="roar", incoming_pokemon_id=incoming, turn_number=1,
    )
    assert result["status"] == "rejected" and manager.read_state() == before


@pytest.mark.parametrize(("move", "target", "incoming", "after"), [("dragon-tail", "self", "self-b", 60), ("circle-throw", "opponent", "opponent-b", 60)])
def test_damage_phazing_requires_exact_hp_and_is_atomic(move, target, incoming, after):
    manager = _known_inactive(_manager(), target)
    if target == "opponent":
        state = manager.read_state()["state"]
        state["switch_hazard_context"] = build_switch_hazard_context(session_id="production-phaze", affected_side="opponent", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
        manager = BattleObservationRuntimeSessionManager.create("production-phaze", state)["manager"]
    before = manager.read_state()
    bad = admit_forced_switch_phazing(runtime_session_manager=manager, captured_session_id="production-phaze", target_side=target, move_id=move, incoming_pokemon_id=incoming, turn_number=1, hp_after=None)
    assert bad["status"] == "rejected" and manager.read_state() == before


@pytest.mark.parametrize(("move", "target", "incoming"), [("dragon-tail", "self", "self-b"), ("circle-throw", "opponent", "opponent-b")])
def test_damage_then_switch_commits_in_one_ordered_transaction(move, target, incoming):
    manager = _known_inactive(_manager(), target)
    if target == "opponent":
        state = manager.read_state()["state"]
        state["switch_hazard_context"] = build_switch_hazard_context(session_id="production-phaze", affected_side="opponent", stealth_rock="absent", spikes_layers=0, toxic_spikes_layers=0, sticky_web="absent")
        manager = BattleObservationRuntimeSessionManager.create("production-phaze", state)["manager"]
    result = admit_forced_switch_phazing(runtime_session_manager=manager, captured_session_id="production-phaze", target_side=target, move_id=move, incoming_pokemon_id=incoming, turn_number=1, hp_after=60)
    assert result["status"] == "resolved", result
    assert [row["event_kind"] for row in result["observation_transaction"]] == ["exact_hp_transition_observed", "pokemon_switch_observed"]
    state = manager.read_state()["state"]
    assert state[f"{target}_side"]["active_slot_index"] == 1


def test_phazing_ko_commits_damage_only_and_suppresses_switch():
    manager = _known_inactive(_manager())
    result = admit_forced_switch_phazing(runtime_session_manager=manager, captured_session_id="production-phaze", target_side="self", move_id="dragon-tail", incoming_pokemon_id="self-b", turn_number=1, hp_after=0)
    assert result["status"] == "resolved"
    assert [row["event_kind"] for row in result["observation_transaction"]] == ["exact_hp_transition_observed"]
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0

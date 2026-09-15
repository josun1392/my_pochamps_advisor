from copy import deepcopy
from types import SimpleNamespace

from llm.advisor_ability_interaction_authority import build_ability_applicability_context
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_pokemon_switch_observation import admit_pokemon_switch_observation
from ui.main_window import MainWindow


def _manager():
    state = create_unknown_bootstrap_battle_state(
        "s", "pikachu", "eevee",
        self_roster={0: "pikachu", 1: "raichu"},
        opponent_roster={0: "eevee", 1: "vaporeon"},
    )["state"]
    for side in ("self_side", "opponent_side"):
        for pokemon in state[side]["pokemon"].values():
            pokemon["current_hp"] = 90
            pokemon["max_hp"] = 100
            pokemon["fainted"] = False
            pokemon["stat_stages"] = {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _switch(manager, *, side="self", slot=1, pokemon="raichu", session="s"):
    return admit_pokemon_switch_observation(
        runtime_session_manager=manager,
        captured_session_id=session,
        side=side,
        switch_in_slot_index=slot,
        switch_in_pokemon_id=pokemon,
        turn_number=4,
    )


def test_explicit_switch_observation_previews_admits_and_applies_exact_runtime_identity():
    manager = _manager()
    before = manager.read_state()["state"]
    before["self_side"]["pokemon"][0]["stat_stages"]["attack"] = 3
    # The runtime owns stage state, so use an explicit initial manager with it.
    manager = BattleObservationRuntimeSessionManager.create("s", before)["manager"]
    result = _switch(manager)
    assert result["status"] == "resolved"
    assert result["observation"]["event_kind"] == "pokemon_switch_observed"
    assert result["observation"]["payload"] == {
        "switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu",
        "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu",
    }
    assert result["observation"]["observation_sequence"] == 1
    assert result["preview"]["status"] == "preview_ready"
    state = manager.read_state()["state"]
    assert state["self_side"]["active_slot_index"] == 1
    assert state["self_side"]["pokemon"][0]["stat_stages"] == {key: 0 for key in ("attack", "defense", "special-attack", "special-defense", "speed", "accuracy", "evasion")}
    assert manager.read_collection_snapshot()["ordered_observations"] == [result["observation"]]


def test_opponent_switch_is_side_neutral_and_does_not_change_self_active_owner():
    manager = _manager()
    result = _switch(manager, side="opponent", slot=1, pokemon="vaporeon")
    state = manager.read_state()["state"]
    assert result["status"] == "resolved"
    assert state["opponent_side"]["active_slot_index"] == 1
    assert state["self_side"]["active_slot_index"] == 0


def test_production_switch_runs_outgoing_regenerator_and_natural_cure_lifecycles():
    state = _manager().read_state()["state"]
    outgoing = state["self_side"]["pokemon"][0]
    outgoing.update(current_hp=30, max_hp=90, fainted=False, current_ability="regenerator")
    outgoing["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    state["ability_applicability_context"] = build_ability_applicability_context(
        session_id="s", source={"side": "self", "slot_index": 0, "pokemon_id": "pikachu"}, ability_id="regenerator", status="applicable",
    )
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["status"] == "resolved"
    retired = manager.read_state()["state"]["self_side"]["pokemon"][0]
    assert retired["current_hp"] == 60 and retired["current_ability"] == {"knowledge": "unknown"}

    state = _manager().read_state()["state"]
    outgoing = state["self_side"]["pokemon"][0]
    outgoing.update(current_ability="natural-cure", condition="burn")
    outgoing["current_ability_provenance"] = {"event_kind": "current_ability_observed", "trust": "user_confirmed_observation", "turn_number": 1}
    outgoing["condition_provenance"] = {"event_kind": "current_condition_observed", "trust": "user_confirmed_observation", "turn_number": 1, "condition": "burn"}
    state["ability_applicability_context"] = build_ability_applicability_context(
        session_id="s", source={"side": "self", "slot_index": 0, "pokemon_id": "pikachu"}, ability_id="natural-cure", status="applicable",
    )
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["status"] == "resolved"
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["condition"] is None


def test_switch_rejects_stale_session_mismatched_or_fainted_incoming_without_runtime_mutation():
    manager = _manager()
    before = manager.read_state()
    assert _switch(manager, session="stale")["reason"] == "runtime_snapshot_unavailable"
    assert _switch(manager, pokemon="wrong")["reason"] == "switch_in_identity_mismatch"
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][1]["fainted"] = True
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]
    assert _switch(manager)["reason"] == "switch_in_fainted"
    assert manager.read_state()["state"]["self_side"]["active_slot_index"] == 0
    assert before["state"]["self_side"]["active_slot_index"] == 0


def test_duplicate_cannot_double_apply_and_same_active_identity_fails_closed():
    manager = _manager()
    first = _switch(manager)
    assert first["status"] == "resolved"
    assert _switch(manager, slot=1, pokemon="raichu")["reason"] == "switch_in_matches_active_owner"
    assert manager.read_state()["state"]["last_applied_observation_sequence"] == 1


def test_mainwindow_switch_helper_only_updates_presentation_after_success(monkeypatch):
    manager = _manager()
    selections = []
    cleared = []
    window = SimpleNamespace(
        _observation_runtime_session_manager=manager,
        _current_trusted_turn_number=4,
        _recommendation_readiness_owner=("s", 0, "pikachu"),
        center_column=SimpleNamespace(llm_advice_panel=SimpleNamespace(clear_recommendation_readiness=lambda: cleared.append(True))),
        select_slot=lambda column, slot: selections.append((column, slot)),
        _retire_advice_presentation_authority=lambda: cleared.append("retired"),
    )
    window._active_session_id = lambda: "s"
    result = MainWindow._confirm_pokemon_switch(window, side="self", switch_in_slot_index=1, switch_in_pokemon_id="raichu")
    assert result["status"] == "resolved"
    assert selections == [("team_my", 1)]
    assert cleared == ["retired", True]
    assert window._recommendation_readiness_owner is None

    failed = SimpleNamespace(**window.__dict__)
    failed._observation_runtime_session_manager = _manager()
    failed._active_session_id = lambda: "s"
    selections.clear(); cleared.clear()
    result = MainWindow._confirm_pokemon_switch(failed, side="self", switch_in_slot_index=1, switch_in_pokemon_id="wrong")
    assert result["status"] == "rejected"
    assert selections == [] and cleared == []


def test_slot_navigation_does_not_reference_or_emit_switch_observation():
    source = MainWindow.select_slot.__code__.co_names
    assert "_confirm_pokemon_switch" not in source
    assert "admit_pokemon_switch_observation" not in source


def test_bootstrap_can_seed_exact_loaded_roster_identities_without_filling_battle_facts():
    created = create_unknown_bootstrap_battle_state(
        "s", "pikachu", "eevee",
        self_roster={0: "pikachu", 1: "raichu"},
        opponent_roster={0: "eevee", 1: "vaporeon"},
    )
    assert created["status"] == "initial_state_ready"
    assert created["state"]["self_side"]["pokemon"][1]["pokemon_id"] == "raichu"
    assert created["state"]["self_side"]["pokemon"][1]["current_hp"] == {"knowledge": "unknown"}

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import FIRST_END_OF_TURN_SOURCE, HP_TRANSITION_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _snapshot(projection, turn):
    return build_turn_snapshot_from_battle_input({
        "pokemon": {"my_active": {"slot_index": 0, "name_en": "pikachu", "name_ko": "Pikachu"}, "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "Eevee"}},
        "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}},
        "current_state_session_id": "s", "runtime_advice_state": projection,
    }, trusted_turn_context={"status": "available", "session_id": "s", "turn_number": turn, "source": "explicit_application_turn_state", "trust": "user_or_application_confirmed"}).to_dict()["current_state"]


def test_confirmed_first_end_of_turn_phase_projects_only_for_its_current_turn():
    manager = _manager()
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    confirmation = boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4)
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert projection["field"]["first_end_of_turn_phases"][0]["turn_number"] == 4
    reached = _snapshot(projection, 4)["first_end_of_turn_phase_context"]
    assert reached["status"] == "reached" and reached["projection_source"] == "runtime_first_end_of_turn_phase_projection"
    assert _snapshot(projection, 5)["first_end_of_turn_phase_context"]["status"] == "unknown"


def test_phase_requires_explicit_turn_and_rejects_later_same_turn_state_transition():
    manager = _manager()
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    assert boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True)["excluded_reason"] == "missing_turn_number"
    phase = boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4)
    hp = boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before": 80, "hp_after": 40}, session_id="s", source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4)
    assert manager.admit_confirmation("s", phase)["status"] == "added"
    assert manager.admit_confirmation("s", hp)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "transition_invalid"

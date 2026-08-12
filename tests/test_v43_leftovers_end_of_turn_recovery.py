from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import FIRST_END_OF_TURN_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager(*, hp=80, item="leftovers", fainted=False):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    pokemon = state["self_side"]["pokemon"][0]
    pokemon.update(current_hp=hp, max_hp=100, known_item=item, fainted=fainted)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _phase(manager):
    boundary = LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})
    confirmation = boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=4)
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def test_leftovers_recovers_only_exact_living_owner_after_confirmed_phase_and_projects_hp():
    manager = _manager()
    _phase(manager)
    state = manager.read_state()["state"]
    pokemon = state["self_side"]["pokemon"][0]
    assert pokemon["current_hp"] == 86
    result = state["leftovers_end_of_turn_context"]
    assert result == [{"session_id": "s", "turn_number": 4, "side": "self", "slot_index": 0, "pokemon_id": "pikachu", "item": "leftovers", "pre_hp": 80, "max_hp": 100, "recovery": 6, "post_hp": 86, "outcome": "recovered", "provenance": result[0]["provenance"]}]
    projection = build_runtime_advice_state_projection(state)["runtime_advice_state"]
    assert projection["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 86}
    current = build_turn_snapshot_from_battle_input({"pokemon": {"my_active": {"slot_index": 0, "name_en": "pikachu", "name_ko": "Pikachu"}, "opponent_active": {"slot_index": 0, "name_en": "eevee", "name_ko": "Eevee"}}, "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}}, "current_state_session_id": "s", "runtime_advice_state": projection}, trusted_turn_context={"status": "available", "session_id": "s", "turn_number": 5, "source": "explicit_application_turn_state", "trust": "user_or_application_confirmed"}).to_dict()["current_state"]
    assert current["runtime_advice_state"]["self"]["active_pokemon"]["current_hp"]["value"] == 86


def test_leftovers_full_hp_is_deterministic_no_change_and_unknown_or_fainted_owners_do_not_activate():
    full = _manager(hp=100); _phase(full)
    full_result = full.read_state()["state"]["leftovers_end_of_turn_context"][0]
    assert full_result["outcome"] == "already_full_hp" and full_result["recovery"] == 0 and full_result["post_hp"] == 100
    unknown_item = _manager(item={"knowledge": "unknown"}); _phase(unknown_item)
    assert unknown_item.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 80
    assert unknown_item.read_state()["state"].get("leftovers_end_of_turn_context", []) == []
    fainted = _manager(hp=0, fainted=True); _phase(fainted)
    assert fainted.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 0
    assert fainted.read_state()["state"].get("leftovers_end_of_turn_context", []) == []

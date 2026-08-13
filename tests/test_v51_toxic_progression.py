"""Explicit toxic progression remains identity-bound and phase-driven."""
from copy import deepcopy

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import CONDITION_APPLICATION_SOURCE, FIRST_END_OF_TURN_SOURCE, SWITCH_SOURCE, USER_TRUST, LifecycleConfirmationBoundary
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_roster_mechanics import build_self_roster_mechanics_context_projection
from llm.advisor_switch_incoming_evaluator import _evaluate_first_status_residual
from llm.advisor_turn_snapshot import build_turn_snapshot_from_battle_input


def _manager(*, hp=100):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=160, fainted=False)
    state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0]); state["self_side"]["pokemon"][1]["pokemon_id"] = "raichu"
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _toxic(boundary, *, turn=4):
    return boundary.confirm(event_kind="condition_applied_observed", payload={"condition": "toxic"}, session_id="s", source=CONDITION_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=turn)


def _phase(boundary, turn):
    return boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def test_ordered_toxic_application_initializes_stage_one_then_advances_across_phases():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _toxic(boundary)); _apply(manager, _phase(boundary, 4))
    state = manager.read_state()["state"]; first = state["toxic_end_of_turn_context"][0]
    assert first["stage"] == 1 and first["damage"] == 10 and state["self_side"]["pokemon"][0]["current_hp"] == 90
    assert state["self_side"]["pokemon"][0]["toxic_progression"]["next_stage"] == 2
    _apply(manager, _phase(boundary, 5))
    second = manager.read_state()["state"]["toxic_end_of_turn_context"][1]
    assert second["stage"] == 2 and second["damage"] == 20 and second["post_hp"] == 70


def test_known_toxic_without_trusted_ordered_application_stays_progression_unknown():
    manager, boundary = _manager(), _boundary()
    assert _toxic(boundary, turn=None)["status"] == "invalid_provenance"
    state = manager.read_state()["state"]
    state["self_side"]["pokemon"][0]["condition"] = "toxic"
    runtime = build_runtime_advice_state_projection(state)["runtime_advice_state"]
    assert runtime["self"]["active_pokemon"]["toxic_progression"] == {"status": "unknown"}


def test_switch_and_frozen_snapshot_isolate_toxic_progression_identity():
    manager, boundary = _manager(), _boundary()
    _apply(manager, _toxic(boundary)); _apply(manager, _phase(boundary, 4))
    before = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert before["self"]["active_pokemon"]["toxic_progression"] == {"status": "known", "value": {"next_stage": 2}}
    frozen = build_turn_snapshot_from_battle_input({"pokemon": {"my_active": {"slot_index": 0, "name_en": "pikachu"}, "opponent_active": {"slot_index": 0, "name_en": "eevee"}}, "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}}, "current_state_session_id": "s", "runtime_advice_state": before}).to_dict()["current_state"]
    _apply(manager, boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu"}, session_id="s", source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu"))
    after = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    assert after["self"]["active_pokemon"]["toxic_progression"] == {"status": "unknown"}
    assert frozen["runtime_advice_state"]["self"]["active_pokemon"]["toxic_progression"] == {"status": "known", "value": {"next_stage": 2}}


def test_toxic_stage_caps_at_fifteen_and_feeds_existing_residual_ko_evidence():
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    pokemon = state["self_side"]["pokemon"][0]
    pokemon.update(current_hp=200, max_hp=200, fainted=False, condition="toxic", toxic_progression={"next_stage": 15, "initialized_turn": 4, "last_processed_turn": 4, "condition_observation_id": "toxic", "provenance": {"event_kind": "condition_applied_observed", "trust": USER_TRUST}})
    manager = BattleObservationRuntimeSessionManager.create("s", state)["manager"]; boundary = _boundary()
    _apply(manager, _phase(boundary, 5))
    result = manager.read_state()["state"]["toxic_end_of_turn_context"][0]
    assert result["stage"] == 15 and result["damage"] == 187
    assert manager.read_state()["state"]["self_side"]["pokemon"][0]["toxic_progression"]["next_stage"] == 15
    evidence = _evaluate_first_status_residual(target={"persistent_condition_authority": {"status": "known", "value": "toxic"}, "toxic_progression_authority": {"status": "known", "value": {"next_stage": 3}}, "ability_authority": {"status": "known", "value": "pressure"}, "hp_authority": {"status": "known", "current_hp": 30, "maximum_hp": 160}}, entry_effect_result=None, damage={"damage_range": {"minimum": 0}})
    assert evidence["toxic_stage"] == 3 and evidence["residual_damage"] == 30 and evidence["guaranteed_ko"] is True
    roster = build_self_roster_mechanics_context_projection(manager.read_state()["state"])
    assert roster["entries"][0]["toxic_progression_authority"] == {"status": "known", "value": {"next_stage": 15}}

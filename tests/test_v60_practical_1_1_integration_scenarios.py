"""Sanitized Practical 1.1 lifecycle, EOT, and direct-Q12 integration scenarios."""

from copy import deepcopy

import pytest

from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CONDITION_APPLICATION_SOURCE,
    CURRENT_ABILITY_SOURCE,
    CURRENT_TYPE_SOURCE,
    CURRENT_WEATHER_SOURCE,
    FIRST_END_OF_TURN_SOURCE,
    HP_TRANSITION_SOURCE,
    SAME_TURN_EVENT_SOURCE,
    SWITCH_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection
from llm.advisor_turn_snapshot import BASE_STAT_KEYS, build_request_start_recommendation_snapshot, build_snapshot_damage_input, build_snapshot_stat_provenance, build_turn_snapshot_from_battle_input


class _Species:
    def get(self, name):
        return {"en": name, "types_en": ["normal"], "base_stats": {key: 80 for key in BASE_STAT_KEYS}}


def _manager(*, hp=80, maximum=100, item=None, reserve=False):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=hp, max_hp=maximum, known_item=item, fainted=False)
    state["opponent_side"]["pokemon"][0].update(current_hp=80, max_hp=100, known_item=None, fainted=False)
    if reserve:
        state["self_side"]["pokemon"][1] = deepcopy(state["self_side"]["pokemon"][0])
        state["self_side"]["pokemon"][1].update(pokemon_id="raichu", known_item=None)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _ability(boundary, side, pokemon, ability, turn=4):
    return boundary.confirm(event_kind="current_ability_observed", payload={"ability": ability}, session_id="s", source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=0, pokemon_id=pokemon, turn_number=turn)


def _weather(boundary, weather, turn=4):
    return boundary.confirm(event_kind="current_weather_observed", payload={"weather": weather}, session_id="s", source=CURRENT_WEATHER_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def _phase(boundary, turn=4):
    return boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


@pytest.mark.parametrize(("weather", "ability", "expected_hp", "context"), [
    ("rain", "rain-dish", 86, "rain_dish_end_of_turn_context"),
    ("snow", "ice-body", 86, "ice_body_end_of_turn_context"),
    ("sun", "solar-power", 68, "solar_power_end_of_turn_context"),
    ("rain", "dry-skin", 92, "dry_skin_end_of_turn_context"),
    ("sun", "dry-skin", 68, "dry_skin_end_of_turn_context"),
])
def test_named_weather_passives_flow_through_authoritative_eot(weather, ability, expected_hp, context):
    manager, boundary = _manager(), _boundary()
    _apply(manager, _ability(boundary, "self", "pikachu", ability)); _apply(manager, _ability(boundary, "opponent", "eevee", "pressure")); _apply(manager, _weather(boundary, weather)); _apply(manager, _phase(boundary))
    state = manager.read_state()["state"]
    assert state["self_side"]["pokemon"][0]["current_hp"] == expected_hp
    assert state[context][0]["status"] == "complete"


def test_black_sludge_type_authority_and_snapshot_do_not_follow_switch_identity():
    manager, boundary = _manager(hp=95, item="black-sludge", reserve=True), _boundary()
    _apply(manager, boundary.confirm(event_kind="current_type_observed", payload={"types": ["poison"]}, session_id="s", source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4)); _apply(manager, _phase(boundary))
    projection = build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]
    frozen = build_turn_snapshot_from_battle_input({"pokemon": {"my_active": {"slot_index": 0, "name_en": "pikachu"}, "opponent_active": {"slot_index": 0, "name_en": "eevee"}}, "item_profiles": {"my_active": {}, "opponent_active": {}}, "moves": {"my_selected_move": {}}, "current_state_session_id": "s", "runtime_advice_state": projection}).to_dict()["current_state"]
    switch = boundary.confirm(event_kind="pokemon_switch_observed", payload={"switch_out_slot_index": 0, "switch_out_pokemon_id": "pikachu", "switch_in_slot_index": 1, "switch_in_pokemon_id": "raichu"}, session_id="s", source=SWITCH_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu")
    _apply(manager, switch)
    assert frozen["runtime_advice_state"]["self"]["active_pokemon"]["current_type"] == {"status": "known", "value": ["poison"]}
    assert build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]["self"]["active_pokemon"]["current_type"] == {"status": "unknown"}


def test_toxic_progression_life_orb_and_sandstorm_preserve_phase_and_event_boundaries():
    toxic, boundary = _manager(hp=100, maximum=160), _boundary()
    condition = boundary.confirm(event_kind="condition_applied_observed", payload={"condition": "toxic"}, session_id="s", source=CONDITION_APPLICATION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4)
    _apply(toxic, condition); _apply(toxic, _phase(boundary, 4)); _apply(toxic, _phase(boundary, 5))
    assert [row["stage"] for row in toxic.read_state()["state"]["toxic_end_of_turn_context"]] == [1, 2]
    assert toxic.read_state()["state"]["self_side"]["pokemon"][0]["current_hp"] == 70

    recoil, boundary = _manager(item="life-orb"), _boundary()
    _apply(recoil, _ability(boundary, "self", "pikachu", "pressure")); _apply(recoil, _ability(boundary, "opponent", "eevee", "pressure"))
    hit = boundary.confirm(event_kind="same_turn_event_observed", payload={"predicate": "qualifying_direct_damage_dealt", "occurred": True, "target_side": "opponent", "target_slot_index": 0, "target_pokemon_id": "eevee"}, session_id="s", source=SAME_TURN_EVENT_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4)
    _apply(recoil, hit)
    frozen_hp = deepcopy(build_runtime_advice_state_projection(recoil.read_state()["state"])["runtime_advice_state"])
    _apply(recoil, boundary.confirm(event_kind="exact_hp_transition_observed", payload={"hp_before": 70, "hp_after": 60}, session_id="s", source=HP_TRANSITION_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4))
    assert recoil.read_state()["state"]["life_orb_recoil_context"][0]["recoil"] == 10
    assert frozen_hp["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 70}

    sand, boundary = _manager(hp=6), _boundary()
    for observation in (_weather(boundary, "sandstorm"), boundary.confirm(event_kind="current_type_observed", payload={"types": ["normal"]}, session_id="s", source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side="self", slot_index=0, pokemon_id="pikachu", turn_number=4), boundary.confirm(event_kind="current_type_observed", payload={"types": ["normal"]}, session_id="s", source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side="opponent", slot_index=0, pokemon_id="eevee", turn_number=4), _ability(boundary, "self", "pikachu", "pressure"), _ability(boundary, "opponent", "eevee", "pressure"), _phase(boundary)):
        _apply(sand, observation)
    result = next(row for row in sand.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert result["guaranteed_ko"] is True and result["post_hp"] == 0


def _direct_result(move, metadata, *, attacker_hp=100, defender_item=None, defender_types=("normal",)):
    provenance = lambda side, slot, pokemon: {"side": side, "slot_index": slot, "pokemon_id": pokemon, "session_id": "s", "source": "user_confirmed_final_battle_stat", "trust": "user_confirmed_current"}
    stats = [{"side": side, "stat": key, "value": 100 + index, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat", "provenance": provenance(side, slot, pokemon)} for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)) for index, key in enumerate(BASE_STAT_KEYS)]
    absent = {"status": "known_absent"}; side = {"ability": absent, "item": absent, "boosts": {key: 0 for key in BASE_STAT_KEYS if key != "hp"}, "current_hp": 100, "max_hp": 100, "status": absent}
    conditions = [{"side": side_name, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"} for side_name in ("self", "opponent")]
    battle = {"current_state_session_id": "s", "pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "moves": {"my_available_moves": [{"slot_index": 0, "move_id": move}]}, "final_stat_context": {"current_final_stats": stats}, "condition_context": {"current_conditions": conditions}, "field_state_context": {"current_field": {"weather": "none", "terrain": "none", "side_effects": []}}, "trusted_level_context": {"current_levels": [{"side": "self", "value": 50, "provenance": {**provenance("self", 0, "pikachu"), "source": "user_confirmed_current_level"}}]}, "direct_mechanics_context": {"generation": "gen9", "attacker": {**deepcopy(side), "current_hp": attacker_hp}, "defender": deepcopy(side), "field": {"weather": absent, "terrain": absent}}}
    snapshot = build_request_start_recommendation_snapshot(battle, selectable_moves=(move,)); damage = build_snapshot_damage_input(snapshot, candidate_slot_index=0, candidate_move_id=move, selectable_moves=(move,), move_metadata=metadata); authority = build_snapshot_stat_provenance(snapshot, species_repository=_Species()); authority["defender"]["types"] = {"available": True, "value": list(defender_types)}
    if defender_item is not None: authority["defender"]["known_item"] = {"status": "known", "value": defender_item}
    return evaluate_direct_damage_mechanics(damage, stat_provenance=authority, trusted_level=50)


def test_direct_q12_consumes_resist_berries_chilan_and_flail_reversal_brackets():
    fire = _direct_result("tackle", {"category": "special", "power": 180, "type": "fire"}, defender_types=("grass",))
    occa = _direct_result("tackle", {"category": "special", "power": 180, "type": "fire"}, defender_item="occa-berry", defender_types=("grass",))
    normal = _direct_result("tackle", {"category": "special", "power": 180, "type": "normal"})
    chilan = _direct_result("tackle", {"category": "special", "power": 180, "type": "normal"}, defender_item="chilan-berry")
    flail = _direct_result("flail", {"category": "physical", "power": 20, "type": "normal"}, attacker_hp=4)
    reversal = _direct_result("reversal", {"category": "physical", "power": 20, "type": "fighting"}, attacker_hp=20)
    assert occa["damage_range"]["maximum"] < fire["damage_range"]["maximum"] and chilan["damage_range"]["maximum"] < normal["damage_range"]["maximum"]
    assert flail["dynamic_power_evidence"]["effective_power"] == 200 and reversal["dynamic_power_evidence"]["effective_power"] == 100
    assert all(result["ko_result"]["status"] == "resolved" for result in (occa, chilan, flail, reversal))

"""Bounded, authority-gated Sandstorm residual transitions."""
from copy import deepcopy

import pytest

from llm.advisor_initial_battle_state import create_unknown_bootstrap_battle_state
from llm.advisor_lifecycle_confirmation import (
    CURRENT_ABILITY_SOURCE,
    CURRENT_TYPE_SOURCE,
    CURRENT_WEATHER_SOURCE,
    FIRST_END_OF_TURN_SOURCE,
    USER_TRUST,
    LifecycleConfirmationBoundary,
)
from llm.advisor_observation_runtime_session import BattleObservationRuntimeSessionManager
from llm.advisor_runtime_state_projection import build_runtime_advice_state_projection


def _manager(*, self_hp=80, self_item=None, self_fainted=False):
    state = create_unknown_bootstrap_battle_state("s", "pikachu", "eevee")["state"]
    state["self_side"]["pokemon"][0].update(current_hp=self_hp, max_hp=100, known_item=self_item, fainted=self_fainted)
    state["opponent_side"]["pokemon"][0].update(current_hp=80, max_hp=100, known_item=None, fainted=False)
    return BattleObservationRuntimeSessionManager.create("s", state)["manager"]


def _boundary():
    return LifecycleConfirmationBoundary("s", {"self": {"slot_index": 0, "pokemon_id": "pikachu"}, "opponent": {"slot_index": 0, "pokemon_id": "eevee"}})


def _apply(manager, confirmation):
    assert manager.admit_confirmation("s", confirmation)["status"] == "added"
    assert manager.apply("s", manager.read_collection_snapshot())["status"] == "applied"


def _weather(boundary, weather, turn=4):
    return boundary.confirm(event_kind="current_weather_observed", payload={"weather": weather}, session_id="s", source=CURRENT_WEATHER_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def _type(boundary, side, pokemon_id, types, turn=4):
    return boundary.confirm(event_kind="current_type_observed", payload={"types": types}, session_id="s", source=CURRENT_TYPE_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=0, pokemon_id=pokemon_id, turn_number=turn)


def _ability(boundary, side, pokemon_id, ability, turn=4):
    return boundary.confirm(event_kind="current_ability_observed", payload={"ability": ability}, session_id="s", source=CURRENT_ABILITY_SOURCE, trust=USER_TRUST, confirmed=True, side=side, slot_index=0, pokemon_id=pokemon_id, turn_number=turn)


def _phase(boundary, turn=4):
    return boundary.confirm(event_kind="first_end_of_turn_reached_observed", payload={}, session_id="s", source=FIRST_END_OF_TURN_SOURCE, trust=USER_TRUST, confirmed=True, turn_number=turn)


def _known_nonimmune_authority(manager, boundary, *, self_type=("normal",), opponent_type=("normal",), self_ability="pressure", opponent_ability="pressure"):
    _apply(manager, _weather(boundary, "sandstorm"))
    _apply(manager, _type(boundary, "self", "pikachu", list(self_type)))
    _apply(manager, _type(boundary, "opponent", "eevee", list(opponent_type)))
    _apply(manager, _ability(boundary, "self", "pikachu", self_ability))
    _apply(manager, _ability(boundary, "opponent", "eevee", opponent_ability))


@pytest.mark.parametrize("types", [("rock",), ("ground",), ("steel",)])
def test_sandstorm_current_type_immunity_requires_no_species_fallback(types):
    manager, boundary = _manager(), _boundary()
    _apply(manager, _weather(boundary, "sandstorm")); _apply(manager, _type(boundary, "self", "pikachu", list(types)))
    _apply(manager, _phase(boundary))
    result = next(row for row in manager.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert result["outcome"] == "immune_by_type" and result["residual_damage"] == 0 and result["post_hp"] == 80


@pytest.mark.parametrize("ability", ["magic-guard", "overcoat", "sand-force", "sand-rush", "sand-veil"])
def test_sandstorm_exact_supported_ability_immunity_is_zero(ability):
    manager, boundary = _manager(), _boundary(); _known_nonimmune_authority(manager, boundary, self_ability=ability)
    _apply(manager, _phase(boundary))
    result = next(row for row in manager.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert result["outcome"] == "immune_by_ability" and result["residual_damage"] == 0


@pytest.mark.parametrize("suppressor", ["cloud-nine", "air-lock"])
def test_sandstorm_safety_goggles_and_global_weather_suppression_are_zero(suppressor):
    goggles, boundary = _manager(self_item="safety-goggles"), _boundary(); _known_nonimmune_authority(goggles, boundary)
    _apply(goggles, _phase(boundary))
    result = next(row for row in goggles.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert result["outcome"] == "prevented_by_safety_goggles" and result["residual_damage"] == 0

    suppressed, boundary = _manager(), _boundary(); _known_nonimmune_authority(suppressed, boundary, opponent_ability=suppressor)
    _apply(suppressed, _phase(boundary))
    assert {row["outcome"] for row in suppressed.read_state()["state"]["sandstorm_end_of_turn_context"]} == {"suppressed_by_ability"}


def test_sandstorm_damage_lethal_ko_and_runtime_hp_projection():
    manager, boundary = _manager(self_hp=6), _boundary(); _known_nonimmune_authority(manager, boundary)
    _apply(manager, _phase(boundary))
    result = next(row for row in manager.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert result["residual_damage"] == 6 and result["post_hp"] == 0 and result["guaranteed_ko"] is True
    assert build_runtime_advice_state_projection(manager.read_state()["state"])["runtime_advice_state"]["self"]["active_pokemon"]["current_hp"] == {"status": "known", "value": 0}


def test_sandstorm_unknown_material_authority_and_same_owner_order_stay_incomplete():
    unknown, boundary = _manager(), _boundary(); _apply(unknown, _weather(boundary, "sandstorm")); _apply(unknown, _type(boundary, "self", "pikachu", ["normal"])); _apply(unknown, _type(boundary, "opponent", "eevee", ["normal"])); _apply(unknown, _ability(boundary, "opponent", "eevee", "pressure")); _apply(unknown, _phase(boundary))
    self_result = next(row for row in unknown.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert self_result["status"] == "incomplete" and self_result["reason"] == "current_ability_unknown"

    unknown_item, boundary = _manager(self_item={"knowledge": "unknown"}), _boundary(); _known_nonimmune_authority(unknown_item, boundary)
    _apply(unknown_item, _phase(boundary))
    self_result = next(row for row in unknown_item.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert self_result["status"] == "incomplete" and self_result["reason"] == "current_item_unknown"

    ordered, boundary = _manager(self_item="leftovers"), _boundary(); _known_nonimmune_authority(ordered, boundary)
    _apply(ordered, _phase(boundary))
    result = next(row for row in ordered.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")
    assert result["status"] == "incomplete" and result["reason"] == "same_owner_end_of_turn_order_unknown"


def test_sandstorm_unknown_or_non_sand_weather_and_fainted_owner_do_not_apply_damage():
    unknown, boundary = _manager(), _boundary(); _apply(unknown, _type(boundary, "self", "pikachu", ["normal"])); _apply(unknown, _phase(boundary))
    assert next(row for row in unknown.read_state()["state"]["sandstorm_end_of_turn_context"] if row["pokemon_id"] == "pikachu")["reason"] == "current_weather_unknown"

    none, boundary = _manager(), _boundary(); _apply(none, _weather(boundary, "none")); _apply(none, _phase(boundary))
    assert none.read_state()["state"].get("sandstorm_end_of_turn_context", []) == []

    fainted, boundary = _manager(self_fainted=True), _boundary(); _apply(fainted, _weather(boundary, "sandstorm")); _apply(fainted, _type(boundary, "opponent", "eevee", ["normal"])); _apply(fainted, _ability(boundary, "opponent", "eevee", "pressure"))
    _apply(fainted, _phase(boundary))
    assert all(row["pokemon_id"] != "pikachu" for row in fainted.read_state()["state"].get("sandstorm_end_of_turn_context", []))

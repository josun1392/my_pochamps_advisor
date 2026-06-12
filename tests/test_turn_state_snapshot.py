from __future__ import annotations

import pytest

from core.turn_state import BattleState, PokemonBattleSlot, TurnInput, TurnSnapshot, normalize_turn_snapshot


def test_pokemon_battle_slot_serializes_defaults_and_unknown_values() -> None:
    slot = PokemonBattleSlot(side="player")

    assert slot.to_dict() == {
        "side": "player",
        "slot_index": None,
        "species_id": None,
        "species_name": None,
        "current_hp_percent": None,
        "known_item_id": None,
        "item_status": None,
        "stat_stages": {},
        "major_status": None,
        "volatile_conditions": [],
    }


def test_pokemon_battle_slot_serializes_confirmed_state() -> None:
    slot = PokemonBattleSlot(
        side="opponent",
        slot_index=1,
        species_id="pikachu",
        species_name="Pikachu",
        current_hp_percent=75.5,
        known_item_id="light-ball",
        item_status="user_confirmed",
        stat_stages={"attack": 1, "speed": -1},
        major_status="paralysis",
        volatile_conditions=("taunt", "encore"),
    )

    assert slot.to_dict() == {
        "side": "opponent",
        "slot_index": 1,
        "species_id": "pikachu",
        "species_name": "Pikachu",
        "current_hp_percent": 75.5,
        "known_item_id": "light-ball",
        "item_status": "user_confirmed",
        "stat_stages": {"attack": 1, "speed": -1},
        "major_status": "paralysis",
        "volatile_conditions": ["taunt", "encore"],
    }


def test_battle_state_serializes_nested_slots() -> None:
    battle_state = BattleState(
        active_player=PokemonBattleSlot(side="player", species_id="charizard", current_hp_percent=100),
        active_opponent=PokemonBattleSlot(side="opponent", species_id="garchomp", current_hp_percent=42),
        weather="sun",
        terrain="electric",
        field_conditions={"stealth_rock": {"opponent": True}},
        turn_number=3,
    )

    serialized = battle_state.to_dict()

    assert serialized["active_player"]["species_id"] == "charizard"
    assert serialized["active_opponent"]["species_id"] == "garchomp"
    assert serialized["field_conditions"] == {"stealth_rock": {"opponent": True}}
    assert serialized["turn_number"] == 3


def test_turn_input_serializes_optional_sides() -> None:
    assert TurnInput().to_dict() == {
        "selected_move_id": None,
        "acting_side": None,
        "target_side": None,
    }
    assert TurnInput(selected_move_id="tackle", acting_side="player", target_side="opponent").to_dict() == {
        "selected_move_id": "tackle",
        "acting_side": "player",
        "target_side": "opponent",
    }


def test_turn_snapshot_serializes_contract_without_engine_results() -> None:
    snapshot = TurnSnapshot(
        battle_state=BattleState(active_player=PokemonBattleSlot(side="player", species_id="pikachu")),
        turn_input=TurnInput(selected_move_id="thunderbolt", acting_side="player", target_side="opponent"),
        notes=("schema only",),
        limitations=("no full turn simulation",),
    )

    serialized = snapshot.to_dict()

    assert serialized["battle_state"]["active_player"]["species_id"] == "pikachu"
    assert serialized["turn_input"]["selected_move_id"] == "thunderbolt"
    assert serialized["notes"] == ["schema only"]
    assert serialized["limitations"] == ["no full turn simulation"]


@pytest.mark.parametrize("hp_percent", [-1, 100.1, "100", True])
def test_hp_percent_validation(hp_percent: object) -> None:
    with pytest.raises(ValueError):
        PokemonBattleSlot(side="player", current_hp_percent=hp_percent)  # type: ignore[arg-type]


@pytest.mark.parametrize("stage_value", [-7, 7, 1.5, True])
def test_stat_stage_validation(stage_value: object) -> None:
    with pytest.raises(ValueError):
        PokemonBattleSlot(side="player", stat_stages={"attack": stage_value})  # type: ignore[dict-item]


def test_invalid_side_validation() -> None:
    with pytest.raises(ValueError):
        PokemonBattleSlot(side="bench")

    with pytest.raises(ValueError):
        TurnInput(acting_side="bench")


def test_invalid_item_status_validation() -> None:
    with pytest.raises(ValueError):
        PokemonBattleSlot(side="player", item_status="held")


def test_from_dict_round_trip_preserves_unknown_values() -> None:
    snapshot = TurnSnapshot.from_dict(
        {
            "battle_state": {
                "active_player": {
                    "side": "player",
                    "species_id": "pikachu",
                    "current_hp_percent": None,
                    "item_status": "unknown",
                    "stat_stages": {},
                    "volatile_conditions": [],
                },
                "field_conditions": {},
            },
            "turn_input": {
                "selected_move_id": None,
                "acting_side": None,
                "target_side": None,
            },
        }
    )

    assert snapshot.to_dict()["battle_state"]["active_player"]["current_hp_percent"] is None
    assert snapshot.to_dict()["battle_state"]["active_player"]["item_status"] == "unknown"
    assert snapshot.to_dict()["turn_input"]["selected_move_id"] is None


def test_normalize_turn_snapshot_accepts_none_mapping_or_snapshot() -> None:
    default_snapshot = normalize_turn_snapshot()
    mapped_snapshot = normalize_turn_snapshot(default_snapshot.to_dict())

    assert default_snapshot.to_dict() == mapped_snapshot.to_dict()
    assert normalize_turn_snapshot(mapped_snapshot) is mapped_snapshot


def test_turn_state_collections_are_immutable_after_creation() -> None:
    slot = PokemonBattleSlot(side="player", stat_stages={"attack": 1}, volatile_conditions=["taunt"])
    battle_state = BattleState(field_conditions={"weather_source": "manual"})

    with pytest.raises(TypeError):
        slot.stat_stages["attack"] = 2  # type: ignore[index]
    with pytest.raises(TypeError):
        battle_state.field_conditions["weather_source"] = "engine"  # type: ignore[index]
    with pytest.raises(AttributeError):
        slot.volatile_conditions.append("encore")  # type: ignore[attr-defined]

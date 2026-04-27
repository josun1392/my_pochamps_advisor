from __future__ import annotations

import json
import pytest

from advisor.parity.bridge import BRIDGE_DIR, ParityBridgeError, call_smogon_calc
from advisor.parity.schemas import DamageRequest


EXAMPLE_REQUEST = BRIDGE_DIR / "examples" / "example_request.json"


def test_bridge_smoke() -> None:
    response = call_smogon_calc(_example_request())

    assert response.schema_version == "v1"
    assert response.damage_min == min(response.damage_rolls)
    assert response.damage_max == max(response.damage_rolls)
    assert response.raw_calc_desc


def test_deterministic() -> None:
    request = _example_request()

    first = call_smogon_calc(request)
    second = call_smogon_calc(request)

    assert first == second


def test_type_effectiveness() -> None:
    request = _request(
        attacker_species="charizard",
        defender_species="venusaur",
        move_name="flamethrower",
    )

    response = call_smogon_calc(request)

    assert response.modifiers.type_effectiveness == 2.0


def test_stab_applied() -> None:
    charizard = call_smogon_calc(
        _request(attacker_species="charizard", move_name="flamethrower")
    )
    blastoise = call_smogon_calc(
        _request(attacker_species="blastoise", move_name="flamethrower")
    )

    assert charizard.modifiers.stab == 1.5
    assert blastoise.modifiers.stab == 1.0


def test_weather_modifier() -> None:
    clear = call_smogon_calc(
        _request(attacker_species="charizard", move_name="fire-blast", weather=None)
    )
    sun = call_smogon_calc(
        _request(attacker_species="charizard", move_name="fire-blast", weather="sun")
    )

    assert sun.modifiers.weather == 1.5
    assert sun.damage_min > clear.damage_min


def test_error_handling() -> None:
    request_data = _request_dict(attacker_species="not-a-pokemon")
    request = DamageRequest.model_validate(request_data)

    with pytest.raises(ParityBridgeError):
        call_smogon_calc(request)


def _example_request() -> DamageRequest:
    return DamageRequest.model_validate_json(EXAMPLE_REQUEST.read_text(encoding="utf-8"))


def _request(
    *,
    attacker_species: str = "charizard",
    defender_species: str = "venusaur",
    move_name: str = "flamethrower",
    weather: str | None = None,
) -> DamageRequest:
    return DamageRequest.model_validate(
        _request_dict(
            attacker_species=attacker_species,
            defender_species=defender_species,
            move_name=move_name,
            weather=weather,
        )
    )


def _request_dict(
    *,
    attacker_species: str = "charizard",
    defender_species: str = "venusaur",
    move_name: str = "flamethrower",
    weather: str | None = None,
) -> dict:
    data = json.loads(EXAMPLE_REQUEST.read_text(encoding="utf-8"))
    data["attacker"].update(
        {
            "species": attacker_species,
            "ability": "blaze",
            "item": None,
            "nature": "modest",
        }
    )
    data["defender"].update(
        {
            "species": defender_species,
            "ability": "overgrow",
            "item": None,
            "nature": "calm",
        }
    )
    data["move"]["name"] = move_name
    data["field"]["weather"] = weather
    data["field"]["format"] = "gen9ou"
    return data

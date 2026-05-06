from __future__ import annotations

from advisor.damage.field import Field
from advisor.damage.grounded import GroundedInputs, is_grounded


def test_garchomp_is_grounded() -> None:
    assert is_grounded(GroundedInputs(("dragon", "ground")), Field())


def test_charizard_is_not_grounded() -> None:
    assert not is_grounded(GroundedInputs(("fire", "flying")), Field())


def test_iron_ball_forces_grounded() -> None:
    assert is_grounded(GroundedInputs(("fire", "flying"), item="iron-ball"), Field())


def test_roosting_flying_type_is_grounded() -> None:
    assert is_grounded(GroundedInputs(("fire", "flying"), is_rooting=True), Field())


def test_levitate_is_not_grounded() -> None:
    assert not is_grounded(GroundedInputs(("dragon", "ground"), ability="levitate"), Field())


def test_air_balloon_is_not_grounded() -> None:
    assert not is_grounded(GroundedInputs(("electric",), item="air-balloon"), Field())


def test_gravity_forces_grounded() -> None:
    assert is_grounded(GroundedInputs(("fire", "flying")), Field(is_gravity=True))

from __future__ import annotations

import pytest

from advisor.damage.modifiers.core import calc_stab
from advisor.damage.q12 import M_NEUTRAL, M_STAB
from advisor.damage.types import type_effectiveness
from llm.advisor_battle_state_context import normalize_current_type_authority


_OMITTED = object()


def _known(side: str, types: list[str]) -> dict[str, object]:
    return {
        "side": side, "state": "known", "types": types, "status": "user_confirmed",
        "source": "user_confirmed_current_type", "authority_provenance": "user_confirmed_current",
    }


def _unknown(side: str) -> dict[str, object]:
    return {
        "side": side, "state": "unknown", "status": "unknown", "source": "unknown",
        "authority_provenance": "unknown",
    }


def _design_type_authority(context: object, *, side: str, legacy_species_types: tuple[str, ...]) -> tuple[str, tuple[str, ...] | None]:
    """Test-only oracle for the documented future adapter; it does not alter Q12."""
    if context is _OMITTED:
        return "legacy_species", legacy_species_types
    if not isinstance(context, dict) or not isinstance(context.get("current_types"), list):
        return "malformed", None
    matches = [entry for entry in context["current_types"] if isinstance(entry, dict) and entry.get("side") == side]
    if len(matches) != 1:
        return ("unknown", None) if not matches else ("malformed", None)
    try:
        entry = normalize_current_type_authority({key: value for key, value in matches[0].items() if key != "provenance"})
    except ValueError:
        return "malformed", None
    if entry["state"] == "unknown":
        return "unknown", None
    return "known_current", tuple(entry["types"])


def test_design_authority_precedence_keeps_legacy_omission_distinct_from_explicit_unknown():
    known = {"current_types": [_known("self", ["fire"]), _known("opponent", ["water", "flying"])]}
    assert _design_type_authority(known, side="self", legacy_species_types=("water",)) == ("known_current", ("fire",))
    assert _design_type_authority(known, side="opponent", legacy_species_types=("ground",)) == ("known_current", ("water", "flying"))
    assert _design_type_authority(_OMITTED, side="self", legacy_species_types=("water",)) == ("legacy_species", ("water",))
    assert _design_type_authority({"current_types": [_unknown("self")]}, side="self", legacy_species_types=("water",)) == ("unknown", None)
    assert _design_type_authority({"current_types": [{**_known("self", ["fire"]), "types": ["fire", "fire"]}]}, side="self", legacy_species_types=("water",)) == ("malformed", None)


@pytest.mark.parametrize(("types", "move_type", "expected"), [
    (("fire",), "fire", M_STAB), (("water", "fire"), "fire", M_STAB), (("water", "fire"), "water", M_STAB),
    (("water", "fire"), "electric", M_NEUTRAL),
])
def test_design_stab_uses_only_the_resolved_acting_side_types(types: tuple[str, ...], move_type: str, expected: int):
    assert calc_stab(types, move_type) == expected


@pytest.mark.parametrize(("move_type", "defender_types", "expected"), [
    ("ice", ("dragon", "ground"), 16384),  # double weakness
    ("fire", ("water", "dragon"), 1024),  # double resistance
    ("normal", ("ghost", "dark"), 0),  # one immunity dominates the product
    ("electric", ("water", "flying"), 16384),
])
def test_design_effectiveness_reuses_the_canonical_dual_type_chart(move_type: str, defender_types: tuple[str, ...], expected: int):
    assert type_effectiveness(move_type, defender_types) == expected


def test_design_side_ownership_maps_self_and_opponent_actions_without_crossing_types():
    context = {"current_types": [_known("self", ["fire"]), _known("opponent", ["water"])]}
    self_attacker = _design_type_authority(context, side="self", legacy_species_types=("grass",))[1]
    self_defender = _design_type_authority(context, side="opponent", legacy_species_types=("rock",))[1]
    opponent_attacker = _design_type_authority(context, side="opponent", legacy_species_types=("rock",))[1]
    opponent_defender = _design_type_authority(context, side="self", legacy_species_types=("grass",))[1]
    assert self_attacker == ("fire",) and self_defender == ("water",)
    assert opponent_attacker == ("water",) and opponent_defender == ("fire",)
    assert calc_stab(self_attacker, "fire") == M_STAB
    assert type_effectiveness("fire", self_defender) == 2048

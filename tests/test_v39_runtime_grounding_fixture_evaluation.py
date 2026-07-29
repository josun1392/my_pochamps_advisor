"""Sanitized, deterministic v15.39 grounding fixtures; no provider access."""
from copy import deepcopy

import pytest

from llm.advisor_candidate_contract import validate_runtime_grounding


def _fact(status, value=None):
    result = {"status": status}
    if status == "known": result["value"] = value
    return result


def _runtime(**facts):
    base = {
        "self": {"active_pokemon": {"current_hp": _fact("unknown"), "max_hp": _fact("unknown"), "fainted": _fact("unknown"), "condition": _fact("unknown"), "item": _fact("unknown")}},
        "opponent": {"active_pokemon": {"current_hp": _fact("unknown"), "max_hp": _fact("unknown"), "fainted": _fact("unknown"), "condition": _fact("unknown"), "item": _fact("unknown")}},
        "field": {"weather": _fact("unknown"), "terrain": _fact("unknown"), "self_side_conditions": _fact("unknown"), "opponent_side_conditions": _fact("unknown")},
    }
    for path, value in facts.items():
        node = base
        parts = path.split(".")
        for part in parts[:-1]: node = node[part]
        node[parts[-1]] = value
    return base


def _grounding(*, confirmed=(), unknown=(), evidence=(), conflicts=(), deps=()):
    return {"schema_version": "grounding-v1", "confirmed_facts": list(confirmed), "unknown_facts": [{"path": p, "authority": "runtime"} for p in unknown], "evidence_only": [{**entry, "authority": "evidence"} for entry in evidence], "conflicts": [{**entry, "authority": "conflict", "source": entry.get("source", "ui")} for entry in conflicts], "conditional_dependencies": [{"path": p} for p in deps]}


def _confirmed(path, status, value=None):
    entry = {"path": path, "status": status, "authority": "runtime"}
    if status == "known": entry["value"] = value
    return entry


CATALOG = (
    ("runtime-unknown-bootstrap", _runtime(), _grounding(unknown=("opponent.active_pokemon.current_hp", "opponent.active_pokemon.item"), deps=("opponent.active_pokemon.current_hp",)), "need more information"),
    ("runtime-known-item-stale-ui", _runtime(**{"opponent.active_pokemon.item": _fact("known", "Focus Sash")}), _grounding(confirmed=(_confirmed("opponent.active_pokemon.item", "known", "Focus Sash"),), evidence=({"path": "opponent.active_pokemon.item", "source": "ui", "value": "Choice Scarf"},), conflicts=({"path": "opponent.active_pokemon.item"},)), "Focus Sash is confirmed"),
    ("runtime-unknown-user-item-evidence", _runtime(), _grounding(unknown=("opponent.active_pokemon.item",), evidence=({"path": "opponent.active_pokemon.item", "source": "user", "value": "Leftovers"},), deps=("opponent.active_pokemon.item",)), "item is unconfirmed"),
    ("runtime-known-absent-condition-weather", _runtime(**{"opponent.active_pokemon.condition": _fact("known_absent"), "field.weather": _fact("known_absent")}), _grounding(confirmed=(_confirmed("opponent.active_pokemon.condition", "known_absent"), _confirmed("field.weather", "known_absent"))), "confirmed absent"),
    ("runtime-partial-known-hp", _runtime(**{"opponent.active_pokemon.current_hp": _fact("known", 73)}), _grounding(confirmed=(_confirmed("opponent.active_pokemon.current_hp", "known", 73),), unknown=("opponent.active_pokemon.max_hp", "opponent.active_pokemon.fainted"), deps=("opponent.active_pokemon.max_hp",)), "survival is conditional"),
    ("runtime-burned-unapplied-paralysis", _runtime(**{"opponent.active_pokemon.condition": _fact("known", "burned")}), _grounding(confirmed=(_confirmed("opponent.active_pokemon.condition", "known", "burned"),), evidence=({"path": "opponent.active_pokemon.condition", "source": "observation", "value": "paralysis"},), conflicts=({"path": "opponent.active_pokemon.condition"},)), "burned is current"),
    ("runtime-field-side-condition-mixed", _runtime(**{"field.weather": _fact("known", "sandstorm"), "field.self_side_conditions": _fact("known_absent")}), _grounding(confirmed=(_confirmed("field.weather", "known", "sandstorm"), _confirmed("field.self_side_conditions", "known_absent")), unknown=("field.opponent_side_conditions",)), "opponent side conditions are unknown"),
    ("runtime-conflicting-item-evidence", _runtime(), _grounding(unknown=("opponent.active_pokemon.item",), evidence=({"path": "opponent.active_pokemon.item", "source": "user", "value": "Choice Scarf"}, {"path": "opponent.active_pokemon.item", "source": "observation", "value": "Leftovers"}), conflicts=({"path": "opponent.active_pokemon.item"},), deps=("opponent.active_pokemon.item",)), "item is conflicting"),
    ("missing-runtime-projection", None, None, ""),
    ("internal-metadata-exclusion", _runtime(), _grounding(unknown=("field.weather",)), "weather is unknown"),
)


@pytest.mark.parametrize("fixture_id,runtime,grounding,answer", CATALOG, ids=[item[0] for item in CATALOG])
def test_runtime_grounding_fixture_catalog(fixture_id, runtime, grounding, answer):
    if fixture_id == "missing-runtime-projection":
        assert validate_runtime_grounding(runtime_advice_state=None, grounding={}, legacy_compatible=False) == ["missing_runtime_projection"]
        return
    assert validate_runtime_grounding(runtime_advice_state=deepcopy(runtime), grounding=deepcopy(grounding), user_answer=answer) == []


def test_fixture_catalog_has_exact_ten_sanitized_ids():
    assert len(CATALOG) == 10
    assert len({item[0] for item in CATALOG}) == 10


def test_fixture_forbidden_internal_metadata_is_rejected():
    runtime = _runtime(); grounding = _grounding(unknown=("field.weather",))
    assert "internal_metadata_in_answer" in validate_runtime_grounding(runtime_advice_state=runtime, grounding=grounding, user_answer="CAS fingerprint")

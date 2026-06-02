from __future__ import annotations

import ast
import json
from pathlib import Path

from core.charge_move_repository import (
    CHARGE_MOVES_VERSION,
    ChargeMoveRepository,
    load_charge_moves,
    normalize_move_id,
)


FIXTURE_PATH = Path("data/static/charge_moves.json")
INITIAL_MOVES = {"solar-beam", "solar-blade", "meteor-beam", "sky-attack"}
REQUIRED_FIELDS = {
    "is_charge_move",
    "power_herb_eligible",
    "charge_type",
    "source",
    "confidence",
    "notes",
}


def test_charge_move_fixture_file_exists() -> None:
    assert FIXTURE_PATH.exists()


def test_charge_move_fixture_version_and_moves_object_exist() -> None:
    data = load_charge_moves()

    assert data["version"] == CHARGE_MOVES_VERSION
    assert isinstance(data["moves"], dict)


def test_charge_move_fixture_ids_are_normalized() -> None:
    data = load_charge_moves()

    for move_id in data["moves"]:
        assert move_id == normalize_move_id(move_id)
        assert move_id == move_id.lower()
        assert "_" not in move_id
        assert " " not in move_id


def test_initial_minimal_charge_moves_exist() -> None:
    data = load_charge_moves()

    assert INITIAL_MOVES <= set(data["moves"])


def test_charge_move_entries_have_required_fields() -> None:
    data = load_charge_moves()

    for move_id, metadata in data["moves"].items():
        assert REQUIRED_FIELDS <= set(metadata), move_id
        assert isinstance(metadata["is_charge_move"], bool)
        assert isinstance(metadata["power_herb_eligible"], bool)
        assert metadata["charge_type"]
        assert metadata["source"]
        assert metadata["confidence"]
        assert metadata["notes"]


def test_known_charge_move_returns_metadata() -> None:
    repo = ChargeMoveRepository()

    metadata = repo.get_charge_move_metadata("solar-beam")

    assert metadata is not None
    assert metadata["is_charge_move"] is True
    assert metadata["power_herb_eligible"] is True


def test_known_charge_move_returns_charge_and_power_herb_eligible() -> None:
    repo = ChargeMoveRepository()

    assert repo.is_charge_move("meteor-beam") is True
    assert repo.is_power_herb_eligible("meteor-beam") is True


def test_unknown_move_returns_none_and_false_safely() -> None:
    repo = ChargeMoveRepository()

    assert repo.get_charge_move_metadata("not-a-real-move") is None
    assert repo.is_charge_move("not-a-real-move") is False
    assert repo.is_power_herb_eligible("not-a-real-move") is False
    assert repo.get_charge_move_metadata(None) is None
    assert repo.is_charge_move(None) is False
    assert repo.is_power_herb_eligible(None) is False


def test_move_id_normalization_handles_case_spaces_and_underscores() -> None:
    repo = ChargeMoveRepository()

    assert normalize_move_id("Solar Beam") == "solar-beam"
    assert normalize_move_id("solar_beam") == "solar-beam"
    assert repo.get_charge_move_metadata("Solar Beam") is not None
    assert repo.get_charge_move_metadata("solar_beam") is not None


def test_charge_move_fixture_has_deferred_candidates_but_not_initial_entries() -> None:
    data = load_charge_moves()

    assert "deferred_moves" in data
    assert "fly" in data["deferred_moves"]
    assert "phantom-force" in data["deferred_moves"]
    assert "fly" not in data["moves"]
    assert "phantom-force" not in data["moves"]


def test_repository_does_not_use_description_parsing() -> None:
    source = Path("core/charge_move_repository.py").read_text(encoding="utf-8").lower()

    assert "description" not in source
    assert "effect_entries" not in source
    assert "flavor_text" not in source


def test_repository_does_not_import_llm_modules() -> None:
    tree = ast.parse(Path("core/charge_move_repository.py").read_text(encoding="utf-8"))
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert not any(module == "llm" or module.startswith("llm.") for module in imported_modules)


def test_repository_does_not_import_damage_formula_or_rolls() -> None:
    tree = ast.parse(Path("core/charge_move_repository.py").read_text(encoding="utf-8"))
    imported_modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)

    assert "advisor.damage.formula" not in imported_modules
    assert "advisor.damage.rolls" not in imported_modules


def test_fixture_json_can_be_loaded_without_helper_side_effects() -> None:
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert data["version"] == CHARGE_MOVES_VERSION

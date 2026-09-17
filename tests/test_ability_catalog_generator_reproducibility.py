"""Regression coverage for safe deterministic ability catalog regeneration."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_HISTORICAL_IMPLEMENTED_DRIFT = {
    "blaze", "defeatist", "fur-coat", "huge-power", "hustle", "ice-scales",
    "iron-fist", "mega-launcher", "minus", "multiscale", "overgrow", "plus",
    "punk-rock", "pure-power", "reckless", "shadow-shield", "sheer-force",
    "skill-link", "strong-jaw", "swarm", "technician", "torrent", "tough-claws",
    "transistor",
}


def _generator_module():
    path = _ROOT / "scripts" / "build_abilities_catalog.py"
    spec = importlib.util.spec_from_file_location("ability_catalog_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _checked_in(path: str) -> dict:
    return json.loads((_ROOT / path).read_text(encoding="utf-8"))


def test_generator_exactly_reproduces_checked_in_catalog_and_derived_categories():
    generator = _generator_module()
    generated = generator.build_catalog()
    canonical = _checked_in("data/static/abilities.json")

    assert generated == canonical
    assert generator.build_catalog() == generated
    assert generator.build_categories(generated) == _checked_in("data/static/ability_categories.json")


def test_generation_preserves_implemented_support_and_rich_metadata_without_promoting_stubs():
    generator = _generator_module()
    generated = generator.build_catalog()["abilities"]
    canonical = _checked_in("data/static/abilities.json")["abilities"]
    generated_implemented = {ability_id for ability_id, row in generated.items() if row["implemented"]}
    canonical_implemented = {ability_id for ability_id, row in canonical.items() if row["implemented"]}

    assert generated_implemented == canonical_implemented
    assert _HISTORICAL_IMPLEMENTED_DRIFT <= generated_implemented
    for ability_id in ("technician", "tough-claws", "multiscale", "shadow-shield", "skill-link", "hustle", "punk-rock"):
        assert generated[ability_id] == canonical[ability_id]

    assert generated["technician"]["category"] == "bp_modifier"
    assert generated["skill-link"]["category"] == "multihit_modifier"
    assert generated["guts"]["implemented"] is False

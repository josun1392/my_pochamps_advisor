from __future__ import annotations

import hashlib
from pathlib import Path

import advisor.canonical_charge_move_lifecycle as canonical
from advisor.canonical_charge_move_lifecycle import (
    COMMIT,
    EXPECTED_ITEMS_SHA256,
    EXPECTED_MOVES_SHA256,
    load_canonical_charge_move_lifecycle_inventory,
    resolve_canonical_charge_move_lifecycle,
)
from core.charge_move_repository import ChargeMoveRepository
from llm.advisor_direct_mechanics import evaluate_direct_damage_mechanics
from tests.test_predictive_water_gun_interval import _fixture as _direct_fixture


EXPECTED_MOVES = {
    "meteor-beam", "sky-attack", "solar-beam", "solar-blade", "fly",
    "dig", "dive", "bounce", "phantom-force", "shadow-force",
    "skull-bash", "razor-wind", "freeze-shock", "ice-burn", "geomancy",
}


def test_exact_fifteen_move_inventory_is_authenticated_once():
    inventory = load_canonical_charge_move_lifecycle_inventory()
    assert set(inventory["moves"]) == EXPECTED_MOVES
    assert len(inventory["moves"]) == len(EXPECTED_MOVES) == 15
    assert inventory["source_provenance"] == {
        "repository": "https://github.com/smogon/pokemon-showdown",
        "commit_sha": COMMIT,
        "moves_sha256": EXPECTED_MOVES_SHA256,
        "items_sha256": EXPECTED_ITEMS_SHA256,
    }
    for move_id, row in inventory["moves"].items():
        assert row["move_id"] == move_id
        assert row["charge_flag_confirmed"] is True
        assert row["charge_move_event_participation"] is True
        assert row["twoturnmove_state_usage"] is True
        assert row["existing_move_volatile_continuation"] is True
        assert row["canonical_recognition_grants_immediate_execution"] is False
        assert row["source"] == "pinned_showdown_charge_move_lifecycle_v1"
        assert row["confidence"] == "authenticated_pinned_source"


def test_unknown_ordinary_move_is_not_charge_classified():
    result = resolve_canonical_charge_move_lifecycle("tackle")
    assert result["status"] == "not_applicable"
    repo = ChargeMoveRepository()
    assert repo.get_charge_move_metadata("tackle") is None
    assert repo.is_charge_move("tackle") is False
    assert repo.immediate_execution_guard("tackle") is None


def test_weather_sensitive_solar_taxonomy_preserves_skip_and_weak_weather_metadata():
    for move_id in ("solar-beam", "solar-blade"):
        row = resolve_canonical_charge_move_lifecycle(move_id)
        assert row["status"] == "resolved"
        assert row["lifecycle_family"] == "weather_sensitive_charge_then_damage"
        assert row["execution_model"] == "charge_then_execute"
        assert row["weather_sensitive_charge_skip"] is True
        assert row["sunny_weather_skip_sources"] == ("sunnyday", "desolateland")
        assert row["weak_weather_damage_modifier_present"] is True
        assert row["terminal_effect_class"] == "damaging_move"
        assert row["canonical_recognition_grants_immediate_execution"] is False


def test_charge_turn_self_effect_family_is_distinct_without_materializing_boosts():
    meteor = resolve_canonical_charge_move_lifecycle("meteor-beam")
    skull = resolve_canonical_charge_move_lifecycle("skull-bash")
    assert meteor["lifecycle_family"] == skull["lifecycle_family"] == "charge_turn_self_effect_then_damage"
    assert meteor["charge_turn_side_effect_class"] == "special_attack_plus_one"
    assert skull["charge_turn_side_effect_class"] == "defense_plus_one"
    assert meteor["charge_turn_side_effect_timing"] == skull["charge_turn_side_effect_timing"] == "before_charge_move_event"
    assert "boost_result" not in meteor and "boost_result" not in skull


def test_semi_invulnerable_family_and_protection_bypass_markers_are_descriptive_only():
    expected = {
        "fly": "airborne", "bounce": "airborne", "dig": "underground",
        "dive": "underwater", "phantom-force": "vanished", "shadow-force": "vanished",
    }
    for move_id, state in expected.items():
        row = resolve_canonical_charge_move_lifecycle(move_id)
        assert row["lifecycle_family"] == "semi_invulnerable_charge_then_damage"
        assert row["execution_model"] == "semi_invulnerable_then_execute"
        assert row["semi_invulnerability_class"] == state
        assert row["semi_invulnerability_special_interactions_present"] is True
        assert row["canonical_recognition_grants_immediate_execution"] is False
    for move_id in ("phantom-force", "shadow-force"):
        assert resolve_canonical_charge_move_lifecycle(move_id)["protection_bypass_later_execution"] is True
    for move_id in ("fly", "bounce", "dig", "dive"):
        assert resolve_canonical_charge_move_lifecycle(move_id)["protection_bypass_later_execution"] is False


def test_ordinary_damage_and_geomancy_terminal_taxonomies_are_not_collapsed():
    for move_id in ("sky-attack", "razor-wind", "freeze-shock", "ice-burn"):
        row = resolve_canonical_charge_move_lifecycle(move_id)
        assert row["lifecycle_family"] == "ordinary_charge_then_damage"
        assert row["terminal_effect_class"] == "damaging_move"
    geomancy = resolve_canonical_charge_move_lifecycle("geomancy")
    assert geomancy["lifecycle_family"] == "charge_then_status_terminal"
    assert geomancy["execution_model"] == "other_two_turn"
    assert geomancy["terminal_effect_class"] == "self_stat_change"


def test_power_herb_is_only_an_authenticated_possible_charge_skip():
    for move_id in EXPECTED_MOVES:
        row = resolve_canonical_charge_move_lifecycle(move_id)
        assert row["power_herb_eligible"] is True
        assert row["power_herb_charge_skip_possible"] is True
        assert row["power_herb_behavior"] == "descriptive_skip_mechanism_only"
        proof = row["source_provenance"]["power_herb_block"]
        assert proof == {
            "showdown_item_id": "powerherb",
            "on_charge_move": True,
            "uses_item": True,
            "returns_false_to_skip_charge": True,
            "execution_grant": False,
        }
        assert "item_after" not in row
        assert "item_consumed" not in row


def test_default_repository_uses_canonical_source_and_preserves_guard():
    repo = ChargeMoveRepository()
    solar = repo.get_charge_move_metadata("solar-beam")
    assert solar is not None
    assert solar["source"] == "pinned_showdown_charge_move_lifecycle_v1"
    assert solar["confidence"] == "authenticated_pinned_source"
    assert solar["source"] != "manual_repo_fixture"
    guard = repo.immediate_execution_guard("solar-beam")
    assert guard == {
        "move_id": "solar-beam",
        "execution_model": "charge_then_execute",
        "reason": "two_turn_execution_unrepresented",
        "source": "pinned_showdown_charge_move_lifecycle_v1",
        "canonical_recognition_grants_immediate_execution": False,
    }


def test_direct_damage_evaluator_still_refuses_immediate_charge_execution():
    _state, _owner, _target, damage, provenance = _direct_fixture()
    damage["move"] = {
        "move_id": "solar-beam",
        "category": "special",
        "power": 120,
        "type": "grass",
    }
    result = evaluate_direct_damage_mechanics(
        damage,
        stat_provenance=provenance,
        trusted_level=50,
    )
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "two_turn_execution_unrepresented"
    assert result["damage_range"] is None


def test_malformed_internal_taxonomy_rejects_instead_of_granting_execution(monkeypatch):
    rows = {move_id: dict(row) for move_id, row in canonical._ROWS.items()}
    rows["solar-beam"]["execution_model"] = "immediate_execute"
    monkeypatch.setattr(canonical, "_ROWS", rows)
    canonical._authenticated_source.cache_clear()
    try:
        result = canonical.resolve_canonical_charge_move_lifecycle("solar-beam")
        assert result["status"] == "rejected"
        assert result["reason"] == "canonical_charge_move_taxonomy_malformed:solar-beam"
    finally:
        canonical._authenticated_source.cache_clear()


def test_source_hash_mismatch_rejects(monkeypatch, tmp_path):
    original = canonical._MOVES_PATH.read_bytes()
    tampered = tmp_path / "moves.ts"
    tampered.write_bytes(original + b"\n// tampered")
    monkeypatch.setattr(canonical, "_MOVES_PATH", tampered)
    canonical._authenticated_source.cache_clear()
    try:
        result = canonical.resolve_canonical_charge_move_lifecycle("solar-beam")
        assert result["status"] == "rejected"
        assert result["reason"] == "canonical_charge_move_moves_source_hash_mismatch"
    finally:
        canonical._authenticated_source.cache_clear()


def test_source_lifecycle_token_mismatch_rejects_after_hash_authentication(monkeypatch, tmp_path):
    original = canonical._MOVES_PATH.read_text(encoding="utf-8")
    tampered_text = original.replace(
        "attacker.addVolatile('twoturnmove', defender);",
        "attacker.addVolatile('not-two-turn', defender);",
        1,
    )
    tampered = tmp_path / "moves.ts"
    tampered.write_text(tampered_text, encoding="utf-8")
    monkeypatch.setattr(canonical, "_MOVES_PATH", tampered)
    monkeypatch.setattr(
        canonical,
        "EXPECTED_MOVES_SHA256",
        hashlib.sha256(tampered.read_bytes()).hexdigest(),
    )
    canonical._authenticated_source.cache_clear()
    try:
        result = canonical.resolve_canonical_charge_move_lifecycle("meteor-beam")
        assert result["status"] == "rejected"
        assert result["reason"].startswith("canonical_charge_move_lifecycle_token_mismatch:")
    finally:
        canonical._authenticated_source.cache_clear()

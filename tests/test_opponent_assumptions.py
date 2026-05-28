from __future__ import annotations

import pytest

from core.pokemon_stat_sample_repository import PokemonStatSampleRepository
from llm.opponent_assumptions import (
    OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K,
    build_opponent_assumptions_payload,
    validate_opponent_assumptions_payload,
)


def test_build_opponent_assumptions_payload_for_species_with_samples() -> None:
    payload = build_opponent_assumptions_payload(
        {"name_en": "garchomp"},
        PokemonStatSampleRepository(),
    )

    assert payload["mode"] == "multi_sample_assumption_v0.38"
    assert payload["available"] is True
    assert payload["scope"] == "opponent_active"
    assert payload["is_confirmed_information"] is False
    assert payload["calculation_usage"] == "context_only"

    opponent = payload["opponent_active"]
    assert opponent["species_id"] == "garchomp"
    assert opponent["known_status"] == "not_confirmed"
    assert opponent["is_user_confirmed"] is False
    assert opponent["user_confirmed_fields"] == {}
    assert opponent["observation_history"] == []
    assert opponent["update_policy"]["mode"] == "static"

    sample = opponent["possible_samples"][0]
    assert sample["sample_id"] == "garchomp_fast_physical_01"
    assert sample["species_id"] == "garchomp"
    assert sample["source"] == "sample_assumed"
    assert sample["source_type"] == "manual_estimate"
    assert sample["confidence"] == "estimated"
    assert sample["prior_probability"] is None
    assert sample["prior_probability_type"] == "not_available"
    assert sample["is_user_confirmed"] is False
    assert sample["possible_item"] is None
    assert sample["possible_stats"]["spe"] == 154
    assert "not confirmed" in " ".join(sample["limitations"]).lower()

    meta = opponent["samples_meta"]
    assert meta["total_known_archetypes"] == 2
    assert meta["included_top_k"] == 2
    assert meta["default_top_k"] == OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K
    assert meta["coverage_probability"] is None
    assert meta["coverage_probability_type"] == "not_available"
    assert meta["omitted_archetypes_note"]

    validate_opponent_assumptions_payload(payload)


def test_build_opponent_assumptions_payload_for_repo_native_species() -> None:
    payload = build_opponent_assumptions_payload(
        {"name_en": "rotom_wash"},
        PokemonStatSampleRepository(),
    )

    assert payload["available"] is True
    assert payload["calculation_usage"] == "context_only"
    assert "damage_estimate" not in payload
    assert "speed_context" not in payload

    opponent = payload["opponent_active"]
    assert opponent["species_id"] == "rotom_wash"
    assert opponent["samples_meta"]["included_top_k"] == 1

    sample = opponent["possible_samples"][0]
    assert sample["sample_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["species_id"] == "rotom-wash"
    assert sample["is_user_confirmed"] is False
    assert sample["prior_probability"] is None

    validate_opponent_assumptions_payload(payload)


def test_build_opponent_assumptions_payload_unknown_species_is_unavailable() -> None:
    payload = build_opponent_assumptions_payload(
        {"name_en": "missingno"},
        PokemonStatSampleRepository(),
    )

    assert payload["available"] is False
    assert payload["reason"] == "no_samples_for_species"
    assert payload["is_confirmed_information"] is False
    assert payload["calculation_usage"] == "context_only"
    assert "Do not invent opponent samples." in payload["limitations"]
    assert payload["opponent_active"]["possible_samples"] == []

    validate_opponent_assumptions_payload(payload)


def test_build_opponent_assumptions_payload_missing_opponent_is_unavailable() -> None:
    payload = build_opponent_assumptions_payload(None, PokemonStatSampleRepository())

    assert payload["available"] is False
    assert payload["reason"] == "opponent_active_missing"
    assert payload["is_confirmed_information"] is False
    assert payload["calculation_usage"] == "context_only"
    assert "Do not invent opponent samples." in payload["limitations"]

    validate_opponent_assumptions_payload(payload)


def test_build_opponent_assumptions_payload_repository_failure_is_unavailable() -> None:
    class BrokenRepository:
        def list_samples_for_species(self, species_id: str) -> list[dict]:
            del species_id
            raise RuntimeError("fixture unavailable")

    payload = build_opponent_assumptions_payload(
        {"name_en": "garchomp"},
        BrokenRepository(),  # type: ignore[arg-type]
    )

    assert payload["available"] is False
    assert payload["reason"] == "repository_unavailable"
    assert payload["is_confirmed_information"] is False
    assert payload["calculation_usage"] == "context_only"

    validate_opponent_assumptions_payload(payload)


def test_validate_opponent_assumptions_rejects_confirmed_possible_sample() -> None:
    payload = build_opponent_assumptions_payload(
        {"name_en": "garchomp"},
        PokemonStatSampleRepository(),
    )
    payload["opponent_active"]["possible_samples"][0]["is_user_confirmed"] = True

    with pytest.raises(ValueError, match="must not be user-confirmed"):
        validate_opponent_assumptions_payload(payload)


def test_validate_opponent_assumptions_rejects_numeric_prior_in_v038() -> None:
    payload = build_opponent_assumptions_payload(
        {"name_en": "garchomp"},
        PokemonStatSampleRepository(),
    )
    payload["opponent_active"]["possible_samples"][0]["prior_probability"] = 0.5

    with pytest.raises(ValueError, match="null prior_probability"):
        validate_opponent_assumptions_payload(payload)

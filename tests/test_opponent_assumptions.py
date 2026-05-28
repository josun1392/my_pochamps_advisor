from __future__ import annotations

import pytest

from core.pokemon_stat_sample_repository import PokemonStatSampleRepository
from llm.opponent_assumptions import (
    OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K,
    build_opponent_assumptions_payload,
    build_opponent_assumptions_debug_summary,
    build_opponent_assumptions_debug_summary_from_assumptions,
    format_opponent_assumptions_debug_json,
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
    assert "possible_stats" not in sample
    assert "stats" not in sample
    assert "sp_distribution" not in sample
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
    assert sample["role"] == "defensive_pivot"
    assert sample["archetype_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["possible_items"] == ["leftovers", "sitrus-berry"]
    assert sample["calculation_usage"] == "context_only"
    assert sample["is_user_confirmed"] is False
    assert sample["prior_probability"] is None
    assert "possible_stats" not in sample
    assert "stats" not in sample
    assert "sp_distribution" not in sample
    assert "source_url" not in sample
    assert "source_note" not in sample
    assert "reviewer_notes" not in sample

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


def test_build_debug_summary_for_available_opponent_assumptions() -> None:
    assumptions = build_opponent_assumptions_payload(
        {"name_en": "rotom_wash"},
        PokemonStatSampleRepository(),
    )

    summary = build_opponent_assumptions_debug_summary_from_assumptions(assumptions)

    assert summary["opponent_species_id"] == "rotom_wash"
    assert summary["opponent_assumptions_available"] is True
    assert summary["reason"] is None
    assert summary["calculation_usage"] == "context_only"
    assert summary["is_confirmed_information"] is False
    assert summary["possible_sample_count"] == 1
    assert summary["included_top_k"] == 1

    sample = summary["possible_samples"][0]
    assert sample["sample_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["species_id"] == "rotom-wash"
    assert sample["role"] == "defensive_pivot"
    assert sample["archetype_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["possible_items"] == ["leftovers", "sitrus-berry"]
    assert sample["confidence"] == "estimated"
    assert sample["is_user_confirmed"] is False
    assert sample["used_for_damage"] is False
    assert sample["used_for_speed"] is False

    guardrails = summary["guardrails"]
    assert guardrails["context_only"] is True
    assert guardrails["not_confirmed"] is True
    assert guardrails["not_damage_input"] is True
    assert guardrails["not_speed_input"] is True
    assert guardrails["not_final_turn_order"] is True


def test_build_debug_summary_from_full_payload_uses_only_opponent_assumptions() -> None:
    assumptions = build_opponent_assumptions_payload(
        {"name_en": "garchomp"},
        PokemonStatSampleRepository(),
    )
    full_payload = {
        "opponent_assumptions": assumptions,
        "pokemon": {"my_active": {"name_en": "charizard"}},
        "secret_api_key": "must-not-leak",
        "env": {"TOKEN": "must-not-leak"},
    }

    summary = build_opponent_assumptions_debug_summary(full_payload)
    rendered = format_opponent_assumptions_debug_json(summary)

    assert summary["opponent_assumptions_available"] is True
    assert summary["possible_sample_count"] == 2
    assert "pokemon" not in summary
    assert "secret_api_key" not in summary
    assert "env" not in summary
    assert "must-not-leak" not in rendered
    assert "possible_stats" not in rendered
    assert '"stats"' not in rendered
    assert "sp_distribution" not in rendered


def test_build_debug_summary_for_unavailable_opponent_assumptions() -> None:
    assumptions = build_opponent_assumptions_payload(
        {"name_en": "missingno"},
        PokemonStatSampleRepository(),
    )

    summary = build_opponent_assumptions_debug_summary_from_assumptions(assumptions)

    assert summary["opponent_species_id"] == "missingno"
    assert summary["opponent_assumptions_available"] is False
    assert summary["reason"] == "no_samples_for_species"
    assert summary["calculation_usage"] == "context_only"
    assert summary["is_confirmed_information"] is False
    assert summary["possible_sample_count"] == 0
    assert summary["included_top_k"] == 0
    assert summary["possible_samples"] == []
    assert summary["guardrails"]["context_only"] is True
    assert summary["guardrails"]["not_damage_input"] is True
    assert summary["guardrails"]["not_speed_input"] is True


def test_build_debug_summary_for_missing_assumptions_is_safe() -> None:
    summary = build_opponent_assumptions_debug_summary({})

    assert summary["opponent_species_id"] == "unknown"
    assert summary["opponent_assumptions_available"] is False
    assert summary["reason"] == "opponent_assumptions_missing"
    assert summary["calculation_usage"] == "context_only"
    assert summary["possible_samples"] == []


def test_debug_summary_preserves_optional_sample_fields_without_full_stats_dump() -> None:
    assumptions = {
        "available": True,
        "calculation_usage": "context_only",
        "is_confirmed_information": False,
        "opponent_active": {
            "species_id": "garchomp",
            "possible_samples": [
                {
                    "sample_id": "garchomp_fast_physical_debug",
                    "species_id": "garchomp",
                    "role": "fast_physical",
                    "archetype_id": "fast_physical",
                    "confidence": "estimated",
                    "is_user_confirmed": False,
                    "possible_items": ["choice-scarf"],
                    "possible_stats": {"spe": 154},
                    "source_metadata": {"source_url": "example"},
                }
            ],
            "samples_meta": {"included_top_k": 1},
        },
    }

    summary = build_opponent_assumptions_debug_summary_from_assumptions(assumptions)
    sample = summary["possible_samples"][0]
    rendered = format_opponent_assumptions_debug_json(summary)

    assert sample == {
        "sample_id": "garchomp_fast_physical_debug",
        "species_id": "garchomp",
        "role": "fast_physical",
        "archetype_id": "fast_physical",
        "confidence": "estimated",
        "is_user_confirmed": False,
        "possible_items": ["choice-scarf"],
        "used_for_damage": False,
        "used_for_speed": False,
    }
    assert "possible_stats" not in rendered
    assert "source_metadata" not in rendered


def test_possible_sample_metadata_is_minimal_and_context_only() -> None:
    payload = build_opponent_assumptions_payload(
        {"name_en": "rotom_wash"},
        PokemonStatSampleRepository(),
    )
    sample = payload["opponent_active"]["possible_samples"][0]

    assert sample["role"] == "defensive_pivot"
    assert sample["archetype_id"] == "rotom_wash_defensive_pivot_repo_v42"
    assert sample["possible_items"] == ["leftovers", "sitrus-berry"]
    assert all(isinstance(item_id, str) for item_id in sample["possible_items"])
    assert sample["confidence"] == "estimated"
    assert sample["is_user_confirmed"] is False
    assert sample["calculation_usage"] == "context_only"
    assert "possible_stats" not in sample
    assert "stats" not in sample
    assert "sp_distribution" not in sample
    assert "source_url" not in sample
    assert "source_note" not in sample
    assert "reviewer_notes" not in sample


def test_format_opponent_assumptions_debug_json_is_pretty_and_copy_ready() -> None:
    summary = {
        "opponent_species_id": "rotom-wash",
        "opponent_assumptions_available": True,
        "guardrails": {"context_only": True},
    }

    rendered = format_opponent_assumptions_debug_json(summary)

    assert rendered.startswith("{\n")
    assert '  "guardrails": {' in rendered
    assert '"opponent_species_id": "rotom-wash"' in rendered

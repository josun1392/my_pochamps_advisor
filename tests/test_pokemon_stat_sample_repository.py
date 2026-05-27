from __future__ import annotations

import json

import pytest

from core.pokemon_stat_sample_repository import (
    ALLOWED_SOURCE_TYPES,
    REQUIRED_STAT_KEYS,
    SAMPLE_ASSUMED,
    PokemonStatSampleRepository,
    load_samples,
    normalize_species_id,
    validate_sample_schema,
)


def test_fixture_loads_with_schema_version_and_format() -> None:
    data = load_samples()

    assert data["schema_version"] == "0.1"
    assert data["format"] == "pokemon_champions"
    assert isinstance(data["samples"], dict)


def test_fixture_contains_required_sentinel_species() -> None:
    data = load_samples()

    assert {"garchomp", "charizard", "corviknight"} <= set(data["samples"])
    assert all(data["samples"][species_id] for species_id in ("garchomp", "charizard", "corviknight"))


def test_list_species_returns_normalized_species_ids() -> None:
    repo = PokemonStatSampleRepository()

    assert repo.list_species() == ["charizard", "corviknight", "garchomp"]


def test_list_samples_for_species_supports_normalization() -> None:
    repo = PokemonStatSampleRepository()

    canonical = repo.list_samples_for_species("garchomp")
    assert repo.list_samples_for_species("Garchomp") == canonical
    assert repo.list_samples_for_species(" garchomp ") == canonical
    assert repo.list_samples_for_species("GAR CHOMP") == []
    assert canonical[0]["sample_id"] == "garchomp_fast_physical_01"


def test_normalize_species_id() -> None:
    assert normalize_species_id("Garchomp") == "garchomp"
    assert normalize_species_id(" garchomp ") == "garchomp"
    assert normalize_species_id("Mr Rime") == "mr-rime"
    assert normalize_species_id("Farfetch'd") == "farfetchd"


def test_get_sample_by_sample_id_and_species() -> None:
    repo = PokemonStatSampleRepository()

    sample = repo.get_sample("garchomp_fast_physical_01")
    species_sample = repo.get_sample("garchomp_fast_physical_01", species_id="Garchomp")

    assert sample is not None
    assert species_sample == sample
    assert sample["species_id"] == "garchomp"
    assert sample["label_en"] == "Fast physical sample"


def test_unknown_species_and_sample_return_safe_empty_results() -> None:
    repo = PokemonStatSampleRepository()

    assert repo.list_samples_for_species("missingno") == []
    assert repo.get_sample("missing_sample_01") is None
    assert repo.get_sample("garchomp_fast_physical_01", species_id="charizard") is None
    assert repo.get_sample("") is None


def test_samples_are_sample_assumed_and_not_user_confirmed() -> None:
    repo = PokemonStatSampleRepository()

    for species_id in repo.list_species():
        for sample in repo.list_samples_for_species(species_id):
            assert sample["status"] == SAMPLE_ASSUMED
            assert sample["is_user_confirmed"] is False
            assert sample["confidence"] == "estimated"


def test_samples_have_required_source_metadata() -> None:
    repo = PokemonStatSampleRepository()
    required_fields = {
        "source_type",
        "source_name",
        "source_url",
        "source_note",
        "regulation",
        "season",
        "is_official",
        "confidence",
        "confidence_reason",
        "created_by",
        "last_reviewed",
    }

    for species_id in repo.list_species():
        for sample in repo.list_samples_for_species(species_id):
            assert required_fields <= set(sample)
            assert sample["source_type"] in ALLOWED_SOURCE_TYPES
            assert sample["source_name"] == "T1 curated sentinel sample"
            assert sample["source_url"] is None
            assert sample["regulation"] == "M-A"
            assert sample["season"] is None
            assert sample["is_official"] is False
            assert sample["confidence_reason"]
            assert sample["created_by"] == "project"
            assert sample["last_reviewed"] == "2026-05-27"


def test_sentinel_samples_are_manual_estimates_not_official_sources() -> None:
    repo = PokemonStatSampleRepository()

    for species_id in repo.list_species():
        for sample in repo.list_samples_for_species(species_id):
            assert sample["source_type"] == "manual_estimate"
            assert sample["is_official"] is False
            assert sample["confidence"] == "estimated"
            assert "not derived from confirmed opponent stats" in sample["confidence_reason"].lower()


def test_samples_have_required_stats_and_sp_distribution() -> None:
    repo = PokemonStatSampleRepository()

    for species_id in repo.list_species():
        for sample in repo.list_samples_for_species(species_id):
            assert set(REQUIRED_STAT_KEYS) <= set(sample["stats"])
            assert set(REQUIRED_STAT_KEYS) <= set(sample["assumptions"]["sp_distribution"])
            assert all(isinstance(sample["stats"][key], int) and sample["stats"][key] > 0 for key in REQUIRED_STAT_KEYS)
            assert all(
                isinstance(sample["assumptions"]["sp_distribution"][key], int)
                and sample["assumptions"]["sp_distribution"][key] >= 0
                for key in REQUIRED_STAT_KEYS
            )


def test_samples_limitations_state_not_user_confirmed() -> None:
    repo = PokemonStatSampleRepository()

    for species_id in repo.list_species():
        for sample in repo.list_samples_for_species(species_id):
            limitations = " ".join(sample["limitations"]).lower()
            assert "not user-confirmed" in limitations
            assert "exact opponent stats" in limitations
            assert "final battle truth" in limitations


def test_repository_returns_copies() -> None:
    repo = PokemonStatSampleRepository()

    sample = repo.get_sample("garchomp_fast_physical_01")
    assert sample is not None
    sample["stats"]["spe"] = 1

    fresh_sample = repo.get_sample("garchomp_fast_physical_01")
    assert fresh_sample is not None
    assert fresh_sample["stats"]["spe"] == 154


def test_invalid_fixture_missing_required_fields_raises(tmp_path) -> None:
    fixture_path = tmp_path / "bad_stat_samples.json"
    fixture_path.write_text(json.dumps({"format": "pokemon_champions"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_samples(fixture_path)


def test_validate_sample_schema_rejects_user_confirmed_sample() -> None:
    data = load_samples()
    copied = json.loads(json.dumps(data))
    copied["samples"]["garchomp"][0]["is_user_confirmed"] = True

    with pytest.raises(ValueError, match="must not be user-confirmed"):
        validate_sample_schema(copied)


def test_validate_sample_schema_rejects_missing_stat_key() -> None:
    data = load_samples()
    copied = json.loads(json.dumps(data))
    del copied["samples"]["garchomp"][0]["stats"]["spe"]

    with pytest.raises(ValueError, match="missing stat keys"):
        validate_sample_schema(copied)


def test_validate_sample_schema_rejects_missing_sp_distribution_key() -> None:
    data = load_samples()
    copied = json.loads(json.dumps(data))
    del copied["samples"]["garchomp"][0]["assumptions"]["sp_distribution"]["spe"]

    with pytest.raises(ValueError, match="missing stat keys"):
        validate_sample_schema(copied)


def test_validate_sample_schema_rejects_invalid_source_type() -> None:
    data = load_samples()
    copied = json.loads(json.dumps(data))
    copied["samples"]["garchomp"][0]["source_type"] = "forum_guess"

    with pytest.raises(ValueError, match="unsupported source_type"):
        validate_sample_schema(copied)


def test_validate_sample_schema_allows_null_source_url() -> None:
    data = load_samples()

    validate_sample_schema(data)
    for samples in data["samples"].values():
        for sample in samples:
            assert sample["source_url"] is None


def test_validate_sample_schema_rejects_non_boolean_is_official() -> None:
    data = load_samples()
    copied = json.loads(json.dumps(data))
    copied["samples"]["garchomp"][0]["is_official"] = "false"

    with pytest.raises(ValueError, match="is_official must be a boolean"):
        validate_sample_schema(copied)

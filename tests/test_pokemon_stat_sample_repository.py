from __future__ import annotations

import json
from pathlib import Path

import pytest

from advisor.damage.stats import StatBlock, StatInputs, final_stats
from core.champions_item_repository import ChampionsItemRepository
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

    required_species = {
        "archaludon",
        "charizard",
        "corviknight",
        "dragonite",
        "garchomp",
        "rotom-wash",
        "tyranitar",
    }
    assert required_species <= set(data["samples"])
    assert all(data["samples"][species_id] for species_id in required_species)


def test_list_species_returns_normalized_species_ids() -> None:
    repo = PokemonStatSampleRepository()

    assert repo.list_species() == [
        "archaludon",
        "charizard",
        "corviknight",
        "dragonite",
        "garchomp",
        "rotom-wash",
        "tyranitar",
    ]


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
            assert sample["last_reviewed"] in {"2026-05-27", "2026-05-28"}


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


def test_repo_native_v42_samples_have_required_fields() -> None:
    repo = PokemonStatSampleRepository()
    samples = _repo_native_samples(repo)

    assert 5 <= len(samples) <= 7
    required_fields = {
        "stats_truth_source",
        "stats_calculator",
        "calculation_usage",
        "prior_probability",
        "prior_probability_type",
        "coverage_probability",
        "coverage_probability_type",
        "archetype_id",
        "archetype_tags",
        "role",
        "stat_focus",
        "possible_items",
        "possible_moves",
        "possible_items_review_status",
        "risk_notes",
        "reviewer_notes",
    }
    for sample in samples:
        assert required_fields <= set(sample)
        assert sample["status"] == SAMPLE_ASSUMED
        assert sample["is_user_confirmed"] is False
        assert sample["source_type"] == "manual_estimate"
        assert sample["confidence"] == "estimated"
        assert sample["calculation_usage"] == "context_only"
        assert sample["prior_probability"] is None
        assert sample["prior_probability_type"] == "not_available"
        assert sample["coverage_probability"] is None
        assert sample["coverage_probability_type"] == "not_available"
        assert sample["stats_truth_source"] == "repo_calculator_from_sp_distribution"
        assert sample["stats_calculator"] == "advisor.damage.stats.final_stats"
        assert isinstance(sample["archetype_tags"], list) and sample["archetype_tags"]
        assert isinstance(sample["possible_items"], list)
        assert isinstance(sample["possible_moves"], list)


def test_repo_native_v42_species_ids_match_species_keys() -> None:
    repo = PokemonStatSampleRepository()

    for species_id in repo.list_species():
        assert normalize_species_id(species_id) == species_id
        for sample in repo.list_samples_for_species(species_id):
            assert sample["species_id"] == species_id

    assert repo.list_samples_for_species("rotom_wash") == repo.list_samples_for_species("rotom-wash")


def test_repo_native_v42_samples_validate_sp_caps_and_totals() -> None:
    repo = PokemonStatSampleRepository()

    for sample in _repo_native_samples(repo):
        sp_distribution = sample["assumptions"]["sp_distribution"]
        assert set(REQUIRED_STAT_KEYS) <= set(sp_distribution)
        assert all(0 <= sp_distribution[key] <= 32 for key in REQUIRED_STAT_KEYS)
        assert sum(sp_distribution[key] for key in REQUIRED_STAT_KEYS) <= 66


def test_repo_native_v42_stats_match_repo_calculator() -> None:
    repo = PokemonStatSampleRepository()

    for sample in _repo_native_samples(repo):
        assert sample["stats"] == _calculate_repo_native_stats(sample)


def test_repo_native_v42_possible_items_are_champions_legal_only() -> None:
    repo = PokemonStatSampleRepository()
    item_repo = ChampionsItemRepository()
    excluded_items = {
        "choice-specs",
        "choice-band",
        "life-orb",
        "heavy-duty-boots",
        "loaded-dice",
        "weakness-policy",
        "assault-vest",
        "throat-spray",
        "power-herb",
        "covert-cloak",
        "air-balloon",
        "black-sludge",
        "rocky-helmet",
    }

    for sample in _repo_native_samples(repo):
        assert all(isinstance(item_id, str) for item_id in sample["possible_items"])
        assert not excluded_items & set(sample["possible_items"])
        assert sample["possible_items_review_status"] == "legal_only"
        for item_id in sample["possible_items"]:
            assert item_repo.is_legal_item(item_id) is True


def test_repo_native_v42_limitations_include_context_only_caveat() -> None:
    repo = PokemonStatSampleRepository()

    for sample in _repo_native_samples(repo):
        limitations = " ".join(sample["limitations"]).lower()
        assert "not user-confirmed" in limitations
        assert "final battle truth" in limitations
        assert "context-only" in limitations


def test_validate_sample_schema_rejects_repo_native_non_context_only_sample() -> None:
    data = load_samples()
    copied = json.loads(json.dumps(data))
    copied["samples"]["garchomp"][1]["calculation_usage"] = "damage_input"

    with pytest.raises(ValueError, match="calculation_usage must be context_only"):
        validate_sample_schema(copied)


def _repo_native_samples(repo: PokemonStatSampleRepository) -> list[dict]:
    samples: list[dict] = []
    for species_id in repo.list_species():
        samples.extend(
            sample
            for sample in repo.list_samples_for_species(species_id)
            if sample.get("stats_truth_source") == "repo_calculator_from_sp_distribution"
        )
    return samples


def _calculate_repo_native_stats(sample: dict) -> dict[str, int]:
    species_id = sample["species_id"]
    cache_path = Path("data/cache/pokemon") / f"{species_id}.json"
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    base_stats = raw["base_stats"]
    sp_distribution = sample["assumptions"]["sp_distribution"]
    nature = sample["assumptions"]["nature"]

    stats = final_stats(
        StatInputs(
            base=StatBlock(
                hp=base_stats["hp"],
                atk=base_stats["atk"],
                def_=base_stats["def"],
                spa=base_stats["spa"],
                spd=base_stats["spd"],
                spe=base_stats["spe"],
            ),
            evs=StatBlock(
                hp=sp_distribution["hp"],
                atk=sp_distribution["atk"],
                def_=sp_distribution["def"],
                spa=sp_distribution["spa"],
                spd=sp_distribution["spd"],
                spe=sp_distribution["spe"],
            ),
            ivs=StatBlock(hp=31, atk=31, def_=31, spa=31, spd=31, spe=31),
            nature_plus=nature["plus"],
            nature_minus=nature["minus"],
            level=sample["assumptions"]["level"],
            rule_set="champions",
            species=species_id,
        )
    )
    return {
        "hp": stats.hp,
        "atk": stats.atk,
        "def": stats.def_,
        "spa": stats.spa,
        "spd": stats.spd,
        "spe": stats.spe,
    }

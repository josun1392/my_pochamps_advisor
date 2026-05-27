from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_POKEMON_STAT_SAMPLES_PATH = Path("data/static/pokemon_stat_samples.json")
REQUIRED_STAT_KEYS = ("hp", "atk", "def", "spa", "spd", "spe")
SAMPLE_ASSUMED = "sample_assumed"
ALLOWED_SOURCE_TYPES = {
    "manual_estimate",
    "usage_based_estimate",
    "team_article_manual_extract",
    "calculator_derived",
    "official_or_replica_team",
    "unknown",
}


def load_samples(path: Path | None = None) -> dict[str, Any]:
    fixture_path = path or DEFAULT_POKEMON_STAT_SAMPLES_PATH
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    validate_sample_schema(data)
    return data


def validate_sample_schema(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Pokemon stat samples fixture must be a JSON object.")
    required_top_level = {"schema_version", "format", "samples"}
    missing = sorted(required_top_level - set(data))
    if missing:
        raise ValueError(f"Pokemon stat samples fixture missing fields: {missing}")
    if data["schema_version"] != "0.1":
        raise ValueError("Pokemon stat samples fixture schema_version must be 0.1.")
    if data["format"] != "pokemon_champions":
        raise ValueError("Pokemon stat samples fixture format must be pokemon_champions.")
    samples = data["samples"]
    if not isinstance(samples, dict):
        raise ValueError("Pokemon stat samples fixture samples field must be an object.")

    seen_sample_ids: set[str] = set()
    for species_id, species_samples in samples.items():
        normalized_species_id = normalize_species_id(species_id)
        if normalized_species_id != species_id:
            raise ValueError(f"Pokemon stat sample species id must be normalized: {species_id}")
        if not isinstance(species_samples, list) or not species_samples:
            raise ValueError(f"Pokemon stat sample species {species_id} must have a non-empty sample list.")
        for sample in species_samples:
            _validate_sample(sample, species_id=species_id, seen_sample_ids=seen_sample_ids)


class PokemonStatSampleRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_POKEMON_STAT_SAMPLES_PATH
        self.data = load_samples(self.path)
        self._samples_by_species = self._index_by_species(self.data["samples"])
        self._samples_by_id = self._index_by_sample_id(self._samples_by_species)

    @property
    def schema_version(self) -> str:
        return str(self.data["schema_version"])

    @property
    def format(self) -> str:
        return str(self.data["format"])

    def list_species(self) -> list[str]:
        return sorted(self._samples_by_species)

    def list_samples_for_species(self, species_id: str) -> list[dict[str, Any]]:
        normalized = normalize_species_id(species_id)
        return [deepcopy(sample) for sample in self._samples_by_species.get(normalized, [])]

    def get_sample(self, sample_id: str, *, species_id: str | None = None) -> dict[str, Any] | None:
        if not isinstance(sample_id, str) or not sample_id.strip():
            return None
        normalized_sample_id = sample_id.strip()
        if species_id is not None:
            normalized_species_id = normalize_species_id(species_id)
            for sample in self._samples_by_species.get(normalized_species_id, []):
                if sample["sample_id"] == normalized_sample_id:
                    return deepcopy(sample)
            return None
        sample = self._samples_by_id.get(normalized_sample_id)
        return deepcopy(sample) if sample is not None else None

    @staticmethod
    def _index_by_species(samples: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        indexed: dict[str, list[dict[str, Any]]] = {}
        for species_id, species_samples in samples.items():
            if not isinstance(species_samples, list):
                continue
            indexed[species_id] = [deepcopy(sample) for sample in species_samples if isinstance(sample, dict)]
        return indexed

    @staticmethod
    def _index_by_sample_id(samples_by_species: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for species_samples in samples_by_species.values():
            for sample in species_samples:
                sample_id = sample.get("sample_id")
                if isinstance(sample_id, str) and sample_id:
                    indexed[sample_id] = sample
        return indexed


def normalize_species_id(species_id: str) -> str:
    return (
        species_id.strip()
        .lower()
        .replace("'", "")
        .replace("\u2019", "")
        .replace("_", "-")
        .replace(" ", "-")
    )


def _validate_sample(
    sample: Any,
    *,
    species_id: str,
    seen_sample_ids: set[str],
) -> None:
    if not isinstance(sample, dict):
        raise ValueError(f"Pokemon stat sample for {species_id} contains a non-object sample.")
    required = {
        "sample_id",
        "species_id",
        "label_en",
        "label_ko",
        "source",
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
        "status",
        "is_user_confirmed",
        "stats",
        "assumptions",
        "limitations",
    }
    missing = sorted(required - set(sample))
    if missing:
        sample_id = sample.get("sample_id", "<missing sample_id>")
        raise ValueError(f"Pokemon stat sample {sample_id} missing fields: {missing}")

    sample_id = _required_string(sample, "sample_id")
    if sample_id in seen_sample_ids:
        raise ValueError(f"Pokemon stat sample id is duplicated: {sample_id}")
    seen_sample_ids.add(sample_id)

    sample_species_id = normalize_species_id(_required_string(sample, "species_id"))
    if sample_species_id != species_id:
        raise ValueError(f"Pokemon stat sample {sample_id} species_id does not match {species_id}.")
    if sample["status"] != SAMPLE_ASSUMED:
        raise ValueError(f"Pokemon stat sample {sample_id} must have status sample_assumed.")
    if sample["is_user_confirmed"] is not False:
        raise ValueError(f"Pokemon stat sample {sample_id} must not be user-confirmed.")
    source_type = _required_string(sample, "source_type")
    if source_type not in ALLOWED_SOURCE_TYPES:
        raise ValueError(f"Pokemon stat sample {sample_id} has unsupported source_type: {source_type}")
    _required_string(sample, "source_name")
    source_url = sample.get("source_url")
    if source_url is not None and not isinstance(source_url, str):
        raise ValueError(f"Pokemon stat sample {sample_id} source_url must be a string or null.")
    _required_string(sample, "regulation")
    if not isinstance(sample["is_official"], bool):
        raise ValueError(f"Pokemon stat sample {sample_id} is_official must be a boolean.")
    if sample["confidence"] != "estimated":
        raise ValueError(f"Pokemon stat sample {sample_id} confidence must be estimated.")
    _required_string(sample, "confidence_reason")
    _validate_required_int_stats(sample["stats"], sample_id=sample_id, field_name="stats")

    assumptions = sample["assumptions"]
    if not isinstance(assumptions, dict):
        raise ValueError(f"Pokemon stat sample {sample_id} assumptions must be an object.")
    _validate_required_int_stats(
        assumptions.get("sp_distribution"),
        sample_id=sample_id,
        field_name="sp_distribution",
        allow_zero=True,
    )

    limitations = sample["limitations"]
    if not isinstance(limitations, list) or not limitations or not all(isinstance(item, str) for item in limitations):
        raise ValueError(f"Pokemon stat sample {sample_id} limitations must be a string list.")
    if not any("not user-confirmed" in limitation.lower() for limitation in limitations):
        raise ValueError(f"Pokemon stat sample {sample_id} must state that it is not user-confirmed.")


def _validate_required_int_stats(
    value: Any,
    *,
    sample_id: str,
    field_name: str,
    allow_zero: bool = False,
) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"Pokemon stat sample {sample_id} {field_name} must be an object.")
    missing = sorted(set(REQUIRED_STAT_KEYS) - set(value))
    if missing:
        raise ValueError(f"Pokemon stat sample {sample_id} {field_name} missing stat keys: {missing}")
    for key in REQUIRED_STAT_KEYS:
        stat_value = value[key]
        if not isinstance(stat_value, int) or isinstance(stat_value, bool):
            raise ValueError(f"Pokemon stat sample {sample_id} {field_name}.{key} must be an integer.")
        if allow_zero:
            if stat_value < 0:
                raise ValueError(f"Pokemon stat sample {sample_id} {field_name}.{key} must be non-negative.")
        elif stat_value < 1:
            raise ValueError(f"Pokemon stat sample {sample_id} {field_name}.{key} must be positive.")


def _required_string(sample: dict[str, Any], key: str) -> str:
    value = sample.get(key)
    if not isinstance(value, str) or not value.strip():
        sample_id = sample.get("sample_id", "<missing sample_id>")
        raise ValueError(f"Pokemon stat sample {sample_id} field {key} must be a non-empty string.")
    return value.strip()

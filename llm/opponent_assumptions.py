from __future__ import annotations

import json
from typing import Any

from core.pokemon_stat_sample_repository import PokemonStatSampleRepository


OPPONENT_ASSUMPTIONS_MODE = "multi_sample_assumption_v0.38"
OPPONENT_ASSUMPTIONS_SCHEMA_VERSION = "opponent_assumptions_v0.47"
OPPONENT_ASSUMPTIONS_METADATA_VERSION = "minimal_metadata_v1"
OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K = 3
OPPONENT_ASSUMPTIONS_PAYLOAD_FEATURES = {
    "possible_samples": True,
    "minimal_metadata": True,
    "debug_summary_supported": True,
    "full_stats_excluded": True,
    "damage_speed_integration": False,
}
OPPONENT_ASSUMPTIONS_LIMITATIONS = [
    "Opponent samples are assumptions, not confirmed sets.",
    "Samples are not used directly for damage or speed calculations in this version.",
    "User-confirmed fields override possible sample assumptions.",
]
OPPONENT_ASSUMPTIONS_UNAVAILABLE_LIMITATIONS = {
    "no_samples_for_species": [
        "No curated opponent sample is available for this species.",
        "Do not invent opponent samples.",
    ],
    "opponent_active_missing": [
        "No opponent active Pokemon is available for sample lookup.",
        "Do not invent opponent samples.",
    ],
    "repository_unavailable": [
        "Opponent sample repository is unavailable.",
        "Do not invent opponent samples.",
    ],
}
OPPONENT_ASSUMPTIONS_DEBUG_GUARDRAILS = {
    "not_confirmed": True,
    "not_damage_input": True,
    "not_speed_input": True,
    "not_final_turn_order": True,
    "context_only": True,
}


def build_opponent_assumptions_payload(
    opponent_active: dict[str, Any] | None,
    repository: PokemonStatSampleRepository | None = None,
    *,
    top_k: int = OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K,
) -> dict[str, Any]:
    if not isinstance(opponent_active, dict):
        return _unavailable_payload(reason="opponent_active_missing")

    species_id = opponent_active.get("name_en") or opponent_active.get("species_id")
    if not isinstance(species_id, str) or not species_id.strip():
        return _unavailable_payload(reason="opponent_active_missing")

    try:
        sample_repository = repository or PokemonStatSampleRepository()
        all_samples = sample_repository.list_samples_for_species(species_id)
    except Exception:
        return _unavailable_payload(reason="repository_unavailable")

    if not all_samples:
        return _unavailable_payload(reason="no_samples_for_species", species_id=species_id)

    selected_samples = select_possible_samples(all_samples, top_k=top_k)
    possible_samples = [_possible_sample_payload(sample) for sample in selected_samples]
    return {
        "mode": OPPONENT_ASSUMPTIONS_MODE,
        "schema_version": OPPONENT_ASSUMPTIONS_SCHEMA_VERSION,
        "metadata_version": OPPONENT_ASSUMPTIONS_METADATA_VERSION,
        "available": True,
        "scope": "opponent_active",
        "is_confirmed_information": False,
        "calculation_usage": "context_only",
        "payload_features": dict(OPPONENT_ASSUMPTIONS_PAYLOAD_FEATURES),
        "opponent_active": {
            "species_id": str(species_id).strip(),
            "known_status": "not_confirmed",
            "is_user_confirmed": False,
            "user_confirmed_fields": {},
            "possible_samples": possible_samples,
            "samples_meta": build_samples_meta(
                selected_samples,
                total_known_archetypes=len(all_samples),
                top_k=top_k,
            ),
            "observation_history": [],
            "update_policy": {
                "version": "0.38.0",
                "mode": "static",
                "note": "No observation-based updates are implemented.",
            },
        },
        "limitations": list(OPPONENT_ASSUMPTIONS_LIMITATIONS),
    }


def select_possible_samples(samples: list[dict[str, Any]], *, top_k: int = OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K) -> list[dict[str, Any]]:
    safe_top_k = max(0, int(top_k))
    return [dict(sample) for sample in samples[:safe_top_k]]


def build_samples_meta(
    samples: list[dict[str, Any]],
    *,
    total_known_archetypes: int,
    top_k: int = OPPONENT_ASSUMPTIONS_DEFAULT_TOP_K,
) -> dict[str, Any]:
    return {
        "total_known_archetypes": total_known_archetypes,
        "included_top_k": len(samples),
        "default_top_k": top_k,
        "coverage_probability": None,
        "coverage_probability_type": "not_available",
        "omitted_archetypes_note": "Only manually curated sentinel samples are available in v0.38.",
    }


def validate_opponent_assumptions_payload(payload: dict[str, Any]) -> None:
    if payload.get("mode") != OPPONENT_ASSUMPTIONS_MODE:
        raise ValueError("Opponent assumptions payload mode is unsupported.")
    if payload.get("is_confirmed_information") is not False:
        raise ValueError("Opponent assumptions must not be confirmed information.")
    if payload.get("calculation_usage") != "context_only":
        raise ValueError("Opponent assumptions calculation_usage must be context_only.")
    if payload.get("available") is False:
        if payload.get("reason") not in {
            "no_samples_for_species",
            "opponent_active_missing",
            "repository_unavailable",
        }:
            raise ValueError("Opponent assumptions unavailable reason is unsupported.")
        return
    if payload.get("available") is not True:
        raise ValueError("Opponent assumptions available must be a boolean.")
    opponent_active = payload.get("opponent_active")
    if not isinstance(opponent_active, dict):
        raise ValueError("Opponent assumptions opponent_active must be an object.")
    possible_samples = opponent_active.get("possible_samples")
    if not isinstance(possible_samples, list):
        raise ValueError("Opponent assumptions possible_samples must be a list.")
    for sample in possible_samples:
        if not isinstance(sample, dict):
            raise ValueError("Opponent assumptions possible_samples entries must be objects.")
        if sample.get("is_user_confirmed") is not False:
            raise ValueError("Opponent possible samples must not be user-confirmed.")
        if sample.get("prior_probability") is not None:
            raise ValueError("v0.38 opponent possible samples must use null prior_probability.")


def build_opponent_assumptions_debug_summary(payload: dict[str, Any]) -> dict[str, Any]:
    opponent_assumptions = payload.get("opponent_assumptions") if isinstance(payload, dict) else None
    return build_opponent_assumptions_debug_summary_from_assumptions(opponent_assumptions)


def build_opponent_assumptions_debug_summary_from_assumptions(
    opponent_assumptions: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(opponent_assumptions, dict):
        return _debug_unavailable_summary(reason="opponent_assumptions_missing")

    opponent_active = opponent_assumptions.get("opponent_active")
    opponent_species_id = "unknown"
    possible_samples: list[dict[str, Any]] = []
    included_top_k = 0
    if isinstance(opponent_active, dict):
        species_id = opponent_active.get("species_id")
        if isinstance(species_id, str) and species_id.strip():
            opponent_species_id = species_id.strip()
        raw_samples = opponent_active.get("possible_samples")
        if isinstance(raw_samples, list):
            possible_samples = [sample for sample in raw_samples if isinstance(sample, dict)]
        samples_meta = opponent_active.get("samples_meta")
        if isinstance(samples_meta, dict) and isinstance(samples_meta.get("included_top_k"), int):
            included_top_k = samples_meta["included_top_k"]

    available = opponent_assumptions.get("available") is True
    if not available:
        return {
            "opponent_species_id": opponent_species_id,
            "opponent_assumptions_available": False,
            "reason": opponent_assumptions.get("reason"),
            "schema_version": _version_or_legacy(opponent_assumptions.get("schema_version")),
            "metadata_version": _version_or_legacy(opponent_assumptions.get("metadata_version")),
            "calculation_usage": opponent_assumptions.get("calculation_usage"),
            "is_confirmed_information": opponent_assumptions.get("is_confirmed_information"),
            "payload_features": _payload_features_or_fallback(opponent_assumptions.get("payload_features")),
            "possible_sample_count": 0,
            "included_top_k": 0,
            "possible_samples": [],
            "guardrails": dict(OPPONENT_ASSUMPTIONS_DEBUG_GUARDRAILS),
        }

    return {
        "opponent_species_id": opponent_species_id,
        "opponent_assumptions_available": True,
        "reason": None,
        "schema_version": _version_or_legacy(opponent_assumptions.get("schema_version")),
        "metadata_version": _version_or_legacy(opponent_assumptions.get("metadata_version")),
        "calculation_usage": opponent_assumptions.get("calculation_usage"),
        "is_confirmed_information": opponent_assumptions.get("is_confirmed_information"),
        "payload_features": _payload_features_or_fallback(opponent_assumptions.get("payload_features")),
        "possible_sample_count": len(possible_samples),
        "included_top_k": included_top_k or len(possible_samples),
        "possible_samples": [_debug_sample_summary(sample) for sample in possible_samples],
        "guardrails": dict(OPPONENT_ASSUMPTIONS_DEBUG_GUARDRAILS),
    }


def format_opponent_assumptions_debug_json(summary: dict[str, Any]) -> str:
    return json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)


def _possible_sample_payload(sample: dict[str, Any]) -> dict[str, Any]:
    assumptions = sample.get("assumptions")
    possible_item = assumptions.get("item") if isinstance(assumptions, dict) else None
    return {
        "sample_id": sample.get("sample_id"),
        "species_id": sample.get("species_id"),
        "label_en": sample.get("label_en"),
        "label_ko": sample.get("label_ko"),
        "source": "sample_assumed",
        "source_type": sample.get("source_type"),
        "confidence": sample.get("confidence"),
        "prior_probability": None,
        "prior_probability_type": "not_available",
        "evidence_basis": "Manual sentinel sample; not usage-derived.",
        "is_user_confirmed": False,
        "possible_item": possible_item,
        "role": sample.get("role"),
        "archetype_id": sample.get("archetype_id"),
        "possible_items": _safe_string_list(sample.get("possible_items")),
        "calculation_usage": sample.get("calculation_usage", "context_only"),
        "limitations": [
            "This is a possible opponent profile, not confirmed.",
            "Do not treat this as exact opponent stats.",
        ],
    }


def _debug_unavailable_summary(*, reason: str) -> dict[str, Any]:
    return {
        "opponent_species_id": "unknown",
        "opponent_assumptions_available": False,
        "reason": reason,
        "schema_version": "legacy",
        "metadata_version": "legacy",
        "calculation_usage": "context_only",
        "is_confirmed_information": False,
        "payload_features": _legacy_payload_features(),
        "possible_sample_count": 0,
        "included_top_k": 0,
        "possible_samples": [],
        "guardrails": dict(OPPONENT_ASSUMPTIONS_DEBUG_GUARDRAILS),
    }


def _debug_sample_summary(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": sample.get("sample_id"),
        "species_id": sample.get("species_id"),
        "role": sample.get("role"),
        "archetype_id": sample.get("archetype_id"),
        "confidence": sample.get("confidence"),
        "is_user_confirmed": sample.get("is_user_confirmed"),
        "possible_items": _debug_possible_items(sample),
        "used_for_damage": False,
        "used_for_speed": False,
    }


def _debug_possible_items(sample: dict[str, Any]) -> list[str]:
    possible_items = sample.get("possible_items")
    if isinstance(possible_items, list):
        return _safe_string_list(possible_items)
    possible_item = sample.get("possible_item")
    if isinstance(possible_item, str) and possible_item:
        return [possible_item]
    return []


def _safe_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _version_or_legacy(value: Any) -> str:
    return value if isinstance(value, str) and value else "legacy"


def _payload_features_or_fallback(value: Any) -> dict[str, bool]:
    if isinstance(value, dict):
        return {
            "possible_samples": bool(value.get("possible_samples")),
            "minimal_metadata": bool(value.get("minimal_metadata")),
            "debug_summary_supported": bool(value.get("debug_summary_supported")),
            "full_stats_excluded": bool(value.get("full_stats_excluded")),
            "damage_speed_integration": bool(value.get("damage_speed_integration")),
        }
    return _legacy_payload_features()


def _legacy_payload_features() -> dict[str, bool]:
    return {
        "possible_samples": False,
        "minimal_metadata": False,
        "debug_summary_supported": True,
        "full_stats_excluded": True,
        "damage_speed_integration": False,
    }


def _unavailable_payload(*, reason: str, species_id: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "mode": OPPONENT_ASSUMPTIONS_MODE,
        "schema_version": OPPONENT_ASSUMPTIONS_SCHEMA_VERSION,
        "metadata_version": OPPONENT_ASSUMPTIONS_METADATA_VERSION,
        "available": False,
        "scope": "opponent_active",
        "reason": reason,
        "is_confirmed_information": False,
        "calculation_usage": "context_only",
        "payload_features": dict(OPPONENT_ASSUMPTIONS_PAYLOAD_FEATURES),
        "limitations": list(
            OPPONENT_ASSUMPTIONS_UNAVAILABLE_LIMITATIONS.get(
                reason,
                ["Opponent sample assumptions are unavailable.", "Do not invent opponent samples."],
            )
        ),
    }
    if species_id is not None:
        payload["opponent_active"] = {
            "species_id": species_id,
            "known_status": "not_confirmed",
            "is_user_confirmed": False,
            "user_confirmed_fields": {},
            "possible_samples": [],
            "samples_meta": build_samples_meta([], total_known_archetypes=0),
            "observation_history": [],
            "update_policy": {
                "version": "0.38.0",
                "mode": "static",
                "note": "No observation-based updates are implemented.",
            },
        }
    return payload

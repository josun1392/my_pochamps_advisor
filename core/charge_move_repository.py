from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from advisor.canonical_charge_move_lifecycle import (
    INVENTORY_SCHEMA_VERSION,
    load_canonical_charge_move_lifecycle_inventory,
)


DEFAULT_CHARGE_MOVES_PATH = Path("data/static/charge_moves.json")
CHARGE_MOVES_VERSION = "charge_moves_v1"
GUARDED_EXECUTION_MODELS = frozenset({
    "charge_then_execute", "semi_invulnerable_then_execute", "other_two_turn",
})


def normalize_move_id(move_id: str) -> str:
    return move_id.strip().lower().replace("_", "-").replace(" ", "-")


def load_charge_moves(path: Path | None = None) -> dict[str, Any]:
    fixture_path = path or DEFAULT_CHARGE_MOVES_PATH
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    _validate_fixture(data)
    return data


class ChargeMoveRepository:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_CHARGE_MOVES_PATH
        self._canonical = path is None
        self.data = (
            load_canonical_charge_move_lifecycle_inventory()
            if self._canonical
            else load_charge_moves(self.path)
        )
        if self._canonical and self.data.get("version") != INVENTORY_SCHEMA_VERSION:
            raise ValueError("Canonical charge move inventory version mismatch.")
        self._moves = self.data["moves"]

    def get_charge_move_metadata(self, move_id: str | None) -> dict[str, Any] | None:
        if not move_id:
            return None
        metadata = self._moves.get(normalize_move_id(move_id))
        return dict(metadata) if isinstance(metadata, dict) else None

    def is_charge_move(self, move_id: str | None) -> bool:
        metadata = self.get_charge_move_metadata(move_id)
        return bool(metadata and metadata.get("is_charge_move") is True)

    def is_power_herb_eligible(self, move_id: str | None) -> bool:
        metadata = self.get_charge_move_metadata(move_id)
        return bool(metadata and metadata.get("power_herb_eligible") is True)

    def immediate_execution_guard(self, move_id: str | None) -> dict[str, Any] | None:
        """Return local canonical evidence that terminal execution is deferred.

        Recognition is deliberately not an execution grant: no current A2
        authority proves a charge was skipped or that turn two is occurring.
        """
        metadata = self.get_charge_move_metadata(move_id)
        if not metadata or metadata.get("execution_model") not in GUARDED_EXECUTION_MODELS:
            return None
        return {
            "move_id": normalize_move_id(str(move_id)),
            "execution_model": metadata["execution_model"],
            "reason": "two_turn_execution_unrepresented",
            "source": metadata["source"],
            "canonical_recognition_grants_immediate_execution": False,
        }


def _validate_fixture(data: Any) -> None:
    if not isinstance(data, dict):
        raise ValueError("Charge move fixture must be a JSON object.")
    if data.get("version") != CHARGE_MOVES_VERSION:
        raise ValueError(f"Charge move fixture version must be {CHARGE_MOVES_VERSION}.")
    moves = data.get("moves")
    if not isinstance(moves, dict):
        raise ValueError("Charge move fixture must include a moves object.")
    for move_id, metadata in moves.items():
        _validate_move_entry(move_id, metadata)
    deferred_moves = data.get("deferred_moves", {})
    if deferred_moves is not None and not isinstance(deferred_moves, dict):
        raise ValueError("Charge move fixture deferred_moves must be an object when present.")


def _validate_move_entry(move_id: Any, metadata: Any) -> None:
    if not isinstance(move_id, str) or not move_id:
        raise ValueError("Charge move fixture contains an invalid move id.")
    if move_id != normalize_move_id(move_id):
        raise ValueError(f"Charge move id must be normalized: {move_id}")
    if not isinstance(metadata, dict):
        raise ValueError(f"Charge move metadata for {move_id} must be an object.")
    required_fields = {
        "is_charge_move",
        "power_herb_eligible",
        "charge_type",
        "execution_model",
        "source",
        "confidence",
        "notes",
    }
    missing = sorted(required_fields - set(metadata))
    if missing:
        raise ValueError(f"Charge move metadata for {move_id} is missing fields: {missing}")
    if not isinstance(metadata["is_charge_move"], bool):
        raise ValueError(f"Charge move metadata for {move_id} must use boolean is_charge_move.")
    if not isinstance(metadata["power_herb_eligible"], bool):
        raise ValueError(f"Charge move metadata for {move_id} must use boolean power_herb_eligible.")
    if metadata["execution_model"] not in GUARDED_EXECUTION_MODELS:
        raise ValueError(f"Charge move metadata for {move_id} has an invalid execution_model.")
    for field in ("charge_type", "source", "confidence", "notes"):
        value = metadata[field]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Charge move metadata for {move_id} must include non-empty {field}.")
    known_exceptions = metadata.get("known_exceptions", [])
    if not isinstance(known_exceptions, list):
        raise ValueError(f"Charge move metadata for {move_id} known_exceptions must be a list.")
    if not all(isinstance(exception, str) and exception for exception in known_exceptions):
        raise ValueError(f"Charge move metadata for {move_id} known_exceptions must be strings.")

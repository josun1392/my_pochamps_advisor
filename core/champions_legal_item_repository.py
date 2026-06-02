from __future__ import annotations

from functools import lru_cache
from typing import Any

from core.champions_item_repository import (
    UNKNOWN,
    ChampionsItemRepository,
    load_champions_legal_items,
    normalize_item_id,
)


BLOCKED_BY_LEGAL_ITEM_COVERAGE = "blocked_by_legal_item_coverage"
UNKNOWN_ITEM = "unknown_item"


@lru_cache(maxsize=1)
def _default_repository() -> ChampionsItemRepository:
    return ChampionsItemRepository()


def is_champions_legal_item(item_id: str | None) -> bool:
    if not isinstance(item_id, str) or not item_id.strip():
        return False
    return _default_repository().is_legal_item(item_id)


def get_legal_item_status(item_id: str | None) -> dict[str, Any]:
    if not isinstance(item_id, str) or not item_id.strip():
        return {
            "item_id": None,
            "legal": False,
            "classification": UNKNOWN,
            "reason": UNKNOWN_ITEM,
        }

    normalized = normalize_item_id(item_id)
    classification = _default_repository().classify_item(normalized)
    legal = bool(classification.get("legal"))
    return {
        "item_id": normalized,
        "legal": legal,
        "classification": classification.get("classification", UNKNOWN),
        "legality_status": classification.get("legality_status", UNKNOWN),
        "reason": None if legal else BLOCKED_BY_LEGAL_ITEM_COVERAGE,
    }

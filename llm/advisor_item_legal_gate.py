"""Legal item gate helpers for user-facing LLM item contexts."""

from __future__ import annotations

from core.champions_legal_item_repository import (
    BLOCKED_BY_LEGAL_ITEM_COVERAGE,
    is_champions_legal_item,
)


def legal_item_context_block_reason(item_id: str | None) -> str | None:
    if is_champions_legal_item(item_id):
        return None
    return BLOCKED_BY_LEGAL_ITEM_COVERAGE

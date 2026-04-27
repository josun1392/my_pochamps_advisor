"""검색 엔진: 한/영 양방향, prefix + fuzzy matching.

KoMappingLoader가 제공하는 데이터를 메모리 인덱스로 구성하여
45초 타이머 환경에서 빠르게 응답한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from rapidfuzz import fuzz

from core.ko_mapping_loader import KoMappingLoader


EntityKind = Literal["pokemon", "move", "ability"]
MatchType = Literal["prefix", "substring", "fuzzy"]

_KIND_TO_MAPPING_KEY: dict[EntityKind, str] = {
    "pokemon": "pokemon",
    "move": "moves",
    "ability": "abilities",
}


@dataclass(frozen=True)
class SearchResult:
    kind: EntityKind
    en: str
    ko: str
    score: float
    match_type: str


@dataclass(frozen=True)
class _IndexEntry:
    kind: EntityKind
    en: str
    ko: str
    en_norm: str
    ko_norm: str


class SearchEngine:
    """KoMappingLoader 기반 검색 엔진."""

    def __init__(self, loader: KoMappingLoader) -> None:
        self._index: list[_IndexEntry] = []
        mapping = loader._mapping

        for kind, mapping_key in _KIND_TO_MAPPING_KEY.items():
            entries = mapping.get(mapping_key, {})
            if not isinstance(entries, dict):
                continue
            for en, ko in entries.items():
                if isinstance(en, str) and isinstance(ko, str):
                    self._index.append(
                        _IndexEntry(
                            kind=kind,
                            en=en,
                            ko=ko,
                            en_norm=_normalize(en),
                            ko_norm=_normalize(ko),
                        )
                    )

    def search(
        self,
        query: str,
        kind: EntityKind | None = None,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> list[SearchResult]:
        """검색 실행."""
        query_norm = _normalize(query)
        if not query_norm or limit <= 0:
            return []

        results: list[SearchResult] = []
        for entry in self._index:
            if kind is not None and entry.kind != kind:
                continue

            match = self._match_entry(entry, query_norm)
            if match is None:
                continue

            score, match_type = match
            if score >= min_score:
                results.append(
                    SearchResult(
                        kind=entry.kind,
                        en=entry.en,
                        ko=entry.ko,
                        score=score,
                        match_type=match_type,
                    )
                )

        return sorted(
            results,
            key=lambda result: (
                _match_rank(result.match_type),
                -result.score,
                result.ko,
                result.en,
                result.kind,
            ),
        )[:limit]

    @staticmethod
    def _match_entry(entry: _IndexEntry, query_norm: str) -> tuple[float, MatchType] | None:
        targets = (entry.ko_norm, entry.en_norm)

        if any(target.startswith(query_norm) for target in targets):
            return 1.0, "prefix"

        substring_scores = []
        for target in targets:
            position = target.find(query_norm)
            if position >= 0:
                position_bonus = max(0.0, 0.09 - min(position, 9) * 0.01)
                substring_scores.append(0.8 + position_bonus)
        if substring_scores:
            return max(substring_scores), "substring"

        fuzzy_score = max(fuzz.ratio(query_norm, target) / 100 for target in targets)
        if fuzzy_score > 0:
            return fuzzy_score, "fuzzy"
        return None


def _normalize(value: str) -> str:
    return re.sub(r"[\s\-]+", "", value.casefold())


def _match_rank(match_type: str) -> int:
    return {
        "prefix": 0,
        "substring": 1,
        "fuzzy": 2,
    }.get(match_type, 3)

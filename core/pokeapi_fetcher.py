from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import requests

from core.cache_manager import CacheManager


JsonDict = dict[str, Any]


class PokeAPIFetcher:
    """PokeAPI 호출 + 캐싱 통합 인터페이스."""

    BASE_URL = "https://pokeapi.co/api/v2"
    TIMEOUT = 10
    USER_AGENT = "PokemonCopilot/0.1 (educational)"

    def __init__(self, cache: CacheManager, offline: bool = False) -> None:
        self.cache = cache
        self.offline = offline
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})

    def get_pokemon(self, identifier: int | str) -> JsonDict:
        return self._get_resource("pokemon", "pokemon", identifier, self._normalize_pokemon)

    def get_move(self, identifier: int | str) -> JsonDict:
        return self._get_resource("moves", "move", identifier, self._normalize_move)

    def get_ability(self, identifier: int | str) -> JsonDict:
        return self._get_resource("abilities", "ability", identifier, self._normalize_ability)

    def get_type(self, identifier: int | str) -> JsonDict:
        return self._get_resource("types", "type", identifier, self._normalize_type)

    def get_species(self, identifier: int | str) -> JsonDict:
        return self._get_resource("species", "pokemon-species", identifier, self._normalize_species)

    def _get_resource(
        self,
        category: str,
        endpoint: str,
        identifier: int | str,
        normalizer: Any,
    ) -> JsonDict:
        cached = self.cache.get(category, identifier)
        if cached is not None:
            return cached

        if self.offline:
            raise RuntimeError(f"Offline mode: cache miss for {category}/{identifier}")

        raw = self._fetch(endpoint, identifier)
        normalized = normalizer(raw)
        self.cache.put(category, int(normalized["id"]), normalized)
        return normalized

    def _fetch(self, endpoint: str, identifier: int | str) -> JsonDict:
        url = f"{self.BASE_URL}/{endpoint}/{identifier}/"
        retry_statuses = {429, 503}
        delays = (1, 2, 4)

        for attempt in range(len(delays) + 1):
            response = self.session.get(url, timeout=self.TIMEOUT)
            if response.status_code in retry_statuses and attempt < len(delays):
                time.sleep(delays[attempt])
                continue
            if response.status_code >= 400:
                response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError(f"PokeAPI 응답이 객체가 아닙니다: {url}")
            return data

        raise RuntimeError(f"PokeAPI 요청 실패: {url}")

    @classmethod
    def _normalize_pokemon(cls, raw: JsonDict) -> JsonDict:
        return {
            "id": raw["id"],
            "name": raw["name"],
            "types": [
                item["type"]["name"]
                for item in sorted(raw.get("types", []), key=lambda value: value.get("slot", 0))
            ],
            "abilities": [
                {
                    "name": item["ability"]["name"],
                    "is_hidden": bool(item.get("is_hidden", False)),
                }
                for item in raw.get("abilities", [])
            ],
            "stats": {
                item["stat"]["name"]: item["base_stat"]
                for item in raw.get("stats", [])
            },
            "sprites": {
                "front_default": raw.get("sprites", {}).get("front_default"),
                "front_shiny": raw.get("sprites", {}).get("front_shiny"),
            },
            "moves": [
                item["move"]["name"]
                for item in raw.get("moves", [])
            ],
            "species_url": raw.get("species", {}).get("url"),
            "_fetched_at": cls._timestamp(),
        }

    @classmethod
    def _normalize_move(cls, raw: JsonDict) -> JsonDict:
        return {
            "id": raw["id"],
            "name": raw["name"],
            "names": cls._localized_names(raw),
            "type": cls._named_resource_name(raw.get("type")),
            "damage_class": cls._named_resource_name(raw.get("damage_class")),
            "power": raw.get("power"),
            "accuracy": raw.get("accuracy"),
            "pp": raw.get("pp"),
            "priority": raw.get("priority"),
            "effect_chance": raw.get("effect_chance"),
            "target": cls._named_resource_name(raw.get("target")),
            "_fetched_at": cls._timestamp(),
        }

    @classmethod
    def _normalize_ability(cls, raw: JsonDict) -> JsonDict:
        effect_entry = cls._first_english_entry(raw.get("effect_entries", []))
        return {
            "id": raw["id"],
            "name": raw["name"],
            "names": cls._localized_names(raw),
            "effect": effect_entry.get("effect"),
            "short_effect": effect_entry.get("short_effect"),
            "generation": cls._named_resource_name(raw.get("generation")),
            "_fetched_at": cls._timestamp(),
        }

    @classmethod
    def _normalize_type(cls, raw: JsonDict) -> JsonDict:
        relations = raw.get("damage_relations", {})
        return {
            "id": raw["id"],
            "name": raw["name"],
            "names": cls._localized_names(raw),
            "damage_class": cls._named_resource_name(raw.get("move_damage_class")),
            "damage_relations": {
                key: [item["name"] for item in relations.get(key, [])]
                for key in (
                    "double_damage_from",
                    "double_damage_to",
                    "half_damage_from",
                    "half_damage_to",
                    "no_damage_from",
                    "no_damage_to",
                )
            },
            "_fetched_at": cls._timestamp(),
        }

    @classmethod
    def _normalize_species(cls, raw: JsonDict) -> JsonDict:
        return {
            "id": raw["id"],
            "name": raw["name"],
            "names": cls._localized_names(raw),
            "varieties": [
                {
                    "name": item["pokemon"]["name"],
                    "is_default": bool(item.get("is_default", False)),
                }
                for item in raw.get("varieties", [])
            ],
            "_fetched_at": cls._timestamp(),
        }

    @staticmethod
    def _localized_names(raw: JsonDict) -> dict[str, str]:
        return {
            item["language"]["name"]: item["name"]
            for item in raw.get("names", [])
            if item.get("language", {}).get("name") and isinstance(item.get("name"), str)
        }

    @staticmethod
    def _named_resource_name(value: JsonDict | None) -> str | None:
        if not value:
            return None
        name = value.get("name")
        return name if isinstance(name, str) else None

    @staticmethod
    def _first_english_entry(entries: list[JsonDict]) -> JsonDict:
        for entry in entries:
            language = entry.get("language", {})
            if language.get("name") == "en":
                return entry
        return {}

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

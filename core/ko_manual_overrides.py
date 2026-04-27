"""PokeAPI 한국어 데이터 누락분에 대한 수동 오버라이드.

build_ko_mapping.py가 PokeAPI에서 한국어를 찾지 못했을 때
이 사전을 fallback으로 참조한다. 새로운 누락이 발견되면 여기에 추가.
"""

from __future__ import annotations


MANUAL_OVERRIDES: dict[str, dict[str, str]] = {
    "moves": {
        "tera-blast": "테라버스트",
    },
    "pokemon": {},
    "abilities": {},
    "types": {},
}

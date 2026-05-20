"""Manual Korean-name overrides for gaps in PokeAPI localized data.

These names are used by build_ko_mapping.py when PokeAPI does not provide a
Korean localized name for a resource.
"""

from __future__ import annotations


MANUAL_OVERRIDES: dict[str, dict[str, str]] = {
    "moves": {
        "aqua-cutter": "아쿠아커터",
        "aqua-step": "아쿠아스텝",
        "armor-cannon": "아머캐논",
        "axe-kick": "발꿈치찍기",
        "bitter-blade": "원념의칼",
        "bitter-malice": "천추지한",
        "ceaseless-edge": "비검천중파",
        "chilling-water": "찬물끼얹기",
        "chilly-reception": "썰렁개그",
        "comeuppance": "앙갚음",
        "dire-claw": "페이탈클로",
        "flower-trick": "트릭플라워",
        "gigaton-hammer": "거대해머",
        "headlong-rush": "들이받기",
        "ice-spinner": "아이스스피너",
        "infernal-parade": "백귀야행",
        "jet-punch": "제트펀치",
        "kowtow-cleave": "도각참",
        "last-respects": "성묘",
        "lumina-crash": "루미나콜리전",
        "matcha-gotcha": "휘적휘적포",
        "mortal-spin": "킬러스핀",
        "mountain-gale": "빙산바람",
        "population-bomb": "찍찍베기",
        "pounce": "달려들기",
        "psyshield-bash": "배리어러시",
        "raging-bull": "레이징불",
        "raging-fury": "대격분",
        "salt-cure": "소금절이",
        "shed-tail": "꼬리자르기",
        "shelter": "농성",
        "snowscape": "설경",
        "spicy-extract": "하바네로엑기스",
        "stone-axe": "암석액스",
        "syrup-bomb": "시럽봄",
        "tera-blast": "테라버스트",
        "tidy-up": "정리정돈",
        "torch-song": "플레어송",
        "trailblaze": "개척하기",
        "triple-arrows": "3연화살",
        "twin-beam": "트윈빔",
        "wave-crash": "웨이브태클",
    },
    "pokemon": {},
    "abilities": {},
    "types": {},
}

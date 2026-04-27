from __future__ import annotations

import logging


LOGGER = logging.getLogger(__name__)

FORM_SUFFIX_KO: dict[str, str] = {
    "therian": "(영물폼)",
    "incarnate": "(화신폼)",
    "rapid-strike": "(연격의 태세)",
    "single-strike": "(일격의 태세)",
    "shadow": "(흑마)",
    "ice": "(백마)",
    "wash": "(세탁)",
    "heat": "(히트)",
    "frost": "(냉동)",
    "fan": "(회전)",
    "mow": "(잔디깎이)",
    "origin": "(오리진폼)",
    "altered": "(어나더폼)",
    "attack": "(어택폼)",
    "defense": "(디펜스폼)",
    "speed": "(스피드폼)",
    "normal": "(노말폼)",
    "mega": " (메가)",
    "mega-x": " (메가X)",
    "mega-y": " (메가Y)",
    "gmax": " (거다이맥스)",
    "alola": " (알로라)",
    "galar": " (가라르)",
    "hisui": " (히스이)",
    "paldea": " (팔데아)",
    "paldea-combat": " (팔데아 컴뱃)",
    "paldea-blaze": " (팔데아 블레이즈)",
    "paldea-aqua": " (팔데아 아쿠아)",
    "primal": " (원시)",
    "crowned": " (왕관)",
    "eternamax": " (무한다이맥스)",
    "ash": " (지우 피카츄)",
    "": "",
}


def split_pokemon_name(api_name: str) -> tuple[str, str]:
    """
    PokeAPI 포켓몬 이름을 기본 species 이름과 form suffix로 나눕니다.

    알려진 폼 접미사 중 가장 긴 값을 먼저 매칭해서
    'urshifu-rapid-strike' 같은 복합 suffix를 보존합니다.
    """
    if "-" not in api_name:
        return api_name, ""

    for suffix in sorted((key for key in FORM_SUFFIX_KO if key), key=len, reverse=True):
        marker = f"-{suffix}"
        if api_name.endswith(marker):
            return api_name[: -len(marker)], suffix

    base, suffix = api_name.rsplit("-", 1)
    return base, suffix


def apply_korean_form(base_ko: str, form_suffix: str) -> str:
    if form_suffix in FORM_SUFFIX_KO:
        return f"{base_ko}{FORM_SUFFIX_KO[form_suffix]}"

    LOGGER.warning("알 수 없는 포켓몬 폼 접미사: %s", form_suffix)
    return f"{base_ko}-{form_suffix}"

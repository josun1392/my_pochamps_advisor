from __future__ import annotations

from types import MethodType, SimpleNamespace

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveView
from core.move_repository import MoveRepository
from core.pokemon_repository import PokemonView
from llm.advisor_payload_contract import ADVISOR_KNOWN_LIMITATIONS, ADVISOR_PAYLOAD_MODE
from ui.main_window import MainWindow


def test_ui_payload_uses_advisor_contract_guardrails() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["scenario"]["mode"] == ADVISOR_PAYLOAD_MODE
    assert payload["scenario"]["known_limitations"] == ADVISOR_KNOWN_LIMITATIONS
    assert "Move damage estimates, when present, use default assumptions and are not final battle damage." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Opponent candidate moves are possible Champions moves, not confirmed moves." in payload["scenario"][
        "known_limitations"
    ]
    assert "Terastallization is banned in PoChamps and must not be considered." in payload["scenario"][
        "known_limitations"
    ]


def test_manual_move_payload_includes_only_user_confirmed_moves() -> None:
    panel = _panel(
        "charizard",
        selected_move_index=2,
        selected_moves=[None, _move("air-slash"), _move("flamethrower"), None],
    )

    available_moves = MainWindow._panel_moves_payload(panel)
    selected_move = MainWindow._selected_move_payload(panel)

    assert [move["move_id"] for move in available_moves] == ["air-slash", "flamethrower"]
    assert [move["slot"] for move in available_moves] == [1, 2]
    assert selected_move is not None
    assert selected_move["move_id"] == "flamethrower"
    assert selected_move["slot"] == 2


def test_ui_payload_attaches_selected_move_damage_estimate() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    estimate = payload["moves"]["my_selected_move"]["damage_estimate"]

    assert estimate["status"] == "available_with_default_assumptions"
    assert estimate["is_final_battle_damage"] is False
    assert "damage_range" in estimate
    assert "percent_range" in estimate
    assert "assumptions" in estimate
    assert "limitations" in estimate
    assert "ko_chance" not in estimate
    assert "ohko_chance" not in estimate


def test_ui_payload_attaches_available_move_damage_estimates() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower"), _move("air-slash")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    estimates = [move["damage_estimate"] for move in payload["moves"]["my_available_moves"]]

    assert payload["moves"]["move_data_status"] == "four_move_damage_comparison_v0.10"
    assert len(estimates) == 2
    assert {estimate["scope"] for estimate in estimates} == {"available_move_comparison"}
    assert all(estimate["status"] == "available_with_default_assumptions" for estimate in estimates)
    assert all("damage_range" in estimate for estimate in estimates)
    assert all("percent_range" in estimate for estimate in estimates)
    assert all("ko_chance" not in estimate for estimate in estimates)


def test_ui_payload_includes_opponent_moves_section() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    opponent_moves = payload["opponent_moves"]

    assert opponent_moves["status"] == "candidates_only"
    assert opponent_moves["known_moves"] == []
    assert len(opponent_moves["candidate_moves"]) == 24
    assert opponent_moves["candidate_moves_limit"] == 24
    assert opponent_moves["candidate_source_status"]["status"] == "available"
    assert all(candidate["source"] == "champions_movepool" for candidate in opponent_moves["candidate_moves"])
    assert all(
        candidate["confidence"] == "possible_not_confirmed"
        for candidate in opponent_moves["candidate_moves"]
    )


def test_opponent_selected_moves_become_known_moves() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    opponent_moves = payload["opponent_moves"]

    assert opponent_moves["status"] == "known_and_candidates"
    assert opponent_moves["known_moves"] == [
        {
            "slot": 0,
            "move_id": "earthquake",
            "name_en": "Earthquake",
            "name_ko": "Earthquake",
            "type": "ground",
            "category": "physical",
            "power": 100,
            "accuracy": 100,
            "pp": 10,
            "source": "user_confirmed",
        }
    ]
    assert "earthquake" not in {candidate["move_id"] for candidate in opponent_moves["candidate_moves"]}
    assert all("damage_estimate" not in candidate for candidate in opponent_moves["candidate_moves"])
    assert all("damage_estimate" not in move for move in opponent_moves["known_moves"])


def test_missing_opponent_fixture_does_not_fallback_to_pokeapi_learnset() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("missingno", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()
    opponent_moves = payload["opponent_moves"]

    assert opponent_moves["status"] == "unavailable_missing_champions_movepool"
    assert opponent_moves["known_moves"] == []
    assert opponent_moves["candidate_moves"] == []
    assert payload["moves"]["opponent_available_moves"] == []


def test_pokemon_payload_marks_base_stats_as_reference_data_only() -> None:
    panel = _panel("charizard", selected_move_index=0, selected_moves=[])

    payload = MainWindow._panel_to_llm_payload(panel, slot_index=0)

    assert payload["name_en"] == "charizard"
    assert payload["base_stats"] == {
        "hp": 78,
        "attack": 84,
        "defense": 78,
        "special-attack": 109,
        "special-defense": 85,
        "speed": 100,
    }
    assert "final_stats" not in payload
    assert "evs" not in payload
    assert "ivs" not in payload
    assert "nature" not in payload
    assert "item" not in payload


def test_ui_cost_text_includes_pricing_status() -> None:
    assert (
        MainWindow._format_cost_text(
            input_tokens=4031,
            output_tokens=52,
            cost=0.0,
            pricing_status="free_tier_zero_cost",
        )
        == "Free tier | input 4031 / output 52 | $0.0000000"
    )
    assert (
        MainWindow._format_cost_text(
            input_tokens=1000,
            output_tokens=100,
            cost=0.00055,
            pricing_status="paid_tier_estimated_cost",
        )
        == "Paid estimate | input 1000 / output 100 | $0.0005500"
    )
    assert (
        MainWindow._format_cost_text(
            input_tokens=1000,
            output_tokens=100,
            cost=0.0,
            pricing_status="unknown_model_or_unknown_pricing",
        )
        == "Pricing unknown | input 1000 / output 100"
    )


def _panel(
    name: str,
    *,
    selected_move_index: int | None,
    selected_moves: list[MoveView | None],
) -> SimpleNamespace:
    return SimpleNamespace(
        pokemon_view=_pokemon(name),
        current_hp_percent=100,
        selected_move_index=selected_move_index,
        selected_moves=selected_moves + [None] * (4 - len(selected_moves)),
    )


def _window(my_panel, opponent_panel):
    window = MainWindow.__new__(MainWindow)
    window.selected_slots = {"team_my": 0, "team_enemy": 0}
    window.move_repo = MoveRepository(CacheManager(), KoMappingLoader())
    window.champions_move_pool_repo = ChampionsMovePoolRepository()

    def _slot_panel(self, column_name: str, slot_index: int):
        del slot_index
        return my_panel if column_name == "team_my" else opponent_panel

    window._slot_panel = MethodType(_slot_panel, window)
    return window


def _pokemon(name: str) -> PokemonView:
    if name == "garchomp":
        return PokemonView(
            en="garchomp",
            ko="Garchomp",
            types_en=["dragon", "ground"],
            types_ko=["Dragon", "Ground"],
            base_stats={
                "hp": 108,
                "attack": 130,
                "defense": 95,
                "special-attack": 80,
                "special-defense": 85,
                "speed": 102,
            },
            abilities_en=["sand-veil", "rough-skin"],
            abilities_ko=["Sand Veil", "Rough Skin"],
            moves_en=["earthquake", "outrage"],
        )
    if name == "missingno":
        return PokemonView(
            en="missingno",
            ko="MissingNo.",
            types_en=["normal"],
            types_ko=["Normal"],
            base_stats={
                "hp": 33,
                "attack": 33,
                "defense": 33,
                "special-attack": 33,
                "special-defense": 33,
                "speed": 33,
            },
            abilities_en=[],
            abilities_ko=[],
            moves_en=[],
        )
    return PokemonView(
        en="charizard",
        ko="Charizard",
        types_en=["fire", "flying"],
        types_ko=["Fire", "Flying"],
        base_stats={
            "hp": 78,
            "attack": 84,
            "defense": 78,
            "special-attack": 109,
            "special-defense": 85,
            "speed": 100,
        },
        abilities_en=["blaze", "solar-power"],
        abilities_ko=["Blaze", "Solar Power"],
        moves_en=["air-slash", "flamethrower"],
    )


def _move(move_id: str) -> MoveView:
    if move_id == "earthquake":
        return MoveView(
            move_id="earthquake",
            name_en="Earthquake",
            name_ko="Earthquake",
            type="ground",
            category="physical",
            power=100,
            accuracy=100,
            pp=10,
        )
    if move_id == "air-slash":
        return MoveView(
            move_id="air-slash",
            name_en="Air Slash",
            name_ko="Air Slash",
            type="flying",
            category="special",
            power=75,
            accuracy=95,
            pp=15,
        )
    return MoveView(
        move_id="flamethrower",
        name_en="Flamethrower",
        name_ko="Flamethrower",
        type="fire",
        category="special",
        power=90,
        accuracy=100,
        pp=15,
    )

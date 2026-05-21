from __future__ import annotations

from types import MethodType, SimpleNamespace

from core.cache_manager import CacheManager
from core.champions_move_pool import ChampionsMovePoolRepository
from core.ko_mapping_loader import KoMappingLoader
from core.move_repository import MoveView
from core.move_repository import MoveRepository
from core.pokemon_repository import PokemonView
from llm.advisor_client import _build_ui_selected_prompt
from llm.advisor_payload_contract import ADVISOR_KNOWN_LIMITATIONS, ADVISOR_PAYLOAD_MODE
from ui.main_window import MainWindow
from ui.widgets.item_profile_dialog import item_profile_from_option


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
    assert "Candidate moves may be mentioned as possible threats only when labeled as unconfirmed." in payload[
        "scenario"
    ]["known_limitations"]
    assert (
        "Opponent known move damage estimates, when present, are default-assumption reference values only."
        in payload["scenario"]["known_limitations"]
    )
    assert (
        "Every damage estimate includes an assumption_profile that identifies the stat model used."
        in payload["scenario"]["known_limitations"]
    )
    assert "User-confirmed final stats may be used when stat_profiles provides all six stats." in payload["scenario"][
        "known_limitations"
    ]
    assert "item_profiles distinguishes unknown, none, system_default_none, and user_confirmed item state." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Only item effects marked as applied in damage_estimate.item_effects are included in damage numbers." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Type matchup descriptions must use damage_estimate.type_effectiveness when present." in payload[
        "scenario"
    ]["known_limitations"]
    assert "Opponent candidate move damage is not calculated in v0.18." in payload["scenario"]["known_limitations"]
    assert "Use my_available_moves damage_estimates to compare the user's own move options." in payload["scenario"][
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
    _assert_default_assumption_profile(estimate)
    assert "damage_range" in estimate
    assert "percent_range" in estimate
    assert "type_effectiveness" in estimate
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
    assert all(
        estimate["assumption_profile"]["id"] == "default_level50_ivs31_evs0_neutral_no_item"
        for estimate in estimates
    )
    assert all("damage_range" in estimate for estimate in estimates)
    assert all("percent_range" in estimate for estimate in estimates)
    assert all("ko_chance" not in estimate for estimate in estimates)
    assert all("item_effects" in estimate for estimate in estimates)


def test_ui_payload_includes_default_stat_profiles() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["stat_profiles"]["my_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["my_active"]["source"] == "system_default"
    assert payload["stat_profiles"]["my_active"]["final_stats"] is None
    assert payload["stat_profiles"]["opponent_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["opponent_active"]["source"] == "system_default"
    assert payload["stat_profiles"]["opponent_active"]["final_stats"] is None


def test_ui_payload_includes_default_item_profiles() -> None:
    my_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    my_item = payload["item_profiles"]["my_active"]
    opponent_item = payload["item_profiles"]["opponent_active"]
    assert my_item["status"] == "system_default_none"
    assert my_item["source"] == "system_default"
    assert my_item["item_id"] is None
    assert my_item["damage_modifier_status"] == "not_applicable"
    assert opponent_item["status"] == "unknown"
    assert opponent_item["source"] == "user_unconfirmed"
    assert opponent_item["item_id"] is None


def test_ui_payload_includes_user_selected_item_profiles() -> None:
    my_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        item_profile=item_profile_from_option("choice-band"),
    )
    opponent_panel = _panel(
        "corviknight",
        selected_move_index=0,
        selected_moves=[_move("drill-peck")],
        item_profile=item_profile_from_option("life-orb", role_key="opponent_active"),
    )
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["item_profiles"]["my_active"]["item_id"] == "choice-band"
    assert payload["item_profiles"]["my_active"]["status"] == "user_confirmed"
    assert payload["item_profiles"]["opponent_active"]["item_id"] == "life-orb"
    assert payload["item_profiles"]["opponent_active"]["status"] == "user_confirmed"
    my_estimate = payload["moves"]["my_available_moves"][0]["damage_estimate"]
    opponent_estimate = payload["opponent_moves"]["known_moves"][0]["damage_estimate"]
    assert my_estimate["item_effects"]["attacker_item"]["status"] == "applied"
    assert opponent_estimate["item_effects"]["attacker_item"]["status"] == "applied"
    assert "recoil" in opponent_estimate["item_effects"]["attacker_item"]["unapplied_effects"]


def test_ui_payload_distinguishes_unknown_and_no_item() -> None:
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        item_profile=item_profile_from_option("none"),
    )
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["item_profiles"]["my_active"]["status"] == "none"
    assert payload["item_profiles"]["opponent_active"]["status"] == "unknown"


def test_ui_payload_includes_user_confirmed_final_stats() -> None:
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        final_stats=_final_stats(spa=300),
    )
    opponent_panel = _panel(
        "garchomp",
        selected_move_index=0,
        selected_moves=[_move("earthquake")],
        final_stats=_final_stats(atk=300),
    )
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["stat_profiles"]["my_active"]["status"] == "user_confirmed_final_stats"
    assert payload["stat_profiles"]["my_active"]["source"] == "user_input"
    assert payload["stat_profiles"]["my_active"]["final_stats"]["spa"] == 300
    assert payload["stat_profiles"]["opponent_active"]["status"] == "user_confirmed_final_stats"
    assert payload["stat_profiles"]["opponent_active"]["final_stats"]["atk"] == 300
    my_estimate = payload["moves"]["my_available_moves"][0]["damage_estimate"]
    opponent_estimate = payload["opponent_moves"]["known_moves"][0]["damage_estimate"]
    assert my_estimate["assumption_profile"]["id"] == "user_confirmed_final_stats_level50"
    assert my_estimate["assumption_profile"]["is_user_confirmed"] is True
    assert opponent_estimate["assumption_profile"]["id"] == "user_confirmed_final_stats_level50"
    assert opponent_estimate["is_final_battle_damage"] is False


def test_partial_final_stats_remain_default_assumption() -> None:
    my_panel = _panel(
        "charizard",
        selected_move_index=0,
        selected_moves=[_move("flamethrower")],
        final_stats={"hp": 153, "atk": 104},
    )
    opponent_panel = _panel("garchomp", selected_move_index=None, selected_moves=[])
    window = _window(my_panel, opponent_panel)

    payload = window._build_llm_battle_input()

    assert payload["stat_profiles"]["my_active"]["status"] == "default_assumption"
    assert payload["stat_profiles"]["my_active"]["final_stats"] is None


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
    known_move = opponent_moves["known_moves"][0]
    assert len(opponent_moves["known_moves"]) == 1
    assert known_move["slot"] == 0
    assert known_move["move_id"] == "earthquake"
    assert known_move["source"] == "user_confirmed"
    assert known_move["damage_estimate"]["status"] == "available_with_default_assumptions"
    assert known_move["damage_estimate"]["scope"] == "opponent_known_move_only"
    assert known_move["damage_estimate"]["target"] == "my_active"
    assert known_move["damage_estimate"]["is_final_battle_damage"] is False
    _assert_default_assumption_profile(known_move["damage_estimate"])
    assert "damage_range" in known_move["damage_estimate"]
    assert "percent_range" in known_move["damage_estimate"]
    assert "ko_chance" not in known_move["damage_estimate"]
    assert "ohko_chance" not in known_move["damage_estimate"]
    assert "earthquake" not in {candidate["move_id"] for candidate in opponent_moves["candidate_moves"]}
    assert all("damage_estimate" not in candidate for candidate in opponent_moves["candidate_moves"])


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


def test_ui_selected_prompt_preserves_opponent_move_guardrails() -> None:
    prompt = _build_ui_selected_prompt(
        {
            "moves": {
                "my_available_moves": [
                    {
                        "move_id": "flamethrower",
                        "damage_estimate": {"status": "available_with_default_assumptions"},
                    }
                ]
            },
            "opponent_moves": {
                "known_moves": [{"move_id": "earthquake", "source": "user_confirmed"}],
                "candidate_moves": [{"move_id": "rock-slide", "confidence": "possible_not_confirmed"}],
            },
        }
    )

    assert "known_moves as user-confirmed" in prompt
    assert "candidate_moves only as possible, not confirmed" in prompt
    assert "label them as unconfirmed" in prompt
    assert "Opponent known move damage estimates" in prompt
    assert "User-confirmed final stats may be used" in prompt
    assert "Opponent candidate move damage is not calculated in v0.14" not in prompt
    assert "Opponent candidate move damage is not calculated in v0.16" not in prompt
    assert "Opponent candidate move damage is not calculated in v0.18" in prompt
    assert "Only item effects marked as applied in damage_estimate.item_effects" in prompt
    assert "If an attacker item effect is applied" in prompt
    assert "default assumptions plus the supported item modifier" in prompt
    assert "If Life Orb is applied, say recoil is not modeled" in prompt
    assert "If Choice Band or Choice Specs is applied, say choice lock is not modeled" in prompt
    assert "Choice lock, Life Orb recoil, Choice Scarf speed" in prompt
    assert "use damage_estimate.type_effectiveness" in prompt
    assert "super effective, resisted, or immune" in prompt
    assert "Do not print raw type_effectiveness labels" in prompt
    assert "super_effective" in prompt
    assert "not_very_effective" in prompt
    assert "super effective" in prompt
    assert "not very effective" in prompt
    assert "immune/no effect" in prompt
    assert "Use my_available_moves damage_estimates to compare the user's own move options" in prompt
    assert "Do not claim OHKO, 2HKO, KO chance, survival, or speed order" in prompt


def test_advisor_contract_preserves_item_modifier_response_guardrail() -> None:
    assert (
        "When item_effects.attacker_item.status is applied, mention that the supported item damage modifier is applied."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert (
        "If an item damage modifier is applied, describe the estimate as default assumptions plus the supported item modifier, not only default assumptions."
        in ADVISOR_KNOWN_LIMITATIONS
    )
    assert "If Life Orb is applied, say Life Orb recoil is not modeled." in ADVISOR_KNOWN_LIMITATIONS
    assert "If Choice Band or Choice Specs is applied, say choice lock is not modeled." in ADVISOR_KNOWN_LIMITATIONS
    assert (
        "Do not print raw type_effectiveness labels like super_effective or not_very_effective; convert them to natural wording."
        in ADVISOR_KNOWN_LIMITATIONS
    )


def _panel(
    name: str,
    *,
    selected_move_index: int | None,
    selected_moves: list[MoveView | None],
    final_stats: dict | None = None,
    item_profile: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        pokemon_view=_pokemon(name),
        current_hp_percent=100,
        selected_move_index=selected_move_index,
        selected_moves=selected_moves + [None] * (4 - len(selected_moves)),
        final_stats=final_stats,
        item_profile=item_profile,
    )


def _assert_default_assumption_profile(estimate: dict) -> None:
    assert estimate["assumption_profile"] == {
        "id": "default_level50_ivs31_evs0_neutral_no_item",
        "label": "Default Level 50 / IV 31 / EV 0 / neutral nature / no item",
        "source": "system_default",
        "confidence": "rough_reference",
        "is_user_confirmed": False,
    }


def _final_stats(
    *,
    hp: int = 153,
    atk: int = 104,
    def_: int = 98,
    spa: int = 161,
    spd: int = 105,
    spe: int = 167,
) -> dict:
    return {
        "hp": hp,
        "atk": atk,
        "def": def_,
        "spa": spa,
        "spd": spd,
        "spe": spe,
    }


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
    if name == "corviknight":
        return PokemonView(
            en="corviknight",
            ko="Corviknight",
            types_en=["flying", "steel"],
            types_ko=["Flying", "Steel"],
            base_stats={
                "hp": 98,
                "attack": 87,
                "defense": 105,
                "special-attack": 53,
                "special-defense": 85,
                "speed": 67,
            },
            abilities_en=["pressure", "unnerve"],
            abilities_ko=["Pressure", "Unnerve"],
            moves_en=["drill-peck"],
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
    if move_id == "drill-peck":
        return MoveView(
            move_id="drill-peck",
            name_en="Drill Peck",
            name_ko="Drill Peck",
            type="flying",
            category="physical",
            power=80,
            accuracy=100,
            pp=20,
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

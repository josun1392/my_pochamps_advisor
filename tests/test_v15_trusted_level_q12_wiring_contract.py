from copy import deepcopy

import llm.advisor_q12_snapshot_adapter as q12_adapter
from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle
from llm.advisor_turn_snapshot import BASE_STAT_KEYS


class _SpeciesRepository:
    def get(self, pokemon_id):
        return {
            "en": pokemon_id,
            "types_en": ["normal"],
            "base_stats": {stat: 80 for stat in BASE_STAT_KEYS},
        }


def _provenance(side, slot, pokemon, session="s0", source="user_confirmed_final_battle_stat", trust="user_confirmed_current"):
    return {
        "side": side, "slot_index": slot, "pokemon_id": pokemon,
        "session_id": session, "source": source, "trust": trust,
    }


def _battle(*, include_level=True, level_session="s0"):
    final_stats = []
    for side, pokemon, slot in (("self", "pikachu", 0), ("opponent", "eevee", 1)):
        for index, stat in enumerate(BASE_STAT_KEYS):
            final_stats.append({
                "side": side, "stat": stat, "value": 100 + index,
                "status": "user_confirmed", "source": "user_confirmed_final_battle_stat",
                "provenance": _provenance(side, slot, pokemon),
            })
    battle = {
        "current_state_session_id": "s0",
        "pokemon": {
            "my_active": {"name_en": "pikachu", "slot_index": 0},
            "opponent_active": {"name_en": "eevee", "slot_index": 1},
        },
        "moves": {"my_available_moves": [
            {"slot_index": 0, "move_id": "tackle"},
            {"slot_index": 1, "move_id": "swift"},
            {"slot_index": 2, "move_id": "protect"},
        ]},
        "final_stat_context": {"current_final_stats": final_stats},
    }
    if include_level:
        battle["trusted_level_context"] = {"current_levels": [{
            "side": "self", "value": 50,
            "provenance": _provenance(
                "self", 0, "pikachu", session=level_session,
                source="user_confirmed_current_level", trust="user_confirmed_current",
            ),
        }]}
    return battle


def _moves():
    return {
        "tackle": {"category": "physical", "power": 40, "type": "normal"},
        "swift": {"category": "special", "power": 60, "type": "normal"},
        "protect": {"category": "status"},
    }


def test_trusted_level_wires_each_damaging_candidate_once_without_provider_payload_leak(monkeypatch):
    calls = []
    original = q12_adapter.calc_damage_rolls

    def tracking(context):
        calls.append(context)
        return original(context)

    monkeypatch.setattr(q12_adapter, "calc_damage_rolls", tracking)
    result = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}, {"move_id": "swift"}, {"move_id": "protect"}],
        battle_input=_battle(), move_repository=_moves(), species_repository=_SpeciesRepository(),
    )
    candidates = result["candidates"]
    assert [candidate["q12_damage"]["status"] for candidate in candidates] == ["resolved", "resolved", "unavailable"]
    assert len(calls) == 2
    assert result["recommendation_request"]["candidate_comparisons"][0].get("q12_damage") is None


def test_missing_or_stale_trusted_level_keeps_candidate_and_never_invokes_q12(monkeypatch):
    monkeypatch.setattr(q12_adapter, "calc_damage_rolls", lambda _context: (_ for _ in ()).throw(AssertionError("must not invoke")))
    for battle in (_battle(include_level=False), _battle(level_session="old-session")):
        result = prepare_ui_recommendation_cycle(
            selected_moves=[{"move_id": "tackle"}], battle_input=battle,
            move_repository=_moves(), species_repository=_SpeciesRepository(),
        )
        candidate = result["candidates"][0]
        assert candidate["move"] == "tackle"
        assert candidate["q12_damage"] == {"status": "unavailable", "limitations": ["trusted_level_unavailable"]}


def test_candidate_q12_result_is_detached_across_source_mutation_and_formula_exception(monkeypatch):
    battle = _battle()
    first = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input=battle,
        move_repository=_moves(), species_repository=_SpeciesRepository(),
    )["candidates"][0]
    frozen = deepcopy(first["q12_damage"])
    battle["trusted_level_context"]["current_levels"][0]["value"] = 1
    battle["final_stat_context"]["current_final_stats"][0]["value"] = 1
    assert first["q12_damage"] == frozen

    monkeypatch.setattr(q12_adapter, "calc_damage_rolls", lambda _context: (_ for _ in ()).throw(RuntimeError("private")))
    errored = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "tackle"}], battle_input=_battle(),
        move_repository=_moves(), species_repository=_SpeciesRepository(),
    )["candidates"][0]
    assert errored["q12_damage"] == {"status": "unavailable", "candidate_move_id": None, "candidate_move_slot": None, "damage_rolls": [], "min_damage": None, "max_damage": None, "current_hp": None, "ko_context": None, "limitations": ["q12_calculation_failed"]}

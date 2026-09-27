from PySide6.QtWidgets import QApplication
import inspect
from types import SimpleNamespace

from llm.advisor_candidate_contract import evaluate_move_candidate
from llm.advisor_recommendation_readiness import build_recommendation_readiness
from ui.main_window import MainWindow
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _prepared(*candidates):
    return {"status": "ready", "candidates": list(candidates)}


def test_readiness_projects_only_canonical_missing_inputs_and_known_routes():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["attacker.current_hp", "field.weather"]}, "action_order": {"status": "insufficient_context", "missing_inputs": ["opponent.grounded"]}},
        {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["attacker.current_hp"]}},
    ))
    assert readiness["status"] == "incomplete"
    assert readiness["missing"] == [
        {"path": "attacker.current_hp", "label": "Current HP needed", "action": "current_hp"},
        {"path": "field.weather", "label": "Weather not confirmed", "action": "current_field_state"},
        {"path": "opponent.grounded", "label": "Groundedness not confirmed", "action": "current_field_state"},
    ]
    assert readiness["action"] == "current_hp"


def test_readiness_distinguishes_unsupported_and_ignores_irrelevant_unknown_state():
    ready = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "known"}, "unavailable_reasons": ["unrelated_unknown"]},
    ))
    assert ready == {"status": "ready", "missing": [], "unsupported": [], "action": None}

    unsupported = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "unsupported_mechanic", "unsupported_reason": "status_move"}},
    ))
    assert unsupported["status"] == "unsupported"
    assert unsupported["missing"] == []

    item = build_recommendation_readiness(prepared_cycle=_prepared(
        {"mechanics_result": {"status": "insufficient_context", "missing_inputs": ["defender.item"]}},
    ))
    assert item["missing"] == [{"path": "defender.item", "label": "Held item unknown", "action": "current_item"}]
    assert item["action"] == "current_item"


def test_readiness_projects_canonical_missing_inputs_from_nonselectable_candidates():
    readiness = build_recommendation_readiness(prepared_cycle={
        "status": "no_selectable_candidates",
        "candidates": [{
            "mechanics_result": {"status": "unavailable"},
            "move_success": {
                "status": "insufficient_context",
                "missing_inputs": ["field.terrain", "attacker.item"],
            },
        }],
    })

    assert readiness == {
        "status": "incomplete",
        "missing": [
            {"path": "field.terrain", "label": "Terrain not confirmed", "action": "current_field_state"},
            {"path": "attacker.item", "label": "Held item unknown", "action": "current_item"},
        ],
        "unsupported": [],
        "action": "current_item",
    }


def test_legacy_action_order_missing_opponent_action_is_not_a_global_readiness_blocker():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {"status": "known"},
        "action_order": {
            "status": "insufficient_context",
            "missing_inputs": ["opponent_action"],
        },
        "move_success": {"status": "resolved"},
    }))

    assert readiness == {
        "status": "ready",
        "missing": [],
        "unsupported": [],
        "action": None,
    }


def test_other_action_order_missing_authority_remains_globally_blocking():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {"status": "known"},
        "action_order": {
            "status": "insufficient_context",
            "missing_inputs": ["opponent_action", "opponent_final_speed"],
        },
    }))

    assert readiness["status"] == "incomplete"
    assert [entry["path"] for entry in readiness["missing"]] == ["opponent_final_speed"]


def test_move_success_missing_opponent_action_remains_blocking_even_when_action_order_copy_is_filtered():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {"status": "known"},
        "action_order": {
            "status": "insufficient_context",
            "missing_inputs": ["opponent_action"],
        },
        "move_success": {
            "status": "insufficient_context",
            "missing_inputs": ["opponent_action"],
        },
    }))

    assert readiness["status"] == "incomplete"
    assert [entry["path"] for entry in readiness["missing"]] == ["opponent_action"]


def test_exact_selected_opponent_action_readiness_behavior_is_unchanged():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {"status": "known"},
        "action_order": {"status": "acts_first", "missing_inputs": []},
        "move_success": {"status": "resolved"},
    }))

    assert readiness == {
        "status": "ready",
        "missing": [],
        "unsupported": [],
        "action": None,
    }


def test_real_psychic_terrain_move_success_missing_authority_remains_blocking_without_selected_opponent_action():
    candidate = evaluate_move_candidate(
        slot_index=0,
        move="quick",
        battle_snapshot={
            "field_state_context": {
                "current_field": {
                    "weather": "none",
                    "terrain": "psychic",
                    "global_effects": [],
                    "side_effects": [],
                    "status": "user_confirmed",
                    "source": "user_confirmed_current_field_state",
                    "confidence": "known",
                }
            },
            "grounded_context": {
                "opponent": {"status": "unknown", "provenance": "unknown"},
            },
        },
        repositories={
            "quick": {
                "category": "physical",
                "power": 40,
                "type": "normal",
                "target": "selected-pokemon",
                "priority": 1,
            },
        },
    )

    assert candidate["action_order"]["status"] == "insufficient_context"
    assert "opponent_action" in candidate["action_order"]["missing_inputs"]
    assert candidate["move_success"] == {
        "status": "insufficient_context",
        "move_success_status": None,
        "missing_inputs": ["effective_priority"],
    }

    readiness = build_recommendation_readiness(prepared_cycle=_prepared(candidate))
    assert readiness["status"] == "incomplete"
    assert "effective_priority" in [entry["path"] for entry in readiness["missing"]]


def test_readiness_routes_canonical_condition_stage_final_stat_and_battle_format_paths():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {
            "status": "insufficient_context",
            "missing_inputs": [
                "opponent_final_speed",
                "opponent_speed_stage",
                "opponent_paralysis",
                "battle_format",
                "attacker.final_stats",
                "defender.status",
                "attacker.boosts",
            ],
        },
    }))

    by_path = {entry["path"]: entry for entry in readiness["missing"]}
    assert by_path["opponent_final_speed"]["action"] == "current_final_stat"
    assert by_path["opponent_speed_stage"]["action"] == "current_stat_stage"
    assert by_path["opponent_paralysis"]["action"] == "current_condition"
    assert by_path["battle_format"]["action"] == "current_battle_format"
    assert by_path["attacker.final_stats"]["action"] == "current_final_stat"
    assert by_path["defender.status"]["action"] == "current_condition"
    assert by_path["attacker.boosts"]["action"] == "current_stat_stage"
    assert all(entry["label"] != "Required deterministic authority is unavailable" for entry in readiness["missing"])


def test_derived_priority_and_move_success_opponent_action_are_specific_but_non_actionable():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {"status": "known"},
        "action_order": {
            "status": "insufficient_context",
            "missing_inputs": ["opponent_action"],
        },
        "move_success": {
            "status": "insufficient_context",
            "missing_inputs": ["effective_priority", "opponent_action"],
        },
    }))

    assert readiness["status"] == "incomplete"
    by_path = {entry["path"]: entry for entry in readiness["missing"]}
    assert by_path["effective_priority"] == {
        "path": "effective_priority",
        "label": "Priority/action context needed",
        "action": None,
    }
    assert by_path["opponent_action"] == {
        "path": "opponent_action",
        "label": "Opponent action context needed for this mechanic",
        "action": None,
    }


def test_existing_readiness_route_families_remain_unchanged():
    readiness = build_recommendation_readiness(prepared_cycle=_prepared({
        "mechanics_result": {
            "status": "insufficient_context",
            "missing_inputs": [
                "attacker.current_hp",
                "attacker.current_type",
                "attacker.condition",
                "attacker.stat_stage",
                "field.weather",
                "field.terrain",
                "opponent.grounded",
                "attacker.ability",
                "attacker.item",
                "switch_permission",
                "previous_damage",
            ],
        },
    }))
    by_path = {entry["path"]: entry["action"] for entry in readiness["missing"]}
    assert by_path == {
        "attacker.current_hp": "current_hp",
        "attacker.current_type": "current_type",
        "attacker.condition": "current_condition",
        "attacker.stat_stage": "current_stat_stage",
        "field.weather": "current_field_state",
        "field.terrain": "current_field_state",
        "opponent.grounded": "current_field_state",
        "attacker.ability": "current_ability",
        "attacker.item": "current_item",
        "switch_permission": "switch_permission",
        "previous_damage": "current_observed_damage",
    }


def test_panel_exposes_readiness_and_routes_only_existing_confirmation_actions():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.readiness_input_requested.connect(emitted.append)
    panel.set_recommendation_readiness({"status": "incomplete", "missing": [{"label": "Current type needed", "action": "current_type"}], "unsupported": [], "action": "current_type"})
    assert "현재 타입" in panel.readiness_label.text()
    assert panel.readiness_input_button.isVisible() is False  # parent is not shown
    panel._request_readiness_input()
    assert emitted == ["current_type"]
    panel.clear_recommendation_readiness()
    assert "아직 확인되지" in panel.readiness_label.text()


def test_panel_groups_multiple_readiness_gaps_with_distinct_routes_and_unavailable_reasons():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.readiness_input_requested.connect(emitted.append)
    panel.set_recommendation_readiness({
        "status": "incomplete",
        "missing": [
            {"label": "Current HP needed", "action": "current_hp"},
            {"label": "Held item unknown", "action": "current_item"},
            {"label": "Toxic progression authority missing", "action": None},
            {"label": "Current HP needed", "action": "current_hp"},
        ],
        "unsupported": ["This selected mechanic is not supported yet"],
        "action": "current_item",
    })
    text = panel.readiness_label.text()
    assert "입력 가능: 현재 HP; 현재 지닌 도구" in text
    assert "현재 직접 입력 경로 없음: 독성 진행 정보" in text
    assert "선택한 기술의 일부 메커니즘은 아직 지원되지 않습니다." in text
    assert panel.readiness_input_button.text() == "입력하기: 현재 HP"
    assert [button.text() for button in panel._readiness_extra_input_buttons] == ["입력하기: 현재 지닌 도구"]
    panel._request_readiness_input()
    panel._readiness_extra_input_buttons[0].click()
    assert emitted == ["current_hp", "current_item"]
    panel.clear_recommendation_readiness()
    assert panel._readiness_extra_input_buttons == []


def test_panel_groups_new_actionable_and_non_actionable_readiness_gaps_without_generic_fallback():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.readiness_input_requested.connect(emitted.append)
    panel.set_recommendation_readiness({
        "status": "incomplete",
        "missing": [
            {"path": "opponent_final_speed", "label": "Opponent final Speed needed", "action": "current_final_stat"},
            {"path": "attacker.condition", "label": "Attacker current condition needed", "action": "current_condition"},
            {"path": "field.terrain", "label": "Terrain not confirmed", "action": "current_field_state"},
            {"path": "effective_priority", "label": "Priority/action context needed", "action": None},
            {"path": "opponent_action", "label": "Opponent action context needed for this mechanic", "action": None},
            {"path": "defender.final_stats", "label": "Defender final stats needed", "action": "current_final_stat"},
        ],
        "unsupported": [],
        "action": "current_final_stat",
    })

    text = panel.readiness_label.text()
    assert "입력 가능: 확정 실능력치; 현재 상태이상; 현재 전장 상태" in text
    assert "현재 직접 입력 경로 없음: 우선도 판정에 필요한 전투 정보; 이 기술 판정에 필요한 상대 행동 정보" in text
    assert "현재 직접 확인할 수 없는 추가 전투 정보" not in text
    assert panel.readiness_input_button.text() == "입력하기: 확정 실능력치"
    assert [button.text() for button in panel._readiness_extra_input_buttons] == [
        "입력하기: 현재 상태이상",
        "입력하기: 현재 전장 상태",
    ]
    panel._request_readiness_input()
    panel._readiness_extra_input_buttons[0].click()
    panel._readiness_extra_input_buttons[1].click()
    assert emitted == ["current_final_stat", "current_condition", "current_field_state"]


def test_main_window_readiness_routes_existing_final_stat_and_battle_format_dialogs():
    source = inspect.getsource(MainWindow._open_readiness_input)
    assert '"current_final_stat": self._open_current_final_stat_dialog' in source
    assert '"current_battle_format": self._open_current_battle_format_dialog' in source
    assert "handler()" in source
    assert "self._check_structured_recommendation_readiness()" in source


def test_panel_emits_final_stat_and_battle_format_readiness_actions():
    QApplication.instance() or QApplication([])
    panel = LLMAdvicePanel()
    emitted: list[str] = []
    panel.readiness_input_requested.connect(emitted.append)

    panel.set_recommendation_readiness({
        "status": "incomplete",
        "missing": [{"path": "opponent_final_speed", "label": "Opponent final Speed needed", "action": "current_final_stat"}],
        "unsupported": [],
        "action": "current_final_stat",
    })
    panel._request_readiness_input()

    panel.set_recommendation_readiness({
        "status": "incomplete",
        "missing": [{"path": "battle_format", "label": "Battle format not confirmed", "action": "current_battle_format"}],
        "unsupported": [],
        "action": "current_battle_format",
    })
    panel._request_readiness_input()

    assert emitted == ["current_final_stat", "current_battle_format"]


def test_main_window_readiness_uses_frozen_preparation_without_a_provider_call():
    source = inspect.getsource(MainWindow._check_structured_recommendation_readiness)
    assert "prepare_ui_recommendation_cycle" in source
    assert "build_recommendation_readiness" in source
    assert "run_structured_ui_recommendation" not in source
    assert "_build_current_structured_analysis_battle_input" in source
    shared = inspect.getsource(MainWindow._build_current_structured_analysis_battle_input)
    assert "include_current_field_state_confirmation=True" in shared
    assert "include_current_hp_confirmations=True" in shared
    assert "include_direct_mechanics_context=True" in shared


def test_item_shortcut_reuses_existing_item_profile_flow_with_identity_check():
    source = inspect.getsource(MainWindow._open_readiness_input)
    assert 'action == "current_item"' in source
    assert 'self._on_item_profile_requested("team_my", slot_index)' in source
    assert "current_session != session_id" in source
    assert 'self.selected_slots.get("team_my") != slot_index' in source
    assert "getattr(view, \"en\", None) != pokemon_id" in source
    assert "self._check_structured_recommendation_readiness()" in source


def test_existing_readiness_routes_refresh_the_current_canonical_projection():
    source = inspect.getsource(MainWindow._open_readiness_input)
    assert "handler()" in source
    assert 'getattr(self, "_recommendation_readiness_owner", None) is not None' in source
    assert "self._check_structured_recommendation_readiness()" in source


def test_paired_hp_apply_validates_each_owner_and_filters_stale_side_before_snapshot():
    apply_source = inspect.getsource(MainWindow._open_current_hp_dialog)
    payload_source = inspect.getsource(MainWindow._build_llm_battle_input)
    assert "dialog.current_hp_confirmations" in apply_source
    assert "owner != self._current_hp_owner_for_side(entry[\"side\"])" in apply_source
    assert "owner != self._current_hp_owner_for_side(side)" in payload_source


def test_hp_owner_identity_changes_when_a_replacement_occupies_the_same_side():
    panels = {
        ("team_my", 0): SimpleNamespace(pokemon_view=SimpleNamespace(en="pikachu")),
        ("team_enemy", 1): SimpleNamespace(pokemon_view=SimpleNamespace(en="eevee")),
    }
    window = SimpleNamespace(
        selected_slots={"team_my": 0, "team_enemy": 1},
        _active_session_id=lambda: "s",
        _slot_panel=lambda column, slot: panels[(column, slot)],
    )
    owner = MainWindow._current_hp_owner_for_side(window, "self")
    panels[("team_my", 0)].pokemon_view = SimpleNamespace(en="raichu")
    assert owner == ("s", 0, "pikachu")
    assert MainWindow._current_hp_owner_for_side(window, "self") == ("s", 0, "raichu")

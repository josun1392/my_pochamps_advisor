from __future__ import annotations

from copy import deepcopy

import pytest

from llm import advisor_client
from llm.advisor_client import build_ui_advice_payload
from llm.advisor_damage_estimate import attach_selected_move_damage_estimate
from llm.advisor_payload_contract import TURN_SNAPSHOT_KNOWN_LIMITATIONS
from llm.advisor_turn_snapshot import (
    build_turn_snapshot_from_battle_input,
    try_build_turn_snapshot_from_battle_input,
)
from scripts.spike_turn_snapshot_debug import build_turn_snapshot_debug_report
from tests.test_advisor_damage_estimate import _battle_input, _flamethrower, _item_profiles


def test_build_turn_snapshot_from_valid_battle_input_maps_active_slots() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="choice-scarf", opponent_item="focus-sash")
    payload["pokemon"]["my_active"]["hp_percent"] = 64
    payload["pokemon"]["opponent_active"]["hp_percent"] = 37.5

    snapshot = build_turn_snapshot_from_battle_input(payload)

    player = snapshot.battle_state.active_player
    opponent = snapshot.battle_state.active_opponent
    assert player is not None
    assert opponent is not None
    assert player.side == "player"
    assert player.slot_index == 0
    assert player.species_id == "charizard"
    assert player.species_name == "Charizard"
    assert player.current_hp_percent == 64
    assert player.known_item_id == "choice-scarf"
    assert player.item_status == "user_confirmed"
    assert dict(player.stat_stages) == {}
    assert player.major_status is None
    assert player.volatile_conditions == ()
    assert opponent.side == "opponent"
    assert opponent.species_id == "garchomp"
    assert opponent.current_hp_percent == 37.5
    assert opponent.known_item_id == "focus-sash"
    assert opponent.item_status == "user_confirmed"
    assert snapshot.battle_state.weather is None
    assert snapshot.battle_state.terrain is None
    assert dict(snapshot.battle_state.field_conditions) == {}
    assert snapshot.battle_state.turn_number is None


def test_build_turn_snapshot_maps_selected_move_to_turn_input() -> None:
    snapshot = build_turn_snapshot_from_battle_input(_battle_input(selected_move=_flamethrower()))

    assert snapshot.turn_input.selected_move_id == "flamethrower"
    assert snapshot.turn_input.acting_side == "player"
    assert snapshot.turn_input.target_side == "opponent"


def test_build_turn_snapshot_keeps_missing_values_safe() -> None:
    snapshot = build_turn_snapshot_from_battle_input({})

    player = snapshot.battle_state.active_player
    opponent = snapshot.battle_state.active_opponent
    assert player is not None
    assert opponent is not None
    assert player.species_id is None
    assert player.species_name is None
    assert player.current_hp_percent is None
    assert player.known_item_id is None
    assert player.item_status == "unknown"
    assert opponent.item_status == "unknown"
    assert snapshot.turn_input.selected_move_id is None


def test_build_turn_snapshot_maps_absent_and_inferred_item_statuses() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = {
        "my_active": {
            "status": "system_default_none",
            "item_id": None,
        },
        "opponent_active": {
            "status": "inferred",
            "item_id": "focus-sash",
        },
    }

    snapshot = build_turn_snapshot_from_battle_input(payload)

    assert snapshot.battle_state.active_player is not None
    assert snapshot.battle_state.active_opponent is not None
    assert snapshot.battle_state.active_player.item_status == "absent"
    assert snapshot.battle_state.active_player.known_item_id is None
    assert snapshot.battle_state.active_opponent.item_status == "inferred"
    assert snapshot.battle_state.active_opponent.known_item_id == "focus-sash"


def test_strict_turn_snapshot_builder_raises_for_invalid_state() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["my_active"]["hp_percent"] = 150

    with pytest.raises(ValueError):
        build_turn_snapshot_from_battle_input(payload)


def test_fallback_turn_snapshot_builder_returns_none_for_invalid_state() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["my_active"]["hp_percent"] = 150

    assert try_build_turn_snapshot_from_battle_input(payload) is None


def test_advisor_payload_can_include_built_turn_snapshot() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="choice-scarf")
    payload = attach_selected_move_damage_estimate(payload)
    snapshot = build_turn_snapshot_from_battle_input(payload)

    advice_payload = build_ui_advice_payload(payload, turn_snapshot=snapshot)

    assert advice_payload["turn_snapshot"] == snapshot.to_dict()
    assert advice_payload["turn_snapshot"]["battle_state"]["active_player"]["known_item_id"] == "choice-scarf"


def test_turn_snapshot_absent_keeps_payload_unchanged() -> None:
    payload = attach_selected_move_damage_estimate(_battle_input(selected_move=_flamethrower()))

    assert build_ui_advice_payload(payload, turn_snapshot=None) == build_ui_advice_payload(payload)


def test_turn_snapshot_does_not_change_damage_ko_or_item_context_payload() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="choice-scarf")
    payload = attach_selected_move_damage_estimate(payload)
    snapshot = build_turn_snapshot_from_battle_input(payload)

    base_payload = build_ui_advice_payload(payload)
    snapshot_payload = build_ui_advice_payload(payload, turn_snapshot=snapshot)
    snapshot_payload_without_turn_snapshot = deepcopy(snapshot_payload)
    snapshot_payload_without_turn_snapshot.pop("turn_snapshot")
    for limitation in snapshot_payload_without_turn_snapshot["scenario"]["known_limitations"][:]:
        if limitation.startswith("turn_snapshot"):
            snapshot_payload_without_turn_snapshot["scenario"]["known_limitations"].remove(limitation)
        elif "turn_snapshot alone" in limitation:
            snapshot_payload_without_turn_snapshot["scenario"]["known_limitations"].remove(limitation)

    assert snapshot_payload_without_turn_snapshot == base_payload


def test_run_ui_selected_advice_adds_snapshot_when_builder_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        captured["prompt"] = prompt
        return "ok", {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"patched": True})

    advisor_client.run_ui_selected_advice(_battle_input(selected_move=_flamethrower()))

    assert '"turn_snapshot"' in captured["prompt"]
    assert "selected/pre-turn known state context only" in captured["prompt"]


def test_run_ui_selected_advice_falls_back_when_snapshot_builder_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def fake_call_gemini(prompt: str, model: str) -> tuple[str, dict[str, int]]:
        captured["prompt"] = prompt
        return "ok", {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}

    payload = _battle_input(selected_move=_flamethrower())
    payload["pokemon"]["my_active"]["hp_percent"] = 150

    monkeypatch.setattr(advisor_client, "call_gemini", fake_call_gemini)
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"patched": True})

    advisor_client.run_ui_selected_advice(payload)

    assert '"turn_snapshot"' not in captured["prompt"]
    assert "selected/pre-turn known state context only" not in captured["prompt"]


def test_turn_snapshot_payload_smoke_preflight_present_and_fallback_paths() -> None:
    payload = _battle_input(selected_move=_flamethrower())
    payload["item_profiles"] = _item_profiles(my_item="choice-scarf", opponent_item="focus-sash")
    payload["pokemon"]["my_active"]["hp_percent"] = 88
    payload["pokemon"]["opponent_active"]["hp_percent"] = 41
    payload = attach_selected_move_damage_estimate(payload)
    snapshot = build_turn_snapshot_from_battle_input(payload)

    base_payload = build_ui_advice_payload(payload)
    snapshot_payload = build_ui_advice_payload(payload, turn_snapshot=snapshot)

    assert snapshot_payload["turn_snapshot"]["battle_state"]["active_player"]["species_id"] == "charizard"
    assert snapshot_payload["turn_snapshot"]["battle_state"]["active_opponent"]["species_id"] == "garchomp"
    assert snapshot_payload["turn_snapshot"]["battle_state"]["active_player"]["current_hp_percent"] == 88
    assert snapshot_payload["turn_snapshot"]["battle_state"]["active_opponent"]["current_hp_percent"] == 41
    assert snapshot_payload["turn_snapshot"]["battle_state"]["active_player"]["known_item_id"] == "choice-scarf"
    assert snapshot_payload["turn_snapshot"]["battle_state"]["active_player"]["item_status"] == "user_confirmed"
    assert snapshot_payload["turn_snapshot"]["turn_input"]["selected_move_id"] == "flamethrower"
    for limitation in TURN_SNAPSHOT_KNOWN_LIMITATIONS:
        assert limitation in snapshot_payload["scenario"]["known_limitations"]

    snapshot_payload_without_snapshot = deepcopy(snapshot_payload)
    snapshot_payload_without_snapshot.pop("turn_snapshot")
    for limitation in TURN_SNAPSHOT_KNOWN_LIMITATIONS:
        snapshot_payload_without_snapshot["scenario"]["known_limitations"].remove(limitation)
    assert snapshot_payload_without_snapshot == base_payload

    invalid_payload = deepcopy(payload)
    invalid_payload["pokemon"]["my_active"]["hp_percent"] = 120
    assert try_build_turn_snapshot_from_battle_input(invalid_payload) is None
    assert build_ui_advice_payload(invalid_payload, turn_snapshot=None) == build_ui_advice_payload(invalid_payload)


def test_turn_snapshot_debug_report_is_local_dry_run_only() -> None:
    report = build_turn_snapshot_debug_report()

    assert report["report_version"] == "v4.8"
    assert report["actual_gemini_call_executed"] is False
    assert report["vertex_ai_call_executed"] is False
    assert report["is_full_turn_engine_result"] is False
    assert report["turn_snapshot_built"] is True
    assert report["summary"] == {
        "player_species": "charizard",
        "opponent_species": "garchomp",
        "player_hp_percent": 88,
        "opponent_hp_percent": 41,
        "player_item": {
            "item_id": "choice-scarf",
            "status": "user_confirmed",
        },
        "opponent_item": {
            "item_id": "focus-sash",
            "status": "user_confirmed",
        },
        "selected_move_id": "flamethrower",
    }
    assert report["payload_checks"] == {
        "top_level_turn_snapshot_present": True,
        "turn_snapshot_absent_without_snapshot": True,
        "limitations_guard_present": True,
        "payload_matches_absent_after_removing_snapshot_fields": True,
        "fallback_helper_returns_none_for_invalid_hp": True,
    }
    assert report["non_goals"] == {
        "full_turn_engine": False,
        "item_trigger_evaluation": False,
        "item_consumption": False,
        "hp_update_logic": False,
        "speed_order_simulation": False,
    }

from llm.advisor_turn_snapshot import capture_ui_current_state_provenance


def test_ui_capture_binds_hp_condition_and_event_to_active_identity_and_session():
    payload = {"pokemon": {"my_active": {"name_en": "pikachu", "slot_index": 0}, "opponent_active": {"name_en": "eevee", "slot_index": 1}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": 50}]}, "condition_context": {"current_conditions": [{"side": "opponent", "condition_type": "burn"}]}, "item_event_context": {"events": [{"side": "opponent", "item": "focus-sash"}]}}
    captured = capture_ui_current_state_provenance(payload, session_id="s1")
    assert captured["current_hp_context"]["current_hp"][0]["provenance"]["pokemon_id"] == "pikachu"
    assert captured["condition_context"]["current_conditions"][0]["provenance"]["slot_index"] == 1
    assert captured["item_event_context"]["events"][0]["provenance"]["session_id"] == "s1"


def test_missing_active_identity_is_not_promoted_to_current_provenance():
    captured = capture_ui_current_state_provenance({"pokemon": {"my_active": {}, "opponent_active": {}}, "current_hp_context": {"current_hp": [{"side": "self", "current_hp": 50}]}}, session_id="s1")
    assert "provenance" not in captured["current_hp_context"]["current_hp"][0]

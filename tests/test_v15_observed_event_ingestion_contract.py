from copy import deepcopy

from llm.advisor_turn_snapshot import (
    build_turn_snapshot_from_battle_input,
    capture_ui_current_state_provenance,
)


def _base_input():
    return {
        "pokemon": {
            "my_active": {"name_en": "pikachu", "slot_index": 0},
            "opponent_active": {"name_en": "eevee", "slot_index": 1},
        },
        "moves": {"my_available_moves": [{"slot_index": 0, "move_id": "tackle"}]},
    }


def _event(**overrides):
    event = {
        "side": "self",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": 1,
    }
    event.update(overrides)
    return event


def test_observed_events_are_structured_only_canonical_and_detached():
    base = _base_input()
    raw_event = _event(note={"visible": True})
    captured = capture_ui_current_state_provenance(
        base, session_id="ui-session-0", observed_events=[raw_event, deepcopy(raw_event)]
    )

    assert "item_event_context" not in base
    assert len(captured["item_event_context"]["observed_events"]) == 1
    event = captured["item_event_context"]["observed_events"][0]
    assert event["event_kind"] == "item_activation_observed"
    assert event["observed"] is True and event["confirmed"] is True
    assert event["provenance"]["session_id"] == "ui-session-0"
    assert event["payload"]["item"] == "focus-sash"
    assert "known_item" not in event

    snapshot = build_turn_snapshot_from_battle_input(captured)
    raw_event["note"]["visible"] = False
    stored = snapshot.to_dict()["current_state"]["item_event_context"]["observed_events"][0]
    assert stored["payload"]["note"] == {"visible": True}


def test_wrong_owner_or_stale_session_event_is_excluded_without_retagging():
    captured = capture_ui_current_state_provenance(
        _base_input(),
        session_id="ui-session-1",
        observed_events=[
            _event(slot_index=1),
            _event(pokemon_id="raichu"),
            _event(session_id="ui-session-0"),
            _event(side="opponent", pokemon_id="eevee", slot_index=1),
        ],
    )

    events = captured["item_event_context"]["observed_events"]
    assert len(events) == 1
    assert events[0]["side"] == "opponent"
    assert events[0]["pokemon_id"] == "eevee"
    assert events[0]["session_id"] == "ui-session-1"


def test_ability_and_condition_events_remain_events_not_current_state_facts():
    captured = capture_ui_current_state_provenance(
        _base_input(),
        session_id="ui-session-0",
        observed_events=[
            _event(event_kind="ability_activation_observed", ability="unknown", event_type=None),
            _event(event_kind="condition_application_observed", condition_type="burn", event_type=None),
        ],
    )

    events = captured["item_event_context"]["observed_events"]
    assert [event["event_kind"] for event in events] == [
        "ability_activation_observed", "condition_application_observed"
    ]
    assert all(event["trust"] == "observed_event" for event in events)
    assert "ability_context" not in captured and "condition_context" not in captured

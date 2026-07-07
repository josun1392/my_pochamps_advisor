from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest
from PySide6.QtWidgets import QApplication, QDialog

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import validate_explicit_user_item_event_confirmation
from tests.test_advisor_payload_contract import _move, _opponent_move_ui_advice_flow_payload, _panel, _window
from tests.test_field_profile_button_integration_contract import _field_profiles_fixture
from ui.widgets.llm_advice_panel import LLMAdvicePanel


_ITEM_EVENT_RESULT_FORBIDDEN_FIELDS = frozenset(
    {
        "berry_recovered_exact_hp",
        "exact_damage",
        "exact_hp",
        "focus_sash_post_hit_hp_1",
        "item_damage_modifier_applied",
        "item_speed_modifier_applied",
        "post_turn_hp_from_item",
        "post_turn_item_state",
        "quick_claw_activated_by_rng",
        "resolved_item_effect",
        "rng_roll",
        "speed_order_override",
    }
)

_ITEM_EVENT_PROMPT_FORBIDDEN_PHRASES = (
    "observed item event",
    "item_event_context",
    "focus sash activated",
    "quick claw activated",
    "berry was consumed",
    "resolved item effect",
    "post-turn item state",
    "exact damage",
    "rng roll",
    "speed order override",
)


class _ProviderSpy:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        self.calls += 1
        raise AssertionError("item event button path must not call provider")


class _FakeItemEventDialog:
    def __init__(
        self,
        *,
        current_events: list[dict[str, Any]] | None,
        result_events: list[dict[str, Any]],
        result_code: QDialog.DialogCode,
    ) -> None:
        self.current_events = deepcopy(current_events)
        self._result_events = deepcopy(result_events)
        self._result_code = result_code
        self.exec_calls = 0
        self.reset_calls = 0

    @property
    def item_event_confirmations(self) -> list[dict[str, Any]]:
        return deepcopy(self._result_events)

    def reset_draft(self) -> None:
        self.reset_calls += 1
        self._result_events = []

    def exec(self) -> QDialog.DialogCode:
        self.exec_calls += 1
        return self._result_code


class _ItemEventButtonContractController:
    """Test-only seam for future LLMAdvicePanel/MainWindow item-event wiring."""

    def __init__(self, *, dialog_factory: Any, provider_call: Any) -> None:
        self._item_event_confirmations: list[dict[str, Any]] = []
        self.item_event_requests = 0
        self.advice_requests = 0
        self._dialog_factory = dialog_factory
        self._provider_call = provider_call

    def open_item_event_dialog(self) -> _FakeItemEventDialog:
        self.item_event_requests += 1
        dialog = self._dialog_factory(current_events=self._item_event_confirmations)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self._item_event_confirmations = self._validated_events(dialog.item_event_confirmations)
        return dialog

    def click_item_event_button(self) -> _FakeItemEventDialog:
        return self.open_item_event_dialog()

    def request_advice(self) -> None:
        self.advice_requests += 1
        self._provider_call()

    def build_battle_input(self) -> dict[str, Any]:
        payload = deepcopy(_opponent_move_ui_advice_flow_payload())
        payload["field_profiles"] = _field_profiles_fixture()
        return payload

    @staticmethod
    def _validated_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [validate_explicit_user_item_event_confirmation(event) for event in events]


def _valid_item_event(**overrides: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": 5,
        "note": "User saw Focus Sash activation text.",
    }
    event.update(overrides)
    return event


def _valid_item_event_missing(field_name: str) -> dict[str, Any]:
    event = _valid_item_event()
    event.pop(field_name)
    return event


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def test_item_event_button_future_open_action_does_not_request_advice_or_provider_call() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    provider_call = _ProviderSpy()
    controller = _ItemEventButtonContractController(
        dialog_factory=lambda *, current_events: _FakeItemEventDialog(
            current_events=current_events,
            result_events=[_valid_item_event()],
            result_code=QDialog.DialogCode.Accepted,
        ),
        provider_call=provider_call,
    )

    dialog = controller.click_item_event_button()

    assert dialog.exec_calls == 1
    assert controller.item_event_requests == 1
    assert controller.advice_requests == 0
    assert provider_call.calls == 0


def test_item_event_button_apply_saves_valid_confirmations_to_session_state() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    event = _valid_item_event()
    provider_call = _ProviderSpy()
    controller = _ItemEventButtonContractController(
        dialog_factory=lambda *, current_events: _FakeItemEventDialog(
            current_events=current_events,
            result_events=[event],
            result_code=QDialog.DialogCode.Accepted,
        ),
        provider_call=provider_call,
    )

    dialog = controller.open_item_event_dialog()

    assert dialog.current_events == []
    assert controller._item_event_confirmations == [event]
    _assert_item_event_result_fields_absent(controller._item_event_confirmations)
    assert provider_call.calls == 0


def test_item_event_button_cancel_preserves_previous_session_state() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    previous_events = [_valid_item_event(item="leftovers", event_type="item_recovery_observed", turn=3)]
    draft_events = [_valid_item_event(item="quick-claw", event_type="item_activation_observed", turn=4)]
    controller = _ItemEventButtonContractController(
        dialog_factory=lambda *, current_events: _FakeItemEventDialog(
            current_events=current_events,
            result_events=draft_events,
            result_code=QDialog.DialogCode.Rejected,
        ),
        provider_call=_ProviderSpy(),
    )
    controller._item_event_confirmations = deepcopy(previous_events)

    dialog = controller.open_item_event_dialog()

    assert dialog.current_events == previous_events
    assert controller._item_event_confirmations == previous_events


def test_item_event_button_reset_cancel_preserves_previous_session_state() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    previous_events = [_valid_item_event(item="sitrus-berry", event_type="item_consumption_observed", turn=6)]

    def dialog_factory(*, current_events: list[dict[str, Any]]) -> _FakeItemEventDialog:
        dialog = _FakeItemEventDialog(
            current_events=current_events,
            result_events=previous_events,
            result_code=QDialog.DialogCode.Rejected,
        )
        dialog.reset_draft()
        return dialog

    controller = _ItemEventButtonContractController(
        dialog_factory=dialog_factory,
        provider_call=_ProviderSpy(),
    )
    controller._item_event_confirmations = deepcopy(previous_events)

    dialog = controller.open_item_event_dialog()

    assert dialog.reset_calls == 1
    assert dialog.item_event_confirmations == []
    assert controller._item_event_confirmations == previous_events


def test_item_event_button_reset_apply_stores_empty_session_state() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    previous_events = [_valid_item_event(item="focus-sash", event_type="item_activation_observed", turn=5)]

    def dialog_factory(*, current_events: list[dict[str, Any]]) -> _FakeItemEventDialog:
        dialog = _FakeItemEventDialog(
            current_events=current_events,
            result_events=previous_events,
            result_code=QDialog.DialogCode.Accepted,
        )
        dialog.reset_draft()
        return dialog

    controller = _ItemEventButtonContractController(
        dialog_factory=dialog_factory,
        provider_call=_ProviderSpy(),
    )
    controller._item_event_confirmations = deepcopy(previous_events)

    dialog = controller.open_item_event_dialog()

    assert dialog.reset_calls == 1
    assert dialog.item_event_confirmations == []
    assert controller._item_event_confirmations == []


@pytest.mark.parametrize(
    "invalid_event",
    [
        _valid_item_event_missing("side"),
        _valid_item_event_missing("item"),
        _valid_item_event_missing("event_type"),
        _valid_item_event_missing("status"),
        _valid_item_event_missing("source"),
        _valid_item_event(source="battle_log_observed"),
        _valid_item_event(status="inferred"),
        _valid_item_event(event_type="resolved_item_effect"),
        _valid_item_event(event_type="post_turn_item_state"),
        _valid_item_event(exact_hp=1),
        _valid_item_event(exact_damage=100),
        _valid_item_event(rng_roll=42),
        _valid_item_event(speed_order_override=True),
    ],
)
def test_item_event_button_invalid_event_is_not_saved(invalid_event: dict[str, Any]) -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    previous_events = [_valid_item_event(item="choice-scarf", event_type="item_reveal_observed", turn=2)]
    controller = _ItemEventButtonContractController(
        dialog_factory=lambda *, current_events: _FakeItemEventDialog(
            current_events=current_events,
            result_events=[invalid_event],
            result_code=QDialog.DialogCode.Accepted,
        ),
        provider_call=_ProviderSpy(),
    )
    controller._item_event_confirmations = deepcopy(previous_events)

    with pytest.raises(ValueError):
        controller.open_item_event_dialog()

    assert controller._item_event_confirmations == previous_events


def test_item_event_button_contract_does_not_add_real_panel_button_or_change_field_button() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    advice_requests = 0
    field_profile_requests = 0

    def record_advice_request() -> None:
        nonlocal advice_requests
        advice_requests += 1

    def record_field_profile_request() -> None:
        nonlocal field_profile_requests
        field_profile_requests += 1

    panel.advice_requested.connect(record_advice_request)
    panel.field_profile_requested.connect(record_field_profile_request)

    assert panel.turn_pipeline_checkbox.isChecked() is False
    assert panel.field_profile_button.objectName() == "fieldProfileButton"
    assert not hasattr(panel, "item_event_button")
    assert not hasattr(panel, "item_event_requested")

    panel.field_profile_button.click()

    assert field_profile_requests == 1
    assert advice_requests == 0


def test_item_event_button_contract_does_not_change_existing_field_state_gate() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    my_panel = _panel("garchomp", selected_move_index=0, selected_moves=[_move("earthquake")])
    opponent_panel = _panel("charizard", selected_move_index=0, selected_moves=[_move("flamethrower")])
    window = _window(my_panel, opponent_panel)
    window._field_profiles = _field_profiles_fixture()

    battle_input = window._build_llm_battle_input()
    off_prompt = advisor_client._build_ui_selected_prompt(
        battle_input,
        enable_turn_pipeline=panel.turn_pipeline_enabled(),
        enable_turn_order_context=panel.turn_pipeline_enabled(),
        enable_opponent_move_context=panel.turn_pipeline_enabled(),
        enable_battle_state_context=panel.turn_pipeline_enabled(),
    )
    off_payload = _prompt_payload(off_prompt)

    panel.turn_pipeline_checkbox.setChecked(True)
    on_prompt = advisor_client._build_ui_selected_prompt(
        battle_input,
        enable_turn_pipeline=panel.turn_pipeline_enabled(),
        enable_turn_order_context=panel.turn_pipeline_enabled(),
        enable_opponent_move_context=panel.turn_pipeline_enabled(),
        enable_battle_state_context=panel.turn_pipeline_enabled(),
    )
    on_payload = _prompt_payload(on_prompt)

    assert "battle_state_context" not in off_payload
    assert "field_profiles" not in off_payload
    assert '"field_profiles"' not in off_prompt
    assert "field_profiles" not in on_payload
    assert on_payload["battle_state_context"]["field"]["weather"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "rain",
    }


def test_item_event_button_session_state_is_not_mapped_into_prompt_payload_yet() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    controller = _ItemEventButtonContractController(
        dialog_factory=lambda *, current_events: _FakeItemEventDialog(
            current_events=current_events,
            result_events=[
                _valid_item_event(item="focus-sash", event_type="item_activation_observed", turn=5),
                _valid_item_event(item="quick-claw", event_type="item_activation_observed", turn=6),
                _valid_item_event(item="sitrus-berry", event_type="item_consumption_observed", turn=7),
            ],
            result_code=QDialog.DialogCode.Accepted,
        ),
        provider_call=_ProviderSpy(),
    )
    controller.open_item_event_dialog()

    off_prompt = advisor_client._build_ui_selected_prompt(
        controller.build_battle_input(),
        enable_turn_pipeline=panel.turn_pipeline_enabled(),
        enable_turn_order_context=panel.turn_pipeline_enabled(),
        enable_opponent_move_context=panel.turn_pipeline_enabled(),
        enable_battle_state_context=panel.turn_pipeline_enabled(),
    )
    off_payload = _prompt_payload(off_prompt)

    panel.turn_pipeline_checkbox.setChecked(True)
    on_prompt = advisor_client._build_ui_selected_prompt(
        controller.build_battle_input(),
        enable_turn_pipeline=panel.turn_pipeline_enabled(),
        enable_turn_order_context=panel.turn_pipeline_enabled(),
        enable_opponent_move_context=panel.turn_pipeline_enabled(),
        enable_battle_state_context=panel.turn_pipeline_enabled(),
    )
    on_payload = _prompt_payload(on_prompt)

    assert "item_event_confirmations" not in off_payload
    assert "item_event_context" not in off_payload
    assert "item_event_confirmations" not in on_payload
    assert "item_event_context" not in on_payload
    _assert_item_event_result_fields_absent(off_payload)
    _assert_item_event_result_fields_absent(on_payload)
    _assert_item_event_prompt_forbidden_phrases_absent(off_prompt)
    _assert_item_event_prompt_forbidden_phrases_absent(on_prompt)

def _assert_item_event_result_fields_absent(value: object) -> None:
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in _ITEM_EVENT_RESULT_FORBIDDEN_FIELDS
            _assert_item_event_result_fields_absent(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_item_event_result_fields_absent(child_value)


def _assert_item_event_prompt_forbidden_phrases_absent(prompt: str) -> None:
    prompt_lower = prompt.lower()
    for phrase in _ITEM_EVENT_PROMPT_FORBIDDEN_PHRASES:
        assert phrase not in prompt_lower

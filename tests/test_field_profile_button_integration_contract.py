from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QApplication, QDialog

import llm.advisor_client as advisor_client
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload
from ui.widgets.field_profile_dialog import default_field_profiles, user_confirmed_field_profile
from ui.widgets.llm_advice_panel import LLMAdvicePanel


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _field_profiles_fixture() -> dict[str, dict[str, Any]]:
    return {
        "weather": user_confirmed_field_profile("rain"),
        "terrain": user_confirmed_field_profile("electric_terrain"),
        "room": user_confirmed_field_profile("trick_room"),
        "screens": user_confirmed_field_profile({"self": ["reflect"], "opponent": ["light_screen"]}),
        "hazards": user_confirmed_field_profile({"self": [], "opponent": ["stealth_rock"]}),
    }


class _FakeFieldProfileDialog:
    def __init__(
        self,
        *,
        current_profiles: dict[str, Any] | None,
        result_profiles: dict[str, Any] | None,
        result_code: QDialog.DialogCode,
    ) -> None:
        self.current_profiles = deepcopy(current_profiles)
        self._result_profiles = deepcopy(result_profiles)
        self._result_code = result_code
        self.exec_calls = 0

    @property
    def field_profiles(self) -> dict[str, Any] | None:
        return deepcopy(self._result_profiles)

    def exec(self) -> QDialog.DialogCode:
        self.exec_calls += 1
        return self._result_code


class _ProviderSpy:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        self.calls += 1
        raise AssertionError("field profile dialog button path must not call provider")


class _FieldProfileButtonContractController:
    """Test-only seam for the future MainWindow field-profile button handler."""

    def __init__(self, *, dialog_factory: Any, provider_call: Any) -> None:
        self.field_profiles: dict[str, Any] | None = None
        self._dialog_factory = dialog_factory
        self._provider_call = provider_call

    def open_field_profile_dialog(self) -> _FakeFieldProfileDialog:
        dialog = self._dialog_factory(current_profiles=self.field_profiles)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            self.field_profiles = dialog.field_profiles
        return dialog

    def build_battle_input(self) -> dict[str, Any]:
        payload = deepcopy(_opponent_move_ui_advice_flow_payload())
        if self.field_profiles is not None:
            payload["field_profiles"] = deepcopy(self.field_profiles)
        return payload


def test_field_profile_button_contract_open_apply_stores_session_state_without_provider_call() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    provider_call = _ProviderSpy()
    profiles = _field_profiles_fixture()

    def dialog_factory(*, current_profiles: dict[str, Any] | None) -> _FakeFieldProfileDialog:
        return _FakeFieldProfileDialog(
            current_profiles=current_profiles,
            result_profiles=profiles,
            result_code=QDialog.DialogCode.Accepted,
        )

    controller = _FieldProfileButtonContractController(
        dialog_factory=dialog_factory,
        provider_call=provider_call,
    )

    dialog = controller.open_field_profile_dialog()

    assert dialog.exec_calls == 1
    assert dialog.current_profiles is None
    assert controller.field_profiles == profiles
    assert provider_call.calls == 0


def test_field_profile_button_contract_cancel_preserves_previous_session_state() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    provider_call = _ProviderSpy()
    previous_profiles = _field_profiles_fixture()
    rejected_profiles = default_field_profiles()

    def dialog_factory(*, current_profiles: dict[str, Any] | None) -> _FakeFieldProfileDialog:
        return _FakeFieldProfileDialog(
            current_profiles=current_profiles,
            result_profiles=rejected_profiles,
            result_code=QDialog.DialogCode.Rejected,
        )

    controller = _FieldProfileButtonContractController(
        dialog_factory=dialog_factory,
        provider_call=provider_call,
    )
    controller.field_profiles = deepcopy(previous_profiles)

    dialog = controller.open_field_profile_dialog()

    assert dialog.exec_calls == 1
    assert dialog.current_profiles == previous_profiles
    assert controller.field_profiles == previous_profiles
    assert provider_call.calls == 0


def test_field_profile_button_contract_reset_unknown_apply_stores_unknown_profiles() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    provider_call = _ProviderSpy()
    previous_profiles = _field_profiles_fixture()
    reset_profiles = default_field_profiles()

    def dialog_factory(*, current_profiles: dict[str, Any] | None) -> _FakeFieldProfileDialog:
        return _FakeFieldProfileDialog(
            current_profiles=current_profiles,
            result_profiles=reset_profiles,
            result_code=QDialog.DialogCode.Accepted,
        )

    controller = _FieldProfileButtonContractController(
        dialog_factory=dialog_factory,
        provider_call=provider_call,
    )
    controller.field_profiles = deepcopy(previous_profiles)

    dialog = controller.open_field_profile_dialog()

    assert dialog.exec_calls == 1
    assert dialog.current_profiles == previous_profiles
    assert controller.field_profiles == reset_profiles
    assert provider_call.calls == 0


def test_field_profile_button_contract_saved_state_respects_limited_context_gate() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    controller = _FieldProfileButtonContractController(
        dialog_factory=lambda *, current_profiles: _FakeFieldProfileDialog(
            current_profiles=current_profiles,
            result_profiles=_field_profiles_fixture(),
            result_code=QDialog.DialogCode.Accepted,
        ),
        provider_call=_ProviderSpy(),
    )
    controller.open_field_profile_dialog()

    assert panel.turn_pipeline_checkbox.isChecked() is False
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

    assert "battle_state_context" not in off_payload
    assert "field_profiles" not in off_payload
    assert '"field_profiles"' not in off_prompt
    assert "If battle_state_context is present" not in off_prompt

    assert "field_profiles" not in on_payload
    battle_state_context = on_payload["battle_state_context"]
    assert battle_state_context["field"]["weather"] == {"known": True, "source": "user_confirmed", "value": "rain"}
    assert battle_state_context["field"]["terrain"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "electric_terrain",
    }
    assert battle_state_context["field"]["room"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "trick_room",
    }
    assert battle_state_context["field"]["screens"] == {
        "known": True,
        "source": "user_confirmed",
        "value": {"self": ["reflect"], "opponent": ["light_screen"]},
    }
    assert battle_state_context["field"]["hazards"] == {
        "known": True,
        "source": "user_confirmed",
        "value": {"self": [], "opponent": ["stealth_rock"]},
    }


def test_field_profile_button_contract_keeps_checkbox_default_and_battle_state_guard_wording() -> None:
    app = QApplication.instance() or QApplication([])
    assert app is not None
    panel = LLMAdvicePanel()
    payload = deepcopy(_opponent_move_ui_advice_flow_payload())
    payload["field_profiles"] = _field_profiles_fixture()

    prompt = advisor_client._build_ui_selected_prompt(
        payload,
        enable_turn_pipeline=True,
        enable_turn_order_context=True,
        enable_opponent_move_context=True,
        enable_battle_state_context=True,
    )

    expected_guard = (
        "If battle_state_context is present, treat it only as a visible or "
        "explicit battle-state snapshot, not a resolved turn simulation. "
        "Unknown battle state fields must remain unknown. Do not infer hidden "
        "items. Do not infer EVs, IVs, or nature. Do not infer boosts, status, "
        "weather, terrain, hazards, screens, or room unless explicitly "
        "provided. Do not reverse-engineer hidden state from damage estimates "
        "or KO context. Do not claim post-turn HP, item consumption, RNG "
        "result, speed tie result, Quick Claw activation, or full turn outcome "
        "from battle_state_context. Treat unsupported entries as boundaries, "
        "not facts to fill in. "
    )

    assert panel.turn_pipeline_checkbox.isChecked() is False
    assert expected_guard in prompt

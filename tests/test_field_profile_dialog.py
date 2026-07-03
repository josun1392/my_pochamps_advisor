from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.widgets.field_profile_dialog import (
    FieldProfileDialog,
    default_field_profiles,
    unknown_field_profile,
    user_confirmed_field_profile,
)


def test_field_profile_dialog_defaults_to_unknown() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog()
    dialog._save_and_accept()

    profiles = dialog.field_profiles
    assert profiles == default_field_profiles()
    dialog.close()


def test_field_profile_dialog_returns_single_value_profiles() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog()
    _set_combo(dialog.weather_combo, "rain")
    _set_combo(dialog.terrain_combo, "electric_terrain")
    _set_combo(dialog.room_combo, "trick_room")
    dialog._save_and_accept()

    profiles = dialog.field_profiles
    assert profiles is not None
    assert profiles["weather"] == {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "rain",
    }
    assert profiles["terrain"] == {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "electric_terrain",
    }
    assert profiles["room"] == {
        "status": "user_confirmed",
        "source": "user_input",
        "value": "trick_room",
    }
    assert profiles["screens"] == unknown_field_profile()
    assert profiles["hazards"] == unknown_field_profile()
    _assert_no_resolution_fields(profiles)


def test_field_profile_dialog_preserves_none_as_known_absence() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog()
    _set_combo(dialog.weather_combo, "none")
    _set_combo(dialog.terrain_combo, "none")
    _set_combo(dialog.room_combo, "none")
    _set_combo(dialog._side_modes["screens"], "none")
    _set_combo(dialog._side_modes["hazards"], "none")
    dialog._save_and_accept()

    profiles = dialog.field_profiles
    assert profiles is not None
    assert profiles["weather"] == user_confirmed_field_profile("none")
    assert profiles["terrain"] == user_confirmed_field_profile("none")
    assert profiles["room"] == user_confirmed_field_profile("none")
    assert profiles["screens"] == user_confirmed_field_profile({"self": [], "opponent": []})
    assert profiles["hazards"] == user_confirmed_field_profile({"self": [], "opponent": []})
    _assert_no_resolution_fields(profiles)


def test_field_profile_dialog_returns_side_specific_screens_and_hazards() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog()
    dialog._screen_checks["self"]["reflect"].setChecked(True)
    dialog._screen_checks["opponent"]["light_screen"].setChecked(True)
    dialog._hazard_checks["opponent"]["stealth_rock"].setChecked(True)
    dialog._save_and_accept()

    profiles = dialog.field_profiles
    assert profiles is not None
    assert profiles["screens"] == {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {
            "self": ["reflect"],
            "opponent": ["light_screen"],
        },
    }
    assert profiles["hazards"] == {
        "status": "user_confirmed",
        "source": "user_input",
        "value": {
            "self": [],
            "opponent": ["stealth_rock"],
        },
    }
    _assert_no_resolution_fields(profiles)


def test_field_profile_dialog_reset_unknown_clears_values_without_accepting() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog()
    _set_combo(dialog.weather_combo, "rain")
    _set_combo(dialog.terrain_combo, "electric_terrain")
    _set_combo(dialog.room_combo, "trick_room")
    dialog._screen_checks["self"]["reflect"].setChecked(True)
    dialog._hazard_checks["opponent"]["stealth_rock"].setChecked(True)

    dialog._reset_unknown()

    assert dialog.field_profiles is None
    dialog._save_and_accept()
    assert dialog.field_profiles == default_field_profiles()


def test_field_profile_dialog_cancel_does_not_accept_changed_profiles() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog()
    _set_combo(dialog.weather_combo, "rain")
    dialog.reject()

    assert dialog.field_profiles is None


def test_field_profile_dialog_loads_initial_field_profiles() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = FieldProfileDialog(
        current_profiles={
            "weather": user_confirmed_field_profile("rain"),
            "terrain": user_confirmed_field_profile("electric_terrain"),
            "room": user_confirmed_field_profile("trick_room"),
            "screens": user_confirmed_field_profile(
                {
                    "self": ["reflect"],
                    "opponent": ["light_screen"],
                }
            ),
            "hazards": user_confirmed_field_profile(
                {
                    "self": [],
                    "opponent": ["stealth_rock"],
                }
            ),
        }
    )

    assert dialog.weather_combo.currentData() == "rain"
    assert dialog.terrain_combo.currentData() == "electric_terrain"
    assert dialog.room_combo.currentData() == "trick_room"
    assert dialog._side_modes["screens"].currentData() == "selected"
    assert dialog._screen_checks["self"]["reflect"].isChecked()
    assert dialog._screen_checks["opponent"]["light_screen"].isChecked()
    assert dialog._side_modes["hazards"].currentData() == "selected"
    assert dialog._hazard_checks["opponent"]["stealth_rock"].isChecked()
    dialog._save_and_accept()
    assert dialog.field_profiles is not None
    assert dialog.field_profiles["weather"] == user_confirmed_field_profile("rain")


def _set_combo(combo, value: str) -> None:
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def _assert_no_resolution_fields(value: object) -> None:
    forbidden = {
        "duration",
        "duration_turns",
        "expires_after_turn",
        "expiration",
        "post_turn_expiration",
        "post_turn_hp",
        "damage_precision",
        "resolved_outcome",
        "full_turn_result",
    }
    if isinstance(value, dict):
        for key, child_value in value.items():
            assert key not in forbidden
            _assert_no_resolution_fields(child_value)
    elif isinstance(value, list):
        for child_value in value:
            _assert_no_resolution_fields(child_value)

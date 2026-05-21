from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.widgets.item_profile_dialog import (
    default_item_profile_for_role,
    item_button_text,
    item_profile_from_option,
    ItemProfileDialog,
    SUPPORTED_ITEM_OPTIONS,
)
from ui.widgets.pokemon_panel import PokemonPanel


def test_item_profile_dialog_exposes_v018_options() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp")

    options = [dialog.item_combo.itemData(index) for index in range(dialog.item_combo.count())]
    assert options == list(SUPPORTED_ITEM_OPTIONS)
    assert "unknown" in options
    assert "none" in options
    assert "choice-band" in options
    assert "choice-specs" in options
    assert "life-orb" in options
    assert "muscle-band" in options
    assert "wise-glasses" in options
    dialog.close()


def test_item_profile_dialog_saves_unknown_and_none() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Corviknight", role_key="opponent_active")
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("unknown"))
    dialog._save_and_accept()
    assert dialog.item_profile is not None
    assert dialog.item_profile["status"] == "unknown"

    dialog = ItemProfileDialog(pokemon_name="Garchomp")
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("none"))
    dialog._save_and_accept()
    assert dialog.item_profile is not None
    assert dialog.item_profile["status"] == "none"
    assert dialog.item_profile["item_id"] is None


def test_item_profile_dialog_saves_supported_damage_item() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp")
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("life-orb"))
    dialog._save_and_accept()

    profile = dialog.item_profile
    assert profile is not None
    assert profile["status"] == "user_confirmed"
    assert profile["source"] == "user_input"
    assert profile["item_id"] == "life-orb"
    assert profile["damage_modifier_status"] == "applied"
    assert "Life Orb recoil is not connected." in profile["notes"]


def test_item_profile_defaults_and_button_text() -> None:
    assert default_item_profile_for_role("my_active")["status"] == "system_default_none"
    assert default_item_profile_for_role("opponent_active")["status"] == "unknown"
    assert item_profile_from_option("choice-band")["item_id"] == "choice-band"
    assert item_button_text(item_profile_from_option("choice-specs")) == "Choice S"
    assert item_button_text(None, role_key="opponent_active") == "Item?"


def test_pokemon_panel_resets_item_profile_on_pokemon_change_and_clear() -> None:
    app = QApplication.instance() or QApplication([])
    del app
    panel = PokemonPanel(1)
    panel.set_item_profile(item_profile_from_option("life-orb"), "Life Orb")
    assert panel.item_profile is not None

    panel.set_pokemon(_pokemon_view())
    assert panel.item_profile is None
    assert panel.item_button.text() == "Item"

    panel.set_item_profile(item_profile_from_option("choice-band"), "Choice B")
    panel.clear_pokemon()
    assert panel.item_profile is None
    assert panel.item_button.text() == "Item"


def _pokemon_view():
    class View:
        en = "garchomp"
        ko = "Garchomp"
        types_ko = ["Dragon", "Ground"]
        base_stats = {
            "hp": 108,
            "attack": 130,
            "defense": 95,
            "special-attack": 80,
            "special-defense": 85,
            "speed": 102,
        }

    return View()

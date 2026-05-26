from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel

from core.champions_item_repository import ChampionsItemRepository
from ui.widgets.item_profile_dialog import (
    default_item_profile_for_role,
    item_button_text,
    item_profile_from_option,
    ItemProfileDialog,
    legal_item_options_from_repository,
    normalized_item_search_text,
)
from ui.widgets.pokemon_panel import PokemonPanel


def _legal_options() -> list[dict]:
    return legal_item_options_from_repository(ChampionsItemRepository())


def test_item_profile_dialog_accepts_repository_backed_legal_options() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    options = [dialog.item_combo.itemData(index) for index in range(dialog.item_combo.count())]
    assert "unknown" in options
    assert "none" in options
    assert "choice-scarf" in options
    assert "focus-sash" in options
    assert "leftovers" in options
    assert "sitrus-berry" in options
    assert "choice-band" not in options
    assert "choice-specs" not in options
    assert "life-orb" not in options
    dialog.close()


def test_item_profile_dialog_orders_options_by_category() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    options = _combo_options(dialog)
    assert options[:2] == ["unknown", "none"]
    assert options.index("focus-sash") < options.index("fairy-feather")
    assert options.index("fairy-feather") < options.index("sitrus-berry")
    assert options.index("sitrus-berry") < options.index("abomasite")
    assert options.index("leftovers") < options.index("audinite")
    dialog.close()


def test_item_profile_dialog_displays_korean_and_english_item_names() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    assert "기합의띠 (Focus Sash)" in _option_label(dialog, "focus-sash")
    assert "먹다남은음식 (Leftovers)" in _option_label(dialog, "leftovers")
    assert "구애스카프 (Choice Scarf)" in _option_label(dialog, "choice-scarf")
    assert "[효과 미계산]" in _option_label(dialog, "focus-sash")
    dialog.close()


def test_item_profile_dialog_falls_back_to_english_when_korean_name_is_missing() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    label = _option_label(dialog, "abomasite")
    assert "Abomasite" in label
    assert " (" not in label
    dialog.close()


def test_item_profile_dialog_uses_short_modeled_status_labels() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    label = _option_label(dialog, "focus-sash")
    assert "legal, effect not modeled" not in label
    assert "effect not modeled" not in label
    dialog.close()


def test_item_profile_dialog_has_search_input() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    assert dialog.search_input.placeholderText() == "아이템 검색..."
    dialog.close()


def test_item_profile_dialog_filters_items_by_search_text() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    for query in ("focus", "focus sash", "focus-sash", "FOCUS"):
        dialog.search_input.setText(query)
        options = _combo_options(dialog)
        assert "focus-sash" in options
        assert "unknown" in options
        assert "none" in options

    dialog.search_input.setText("left")
    assert "leftovers" in _combo_options(dialog)

    dialog.search_input.setText("sitrus")
    assert "sitrus-berry" in _combo_options(dialog)

    dialog.close()


def test_item_profile_dialog_filters_items_by_korean_search_text() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    dialog.search_input.setText("기합")
    assert "focus-sash" in _combo_options(dialog)
    assert "unknown" in _combo_options(dialog)
    assert "none" in _combo_options(dialog)

    dialog.search_input.setText("먹다")
    assert "leftovers" in _combo_options(dialog)

    dialog.search_input.setText("구애")
    assert "choice-scarf" in _combo_options(dialog)

    dialog.close()


def test_item_profile_dialog_search_keeps_non_legal_damage_items_hidden() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    for query in ("choice", "choice band", "life", "life-orb"):
        dialog.search_input.setText(query)
        options = _combo_options(dialog)
        assert "choice-band" not in options
        assert "choice-specs" not in options
        assert "life-orb" not in options
        assert "unknown" in options
        assert "none" in options

    dialog.close()


def test_item_profile_dialog_saves_filtered_item_selection() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    dialog.search_input.setText("focus sash")
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("focus-sash"))
    dialog._save_and_accept()

    assert dialog.item_profile is not None
    assert dialog.item_profile["item_id"] == "focus-sash"
    assert dialog.item_profile["status"] == "user_confirmed"
    assert dialog.item_profile["effect_support_status"] == "legal_but_not_modeled"


def test_item_search_normalization_treats_spaces_and_hyphens_alike() -> None:
    assert normalized_item_search_text("Focus Sash") == "focus-sash"
    assert normalized_item_search_text("focus_sash") == "focus-sash"


def test_item_profile_dialog_saves_unknown_and_none() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    options = _legal_options()
    dialog = ItemProfileDialog(
        pokemon_name="Corviknight",
        role_key="opponent_active",
        item_options=options,
    )
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("unknown"))
    dialog._save_and_accept()
    assert dialog.item_profile is not None
    assert dialog.item_profile["status"] == "unknown"

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=options)
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("none"))
    dialog._save_and_accept()
    assert dialog.item_profile is not None
    assert dialog.item_profile["status"] == "none"
    assert dialog.item_profile["source"] == "user_input"
    assert dialog.item_profile["item_id"] is None


def test_item_profile_dialog_saves_legal_but_not_modeled_item() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    options = _legal_options()
    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=options)
    dialog.item_combo.setCurrentIndex(dialog.item_combo.findData("choice-scarf"))
    dialog._save_and_accept()

    profile = dialog.item_profile
    assert profile is not None
    assert profile["status"] == "user_confirmed"
    assert profile["source"] == "user_input"
    assert profile["item_id"] == "choice-scarf"
    assert profile["legality_status"] == "legal"
    assert profile["effect_support_status"] == "legal_but_not_modeled"
    assert profile["damage_modifier_status"] == "not_applied"
    assert profile["ui_status"] == "recognized_not_modeled"


def test_legacy_damage_test_helper_still_builds_supported_item_profile() -> None:
    profile = item_profile_from_option("choice-band")

    assert profile["item_id"] == "choice-band"
    assert profile["status"] == "user_confirmed"
    assert profile["effect_support_status"] == "damage_supported_but_not_champions_legal"
    assert profile["ui_status"] == "damage_test_only"
    assert profile["damage_modifier_status"] == "applied"


def test_item_profile_defaults_and_button_text() -> None:
    assert default_item_profile_for_role("my_active")["status"] == "system_default_none"
    assert default_item_profile_for_role("opponent_active")["status"] == "unknown"
    assert item_profile_from_option("choice-band")["item_id"] == "choice-band"
    assert item_button_text(item_profile_from_option("choice-scarf", item_options=_legal_options())).startswith(
        "구애스카프"
    )
    assert item_button_text(None, role_key="opponent_active") == "Item?"


def test_pokemon_panel_resets_item_profile_on_pokemon_change_and_clear() -> None:
    app = QApplication.instance() or QApplication([])
    del app
    panel = PokemonPanel(1)
    panel.set_item_profile(item_profile_from_option("choice-scarf", item_options=_legal_options()), "Choice S")
    assert panel.item_profile is not None

    panel.set_pokemon(_pokemon_view())
    assert panel.item_profile is None
    assert panel.item_button.text() == "Item"

    panel.set_item_profile(item_profile_from_option("choice-scarf", item_options=_legal_options()), "Choice S")
    panel.clear_pokemon()
    assert panel.item_profile is None
    assert panel.item_button.text() == "Item"


def test_item_profile_dialog_guidance_explains_legal_but_not_modeled_boundary() -> None:
    app = QApplication.instance() or QApplication([])
    del app

    dialog = ItemProfileDialog(pokemon_name="Garchomp", item_options=_legal_options())

    label_texts = [label.text() for label in dialog.findChildren(QLabel)]
    guidance = "\n".join(label_texts)
    assert "Regulation M-A legal item fixture" in guidance
    assert "item_effects" in guidance
    assert "KO" in guidance
    dialog.close()


def _combo_options(dialog: ItemProfileDialog) -> list[str]:
    return [str(dialog.item_combo.itemData(index)) for index in range(dialog.item_combo.count())]


def _option_label(dialog: ItemProfileDialog, option_id: str) -> str:
    index = dialog.item_combo.findData(option_id)
    assert index >= 0
    return dialog.item_combo.itemText(index)


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

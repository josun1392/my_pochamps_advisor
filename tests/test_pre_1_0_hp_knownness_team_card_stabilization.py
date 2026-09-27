"""Exact runtime HP, local percentage, and card geometry remain separate."""

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.widgets.pokemon_panel import PokemonPanel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _view(name: str = "pikachu") -> SimpleNamespace:
    return SimpleNamespace(ko=name, en=name, types_ko=["전기", "강철"])


def test_new_and_loaded_cards_show_unknown_until_local_percentage_is_entered() -> None:
    _app()
    panel = PokemonPanel(1)
    for loaded in (False, True):
        if loaded:
            panel.set_pokemon(_view())
        assert panel.current_hp_percent is None
        assert panel.hp_bar.format() == "미확인"
        assert panel.hp_spinbox.text() == "미입력"
        assert panel.hp_bar.value() == 0
    panel.set_hp(100)
    assert panel.current_hp_percent == 100
    assert panel.hp_bar.format() == "100% 입력"
    assert panel.hp_spinbox.text() == "100 %"
    panel.close()


def test_exact_projection_overrides_card_display_without_changing_local_input() -> None:
    _app()
    panel = PokemonPanel(1)
    panel.set_pokemon(_view())
    panel.set_hp(75)
    panel.set_runtime_exact_hp(0, 1)
    assert panel.hp_bar.value() == 0
    assert panel.hp_bar.format() == "0/1 확정"
    assert panel.current_hp_percent == 75
    panel.set_runtime_exact_hp(None)
    assert panel.hp_bar.format() == "75% 입력"
    panel.close()


def test_runtime_exact_hp_is_projected_only_to_matching_active_owner_on_both_sides() -> None:
    _app()
    window = MainWindow()
    for column_name in ("team_my", "team_enemy"):
        column = window.my_team_column if column_name == "team_my" else window.opponent_team_column
        column.panels[0].set_pokemon(_view("pikachu"))
        column.panels[1].set_pokemon(_view("eevee"))
        column.panels[1].set_hp(50)
        window._sync_active_card_exact_hp(column_name, 0, {"pokemon_id": "pikachu", "current_hp": 0, "max_hp": 1})
        assert column.panels[0].hp_bar.format() == "0/1 확정"
        assert column.panels[1].hp_bar.format() == "50% 입력"
        window._sync_active_card_exact_hp(column_name, 1, {"pokemon_id": "eevee", "current_hp": 20, "max_hp": 40})
        assert column.panels[0].hp_bar.format() == "미확인"
        assert column.panels[1].hp_bar.format() == "20/40 확정"
        window._sync_active_card_exact_hp(column_name, 1, {"pokemon_id": "pikachu", "current_hp": 1, "max_hp": 1})
        assert column.panels[1].hp_bar.format() == "50% 입력"
    window.close()


def test_local_percentage_and_runtime_projection_create_no_observation() -> None:
    _app()
    window = MainWindow()
    window.my_team_column.panels[0].set_pokemon(window.repo.get("pikachu"))
    window.opponent_team_column.panels[0].set_pokemon(window.repo.get("pikachu"))
    window.center_column.start_battle_button.click()
    manager = window._observation_runtime_session_manager
    before = manager.read_collection_snapshot()["ordered_observations"]
    window.my_team_column.panels[0].hp_spinbox.setValue(60)
    window._refresh_guided_turn_workspace()
    assert window.my_team_column.panels[0].hp_bar.format() == "60% 입력"
    state = manager.read_state()["state"]
    assert not isinstance(state["self_side"]["pokemon"][0]["current_hp"], int)
    assert manager.read_collection_snapshot()["ordered_observations"] == before
    assert window._admit_current_state_fact("current_hp_observed", {"current_hp": 40, "maximum_hp": 100}, "self")
    window._refresh_guided_turn_workspace()
    assert window.my_team_column.panels[0].hp_bar.format() == "40/100 확정"
    assert window.my_team_column.panels[0].current_hp_percent == 60
    assert window.opponent_team_column.panels[0].hp_bar.format() == "미확인"
    assert "HP 40/100" in window.center_column.guided_turn_workspace.situation_label.text()
    window.close()


def test_loaded_card_bottom_move_row_and_selected_border_fit_at_narrow_width() -> None:
    app = _app()
    panel = PokemonPanel(1, is_active=True)
    panel.set_pokemon(_view())
    panel.set_selected(True)
    panel.resize(260, panel.height())
    panel.show()
    panel.layout().activate()
    app.processEvents()
    assert panel.height() <= 150
    assert max(button.mapTo(panel, button.rect().bottomRight()).y() for button in panel.move_buttons) <= panel.contentsRect().bottom() - 4
    for widget in (panel.item_button, panel.stats_button, panel.active_indicator):
        assert widget.mapTo(panel, widget.rect().bottomRight()).x() < panel.width()
    panel.close()

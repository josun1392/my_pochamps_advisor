from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtWidgets import QApplication

from ui.widgets.pokemon_panel import PokemonPanel


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dual_type_view():
    return SimpleNamespace(
        ko="누리레느",
        en="primarina",
        base_stats={
            "hp": 80,
            "attack": 74,
            "defense": 74,
            "special-attack": 126,
            "special-defense": 116,
            "speed": 60,
        },
        types_ko=["물", "페어리"],
    )


def _show_at_team_width(panel: PokemonPanel, width: int = 280) -> None:
    app = _app()
    panel.resize(width, panel.height())
    panel.show()
    panel.layout().activate()
    app.processEvents()


def _assert_control_inside_panel(panel: PokemonPanel, widget) -> None:
    top_left = widget.mapTo(panel, widget.rect().topLeft())
    bottom_right = widget.mapTo(panel, widget.rect().bottomRight())
    assert top_left.x() >= 0
    assert bottom_right.x() < panel.width()


def test_unloaded_card_keeps_item_stats_and_active_indicator_reachable() -> None:
    _app()
    panel = PokemonPanel(1, is_active=True)
    _show_at_team_width(panel)

    assert panel.item_button.isVisible()
    assert panel.stats_button.isVisible()
    assert panel.active_indicator.isVisible()
    _assert_control_inside_panel(panel, panel.item_button)
    _assert_control_inside_panel(panel, panel.stats_button)
    _assert_control_inside_panel(panel, panel.active_indicator)

    panel.close()


def test_loaded_dual_type_card_prioritizes_controls_and_removes_inline_base_stats() -> None:
    _app()
    panel = PokemonPanel(1, is_active=True)
    view = _dual_type_view()
    panel.set_pokemon(view)
    _show_at_team_width(panel)

    assert panel.name_label.text() == view.ko
    assert panel.detail_label.text() == view.en
    assert "HP80" not in panel.detail_label.text()
    assert "A74" not in panel.detail_label.text()
    assert "C126" not in panel.detail_label.text()
    assert [badge.text() for badge in panel.type_badges] == ["물", "페어리"]
    assert all(badge.isVisible() for badge in panel.type_badges)

    for widget in (panel.item_button, panel.stats_button, panel.active_indicator):
        assert widget.isVisible()
        _assert_control_inside_panel(panel, widget)

    panel.close()


def test_metadata_loading_at_narrow_team_width_has_no_signal_side_effect() -> None:
    _app()
    panel = PokemonPanel(2, is_active=False)
    emitted: list[tuple[str, int]] = []
    panel.slot_clicked.connect(lambda slot: emitted.append(("slot", slot)))
    panel.move_slot_selected.connect(lambda slot: emitted.append(("move", slot)))
    panel.stat_profile_requested.connect(lambda slot: emitted.append(("stats", slot)))
    panel.item_profile_requested.connect(lambda slot: emitted.append(("item", slot)))

    panel.set_pokemon(_dual_type_view())
    _show_at_team_width(panel, width=250)

    assert emitted == []
    assert panel.pokemon_view is not None
    assert panel.selected_move_index is None
    for widget in (panel.item_button, panel.stats_button, panel.active_indicator):
        assert widget.isVisible()
        _assert_control_inside_panel(panel, widget)

    panel.close()


def test_own_and_opponent_cards_share_the_same_responsive_pokemon_panel_contract() -> None:
    _app()
    own = PokemonPanel(1, is_active=True)
    opponent = PokemonPanel(1, is_active=True)

    for panel in (own, opponent):
        panel.set_pokemon(_dual_type_view())
        _show_at_team_width(panel, width=260)
        assert panel.detail_label.text() == "primarina"
        assert [badge.text() for badge in panel.type_badges if badge.isVisible()] == ["물", "페어리"]
        for widget in (panel.item_button, panel.stats_button, panel.active_indicator):
            _assert_control_inside_panel(panel, widget)
        panel.close()

from __future__ import annotations

from ui.widgets.stat_profile_dialog import (
    champions_final_stat_limits,
    validate_final_stats,
    StatProfileDialog,
)
from PySide6.QtWidgets import QApplication


def test_validate_final_stats_accepts_complete_positive_integers() -> None:
    assert validate_final_stats(
        {
            "hp": 153,
            "atk": 104,
            "def": 98,
            "spa": 161,
            "spd": 105,
            "spe": 167,
        }
    ) == {
        "hp": 153,
        "atk": 104,
        "def": 98,
        "spa": 161,
        "spd": 105,
        "spe": 167,
    }


def test_validate_final_stats_rejects_partial_or_invalid_stats() -> None:
    assert validate_final_stats({"hp": 153, "atk": 104}) is None
    assert validate_final_stats(
        {
            "hp": 153,
            "atk": 104,
            "def": 98,
            "spa": 161,
            "spd": 105,
            "spe": 0,
        }
    ) is None
    assert validate_final_stats(
        {
            "hp": 153,
            "atk": 104,
            "def": 98,
            "spa": 161,
            "spd": 105,
            "spe": "167",
        }
    ) is None


def test_champions_final_stat_limits_use_stat_point_caps() -> None:
    limits = champions_final_stat_limits(
        {
            "hp": 108,
            "attack": 130,
            "defense": 95,
            "special-attack": 80,
            "special-defense": 85,
            "speed": 102,
        }
    )

    assert limits is not None
    assert limits["hp"] == 215
    assert limits["atk"] == 200
    assert limits["def"] == 161
    assert limits["spa"] == 145
    assert limits["spd"] == 150
    assert limits["spe"] == 169


def test_validate_final_stats_rejects_values_above_champions_limits() -> None:
    limits = {
        "hp": 215,
        "atk": 200,
        "def": 161,
        "spa": 144,
        "spd": 150,
        "spe": 169,
    }

    assert (
        validate_final_stats(
            {
                "hp": 216,
                "atk": 200,
                "def": 161,
                "spa": 144,
                "spd": 150,
                "spe": 169,
            },
            limits,
        )
        is None
    )


def test_stat_profile_dialog_shows_and_enforces_champions_limits() -> None:
    app = QApplication.instance() or QApplication([])
    del app
    base_stats = {
        "hp": 108,
        "attack": 130,
        "defense": 95,
        "special-attack": 80,
        "special-defense": 85,
        "speed": 102,
    }
    dialog = StatProfileDialog(
        pokemon_name="Garchomp",
        current_stats=None,
        base_stats=base_stats,
        stat_limits=champions_final_stat_limits(base_stats),
    )

    assert dialog._spinboxes["hp"].maximum() == 32
    assert dialog._spinboxes["atk"].maximum() == 32
    dialog._spinboxes["hp"].setValue(999)
    assert dialog._spinboxes["hp"].value() == 32
    dialog._save_and_accept()
    assert dialog.final_stats is not None
    assert dialog.final_stats["hp"] == 215
    dialog.close()


def test_stat_profile_dialog_enforces_total_stat_point_cap() -> None:
    app = QApplication.instance() or QApplication([])
    del app
    base_stats = {
        "hp": 108,
        "attack": 130,
        "defense": 95,
        "special-attack": 80,
        "special-defense": 85,
        "speed": 102,
    }
    dialog = StatProfileDialog(
        pokemon_name="Garchomp",
        current_stats=None,
        base_stats=base_stats,
        stat_limits=champions_final_stat_limits(base_stats),
    )

    dialog._spinboxes["hp"].setValue(32)
    dialog._spinboxes["atk"].setValue(32)
    dialog._spinboxes["def"].setValue(32)

    total = sum(spinbox.value() for spinbox in dialog._spinboxes.values())
    assert total == 66
    assert dialog._spinboxes["def"].value() == 2
    dialog.close()

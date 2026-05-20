from __future__ import annotations

from ui.widgets.stat_profile_dialog import validate_final_stats


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

from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import build_current_hp_context_from_confirmations, normalize_user_confirmed_current_hp


def _entry(**updates: object) -> dict[str, object]:
    value = {"side": "opponent", "current_hp": 240, "maximum_hp": 300, "status": "user_confirmed", "source": "user_confirmed_current_hp"}; value.update(updates); return value


def test_current_hp_is_exact_and_keeps_current_and_maximum_distinct() -> None:
    assert normalize_user_confirmed_current_hp(_entry()) == {**_entry(), "confidence": "known"}
    assert build_current_hp_context_from_confirmations([_entry(), _entry(current_hp=200)]) == {"current_hp": [{**_entry(current_hp=200), "confidence": "known"}]}


@pytest.mark.parametrize("updates", [{"current_hp": -1}, {"current_hp": 301}, {"maximum_hp": 0}, {"current_hp": 1.5}, {"current_hp_percent": 80}, {"post_turn_hp": 20}, {"source": "estimated_current_hp"}])
def test_current_hp_rejects_percent_estimates_post_turn_and_invalid_ranges(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError): normalize_user_confirmed_current_hp(_entry(**updates))

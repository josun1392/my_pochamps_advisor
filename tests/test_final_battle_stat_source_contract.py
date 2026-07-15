from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import normalize_user_confirmed_final_battle_stat


def _entry(**updates: object) -> dict[str, object]:
    value = {"side": "self", "stat": "attack", "value": 205, "status": "user_confirmed", "source": "user_confirmed_final_battle_stat"}
    value.update(updates)
    return value


def test_final_stat_normalizes_supported_stage_unmodified_values() -> None:
    assert normalize_user_confirmed_final_battle_stat(_entry(stat="SpA", value=222)) == {**_entry(stat="special-attack", value=222), "confidence": "known"}


@pytest.mark.parametrize("updates", [{"value": 0}, {"value": -1}, {"value": 1.5}, {"value": "205"}, {"value": 10000}, {"stat": "accuracy"}, {"source": "species_base_stat"}, {"effective_stat": 100}, {"current_hp": 100}])
def test_final_stat_rejects_invalid_inferred_or_resolved_values(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_final_battle_stat(_entry(**updates))

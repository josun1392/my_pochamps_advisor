from __future__ import annotations

import pytest

from llm.advisor_battle_state_context import normalize_user_confirmed_current_field_state


def _field(**updates: object) -> dict[str, object]:
    field: dict[str, object] = {
        "weather": "rain",
        "terrain": "none",
        "global_effects": ["trick-room"],
        "side_effects": [{"side": "self", "effect": "reflect"}],
        "status": "user_confirmed",
        "source": "user_confirmed_current_field_state",
    }
    field.update(updates)
    return field


def test_current_field_snapshot_normalizes_and_preserves_explicit_none() -> None:
    normalized = normalize_user_confirmed_current_field_state(
        _field(global_effects=["gravity", "trick-room"], side_effects=[{"side": "opponent", "effect": "tailwind"}, {"side": "self", "effect": "reflect"}])
    )
    assert normalized == {
        "weather": "rain", "terrain": "none", "global_effects": ["gravity", "trick-room"],
        "side_effects": [{"side": "self", "effect": "reflect"}, {"side": "opponent", "effect": "tailwind"}],
        "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known",
    }


@pytest.mark.parametrize(
    "updates",
    [
        {"weather": "rain/sun"}, {"terrain": "unknown"}, {"global_effects": ["trick-room", "trick-room"]},
        {"side_effects": [{"side": "self", "effect": "reflect"}, {"side": "self", "effect": "reflect"}]},
        {"status": "observed"}, {"source": "battle_log"}, {"turns_remaining": 3},
        {"side_effects": [{"side": "ally", "effect": "reflect"}]},
    ],
)
def test_current_field_snapshot_rejects_invalid_and_forbidden_inputs(updates: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_field_state(_field(**updates))

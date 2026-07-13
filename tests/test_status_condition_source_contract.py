from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from llm.advisor_battle_state_context import (
    USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_TYPES,
    USER_CONFIRMED_CURRENT_CONDITION_FORBIDDEN_FIELDS,
    USER_CONFIRMED_CURRENT_CONDITION_FUTURE_UNSUPPORTED_SOURCES,
    build_battle_state_context_from_ui_selected_state,
    normalize_user_confirmed_current_condition,
)


def _condition(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "side": "self",
        "condition_type": "burn",
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
    }
    candidate.update(overrides)
    return candidate


@pytest.mark.parametrize("condition_type", sorted(USER_CONFIRMED_CURRENT_CONDITION_ALLOWED_TYPES))
def test_user_confirmed_current_condition_normalizes_only_known_current_meaning(condition_type: str) -> None:
    assert normalize_user_confirmed_current_condition(_condition(condition_type=condition_type)) == {
        "side": "self",
        "condition_type": condition_type,
        "status": "user_confirmed",
        "source": "user_confirmed_current_condition",
        "confidence": "known",
    }


@pytest.mark.parametrize(
    "candidate",
    [
        _condition(side=None),
        _condition(side="ally"),
        _condition(condition_type=None),
        _condition(condition_type="confusion"),
        _condition(status=None),
        _condition(status="observed"),
        _condition(source=None),
        _condition(source="battle_log"),
        _condition(confidence="observed"),
        {key: value for key, value in _condition().items() if key != "side"},
        {key: value for key, value in _condition().items() if key != "condition_type"},
        {key: value for key, value in _condition().items() if key != "status"},
        {key: value for key, value in _condition().items() if key != "source"},
    ],
)
def test_invalid_current_condition_source_status_or_type_is_rejected(candidate: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        normalize_user_confirmed_current_condition(candidate)


@pytest.mark.parametrize("source", sorted(USER_CONFIRMED_CURRENT_CONDITION_FUTURE_UNSUPPORTED_SOURCES))
def test_future_condition_source_name_is_not_trusted_until_its_own_contract_exists(source: str) -> None:
    with pytest.raises(ValueError, match="source"):
        normalize_user_confirmed_current_condition(_condition(source=source))


@pytest.mark.parametrize("field_name", sorted(USER_CONFIRMED_CURRENT_CONDITION_FORBIDDEN_FIELDS))
def test_forbidden_current_condition_fields_are_rejected_recursively(field_name: str) -> None:
    candidate = _condition()
    candidate["nested"] = {field_name: True}

    with pytest.raises(ValueError, match=field_name):
        normalize_user_confirmed_current_condition(candidate)


def test_condition_foundation_does_not_map_status_into_existing_ui_selected_payload_path() -> None:
    battle_input = {
        "pokemon": {
            "my_active": {"name_en": "Garchomp", "hp_percent": 100},
            "opponent_active": {"name_en": "Charizard", "hp_percent": 70},
        },
        "condition_confirmations": [_condition()],
    }

    context = build_battle_state_context_from_ui_selected_state(deepcopy(battle_input))

    assert context["self_active"]["status"] == {"known": False, "value": "unknown"}
    assert context["opponent_active"]["status"] == {"known": False, "value": "unknown"}
    assert "condition_confirmations" not in context

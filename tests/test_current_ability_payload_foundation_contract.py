from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

import pytest

import llm.advisor_client as advisor_client
from llm.advisor_battle_state_context import build_current_ability_context_from_confirmations
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


FORBIDDEN_ABILITY_FIELDS = frozenset(
    {
        "ability_activated_this_turn",
        "ability_triggered_this_turn",
        "ability_suppressed",
        "ability_replaced",
        "ability_copied",
        "ability_revealed_by_inference",
        "resolved_ability_effect",
        "exact_stat_change",
        "exact_damage_modifier",
        "exact_damage",
        "exact_post_turn_hp",
        "boosted_stat",
        "final_speed_order",
        "immunity_resolved",
        "prevention_resolved",
        "rng_roll",
        "post_turn_ability_state",
    }
)


def _ability(**overrides: Any) -> dict[str, Any]:
    candidate = {
        "side": "self",
        "ability": "intimidate",
        "status": "user_confirmed",
        "source": "user_confirmed_current_ability",
    }
    candidate.update(overrides)
    return candidate


def _payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _assert_no_forbidden(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in FORBIDDEN_ABILITY_FIELDS
            _assert_no_forbidden(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_forbidden(child)


def test_payload_foundation_revalidates_current_abilities_by_side() -> None:
    raw = [_ability(ability="Quark Drive"), _ability(side="opponent", ability="unknown")]
    context = build_current_ability_context_from_confirmations(raw)
    assert context is not None

    payload = advisor_client.build_ui_advice_payload(
        deepcopy(_opponent_move_ui_advice_flow_payload()),
        ability_context=context,
        enable_ability_context=True,
    )

    assert payload["ability_context"] == {
        "current_abilities": [
            {**_ability(ability="quark-drive"), "confidence": "known"},
            {**_ability(side="opponent", ability="unknown"), "confidence": "known"},
        ]
    }
    _assert_no_forbidden(payload)


def test_disabled_or_all_invalid_ability_context_is_absent() -> None:
    raw = [_ability(ability="none"), _ability(side="opponent", ability="levitate / heatproof")]
    context = build_current_ability_context_from_confirmations(raw)
    base = deepcopy(_opponent_move_ui_advice_flow_payload())

    assert context is None
    assert "ability_context" not in advisor_client.build_ui_advice_payload(
        base, ability_context={"current_abilities": [{**_ability(), "confidence": "known"}]}, enable_ability_context=False
    )
    assert "ability_context" not in advisor_client.build_ui_advice_payload(
        base, ability_context=context, enable_ability_context=True
    )


@pytest.mark.parametrize("field_name", sorted(FORBIDDEN_ABILITY_FIELDS))
def test_invalid_and_forbidden_abilities_are_omitted_from_foundation(field_name: str) -> None:
    context = build_current_ability_context_from_confirmations(
        [_ability(), _ability(side="opponent", **{field_name: True})]
    )

    assert context == {"current_abilities": [{**_ability(), "confidence": "known"}]}


def test_prompt_isolation_strips_raw_and_normalized_ability_context_without_changing_acknowledgement() -> None:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input["current_ability_confirmations"] = [_ability(), _ability(side="opponent", ability="unknown")]
    battle_input["current_condition_confirmations"] = [
        {
            "side": "self",
            "condition_type": "burn",
            "status": "user_confirmed",
            "source": "user_confirmed_current_condition",
        }
    ]
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=True)
    payload = _payload(prompt)

    assert "current_ability_confirmations" not in payload
    assert "ability_context" not in payload
    assert "ability_context" not in prompt
    assert "Current ability |" not in prompt
    assert "condition_context" in payload
    assert "- Current condition | self | burn" in prompt

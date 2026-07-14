from __future__ import annotations

import json
from copy import deepcopy

import pytest

import llm.advisor_client as advisor_client
import scripts.run_sanitized_condition_smoke as smoke_cli
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


def _fixture() -> dict:
    battle_input = deepcopy(_opponent_move_ui_advice_flow_payload())
    battle_input.update(
        {
            "current_condition_confirmations": [
                {"side": "self", "condition_type": "burn", "status": "user_confirmed", "source": "user_confirmed_current_condition"},
                {"side": "opponent", "condition_type": "unknown", "status": "user_confirmed", "source": "user_confirmed_current_condition"},
            ],
            "current_ability_confirmations": [
                {"side": "self", "ability": "intimidate", "status": "user_confirmed", "source": "user_confirmed_current_ability"},
                {"side": "opponent", "ability": "unknown", "status": "user_confirmed", "source": "user_confirmed_current_ability"},
            ],
            "current_stat_stage_confirmations": [
                {"side": "self", "stat": "attack", "stage": -1, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"},
                {"side": "self", "stat": "speed", "stage": 2, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"},
                {"side": "opponent", "stat": "defense", "stage": -1, "status": "user_confirmed", "source": "user_confirmed_current_stat_stage"},
            ],
            "current_field_state_confirmation": {
                "weather": "rain", "terrain": "none", "global_effects": ["trick-room"],
                "side_effects": [{"side": "self", "effect": "reflect"}, {"side": "opponent", "effect": "tailwind"}],
                "status": "user_confirmed", "source": "user_confirmed_current_field_state",
            },
            "item_event_confirmations": [{
                "side": "opponent", "item": "focus-sash", "event_type": "item_activation_observed",
                "status": "user_confirmed", "source": "explicit_user_event_confirmation", "turn": None, "note": None,
            }],
        }
    )
    return battle_input


def _payload_and_entries(*, enabled: bool = True) -> tuple[dict, tuple, str]:
    battle_input = _fixture()
    prompt = advisor_client._build_ui_selected_prompt(battle_input, enable_battle_state_context=enabled)
    payload = json.loads(prompt.rsplit("\n\n", 1)[1])
    return payload, advisor_client.build_trusted_context_acknowledgement_entries(payload), prompt


def _response(entries: tuple, advice: str = "Choose cautiously; the confirmed contexts do not establish timing, causes, exact damage, or final order.") -> str:
    labels = {
        "current_condition": "Current condition", "current_ability": "Current ability",
        "current_stat_stage": "Current stat stage", "current_weather": "Current weather",
        "current_terrain": "Current terrain", "current_global_field_effect": "Current global field effect",
        "current_side_field_effect": "Current side field effect", "observed_item_event": "Observed item event",
    }
    lines: list[str] = []
    for category, side, identity, detail in entries:
        label = labels[category]
        if category == "current_stat_stage":
            value = int(detail)
            lines.append(f"- {label} | {side} | {identity} | {value:+d}" if value else f"- {label} | {side} | {identity} | 0")
        elif category == "observed_item_event":
            lines.append(f"- {label} | {side} | {identity} | {detail}")
        elif side:
            lines.append(f"- {label} | {side} | {identity}")
        else:
            lines.append(f"- {label} | {identity}")
    return "[Trusted Context]\n" + "\n".join(lines) + f"\n\n[Advice]\n{advice}"


def test_integrated_fixture_uses_normalized_payload_exact_set_and_cli_evaluator() -> None:
    payload, entries, prompt = _payload_and_entries()
    assert set(payload) >= {"condition_context", "ability_context", "stat_stage_context", "field_state_context", "item_event_context"}
    assert entries == (
        ("current_condition", "self", "burn", None), ("current_condition", "opponent", "unknown", None),
        ("current_ability", "self", "intimidate", None), ("current_ability", "opponent", "unknown", None),
        ("current_stat_stage", "self", "attack", "-1"), ("current_stat_stage", "self", "speed", "2"),
        ("current_stat_stage", "opponent", "defense", "-1"), ("current_weather", "", "rain", None),
        ("current_terrain", "", "none", None), ("current_global_field_effect", "", "trick-room", None),
        ("current_side_field_effect", "self", "reflect", None), ("current_side_field_effect", "opponent", "tailwind", None),
        ("observed_item_event", "opponent", "focus-sash", "item_activation_observed"),
    )
    response = _response(entries)
    assert "[Trusted Context]" in prompt and "[Advice]" in prompt
    assert advisor_client.validate_trusted_context_acknowledgement(response, entries) is None
    assert smoke_cli.evaluate_current_condition_item_event_response(response, expected_entries=entries)[0] == "pass"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: text.replace("- Current condition | self | burn\n", ""),
        lambda text: text.replace("- Current ability | self | intimidate\n", ""),
        lambda text: text.replace("- Current stat stage | self | speed | +2\n", ""),
        lambda text: text.replace("- Current weather | rain\n", ""),
        lambda text: text.replace("- Current side field effect | opponent | tailwind\n", ""),
        lambda text: text.replace("- Observed item event | opponent | focus-sash | item_activation_observed\n", ""),
        lambda text: text.replace("opponent | unknown", "opponent | levitate", 1),
        lambda text: text.replace("self | speed | +2", "self | speed | +3"),
        lambda text: text.replace("Current global field effect | trick-room", "Current side field effect | self | trick-room"),
        lambda text: text.replace("\n\n[Advice]", "\n- Current condition | self | burn\n\n[Advice]"),
    ],
)
def test_integrated_exact_set_rejects_missing_extra_duplicate_and_mismatch(mutate) -> None:
    _, entries, _ = _payload_and_entries()
    assert advisor_client.validate_trusted_context_acknowledgement(mutate(_response(entries)), entries) is not None


@pytest.mark.parametrize(
    "claim",
    [
        "Burn was applied this turn.", "Opponent paralysis is confirmed.",
        "Intimidate activated this turn and opponent Attack was definitely lowered.",
        "Attack dropped this turn because of Intimidate.", "Focus Sash left the Pokemon at exactly 1 HP.",
        "There are turns remaining for rain.", "The final speed order is known.",
        "The exact damage is 42 and post-turn HP is 58.",
    ],
)
def test_integrated_forbidden_boundaries_fail_after_exact_acknowledgement(claim: str) -> None:
    _, entries, _ = _payload_and_entries()
    assert smoke_cli.evaluate_current_condition_item_event_response(_response(entries, claim), expected_entries=entries)[0] == "fail"


def test_integrated_gate_off_omits_all_context_but_preserves_normal_advice_path() -> None:
    payload, entries, prompt = _payload_and_entries(enabled=False)
    assert entries == ()
    assert not {"condition_context", "ability_context", "stat_stage_context", "field_state_context", "item_event_context"} & set(payload)
    assert "Start the answer with exactly this short trusted-context acknowledgement format" not in prompt


def test_mocked_normal_ui_advice_path_preserves_structured_text(monkeypatch) -> None:
    _, entries, _ = _payload_and_entries()
    response = _response(entries)
    monkeypatch.setattr(advisor_client, "call_gemini", lambda prompt, model: (response, {"input_tokens": 1, "output_tokens": 1, "cached_tokens": 0}))
    monkeypatch.setattr(advisor_client, "_log_advisor_call", lambda **kwargs: {"estimated_cost_usd": 0.0})
    advice, _, _ = advisor_client.run_ui_selected_advice(_fixture(), model="offline-test", enable_battle_state_context=True)
    assert advice == response
    assert "[Trusted Context]" in advice and "[Advice]" in advice

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from llm.advisor_client import _build_ui_selected_prompt
from tests.test_advisor_payload_contract import _opponent_move_ui_advice_flow_payload


_FORBIDDEN_FIELDS = frozenset(
    {
        "berry_recovered_exact_hp",
        "exact_damage",
        "exact_hp",
        "focus_sash_post_hit_hp_1",
        "item_damage_modifier_applied",
        "item_speed_modifier_applied",
        "post_turn_hp_from_item",
        "post_turn_item_state",
        "quick_claw_activated_by_rng",
        "resolved_effects",
        "resolved_item_effect",
        "rng_roll",
        "speed_order_override",
    }
)


def _focus_sash_event() -> dict[str, Any]:
    return {
        "side": "opponent",
        "item": "focus-sash",
        "event_type": "item_activation_observed",
        "status": "user_confirmed",
        "source": "explicit_user_event_confirmation",
        "turn": 5,
        "note": "User saw Focus Sash activation text.",
    }


def _fixture_a_battle_input() -> dict[str, Any]:
    payload = deepcopy(_opponent_move_ui_advice_flow_payload())
    payload["item_profiles"] = {
        "my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "leftovers"},
    }
    payload["item_event_confirmations"] = [_focus_sash_event()]
    payload.pop("opponent_moves", None)
    payload.pop("speed_context", None)
    payload["moves"] = {}
    return payload


def _fixture_b_battle_input() -> dict[str, Any]:
    payload = deepcopy(_opponent_move_ui_advice_flow_payload())
    payload["item_profiles"] = {
        "my_active": {"status": "user_confirmed", "source": "user_input", "item_id": "leftovers"},
        "opponent_active": {"status": "user_confirmed", "source": "user_input", "item_id": "choice-scarf"},
    }
    payload["item_event_confirmations"] = [_focus_sash_event()]
    return payload


def _prompt_payload(prompt: str) -> dict[str, Any]:
    return json.loads(prompt.rsplit("\n\n", 1)[1])


def _assert_forbidden_fields_absent(value: object) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            assert key not in _FORBIDDEN_FIELDS
            _assert_forbidden_fields_absent(child)
    elif isinstance(value, list):
        for child in value:
            _assert_forbidden_fields_absent(child)


def _evaluate_item_event_readback(response: str) -> set[str]:
    """Test-only evaluator for the v12.45 synthetic response contracts."""
    lower = response.lower()
    failures: set[str] = set()
    known_current = all(anchor in lower for anchor in ("self", "leftovers", "user-confirmed", "current"))
    observed_event = all(
        anchor in lower for anchor in ("opponent", "focus sash", "activation", "observed", "user explicitly confirmed")
    )
    if not known_current:
        failures.add("known_item_identity_missing")
    if not observed_event:
        failures.add("observed_event_omitted")
    if "both activated" in lower or "leftovers activation" in lower or "focus sash recovery" in lower:
        failures.add("identity_mixing")
    if any(
        claim in lower
        for claim in (
            "focus sash left the pokémon at exactly 1 hp",
            "focus sash left the pokemon at exactly 1 hp",
            "exact hp was restored",
            "exact damage was prevented",
            "resolved_item_effect is known",
            "post-turn hp is known",
            "quick claw rng roll is known",
            "final speed order is known",
        )
    ):
        failures.add("unsupported_resolution")
    has_damage_range = " hp" in lower and ("-" in lower or "%" in lower)
    if has_damage_range and not observed_event:
        failures.add("damage_distraction")
    return failures


def test_fixture_a_payload_separates_known_leftovers_from_observed_focus_sash() -> None:
    prompt = _build_ui_selected_prompt(_fixture_a_battle_input(), enable_battle_state_context=True)
    payload = _prompt_payload(prompt)

    assert payload["battle_state_context"]["self_active"]["item"] == {
        "known": True,
        "source": "user_confirmed",
        "value": "leftovers",
    }
    assert payload["item_event_context"]["observed_events"] == [{**_focus_sash_event(), "confidence": "observed"}]
    assert payload["battle_state_context"]["self_active"]["item"] != payload["item_event_context"]["observed_events"][0]
    _assert_forbidden_fields_absent(payload)


def test_fixture_a_prompt_keeps_observed_only_guard_and_current_known_item_structure() -> None:
    prompt = _build_ui_selected_prompt(_fixture_a_battle_input(), enable_battle_state_context=True)

    assert "If item_event_context is present" in prompt
    assert "explicitly user-confirmed observed item event" in prompt
    assert "Distinguish current known items from explicitly observed item events." in prompt
    assert "Briefly acknowledge each observed event by side, item, and event type" in prompt
    assert "user-confirmed observation only" in prompt
    assert "not a resolved mechanic result" in prompt
    assert "Do not infer exact HP, exact damage" in prompt


def test_fixture_b_full_prompt_preserves_item_event_guard_with_broad_advice_context() -> None:
    prompt = _build_ui_selected_prompt(_fixture_b_battle_input(), enable_battle_state_context=True)
    payload = _prompt_payload(prompt)

    assert "item_event_context" in payload
    assert "damage_estimate" in prompt
    assert "If item_event_context is present" in prompt
    assert "Recommend the best one-turn action" in prompt


def test_fixture_b_full_prompt_includes_contrast_readback_without_suppressing_damage_context() -> None:
    prompt = _build_ui_selected_prompt(_fixture_b_battle_input(), enable_battle_state_context=True)

    assert "Distinguish current known items from explicitly observed item events." in prompt
    assert "Briefly acknowledge each observed event by side, item, and event type" in prompt
    assert "damage_estimate" in prompt


def test_known_item_without_event_omits_contrast_readback_instruction() -> None:
    payload = _fixture_a_battle_input()
    payload.pop("item_event_confirmations")

    prompt = _build_ui_selected_prompt(payload, enable_battle_state_context=True)

    assert "item_event_context" not in _prompt_payload(prompt)
    assert "Distinguish current known items from explicitly observed item events." not in prompt
    assert "Briefly acknowledge each observed event by side, item, and event type" not in prompt


def test_synthetic_good_readback_passes_narrow_semantics_contract() -> None:
    response = (
        "Self has a user-confirmed current Leftovers item. The user explicitly confirmed an opponent "
        "Focus Sash activation event was observed. This observation does not establish the exact resolved "
        "effect or resulting HP."
    )

    assert _evaluate_item_event_readback(response) == set()


def test_synthetic_identity_mixing_fails_contract() -> None:
    response = "Self has a user-confirmed current Leftovers item, and Leftovers and Focus Sash are both activated."

    assert "identity_mixing" in _evaluate_item_event_readback(response)
    assert "observed_event_omitted" in _evaluate_item_event_readback(response)


def test_synthetic_event_omission_fails_contract() -> None:
    response = "Use Flamethrower for general battle advice; self has a user-confirmed current Leftovers item."

    assert "observed_event_omitted" in _evaluate_item_event_readback(response)


def test_synthetic_unsupported_resolution_fails_contract() -> None:
    response = (
        "Self has a user-confirmed current Leftovers item. The user explicitly confirmed an opponent Focus "
        "Sash activation event was observed. Focus Sash left the Pokémon at exactly 1 HP."
    )

    assert "unsupported_resolution" in _evaluate_item_event_readback(response)


def test_synthetic_exact_outcome_claim_fails_contract() -> None:
    response = (
        "Self has a user-confirmed current Leftovers item. The user explicitly confirmed an opponent Focus "
        "Sash activation event was observed. Exact damage was prevented."
    )

    assert "unsupported_resolution" in _evaluate_item_event_readback(response)


def test_synthetic_rng_and_final_order_claims_fail_contract() -> None:
    response = (
        "Self has a user-confirmed current Leftovers item. The user explicitly confirmed an opponent Focus "
        "Sash activation event was observed. Quick Claw RNG roll is known, and final speed order is known."
    )

    assert "unsupported_resolution" in _evaluate_item_event_readback(response)


def test_synthetic_damage_range_only_fails_as_event_distraction() -> None:
    response = "Self has a user-confirmed current Leftovers item. Use Flamethrower: it deals 31-37 HP (16.9-20.2%)."

    failures = _evaluate_item_event_readback(response)
    assert "observed_event_omitted" in failures
    assert "damage_distraction" in failures


def test_damage_range_with_explicit_observed_readback_is_not_itself_a_distraction() -> None:
    response = (
        "Self has a user-confirmed current Leftovers item. The user explicitly confirmed an opponent Focus "
        "Sash activation event was observed. The move has a 31-37 HP (16.9-20.2%) estimate under its existing assumptions."
    )

    assert "damage_distraction" not in _evaluate_item_event_readback(response)

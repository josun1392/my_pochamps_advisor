from __future__ import annotations

import pytest

from llm.advisor_candidate_contract import (
    _dark_type_prankster_source,
    _priority_blocking_ability_source,
    _psychic_terrain_priority_source,
)


def _type_row(side: str, *, types: list[str] | None) -> dict:
    if types is None:
        return {
            "side": side,
            "state": "unknown",
            "status": "unknown",
            "source": "unknown",
            "authority_provenance": "unknown",
            "confidence": "unknown",
        }
    return {
        "side": side,
        "state": "known",
        "types": types,
        "status": "user_confirmed",
        "source": "user_confirmed_current_type",
        "authority_provenance": "user_confirmed_current",
        "confidence": "known",
    }


def _snapshot_with_target_types(types: list[str] | None) -> dict:
    return {"current_type_context": {"current_types": [_type_row("opponent", types=types)]}}


@pytest.mark.parametrize("category", ["physical", "special"])
def test_non_status_moves_bypass_prankster_dark_before_incomplete_action_order(category: str) -> None:
    result = _dark_type_prankster_source(
        _snapshot_with_target_types(None),
        {"category": category, "target": "selected-pokemon"},
        {"status": "insufficient_context", "missing_inputs": ["opponent_action"]},
    )

    assert result == {"status": "allowed", "move_success_status": "allowed"}


def test_applicable_prankster_status_move_still_requires_application_authority() -> None:
    result = _dark_type_prankster_source(
        _snapshot_with_target_types(["dark"]),
        {"category": "status", "target": "selected-pokemon"},
        {"status": "insufficient_context", "missing_inputs": ["opponent_action"]},
    )

    assert result == {
        "status": "insufficient_context",
        "move_success_status": None,
        "missing_inputs": ["self.prankster_applied"],
    }


def test_prankster_status_move_into_dark_target_still_blocks() -> None:
    result = _dark_type_prankster_source(
        _snapshot_with_target_types(["dark", "ghost"]),
        {"category": "status", "target": "selected-pokemon"},
        {"status": "acts_first", "self_prankster_applied": True},
    )

    assert result["status"] == "blocked"
    assert result["block_reason"] == "dark_type_prankster_immunity"
    assert result["priority_block_source"] == "dark_type_prankster_immunity"
    assert result["dark_type_prankster_immunity_blocked"] is True


def test_prankster_status_move_into_non_dark_target_is_allowed() -> None:
    result = _dark_type_prankster_source(
        _snapshot_with_target_types(["water"]),
        {"category": "status", "target": "selected-pokemon"},
        {"status": "acts_first", "self_prankster_applied": True},
    )

    assert result == {"status": "allowed", "move_success_status": "allowed"}


def test_prankster_status_move_with_unknown_target_type_fails_closed() -> None:
    result = _dark_type_prankster_source(
        _snapshot_with_target_types(None),
        {"category": "status", "target": "selected-pokemon"},
        {"status": "acts_first", "self_prankster_applied": True},
    )

    assert result == {
        "status": "insufficient_context",
        "move_success_status": None,
        "missing_inputs": ["opponent.current_type"],
    }


def test_psychic_terrain_positive_priority_behavior_is_unchanged() -> None:
    metadata = {"category": "physical", "target": "selected-pokemon"}
    action_order = {"status": "acts_first", "self_priority": 1}
    snapshot = {
        "field_state_context": {
            "current_field": {
                "weather": "none",
                "terrain": "psychic",
                "global_effects": [],
                "side_effects": [],
                "status": "user_confirmed",
                "source": "user_confirmed_current_field_state",
                "confidence": "known",
            }
        },
        "grounded_context": {
            "opponent": {"status": "known_grounded", "provenance": "user_confirmed_current"}
        },
    }

    blocked = _psychic_terrain_priority_source(snapshot, metadata, action_order)
    assert blocked["status"] == "blocked"
    assert blocked["block_reason"] == "psychic_terrain_priority"

    snapshot["grounded_context"]["opponent"] = {"status": "unknown", "provenance": "unknown"}
    incomplete = _psychic_terrain_priority_source(snapshot, metadata, action_order)
    assert incomplete["status"] == "insufficient_context"
    assert incomplete["missing_inputs"] == ["opponent.grounded"]


@pytest.mark.parametrize("ability", ["queenly-majesty", "dazzling", "armor-tail"])
def test_priority_blocking_abilities_still_block_relevant_positive_priority_moves(ability: str) -> None:
    result = _priority_blocking_ability_source(
        {
            "ability_context": {
                "current_abilities": [{
                    "side": "opponent",
                    "ability": ability,
                    "status": "user_confirmed",
                    "source": "user_confirmed_current_ability",
                    "confidence": "known",
                }]
            }
        },
        {"category": "physical", "target": "selected-pokemon"},
        {"status": "acts_first", "self_priority": 1},
    )

    assert result["status"] == "blocked"
    assert result["block_reason"] == "priority_blocking_ability"
    assert result["defender_ability_authority_used"] == ability


def test_unknown_relevant_priority_blocking_ability_still_fails_closed() -> None:
    result = _priority_blocking_ability_source(
        {
            "ability_context": {
                "current_abilities": [{
                    "side": "opponent",
                    "ability": "unknown",
                    "status": "user_confirmed",
                    "source": "user_confirmed_current_ability",
                    "confidence": "known",
                }]
            }
        },
        {"category": "physical", "target": "selected-pokemon"},
        {"status": "acts_first", "self_priority": 1},
    )

    assert result["status"] == "insufficient_context"
    assert result["missing_inputs"] == ["opponent.priority_blocking_ability"]

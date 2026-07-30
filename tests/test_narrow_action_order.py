import pytest

from llm.advisor_candidate_contract import build_evidence_bundle, build_recommendation_request, evaluate_move_candidate
from llm.narrow_action_order import evaluate_action_order


def _action(move_id: str, priority: int) -> dict[str, object]:
    return {"move_id": move_id, "priority": priority}


@pytest.mark.parametrize(
    ("self_priority", "opponent_priority", "expected"),
    [(1, 0, "acts_first"), (0, 1, "acts_second")],
)
def test_priority_is_decisive_without_speed_or_field(self_priority, opponent_priority, expected):
    result = evaluate_action_order(
        self_action=_action("quick-attack", self_priority), opponent_action=_action("tackle", opponent_priority),
        self_final_speed=None, opponent_final_speed=None, trick_room="unknown",
    )
    assert result["status"] == expected
    assert result["reason"] == "priority_advantage"
    assert result["speed_comparison"] == "not_needed"


@pytest.mark.parametrize(
    ("self_speed", "opponent_speed", "trick_room", "expected"),
    [(120, 80, "inactive", "acts_first"), (80, 120, "inactive", "acts_second"), (80, 120, "active", "acts_first")],
)
def test_equal_priority_uses_only_trusted_final_speed(self_speed, opponent_speed, trick_room, expected):
    result = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=self_speed, opponent_final_speed=opponent_speed, trick_room=trick_room,
    )
    assert result["status"] == expected
    assert result["reason"] == "speed_advantage"


def test_equal_speed_is_explicit_tie_and_unknowns_are_not_defaulted():
    tie = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=100, trick_room="inactive",
    )
    assert tie["status"] == "speed_tie"
    unknown_field = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="unknown",
    )
    assert unknown_field["status"] == "insufficient_context"
    assert unknown_field["missing_inputs"] == ["trick_room"]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"opponent_action": None}, "opponent_action"),
        ({"self_final_speed": None}, "self_final_speed"),
        ({"opponent_final_speed": None}, "opponent_final_speed"),
    ],
)
def test_missing_authoritative_inputs_remain_insufficient(kwargs, expected):
    values = {
        "self_action": _action("tackle", 0), "opponent_action": _action("scratch", 0),
        "self_final_speed": 100, "opponent_final_speed": 90, "trick_room": "inactive",
    }
    values.update(kwargs)
    result = evaluate_action_order(**values)
    assert result["status"] == "insufficient_context"
    assert result["missing_inputs"] == [expected]


def test_conditional_priority_is_explicitly_unsupported():
    result = evaluate_action_order(
        self_action=_action("grassy-glide", 0), opponent_action=_action("tackle", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
    )
    assert result["status"] == "unsupported_mechanic"
    assert result["unsupported_reason"] == "conditional_priority_mechanic"


def _speed(side: str, value: int) -> dict[str, object]:
    return {
        "side": side, "stat": "speed", "value": value, "status": "user_confirmed",
        "source": "user_confirmed_final_battle_stat", "confidence": "known",
    }


def test_candidate_payload_uses_canonical_priority_and_trusted_runtime_only():
    snapshot = {
        "final_stat_context": {"current_final_stats": [_speed("self", 120), _speed("opponent", 80)]},
        "field_state_context": {"current_field": {
            "weather": "none", "terrain": "none", "global_effects": [], "side_effects": [],
            "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known",
        }},
        "opponent_selected_move": {"move_id": "scratch", "priority": 99},
    }
    repositories = {
        "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0},
        "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 1},
    }
    candidate = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=snapshot, repositories=repositories)
    assert candidate["action_order"]["status"] == "acts_second"
    assert candidate["action_order"]["opponent_priority"] == 1
    request = build_recommendation_request(evidence_bundle=build_evidence_bundle(snapshot, [candidate], []))
    assert request["candidate_comparisons"][0]["action_order"] == candidate["action_order"]


def test_candidate_never_promotes_unknown_field_or_unresolved_opponent_metadata():
    snapshot = {
        "final_stat_context": {"current_final_stats": [_speed("self", 120), _speed("opponent", 80)]},
        "opponent_selected_move": {"move_id": "unknown-move"},
    }
    candidate = evaluate_move_candidate(
        slot_index=0, move="tackle", battle_snapshot=snapshot,
        repositories={"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}},
    )
    assert candidate["action_order"]["status"] == "insufficient_context"
    assert candidate["action_order"]["missing_inputs"] == ["opponent_move_priority"]

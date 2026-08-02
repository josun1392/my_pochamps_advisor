import pytest

from llm.advisor_candidate_contract import build_evidence_bundle, build_recommendation_request, evaluate_move_candidate
from llm.advisor_client import format_recommendation_presentation_text
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


def test_trick_room_active_reverses_only_equal_priority_and_omitted_standalone_stays_compatible():
    active = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=80, opponent_final_speed=120, trick_room="active",
        trick_room_provenance="user_confirmed_current",
    )
    priority = evaluate_action_order(
        self_action=_action("quick-attack", 1), opponent_action=_action("scratch", 0),
        self_final_speed=80, opponent_final_speed=120, trick_room="unknown",
        trick_room_provenance="unknown",
    )
    omitted = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=120, opponent_final_speed=80,
    )
    assert active["status"] == "acts_first" and active["trick_room_authority"] == "user_confirmed_current"
    assert priority["status"] == "acts_first" and priority["reason"] == "priority_advantage"
    assert omitted["status"] == "acts_first" and omitted["trick_room_authority"] == "omitted"


def test_trick_room_active_preserves_speed_stage_order_and_tie():
    reversed_order = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=120, trick_room="active",
        self_speed_stage=1, opponent_speed_stage=0,
    )
    tie = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=100, trick_room="active",
    )
    assert reversed_order["status"] == "acts_second" and reversed_order["speed_stage_adjustment_applied"] is True
    assert tie["status"] == "speed_tie"


def test_tailwind_adjusts_stage_resolved_speed_before_trick_room_and_preserves_ties():
    inactive = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=150, trick_room="inactive",
        self_speed_stage=0, opponent_speed_stage=0,
        self_tailwind="active", opponent_tailwind="inactive",
    )
    active = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=150, trick_room="active",
        self_speed_stage=0, opponent_speed_stage=0,
        self_tailwind="active", opponent_tailwind="inactive",
    )
    tie = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=200, trick_room="active",
        self_tailwind="active", opponent_tailwind="inactive",
    )
    assert inactive["status"] == "acts_first" and inactive["tailwind_adjustment_applied"] is True
    assert active["status"] == "acts_second" and active["tailwind_adjustment_applied"] is True
    assert tie["status"] == "speed_tie"


def test_tailwind_unknown_and_malformed_fail_closed_only_for_equal_priority():
    unknown = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_tailwind="unknown", opponent_tailwind="inactive",
    )
    malformed = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_tailwind="invalid", opponent_tailwind="inactive",
    )
    priority = evaluate_action_order(
        self_action=_action("quick-attack", 1), opponent_action=_action("scratch", 0),
        self_final_speed=None, opponent_final_speed=None, trick_room="unknown",
        self_tailwind="unknown", opponent_tailwind="unknown",
    )
    assert unknown["missing_inputs"] == ["self_tailwind"]
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "tailwind_context"
    assert priority["status"] == "acts_first" and priority["reason"] == "priority_advantage"


def test_tailwind_side_authority_variants_do_not_reuse_prior_snapshot_evidence():
    base = {
        "self_action": _action("tackle", 0), "opponent_action": _action("scratch", 0),
        "self_final_speed": 100, "opponent_final_speed": 150, "trick_room": "inactive",
    }
    self_active = evaluate_action_order(**base, self_tailwind="active", opponent_tailwind="inactive")
    opponent_active = evaluate_action_order(**base, self_tailwind="inactive", opponent_tailwind="active")
    both_active = evaluate_action_order(**base, self_tailwind="active", opponent_tailwind="active")
    both_inactive = evaluate_action_order(**base, self_tailwind="inactive", opponent_tailwind="inactive")
    opponent_unknown = evaluate_action_order(**base, self_tailwind="inactive", opponent_tailwind="unknown")
    missing_speed = evaluate_action_order(**{**base, "self_final_speed": None}, self_tailwind="inactive", opponent_tailwind="inactive")
    assert self_active["status"] == "acts_first" and self_active["self_tailwind"] == "active"
    assert opponent_active["status"] == "acts_second" and opponent_active["opponent_tailwind"] == "active"
    assert both_active["status"] == both_inactive["status"] == "acts_second"
    assert opponent_unknown["missing_inputs"] == ["opponent_tailwind"]
    assert missing_speed["missing_inputs"] == ["self_final_speed"]


def test_paralysis_uses_canonical_integer_speed_reduction_before_tailwind_and_trick_room():
    inactive = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=201, opponent_final_speed=150, trick_room="inactive",
        self_paralysis="paralyzed", opponent_paralysis="not_paralyzed",
        self_tailwind="inactive", opponent_tailwind="inactive",
    )
    tailwind = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=201, opponent_final_speed=150, trick_room="inactive",
        self_paralysis="paralyzed", opponent_paralysis="not_paralyzed",
        self_tailwind="active", opponent_tailwind="inactive",
    )
    trick_room = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=201, opponent_final_speed=150, trick_room="active",
        self_paralysis="paralyzed", opponent_paralysis="not_paralyzed",
        self_tailwind="inactive", opponent_tailwind="inactive",
    )
    assert inactive["status"] == "acts_second" and inactive["self_final_speed"] == 100
    assert tailwind["status"] == "acts_first" and tailwind["self_final_speed"] == 200
    assert trick_room["status"] == "acts_first" and trick_room["paralysis_speed_adjustment_applied"] is True


def test_paralysis_unknown_malformed_and_quick_feet_fail_closed_only_when_needed():
    unknown = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_paralysis="unknown", opponent_paralysis="not_paralyzed",
    )
    malformed = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_paralysis="invalid", opponent_paralysis="not_paralyzed",
    )
    quick_feet = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_paralysis="paralyzed", opponent_paralysis="not_paralyzed", self_paralysis_speed_ability_unsupported=True,
    )
    priority = evaluate_action_order(
        self_action=_action("quick-attack", 1), opponent_action=_action("scratch", 0),
        self_final_speed=None, opponent_final_speed=None, trick_room="unknown",
        self_paralysis="unknown", opponent_paralysis="unknown",
    )
    assert unknown["missing_inputs"] == ["self_paralysis"]
    assert malformed["unsupported_reason"] == "paralysis_context"
    assert quick_feet["unsupported_reason"] == "paralysis_speed_ability"
    assert priority["status"] == "acts_first" and "self_paralysis" not in priority


def test_explicit_speed_stage_authority_adjusts_equal_priority_speed_only():
    result = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=120, trick_room="inactive",
        self_speed_stage=1, opponent_speed_stage=0,
    )
    assert result["status"] == "acts_first"
    assert result["speed_stage_adjustment_applied"] is True
    assert (result["self_speed_stage"], result["opponent_speed_stage"]) == (1, 0)


def test_explicit_unknown_or_malformed_speed_stage_fails_closed_but_priority_does_not_need_it():
    unknown = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_speed_stage=None, opponent_speed_stage=0,
    )
    malformed = evaluate_action_order(
        self_action=_action("tackle", 0), opponent_action=_action("scratch", 0),
        self_final_speed=100, opponent_final_speed=90, trick_room="inactive",
        self_speed_stage=7, opponent_speed_stage=0,
    )
    priority = evaluate_action_order(
        self_action=_action("quick-attack", 1), opponent_action=_action("scratch", 0),
        self_final_speed=None, opponent_final_speed=None, trick_room="unknown",
        self_speed_stage=None, opponent_speed_stage=None,
    )
    assert unknown["missing_inputs"] == ["self_speed_stage"]
    assert malformed["status"] == "unsupported_mechanic" and malformed["unsupported_reason"] == "speed_stage_context"
    assert priority["status"] == "acts_first" and "speed_stage_adjustment_applied" not in priority


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


def test_candidate_derives_trick_room_tristate_only_from_confirmed_field_snapshot():
    base = {
        "final_stat_context": {"current_final_stats": [_speed("self", 120), _speed("opponent", 80)]},
        "opponent_selected_move": {"move_id": "scratch"},
        "condition_context": {"current_conditions": [{"side": side, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"} for side in ("self", "opponent")]},
    }
    repository = {
        "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0},
        "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0},
    }
    active = {
        **base,
        "field_state_context": {"current_field": {
            "weather": "none", "terrain": "none", "global_effects": ["trick-room"], "side_effects": [],
            "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known",
        }},
    }
    tails_inactive = {"tailwind": {side: {"status": "known_inactive", "provenance": "user_confirmed_current"} for side in ("self", "opponent")}}
    known = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=active, repositories=repository)
    malformed = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot={**base, "field_state_context": {"current_field": {"global_effects": ["trick-room"]}, **tails_inactive}}, repositories=repository)
    explicit_unknown = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot={**base, "field_state_context": {"trick_room": {"status": "unknown", "provenance": "unknown"}, **tails_inactive}}, repositories=repository)
    assert known["action_order"]["status"] == "acts_second"
    assert known["action_order"]["trick_room"] == "active"
    assert known["action_order"]["trick_room_authority"] == "user_confirmed_current"
    assert malformed["action_order"]["missing_inputs"] == ["trick_room"]
    assert explicit_unknown["action_order"]["missing_inputs"] == ["trick_room"]


def test_candidate_derives_side_owned_tailwind_only_from_confirmed_field_snapshot():
    base = {
        "final_stat_context": {"current_final_stats": [_speed("self", 100), _speed("opponent", 150)]},
        "opponent_selected_move": {"move_id": "scratch"},
        "condition_context": {"current_conditions": [{"side": side, "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"} for side in ("self", "opponent")]},
    }
    repository = {
        "tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0},
        "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0},
    }
    confirmed = {**base, "field_state_context": {"current_field": {
        "weather": "none", "terrain": "none", "global_effects": [], "side_effects": [{"side": "self", "effect": "tailwind"}],
        "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known",
    }}}
    explicit_unknown = {**base, "field_state_context": {"trick_room": {"status": "known_inactive", "provenance": "user_confirmed_current"}, "tailwind": {"self": {"status": "unknown", "provenance": "unknown"}, "opponent": {"status": "known_inactive", "provenance": "user_confirmed_current"}}}}
    known = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=confirmed, repositories=repository)
    unknown = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot=explicit_unknown, repositories=repository)
    assert known["action_order"]["status"] == "acts_first"
    assert known["action_order"]["self_tailwind"] == "active"
    assert known["action_order"]["opponent_tailwind"] == "inactive"
    assert unknown["action_order"]["missing_inputs"] == ["self_tailwind"]


def test_candidate_derives_paralysis_from_confirmed_conditions_and_rejects_quick_feet():
    base = {
        "final_stat_context": {"current_final_stats": [_speed("self", 201), _speed("opponent", 150)]},
        "field_state_context": {"current_field": {"weather": "none", "terrain": "none", "global_effects": [], "side_effects": [], "status": "user_confirmed", "source": "user_confirmed_current_field_state", "confidence": "known"}},
        "opponent_selected_move": {"move_id": "scratch"},
    }
    repository = {"tackle": {"category": "physical", "power": 40, "type": "normal", "priority": 0}, "scratch": {"category": "physical", "power": 40, "type": "normal", "priority": 0}}
    conditions = {"current_conditions": [{"side": "self", "condition_type": "paralysis", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}, {"side": "opponent", "condition_type": "none", "status": "user_confirmed", "source": "user_confirmed_current_condition", "confidence": "known"}]}
    known = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot={**base, "condition_context": conditions}, repositories=repository)
    quick_feet = evaluate_move_candidate(slot_index=0, move="tackle", battle_snapshot={**base, "condition_context": conditions, "ability_context": {"current_abilities": [{"side": "self", "ability": "quick-feet"}]}}, repositories=repository)
    assert known["action_order"]["self_paralysis"] == "paralyzed"
    assert known["action_order"]["status"] == "acts_second"
    assert quick_feet["action_order"]["unsupported_reason"] == "paralysis_speed_ability"


def test_presentation_uses_bounded_trick_room_action_order_text_only_for_selected_candidate():
    presentation = {
        "status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0,
        "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [],
        "selected_candidate": {
            "selected_action": {"slot_index": 0, "move": "tackle"},
            "evidence": {
                "mechanics_result": {"status": "insufficient_context"},
                "action_order": {"status": "acts_first", "reason": "speed_advantage", "trick_room": "active"},
                "comparison_facts": {},
            },
        },
    }
    text = format_recommendation_presentation_text(presentation_model=presentation)
    assert "\ud2b8\ub9ad\ub8f8\uc774 \uc801\uc6a9\ub418\uc5b4 \ub354 \ub290\ub9b0 \ucabd\uc774 \uba3c\uc800 \ud589\ub3d9\ud568" in text
    assert "trick_room" not in text and "user_confirmed_current" not in text


def test_presentation_uses_bounded_tailwind_text_only_when_applied():
    presentation = {
        "status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0,
        "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [],
        "selected_candidate": {"selected_action": {"slot_index": 0, "move": "tackle"}, "evidence": {
            "mechanics_result": {"status": "insufficient_context"},
            "action_order": {"status": "acts_first", "reason": "speed_advantage", "trick_room": "inactive", "self_tailwind": "active", "tailwind_adjustment_applied": True},
            "comparison_facts": {},
        }},
    }
    text = format_recommendation_presentation_text(presentation_model=presentation)
    assert "우리 쪽 순풍을 반영해 먼저 행동함" in text
    assert "tailwind" not in text and "effective_speed" not in text


def test_presentation_uses_bounded_paralysis_text_only_when_applied():
    presentation = {
        "status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0,
        "primary_reasons": [], "risks": [], "alternatives": [], "candidate_summaries": [],
        "selected_candidate": {"selected_action": {"slot_index": 0, "move": "tackle"}, "evidence": {
            "mechanics_result": {"status": "insufficient_context"},
            "action_order": {"status": "acts_second", "reason": "speed_advantage", "trick_room": "inactive", "self_paralysis": "paralyzed", "paralysis_speed_adjustment_applied": True},
            "comparison_facts": {},
        }},
    }
    text = format_recommendation_presentation_text(presentation_model=presentation)
    assert "마비로 감소한 스피드를 반영하면 후공함" in text
    assert "paralysis" not in text and "effective_speed" not in text

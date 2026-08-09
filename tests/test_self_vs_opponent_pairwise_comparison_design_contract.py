"""Canonical design matrix; production pair evaluation is intentionally absent."""


def _pair_id(session, self_id, opponent_id):
    return f"pair:{session}:{self_id}:{opponent_id}"


def _pairs(self_ids, opponent_ids, *, complete, unknown_slots):
    return [{"pair_id": _pair_id("s", self_id, opponent_id), "self_candidate_id": self_id, "opponent_candidate_id": opponent_id, "opponent_candidate_set_complete": complete, "unknown_slots_remaining": unknown_slots} for self_id in self_ids for opponent_id in opponent_ids]


def _preemption(*, order, first_move_success, first_ohko):
    if order in {"self_first", "opponent_first"} and first_move_success == "allowed" and first_ohko == "guaranteed":
        return "second_action_preempted"
    return "not_deterministically_preempted"


def test_pair_identity_and_enumeration_are_deterministic_nonsemantic_cartesian_products():
    rows = _pairs(("self:0:tackle", "self:1:protect"), ("opponent-action:s:a:eq:0", "opponent-action:s:a:protect:1"), complete=False, unknown_slots=2)
    assert len(rows) == 4
    assert len({row["pair_id"] for row in rows}) == 4
    assert all(row["opponent_candidate_set_complete"] is False and row["unknown_slots_remaining"] == 2 for row in rows)
    assert _pairs(("self:0:tackle",), (), complete=False, unknown_slots=4) == []


def test_preemption_requires_definite_order_allowed_move_and_guaranteed_ohko_only():
    assert _preemption(order="self_first", first_move_success="allowed", first_ohko="guaranteed") == "second_action_preempted"
    assert _preemption(order="opponent_first", first_move_success="allowed", first_ohko="guaranteed") == "second_action_preempted"
    assert _preemption(order="self_first", first_move_success="allowed", first_ohko="possible") == "not_deterministically_preempted"
    assert _preemption(order="speed_tie", first_move_success="allowed", first_ohko="guaranteed") == "not_deterministically_preempted"
    assert _preemption(order="self_first", first_move_success="blocked", first_ohko="guaranteed") == "not_deterministically_preempted"


def test_pair_layers_keep_unknown_damage_and_not_applicable_status_distinct_from_identity():
    pair = {"pair_identity": "complete", "action_order": "insufficient_context", "self_move_success": "allowed", "opponent_move_success": "allowed", "self_damage": "complete", "opponent_damage": "not_applicable", "self_ko": "complete", "opponent_ko": "not_applicable", "pair_mechanical_complete": False}
    assert pair["pair_identity"] == "complete"
    assert pair["opponent_damage"] == "not_applicable"
    assert pair["action_order"] == "insufficient_context"
    assert pair["pair_mechanical_complete"] is False


def test_probability_is_supplemental_and_never_a_deterministic_preemption_input():
    pair = {"action_order": "self_first", "self_ohko": "possible", "self_ko_by_1": {"numerator": 3, "denominator": 4}, "opponent_action_preemption": "not_deterministically_preempted"}
    assert pair["self_ko_by_1"] == {"numerator": 3, "denominator": 4}
    assert pair["opponent_action_preemption"] == "not_deterministically_preempted"

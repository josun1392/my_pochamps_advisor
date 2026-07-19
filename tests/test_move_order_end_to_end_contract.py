import llm.advisor_client as client


def test_move_order_acknowledgement_is_exact_and_mutation_safe() -> None:
    expected = (("move_priority", "self", "quick-attack", "1"), ("move_priority", "opponent", "tackle", "0"), ("move_order", "self-first", "priority-advantage", "priority-stage-speed-tailwind-trick-room-only"))
    response = "[Trusted Context]\n[Deterministic Results]\n- Move priority | self | quick-attack | 1\n- Move priority | opponent | tackle | 0\n- Move order | self-first | priority-advantage | priority-stage-speed-tailwind-trick-room-only\n[Advice]\n현재 확인된 우선도에서는 self가 먼저 행동한다."
    assert client.validate_deterministic_result_acknowledgement(response, expected) is None
    assert client.validate_deterministic_result_acknowledgement(response.replace("self-first", "opponent-first"), expected) is not None

from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle


def test_no_usable_fixture_is_blocked_before_provider_when_no_candidates_are_selectable():
    prepared = prepare_ui_recommendation_cycle(
        selected_moves=[{"move_id": "missing-a"}, {"move_id": "missing-b"}],
        battle_input={"scenario": {"mode": "advisor"}, "pokemon": {"my_active": {"name_en": "self"}, "opponent_active": {"name_en": "opponent"}}},
        move_repository={},
    )
    assert prepared["status"] == "no_selectable_candidates"
    assert len(prepared["candidates"]) == 2
    assert prepared["recommendation_request"] is None
    assert all(candidate["availability"] == "unavailable" for candidate in prepared["candidates"])

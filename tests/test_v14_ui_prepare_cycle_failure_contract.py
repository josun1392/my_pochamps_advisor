from llm.advisor_candidate_contract import prepare_ui_recommendation_cycle


def _input():
    return {"scenario": {"known_limitations": []}, "pokemon": {"my_active": {"name_en": "a"}, "opponent_active": {"name_en": "b"}}}


def test_no_candidates_no_selectable_and_invalid_snapshot_are_sanitized_without_repository_output():
    no_candidates = prepare_ui_recommendation_cycle(selected_moves=[], battle_input=_input(), move_repository={})
    no_selectable = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "missing"}], battle_input=_input(), move_repository={})
    invalid = prepare_ui_recommendation_cycle(selected_moves=[{"move_id": "a"}], battle_input={}, move_repository={})
    assert no_candidates["status"] == "no_candidates" and no_candidates["recommendation_request"] is None
    assert no_selectable["status"] == "no_selectable_candidates" and no_selectable["recommendation_request"] is None
    assert invalid == {"status": "invalid_snapshot", "candidates": [], "evidence_bundle": None, "recommendation_request": None, "recommendation_result": None, "errors": ["missing_selected_pokemon"]}
    assert all("repositories" not in value and "move_repository" not in value for value in (no_candidates, no_selectable, invalid))

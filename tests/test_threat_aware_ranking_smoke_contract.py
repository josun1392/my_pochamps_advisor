from scripts.run_sanitized_threat_ranking_smoke import EXIT, FIXTURES, _prepared, run_smoke


def _response(payload):
    winner = next(row for row in payload["candidate_comparisons"] if row["mechanics_comparison"]["rank"] == 1)
    return {"recommendation_status": "resolved", "selected_candidate_id": winner["slot_index"], "explanation_code": "clear_ranked_winner"}


def test_fake_provider_grounding_preflights_partial_danger_and_neutral_fixtures():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 2


def test_fixture_one_penalizes_danger_and_fixture_two_preserves_base_order():
    danger, neutral = (_prepared(fixture) for fixture in FIXTURES)
    assert [row["mechanics_comparison"]["rank"] for row in danger["recommendation_request"]["candidate_comparisons"]] == [2, 1]
    assert [row["mechanics_comparison"]["rank"] for row in neutral["recommendation_request"]["candidate_comparisons"]] == [1, 2]
    assert all(summary["candidate_set_complete"] is False and summary["unknown_slots_remaining"] == 3 for summary in neutral["evidence_bundle"]["known_opponent_threat_summaries"]["threat_summaries"])


def test_smoke_runner_rejects_unapproved_fixture_order_before_provider_call():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=(FIXTURES[1], FIXTURES[0]), max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["usage"] and result["provider_calls"] == 0

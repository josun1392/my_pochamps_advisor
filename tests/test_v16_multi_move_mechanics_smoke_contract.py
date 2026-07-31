from copy import deepcopy
import json

from scripts.run_sanitized_multi_move_mechanics_smoke import ACCURACY_FIXTURES, CONSEQUENCE_FIXTURES, EXIT, FIXED_HIT_FIXTURES, FIXTURES, GROUNDING_FIXTURES, STATUS_FIXTURES, _prepared, main, run_smoke


def _code(rows, winner):
    comparison = winner["mechanics_comparison"]
    if comparison["comparison_reason"] == "only_rankable_candidate":
        return "only_rankable_candidate"
    rankable = [row for row in rows if row["mechanics_comparison"]["comparison_status"] == "rankable"]
    return "stable_tie_break" if any(row is not winner and row["mechanics_result"] == winner["mechanics_result"] for row in rankable) else "clear_ranked_winner"


def _response(payload, *, selected=None):
    rows = payload["candidate_comparisons"]
    winner = next(row for row in rows if row["mechanics_comparison"]["rank"] == 1)
    if selected is not None:
        winner = next(row for row in rows if row["slot_index"] == selected)
    return {"recommendation_status": "resolved", "selected_candidate_id": winner["slot_index"], "explanation_code": _code(rows, winner)}


def test_three_fixture_fake_provider_binds_deterministic_acknowledgements():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 3


def test_multi_candidate_grounding_fixtures_preserve_isolated_mechanics_and_action_order():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=GROUNDING_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 2
    complete = _prepared(GROUNDING_FIXTURES[0])["recommendation_request"]["candidate_comparisons"]
    assert all(row["comparison_facts"]["candidate_id"] == {"slot_index": row["slot_index"], "move": row["move"]} for row in complete)
    assert any(row["action_order"]["status"] == "acts_first" for row in complete)
    mixed = _prepared(GROUNDING_FIXTURES[1])["recommendation_request"]["candidate_comparisons"]
    assert [row["mechanics_result"]["status"] for row in mixed] == ["known", "insufficient_context", "unsupported_mechanic"]


def test_accuracy_fixture_pair_preserves_numeric_and_always_hit_distinction():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=ACCURACY_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 2
    known = _prepared(ACCURACY_FIXTURES[0])["recommendation_request"]["candidate_comparisons"]
    assert [row["accuracy_evidence"]["status"] for row in known] == ["known_accuracy", "known_accuracy"]
    assert known[0]["accuracy_evidence"]["canonical_accuracy"] == 100
    mixed = _prepared(ACCURACY_FIXTURES[1])["recommendation_request"]["candidate_comparisons"]
    assert [row["accuracy_evidence"]["status"] for row in mixed] == ["known_accuracy", "always_hits", "unsupported_mechanic"]


def test_status_fixture_pair_keeps_roles_separate_from_damage_and_selected_evidence():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=STATUS_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 2
    damage_status = _prepared(STATUS_FIXTURES[0])["recommendation_request"]["candidate_comparisons"]
    assert [row["status_move_evidence"]["role_tags"] for row in damage_status] == [[], ["recovery"], ["self_stat_raise"]]
    assert all("damage_range" not in row["mechanics_result"] for row in damage_status[1:])
    mixed = _prepared(STATUS_FIXTURES[1])["recommendation_request"]["candidate_comparisons"]
    assert [row["status_move_evidence"]["status"] for row in mixed] == ["not_applicable", "known_role", "insufficient_context", "unsupported_mechanic"]
    assert all(row["comparison_facts"]["candidate_id"] == {"slot_index": row["slot_index"], "move": row["move"]} for row in mixed)


def test_consequence_fixture_pair_keeps_canonical_tags_candidate_local():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=CONSEQUENCE_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 2
    recoil = _prepared(CONSEQUENCE_FIXTURES[0])["recommendation_request"]["candidate_comparisons"]
    assert [row["move_consequence_evidence"]["consequence_tags"] for row in recoil] == [["recoil"], ["drain_or_healing_from_damage"], []]
    terminal = _prepared(CONSEQUENCE_FIXTURES[1])["recommendation_request"]["candidate_comparisons"]
    assert [row["move_consequence_evidence"]["status"] for row in terminal] == ["known", "known", "known", "unsupported_mechanic"]


def test_fixed_hit_fixture_pair_preserves_per_hit_total_and_variable_hit_boundary():
    result = run_smoke(actual=True, model="gemini-2.5-flash", fixtures=FIXED_HIT_FIXTURES, max_calls=2, no_retry=True, credential_available=lambda: True, provider_call=_response)
    assert result["exit_code"] == EXIT["ok"] and result["provider_calls"] == 2
    complete = _prepared(FIXED_HIT_FIXTURES[0])["recommendation_request"]["candidate_comparisons"]
    fixed = complete[0]["mechanics_result"]
    assert fixed["hit_count"] == 2
    assert isinstance(fixed["per_hit_damage_range"], dict)
    assert isinstance(fixed["damage_range"], dict)
    assert complete[0]["mechanics_comparison"]["rank"] == 1
    assert complete[1]["mechanics_result"]["hit_count"] == 1
    mixed = _prepared(FIXED_HIT_FIXTURES[1])["recommendation_request"]["candidate_comparisons"]
    assert mixed[0]["mechanics_result"]["hit_count"] == 2
    assert [row["mechanics_result"].get("unsupported_reason") for row in mixed[1:]] == ["variable_multi_hit_move", "invalid_fixed_hit_count"]


def test_cli_allows_only_the_bounded_multi_candidate_fixture_pair(capsys):
    def adapters(*, model):
        assert model == "gemini-2.5-flash"
        return (lambda: True), _response

    assert main(["--actual", "--model", "gemini-2.5-flash", "--fixtures", *GROUNDING_FIXTURES, "--max-calls", "2", "--no-retry"], adapter_factory=adapters) == EXIT["ok"]
    assert json.loads(capsys.readouterr().out) == {"exit_code": EXIT["ok"], "provider_calls": 2}


def test_cli_allows_the_bounded_status_fixture_pair(capsys):
    def adapters(*, model):
        assert model == "gemini-2.5-flash"
        return (lambda: True), _response

    assert main(["--actual", "--model", "gemini-2.5-flash", "--fixtures", *STATUS_FIXTURES, "--max-calls", "2", "--no-retry"], adapter_factory=adapters) == EXIT["ok"]
    assert json.loads(capsys.readouterr().out) == {"exit_code": EXIT["ok"], "provider_calls": 2}


def test_cli_allows_the_bounded_fixed_hit_fixture_pair(capsys):
    def adapters(*, model):
        assert model == "gemini-2.5-flash"
        return (lambda: True), _response

    assert main(["--actual", "--model", "gemini-2.5-flash", "--fixtures", *FIXED_HIT_FIXTURES, "--max-calls", "2", "--no-retry"], adapter_factory=adapters) == EXIT["ok"]
    assert json.loads(capsys.readouterr().out) == {"exit_code": EXIT["ok"], "provider_calls": 2}


def test_multi_provider_rejects_wrong_candidate_rank_and_extra_acknowledgements():
    from llm.advisor_candidate_contract import complete_recommendation_cycle
    prepared = _prepared(FIXTURES[0])
    wrong = _response(prepared["recommendation_request"], selected=0)
    assert complete_recommendation_cycle(prepared_cycle=prepared, response_payload=wrong)["errors"] == ["multi_provider_binding_invalid"]
    extra = deepcopy(_response(prepared["recommendation_request"]))
    extra["ranking_acknowledgements"] = []
    assert complete_recommendation_cycle(prepared_cycle=prepared, response_payload=extra)["errors"] == ["multi_provider_binding_invalid"]


def test_multi_provider_rejects_wrong_code_and_nonrankable_selection():
    from llm.advisor_candidate_contract import complete_recommendation_cycle
    mixed = _prepared(FIXTURES[1])
    wrong_code = _response(mixed["recommendation_request"])
    wrong_code["explanation_code"] = "clear_ranked_winner"
    assert complete_recommendation_cycle(prepared_cycle=mixed, response_payload=wrong_code)["errors"] == ["multi_provider_binding_invalid"]
    nonrankable = _response(mixed["recommendation_request"], selected=1)
    assert complete_recommendation_cycle(prepared_cycle=mixed, response_payload=nonrankable)["errors"] == ["multi_provider_binding_invalid"]


def test_schema_is_minimal_and_native_evidence_remains_server_side():
    from llm.advisor_client import _structured_provider_schema
    prepared = _prepared(FIXTURES[2])
    payload = prepared["recommendation_request"]
    schema = _structured_provider_schema(mechanics_grounding_required=True, ranking_acknowledgement_required=True, provider_payload=payload)
    assert set(schema["properties"]) == {"recommendation_status", "selected_candidate_id", "explanation_code"}
    completed = __import__("llm.advisor_candidate_contract", fromlist=["complete_recommendation_cycle"]).complete_recommendation_cycle(prepared_cycle=prepared, response_payload=_response(payload))
    assert completed["status"] == "resolved"
    assert completed["candidates"][0]["mechanics_result"] == payload["candidate_comparisons"][0]["mechanics_result"]


def test_default_invalid_and_unavailable_paths_do_not_call_provider():
    calls = []
    assert run_smoke(actual=False, provider_call=lambda _: calls.append(True))["provider_calls"] == 0
    assert run_smoke(actual=True, model="wrong", fixtures=FIXTURES, max_calls=3, no_retry=True, credential_available=lambda: True, provider_call=lambda _: calls.append(True))["exit_code"] == EXIT["usage"]
    assert calls == []

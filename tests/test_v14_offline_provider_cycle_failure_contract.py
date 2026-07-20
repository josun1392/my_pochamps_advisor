from copy import deepcopy

from llm.advisor_candidate_contract import run_offline_recommendation_cycle
from tests.test_v14_offline_provider_cycle_contract import _battle_input, _response


REPOSITORY = {"tackle": {"category": "physical", "power": 40, "type": "normal"}}


def test_nonready_preparation_blocks_provider_and_keeps_preparation_result():
    calls = []
    result = run_offline_recommendation_cycle(selected_moves=[], battle_input=_battle_input(), move_repository=REPOSITORY, fake_provider=lambda payload: calls.append(payload))
    assert result["status"] == "preparation_not_ready" and calls == []
    assert result["provider_stage"] is None and result["prepared_cycle"]["status"] == "no_candidates"


def test_provider_exception_and_malformed_response_preserve_prepared_evidence_without_raw_return():
    exploding = run_offline_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=_battle_input(), move_repository=REPOSITORY, fake_provider=lambda _: (_ for _ in ()).throw(RuntimeError("private secret")))
    malformed = run_offline_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=_battle_input(), move_repository=REPOSITORY, fake_provider=lambda _: "raw response")
    for result, status in ((exploding, "provider_unavailable"), (malformed, "provider_response_malformed")):
        assert result["status"] == status and result["completed_cycle"] is None
        assert result["prepared_cycle"]["evidence_bundle"] and "raw response" not in str(result)


def test_semantic_failure_keeps_evidence_without_retry_or_raw_response_alias():
    calls = []
    raw = _response(); raw["primary_reasons"] = [{"kind": "partial_context", "claim": "missing evidence"}]
    result = run_offline_recommendation_cycle(selected_moves=[{"move_id": "tackle"}], battle_input=_battle_input(), move_repository=REPOSITORY, fake_provider=lambda _: calls.append(1) or raw)
    raw["recommended_move"] = "changed"
    assert calls == [1] and result["status"] == "response_validation_failed"
    assert result["completed_cycle"]["evidence_bundle"] == result["prepared_cycle"]["evidence_bundle"]
    assert "changed" not in str(result) and "response_payload" in result["provider_stage"]

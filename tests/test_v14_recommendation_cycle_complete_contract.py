from copy import deepcopy
import inspect

import llm.advisor_candidate_contract as contract
from llm.advisor_client import run_ui_selected_advice


def _ready_cycle():
    candidate = {"slot_index": 0, "move": "move", "status": "resolved", "availability": "usable", "damage": {"status": "resolved"}, "dynamic_move": None, "self_effects": [], "warnings": [], "unavailable_reasons": []}
    evidence = contract.build_evidence_bundle({}, [candidate], [])
    request = contract.build_recommendation_request(evidence_bundle=evidence)
    return {"status": "ready", "candidates": [candidate], "evidence_bundle": evidence, "recommendation_request": request, "errors": []}


def _payload():
    return {"recommendation_status": "resolved", "recommended_move": "move", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": []}


def test_completion_reuses_parser_and_copies_inputs_without_raw_response_retention():
    cycle = _ready_cycle(); before = deepcopy(cycle); payload = _payload()
    completed = contract.complete_recommendation_cycle(prepared_cycle=cycle, response_payload=payload)
    payload["recommended_move"] = "mutated"; cycle["candidates"][0]["move"] = "mutated"
    assert completed["status"] == "resolved" and completed["recommendation_result"]["recommended_move"] == "move"
    assert before["recommendation_request"] == completed["recommendation_request"] and "response_payload" not in completed


def test_nonready_and_parser_failure_preserve_evidence_with_sanitized_errors():
    nonready = contract.complete_recommendation_cycle(prepared_cycle={"status": "no_candidates", "candidates": [], "evidence_bundle": {}}, response_payload=_payload())
    assert nonready == {"status": "cycle_not_ready", "candidates": [], "evidence_bundle": {}, "recommendation_request": None, "recommendation_result": None, "errors": ["cycle_not_ready"]}
    cycle = _ready_cycle(); before = deepcopy(cycle)
    failed = contract.complete_recommendation_cycle(prepared_cycle=cycle, response_payload={**_payload(), "risks": [{"raw_response": "private"}]})
    assert failed["status"] == "response_validation_failed" and "private" not in str(failed) and failed["evidence_bundle"] == before["evidence_bundle"]


def test_pure_cycle_has_no_provider_ui_or_selected_move_flow_dependency():
    source = inspect.getsource(contract)
    assert "advisor_client" not in source and "ui." not in source and "run_ui_selected_advice" not in source
    assert "prepare_recommendation_cycle" not in inspect.getsource(run_ui_selected_advice)

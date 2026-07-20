from copy import deepcopy
import inspect

from llm import advisor_candidate_contract
from llm.advisor_candidate_contract import build_recommendation_presentation_model


def _completed():
    return {"status": "resolved", "candidates": [{"slot_index": 0, "move": "tackle", "warnings": []}], "recommendation_result": {"status": "resolved", "recommended_move": "tackle", "recommended_slot_index": 0, "primary_reasons": [], "risks": [], "alternatives": [], "errors": []}, "errors": []}


def test_presentation_copies_completed_cycle_and_excludes_provider_internals():
    completed = _completed(); model = build_recommendation_presentation_model(completed_cycle=completed)
    completed["candidates"][0]["move"] = "changed"; completed["recommendation_result"]["primary_reasons"].append({"kind": "damage"})
    assert model["candidate_summaries"][0]["move"] == "tackle" and model["primary_reasons"] == []
    assert not ({"provider_stage", "response_payload", "raw_response", "repository", "fake_provider"} & set(model))


def test_presentation_rejects_unsafe_objects_and_pure_module_has_no_qt_or_provider_call():
    unsafe = _completed(); unsafe["candidates"] = [{"bad": object()}]
    model = build_recommendation_presentation_model(completed_cycle=unsafe)
    source = inspect.getsource(advisor_candidate_contract)
    assert model["status"] == "validation_failed" and model["candidate_summaries"] == []
    assert "call_gemini(" not in source and "PySide6" not in source and "requests." not in source

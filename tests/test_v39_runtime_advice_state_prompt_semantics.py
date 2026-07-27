from llm.advisor_candidate_contract import adapt_provider_recommendation_response, validate_runtime_grounding
from llm.advisor_client import _STRUCTURED_SEMANTIC_GUIDANCE


def _response(*, grounding=None):
    value = {
        "recommendation_status": "insufficient_context",
        "recommended_move": None,
        "recommended_slot_index": None,
        "primary_reasons": [], "risks": [], "alternatives": [],
    }
    if grounding is not None:
        value["grounding"] = grounding
    return value


def _grounding():
    return {"schema_version": "grounding-v1", "confirmed_facts": [], "unknown_facts": [], "evidence_only": [], "conflicts": [], "conditional_dependencies": []}


def test_prompt_defines_runtime_state_unknown_and_known_absent_semantics():
    text = _STRUCTURED_SEMANTIC_GUIDANCE.lower()
    assert "runtime_advice_state" in text
    assert "unknown is unobserved" in text
    assert "known_absent is confirmed absence" in text
    assert "cannot override runtime known facts" in text


def test_grounding_v1_requires_exact_fields():
    assert adapt_provider_recommendation_response(provider_response=_response(grounding=_grounding()))["grounding"]["schema_version"] == "grounding-v1"
    assert adapt_provider_recommendation_response(provider_response=_response(grounding={"schema_version": "grounding-v1"}))["status"] == "provider_response_validation_failed"


def test_legacy_six_field_response_remains_explicitly_valid():
    assert adapt_provider_recommendation_response(provider_response=_response())["recommendation_status"] == "insufficient_context"


def test_grounding_rejects_internal_metadata_shape():
    bad = _grounding(); bad["fingerprint"] = "secret"
    assert adapt_provider_recommendation_response(provider_response=_response(grounding=bad))["status"] == "provider_response_validation_failed"


def test_validator_rejects_unknown_promoted_to_known_and_internal_answer():
    runtime = {"self": {"item": {"status": "unknown"}}}
    grounding = _grounding(); grounding["confirmed_facts"] = [{"path": "self.item", "status": "known", "value": "Focus Sash"}]
    assert "unknown_promoted" in validate_runtime_grounding(runtime_advice_state=runtime, grounding=grounding)
    assert "internal_metadata_in_answer" in validate_runtime_grounding(runtime_advice_state=runtime, grounding=_grounding(), user_answer="fingerprint")


def test_validator_accepts_known_absent_and_unknown():
    runtime = {"field": {"weather": {"status": "known_absent"}, "terrain": {"status": "unknown"}}}
    grounding = _grounding(); grounding["confirmed_facts"] = [{"path": "field.weather", "status": "known_absent"}]; grounding["unknown_facts"] = [{"path": "field.terrain"}]
    assert validate_runtime_grounding(runtime_advice_state=runtime, grounding=grounding) == []

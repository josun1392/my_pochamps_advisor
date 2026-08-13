from llm.advisor_candidate_contract import build_recommendation_request, complete_recommendation_cycle
from llm.advisor_client import _structured_provider_schema


def _prepared_cycle():
    candidate = {
        "slot_index": 0,
        "move": "tackle",
        "status": "resolved",
        "availability": "usable",
        "damage": {"status": "resolved"},
        "dynamic_move": None,
        "self_effects": [],
        "warnings": [],
        "unavailable_reasons": [],
    }
    evidence_bundle = {
        "battle_snapshot_summary": {},
        "candidates": [candidate],
        "known_limitations": [],
    }
    return {
        "status": "ready",
        "candidates": [candidate],
        "evidence_bundle": evidence_bundle,
        "recommendation_request": build_recommendation_request(evidence_bundle=evidence_bundle),
        "errors": [],
    }


def _response(*, reason):
    return {
        "recommendation_status": "resolved",
        "recommended_move": "tackle",
        "recommended_slot_index": 0,
        "primary_reasons": [reason],
        "risks": [],
        "alternatives": [],
    }


def test_generic_claim_schema_does_not_expose_internal_mechanics_linkage_fields():
    claim_schema = _structured_provider_schema()["properties"]["primary_reasons"]["items"]
    assert set(claim_schema["properties"]) == {"kind", "claim"}
    assert "numeric mechanics values" in claim_schema["properties"]["claim"]["description"]


def test_generic_grounded_claim_passes_but_unprojected_numeric_linkage_stays_rejected():
    prepared = _prepared_cycle()
    valid = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload=_response(reason={"kind": "damage", "claim": "deterministic damage evidence"}),
    )
    assert valid["status"] == "resolved"

    invalid = complete_recommendation_cycle(
        prepared_cycle=prepared,
        response_payload=_response(
            reason={
                "kind": "damage",
                "claim": "deterministic damage evidence",
                "mechanics_path": "candidate_comparisons.0.mechanics_result",
                "numeric_scope": "damage_range",
            }
        ),
    )
    assert invalid["status"] == "response_validation_failed"
    assert invalid["errors"] == ["mechanics_numeric_scope_invalid"]

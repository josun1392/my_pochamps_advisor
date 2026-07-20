import math
import sys

import pytest

from llm.advisor_candidate_contract import build_recommendation_request, serialize_recommendation_request


def _candidate():
    return {"slot_index": 0, "move": "protect", "status": "partial", "availability": "partially_evaluable",
            "damage": {"status": "resolved", "ko": {"status": "possible"}}, "hit_chance": {"status": "resolved"},
            "move_order": {"status": "resolved"}, "self_effects": [{"effect": {"amount": 1}}],
            "dynamic_move": {"status": "resolved", "effective_power": 40}, "warnings": ["w"], "unavailable_reasons": ["r"]}


def test_request_and_serialization_deep_copy_source_evidence_without_provider_fields():
    snapshot = {"nested": [1]}; candidate = _candidate(); limitations = ["limited"]
    request = build_recommendation_request(evidence_bundle={"battle_snapshot_summary": snapshot, "candidates": [candidate], "known_limitations": limitations})
    snapshot["nested"].append(2); candidate["damage"]["ko"]["status"] = "mutated"; candidate["hit_chance"]["status"] = "mutated"; candidate["move_order"]["status"] = "mutated"; candidate["dynamic_move"]["effective_power"] = 9; candidate["self_effects"][0]["effect"]["amount"] = 9; limitations.append("mutated")
    serialized = serialize_recommendation_request(request)
    serialized["candidate_comparisons"][0]["warnings"].append("serialized-only")
    assert request["battle_snapshot_summary"] == {"nested": [1]}
    assert request["candidate_comparisons"][0]["damage"] == {"status": "resolved", "ko": {"status": "possible"}}
    assert request["candidate_comparisons"][0]["hit_chance"] == {"status": "resolved"}
    assert request["candidate_comparisons"][0]["move_order"] == {"status": "resolved"}
    assert request["candidate_comparisons"][0]["dynamic_move"] == {"status": "resolved", "effective_power": 40}
    assert request["candidate_comparisons"][0]["self_effects"] == [{"effect": {"amount": 1}}]
    assert request["known_limitations"] == ["limited"] and request["candidate_comparisons"][0]["warnings"] == ["w"]
    assert not ({"ranking_score", "automatic_winner", "provider_model", "api_key", "raw_prompt", "raw_response", "token_usage"} & set(request))


@pytest.mark.parametrize("value", [{"nested": {"API-Key": "secret"}}, {"access_token": "secret"}, {"x": math.nan}, {"x": math.inf}, {"x": -math.inf}, {"x": ValueError("private")}, {"x": object()}, {"x": lambda: None}, {"x": sys}])
def test_serialization_rejects_nested_secrets_and_non_json_safe_values(value):
    with pytest.raises(ValueError):
        serialize_recommendation_request(value)

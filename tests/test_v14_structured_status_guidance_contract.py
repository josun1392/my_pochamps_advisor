from llm.advisor_client import _STRUCTURED_SEMANTIC_GUIDANCE


def test_status_guidance_avoids_fabricated_recommendation_pairs():
    assert "no_usable_candidate" in _STRUCTURED_SEMANTIC_GUIDANCE and "resolved recommendation" in _STRUCTURED_SEMANTIC_GUIDANCE

from llm.advisor_client import _STRUCTURED_RESPONSE_KEYS, _STRUCTURED_SEMANTIC_GUIDANCE


def test_guidance_matches_status_and_alternative_parser_contract():
    assert "insufficient_context" in _STRUCTURED_SEMANTIC_GUIDANCE
    assert "move+slot" in _STRUCTURED_SEMANTIC_GUIDANCE and len(_STRUCTURED_RESPONSE_KEYS) == 6

from llm.advisor_client import _STRUCTURED_SEMANTIC_GUIDANCE, _STRUCTURED_PROVIDER_PAYLOAD_KEYS


def test_guidance_forbids_contradictory_partial_context_without_changing_payload_keys():
    assert "Never use partial_context" in _STRUCTURED_SEMANTIC_GUIDANCE
    assert len(_STRUCTURED_PROVIDER_PAYLOAD_KEYS) == 7

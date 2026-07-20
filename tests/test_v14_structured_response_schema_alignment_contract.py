from llm.advisor_client import _STRUCTURED_RESPONSE_KEYS, _structured_provider_schema


def test_provider_schema_and_adapter_six_field_contract_align():
    assert set(_structured_provider_schema()["properties"]) == set(_STRUCTURED_RESPONSE_KEYS)

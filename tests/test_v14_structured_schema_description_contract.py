from llm.advisor_client import _structured_provider_schema


def test_schema_descriptions_cover_exact_pair_grounding_and_alternatives():
    properties = _structured_provider_schema()["properties"]
    assert all("description" in properties[key] for key in properties)
    assert "exact selectable" in properties["recommended_move"]["description"].lower()

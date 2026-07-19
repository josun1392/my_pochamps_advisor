import llm.advisor_client as client


def test_hit_chance_result_is_exact_and_semantically_limited() -> None:
    expected = (("hit_chance", "self", "opponent", "stone-edge", "80%", "stage-adjusted-accuracy", "move-accuracy-and-stages-only"),)
    response = "[Trusted Context]\n[Deterministic Results]\n- Hit chance | self | opponent | stone-edge | 80% | stage-adjusted-accuracy | move-accuracy-and-stages-only\n[Advice]\nThe limited hit chance is 80%."
    assert client.validate_deterministic_result_acknowledgement(response, expected) is None
    assert client.validate_deterministic_result_acknowledgement(response.replace("80%", "81%"), expected) is not None
    assert client.evaluate_deterministic_result_response(response + " No Guard guarantees the hit.", (), expected) == "deterministic-results semantic boundary violation"
